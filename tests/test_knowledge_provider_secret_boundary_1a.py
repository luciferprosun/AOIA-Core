from __future__ import annotations

import ast
import json
import os
import unittest
from pathlib import Path

from runtime.knowledge_modules.provider_bridge import KnowledgeProviderBridge1A
from tests.knowledge_context_test_support_1a import context_fixture, target


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeProviderSecretBoundary1ATests(unittest.TestCase):
    def test_context_request_and_result_never_contain_environment_secrets(self):
        fixture = context_fixture()
        secret = "aoia-test-secret-value-that-must-not-escape"
        previous = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = secret
        try:
            prepared = KnowledgeProviderBridge1A.prepare_provider_request(
                fixture.package, target()
            )
            result = KnowledgeProviderBridge1A(fixture.hub).execute(
                profile=fixture.profile,
                query=fixture.query,
                instance_configurations=fixture.configurations,
                provider_target=target(),
            )
        finally:
            if previous is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = previous
        self.assertNotIn(secret, json.dumps(fixture.package.to_dict(), sort_keys=True))
        self.assertNotIn(secret, json.dumps(prepared.request.to_dict(), sort_keys=True))
        self.assertNotIn(secret, json.dumps(result.to_dict(), sort_keys=True))

    def test_bridge_has_no_network_client_secret_access_subprocess_or_writes(self):
        path = ROOT / "runtime/knowledge_modules/provider_bridge.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        for forbidden in (
            "os", "pathlib", "socket", "ssl", "subprocess", "urllib", "requests",
            "httpx", "aiohttp", "openai", "anthropic",
        ):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for name in imports))
        self.assertTrue({"open", "write_text", "write_bytes", "unlink", "mkdir"}.isdisjoint(calls))

    def test_bridge_imports_exact_canonical_provider_modules_only(self):
        source = (ROOT / "runtime/knowledge_modules/provider_bridge.py").read_text(encoding="utf-8")
        self.assertIn("from runtime.providers.gateway import run_provider_request", source)
        self.assertIn("from runtime.providers.payloads import build_provider_envelope", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("_OPENROUTER_ENDPOINT", source)
        self.assertNotIn("_read_api_key", source)


if __name__ == "__main__":
    unittest.main()
