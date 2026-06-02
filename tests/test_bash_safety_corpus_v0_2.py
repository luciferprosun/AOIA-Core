from __future__ import annotations

import json
import unittest
from pathlib import Path

from runtime.safety.bash_parser import parse_bash_command
from runtime.schemas.command_proposal import (
    APPROVAL_STATES,
    CLASSIFICATION_LABELS,
    CommandProposal,
)

CORPUS_PATH = Path(__file__).resolve().parent / "corpus" / "bash_safety_v0_2.jsonl"
REQUIRED_FIELDS = {
    "id",
    "command",
    "expected_classification",
    "expected_approval_state",
    "category",
    "note",
}
REQUIRED_CATEGORIES = {
    "safe_basic",
    "dangerous_root_delete",
    "dangerous_privilege",
    "dangerous_pipe_to_shell",
    "dangerous_format_or_disk",
    "ambiguous_recursive_delete",
    "ambiguous_chaining",
    "ambiguous_command_substitution",
    "ambiguous_redirection",
    "ambiguous_permissions",
    "unknown_parse_error",
    "false_positive_trap",
}


def load_corpus() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


class BashSafetyCorpusV02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = load_corpus()

    def test_corpus_size_is_bounded(self) -> None:
        self.assertGreaterEqual(len(self.rows), 24)
        self.assertLessEqual(len(self.rows), 36)

    def test_every_row_has_required_fields(self) -> None:
        for row in self.rows:
            self.assertEqual(REQUIRED_FIELDS, set(row))
            self.assertTrue(all(isinstance(value, str) for value in row.values()))

    def test_ids_are_unique(self) -> None:
        ids = [row["id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_expected_values_are_allowed(self) -> None:
        for row in self.rows:
            self.assertIn(row["expected_classification"], CLASSIFICATION_LABELS)
            self.assertIn(row["expected_approval_state"], APPROVAL_STATES)

    def test_required_categories_are_present(self) -> None:
        categories = {row["category"] for row in self.rows}
        self.assertTrue(REQUIRED_CATEGORIES.issubset(categories))

    def test_parser_matches_corpus_expectations(self) -> None:
        for row in self.rows:
            with self.subTest(row_id=row["id"]):
                proposal = parse_bash_command(row["command"], source="corpus_v0_2")
                self.assertIsInstance(proposal, CommandProposal)
                self.assertEqual(
                    proposal.classification,
                    row["expected_classification"],
                )
                self.assertEqual(
                    proposal.approval_state,
                    row["expected_approval_state"],
                )
                self.assertTrue(proposal.dry_run)
                self.assertFalse(hasattr(proposal, "execute"))
                self.assertFalse(hasattr(proposal, "run"))
                self.assertFalse(hasattr(proposal, "dispatch"))


if __name__ == "__main__":
    unittest.main()
