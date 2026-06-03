from __future__ import annotations

import json
import unittest
from pathlib import Path

from runtime.safety.approval_gate import evaluate_approval
from runtime.safety.bash_parser import parse_bash_command
from runtime.schemas.command_proposal import (
    APPROVAL_STATES,
    CLASSIFICATION_LABELS,
    CommandProposal,
)

CORPUS_PATH = Path(__file__).resolve().parent / "corpus" / "bash_safety_v0_3.jsonl"
REQUIRED_FIELDS = {
    "case_id",
    "category",
    "command",
    "expected_label",
    "expected_approval_state",
    "risk_reason",
    "notes",
}
REQUIRED_CATEGORIES = {
    "obfuscated_root_delete",
    "absolute_path_invocation",
    "escaped_command_name",
    "ifs_substitution",
    "env_wrapper",
    "xargs_wrapper",
    "alias_function_definition",
    "heredoc_indicator",
    "base64_payload_indicator",
    "nested_command_substitution",
    "pipe_to_shell_variant",
    "redirection_to_sensitive_path",
    "sudo_privilege_variant",
    "chmod_chown_recursive",
    "false_positive_output_only",
    "safe_admin_read_only",
    "unknown_unbalanced_quote",
    "unicode_or_encoding_trick",
}


def load_corpus() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(CORPUS_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise AssertionError(f"invalid JSONL at line {line_number}: {error}") from error
        rows.append(row)
    return rows


class BashSafetyCorpusV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = load_corpus()

    def test_corpus_has_exactly_thirty_cases(self) -> None:
        self.assertEqual(30, len(self.rows))

    def test_every_row_has_required_fields(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row.get("case_id")):
                self.assertEqual(REQUIRED_FIELDS, set(row))
                for field in REQUIRED_FIELDS:
                    self.assertIsInstance(row[field], str)
                    self.assertTrue(row[field].strip())

    def test_case_ids_are_unique(self) -> None:
        case_ids = [row["case_id"] for row in self.rows]
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_expected_values_are_supported(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                self.assertIn(row["expected_label"], CLASSIFICATION_LABELS)
                self.assertIn(row["expected_approval_state"], APPROVAL_STATES)

    def test_required_categories_are_present(self) -> None:
        categories = {row["category"] for row in self.rows}
        self.assertTrue(REQUIRED_CATEGORIES.issubset(categories))

    def test_parser_and_gate_match_v0_3_expectations(self) -> None:
        for row in self.rows:
            with self.subTest(case_id=row["case_id"]):
                proposal = parse_bash_command(row["command"], source="corpus_v0_3")
                self.assertIsInstance(proposal, CommandProposal)
                self.assertEqual(row["expected_label"], proposal.classification)
                self.assertEqual(row["expected_approval_state"], proposal.approval_state)
                self.assertTrue(hasattr(proposal, "classification"))
                if row["expected_label"] != "safe":
                    self.assertNotEqual("safe", proposal.classification)

                decision = evaluate_approval(proposal)
                self.assertFalse(decision.execution_permitted)
                if row["expected_label"] in {"ambiguous", "dangerous", "unknown"}:
                    self.assertFalse(decision.allowed)

    def test_this_file_has_no_forbidden_execution_primitives(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        blocked = (
            "sub" + "process",
            "os." + "system",
            "shell" + "=True",
            "P" + "open",
            "ev" + "al(",
            "ex" + "ec(",
        )
        for pattern in blocked:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)

    def test_this_file_does_not_import_forbidden_runtime_boundaries(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        blocked = (
            "event_" + "ledger",
            "shell_" + "tools",
            "exec" + "utor",
            "prov" + "iders",
            "rout" + "ing",
        )
        for pattern in blocked:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)


if __name__ == "__main__":
    unittest.main()
