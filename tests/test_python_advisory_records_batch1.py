import json
import pathlib
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
BATCH_PATH = (
    PROJECT_ROOT
    / "knowledge"
    / "languages"
    / "python"
    / "advisory"
    / "level_6_security_pitfalls"
    / "dangerous_builtins_batch1.jsonl"
)

FORBIDDEN_CORRECTED_PATTERNS = (
    "eval(input(",
    "exec(input(",
    "shell=True",
    "os.system(",
    "os.popen(",
    "pickle.load(",
    "pickle.loads(",
)


class PythonAdvisoryRecordsBatch1Tests(unittest.TestCase):
    def test_batch_has_exactly_ten_valid_json_records(self):
        self.assertEqual(10, len(self._records()))

    def test_record_ids_are_unique(self):
        ids = [record["id"] for record in self._records()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_records_are_not_promoted_or_officially_checked(self):
        for record in self._records():
            self.assertNotEqual("promoted_to_advisory", record.get("promotion_status"), record["id"])
            self.assertNotEqual("promoted", record.get("review_status"), record["id"])
            self.assertNotEqual("official_docs_checked", record.get("review_status"), record["id"])
            self.assertNotEqual("safe_to_execute_in_test_sandbox", record.get("execution_policy"), record["id"])

    def test_highest_risk_topics_are_critical(self):
        records = {record["id"]: record for record in self._records()}
        critical_ids = {
            "python-advisory-eval-user-input-batch1",
            "python-advisory-exec-model-generated-code-batch1",
            "python-advisory-pickle-untrusted-data-batch1",
            "python-advisory-subprocess-shell-true-user-input-batch1",
        }
        for record_id in critical_ids:
            self.assertEqual("critical", records[record_id]["risk_level"])

    def test_critical_records_are_never_execute(self):
        for record in self._records():
            if record.get("risk_level") == "critical":
                self.assertEqual("never_execute", record.get("execution_policy"), record["id"])

    def test_required_advisory_text_fields_are_non_empty(self):
        for record in self._records():
            self.assertTrue(record.get("unsafe_or_wrong_pattern"), record["id"])
            self.assertTrue(record.get("corrected_pattern"), record["id"])
            self.assertTrue(record.get("safety_notes"), record["id"])
            self.assertGreaterEqual(len(record.get("negative_tests", [])), 1, record["id"])

    def test_corrected_patterns_do_not_contain_forbidden_execution_patterns(self):
        for record in self._records():
            corrected = record["corrected_pattern"]
            for forbidden in FORBIDDEN_CORRECTED_PATTERNS:
                self.assertNotIn(forbidden, corrected, record["id"])

    def _records(self) -> list[dict]:
        records = []
        for line_number, line in enumerate(BATCH_PATH.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{BATCH_PATH}:{line_number} invalid JSONL") from exc
        return records


if __name__ == "__main__":
    unittest.main()
