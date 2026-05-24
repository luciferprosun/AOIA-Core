import json
import tempfile
import unittest
from pathlib import Path

from knowledge.validator.validator import validate_path


VALID_ENTRY = {
    "id": "ls-command",
    "command": "ls",
    "description": "Lists directory contents.",
    "category": "filesystem",
    "tags": ["directory-listing", "read-only"],
    "risk": "low",
    "os": ["linux"],
    "shell": ["bash"],
    "examples": [
        {
            "input": "ls -la",
            "expected_effect": "Prints detailed directory contents.",
        }
    ],
}


class KnowledgeValidatorTests(unittest.TestCase):
    def test_valid_entry_passes(self) -> None:
        with knowledge_dir() as root:
            write_entry(root, "ls-command.json", VALID_ENTRY)
            report = validate_path(root)
            self.assertTrue(report.ok)
            self.assertEqual(report.checked_files, 1)

    def test_invalid_json_fails(self) -> None:
        with knowledge_dir() as root:
            (root / "examples" / "bad-json.json").write_text("{bad", encoding="utf-8")
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid JSON", report.message)

    def test_missing_required_field_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            del entry["risk"]
            write_entry(root, "missing-risk.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("missing required field: risk", report.message)

    def test_duplicate_command_fails(self) -> None:
        with knowledge_dir() as root:
            write_entry(root, "first-command.json", VALID_ENTRY)
            duplicate = dict(VALID_ENTRY)
            duplicate["id"] = "second-command"
            write_entry(root, "second-command.json", duplicate)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("duplicate command 'ls'", report.message)

    def test_invalid_tag_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            entry["tags"] = ["Read Only"]
            write_entry(root, "invalid-tag.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid tag", report.message)

    def test_invalid_risk_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            entry["risk"] = "extreme"
            write_entry(root, "invalid-risk.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid risk", report.message)

    def test_invalid_filename_fails(self) -> None:
        with knowledge_dir() as root:
            write_entry(root, "BadName.json", VALID_ENTRY)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid filename", report.message)

    def test_invalid_category_fails(self) -> None:
        with knowledge_dir() as root:
            entry = dict(VALID_ENTRY)
            entry["category"] = "misc"
            write_entry(root, "invalid-category.json", entry)
            report = validate_path(root)
            self.assertFalse(report.ok)
            self.assertIn("invalid category", report.message)


class knowledge_dir:
    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "knowledge"
        (self.root / "examples").mkdir(parents=True)
        return self.root

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tmp.cleanup()


def write_entry(root: Path, filename: str, entry: dict) -> None:
    (root / "examples" / filename).write_text(
        json.dumps(entry, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
