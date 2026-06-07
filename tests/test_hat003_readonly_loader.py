from __future__ import annotations

import ast
import unittest
from pathlib import Path

from runtime.knowledge import load_hat003_status, validate_hat003_read_only


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "runtime" / "knowledge" / "hat003_readonly.py"


class Hat003ReadOnlyLoaderTests(unittest.TestCase):
    def test_status_reports_current_hat003_counts(self) -> None:
        status = load_hat003_status(PROJECT_ROOT)

        self.assertEqual("hat_003_python", status.get("hat_id"))
        self.assertEqual("DRAFT", status.get("status"))
        self.assertFalse(status.get("execution_permitted"))
        self.assertTrue(status.get("read_only"))
        self.assertFalse(status.get("runtime_routing_enabled"))
        self.assertEqual("loader_status_validator_only", status.get("runtime_integration"))
        self.assertEqual(125, status["counts"]["knowledge_cards_thinned"])
        self.assertEqual(125, status["counts"]["knowledge_card_quarantine_index"])
        self.assertEqual(45, status["counts"]["validation_rules_normalized"])
        self.assertEqual(65, status["counts"]["corpus_cases_normalized"])
        self.assertEqual(92, status["counts"]["source_atlas"])
        self.assertEqual(327, status["counts"]["retrieval_index"])

    def test_status_reports_retrieval_kind_counts(self) -> None:
        status = load_hat003_status(PROJECT_ROOT)

        self.assertEqual(
            {
                "corpus_case": 65,
                "knowledge_card": 125,
                "source_atlas_entry": 92,
                "validation_rule": 45,
            },
            status["retrieval_kind_counts"],
        )

    def test_validator_accepts_current_hat003_artifacts(self) -> None:
        report = validate_hat003_read_only(PROJECT_ROOT)

        self.assertTrue(report.ok, report.problems)
        self.assertEqual((), report.problems)
        self.assertIsNotNone(report.status)

    def test_loader_module_does_not_import_execution_surfaces(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "runtime.tools.executor",
            "runtime.tools.shell_tools",
            "runtime.safety.approval_gate",
            "runtime.tools.event_ledger",
            "runtime.providers",
            "runtime.tools.browser_tools",
            "subprocess",
            "socket",
        }

        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))

    def test_loader_module_does_not_define_execution_calls(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_calls = {"eval", "exec", "compile", "__import__"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, forbidden_calls)


if __name__ == "__main__":
    unittest.main()
