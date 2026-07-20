from __future__ import annotations

import ast
import unittest
from dataclasses import dataclass
from pathlib import Path

from runtime.knowledge_modules.german_law import EXPECTED_GERMAN_LAW_DESCRIPTOR
from runtime.knowledge_modules.hub import KnowledgeHub1B
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    instance_descriptor,
    module_descriptor,
    profile,
    query,
    registry_with,
    selection,
    synthetic_configuration,
)


ROOT = Path(__file__).resolve().parents[1]
GENERIC = (
    "contracts.py",
    "evidence.py",
    "instances.py",
    "profiles.py",
    "planning.py",
    "composite.py",
    "policy.py",
    "registry.py",
    "selection.py",
    "transports.py",
    "hub.py",
)
FORBIDDEN_IMPORTS = {
    "aiohttp", "anthropic", "asyncio", "httpx", "openai", "openrouter",
    "requests", "socket", "subprocess", "threading", "urllib", "webbrowser",
}


class KnowledgeHubProviderIndependence1BTests(unittest.TestCase):
    def test_generic_control_plane_has_no_provider_network_process_or_async_imports(self):
        for name in GENERIC:
            with self.subTest(name=name):
                path = ROOT / "runtime/knowledge_modules" / name
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imported = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported.add(node.module.split(".")[0])
                self.assertTrue(imported.isdisjoint(FORBIDDEN_IMPORTS), (name, imported & FORBIDDEN_IMPORTS))

    def test_no_async_background_retry_failover_or_provider_control_state(self):
        combined = "\n".join(
            (ROOT / "runtime/knowledge_modules" / name).read_text(encoding="utf-8")
            for name in GENERIC
        )
        for forbidden in ("async def ", "create_task(", "Thread(", "provider_api_key", "OPENROUTER_API_KEY"):
            self.assertNotIn(forbidden, combined)

    def test_logical_german_descriptor_contains_no_machine_location(self):
        payload = str(EXPECTED_GERMAN_LAW_DESCRIPTOR.to_dict())
        self.assertNotIn("/home/", payload)
        self.assertNotIn("/media/", payload)
        self.assertNotIn("module_repository_path", payload)

    def test_generic_planner_contains_no_german_jurisdiction_or_language_default(self):
        source = (ROOT / "runtime/knowledge_modules/planning.py").read_text(encoding="utf-8")
        self.assertNotIn("DE-BUND", source)
        self.assertNotIn('("de",)', source)

    def test_instance_configuration_is_adapter_specific_not_storage_specific(self):
        descriptor = module_descriptor("opaque-configuration-1a")
        instance = instance_descriptor(descriptor)

        @dataclass(frozen=True, slots=True)
        class OpaqueConfiguration:
            reviewed_deployment: str

        class OpaqueAdapter(SyntheticAdapter):
            @staticmethod
            def _require_configuration(configuration):
                if configuration != OpaqueConfiguration("fixture-deployment"):
                    raise AssertionError("adapter received an unexpected deployment configuration")
                return synthetic_configuration(descriptor.module_id)

            def verify(self, configuration, expected_descriptor):
                return super().verify(
                    self._require_configuration(configuration), expected_descriptor
                )

            def query_plan(self, configuration, module_plan, expected_descriptor):
                return super().query_plan(
                    self._require_configuration(configuration),
                    module_plan,
                    expected_descriptor,
                )

        hub = KnowledgeHub1B(registry_with((descriptor, OpaqueAdapter, instance)))
        result = hub.execute(
            profile(selection(descriptor, instance)),
            query(),
            {instance.instance_id: OpaqueConfiguration("fixture-deployment")},
        )
        self.assertEqual(result.status, "KNOWLEDGE_EVIDENCE_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
