import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge" / "languages" / "python"
EXAMPLES_PATH = PYTHON_KNOWLEDGE_DIR / "examples.jsonl"

REQUIRED_FIELDS = {
    "id",
    "title",
    "domain",
    "difficulty",
    "tags",
    "unsafe_or_wrong_pattern",
    "corrected_pattern",
    "explanation",
    "safety_notes",
    "verification_steps",
    "related_linux_rhcsa_links",
    "review_status",
    "evidence_refs",
    "execution_policy",
}


class PythonKnowledgeScaffoldTests(unittest.TestCase):
    def test_python_knowledge_scaffold_files_exist(self):
        self.assertTrue((PYTHON_KNOWLEDGE_DIR / "README.md").exists())
        self.assertTrue((PYTHON_KNOWLEDGE_DIR / "corpus_schema.md").exists())
        self.assertTrue((PYTHON_KNOWLEDGE_DIR / "examples.jsonl").exists())
        self.assertTrue((PYTHON_KNOWLEDGE_DIR / "AUDIT_NOTES.md").exists())

    def test_examples_jsonl_contains_exactly_three_records(self):
        records = self._load_records()
        self.assertEqual(3, len(records))

    def test_example_records_have_required_fields(self):
        for record in self._load_records():
            self.assertEqual(REQUIRED_FIELDS, set(record))
            self.assertEqual("candidate", record["review_status"])
            self.assertEqual("advisory_only_no_execution", record["execution_policy"])
            self.assertIsInstance(record["tags"], list)
            self.assertIsInstance(record["verification_steps"], list)
            self.assertIsInstance(record["related_linux_rhcsa_links"], list)
            self.assertIsInstance(record["evidence_refs"], list)

    def test_examples_cover_expected_python_topics(self):
        records = {record["id"]: record for record in self._load_records()}
        self.assertIn("python-subprocess-shell-true-user-input", records)
        self.assertIn("python-unsafe-file-overwrite", records)
        self.assertIn("python-global-pip-externally-managed", records)
        self.assertIn("shell=True", records["python-subprocess-shell-true-user-input"]["unsafe_or_wrong_pattern"])
        self.assertIn("open(path, \"w\")", records["python-unsafe-file-overwrite"]["unsafe_or_wrong_pattern"])
        self.assertIn("python3 -m venv .venv", records["python-global-pip-externally-managed"]["corrected_pattern"])

    def _load_records(self) -> list[dict]:
        lines = [
            line.strip()
            for line in EXAMPLES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return [json.loads(line) for line in lines]


if __name__ == "__main__":
    unittest.main()
