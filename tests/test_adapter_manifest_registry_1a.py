from __future__ import annotations

import ast
import builtins
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import socket
import subprocess
from unittest import TestCase, main
from unittest.mock import patch

import runtime.execution.adapter_manifest as manifest_module
from runtime.execution.adapter_manifest import (
    AOIA_ADAPTER_MANIFEST_ENTRY_V1,
    AOIA_ADAPTER_MANIFEST_V1,
    AOIA_DATA_SCHEMA_V1,
    AdapterManifestError,
    AdapterManifestFailureCode,
    load_manifest,
    resolve_adapter_metadata,
    verify_adapter_entry,
    verify_manifest,
)
from runtime.execution.authority_contracts import (
    AuthorityBindingMismatch,
    validate_authority_bindings,
)
from runtime.execution.canonical_serialization import (
    FrozenDict,
    canonical_json_bytes,
    domain_separated_sha256,
)
from tests.test_authority_contracts_1a import (
    make_approval,
    make_bound_contracts,
    make_plan,
    make_request,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime/execution/adapter_manifest.py"
REGISTRY_PATH = ROOT / "runtime/execution/adapter_manifest_registry.json"
BASE_SHA = "3dcd8f326053ed15706817413514371e040bb877"
H1 = "1" * 64
H2 = "2" * 64


def empty_data_schema() -> dict[str, object]:
    return {
        "schema_version": AOIA_DATA_SCHEMA_V1,
        "root": {
            "type": "object",
            "properties": {},
            "required": [],
            "additional_properties": False,
            "maximum_properties": 0,
        },
    }


def policy_reference(policy_id: str) -> dict[str, object]:
    return {
        "policy_id": policy_id,
        "policy_version": "1",
        "policy_hash": H1,
    }


def bind_entry_hash(value: dict[str, object]) -> dict[str, object]:
    result = deepcopy(value)
    material = {key: item for key, item in result.items() if key != "adapter_entry_hash"}
    result["adapter_entry_hash"] = domain_separated_sha256(
        AOIA_ADAPTER_MANIFEST_ENTRY_V1, material
    )
    return result


def entry_payload(
    *,
    adapter_id: str = "internal.inspect",
    adapter_version: str = "1",
    **changes: object,
) -> dict[str, object]:
    value: dict[str, object] = {
        "adapter_id": adapter_id,
        "adapter_version": adapter_version,
        "adapter_type": "internal",
        "implementation_reference": f"aoia_adapter:{adapter_id}:{adapter_version}",
        "operation": "inspect",
        "protocol": "none",
        "allowed_resource_types": [],
        "argument_schema": empty_data_schema(),
        "output_schema": empty_data_schema(),
        "allowed_destinations": [],
        "allowed_filesystem_paths": [],
        "network_required": False,
        "write_capability": False,
        "required_permissions": [],
        "required_credentials": [],
        "environment_allowlist": [],
        "timeout_seconds": 30,
        "maximum_input_bytes": 4096,
        "maximum_output_bytes": 4096,
        "maximum_results": 1,
        "retry_policy": {
            "mode": "none",
            "maximum_attempts": 1,
            "backoff_seconds": 0,
        },
        "failure_policy": {
            "mode": "fail-closed",
            "on_timeout": "deny",
            "on_error": "deny",
            "allow_partial_results": False,
        },
        "evidence_policy": policy_reference("evidence.default"),
        "redaction_policy": policy_reference("redaction.default"),
        "audit_policy": policy_reference("audit.default"),
        "sandbox_policy": {
            **policy_reference("sandbox.default"),
            "required": True,
        },
        "provenance": {
            "repository_id": "luciferprosun/AOIA-Core",
            "source_commit": BASE_SHA,
        },
        "implementation_sha256": "a" * 64,
        "adapter_entry_hash": "0" * 64,
        "enabled": False,
    }
    value.update(changes)
    return bind_entry_hash(value)


def network_entry_payload(**changes: object) -> dict[str, object]:
    value = entry_payload(
        adapter_id="provider.example",
        adapter_type="provider",
        protocol="https",
        allowed_resource_types=["network-destination", "provider-request"],
        allowed_destinations=[
            {"scheme": "https", "host": "api.example.com", "port": 443}
        ],
        network_required=True,
        required_permissions=["network.connect", "provider.invoke"],
    )
    value.update(changes)
    return bind_entry_hash(value)


def filesystem_entry_payload(**changes: object) -> dict[str, object]:
    value = entry_payload(
        adapter_id="filesystem.inspect",
        adapter_type="filesystem",
        protocol="filesystem",
        allowed_resource_types=["file"],
        allowed_filesystem_paths=[
            {
                "root_id": "repository",
                "relative_path": "data/example.json",
                "access": "read-file",
                "symlink_policy": "forbid",
            }
        ],
        required_permissions=["filesystem.read"],
    )
    value.update(changes)
    return bind_entry_hash(value)


def bind_manifest_hash(
    entries: list[dict[str, object]],
    *,
    schema_version: int = 1,
    manifest_version: str = "1",
    preserve_input_order: bool = True,
) -> dict[str, object]:
    canonical_entries = sorted(
        deepcopy(entries),
        key=lambda item: (item["adapter_id"], item["adapter_version"]),
    )
    value: dict[str, object] = {
        "schema_version": schema_version,
        "manifest_version": manifest_version,
        "adapters": deepcopy(entries) if preserve_input_order else canonical_entries,
        "manifest_hash": domain_separated_sha256(
            AOIA_ADAPTER_MANIFEST_V1,
            {
                "schema_version": schema_version,
                "manifest_version": manifest_version,
                "adapters": canonical_entries,
            },
        ),
    }
    return value


def assert_code(
    case: TestCase,
    expected: AdapterManifestFailureCode,
    operation,
) -> AdapterManifestError:
    with case.assertRaises(AdapterManifestError) as raised:
        operation()
    case.assertEqual(expected, raised.exception.code)
    return raised.exception


class AdapterManifestRegistryCoreTests(TestCase):
    def test_valid_empty_manifest_is_accepted(self):
        loaded = load_manifest()
        self.assertEqual(1, loaded.schema_version)
        self.assertEqual("1", loaded.manifest_version)
        self.assertEqual((), loaded.adapters)

    def test_canonical_manifest_bytes_are_stable(self):
        loaded = load_manifest()
        self.assertEqual(
            canonical_json_bytes(loaded.to_dict()),
            canonical_json_bytes(loaded.to_dict()),
        )

    def test_json_key_order_does_not_change_hash(self):
        original = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        reordered = dict(reversed(tuple(original.items())))
        self.assertEqual(verify_manifest(original), verify_manifest(reordered))

    def test_adapter_order_is_canonicalized(self):
        second = entry_payload(adapter_id="internal.zulu")
        first = entry_payload(adapter_id="internal.alpha")
        verified = verify_manifest(bind_manifest_hash([second, first]))
        self.assertEqual(
            ("internal.alpha", "internal.zulu"),
            tuple(entry.adapter_id for entry in verified.adapters),
        )

    def test_duplicate_adapter_id_version_is_rejected(self):
        entry = entry_payload()
        value = bind_manifest_hash([entry, deepcopy(entry)])
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENTRY_DUPLICATE,
            lambda: verify_manifest(value),
        )

    def test_unknown_top_level_field_is_rejected(self):
        value = bind_manifest_hash([])
        value["description"] = "not part of the authority contract"
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            lambda: verify_manifest(value),
        )

    def test_unknown_adapter_field_is_rejected(self):
        value = entry_payload()
        value["description"] = "unknown"
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID,
            lambda: verify_adapter_entry(value),
        )

    def test_stale_manifest_hash_is_rejected(self):
        value = bind_manifest_hash([])
        value["manifest_hash"] = "0" * 64
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_HASH_MISMATCH,
            lambda: verify_manifest(value),
        )

    def test_stale_entry_hash_is_rejected(self):
        value = entry_payload()
        value["operation"] = "changed"
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENTRY_HASH_MISMATCH,
            lambda: verify_adapter_entry(value),
        )

    def test_malformed_manifest_hash_is_rejected(self):
        value = bind_manifest_hash([])
        value["manifest_hash"] = "ABC"
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            lambda: verify_manifest(value),
        )

    def test_malformed_entry_hash_is_rejected(self):
        value = entry_payload()
        value["adapter_entry_hash"] = "ABC"
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID,
            lambda: verify_adapter_entry(value),
        )

    def test_duplicate_json_object_key_is_rejected(self):
        raw = (
            b'{"schema_version":1,"schema_version":1,"manifest_version":"1",'
            b'"adapters":[],"manifest_hash":"' + b"0" * 64 + b'"}'
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            lambda: manifest_module._parse_manifest_bytes(raw),
        )

    def test_missing_enabled_is_rejected(self):
        value = entry_payload()
        del value["enabled"]
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID,
            lambda: verify_adapter_entry(value),
        )

    def test_initial_enabled_true_is_rejected(self):
        value = entry_payload(enabled=True)
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_INITIAL_STATE_VIOLATION,
            lambda: verify_adapter_entry(value),
        )

    def test_unknown_adapter_is_denied(self):
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_UNKNOWN,
            lambda: resolve_adapter_metadata("internal.missing", "1"),
        )

    def test_unknown_adapter_version_is_denied(self):
        verified = verify_manifest(bind_manifest_hash([entry_payload()]))
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_VERSION_UNKNOWN,
            lambda: manifest_module._find_entry(
                verified, "internal.inspect", "2"
            ),
        )

    def test_disabled_adapter_is_denied(self):
        verified = verify_manifest(bind_manifest_hash([entry_payload()]))
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_DISABLED,
            lambda: manifest_module._resolve_adapter_metadata(
                verified, "internal.inspect", "1", {}
            ),
        )

    def test_disabled_precedes_implementation_resolution_in_public_lookup(self):
        verified = verify_manifest(bind_manifest_hash([entry_payload()]))
        with (
            patch.object(manifest_module, "load_manifest", return_value=verified),
            patch.object(
                manifest_module,
                "_verify_implementation_identity",
                side_effect=AssertionError("implementation resolution"),
            ) as identity_check,
        ):
            assert_code(
                self,
                AdapterManifestFailureCode.ADAPTER_DISABLED,
                lambda: resolve_adapter_metadata("internal.inspect", "1"),
            )
            self.assertFalse(
                manifest_module.is_adapter_enabled("internal.inspect", "1")
            )
        identity_check.assert_not_called()


class DangerousAuthorityFieldTests(TestCase):
    def _assert_extra_field(
        self,
        field: str,
        value: object,
        code: AdapterManifestFailureCode,
    ) -> None:
        entry = entry_payload()
        entry[field] = value
        assert_code(self, code, lambda: verify_adapter_entry(entry))

    def test_arbitrary_command_field_is_rejected(self):
        self._assert_extra_field(
            "command",
            "rm -rf target",
            AdapterManifestFailureCode.ADAPTER_ARBITRARY_COMMAND_FORBIDDEN,
        )

    def test_arbitrary_executable_field_is_rejected(self):
        self._assert_extra_field(
            "executable",
            "/bin/sh",
            AdapterManifestFailureCode.ADAPTER_ARBITRARY_EXECUTABLE_FORBIDDEN,
        )

    def test_arbitrary_url_is_rejected(self):
        self._assert_extra_field(
            "url",
            "https://unapproved.example",
            AdapterManifestFailureCode.ADAPTER_ARBITRARY_URL_FORBIDDEN,
        )

    def test_arbitrary_import_path_is_rejected(self):
        entry = entry_payload(implementation_reference="os.system")
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_DYNAMIC_IMPORT_FORBIDDEN,
            lambda: verify_adapter_entry(entry),
        )

    def test_dynamic_callable_is_rejected(self):
        self._assert_extra_field(
            "callable",
            "caller_supplied",
            AdapterManifestFailureCode.ADAPTER_DYNAMIC_CALLABLE_FORBIDDEN,
        )

    def test_shell_true_is_rejected(self):
        self._assert_extra_field(
            "shell",
            True,
            AdapterManifestFailureCode.ADAPTER_SHELL_MODE_FORBIDDEN,
        )

    def test_reserved_argument_authority_names_are_rejected(self):
        expectations = {
            "command": AdapterManifestFailureCode.ADAPTER_ARBITRARY_COMMAND_FORBIDDEN,
            "argv": AdapterManifestFailureCode.ADAPTER_ARBITRARY_EXECUTABLE_FORBIDDEN,
            "url": AdapterManifestFailureCode.ADAPTER_ARBITRARY_URL_FORBIDDEN,
            "module": AdapterManifestFailureCode.ADAPTER_DYNAMIC_IMPORT_FORBIDDEN,
            "callable": AdapterManifestFailureCode.ADAPTER_DYNAMIC_CALLABLE_FORBIDDEN,
            "shell": AdapterManifestFailureCode.ADAPTER_SHELL_MODE_FORBIDDEN,
            "environment": AdapterManifestFailureCode.ADAPTER_ENVIRONMENT_POLICY_INVALID,
        }
        for property_name, expected_code in expectations.items():
            with self.subTest(property_name=property_name):
                schema = empty_data_schema()
                schema["root"]["properties"] = {
                    property_name: {"type": "boolean"}
                }
                schema["root"]["maximum_properties"] = 1
                entry = entry_payload(argument_schema=schema)
                assert_code(
                    self,
                    expected_code,
                    lambda entry=entry: verify_adapter_entry(entry),
                )


class NetworkEnvironmentFilesystemTests(TestCase):
    def test_wildcard_destination_is_rejected(self):
        entry = network_entry_payload(
            allowed_destinations=[
                {"scheme": "https", "host": "*.example.com", "port": 443}
            ]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_destination_path_query_and_fragment_are_rejected(self):
        for host in ("api.example.com/path", "api.example.com?x=1", "api.example.com#x"):
            with self.subTest(host=host):
                entry = network_entry_payload(
                    allowed_destinations=[
                        {"scheme": "https", "host": host, "port": 443}
                    ]
                )
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )

    def test_wildcard_environment_is_rejected(self):
        entry = entry_payload(environment_allowlist=["*"])
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENVIRONMENT_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_unrestricted_environment_inheritance_is_rejected(self):
        entry = entry_payload(environment_allowlist=["inherit-all"])
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENVIRONMENT_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_sensitive_environment_names_are_rejected(self):
        for name in ("PATH", "PYTHONPATH", "AWS_SECRET_ACCESS_KEY", "API_TOKEN"):
            with self.subTest(name=name):
                entry = entry_payload(environment_allowlist=[name])
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_ENVIRONMENT_POLICY_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )

    def test_duplicate_destinations_are_rejected(self):
        destination = {"scheme": "https", "host": "api.example.com", "port": 443}
        entry = network_entry_payload(
            allowed_destinations=[deepcopy(destination), deepcopy(destination)]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_malformed_protocol_is_rejected(self):
        entry = entry_payload(protocol="smtp")
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_malformed_filesystem_rule_is_rejected(self):
        entry = filesystem_entry_payload(
            allowed_filesystem_paths=[
                {
                    "root_id": "repository",
                    "relative_path": "data/example.json",
                    "access": "read-file",
                }
            ]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_FILESYSTEM_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_filesystem_traversal_is_rejected(self):
        entry = filesystem_entry_payload(
            allowed_filesystem_paths=[
                {
                    "root_id": "repository",
                    "relative_path": "data/../secret",
                    "access": "read-file",
                    "symlink_policy": "forbid",
                }
            ]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_FILESYSTEM_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_absolute_and_home_paths_are_rejected(self):
        for relative_path in ("/etc/passwd", "~/secret"):
            with self.subTest(relative_path=relative_path):
                entry = filesystem_entry_payload(
                    allowed_filesystem_paths=[
                        {
                            "root_id": "repository",
                            "relative_path": relative_path,
                            "access": "read-file",
                            "symlink_policy": "forbid",
                        }
                    ]
                )
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_FILESYSTEM_POLICY_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )


class LimitsFailureAndSecretTests(TestCase):
    def test_negative_limits_are_rejected(self):
        entry = entry_payload(maximum_results=-1)
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_LIMIT_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_zero_boolean_and_oversize_timeout_are_rejected(self):
        for value in (0, True, 3_601):
            with self.subTest(timeout=value):
                entry = entry_payload(timeout_seconds=value)
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_LIMIT_POLICY_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )

    def test_malformed_retry_policy_is_rejected(self):
        entry = entry_payload(
            retry_policy={
                "mode": "retry",
                "maximum_attempts": 2,
                "backoff_seconds": 1,
            }
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_RETRY_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_non_fail_closed_failure_policy_is_rejected(self):
        entry = entry_payload(
            failure_policy={
                "mode": "fallback",
                "on_timeout": "continue",
                "on_error": "continue",
                "allow_partial_results": True,
            }
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_FAILURE_POLICY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_secret_api_key_value_is_rejected(self):
        entry = entry_payload(
            required_credentials=[
                {
                    "credential_type": "api-key",
                    "credential_reference": "credential:provider.primary",
                    "api_key": "sk-proj-abcdefghijklmnop",
                }
            ]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_SECRET_MATERIAL_FORBIDDEN,
            lambda: verify_adapter_entry(entry),
        )

    def test_bearer_token_value_is_rejected(self):
        entry = entry_payload(
            required_credentials=[
                {
                    "credential_type": "oauth2-token",
                    "credential_reference": "Bearer abcdefghijklmnop",
                }
            ]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_SECRET_MATERIAL_FORBIDDEN,
            lambda: verify_adapter_entry(entry),
        )

    def test_private_key_material_is_rejected(self):
        entry = entry_payload(
            required_credentials=[
                {
                    "credential_type": "ssh-key",
                    "credential_reference": (
                        "-----BEGIN OPENSSH PRIVATE KEY----- secret material"
                    ),
                }
            ]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_SECRET_MATERIAL_FORBIDDEN,
            lambda: verify_adapter_entry(entry),
        )

    def test_password_value_is_rejected(self):
        entry = entry_payload(
            required_credentials=[
                {
                    "credential_type": "username-password",
                    "credential_reference": "credential:service.primary",
                    "password": "correct-horse-battery-staple",
                }
            ]
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_SECRET_MATERIAL_FORBIDDEN,
            lambda: verify_adapter_entry(entry),
        )

    def test_opaque_credential_reference_is_accepted(self):
        entry = entry_payload(
            required_credentials=[
                {
                    "credential_type": "api-key",
                    "credential_reference": "credential:provider.openai.primary",
                }
            ]
        )
        verified = verify_adapter_entry(entry)
        self.assertEqual(
            "credential:provider.openai.primary",
            verified.required_credentials[0]["credential_reference"],
        )


class ImplementationIntegrityAndInertnessTests(TestCase):
    def test_malformed_implementation_hash_is_rejected(self):
        entry = entry_payload(implementation_sha256="not-a-digest")
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ENTRY_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_implementation_hash_mismatch_is_denied(self):
        entry = verify_adapter_entry(entry_payload())
        identity = manifest_module._ImplementationIdentity(
            implementation_reference=entry.implementation_reference,
            implementation_sha256="b" * 64,
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_HASH_MISMATCH,
            lambda: manifest_module._verify_implementation_identity(
                entry, {(entry.adapter_id, entry.adapter_version): identity}
            ),
        )

    def test_unknown_implementation_is_denied(self):
        entry = verify_adapter_entry(entry_payload())
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_UNKNOWN,
            lambda: manifest_module._verify_implementation_identity(entry, {}),
        )

    def test_unmanifested_implementation_is_denied(self):
        verified = verify_manifest(bind_manifest_hash([]))
        identity = manifest_module._ImplementationIdentity(
            implementation_reference="aoia_adapter:internal.orphan:1",
            implementation_sha256="b" * 64,
        )
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_IMPLEMENTATION_UNMANIFESTED,
            lambda: manifest_module._verify_implementation_registry_closure(
                verified, {("internal.orphan", "1"): identity}
            ),
        )

    def test_manifest_load_cannot_import_adapter_modules(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if "adapter" in name and name != "runtime.execution.adapter_manifest":
                raise AssertionError(f"unexpected adapter import: {name}")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            self.assertEqual((), load_manifest().adapters)

    def test_manifest_load_performs_no_network(self):
        with (
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(
                socket, "create_connection", side_effect=AssertionError("network")
            ),
        ):
            self.assertEqual((), load_manifest().adapters)

    def test_manifest_load_performs_no_subprocess(self):
        with (
            patch.object(subprocess, "run", side_effect=AssertionError("process")),
            patch.object(subprocess, "Popen", side_effect=AssertionError("process")),
        ):
            self.assertEqual((), load_manifest().adapters)

    def test_manifest_load_performs_no_filesystem_mutation(self):
        before = (REGISTRY_PATH.read_bytes(), REGISTRY_PATH.stat().st_mtime_ns)
        load_manifest()
        after = (REGISTRY_PATH.read_bytes(), REGISTRY_PATH.stat().st_mtime_ns)
        self.assertEqual(before, after)


class SemanticHashBindingTests(TestCase):
    def _assert_entry_and_manifest_hash_change(
        self,
        original: dict[str, object],
        changed: dict[str, object],
    ) -> None:
        self.assertNotEqual(
            original["adapter_entry_hash"], changed["adapter_entry_hash"]
        )
        self.assertNotEqual(
            bind_manifest_hash([original])["manifest_hash"],
            bind_manifest_hash([changed])["manifest_hash"],
        )

    def test_enabled_change_changes_entry_and_manifest_hashes(self):
        original = entry_payload()
        changed = entry_payload(enabled=True)
        self._assert_entry_and_manifest_hash_change(original, changed)

    def test_destination_change_changes_entry_and_manifest_hashes(self):
        original = network_entry_payload()
        changed = network_entry_payload(
            allowed_destinations=[
                {"scheme": "https", "host": "api2.example.com", "port": 443}
            ]
        )
        self._assert_entry_and_manifest_hash_change(original, changed)

    def test_permissions_change_changes_entry_and_manifest_hashes(self):
        original = entry_payload()
        changed = entry_payload(required_permissions=["filesystem.read"])
        self._assert_entry_and_manifest_hash_change(original, changed)

    def test_environment_allowlist_change_changes_hashes(self):
        original = entry_payload()
        changed = entry_payload(environment_allowlist=["LANG"])
        self._assert_entry_and_manifest_hash_change(original, changed)

    def test_implementation_hash_change_changes_hashes(self):
        original = entry_payload()
        changed = entry_payload(implementation_sha256="b" * 64)
        self._assert_entry_and_manifest_hash_change(original, changed)


class AuthorityCompatibilityTests(TestCase):
    def test_visible_plan_manifest_binding_is_compatible(self):
        identity = load_manifest().identity
        plan = make_plan(
            adapter_manifest_version=identity.manifest_version,
            adapter_manifest_hash=identity.manifest_hash,
        )
        self.assertEqual(identity.manifest_hash, plan.adapter_manifest_hash)
        self.assertTrue(plan.verify_hash())

    def test_human_approval_manifest_binding_is_compatible(self):
        identity = load_manifest().identity
        approval = make_approval(
            adapter_manifest_version=identity.manifest_version,
            adapter_manifest_hash=identity.manifest_hash,
        )
        self.assertEqual(identity.manifest_hash, approval.adapter_manifest_hash)
        self.assertTrue(approval.verify_hash())

    def test_approved_execution_request_binding_is_compatible(self):
        identity = load_manifest().identity
        request = make_request(
            adapter_manifest_version=identity.manifest_version,
            adapter_manifest_hash=identity.manifest_hash,
        )
        self.assertEqual(identity.manifest_hash, request.adapter_manifest_hash)
        self.assertTrue(request.verify_hash())

    def test_old_approval_fails_after_semantic_manifest_change(self):
        case, scope, plan, approval, request = make_bound_contracts()
        changed_plan = make_plan(
            case_id=case.case_id,
            scope_id=scope.scope_id,
            policy_version=case.policy_version,
            adapter_manifest_version=plan.adapter_manifest_version,
            adapter_manifest_hash="9" * 64,
        )
        self.assertNotEqual(plan.plan_hash, changed_plan.plan_hash)
        with self.assertRaises(AuthorityBindingMismatch):
            validate_authority_bindings(
                case=case,
                scope=scope,
                plan=changed_plan,
                approval=approval,
                request=request,
            )


class NoFallbackAndApiBoundaryTests(TestCase):
    def test_resolver_cannot_fallback_to_tool_registry(self):
        import runtime.schemas.tool_registry as tool_registry

        with patch.object(
            tool_registry, "lookup_tool", side_effect=AssertionError("legacy fallback")
        ) as lookup:
            assert_code(
                self,
                AdapterManifestFailureCode.ADAPTER_UNKNOWN,
                lambda: resolve_adapter_metadata("legacy.tool", "1"),
            )
        lookup.assert_not_called()

    def test_resolver_cannot_fallback_to_provider_registry(self):
        import runtime.provider_registry as provider_registry

        with patch.object(
            provider_registry,
            "get_provider_profile",
            side_effect=AssertionError("legacy fallback"),
        ) as lookup:
            assert_code(
                self,
                AdapterManifestFailureCode.ADAPTER_UNKNOWN,
                lambda: resolve_adapter_metadata("provider.openai", "1"),
            )
        lookup.assert_not_called()

    def test_resolver_cannot_scan_for_implementations(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue({"importlib", "pkgutil"}.isdisjoint(imports))
        self.assertTrue({"rglob", "glob", "iterdir"}.isdisjoint(calls))

    def test_r3_2_exports_no_execution_api(self):
        forbidden = {
            "execute",
            "invoke",
            "run",
            "dispatch",
            "call",
            "write",
            "call_provider",
            "run_subprocess",
        }
        self.assertTrue(forbidden.isdisjoint(manifest_module.__all__))
        for name in manifest_module.__all__:
            self.assertNotIn(name.casefold(), forbidden)

    def test_all_initial_production_entries_are_disabled(self):
        loaded = load_manifest()
        self.assertEqual(0, len(loaded.adapters))
        self.assertTrue(all(not entry.enabled for entry in loaded.adapters))

    def test_verified_values_are_deeply_immutable(self):
        entry = verify_adapter_entry(entry_payload())
        self.assertIsInstance(entry.argument_schema, FrozenDict)
        with self.assertRaises(FrozenInstanceError):
            entry.enabled = True
        with self.assertRaises(TypeError):
            entry.argument_schema["root"] = {}


class CorruptionVersioningAndSchemaTests(TestCase):
    def test_manifest_corruption_fails_closed(self):
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            lambda: manifest_module._parse_manifest_bytes(b"{"),
        )

    def test_excessive_json_nesting_fails_with_typed_denial(self):
        raw = (b"[" * 1_100) + b"0" + (b"]" * 1_100)
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_INVALID,
            lambda: manifest_module._parse_manifest_bytes(raw),
        )

    def test_unsupported_schema_version_fails_closed(self):
        value = bind_manifest_hash([], schema_version=2)
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_SCHEMA_UNSUPPORTED,
            lambda: verify_manifest(value),
        )

    def test_unsupported_manifest_version_fails_closed(self):
        value = bind_manifest_hash([], manifest_version="2")
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_VERSION_UNSUPPORTED,
            lambda: verify_manifest(value),
        )

    def test_missing_manifest_has_no_empty_fallback(self):
        missing = Path("/tmp/aoia-r3-2-definitely-missing/manifest.json")
        with patch.object(manifest_module, "_MANIFEST_PATH", missing):
            assert_code(
                self,
                AdapterManifestFailureCode.ADAPTER_MANIFEST_MISSING,
                load_manifest,
            )

    def test_argument_schema_ref_and_custom_keywords_are_rejected(self):
        for keyword in ("$ref", "pattern", "oneOf"):
            with self.subTest(keyword=keyword):
                schema = empty_data_schema()
                schema["root"][keyword] = "forbidden"
                entry = entry_payload(argument_schema=schema)
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_ARGUMENT_SCHEMA_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )

    def test_output_schema_ref_and_custom_keywords_are_rejected(self):
        for keyword in ("$ref", "format", "anyOf"):
            with self.subTest(keyword=keyword):
                schema = empty_data_schema()
                schema["root"][keyword] = "forbidden"
                entry = entry_payload(output_schema=schema)
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_OUTPUT_SCHEMA_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )

    def test_data_schema_root_must_be_a_bounded_object(self):
        schema = {
            "schema_version": AOIA_DATA_SCHEMA_V1,
            "root": {
                "type": "string",
                "semantic_type": "text",
                "minimum_bytes": 0,
                "maximum_bytes": 16,
                "allowed_values": [],
            },
        }
        entry = entry_payload(argument_schema=schema)
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_ARGUMENT_SCHEMA_INVALID,
            lambda: verify_adapter_entry(entry),
        )

    def test_data_schema_depth_and_node_limits_are_enforced(self):
        leaf: dict[str, object] = {"type": "boolean"}
        for _index in range(8):
            leaf = {
                "type": "array",
                "items": leaf,
                "minimum_items": 0,
                "maximum_items": 1,
                "unique_items": False,
            }
        deep_schema = empty_data_schema()
        deep_schema["root"]["properties"] = {"nested": leaf}
        deep_schema["root"]["maximum_properties"] = 1

        wide_schema = empty_data_schema()
        wide_schema["root"]["properties"] = {
            f"field-{index:03d}": {"type": "boolean"}
            for index in range(256)
        }
        wide_schema["root"]["maximum_properties"] = 256

        for schema in (deep_schema, wide_schema):
            with self.subTest(kind="deep" if schema is deep_schema else "wide"):
                entry = entry_payload(argument_schema=schema)
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_ARGUMENT_SCHEMA_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )

    def test_cross_field_network_policy_is_enforced(self):
        cases = (
            network_entry_payload(network_required=False),
            network_entry_payload(required_permissions=["provider.invoke"]),
            entry_payload(
                allowed_destinations=[
                    {"scheme": "https", "host": "api.example.com", "port": 443}
                ]
            ),
        )
        for entry in cases:
            with self.subTest(entry=entry["adapter_id"]):
                assert_code(
                    self,
                    AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
                    lambda entry=entry: verify_adapter_entry(entry),
                )

    def test_manifest_byte_limit_is_enforced(self):
        oversized = b" " * (manifest_module._MAX_MANIFEST_BYTES + 1)
        assert_code(
            self,
            AdapterManifestFailureCode.ADAPTER_MANIFEST_TOO_LARGE,
            lambda: manifest_module._parse_manifest_bytes(oversized),
        )

    def test_oversized_policy_arrays_fail_with_typed_denials(self):
        destination_entry = network_entry_payload()
        destination_entry["allowed_destinations"] = [
            {"scheme": "https", "host": "api.example.com", "port": 443}
        ] * (manifest_module._MAX_POLICY_ITEMS + 1)

        credential_entry = entry_payload()
        credential_entry["required_credentials"] = [
            {
                "credential_type": "api-key",
                "credential_reference": "credential:provider.primary",
            }
        ] * (manifest_module._MAX_POLICY_ITEMS + 1)

        cases = (
            (
                destination_entry,
                AdapterManifestFailureCode.ADAPTER_DESTINATION_POLICY_INVALID,
            ),
            (
                credential_entry,
                AdapterManifestFailureCode.ADAPTER_CREDENTIAL_POLICY_INVALID,
            ),
        )
        for entry, expected in cases:
            with self.subTest(expected=expected.value):
                assert_code(
                    self,
                    expected,
                    lambda entry=entry: verify_adapter_entry(entry),
                )


if __name__ == "__main__":
    main()
