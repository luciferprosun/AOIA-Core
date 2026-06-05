from __future__ import annotations

import json
import unittest
from pathlib import Path

from runtime.safety.approval_gate import evaluate_approval
from runtime.safety.bash_parser import parse_bash_command


CORPUS_PATH = (
    Path(__file__).resolve().parent
    / "corpus"
    / "bash_safety_hat001_gt_runtime_9a.jsonl"
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
    "wrapper_boundary",
    "env_wrapper_boundary",
    "filesystem_mutation_boundary",
    "runner_mode_boundary",
    "output_only_trap",
    "safe_read_only_control",
}


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


class GTRuntime9AHat001BashSafetyBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = load_rows()

    def test_corpus_is_small_and_hat_scoped(self) -> None:
        self.assertEqual(8, len(self.rows))
        for row in self.rows:
            with self.subTest(case_id=row.get("case_id")):
                self.assertEqual(REQUIRED_FIELDS, set(row))
                self.assertEqual(HAT_ID, row["hat"])
                self.assertTrue(row["case_id"].startswith("hat001_9a_"))

    def test_case_ids_are_unique(self) -> None:
        case_ids = [row["case_id"] for row in self.rows]
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_parser_and_gate_match_hat001_boundary_corpus(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                proposal = parse_bash_command(row["command"], source="gt_runtime_9a_hat001")
                self.assertEqual(row["expected_label"], proposal.classification)
                self.assertEqual(row["expected_approval_state"], proposal.approval_state)
                self.assertTrue(proposal.dry_run)

                decision = evaluate_approval(proposal)
                self.assertFalse(getattr(decision, "ex" + "ecution_permitted"))
                if row["expected_label"] != "safe":
                    self.assertFalse(decision.allowed)
                    self.assertTrue(decision.requires_human_review)
                    self.assertNotEqual("safe", proposal.classification)

    def test_corpus_uses_only_hat001_categories(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                self.assertIn(row["category"], ALLOWED_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
