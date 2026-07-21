from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.providers.model_profiles import ModelProfile, ModelProfileError
from runtime.providers.user_connections import UserProviderStore, UserProviderStoreError


class UserModelProfiles1ATests(unittest.TestCase):
    def make_store(self, root: Path) -> UserProviderStore:
        store = UserProviderStore(
            root / "project",
            state_root=root / "state",
            secrets_root=root / "secrets",
        )
        store.create_connection(
            connection_id="one-openrouter",
            display_name="One OpenRouter Connection",
            api_style="openai_compatible",
            base_url="https://openrouter.ai/api/v1",
            native_adapter_id=None,
            credential_reference="one-openrouter-key",
            created_at="operator-time",
        )
        return store

    def test_one_connection_supports_several_dynamic_model_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            definitions = (
                ("gemma-27b", "Gemma 3 27B", "google/gemma-3-27b-it", ("MAIN", "CRITIC")),
                ("qwen-30b", "Qwen 3 30B", "qwen/qwen3-30b-a3b", ("CRITIC", "AUDITOR")),
                (
                    "llama-70b",
                    "Llama 3.3 70B",
                    "meta-llama/llama-3.3-70b-instruct",
                    ("AUDITOR", "SYNTHESIZER"),
                ),
            )
            created = tuple(
                store.create_model_profile(
                    model_profile_id=profile_id,
                    connection_id="one-openrouter",
                    display_name=display_name,
                    remote_model_id=remote_model_id,
                    allowed_roles=roles,
                )
                for profile_id, display_name, remote_model_id, roles in definitions
            )
            self.assertEqual(
                tuple(sorted(created, key=lambda item: item.model_profile_id)),
                store.list_model_profiles("one-openrouter"),
            )
            self.assertEqual(
                {definition[2] for definition in definitions},
                {profile.remote_model_id for profile in store.list_model_profiles()},
            )

    def test_configured_key_cannot_enter_later_model_metadata_or_revision_hash(self) -> None:
        configured_key = "plain-model-key-material-12345"
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            store.save_credential("one-openrouter-key", configured_key)
            with self.assertRaises(UserProviderStoreError) as caught:
                store.create_model_profile(
                    model_profile_id="secret-equivalent-model",
                    connection_id="one-openrouter",
                    display_name=f"Model {configured_key}",
                    remote_model_id="vendor/ordinary-model",
                    allowed_roles=("MAIN",),
                )
            self.assertNotIn(configured_key, str(caught.exception))
            self.assertEqual((), store.list_model_profiles())

    def test_secret_equivalence_is_rejected_before_model_hashing(self) -> None:
        configured_key = "plain-prehash-model-key-material-12345"
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            store.save_credential("one-openrouter-key", configured_key)
            with (
                patch(
                    "runtime.providers.model_profiles.canonical_sha256",
                    side_effect=AssertionError("hashing must not run"),
                ),
                self.assertRaisesRegex(
                    UserProviderStoreError,
                    "contains configured credential material",
                ),
            ):
                store.create_model_profile(
                    model_profile_id="prehash-model",
                    connection_id="one-openrouter",
                    display_name=f"Model {configured_key}",
                    remote_model_id="vendor/ordinary-model",
                    allowed_roles=("MAIN",),
                )
            self.assertEqual((), store.list_model_profiles())

    def test_configured_credential_cannot_equal_generated_model_hash(self) -> None:
        values = {
            "model_profile_id": "hash-collision-model",
            "connection_id": "one-openrouter",
            "display_name": "Hash Collision Model",
            "remote_model_id": "vendor/hash-collision-model",
            "enabled": True,
            "allowed_roles": ("MAIN",),
            "context_limit": None,
            "output_limit": None,
        }
        predicted_hash = ModelProfile(**values).model_revision_hash
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            store.save_credential("one-openrouter-key", predicted_hash)
            with self.assertRaisesRegex(
                UserProviderStoreError,
                "contains configured credential material",
            ):
                store.create_model_profile(**values)
            self.assertEqual((), store.list_model_profiles())
            self.assertNotIn(
                predicted_hash,
                store.config_path.read_text(encoding="utf-8"),
            )

    def test_numeric_limit_cannot_serialize_configured_credential_text(self) -> None:
        numeric_secret = "10000000"
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            store.save_credential("one-openrouter-key", numeric_secret)
            with self.assertRaisesRegex(
                UserProviderStoreError,
                "contains configured credential material",
            ):
                store.create_model_profile(
                    model_profile_id="numeric-secret-model",
                    connection_id="one-openrouter",
                    display_name="Numeric Secret Model",
                    remote_model_id="vendor/numeric-secret-model",
                    allowed_roles=("MAIN",),
                    context_limit=10_000_000,
                    output_limit=10_000_000,
                )
            self.assertEqual((), store.list_model_profiles())

    def test_profile_roles_and_optional_limits_are_canonical_and_hash_bound(self) -> None:
        profile = ModelProfile(
            model_profile_id="bounded-model",
            connection_id="one-openrouter",
            display_name="Bounded Model",
            remote_model_id="vendor/bounded-model",
            enabled=True,
            allowed_roles=("synthesizer", "main", "critic"),
            context_limit=128_000,
            output_limit=4096,
        )
        repeated = ModelProfile.from_dict(profile.to_dict())
        self.assertEqual(("MAIN", "CRITIC", "SYNTHESIZER"), profile.allowed_roles)
        self.assertEqual(profile, repeated)
        self.assertEqual(profile.model_revision_hash, repeated.model_revision_hash)
        self.assertEqual(128_000, profile.context_limit)
        self.assertEqual(4096, profile.output_limit)

    def test_unsupported_duplicate_or_empty_roles_fail_closed(self) -> None:
        for roles in ((), ("MAIN", "MAIN"), ("MAIN", "EXECUTOR")):
            with self.subTest(roles=roles):
                with self.assertRaises(ModelProfileError):
                    ModelProfile(
                        model_profile_id="invalid-roles",
                        connection_id="one-openrouter",
                        display_name="Invalid Roles",
                        remote_model_id="vendor/model",
                        enabled=True,
                        allowed_roles=roles,
                    )

    def test_duplicate_model_profile_id_fails_without_replacing_original(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            original = store.create_model_profile(
                model_profile_id="reviewer",
                connection_id="one-openrouter",
                display_name="Reviewer",
                remote_model_id="vendor/reviewer",
                allowed_roles=("CRITIC",),
            )
            with self.assertRaisesRegex(UserProviderStoreError, "duplicate model_profile_id"):
                store.create_model_profile(
                    model_profile_id="reviewer",
                    connection_id="one-openrouter",
                    display_name="Replacement",
                    remote_model_id="vendor/replacement",
                    allowed_roles=("AUDITOR",),
                )
            self.assertEqual(original, store.get_model_profile("reviewer"))

    def test_unknown_connection_cannot_receive_a_model_profile(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            store = self.make_store(Path(raw_root))
            with self.assertRaisesRegex(UserProviderStoreError, "unknown connection"):
                store.create_model_profile(
                    model_profile_id="orphan",
                    connection_id="missing-connection",
                    display_name="Orphan",
                    remote_model_id="vendor/orphan",
                    allowed_roles=("MAIN",),
                )

    def test_disable_is_hot_reloaded_and_invalidates_model_revision(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            first_store = self.make_store(root)
            original = first_store.create_model_profile(
                model_profile_id="critic",
                connection_id="one-openrouter",
                display_name="Critic",
                remote_model_id="vendor/critic",
                allowed_roles=("CRITIC",),
            )
            second_store = UserProviderStore(
                root / "project",
                state_root=root / "state",
                secrets_root=root / "secrets",
            )
            disabled = second_store.disable_model_profile("critic")
            self.assertFalse(disabled.enabled)
            self.assertNotEqual(original.model_revision_hash, disabled.model_revision_hash)
            self.assertEqual(disabled, first_store.get_model_profile("critic"))

    def test_changed_remote_model_or_role_changes_revision_hash(self) -> None:
        base = dict(
            model_profile_id="mutable-evidence",
            connection_id="one-openrouter",
            display_name="Mutable Evidence",
            enabled=True,
            context_limit=None,
            output_limit=None,
        )
        main = ModelProfile(
            **base,
            remote_model_id="vendor/model-a",
            allowed_roles=("MAIN",),
        )
        changed_model = ModelProfile(
            **base,
            remote_model_id="vendor/model-b",
            allowed_roles=("MAIN",),
        )
        changed_role = ModelProfile(
            **base,
            remote_model_id="vendor/model-a",
            allowed_roles=("CRITIC",),
        )
        self.assertNotEqual(main.model_revision_hash, changed_model.model_revision_hash)
        self.assertNotEqual(main.model_revision_hash, changed_role.model_revision_hash)

    def test_malformed_limit_and_revision_hash_fail_closed(self) -> None:
        for field, value in (("context_limit", 0), ("output_limit", True), ("output_limit", -1)):
            values = dict(
                model_profile_id="invalid-limit",
                connection_id="one-openrouter",
                display_name="Invalid Limit",
                remote_model_id="vendor/model",
                enabled=True,
                allowed_roles=("MAIN",),
                context_limit=None,
                output_limit=None,
            )
            values[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ModelProfileError):
                    ModelProfile(**values)

        valid = ModelProfile(
            model_profile_id="valid-hash",
            connection_id="one-openrouter",
            display_name="Valid Hash",
            remote_model_id="vendor/model",
            enabled=True,
            allowed_roles=("MAIN",),
        ).to_dict()
        valid["model_revision_hash"] = "0" * 64
        with self.assertRaisesRegex(ModelProfileError, "does not match"):
            ModelProfile.from_dict(valid)

    def test_explicit_secret_cannot_enter_model_display_or_remote_id(self) -> None:
        explicit_key = "ghp_" + "A" * 24
        for field in ("display_name", "remote_model_id"):
            values = {
                "model_profile_id": "secret-metadata",
                "connection_id": "one-openrouter",
                "display_name": "Safe Display",
                "remote_model_id": "vendor/safe-model",
                "enabled": True,
                "allowed_roles": ("MAIN",),
            }
            values[field] = explicit_key
            with self.subTest(field=field):
                with self.assertRaisesRegex(ModelProfileError, "secret-like"):
                    ModelProfile(**values)


if __name__ == "__main__":
    unittest.main()
