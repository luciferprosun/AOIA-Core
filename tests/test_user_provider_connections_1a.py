from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.providers.user_connections import (
    OPENROUTER_BASE_URL,
    PROVIDER_STORE_SCHEMA_VERSION,
    ProviderConnection,
    UserProviderStore,
    UserProviderStoreError,
    openrouter_connection_preset,
)
from runtime.providers.redaction import redact_provider_text


class UserProviderConnections1ATests(unittest.TestCase):
    def make_store(self, root: Path) -> UserProviderStore:
        return UserProviderStore(
            root / "project",
            state_root=root / "state",
            secrets_root=root / "secrets",
        )

    def create_openrouter(
        self,
        store: UserProviderStore,
        *,
        connection_id: str = "my-openrouter",
        api_key: str | None = None,
    ) -> ProviderConnection:
        return store.create_connection(
            connection_id=connection_id,
            display_name="My OpenRouter",
            api_style="openai_compatible",
            base_url=OPENROUTER_BASE_URL,
            native_adapter_id=None,
            credential_reference=f"{connection_id}-credential",
            created_at="2026-07-20T23:45:00+02:00",
            api_key=api_key,
        )

    def test_connection_and_secret_are_stored_separately_with_private_modes(self) -> None:
        secret = "sk-test-provider-secret-value"
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            store = self.make_store(root)
            connection = self.create_openrouter(store, api_key=secret)

            self.assertEqual("configured", store.credential_status(connection.credential_reference))
            self.assertEqual(secret, store.read_credential(connection.credential_reference))
            self.assertEqual((connection,), store.list_connections())
            rendered = store.config_path.read_text(encoding="utf-8")
            self.assertNotIn(secret, rendered)
            self.assertNotIn(secret, connection.connection_revision_hash)
            self.assertNotIn(secret, repr(connection))
            credential_path = root / "secrets" / "my-openrouter-credential.key"
            self.assertEqual(0o700, stat.S_IMODE((root / "secrets").stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE(credential_path.stat().st_mode))
            self.assertEqual(0o600, stat.S_IMODE(store.config_path.stat().st_mode))

    def test_missing_credential_is_masked_and_never_read_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            connection = self.create_openrouter(store)
            self.assertEqual("missing", store.credential_status(connection.credential_reference))
            with self.assertRaisesRegex(UserProviderStoreError, "credential is missing"):
                store.read_credential(connection.credential_reference)

    def test_duplicate_connection_id_fails_closed_without_replacing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            original = self.create_openrouter(store)
            with self.assertRaisesRegex(UserProviderStoreError, "duplicate connection_id"):
                self.create_openrouter(store)
            self.assertEqual((original,), store.list_connections())

    def test_duplicate_credential_reference_cannot_overwrite_another_connection(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            original = self.create_openrouter(store, api_key="first-safe-secret")
            with self.assertRaisesRegex(UserProviderStoreError, "duplicate credential_reference"):
                store.create_connection(
                    connection_id="second-openrouter",
                    display_name="Second OpenRouter",
                    api_style="openai_compatible",
                    base_url=OPENROUTER_BASE_URL,
                    credential_reference=original.credential_reference,
                    created_at="operator-time",
                    api_key="second-safe-secret",
                )
            self.assertEqual("first-safe-secret", store.read_credential(original.credential_reference))

    def test_loaded_configuration_rejects_duplicate_credential_references(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            first = ProviderConnection(
                connection_id="first-connection",
                display_name="First Connection",
                api_style="openai_compatible",
                base_url=OPENROUTER_BASE_URL,
                native_adapter_id=None,
                credential_reference="shared-credential",
                enabled=True,
                created_at="operator-time",
            )
            second = ProviderConnection(
                connection_id="second-connection",
                display_name="Second Connection",
                api_style="openai_compatible",
                base_url="https://models.example.test/v1",
                native_adapter_id=None,
                credential_reference="shared-credential",
                enabled=True,
                created_at="operator-time",
            )
            store.state_root.mkdir(parents=True)
            store.config_path.write_text(
                json.dumps(
                    {
                        "schema_version": PROVIDER_STORE_SCHEMA_VERSION,
                        "connections": [first.to_dict(), second.to_dict()],
                        "model_profiles": [],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(UserProviderStoreError, "duplicate credential references"):
                store.list_connections()

    def test_secret_like_values_are_rejected_from_normal_metadata(self) -> None:
        explicit_key = "sk-" + "A" * 24
        with self.assertRaisesRegex(UserProviderStoreError, "secret-like"):
            ProviderConnection(
                connection_id="metadata-secret-test",
                display_name=f"Connection {explicit_key}",
                api_style="openai_compatible",
                base_url="https://models.example.test/v1",
                native_adapter_id=None,
                credential_reference="metadata-secret-key",
                enabled=True,
                created_at="operator-time",
            )
        with self.assertRaisesRegex(UserProviderStoreError, "secret-like"):
            ProviderConnection(
                connection_id="metadata-url-test",
                display_name="Metadata URL Test",
                api_style="openai_compatible",
                base_url=f"https://models.example.test/{explicit_key}",
                native_adapter_id=None,
                credential_reference="metadata-url-key",
                enabled=True,
                created_at="operator-time",
            )

    def test_arbitrary_configured_key_cannot_enter_connection_metadata_or_hash(self) -> None:
        arbitrary_key = "plain-private-key-material-12345"
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            with self.assertRaises(UserProviderStoreError) as caught:
                store.create_connection(
                    connection_id="private-key-connection",
                    display_name=f"Connection {arbitrary_key}",
                    api_style="openai_compatible",
                    base_url=OPENROUTER_BASE_URL,
                    credential_reference="private-key-reference",
                    created_at="operator-time",
                    api_key=arbitrary_key,
                )
            self.assertNotIn(arbitrary_key, str(caught.exception))
            self.assertFalse(store.config_path.exists())

    def test_secret_equivalence_is_rejected_before_connection_hashing(self) -> None:
        arbitrary_key = "plain-prehash-connection-key-material-12345"
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            with (
                patch(
                    "runtime.providers.user_connections.canonical_sha256",
                    side_effect=AssertionError("hashing must not run"),
                ),
                self.assertRaisesRegex(
                    UserProviderStoreError,
                    "contains configured credential material",
                ),
            ):
                store.create_connection(
                    connection_id="prehash-connection",
                    display_name=f"Connection {arbitrary_key}",
                    api_style="openai_compatible",
                    base_url=OPENROUTER_BASE_URL,
                    credential_reference="prehash-reference",
                    created_at="operator-time",
                    api_key=arbitrary_key,
                )
            self.assertFalse(store.config_path.exists())

    def test_preprovisioned_credential_cannot_enter_new_connection_metadata(self) -> None:
        secret = "ordinary-preprovisioned-credential-material-001"
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            store.save_credential("future-connection", secret)
            with self.assertRaisesRegex(
                UserProviderStoreError,
                "contains configured credential material",
            ):
                store.create_connection(
                    connection_id="future-connection",
                    display_name=f"Connection {secret}",
                    api_style="openai_compatible",
                    base_url="https://future.example.test/v1",
                    credential_reference="future-connection",
                    created_at="operator-time",
                    api_key=None,
                )
            self.assertFalse(store.config_path.exists())

    def test_credential_cannot_equal_connection_hash_or_json_schema_key(self) -> None:
        values = {
            "connection_id": "hash-collision-connection",
            "display_name": "Hash Collision Connection",
            "api_style": "openai_compatible",
            "base_url": OPENROUTER_BASE_URL,
            "native_adapter_id": None,
            "credential_reference": "hash-collision-reference",
            "enabled": True,
            "created_at": "operator-time",
        }
        predicted_hash = ProviderConnection(**values).connection_revision_hash
        for secret in (predicted_hash, "schema_version"):
            with self.subTest(secret_kind="hash" if len(secret) == 64 else "json-key"):
                with tempfile.TemporaryDirectory() as raw_root:
                    store = self.make_store(Path(raw_root))
                    with self.assertRaisesRegex(
                        UserProviderStoreError,
                        "contains configured credential material",
                    ):
                        store.create_connection(**values, api_key=secret)
                    self.assertFalse(store.config_path.exists())

    def test_credential_cannot_collide_with_masked_status_literal(self) -> None:
        for secret in ("configured", "configure", "REDACTED"):
            with self.subTest(secret=secret), tempfile.TemporaryDirectory() as raw_root:
                store = self.make_store(Path(raw_root))
                with self.assertRaisesRegex(
                    UserProviderStoreError,
                    "masked status literal",
                ):
                    self.create_openrouter(store, api_key=secret)
                self.assertFalse(store.config_path.exists())

    def test_redaction_replacement_never_reintroduces_known_secret(self) -> None:
        secret = "REDACTED"
        rendered = redact_provider_text(
            f"provider failure contained {secret}",
            known_secrets=(secret,),
        )
        self.assertNotIn(secret, rendered)

    def test_rotated_credential_cannot_equal_existing_connection_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            connection = self.create_openrouter(store)
            with self.assertRaisesRegex(
                UserProviderStoreError,
                "contains configured credential material",
            ):
                store.save_credential(
                    connection.credential_reference,
                    connection.connection_revision_hash,
                )
            self.assertEqual(
                "missing",
                store.credential_status(connection.credential_reference),
            )

    def test_generic_https_validation_and_unbounded_native_adapter_rejection(self) -> None:
        valid = ProviderConnection(
            connection_id="generic-compatible",
            display_name="Generic Compatible",
            api_style="openai_compatible",
            base_url="https://models.example.test/custom/v1/",
            native_adapter_id=None,
            credential_reference="generic-compatible-key",
            enabled=True,
            created_at="operator-time",
        )
        self.assertEqual("https://models.example.test/custom/v1", valid.base_url)
        for url in (
            "http://models.example.test/v1",
            "https://user:password@models.example.test/v1",
            "https://models.example.test/v1?key=value",
            "https://models.example.test/v1/chat/completions",
            "not-a-url",
        ):
            with self.subTest(url=url):
                with self.assertRaises(UserProviderStoreError):
                    ProviderConnection(
                        connection_id="bad-compatible",
                        display_name="Bad Compatible",
                        api_style="openai_compatible",
                        base_url=url,
                        native_adapter_id=None,
                        credential_reference="bad-compatible-key",
                        enabled=True,
                        created_at="operator-time",
                    )
        for adapter_id in ("gemini_chat", "arbitrary_adapter"):
            with self.subTest(adapter_id=adapter_id), self.assertRaisesRegex(
                UserProviderStoreError,
                "api_style is unsupported",
            ):
                ProviderConnection(
                    connection_id="native-unsupported",
                    display_name="Native adapter requires a separately bounded path",
                    api_style="native_existing_adapter",
                    base_url=None,
                    native_adapter_id=adapter_id,
                    credential_reference="native-unsupported-key",
                    enabled=True,
                    created_at="operator-time",
                )

    def test_disable_is_hot_reloaded_and_changes_revision_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            first_store = self.make_store(root)
            original = self.create_openrouter(first_store)
            second_store = self.make_store(root)
            disabled = second_store.disable_connection(original.connection_id)
            self.assertFalse(disabled.enabled)
            self.assertNotEqual(original.connection_revision_hash, disabled.connection_revision_hash)
            self.assertEqual(disabled, first_store.get_connection(original.connection_id))

    def test_openrouter_preset_is_metadata_only_and_deterministic(self) -> None:
        values = {
            "connection_id": "preset-openrouter",
            "display_name": "Preset OpenRouter",
            "credential_reference": "preset-openrouter-key",
            "created_at": "operator-time",
        }
        first = openrouter_connection_preset(**values)
        second = openrouter_connection_preset(**values)
        self.assertEqual(first, second)
        self.assertEqual(OPENROUTER_BASE_URL, first.base_url)
        self.assertEqual("openai_compatible", first.api_style)

    def test_malformed_or_duplicate_persisted_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            store = self.make_store(root)
            store.state_root.mkdir(parents=True)
            store.config_path.write_text('{"schema_version":', encoding="utf-8")
            with self.assertRaisesRegex(UserProviderStoreError, "malformed"):
                store.list_connections()

            connection = openrouter_connection_preset(
                connection_id="duplicate",
                display_name="Duplicate",
                credential_reference="duplicate-key",
                created_at="operator-time",
            )
            payload = {
                "schema_version": "user-provider-store-1a",
                "connections": [connection.to_dict(), connection.to_dict()],
                "model_profiles": [],
            }
            store.config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(UserProviderStoreError, "duplicate connection IDs"):
                store.list_connections()

    def test_symlink_and_unsafe_secret_permissions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            store = self.make_store(root)
            store.secrets_root.mkdir(parents=True, mode=0o700)
            target = root / "outside-secret"
            target.write_text("outside-value", encoding="utf-8")
            link = store.secrets_root / "linked-key.key"
            link.symlink_to(target)
            with self.assertRaisesRegex(UserProviderStoreError, "non-symlink"):
                store.read_credential("linked-key")

            unsafe = store.secrets_root / "unsafe-key.key"
            unsafe.write_text("unsafe-value", encoding="utf-8")
            unsafe.chmod(0o644)
            with self.assertRaisesRegex(UserProviderStoreError, "permissions are unsafe"):
                store.read_credential("unsafe-key")

    def test_hardlinked_secret_is_never_modified_and_reads_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            project = root / "project"
            project.mkdir()
            store = self.make_store(root)
            store.secrets_root.mkdir(parents=True, mode=0o700)
            repository_target = project / "credential-leak.key"
            repository_target.write_text("original-repository-bytes", encoding="utf-8")
            repository_target.chmod(0o600)
            linked_secret = store.secrets_root / "victim.key"
            os.link(repository_target, linked_secret)

            with self.assertRaisesRegex(UserProviderStoreError, "link count is unsafe"):
                store.read_credential("victim")

            replacement = "replacement-secret-material-000005"
            store.save_credential("victim", replacement)
            self.assertEqual(
                "original-repository-bytes",
                repository_target.read_text(encoding="utf-8"),
            )
            self.assertEqual(replacement, store.read_credential("victim"))
            self.assertEqual(1, linked_secret.stat().st_nlink)

    def test_concurrent_store_instances_cannot_mix_metadata_and_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            first = self.make_store(root)
            second = self.make_store(root)
            barrier = threading.Barrier(2)
            outcomes: list[tuple[str, object]] = []
            outcomes_lock = threading.Lock()
            candidates = (
                (first, "Alpha Connection", "https://alpha.example.test/v1", "alpha-secret-material-000006"),
                (second, "Beta Connection", "https://beta.example.test/v1", "beta-secret-material-000007"),
            )

            def create(candidate: tuple[UserProviderStore, str, str, str]) -> None:
                store, display_name, base_url, secret = candidate
                barrier.wait()
                try:
                    connection = store.create_connection(
                        connection_id="shared-connection",
                        display_name=display_name,
                        api_style="openai_compatible",
                        base_url=base_url,
                        credential_reference="shared-credential",
                        created_at="operator-time",
                        api_key=secret,
                    )
                    result: tuple[str, object] = ("success", connection)
                except UserProviderStoreError as error:
                    result = ("error", error)
                with outcomes_lock:
                    outcomes.append(result)

            threads = [threading.Thread(target=create, args=(item,)) for item in candidates]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(5)
                self.assertFalse(thread.is_alive(), "provider store mutation deadlocked")

            self.assertEqual(1, sum(kind == "success" for kind, _ in outcomes))
            self.assertEqual(1, sum(kind == "error" for kind, _ in outcomes))
            final_store = self.make_store(root)
            connection = final_store.get_connection("shared-connection")
            secret = final_store.read_credential("shared-credential")
            self.assertIn(
                (connection.display_name, connection.base_url, secret),
                {
                    (
                        "Alpha Connection",
                        "https://alpha.example.test/v1",
                        "alpha-secret-material-000006",
                    ),
                    (
                        "Beta Connection",
                        "https://beta.example.test/v1",
                        "beta-secret-material-000007",
                    ),
                },
            )

    def test_secret_storage_inside_or_resolving_into_project_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            project = root / "project"
            project.mkdir()
            with self.assertRaisesRegex(UserProviderStoreError, "outside the project"):
                UserProviderStore(
                    project,
                    state_root=root / "state",
                    secrets_root=project / "secrets",
                )

            outside = root / "outside"
            outside.mkdir()
            link = outside / "linked-into-project"
            link.symlink_to(project, target_is_directory=True)
            with self.assertRaisesRegex(UserProviderStoreError, "outside the project"):
                UserProviderStore(
                    project,
                    state_root=root / "state",
                    secrets_root=link / "secrets",
                )

    def test_default_state_path_uses_runtime_state_convention(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            project = root / "project"
            project.mkdir()
            old = os.environ.get("AOIA_HOME")
            os.environ["AOIA_HOME"] = str(root / "aoia-home")
            try:
                store = UserProviderStore(project, secrets_root=root / "secrets")
            finally:
                if old is None:
                    os.environ.pop("AOIA_HOME", None)
                else:
                    os.environ["AOIA_HOME"] = old
            self.assertTrue(str(store.config_path).startswith(str(root / "aoia-home")))
            self.assertEqual("provider_connections_1a.json", store.config_path.name)


if __name__ == "__main__":
    unittest.main()
