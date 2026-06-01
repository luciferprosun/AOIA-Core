import ast
import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge" / "languages" / "python"
ENUMS_PATH = PYTHON_KNOWLEDGE_DIR / "schema_enums.json"
REFERENCE_DIR = PYTHON_KNOWLEDGE_DIR / "reference"
OFFICIAL_DOCS_CROSSCHECK_DIR = PYTHON_KNOWLEDGE_DIR / "official_docs_crosscheck"

REQUIRED_ENUM_GROUPS = {
    "difficulty",
    "review_status",
    "risk_level",
    "execution_policy",
    "promotion_status",
    "confidence_level",
}

DANGEROUS_TERMS = {
    "eval",
    "exec",
    "compile",
    "import",
    "subprocess",
    "os.system",
    "os.popen",
    "pickle",
    "shutil.rmtree",
    "tempfile.mktemp",
}

REVIEW_ORDER = {
    "imported_unverified": 0,
    "candidate": 1,
    "human_reviewed": 2,
    "official_docs_checked": 3,
    "promoted": 4,
    "deprecated": 0,
    "rejected": 0,
}

RISK_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


class PythonSchemaHardeningTests(unittest.TestCase):
    def test_schema_enums_contain_required_groups(self):
        enums = self._load_enums()
        self.assertEqual(REQUIRED_ENUM_GROUPS, set(enums))
        for values in enums.values():
            self.assertIsInstance(values, list)
            self.assertGreater(len(values), 0)

    def test_all_python_jsonl_files_are_valid(self):
        for path in self._jsonl_paths():
            self.assertGreater(len(self._load_jsonl(path)), 0, f"empty JSONL: {path}")

    def test_required_policy_fields_present(self):
        for path, record in self._all_records():
            self.assertIn("id", record, str(path))
            self.assertIn("review_status", record, record.get("id", str(path)))
            self.assertIn("execution_policy", record, record.get("id", str(path)))
            if REFERENCE_DIR in path.parents:
                self.assertIn("source_ref", record, record["id"])
                self.assertTrue(record["source_ref"], record["id"])

    def test_enum_values_are_valid_when_present(self):
        enums = self._load_enums()
        for _, record in self._all_records():
            for field, allowed in enums.items():
                if field in record:
                    self.assertIn(record[field], allowed, f"{record['id']} invalid {field}")

    def test_promoted_to_advisory_requires_promoted_review_status(self):
        for _, record in self._all_records():
            if record.get("promotion_status") == "promoted_to_advisory":
                self.assertEqual("promoted", record.get("review_status"), record["id"])

    def test_safe_to_execute_requires_review(self):
        allowed_statuses = {"human_reviewed", "official_docs_checked", "promoted"}
        for _, record in self._all_records():
            if record.get("execution_policy") == "safe_to_execute_in_test_sandbox":
                self.assertIn(record.get("review_status"), allowed_statuses, record["id"])

    def test_eval_and_exec_are_not_low_risk_or_sandbox_executable(self):
        for _, record in self._all_records():
            term = str(record.get("term", "")).lower()
            title = str(record.get("title", "")).lower()
            if term in {"eval", "exec"} or title in {"eval", "exec"}:
                self.assertNotEqual("low", record.get("risk_level"), record["id"])
                self.assertNotEqual(
                    "safe_to_execute_in_test_sandbox",
                    record.get("execution_policy"),
                    record["id"],
                )

    def test_no_python_jsonl_record_is_marked_promoted_during_h15(self):
        for _, record in self._all_records():
            self.assertNotEqual("promoted", record.get("review_status"), record["id"])
            self.assertNotEqual(
                "promoted_to_advisory",
                record.get("promotion_status"),
                record["id"],
            )

    def test_duplicate_ids_are_not_present(self):
        seen = {}
        for path, record in self._all_records():
            record_id = record["id"]
            self.assertNotIn(record_id, seen, f"duplicate id {record_id}: {path} and {seen.get(record_id)}")
            seen[record_id] = path

    def test_dangerous_functions_are_high_or_critical_when_detected(self):
        for _, record in self._all_records():
            haystack = " ".join(
                str(record.get(field, "")).lower()
                for field in ("id", "title", "term", "unsafe_or_wrong_pattern")
            )
            if "risk_level" in record and any(term in haystack for term in DANGEROUS_TERMS):
                self.assertGreaterEqual(
                    RISK_ORDER.get(record.get("risk_level", "low"), 0),
                    RISK_ORDER["high"],
                    record["id"],
                )

    def test_no_examples_executed_by_this_test_module(self):
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        forbidden_calls = {"eval", "exec"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, forbidden_calls)

    def _load_enums(self) -> dict:
        return json.loads(ENUMS_PATH.read_text(encoding="utf-8"))

    def _jsonl_paths(self) -> list[Path]:
        return sorted(
            path
            for path in PYTHON_KNOWLEDGE_DIR.rglob("*.jsonl")
            if OFFICIAL_DOCS_CROSSCHECK_DIR not in path.parents
        )

    def _all_records(self):
        for path in self._jsonl_paths():
            for record in self._load_jsonl(path):
                yield path, record

    def _load_jsonl(self, path: Path) -> list[dict]:
        records = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{path}:{line_number} invalid JSONL") from exc
        return records


if __name__ == "__main__":
    unittest.main()
