from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


class AdversarialCorpusV02StubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus_path = Path(__file__).resolve().parents[1] / "corpus" / "adversarial_v0.2_stub.jsonl"
        cls.source_path = Path(__file__).resolve()

    def load_records(self) -> list[dict[str, object]]:
        text = self.corpus_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in text if line.strip()]

    def test_corpus_exists(self) -> None:
        self.assertTrue(self.corpus_path.exists())

    def test_every_line_is_valid_json(self) -> None:
        for line in self.corpus_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                json.loads(line)

    def test_record_count_is_between_twenty_and_thirty(self) -> None:
        records = self.load_records()
        self.assertGreaterEqual(len(records), 20)
        self.assertLessEqual(len(records), 30)

    def test_every_record_has_required_fields(self) -> None:
        required = {"id", "command", "expected_label", "category", "rationale", "should_execute"}
        for record in self.load_records():
            self.assertEqual(set(record.keys()), required)

    def test_expected_label_is_allowed(self) -> None:
        allowed = {"safe", "ambiguous", "dangerous", "unknown"}
        for record in self.load_records():
            self.assertIn(record["expected_label"], allowed)

    def test_should_execute_is_always_false(self) -> None:
        for record in self.load_records():
            self.assertIs(record["should_execute"], False)

    def test_ids_are_unique(self) -> None:
        ids = [record["id"] for record in self.load_records()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_required_categories_are_represented(self) -> None:
        required_categories = {
            "whitespace_obfuscation",
            "quoting_tricks",
            "variable_interpolation",
            "command_substitution",
            "encoded_payload_indicator",
            "heredoc_indicator",
            "chained_commands",
            "pipe_to_shell",
            "redirection_to_sensitive_path",
            "recursive_permission_change",
            "privilege_escalation_indicator",
            "safe_command_false_positive_trap",
            "ambiguous_admin_command",
            "context_dependent_danger",
            "unknown_or_incomplete_command",
        }
        categories = {record["category"] for record in self.load_records()}
        self.assertTrue(required_categories.issubset(categories))

    def test_no_command_is_executed(self) -> None:
        records = self.load_records()
        self.assertTrue(all(isinstance(record["command"], str) for record in records))
        self.assertTrue(all(record["should_execute"] is False for record in records))

    def test_test_file_does_not_import_forbidden_execution_helpers(self) -> None:
        source = self.source_path.read_text(encoding="utf-8")
        forbidden_patterns = (
            r"\bsub" + r"process\b",
            r"\bos" + r"\.system\b",
            r"\bpt" + r"y\b",
            r"\bshell_" + r"tools\b",
            r"\bexec" + r"utor\b",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, source))


if __name__ == "__main__":
    unittest.main()
