import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
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
    "scanned_file_paths",
    "total_records",
    "templates_skipped",
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


def load_scan_module():
    module_name = "aoia_duplicate_conflict_scan"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, SCAN_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load scan module: {SCAN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class PythonDuplicateConflictScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assert_path_exists(SCAN_SCRIPT)
        cls.scan_module = load_scan_module()
        cls.report = cls.scan_module.scan_duplicate_conflicts()

    def test_tracked_reports_exist_without_refresh(self):
        self.assertTrue(RESULTS_PATH.exists())
        self.assertTrue(SUMMARY_PATH.exists())

    def test_results_have_required_keys(self):
        self.assertEqual(REQUIRED_RESULT_KEYS, set(self.report))
        self.assertTrue(self.scan_module.verify_duplicate_conflict_report(self.report))

    def test_no_premature_promotion_or_official_docs_checked(self):
        data = self.report
        self.assertEqual([], data["premature_promotions"])
        self.assertEqual([], data["official_docs_checked_without_gate"])
        self.assertEqual([], data["safe_to_execute_records"])

    def test_records_remain_unpromoted(self):
        data = self.report
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
        summary = self.scan_module.serialize_duplicate_conflict_summary(self.report).decode("utf-8")
        self.assertIn("does not merge, delete, promote, or execute records", summary)

    def test_repeated_scans_and_serialization_are_deterministic(self):
        second_report = self.scan_module.scan_duplicate_conflicts()
        self.assertEqual(self.report, second_report)
        self.assertEqual(
            self.scan_module.serialize_duplicate_conflict_report(self.report),
            self.scan_module.serialize_duplicate_conflict_report(second_report),
        )
        self.assertEqual(
            self.scan_module.serialize_duplicate_conflict_summary(self.report),
            self.scan_module.serialize_duplicate_conflict_summary(second_report),
        )

    def test_explicit_writer_requires_output_root(self):
        with self.assertRaises(TypeError):
            self.scan_module.write_duplicate_conflict_report(self.report)

    def test_explicit_writer_is_deterministic_in_temporary_roots(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = self.scan_module.write_duplicate_conflict_report(
                self.report,
                output_root=first,
            )
            second_paths = self.scan_module.write_duplicate_conflict_report(
                self.report,
                output_root=second,
            )
            self.assertEqual(first_paths.results_path.read_bytes(), second_paths.results_path.read_bytes())
            self.assertEqual(first_paths.summary_path.read_bytes(), second_paths.summary_path.read_bytes())

    def test_writer_rejects_relative_traversal_and_symlink_output(self):
        with self.assertRaises(ValueError):
            self.scan_module.write_duplicate_conflict_report(
                self.report,
                output_root="relative-output",
            )
        with self.assertRaises(ValueError):
            self.scan_module.write_duplicate_conflict_report(
                self.report,
                output_root=PROJECT_ROOT / "tests" / ".." / "tests",
            )
        with tempfile.TemporaryDirectory() as temporary_root:
            root = pathlib.Path(temporary_root)
            real_output = root / "real"
            linked_output = root / "linked"
            real_output.mkdir()
            linked_output.symlink_to(real_output, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.scan_module.write_duplicate_conflict_report(
                    self.report,
                    output_root=linked_output,
                )

    def test_writer_does_not_overwrite_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            root = pathlib.Path(temporary_root)
            unrelated = root / "unrelated.txt"
            unrelated.write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.scan_module.write_duplicate_conflict_report(
                    self.report,
                    output_root=root,
                )
            self.assertEqual("keep", unrelated.read_text(encoding="utf-8"))

    def test_writer_does_not_refresh_repository_report_directory(self):
        with self.assertRaises(ValueError):
            self.scan_module.write_duplicate_conflict_report(
                self.report,
                output_root=SCAN_SCRIPT.parent,
            )

    def test_failed_scan_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as source_root, tempfile.TemporaryDirectory() as output_root:
            pathlib.Path(source_root, "examples.jsonl").write_text("{malformed json}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.scan_module.scan_duplicate_conflicts(source_root)
            self.assertEqual([], list(pathlib.Path(output_root).iterdir()))

    def test_cli_requires_explicit_output_root(self):
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, str(SCAN_SCRIPT)],
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("--output-root", completed.stderr)

    def test_verifier_rejects_malformed_report(self):
        malformed = dict(self.report)
        malformed.pop("total_records")
        self.assertFalse(self.scan_module.verify_duplicate_conflict_report(malformed))
        with self.assertRaises(ValueError):
            self.scan_module.serialize_duplicate_conflict_report(malformed)

    @staticmethod
    def assert_path_exists(path: pathlib.Path):
        if not path.exists():
            raise AssertionError(f"missing scan script: {path}")

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
