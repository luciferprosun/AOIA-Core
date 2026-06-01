import json
import pathlib
import subprocess
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN_SCRIPT = (
    PROJECT_ROOT
    / "knowledge"
    / "languages"
    / "python"
    / "audits"
    / "duplicate_conflict_scan"
    / "scan_python_knowledge_duplicates.py"
)
RESULTS_PATH = SCAN_SCRIPT.parent / "H21_DUPLICATE_CONFLICT_SCAN_RESULTS.json"
SUMMARY_PATH = SCAN_SCRIPT.parent / "H21_DUPLICATE_CONFLICT_SCAN_SUMMARY.md"

REQUIRED_RESULT_KEYS = {
    "scanned_files",
    "total_records",
    "duplicate_ids",
    "duplicate_terms",
    "duplicate_titles",
    "duplicate_unsafe_patterns",
    "duplicate_corrected_patterns",
    "status_conflicts",
    "policy_conflicts",
    "dangerous_low_risk_records",
    "premature_promotions",
    "official_docs_checked_without_gate",
    "safe_to_execute_records",
    "missing_source_refs",
}


class PythonDuplicateConflictScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assert_path_exists(SCAN_SCRIPT)
        subprocess.run(
            [sys.executable, str(SCAN_SCRIPT)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_scan_outputs_exist(self):
        self.assertTrue(RESULTS_PATH.exists())
        self.assertTrue(SUMMARY_PATH.exists())

    def test_results_have_required_keys(self):
        data = self._results()
        self.assertTrue(REQUIRED_RESULT_KEYS.issubset(data))

    def test_no_premature_promotion_or_official_docs_checked(self):
        data = self._results()
        self.assertEqual([], data["premature_promotions"])
        self.assertEqual([], data["official_docs_checked_without_gate"])
        self.assertEqual([], data["safe_to_execute_records"])

    def test_records_remain_unpromoted(self):
        data = self._results()
        for collection_name in ("duplicate_ids", "duplicate_terms", "status_conflicts", "policy_conflicts"):
            self.assertIsInstance(data[collection_name], list)
        all_records = self._flatten_record_summaries(data)
        for record in all_records:
            self.assertNotEqual("promoted_to_advisory", record.get("promotion_status"), record.get("id"))
            self.assertNotEqual("promoted", record.get("review_status"), record.get("id"))
            self.assertNotEqual("official_docs_checked", record.get("review_status"), record.get("id"))
            self.assertNotEqual(
                "safe_to_execute_in_test_sandbox",
                record.get("execution_policy"),
                record.get("id"),
            )

    def test_scan_does_not_report_network_or_execution_artifacts(self):
        summary = SUMMARY_PATH.read_text(encoding="utf-8")
        self.assertIn("does not merge, delete, promote, or execute records", summary)

    @staticmethod
    def assert_path_exists(path: pathlib.Path):
        if not path.exists():
            raise AssertionError(f"missing scan script: {path}")

    def _results(self) -> dict:
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))

    def _flatten_record_summaries(self, data: dict) -> list[dict]:
        records = []
        for value in data.values():
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("records"), list):
                    records.extend(item["records"])
                elif isinstance(item, dict):
                    records.append(item)
        return records


if __name__ == "__main__":
    unittest.main()
