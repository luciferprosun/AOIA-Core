from __future__ import annotations

import ast
import json
import os
import socket
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.integration_boundaries.nvidia_inert_foundation import (
    DEFERRED_NVIDIA_CAPABILITY_IDS,
    EXTERNAL_ADVISORY_NON_AUTHORITY,
    NVIDIA_DISABLED_ADAPTER_IDENTITY,
    NVIDIA_PROVIDER_IDENTITY,
    NVIDIA_REASON_DISABLED_BY_DEFAULT,
    NVIDIA_REASON_INVALID_CONFIGURATION,
    NON_AUTHORITY,
    InertNvidiaAdapter,
    NvidiaFoundationStatus,
    NvidiaIntegrationConfig,
    create_nvidia_advisory_request,
    get_nvidia_capability_declaration,
    list_active_nvidia_capabilities,
    list_deferred_nvidia_capabilities,
    resolve_nvidia_integration_config,
)
from runtime.provider_critic.records import ProviderCritiqueRecord
from runtime.providers.registry import list_runtime_providers
from runtime.providers.selector import list_available_providers
from runtime.safety.workspace_guard import (
    WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL,
    validate_workspace_target_path,
)
from runtime.safety.write_kill_switch import (
    WRITES_DISABLED,
    WRITE_KILL_SWITCH_BLOCKED_DISABLED,
    evaluate_write_kill_switch_value,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = (
    REPO_ROOT
    / "runtime"
    / "integration_boundaries"
    / "nvidia_inert_foundation.py"
)


class NvidiaInertIntegrationFoundation1ATests(unittest.TestCase):
    def test_default_foundation_is_disabled_and_has_zero_active_capabilities(self):
        adapter = InertNvidiaAdapter()

        self.assertFalse(adapter.configuration.enabled)
        self.assertEqual(
            NvidiaFoundationStatus.DISABLED.value, adapter.availability.status
        )
        self.assertEqual(
            NVIDIA_REASON_DISABLED_BY_DEFAULT, adapter.availability.reason_code
        )
        self.assertFalse(adapter.availability.config_present)
        self.assertEqual((), adapter.availability.active_capability_ids)
        self.assertEqual((), list_active_nvidia_capabilities())

    def test_explicit_disabled_configuration_remains_inert(self):
        resolution = resolve_nvidia_integration_config(
            {
                "enabled": False,
                "adapter_identity": NVIDIA_DISABLED_ADAPTER_IDENTITY,
                "requested_capability_ids": (),
            }
        )

        self.assertEqual(NvidiaFoundationStatus.DISABLED.value, resolution.availability.status)
        self.assertTrue(resolution.availability.config_present)
        self.assertIsNone(resolution.failure)
        self.assertFalse(resolution.config.enabled)

    def test_activation_and_capability_requests_fail_closed(self):
        cases = (
            {"enabled": True},
            {"requested_capability_ids": ("nvidia.advisory.analysis",)},
            {"adapter_identity": "nvidia-live-adapter"},
        )

        for raw_config in cases:
            with self.subTest(raw_config=raw_config):
                resolution = resolve_nvidia_integration_config(raw_config)

                self.assertEqual(
                    NvidiaFoundationStatus.BLOCKED_INVALID_CONFIGURATION.value,
                    resolution.availability.status,
                )
                self.assertEqual(
                    NVIDIA_REASON_INVALID_CONFIGURATION,
                    resolution.failure.reason_code,
                )
                self.assertFalse(resolution.config.enabled)
                self.assertEqual((), resolution.config.requested_capability_ids)

    def test_unknown_or_malformed_configuration_is_blocked_without_reflection(self):
        sensitive_marker = "do-not-reflect-material"
        cases = (
            {"key_reference": sensitive_marker},
            "enabled=true",
            {"enabled": "false"},
            {"requested_capability_ids": [object()]},
        )

        for raw_config in cases:
            with self.subTest(kind=type(raw_config).__name__):
                resolution = resolve_nvidia_integration_config(raw_config)
                serialized = json.dumps(resolution.to_dict(), sort_keys=True)

                self.assertEqual(
                    NvidiaFoundationStatus.BLOCKED_INVALID_CONFIGURATION.value,
                    resolution.availability.status,
                )
                self.assertNotIn(sensitive_marker, serialized)
                self.assertNotIn(sensitive_marker, repr(resolution))

    def test_direct_configuration_contract_rejects_activation(self):
        cases = (
            {"enabled": True},
            {"requested_capability_ids": ("nvidia.advisory.analysis",)},
            {"schema_version": "UNKNOWN"},
        )

        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                NvidiaIntegrationConfig(**values)

    def test_capability_declaration_is_immutable_and_non_authoritative(self):
        declaration = get_nvidia_capability_declaration()
        forced = replace(
            declaration,
            active_capability_ids=("nvidia.advisory.analysis",),
            network_access=True,
            gpu_access=True,
            process_access=True,
            filesystem_write_access=True,
            tool_access=True,
            approval_authority=True,
            ledger_mutation_access=True,
            memory_patch_access=True,
            automatic_selection=True,
        )

        self.assertEqual((), forced.active_capability_ids)
        for field in (
            "network_access",
            "gpu_access",
            "process_access",
            "filesystem_write_access",
            "tool_access",
            "approval_authority",
            "ledger_mutation_access",
            "memory_patch_access",
            "automatic_selection",
        ):
            self.assertIs(getattr(forced, field), False)

    def test_deferred_capabilities_are_structural_only(self):
        declaration = get_nvidia_capability_declaration()

        self.assertEqual(DEFERRED_NVIDIA_CAPABILITY_IDS, list_deferred_nvidia_capabilities())
        self.assertEqual(DEFERRED_NVIDIA_CAPABILITY_IDS, declaration.deferred_capability_ids)
        self.assertEqual((), declaration.active_capability_ids)

    def test_request_contract_is_deterministic_and_hash_only(self):
        first = self.request()
        second = self.request()

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(("a" * 64,), first.evidence_hashes)

    def test_request_contract_rejects_unknown_capability_and_bad_evidence(self):
        cases = (
            {"capability_identity": "nvidia.execute"},
            {"evidence_hashes": ("not-a-hash",)},
            {"correlation_id": "contains spaces"},
            {"created_at_tick": -1},
        )

        for values in cases:
            arguments = {
                "correlation_id": "nvidia-request-1a",
                "capability_identity": "nvidia.advisory.guardrail",
                "evidence_hashes": ("a" * 64,),
                "created_at_tick": 7,
                **values,
            }
            with self.subTest(values=values), self.assertRaises(ValueError):
                create_nvidia_advisory_request(**arguments)

    def test_adapter_returns_disabled_response_without_fake_advisory(self):
        response = InertNvidiaAdapter().request_advisory(self.request())
        data = response.to_dict()

        self.assertEqual(NvidiaFoundationStatus.DISABLED.value, response.status)
        self.assertEqual(EXTERNAL_ADVISORY_NON_AUTHORITY, response.advisory_label)
        self.assertEqual(NON_AUTHORITY, response.authority_status)
        self.assertIsNone(response.advisory_payload)
        self.assertEqual(NVIDIA_REASON_DISABLED_BY_DEFAULT, response.failure.reason_code)
        self.assertEqual(NVIDIA_PROVIDER_IDENTITY, response.provenance.provider_identity)
        self.assertEqual(
            NVIDIA_DISABLED_ADAPTER_IDENTITY, response.provenance.adapter_identity
        )
        self.assertEqual("nvidia-request-1a", response.provenance.request_correlation_id)
        self.assertNotIn("approval_status", data)
        self.assert_inert_response(data)

    def test_invalid_config_returns_blocked_failure_not_an_advisory(self):
        response = InertNvidiaAdapter({"enabled": True}).request_advisory(
            self.request()
        )

        self.assertEqual(
            NvidiaFoundationStatus.BLOCKED_INVALID_CONFIGURATION.value,
            response.status,
        )
        self.assertEqual(NVIDIA_REASON_INVALID_CONFIGURATION, response.failure.reason_code)
        self.assertIsNone(response.advisory_payload)
        self.assert_inert_response(response.to_dict())

    def test_response_cannot_be_replaced_into_authority_or_effects(self):
        response = InertNvidiaAdapter().request_advisory(self.request())
        forced = replace(
            response,
            advisory_payload="fabricated output",
            network_called=True,
            gpu_used=True,
            process_started=True,
            filesystem_written=True,
            tool_called=True,
            provider_selected=True,
            ledger_mutated=True,
            memory_patch_created=True,
            action_proposal_created=True,
            approval_created=True,
            can_approve=True,
            can_execute=True,
            can_write=True,
            can_mutate_ledger=True,
            can_change_gate=True,
            can_bypass_kill_switch=True,
            can_bypass_workspace_guard=True,
        )

        self.assertIsNone(forced.advisory_payload)
        self.assert_inert_response(forced.to_dict())

    def test_adapter_does_not_use_network_process_files_or_environment(self):
        denied = AssertionError("inert NVIDIA adapter attempted an external effect")
        with (
            patch.object(socket, "socket", side_effect=denied),
            patch.object(socket, "create_connection", side_effect=denied),
            patch.object(subprocess, "run", side_effect=denied),
            patch.object(subprocess, "Popen", side_effect=denied),
            patch("builtins.open", side_effect=denied),
            patch.object(os, "getenv", side_effect=denied),
            patch.object(Path, "write_text", side_effect=denied),
            patch.object(Path, "write_bytes", side_effect=denied),
        ):
            response = InertNvidiaAdapter().request_advisory(self.request())

        self.assertEqual(NvidiaFoundationStatus.DISABLED.value, response.status)
        self.assert_inert_response(response.to_dict())

    def test_adapter_does_not_mutate_ledger(self):
        with TemporaryDirectory(prefix="aoia-nvidia-ledger-", dir="/tmp") as temporary:
            ledger = Path(temporary) / "ledger.jsonl"
            ledger.write_bytes(b"sentinel-ledger\n")
            before = ledger.read_bytes()
            with patch(
                "runtime.audit.durable_audit_ledger.append_audit_entry",
                side_effect=AssertionError("ledger mutation attempted"),
            ):
                response = InertNvidiaAdapter().request_advisory(self.request())

            self.assertEqual(before, ledger.read_bytes())
            self.assertFalse(response.ledger_mutated)
            self.assertFalse(response.can_mutate_ledger)

    def test_global_write_kill_switch_keeps_precedence(self):
        kill_switch = evaluate_write_kill_switch_value(WRITES_DISABLED)
        response = InertNvidiaAdapter().request_advisory(self.request())

        self.assertEqual(WRITE_KILL_SWITCH_BLOCKED_DISABLED, kill_switch.status.value)
        self.assertFalse(kill_switch.writes_allowed)
        self.assertFalse(response.can_write)
        self.assertFalse(response.can_bypass_kill_switch)

    def test_workspace_guard_cannot_be_bypassed(self):
        with TemporaryDirectory(prefix="aoia-nvidia-workspace-", dir="/tmp") as workspace:
            guard = validate_workspace_target_path(workspace, "../escape.txt")
            response = InertNvidiaAdapter().request_advisory(self.request())

        self.assertEqual(WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL, guard.status.value)
        self.assertFalse(guard.allowed)
        self.assertFalse(response.can_bypass_workspace_guard)
        self.assertFalse(response.filesystem_written)

    def test_existing_provider_registry_and_selector_do_not_include_nvidia(self):
        registry_before = list_runtime_providers()
        selector_before = list_available_providers()

        InertNvidiaAdapter().request_advisory(self.request())

        self.assertEqual(registry_before, list_runtime_providers())
        self.assertEqual(selector_before, list_available_providers())
        self.assertNotIn(
            NVIDIA_PROVIDER_IDENTITY,
            {descriptor.provider_id for descriptor in list_runtime_providers()},
        )
        self.assertNotIn(
            NVIDIA_PROVIDER_IDENTITY,
            {status.provider_id for status in list_available_providers()},
        )

    def test_provider_critic_authority_remains_unchanged(self):
        record = ProviderCritiqueRecord.from_untrusted_output(
            source_provider="fixture-provider",
            model_name="fixture-model",
            prompt_text="classify fixture",
            critique_text="metadata only",
        )
        response = InertNvidiaAdapter().request_advisory(self.request())

        self.assertTrue(record.untrusted)
        self.assertFalse(record.action_authorized)
        self.assertFalse(record.execution_permitted)
        self.assertFalse(record.provider_call_permitted)
        self.assertFalse(response.can_approve)
        self.assertFalse(response.can_execute)

    def test_serialization_contains_no_sensitive_configuration_fields(self):
        response = InertNvidiaAdapter(
            {"key_reference": "do-not-reflect-material"}
        ).request_advisory(self.request())
        serialized = json.dumps(response.to_dict(), sort_keys=True).casefold()

        for forbidden in (
            "do-not-reflect-material",
            "api_key",
            "access_token",
            "credential_value",
            "approval_status",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_adapter_surface_exposes_no_execution_entrypoint(self):
        adapter = InertNvidiaAdapter()

        for method_name in (
            "run",
            "execute",
            "dispatch",
            "write",
            "approve",
            "connect",
            "generate",
            "invoke",
            "load_model",
        ):
            self.assertFalse(hasattr(adapter, method_name))

    def test_module_static_surface_has_no_external_capability(self):
        scan = scan_module(RUNTIME_FILE)
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        forbidden_import_roots = (
            "os",
            "pathlib",
            "socket",
            "subprocess",
            "urllib",
            "http",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "importlib",
            "nvidia",
            "torch",
            "runtime.providers",
            "runtime.control_write",
            "runtime.audit",
            "runtime.execution",
            "runtime.safety",
        )
        forbidden_calls = (
            "open",
            "eval",
            "exec",
            "__import__",
            "os.getenv",
            "os.system",
            "subprocess.run",
            "subprocess.Popen",
            "pathlib.Path.write_text",
            "pathlib.Path.write_bytes",
        )

        for imported in scan.imports:
            self.assertFalse(
                any(
                    imported == root or imported.startswith(root + ".")
                    for root in forbidden_import_roots
                ),
                imported,
            )
        for called in scan.calls:
            self.assertNotIn(called, forbidden_calls)
        for forbidden_text in (
            "os.environ",
            "getenv(",
            "api_key",
            "endpoint_url",
            "shell=true",
        ):
            self.assertNotIn(forbidden_text, source)

    @staticmethod
    def request():
        return create_nvidia_advisory_request(
            correlation_id="nvidia-request-1a",
            capability_identity="nvidia.advisory.guardrail",
            evidence_hashes=("a" * 64,),
            created_at_tick=7,
        )

    def assert_inert_response(self, data):
        for field in (
            "network_called",
            "gpu_used",
            "process_started",
            "filesystem_written",
            "tool_called",
            "provider_selected",
            "ledger_mutated",
            "memory_patch_created",
            "action_proposal_created",
            "approval_created",
            "can_approve",
            "can_execute",
            "can_write",
            "can_mutate_ledger",
            "can_change_gate",
            "can_bypass_kill_switch",
            "can_bypass_workspace_guard",
        ):
            self.assertIs(data[field], False)
        self.assertIs(data["human_review_required"], True)


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            calls.add(call_name(node.func))
    return type(
        "Scan",
        (),
        {"imports": tuple(sorted(imports)), "calls": tuple(sorted(calls))},
    )()


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


if __name__ == "__main__":
    unittest.main()
