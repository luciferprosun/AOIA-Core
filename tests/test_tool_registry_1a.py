from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.schemas.tool_registry import (
    ToolDescriptor,
    ToolKind,
    ToolRegistry,
    ToolRegistryStatus,
    ToolRiskClass,
    get_default_tool_registry,
    lookup_tool,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_REGISTRY = REPO_ROOT / "runtime" / "schemas" / "tool_registry.py"


class ToolRegistry1ATests(unittest.TestCase):
    def test_default_registry_is_deterministic(self):
        first = get_default_tool_registry()
        second = get_default_tool_registry()

        self.assertEqual(first.registry_hash, second.registry_hash)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual("AOIA_TOOL_REGISTRY_1A", first.schema_version)

    def test_default_registry_contains_expected_static_metadata_ids(self):
        registry = get_default_tool_registry()
        ids = tuple(descriptor.tool_id for descriptor in registry.list_tools())

        self.assertEqual(
            (
                "browser_action",
                "file_write",
                "git_commit",
                "git_push",
                "package_install",
                "provider_call",
                "shell_command",
                "test_run",
            ),
            ids,
        )

    def test_lookup_known_tool_returns_deterministic_descriptor(self):
        first = lookup_tool("file_write")
        second = lookup_tool("file_write")

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first, second)
        self.assertEqual(ToolKind.FILE_SYSTEM, first.tool_kind)
        self.assertEqual(ToolRegistryStatus.PREVIEW_ONLY, first.registry_status)
        self.assertEqual(ToolRiskClass.HIGH, first.risk_class)
        self.assertTrue(first.previewable)
        self.assertTrue(first.write_related)
        self.assert_all_authority_false(first)

    def test_lookup_unknown_or_dangerous_tool_returns_none(self):
        dangerous_ids = (
            "provider_made_up_tool_xyz",
            "rm -rf /",
            "../tool",
            "/bin/sh",
            "python -c",
            "curl http://example.com",
            "",
            "bad\x00id",
        )
        for tool_id in dangerous_ids:
            with self.subTest(tool_id=tool_id):
                self.assertIsNone(lookup_tool(tool_id))

    def test_provider_suggested_tool_id_is_not_dynamically_registered(self):
        registry = get_default_tool_registry()

        self.assertIsNone(lookup_tool("provider_made_up_tool_xyz", registry))
        self.assertEqual(8, len(registry.list_tools()))

    def test_descriptor_and_registry_are_frozen(self):
        registry = get_default_tool_registry()
        descriptor = lookup_tool("file_write", registry)

        with self.assertRaises(FrozenInstanceError):
            descriptor.display_name = "changed"
        with self.assertRaises(FrozenInstanceError):
            registry.registry_hash = "changed"
        with self.assertRaises(FrozenInstanceError):
            registry.descriptors = ()

    def test_registry_has_no_dynamic_registration_methods(self):
        registry = get_default_tool_registry()
        descriptor = lookup_tool("file_write", registry)
        forbidden_methods = (
            "execute",
            "run",
            "call",
            "invoke",
            "dispatch",
            "approve",
            "allow",
            "deny",
            "register_tool",
            "add_tool",
            "remove_tool",
            "load_provider_tool",
            "load_plugin",
        )

        for obj in (registry, descriptor):
            for method_name in forbidden_methods:
                with self.subTest(obj=type(obj).__name__, method_name=method_name):
                    self.assertFalse(callable(getattr(obj, method_name, None)))

    def test_no_forbidden_authority_fields_exist(self):
        registry = get_default_tool_registry()
        descriptor = lookup_tool("file_write", registry)
        forbidden_fields = (
            "allowed",
            "approved",
            "permission",
            "authorized",
            "can_execute_true",
            "can_write_true",
            "policy_decision",
            "gate_result",
            "approval_granted",
            "execution_permitted",
            "tool_allowed",
        )

        for obj in (registry, descriptor):
            for field_name in forbidden_fields:
                with self.subTest(obj=type(obj).__name__, field_name=field_name):
                    self.assertFalse(hasattr(obj, field_name))

    def test_descriptor_hash_is_deterministic_and_changes_with_metadata(self):
        descriptor = lookup_tool("file_write")
        changed = replace(descriptor, description="Changed inert metadata.")

        self.assertEqual(descriptor.descriptor_hash, lookup_tool("file_write").descriptor_hash)
        self.assertNotEqual(descriptor.descriptor_hash, changed.descriptor_hash)

    def test_registry_hash_changes_when_descriptor_metadata_changes(self):
        registry = get_default_tool_registry()
        changed_descriptor = replace(lookup_tool("file_write", registry), description="Changed inert metadata.")
        changed_descriptors = tuple(
            changed_descriptor if descriptor.tool_id == "file_write" else descriptor
            for descriptor in registry.descriptors
        )
        changed_registry = ToolRegistry(descriptors=changed_descriptors)

        self.assertNotEqual(registry.registry_hash, changed_registry.registry_hash)

    def test_risk_status_and_previewable_are_advisory_only(self):
        for descriptor in get_default_tool_registry().list_tools():
            with self.subTest(tool_id=descriptor.tool_id):
                self.assertIsInstance(descriptor.risk_class, ToolRiskClass)
                self.assertIsInstance(descriptor.registry_status, ToolRegistryStatus)
                self.assertIsInstance(descriptor.previewable, bool)
                self.assert_all_authority_false(descriptor)

    def test_authority_booleans_always_remain_false(self):
        registry = get_default_tool_registry()
        descriptor = lookup_tool("file_write", registry)
        replaced_descriptor = replace(
            descriptor,
            tool_called=True,
            can_call_tool=True,
            can_execute=True,
            can_write=True,
            can_commit=True,
            can_change_approval_gate=True,
            can_change_policy=True,
            can_access_network=True,
            can_read_env=True,
            can_load_api_key=True,
        )
        replaced_registry = replace(
            registry,
            tool_called=True,
            can_call_tool=True,
            can_execute=True,
            can_write=True,
            can_commit=True,
            can_change_approval_gate=True,
            can_change_policy=True,
            can_access_network=True,
            can_read_env=True,
            can_load_api_key=True,
        )

        self.assert_all_authority_false(descriptor)
        self.assert_all_authority_false(registry)
        self.assert_all_authority_false(replaced_descriptor)
        self.assert_all_authority_false(replaced_registry)

    def test_list_by_kind_is_deterministic_metadata_only(self):
        registry = get_default_tool_registry()
        git_tools = registry.list_by_kind(ToolKind.GIT)

        self.assertEqual(("git_commit", "git_push"), tuple(descriptor.tool_id for descriptor in git_tools))
        for descriptor in git_tools:
            self.assertTrue(descriptor.git_related)
            self.assert_all_authority_false(descriptor)
        self.assertEqual((), registry.list_by_kind("NOT_A_KIND"))

    def test_no_filesystem_writes_occur(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            _registry = get_default_tool_registry()
            _descriptor = lookup_tool("file_write")
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_static_forbidden_imports_and_capabilities(self):
        forbidden_modules = {
            "subprocess",
            "os",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "http.client",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "git",
            "dotenv",
            "runtime.intent_router",
            "runtime.tool_call_preview_dispatcher",
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.human_decision_gate_integration",
            "runtime.tools.executor",
            "runtime.tools.browser_tools",
            "runtime.tools.shell_tools",
        }
        forbidden_text = (
            "sub" + "process",
            "os" + "." + "system",
            "popen",
            "socket",
            "requests",
            "urllib",
            "http.client",
            "open(",
            ".write(",
            "pathlib",
            "shutil",
            "webbrowser",
            "playwright",
            "selenium",
            "os.environ",
            "getenv(",
            "dispatch(",
            "invoke(",
            "execute(",
        )
        source = TOOL_REGISTRY.read_text(encoding="utf-8")
        lowered = source.casefold()
        for term in forbidden_text:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for module_name in imports:
            with self.subTest(module_name=module_name):
                self.assertFalse(
                    any(
                        module_name == forbidden
                        or module_name.startswith(forbidden + ".")
                        for forbidden in forbidden_modules
                    )
                )

    def test_manual_descriptor_claims_cannot_add_authority(self):
        descriptor = ToolDescriptor(
            tool_id="manual_tool",
            tool_kind=ToolKind.UNKNOWN,
            display_name="Manual",
            description="Manual metadata.",
            risk_class=ToolRiskClass.UNKNOWN,
            registry_status=ToolRegistryStatus.DISABLED_METADATA_ONLY,
            argument_schema={},
            tool_called=True,
            can_call_tool=True,
            can_execute=True,
            can_write=True,
            can_commit=True,
            can_change_approval_gate=True,
            can_change_policy=True,
            can_access_network=True,
            can_read_env=True,
            can_load_api_key=True,
        )

        self.assert_all_authority_false(descriptor)

    def assert_all_authority_false(self, value):
        fields = (
            "tool_called",
            "can_call_tool",
            "can_execute",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        )
        for field_name in fields:
            with self.subTest(field_name=field_name):
                self.assertFalse(getattr(value, field_name))


if __name__ == "__main__":
    unittest.main()
