from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.cpt.audit import append_transformation_record
from runtime.cpt.transformer import transform_prompt


class CptAuditTests(unittest.TestCase):
    def test_explicit_append_writes_one_jsonl_line(self) -> None:
        record = transform_prompt("Review this migration.")
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "cpt" / "audit.jsonl"

            append_transformation_record(record, audit_path)

            lines = audit_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, len(lines))
            self.assertEqual(record.transformation_id, json.loads(lines[0])["transformation_id"])

    def test_second_append_adds_line_and_does_not_overwrite(self) -> None:
        first = transform_prompt("Review first.")
        second = transform_prompt("Review second.")
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.jsonl"

            append_transformation_record(first, audit_path)
            append_transformation_record(second, audit_path)

            lines = audit_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(2, len(lines))
            self.assertEqual(first.transformation_id, json.loads(lines[0])["transformation_id"])
            self.assertEqual(second.transformation_id, json.loads(lines[1])["transformation_id"])

    def test_audit_writer_does_not_mutate_record(self) -> None:
        record = transform_prompt("Review immutable behavior.")
        before = record.to_dict()
        with tempfile.TemporaryDirectory() as temp_dir:
            append_transformation_record(record, Path(temp_dir) / "audit.jsonl")

        self.assertEqual(before, record.to_dict())

    def test_audit_writer_respects_user_provided_path(self) -> None:
        record = transform_prompt("Review path handling.")
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "nested" / "chosen.jsonl"

            append_transformation_record(record, audit_path)

            self.assertTrue(audit_path.exists())
            self.assertFalse((Path(temp_dir) / "audit.jsonl").exists())

    def test_directory_path_is_rejected(self) -> None:
        record = transform_prompt("Review directory path handling.")
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "file path"):
                append_transformation_record(record, Path(temp_dir))

    def test_parent_directory_traversal_path_is_rejected(self) -> None:
        record = transform_prompt("Review traversal path handling.")

        with self.assertRaisesRegex(ValueError, "traversal"):
            append_transformation_record(record, Path("audit") / ".." / "cpt.jsonl")

    def test_invalid_status_is_rejected(self) -> None:
        record = transform_prompt("Review audit status.")
        forged = object.__new__(type(record))
        for field, value in record.to_dict().items():
            object.__setattr__(forged, field, value)
        object.__setattr__(forged, "canonical_status", "CANONICAL")

        with self.assertRaises(ValueError):
            replace(record, canonical_status="CANONICAL")
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                append_transformation_record(forged, Path(temp_dir) / "audit.jsonl")


if __name__ == "__main__":
    unittest.main()
