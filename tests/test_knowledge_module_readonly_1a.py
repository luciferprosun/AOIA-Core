from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from runtime.knowledge_modules.german_law import (
    EXPECTED_MANIFEST_HASHES,
    EXPECTED_GERMAN_LAW_DESCRIPTOR,
    GERMAN_LAW_EXPECTED_HEAD,
    GermanLawModuleAdapter,
    production_german_law_configuration,
)
from runtime.knowledge_modules.selection import KnowledgeModuleQuery


ROOT = Path(__file__).resolve().parents[1]
GERMAN_REPOSITORY = "/home/l/AOIA_PRODUCTION/repos/AOIA-German-Law-Knowledge-Pack"
CORPUS_ROOT = "/home/l/AOIA_PRODUCTION/data/german-law-corpus"


def selected_hashes():
    corpus = Path(CORPUS_ROOT).resolve()
    return tuple(
        (relative, hashlib.sha256((corpus / relative).read_bytes()).hexdigest())
        for relative, _ in EXPECTED_MANIFEST_HASHES
    )


class KnowledgeModuleReadonly1ATests(unittest.TestCase):
    def test_inert_modules_exclude_the_two_explicit_gateways_and_import_no_provider_or_network(self):
        files = tuple(
            path
            for path in (ROOT / "runtime/knowledge_modules").glob("*.py")
            if path.name not in {"external_gateway.py", "provider_bridge.py"}
        )
        forbidden = {
            "subprocess",
            "socket",
            "ssl",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "openai",
            "anthropic",
            "webbrowser",
        }
        for path in files:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports = set()
                imported_modules = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported_modules.update(alias.name for alias in node.names)
                        imports.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported_modules.add(node.module)
                        imports.add(node.module.split(".")[0])
                self.assertTrue(imports.isdisjoint(forbidden))
                self.assertFalse(
                    any(
                        name.startswith(
                            (
                                "runtime.providers",
                                "runtime.provider_live_adapter",
                                "runtime.execution",
                                "runtime.git_ops",
                                "runtime.browser_ops",
                            )
                        )
                        for name in imported_modules
                    )
                )

    def test_contract_registry_selection_and_evidence_have_no_capability_imports_or_writes(self):
        files = (
            "runtime/knowledge_modules/contracts.py",
            "runtime/knowledge_modules/citation_validation.py",
            "runtime/knowledge_modules/composite.py",
            "runtime/knowledge_modules/context.py",
            "runtime/knowledge_modules/context_policy.py",
            "runtime/knowledge_modules/context_serializer.py",
            "runtime/knowledge_modules/evidence.py",
            "runtime/knowledge_modules/instances.py",
            "runtime/knowledge_modules/planning.py",
            "runtime/knowledge_modules/policy.py",
            "runtime/knowledge_modules/profiles.py",
            "runtime/knowledge_modules/provider_result.py",
            "runtime/knowledge_modules/provider_target.py",
            "runtime/knowledge_modules/registry.py",
            "runtime/knowledge_modules/selection.py",
            "runtime/knowledge_modules/structured_answer.py",
            "runtime/knowledge_modules/transports.py",
            "runtime/schemas/knowledge_context.py",
            "runtime/schemas/knowledge_module.py",
            "runtime/schemas/knowledge_provider_result.py",
            "runtime/schemas/structured_knowledge_answer.py",
        )
        forbidden_imports = {
            "subprocess",
            "socket",
            "ssl",
            "urllib",
            "requests",
            "httpx",
            "openai",
            "git",
            "webbrowser",
        }
        forbidden_calls = {
            "open",
            "write_text",
            "write_bytes",
            "unlink",
            "mkdir",
            "subprocess.run",
            "subprocess.Popen",
        }
        for relative in files:
            with self.subTest(relative=relative):
                tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
                imports = set()
                calls = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module.split(".")[0])
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            calls.add(node.func.id)
                        elif isinstance(node.func, ast.Attribute):
                            calls.add(node.func.attr)
                self.assertTrue(imports.isdisjoint(forbidden_imports))
                self.assertTrue(calls.isdisjoint(forbidden_calls))

    def test_real_query_preserves_selected_manifest_bytes(self):
        configuration = production_german_law_configuration(
            module_repository_path=GERMAN_REPOSITORY,
            corpus_data_root=CORPUS_ROOT,
            expected_repository_head=GERMAN_LAW_EXPECTED_HEAD,
        )
        before = selected_hashes()
        bundle = GermanLawModuleAdapter().query(
            configuration,
            KnowledgeModuleQuery(question="§ 2 NachwG", retrieval_mode="SOURCE_DISCOVERY"),
            EXPECTED_GERMAN_LAW_DESCRIPTOR,
        )
        after = selected_hashes()
        self.assertEqual(before, after)
        self.assertEqual(bundle.authority_status, "NON_AUTHORITATIVE_EVIDENCE_BUNDLE")
        self.assertFalse(bundle.can_write)
        self.assertFalse(bundle.can_execute)
        self.assertFalse(bundle.can_call_provider)


if __name__ == "__main__":
    unittest.main()
