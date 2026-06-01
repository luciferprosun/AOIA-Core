import json
import pathlib
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
BATCH_DIR = (
    PROJECT_ROOT
    / "knowledge"
    / "languages"
    / "python"
    / "official_docs_crosscheck"
    / "batch_1_dangerous_builtins"
)
TARGET_MAP_PATH = BATCH_DIR / "OFFICIAL_DOCS_TARGET_MAP.jsonl"
DISCREPANCY_LOG_PATH = BATCH_DIR / "BATCH1_DISCREPANCY_LOG.jsonl"
CHECKLIST_PATH = BATCH_DIR / "BATCH1_CROSSCHECK_CHECKLIST.md"
ADVISORY_PATH = (
    PROJECT_ROOT
    / "knowledge"
    / "languages"
    / "python"
    / "advisory"
    / "level_6_security_pitfalls"
    / "dangerous_builtins_batch1.jsonl"
)


class PythonOfficialDocsBatch1Tests(unittest.TestCase):
    def test_target_map_is_valid_jsonl_with_ten_pending_records(self):
        records = self._load_jsonl(TARGET_MAP_PATH)
        self.assertEqual(10, len(records))
        for record in records:
            self.assertFalse(record["live_checked"], record["id"])
            self.assertEqual("pending", record["check_status"], record["id"])
            self.assertTrue(record["target_doc_url"], record["id"])

    def test_discrepancy_log_is_valid_jsonl(self):
        records = self._load_jsonl(DISCREPANCY_LOG_PATH)
        self.assertEqual(1, len(records))
        self.assertEqual("template_only", records[0]["status"])

    def test_batch_checklist_exists_and_contains_required_terms(self):
        self.assertTrue(CHECKLIST_PATH.exists())
        text = CHECKLIST_PATH.read_text(encoding="utf-8")
        for required in (
            "eval",
            "exec",
            "compile",
            "import",
            "pickle",
            "subprocess",
            "remain_candidate",
            "do_not_promote_reason",
        ):
            self.assertIn(required, text)

    def test_h19_advisory_records_remain_unpromoted_and_unchecked(self):
        for record in self._load_jsonl(ADVISORY_PATH):
            self.assertNotEqual("promoted", record.get("review_status"), record["id"])
            self.assertNotEqual("official_docs_checked", record.get("review_status"), record["id"])
            self.assertNotEqual("human_reviewed", record.get("review_status"), record["id"])
            self.assertNotEqual("promoted_to_advisory", record.get("promotion_status"), record["id"])
            self.assertNotEqual("safe_to_execute_in_test_sandbox", record.get("execution_policy"), record["id"])

    def _load_jsonl(self, path: pathlib.Path) -> list[dict]:
        self.assertTrue(path.exists(), f"missing JSONL file: {path}")
        records = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{path}:{line_number} invalid JSONL") from exc
        self.assertGreater(len(records), 0)
        return records


if __name__ == "__main__":
    unittest.main()
