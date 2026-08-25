from __future__ import annotations

import ast
import unittest
from pathlib import Path

from commands import build_command_registry
from evidence_review import (
    AUTHORITY_MARKER,
    ReviewInputError,
    bundled_scenario,
    format_review_summary,
    review_candidate,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "runtime" / "evidence_review"


class EvidenceReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = bundled_scenario()

    def test_bundled_answer_is_flagged_as_stale(self) -> None:
        result = review_candidate(str(self.scenario["candidate_answer"]))

        self.assertEqual(result["value_status"], "STALE_VALUE_DETECTED")
        self.assertEqual(result["decision_state"], "HUMAN_REVIEW_REQUIRED")
        self.assertGreaterEqual(result["severity_counts"]["critical"], 1)
        self.assertIn("12.82", result["detected_euro_values"])
        self.assertEqual(result["expected_current_value"], "13.90")

    def test_corrected_example_is_correlated_but_never_approved(self) -> None:
        result = review_candidate(str(self.scenario["corrected_example"]))

        self.assertEqual(result["value_status"], "CURRENT_VALUE_CORROBORATED")
        self.assertEqual(result["decision_state"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(result["authority"], AUTHORITY_MARKER)
        self.assertFalse(result["legal_advice"])
        self.assertFalse(result["network_used"])
        self.assertEqual(result["severity_counts"]["critical"], 0)

    def test_conflicting_values_fail_closed(self) -> None:
        result = review_candidate("Seit 2026 gelten 12,82 Euro oder 13,90 Euro laut BMAS.")

        self.assertEqual(result["value_status"], "CONFLICTING_VALUES_DETECTED")
        self.assertEqual(result["severity_counts"]["critical"], 1)
        self.assertEqual(result["decision_state"], "HUMAN_REVIEW_REQUIRED")

    def test_unrecognised_value_is_not_correlated(self) -> None:
        result = review_candidate("Im Juli 2026 gelten laut BMAS 15,00 Euro.")

        self.assertEqual(result["value_status"], "CURRENT_VALUE_NOT_ESTABLISHED")
        self.assertEqual(result["severity_counts"]["critical"], 1)

    def test_snapshot_and_evidence_hashes_are_deterministic(self) -> None:
        answer = str(self.scenario["candidate_answer"])
        first = review_candidate(answer)
        second = review_candidate(answer)

        self.assertEqual(first["snapshot_hash"], second["snapshot_hash"])
        self.assertEqual(first["evidence_digest"], second["evidence_digest"])
        self.assertRegex(first["snapshot_hash"], r"^[0-9a-f]{64}$")

    def test_scenario_registry_is_returned_as_an_isolated_copy(self) -> None:
        first = bundled_scenario()
        first["evidence"][0]["fact"] = "mutated"

        second = bundled_scenario()
        self.assertNotEqual(second["evidence"][0]["fact"], "mutated")

    def test_invalid_answers_fail_closed(self) -> None:
        for answer in (None, 42, [], "   ", "x" * 20_001):
            with self.subTest(answer_type=type(answer).__name__):
                with self.assertRaises(ReviewInputError):
                    review_candidate(answer)  # type: ignore[arg-type]

    def test_cli_command_uses_same_engine(self) -> None:
        result = build_command_registry().execute("/review corrected", object())

        self.assertTrue(result.handled)
        self.assertIn("CURRENT_VALUE_CORROBORATED", result.message)
        self.assertIn("HUMAN_REVIEW_REQUIRED", result.message)
        self.assertIn(AUTHORITY_MARKER, result.message)

    def test_operator_summary_contains_hashes_and_next_step(self) -> None:
        result = review_candidate(str(self.scenario["candidate_answer"]))
        summary = format_review_summary(result)

        self.assertIn(result["evidence_digest"], summary)
        self.assertIn(result["snapshot_hash"], summary)
        self.assertIn("next step:", summary)


class EvidenceReviewBoundaryTests(unittest.TestCase):
    def test_module_has_no_process_or_provider_client_imports(self) -> None:
        forbidden_roots = {
            "aiohttp",
            "anthropic",
            "httpx",
            "openai",
            "requests",
            "subprocess",
        }
        violations: list[str] = []
        for path in SOURCE_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = {alias.name.split(".", 1)[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = {node.module.split(".", 1)[0]}
                else:
                    continue
                blocked = names & forbidden_roots
                if blocked:
                    violations.append(f"{path.name}: {sorted(blocked)}")
        self.assertEqual(violations, [])

    def test_module_contains_no_write_mode_file_open(self) -> None:
        violations: list[str] = []
        for path in SOURCE_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    mode = node.args[1] if len(node.args) > 1 else None
                    if isinstance(mode, ast.Constant) and any(flag in str(mode.value) for flag in "wax+"):
                        violations.append(path.name)
        self.assertEqual(violations, [])

    def test_active_surfaces_use_only_aoia_core_identity(self) -> None:
        retired_identity = "".join(("hack", "verse"))
        paths = [
            *SOURCE_ROOT.glob("*.py"),
            REPOSITORY_ROOT / "runtime" / "webapp.py",
            REPOSITORY_ROOT / "web" / "index.html",
            REPOSITORY_ROOT / "web" / "app.js",
            REPOSITORY_ROOT / "web" / "styles.css",
        ]
        violations = [
            str(path.relative_to(REPOSITORY_ROOT))
            for path in paths
            if retired_identity in path.read_text(encoding="utf-8").casefold()
        ]
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
