import json
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge" / "languages" / "python"

FORBIDDEN_CORRECTED_PATTERNS = (
    "eval(input(",
    "exec(input(",
    "os.system(",
    "os.popen(",
    "shell=True",
    "sudo pip install",
    "tempfile.mktemp(",
)

DELETE_PATTERNS = (
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
    "pathlib.Path.unlink",
)

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"password\s*=", re.IGNORECASE),
    re.compile(r"api_key\s*=", re.IGNORECASE),
    re.compile(r"secret\s*=", re.IGNORECASE),
)


class PythonDangerousPatternTests(unittest.TestCase):
    def test_corrected_patterns_do_not_contain_forbidden_execution_patterns(self):
        for record in self._all_records():
            corrected = str(record.get("corrected_pattern", ""))
            for pattern in FORBIDDEN_CORRECTED_PATTERNS:
                self.assertNotIn(pattern, corrected, record["id"])

    def test_pickle_mentions_include_untrusted_data_warning(self):
        for record in self._all_records():
            text = self._non_unsafe_text(record)
            if "pickle.load" in text or "pickle.loads" in text:
                notes = str(record.get("safety_notes", "")).lower()
                self.assertIn("untrusted", notes, record["id"])

    def test_destructive_file_operations_include_dry_run_or_confirmation(self):
        for record in self._all_records():
            text = self._non_unsafe_text(record)
            if any(pattern in text for pattern in DELETE_PATTERNS):
                notes = str(record.get("safety_notes", "")).lower()
                self.assertTrue(
                    "dry-run" in notes or "confirmation" in notes or "confirm" in notes,
                    record["id"],
                )

    def test_requests_mentions_include_timeout(self):
        for record in self._all_records():
            text = self._non_unsafe_text(record)
            if "requests.get" in text or "requests.post" in text:
                self.assertIn("timeout", text.lower(), record["id"])

    def test_no_obvious_secret_patterns_in_jsonl_fields(self):
        for record in self._all_records():
            text = self._all_string_text(record)
            for pattern in SECRET_PATTERNS:
                self.assertIsNone(pattern.search(text), record["id"])

    def _jsonl_paths(self) -> list[Path]:
        return sorted(PYTHON_KNOWLEDGE_DIR.rglob("*.jsonl"))

    def _all_records(self):
        for path in self._jsonl_paths():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)

    def _non_unsafe_text(self, record: dict) -> str:
        return " ".join(
            self._string_values(value)
            for key, value in record.items()
            if key != "unsafe_or_wrong_pattern"
        )

    def _all_string_text(self, record: dict) -> str:
        return " ".join(self._string_values(value) for value in record.values())

    def _string_values(self, value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return " ".join(self._string_values(item) for item in value)
        if isinstance(value, dict):
            return " ".join(self._string_values(item) for item in value.values())
        return ""


if __name__ == "__main__":
    unittest.main()
