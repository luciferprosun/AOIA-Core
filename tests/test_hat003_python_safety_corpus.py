from __future__ import annotations

import json
import unittest
from pathlib import Path


CORPUS_PATH = Path(__file__).resolve().parent / "corpus" / "python_safety_hat003_v0_1.jsonl"

REQUIRED_FIELDS = {
    "case_id",
    "hat",
    "corpus_version",
    "category",
    "risk_level",
    "code_snippet_as_text",
    "expected_label",
    "expected_approval_state",
    "execution_policy",
    "risk_reason",
    "risky_patterns",
    "notes",
}

REQUIRED_CONSTANTS = {
    "hat": "hat_003_python_safety",
    "corpus_version": "0.1",
    "execution_policy": "text_only_never_execute",
}

ALLOWED_RISK_LEVELS = {"medium", "high", "critical"}
ALLOWED_EXPECTED_LABELS = {"ambiguous", "dangerous"}
ALLOWED_APPROVAL_STATES = {"requires_human_review"}

REQUIRED_CATEGORIES = {
    "dynamic_execution",
    "process_execution",
    "shell_bridge",
    "process_replacement",
    "terminal_automation",
    "dynamic_import",
    "filesystem_mutation",
    "network_side_effect",
    "unsafe_deserialization",
    "command_construction",
    "hidden_side_effect",
}

TEXT_FIELDS = REQUIRED_FIELDS - {"risky_patterns"}


def load_corpus() -> list[dict]:
    records: list[dict] = []
    for line_number, line in enumerate(CORPUS_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise AssertionError(f"invalid JSONL at line {line_number}: {error}") from error
    return records


class Hat003PythonSafetyCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_corpus()

    def test_corpus_file_exists(self) -> None:
        self.assertTrue(CORPUS_PATH.exists())

    def test_corpus_has_exactly_eighteen_records(self) -> None:
        self.assertEqual(18, len(self.records))

    def test_every_record_has_exact_schema(self) -> None:
        for record in self.records:
            with self.subTest(case_id=record.get("case_id")):
                self.assertEqual(REQUIRED_FIELDS, set(record))

    def test_text_fields_are_non_empty_strings(self) -> None:
        for record in self.records:
            with self.subTest(case_id=record["case_id"]):
                for field in TEXT_FIELDS:
                    self.assertIsInstance(record[field], str)
                    self.assertTrue(record[field].strip(), field)

    def test_risky_patterns_are_non_empty_string_lists(self) -> None:
        for record in self.records:
            with self.subTest(case_id=record["case_id"]):
                patterns = record["risky_patterns"]
                self.assertIsInstance(patterns, list)
                self.assertGreater(len(patterns), 0)
                for pattern in patterns:
                    self.assertIsInstance(pattern, str)
                    self.assertTrue(pattern.strip())

    def test_required_constants_are_present(self) -> None:
        for record in self.records:
            with self.subTest(case_id=record["case_id"]):
                for field, expected in REQUIRED_CONSTANTS.items():
                    self.assertEqual(expected, record[field])

    def test_case_ids_are_unique_and_versioned(self) -> None:
        case_ids = [record["case_id"] for record in self.records]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        for case_id in case_ids:
            self.assertTrue(case_id.startswith("hat003_v0_1_"), case_id)

    def test_expected_values_are_supported(self) -> None:
        for record in self.records:
            with self.subTest(case_id=record["case_id"]):
                self.assertIn(record["risk_level"], ALLOWED_RISK_LEVELS)
                self.assertIn(record["expected_label"], ALLOWED_EXPECTED_LABELS)
                self.assertIn(record["expected_approval_state"], ALLOWED_APPROVAL_STATES)

    def test_required_categories_are_represented(self) -> None:
        categories = {record["category"] for record in self.records}
        self.assertTrue(REQUIRED_CATEGORIES.issubset(categories))

    def test_code_snippet_field_is_text_only_metadata(self) -> None:
        for record in self.records:
            with self.subTest(case_id=record["case_id"]):
                snippet = record["code_snippet_as_text"]
                self.assertIsInstance(snippet, str)
                self.assertGreater(len(snippet.strip()), 0)
                self.assertEqual("text_only_never_execute", record["execution_policy"])


if __name__ == "__main__":
    unittest.main()
