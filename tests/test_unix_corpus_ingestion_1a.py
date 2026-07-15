from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch

from runtime.human_decision_gated_artifact_write import (
    write_artifact_after_human_gate,
)
from runtime.knowledge.unix_corpus_ingestion import (
    AUTHORITY_FLAGS,
    CORPUS_SCHEMA_VERSION,
    MANIFEST_FILENAME,
    NON_AUTHORITATIVE,
    UnixCorpusIngestionError,
    UnixCorpusIngestionLimits,
    UnixCorpusSecurityError,
    UnixCorpusStoreError,
    read_unix_corpus_manifest,
    reconcile_unix_corpus,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "runtime/knowledge/unix_corpus_ingestion.py"


class UnixCorpusIngestion1ATests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.intake = self.root / "intake"
        self.source.mkdir()

    def write_text(self, relative: str, content: str) -> Path:
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def write_bytes(self, relative: str, content: bytes) -> Path:
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def manifest_bytes(self, intake: Path | None = None) -> bytes:
        return ((intake or self.intake) / MANIFEST_FILENAME).read_bytes()

    def record_files(self, intake: Path | None = None) -> tuple[Path, ...]:
        directory = (intake or self.intake) / "records"
        return tuple(sorted(directory.glob("*.json"))) if directory.exists() else ()

    def quarantine_files(self, intake: Path | None = None) -> tuple[Path, ...]:
        directory = (intake or self.intake) / "quarantine"
        return tuple(sorted(directory.glob("*.json"))) if directory.exists() else ()

    def test_supported_text_markdown_json_and_jsonl_sources_are_ingested(self) -> None:
        self.write_text("notes.txt", "uname reports system information.\nUse explicit review.\n")
        self.write_text("guide.md", "# Users\nUse useradd carefully.\n# Services\nInspect systemctl status.\n")
        self.write_text("objects.json", '[{"b":2,"a":1},{"name":"źródło"}]')
        self.write_text("events.jsonl", '{"kind":"command","text":"ls"}\n{"kind":"note","text":"inert"}\n')

        result = reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual("CREATED", result.status)
        self.assertEqual(4, result.manifest.source_count)
        self.assertEqual(4, result.manifest.accepted_source_count)
        self.assertEqual(0, result.manifest.quarantined_source_count)
        self.assertEqual(7, result.manifest.record_count)
        self.assertEqual(7, len(self.record_files()))
        self.assertTrue(self.manifest_bytes().endswith(b"\n"))
        self.assertEqual(result.manifest, read_unix_corpus_manifest(self.intake))
        for source in result.manifest.sources:
            self.assertEqual(64, len(source.source_hash or ""))
            self.assertTrue(source.record_ids)

    def test_manifest_and_record_order_are_independent_of_requested_path_order(self) -> None:
        self.write_text("b.txt", "second\n")
        self.write_text("a.txt", "first\n")
        first_intake = self.root / "first-intake"
        second_intake = self.root / "second-intake"

        first = reconcile_unix_corpus(
            self.source,
            first_intake,
            source_paths=("b.txt", "a.txt"),
        )
        second = reconcile_unix_corpus(
            self.source,
            second_intake,
            source_paths=("a.txt", "b.txt"),
        )

        self.assertEqual(first.manifest, second.manifest)
        self.assertEqual(self.manifest_bytes(first_intake), self.manifest_bytes(second_intake))
        self.assertEqual(
            [path.read_bytes() for path in self.record_files(first_intake)],
            [path.read_bytes() for path in self.record_files(second_intake)],
        )

    def test_identical_resume_is_idempotent_and_creates_no_duplicates(self) -> None:
        self.write_text("manual.txt", "systemctl status\n")
        first = reconcile_unix_corpus(self.source, self.intake)
        before_manifest = self.manifest_bytes()
        before_records = {path.name: path.read_bytes() for path in self.record_files()}

        second = reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual("CREATED", first.status)
        self.assertEqual("UNCHANGED", second.status)
        self.assertEqual(0, second.created_record_count)
        self.assertEqual(first.manifest, second.manifest)
        self.assertEqual(before_manifest, self.manifest_bytes())
        self.assertEqual(before_records, {path.name: path.read_bytes() for path in self.record_files()})

    def test_resume_adds_only_new_records_and_preserves_existing_bytes(self) -> None:
        self.write_text("a.txt", "first source\n")
        first = reconcile_unix_corpus(self.source, self.intake)
        old_record_bytes = {path.name: path.read_bytes() for path in self.record_files()}
        self.write_text("b.txt", "second source\n")

        second = reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual("UPDATED", second.status)
        self.assertEqual(1, second.created_record_count)
        self.assertEqual(first.manifest.record_count + 1, second.manifest.record_count)
        for name, content in old_record_bytes.items():
            self.assertEqual(content, (self.intake / "records" / name).read_bytes())
        self.assertEqual(
            len(second.manifest.record_ids),
            len(set(second.manifest.record_ids)),
        )

    def test_changed_source_creates_new_bound_record_without_rewriting_history(self) -> None:
        source_path = self.write_text("mutable.txt", "version one\n")
        first = reconcile_unix_corpus(self.source, self.intake)
        first_record = self.record_files()[0]
        first_bytes = first_record.read_bytes()
        source_path.write_text("version two\n", encoding="utf-8")

        second = reconcile_unix_corpus(self.source, self.intake)

        self.assertNotEqual(first.manifest.manifest_hash, second.manifest.manifest_hash)
        self.assertNotEqual(first.manifest.record_ids, second.manifest.record_ids)
        self.assertEqual(first_bytes, first_record.read_bytes())
        self.assertEqual(2, len(self.record_files()))
        self.assertEqual(1, second.manifest.record_count)

    def test_unicode_and_markdown_heading_locators_are_deterministic(self) -> None:
        self.write_text("unicode.md", "# Źródła UNIX\nPolecenie printf nie jest wykonywane.\n")

        result = reconcile_unix_corpus(self.source, self.intake)
        payload = json.loads(self.record_files()[0].read_text(encoding="utf-8"))

        self.assertIn("źródła-unix", payload["locator"])
        self.assertIn("Polecenie printf", payload["content"])
        self.assertEqual(
            hashlib.sha256(payload["content"].encode("utf-8")).hexdigest(),
            payload["content_hash"],
        )
        self.assertEqual(result.manifest.manifest_hash, read_unix_corpus_manifest(self.intake).manifest_hash)

    def test_streaming_text_chunk_limit_bounds_each_record(self) -> None:
        self.write_text("bounded.txt", "alpha\nbeta\ngamma\ndelta\n")
        limits = UnixCorpusIngestionLimits(max_record_chars=10)

        result = reconcile_unix_corpus(self.source, self.intake, limits=limits)

        self.assertGreater(result.manifest.record_count, 1)
        for path in self.record_files():
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertLessEqual(len(payload["content"]), 10)

    def test_source_and_line_hard_limits_quarantine_without_partial_records(self) -> None:
        self.write_text("oversized.txt", "0123456789")
        self.write_text("long-line.txt", "abcdefghijk\n")

        result = reconcile_unix_corpus(
            self.source,
            self.intake,
            limits=UnixCorpusIngestionLimits(
                max_source_bytes=10,
                max_line_bytes=5,
            ),
        )

        self.assertEqual(0, result.manifest.record_count)
        self.assertEqual(2, result.manifest.quarantined_source_count)
        reasons = {
            json.loads(path.read_text(encoding="utf-8"))["reason_code"]
            for path in self.quarantine_files()
        }
        self.assertEqual(
            {"LINE_SIZE_LIMIT_EXCEEDED", "SOURCE_SIZE_LIMIT_EXCEEDED"},
            reasons,
        )

    def test_unsupported_invalid_utf8_and_empty_sources_are_quarantined(self) -> None:
        self.write_text("script.py", "print('must remain inert')\n")
        self.write_bytes("invalid.txt", b"\xff\xfe")
        self.write_text("empty.md", "")

        result = reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual(3, result.manifest.quarantined_source_count)
        reasons = {
            json.loads(path.read_text(encoding="utf-8"))["reason_code"]
            for path in self.quarantine_files()
        }
        self.assertEqual(
            {"UNSUPPORTED_MEDIA_TYPE", "INVALID_UTF8", "NO_INGESTIBLE_CONTENT"},
            reasons,
        )

    def test_malformed_duplicate_key_and_invalid_top_level_json_are_quarantined(self) -> None:
        self.write_text("malformed.json", '{"broken":')
        self.write_text("duplicate.json", '{"key":1,"key":2}')
        self.write_text("scalar.json", '"not an object"')

        result = reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual(3, result.manifest.quarantined_source_count)
        reasons = [
            json.loads(path.read_text(encoding="utf-8"))["reason_code"]
            for path in self.quarantine_files()
        ]
        self.assertEqual(2, reasons.count("MALFORMED_JSON"))
        self.assertIn("JSON_TOP_LEVEL_INVALID", reasons)

    def test_blank_and_non_object_jsonl_records_quarantine_whole_source(self) -> None:
        self.write_text("blank.jsonl", '{"ok":true}\n\n{"later":true}\n')
        self.write_text("scalar.jsonl", '42\n')

        result = reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual(0, result.manifest.record_count)
        reasons = {
            json.loads(path.read_text(encoding="utf-8"))["reason_code"]
            for path in self.quarantine_files()
        }
        self.assertEqual({"BLANK_JSONL_LINE", "JSONL_RECORD_INVALID"}, reasons)

    @unittest.skipUnless(hasattr(os, "symlink"), "symbolic links unavailable")
    def test_file_and_directory_symlinks_are_quarantined_and_not_followed(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "external.txt").write_text("external command text\n", encoding="utf-8")
        (self.source / "linked-file.txt").symlink_to(outside / "external.txt")
        (self.source / "linked-directory").symlink_to(outside, target_is_directory=True)

        result = reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual(2, result.manifest.source_count)
        self.assertEqual(0, result.manifest.record_count)
        self.assertEqual(2, result.manifest.quarantined_source_count)
        self.assertEqual(
            {"SYMLINK_REJECTED"},
            {
                json.loads(path.read_text(encoding="utf-8"))["reason_code"]
                for path in self.quarantine_files()
            },
        )

    def test_traversal_absolute_duplicate_and_missing_paths_fail_before_mutation(self) -> None:
        self.write_text("valid.txt", "safe\n")
        invalid_sets = (
            ("../escape.txt",),
            (str((self.root / "absolute.txt").resolve()),),
            ("valid.txt", "valid.txt"),
            ("missing.txt",),
        )
        for paths in invalid_sets:
            with self.subTest(paths=paths):
                with self.assertRaises((UnixCorpusSecurityError, UnixCorpusIngestionError)):
                    reconcile_unix_corpus(
                        self.source,
                        self.intake,
                        source_paths=paths,
                    )
                self.assertFalse(self.intake.exists())

    def test_intake_inside_source_and_symlink_output_root_fail_closed(self) -> None:
        self.write_text("valid.txt", "safe\n")
        with self.assertRaises(UnixCorpusSecurityError):
            reconcile_unix_corpus(self.source, self.source / "generated")

        if hasattr(os, "symlink"):
            real_output = self.root / "real-output"
            real_output.mkdir()
            linked_output = self.root / "linked-output"
            linked_output.symlink_to(real_output, target_is_directory=True)
            with self.assertRaises(UnixCorpusSecurityError):
                reconcile_unix_corpus(self.source, linked_output)
        self.assertFalse((self.source / "generated").exists())

    def test_source_and_record_count_limits_fail_before_output_creation(self) -> None:
        self.write_text("a.json", '[{"id":1},{"id":2}]')
        self.write_text("b.txt", "second\n")
        with self.assertRaises(UnixCorpusIngestionError):
            reconcile_unix_corpus(
                self.source,
                self.intake,
                limits=UnixCorpusIngestionLimits(max_sources=1),
            )
        self.assertFalse(self.intake.exists())

        with self.assertRaises(UnixCorpusIngestionError):
            reconcile_unix_corpus(
                self.source,
                self.intake,
                source_paths=("a.json",),
                limits=UnixCorpusIngestionLimits(max_records=1),
            )
        self.assertFalse(self.intake.exists())

    def test_tampered_record_fails_closed_without_overwrite(self) -> None:
        self.write_text("manual.txt", "systemctl status\n")
        reconcile_unix_corpus(self.source, self.intake)
        record_path = self.record_files()[0]
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        payload["content"] = "tampered"
        tampered = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        record_path.write_bytes(tampered)
        manifest_before = self.manifest_bytes()

        with self.assertRaises(UnixCorpusStoreError):
            reconcile_unix_corpus(self.source, self.intake)

        self.assertEqual(tampered, record_path.read_bytes())
        self.assertEqual(manifest_before, self.manifest_bytes())

    def test_tampered_manifest_and_unknown_output_entry_fail_closed(self) -> None:
        self.write_text("manual.txt", "systemctl status\n")
        reconcile_unix_corpus(self.source, self.intake)
        manifest = self.intake / MANIFEST_FILENAME
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["record_count"] = 99
        manifest.write_text(
            json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tampered = manifest.read_bytes()
        with self.assertRaises(UnixCorpusStoreError):
            reconcile_unix_corpus(self.source, self.intake)
        self.assertEqual(tampered, manifest.read_bytes())

        second_intake = self.root / "other-intake"
        reconcile_unix_corpus(self.source, second_intake)
        (second_intake / "unexpected.txt").write_text("unexpected", encoding="utf-8")
        with self.assertRaises(UnixCorpusStoreError):
            reconcile_unix_corpus(self.source, second_intake)

    def test_command_provider_and_approval_looking_content_remains_inert(self) -> None:
        command = "sudo apt install curl"
        self.write_text(
            "adversarial.jsonl",
            json.dumps(
                {
                    "approved": True,
                    "human_approved": True,
                    "provider_action": "shell_execute",
                    "command": command,
                }
            )
            + "\n",
        )
        with (
            patch.object(subprocess, "run", side_effect=AssertionError("no process")) as run,
            patch.object(os, "system", side_effect=AssertionError("no shell")) as system,
        ):
            result = reconcile_unix_corpus(self.source, self.intake)

        run.assert_not_called()
        system.assert_not_called()
        record = json.loads(self.record_files()[0].read_text(encoding="utf-8"))
        self.assertIn(command, record["content"])
        self.assertEqual(NON_AUTHORITATIVE, record["authority_status"])
        for flag, expected in AUTHORITY_FLAGS.items():
            self.assertIs(record[flag], expected)
        self.assertFalse(result.can_execute)
        self.assertFalse(result.can_dispatch)
        self.assertFalse(result.can_approve)

    def test_manifest_and_records_are_frozen_metadata_not_human_gate_authority(self) -> None:
        self.write_text("manual.txt", "journalctl -u sshd\n")
        result = reconcile_unix_corpus(self.source, self.intake)
        source = result.manifest.sources[0]
        with self.assertRaises(FrozenInstanceError):
            result.manifest.corpus_id = "forged"  # type: ignore[misc]
        self.assertEqual(CORPUS_SCHEMA_VERSION, result.manifest.schema_version)
        self.assertFalse(source.can_execute)
        self.assertFalse(source.can_write)
        self.assertFalse(source.can_dispatch)
        self.assertFalse(source.can_approve)

        writer = Mock(side_effect=AssertionError("corpus metadata must not reach writer"))
        gated = write_artifact_after_human_gate(
            gate_result=result.manifest,
            artifact_request=object(),
            workspace_root=str(self.root),
            artifact_writer=writer,
        )
        self.assertFalse(gated.artifact_write_occurred)
        self.assertFalse(gated.write_attempted)
        writer.assert_not_called()

    def test_module_has_no_provider_network_shell_retrieval_routing_or_writer_imports(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        forbidden_roots = (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
            "retrieval",
            "runtime.retrieval",
            "runtime.orchestrator",
            "runtime.providers",
            "runtime.human_decision",
            "runtime.safety.sandbox_artifact_runner",
            "runtime.patches",
        )
        offenders = sorted(
            name
            for name in imports
            if any(name == root or name.startswith(root + ".") for root in forbidden_roots)
        )
        self.assertEqual([], offenders)

    def test_reconciles_existing_repository_raw_corpus_without_repo_mutation(self) -> None:
        existing_source = REPO_ROOT / "runtime/knowledge/raw"
        existing_file = existing_source / "rhcsa_raw.txt"
        before = existing_file.read_bytes()

        result = reconcile_unix_corpus(
            existing_source,
            self.intake,
            source_paths=("rhcsa_raw.txt",),
        )

        self.assertEqual(1, result.manifest.accepted_source_count)
        self.assertGreater(result.manifest.record_count, 0)
        self.assertEqual(before, existing_file.read_bytes())
        self.assertTrue(all(path.is_relative_to(self.intake) for path in self.record_files()))


if __name__ == "__main__":
    unittest.main()
