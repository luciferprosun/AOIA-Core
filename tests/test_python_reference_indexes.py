import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = PROJECT_ROOT / "knowledge" / "languages" / "python" / "reference"
KEYWORDS_PATH = REFERENCE_DIR / "keywords_index.jsonl"
BUILTINS_PATH = REFERENCE_DIR / "builtins_index.jsonl"


class PythonReferenceIndexesTests(unittest.TestCase):
    def test_keywords_index_is_valid_jsonl_with_required_policy_fields(self):
        records = self._load_jsonl(KEYWORDS_PATH)
        terms = {record["term"] for record in records}

        self.assertIn("match", terms)
        self.assertIn("case", terms)
        for record in records:
            self.assertIn("review_status", record)
            self.assertIn("execution_policy", record)
            self.assertIn("source_ref", record)
            self.assertEqual("reference_only_no_execution", record["execution_policy"])

    def test_builtins_index_is_valid_jsonl_with_required_policy_fields(self):
        records = self._load_jsonl(BUILTINS_PATH)
        terms = {record["term"] for record in records}

        self.assertIn("eval", terms)
        self.assertIn("exec", terms)
        self.assertIn("open", terms)
        for record in records:
            self.assertIn("review_status", record)
            self.assertIn("execution_policy", record)
            self.assertIn("source_ref", record)
            self.assertEqual("reference_only_no_execution", record["execution_policy"])

    def test_eval_and_exec_are_not_low_risk(self):
        records = {record["term"]: record for record in self._load_jsonl(BUILTINS_PATH)}

        self.assertNotEqual("low", records["eval"]["risk_level"])
        self.assertNotEqual("low", records["exec"]["risk_level"])

    def test_examples_are_reference_only_and_not_executed(self):
        for path in (KEYWORDS_PATH, BUILTINS_PATH):
            for record in self._load_jsonl(path):
                self.assertEqual("reference_only_no_execution", record["execution_policy"])
                self.assertIsInstance(record["example"], str)

    def _load_jsonl(self, path: Path) -> list[dict]:
        self.assertTrue(path.exists(), f"missing reference index: {path}")
        records = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{path}:{line_number} is not valid JSON") from exc
        self.assertGreater(len(records), 0)
        return records


if __name__ == "__main__":
    unittest.main()
