from __future__ import annotations

import json
import unittest
from pathlib import Path

from runtime.safety.approval_gate import evaluate_approval
from runtime.safety.bash_parser import parse_bash_command


CORPUS_PATH = (
    Path(__file__).resolve().parent
    / "corpus"
    / "bash_safety_hat001_gt_runtime_9b.jsonl"
)
REQUIRED_FIELDS = {
    "case_id",
    "hat",
    "category",
    "command",
    "expected_label",
    "expected_approval_state",
    "notes",
}
HAT_ID = "hat_001_bash_safety"
ALLOWED_CATEGORIES = {
    "ambiguous_review_boundary",
    "false_positive_safe_text",
    "false_positive_conservative_text",
    "false_negative_suffix_trap",
    "false_negative_substitution_trap",
}
REQUIRED_CATEGORIES = ALLOWED_CATEGORIES
SAFE_LABELS = {"safe"}
REVIEW_LABELS = {"ambiguous", "dangerous", "unknown"}


def load_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(CORPUS_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise AssertionError(f"invalid JSONL at line {line_number}: {error}") from error
    return rows


class GTRuntime9BHat001BashSafetyBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = load_rows()

    def test_corpus_is_small_and_hat_scoped(self) -> None:
        self.assertEqual(12, len(self.rows))
        for row in self.rows:
            with self.subTest(case_id=row.get("case_id")):
                self.assertEqual(REQUIRED_FIELDS, set(row))
                self.assertEqual(HAT_ID, row["hat"])
                self.assertTrue(row["case_id"].startswith("hat001_9b_"))
                self.assertIn(row["category"], ALLOWED_CATEGORIES)

    def test_case_ids_are_unique(self) -> None:
        case_ids = [row["case_id"] for row in self.rows]
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_required_boundary_categories_are_present(self) -> None:
        categories = {row["category"] for row in self.rows}
        self.assertTrue(REQUIRED_CATEGORIES.issubset(categories))

    def test_parser_and_gate_match_hat001_9b_corpus(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                proposal = parse_bash_command(row["command"], source="gt_runtime_9b_hat001")
                self.assertEqual(row["expected_label"], proposal.classification)
                self.assertEqual(row["expected_approval_state"], proposal.approval_state)
                self.assertTrue(proposal.dry_run)

                decision = evaluate_approval(proposal)
                self.assertFalse(getattr(decision, "ex" + "ecution_permitted"))
                if row["expected_label"] in SAFE_LABELS:
                    self.assertTrue(decision.allowed)
                    self.assertFalse(decision.requires_human_review)
                if row["expected_label"] in REVIEW_LABELS:
                    self.assertFalse(decision.allowed)
                    self.assertTrue(decision.requires_human_review)

    def test_false_positive_text_is_not_marked_dangerous(self) -> None:
        for row in self.rows:
            if not row["category"].startswith("false_positive_"):
                continue
            with self.subTest(case_id=row["case_id"]):
                proposal = parse_bash_command(row["command"], source="gt_runtime_9b_hat001")
                self.assertNotEqual("dangerous", proposal.classification)

    def test_false_negative_traps_are_not_silently_safe(self) -> None:
        for row in self.rows:
            if not row["category"].startswith("false_negative_"):
                continue
            with self.subTest(case_id=row["case_id"]):
                proposal = parse_bash_command(row["command"], source="gt_runtime_9b_hat001")
                decision = evaluate_approval(proposal)
                self.assertNotEqual("safe", proposal.classification)
                self.assertEqual("requires_human_review", proposal.approval_state)
                self.assertTrue(decision.requires_human_review)

    def test_ambiguous_boundaries_require_review(self) -> None:
        for row in self.rows:
            if row["category"] != "ambiguous_review_boundary":
                continue
            with self.subTest(case_id=row["case_id"]):
                proposal = parse_bash_command(row["command"], source="gt_runtime_9b_hat001")
                self.assertEqual("ambiguous", proposal.classification)
                self.assertEqual("requires_human_review", proposal.approval_state)


if __name__ == "__main__":
    unittest.main()
