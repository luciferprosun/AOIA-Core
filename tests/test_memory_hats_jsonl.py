import ast
import importlib
import inspect
import json
import unittest

from runtime.memory_hats import (
    PheromoneTag,
    ReviewStatus,
    TagType,
    export_tags_to_jsonl,
    import_tags_from_jsonl,
    tag_from_jsonl_record,
    tag_to_jsonl_record,
)


class MemoryHatsJsonlTests(unittest.TestCase):
    def _tag(
        self,
        fingerprint_hash: str = "hash-1",
        review_status: ReviewStatus = ReviewStatus.CONFIRMED,
    ) -> PheromoneTag:
        return PheromoneTag(
            fingerprint_hash=fingerprint_hash,
            hat_id="linux_rhcsa",
            path="linux_rhcsa/command_grammar/unsupported_linux_command/dnf_status_sshd",
            tag_type=TagType.UNSUPPORTED_LINUX_COMMAND,
            normalized_trigger="dnf status sshd",
            correction_text="Use systemctl status sshd for service status checks.",
            evidence_refs=["man systemctl", "man dnf"],
            review_status=review_status,
            seen_count=3,
            hat_version="v0.1",
            created_by="manual",
            first_seen="2026-06-01T00:00:00Z",
            last_seen="2026-06-01T00:01:00Z",
            notes="local test tag",
        )

    def test_tag_to_jsonl_record_returns_json_compatible_dict(self):
        record = tag_to_jsonl_record(self._tag())

        self.assertIsInstance(record, dict)
        json.dumps(record)
        self.assertEqual("unsupported_linux_command", record["tag_type"])
        self.assertEqual("confirmed", record["review_status"])

    def test_tag_from_jsonl_record_round_trips_confirmed_tag(self):
        original = self._tag()
        restored = tag_from_jsonl_record(tag_to_jsonl_record(original))

        self.assertEqual(original.to_dict(), restored.to_dict())
        self.assertEqual(ReviewStatus.CONFIRMED, restored.review_status)

    def test_evidence_refs_are_copied_and_independent(self):
        record = tag_to_jsonl_record(self._tag())
        restored = tag_from_jsonl_record(record)

        record["evidence_refs"].append("changed record")
        restored.evidence_refs.append("changed tag")

        self.assertEqual(["man systemctl", "man dnf", "changed record"], record["evidence_refs"])
        self.assertEqual(["man systemctl", "man dnf", "changed tag"], restored.evidence_refs)

    def test_export_tags_to_jsonl_exports_one_json_object_per_line(self):
        text = export_tags_to_jsonl(
            [
                self._tag("hash-1"),
                self._tag("hash-2", review_status=ReviewStatus.CANDIDATE),
            ]
        )

        lines = text.strip().splitlines()
        self.assertEqual(2, len(lines))
        self.assertEqual("hash-1", json.loads(lines[0])["fingerprint_hash"])
        self.assertEqual("hash-2", json.loads(lines[1])["fingerprint_hash"])

    def test_import_tags_from_jsonl_imports_multiple_tags(self):
        tags = [self._tag("hash-1"), self._tag("hash-2")]
        text = export_tags_to_jsonl(tags)

        restored = import_tags_from_jsonl(text)

        self.assertEqual(["hash-1", "hash-2"], [tag.fingerprint_hash for tag in restored])

    def test_import_tags_from_jsonl_ignores_blank_lines(self):
        text = "\n" + export_tags_to_jsonl([self._tag()]) + "\n\n"

        restored = import_tags_from_jsonl(text)

        self.assertEqual(1, len(restored))
        self.assertEqual("hash-1", restored[0].fingerprint_hash)

    def test_malformed_jsonl_raises_value_error(self):
        with self.assertRaises(ValueError):
            import_tags_from_jsonl("{not-json}\n")

    def test_missing_required_field_raises_value_error(self):
        record = tag_to_jsonl_record(self._tag())
        del record["path"]

        with self.assertRaises(ValueError):
            tag_from_jsonl_record(record)

    def test_invalid_enum_string_raises_value_error(self):
        record = tag_to_jsonl_record(self._tag())
        record["tag_type"] = "not_a_real_tag_type"

        with self.assertRaises(ValueError):
            tag_from_jsonl_record(record)

    def test_export_import_preserves_core_fields(self):
        original = self._tag()

        restored = import_tags_from_jsonl(export_tags_to_jsonl([original]))[0]

        self.assertEqual(original.fingerprint_hash, restored.fingerprint_hash)
        self.assertEqual(original.hat_id, restored.hat_id)
        self.assertEqual(original.path, restored.path)
        self.assertEqual(original.tag_type, restored.tag_type)
        self.assertEqual(original.normalized_trigger, restored.normalized_trigger)
        self.assertEqual(original.correction_text, restored.correction_text)
        self.assertEqual(original.evidence_refs, restored.evidence_refs)
        self.assertEqual(original.review_status, restored.review_status)
        self.assertEqual(original.seen_count, restored.seen_count)

    def test_import_does_not_touch_sqlite_or_storage(self):
        module = importlib.import_module("runtime.memory_hats.jsonl")
        source = inspect.getsource(module)

        self.assertNotIn("SQLiteTagStore", source)
        self.assertNotIn("sqlite3", source)
        self.assertNotIn("runtime.memory_hats.storage", source)

    def test_module_has_no_storage_rhcsa_process_or_network_imports(self):
        module = importlib.import_module("runtime.memory_hats.jsonl")
        tree = ast.parse(inspect.getsource(module))
        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)

        forbidden_imports = {
            "sqlite3",
            "subprocess",
            "socket",
            "http.client",
            "urllib",
            "urllib.request",
            "requests",
            "httpx",
            "runtime.memory_hats.storage",
            "runtime.tools.command_grammar",
            "runtime.commands",
            "runtime.router",
            "runtime.providers",
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported_names))


if __name__ == "__main__":
    unittest.main()
