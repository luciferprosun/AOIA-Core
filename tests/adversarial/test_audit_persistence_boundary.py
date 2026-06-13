from __future__ import annotations

import ast
import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.safety.audit_event_logger import (
    AUDIT_LOG_FILENAME,
    MAX_AUDIT_EVENT_JSONL_BYTES,
    AuditLogPathBlockedError,
    AuditLogSizeBlockedError,
    append_audit_event_jsonl,
)
from runtime.safety.audit_event_policy import AuditEventChainBlockedError
from runtime.schemas.action_proposal import create_human_review_only_proposal
from runtime.schemas.approval_decision import create_human_approval_decision
from runtime.schemas.audit_event import (
    AuditEvent,
    create_action_proposal_audit_event,
    create_approval_decision_audit_event,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_LOGGER_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "audit_event_logger.py"


class AuditPersistenceBoundaryTests(unittest.TestCase):
    def test_audit_log_is_created_in_explicit_temp_audit_directory(self) -> None:
        with TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir) / "audit"
            event = self.make_first_event()

            result = append_audit_event_jsonl(audit_dir, event)

            self.assertTrue(result.write_completed)
            self.assertEqual(Path(result.audit_log_path), audit_dir / AUDIT_LOG_FILENAME)
            self.assertTrue((audit_dir / AUDIT_LOG_FILENAME).is_file())

    def test_logger_writes_exactly_one_jsonl_line_per_event(self) -> None:
        with TemporaryDirectory() as tmpdir:
            event = self.make_first_event()

            append_audit_event_jsonl(Path(tmpdir), event)
            lines = self.read_lines(Path(tmpdir))

            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["event_hash"], event.event_hash)

    def test_second_event_appends_without_overwrite(self) -> None:
        with TemporaryDirectory() as tmpdir:
            first = self.make_first_event()
            second = self.make_second_event(first)

            append_audit_event_jsonl(Path(tmpdir), first)
            append_audit_event_jsonl(Path(tmpdir), second, expected_previous_hash=first.event_hash)
            lines = self.read_lines(Path(tmpdir))

            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["event_hash"], first.event_hash)
            self.assertEqual(json.loads(lines[1])["previous_event_hash"], first.event_hash)

    def test_existing_log_content_is_preserved(self) -> None:
        with TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir)
            first = self.make_first_event()
            second = self.make_second_event(first)

            append_audit_event_jsonl(audit_dir, first)
            first_line = self.read_lines(audit_dir)[0]
            append_audit_event_jsonl(audit_dir, second)

            self.assertEqual(self.read_lines(audit_dir)[0], first_line)

    def test_log_path_is_fixed_filename_not_caller_controlled(self) -> None:
        with TemporaryDirectory() as tmpdir:
            event = replace(self.make_first_event(), subject_id="../attempted-filename-injection")

            result = append_audit_event_jsonl(Path(tmpdir), event)

            self.assertEqual(Path(result.audit_log_path).name, AUDIT_LOG_FILENAME)
            self.assertFalse((Path(tmpdir) / "attempted-filename-injection").exists())

    def test_relative_audit_directory_is_rejected(self) -> None:
        with self.assertRaises(AuditLogPathBlockedError):
            append_audit_event_jsonl("relative-audit-dir", self.make_first_event())

    def test_symlink_audit_directory_is_rejected_when_supported(self) -> None:
        with TemporaryDirectory() as tmpdir, TemporaryDirectory() as outside:
            link_path = Path(tmpdir) / "audit-link"
            try:
                link_path.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            with self.assertRaises(AuditLogPathBlockedError):
                append_audit_event_jsonl(link_path, self.make_first_event())

    def test_symlink_log_escape_is_rejected_when_supported(self) -> None:
        with TemporaryDirectory() as tmpdir, TemporaryDirectory() as outside:
            audit_dir = Path(tmpdir) / "audit"
            audit_dir.mkdir()
            outside_log = Path(outside) / AUDIT_LOG_FILENAME
            log_path = audit_dir / AUDIT_LOG_FILENAME
            try:
                log_path.symlink_to(outside_log)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            with self.assertRaises(AuditLogPathBlockedError):
                append_audit_event_jsonl(audit_dir, self.make_first_event())
            self.assertFalse(outside_log.exists())

    def test_oversized_serialized_event_is_rejected_before_write(self) -> None:
        with TemporaryDirectory() as tmpdir:
            oversized = replace(self.make_first_event(), notes="x" * MAX_AUDIT_EVENT_JSONL_BYTES)

            with self.assertRaises(AuditLogSizeBlockedError):
                append_audit_event_jsonl(Path(tmpdir), oversized)

            self.assertFalse((Path(tmpdir) / AUDIT_LOG_FILENAME).exists())

    def test_fsync_path_is_exercised(self) -> None:
        calls = []

        def fake_fsync(fd: int) -> None:
            calls.append(fd)

        with TemporaryDirectory() as tmpdir, patch("runtime.safety.audit_event_logger.posix.fsync", fake_fsync):
            result = append_audit_event_jsonl(Path(tmpdir), self.make_first_event())

            self.assertTrue(result.fsync_completed)
            self.assertEqual(len(calls), 1)

    def test_invalid_event_object_is_rejected(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with self.assertRaises(TypeError):
                append_audit_event_jsonl(Path(tmpdir), object())

    def test_expected_previous_hash_mismatch_is_rejected(self) -> None:
        with TemporaryDirectory() as tmpdir:
            first = self.make_first_event()
            second = self.make_second_event(first)

            append_audit_event_jsonl(Path(tmpdir), first)
            with self.assertRaises(AuditEventChainBlockedError):
                append_audit_event_jsonl(Path(tmpdir), second, expected_previous_hash="wrong")

    def test_existing_log_previous_hash_mismatch_is_rejected(self) -> None:
        with TemporaryDirectory() as tmpdir:
            first = self.make_first_event()
            bad_second = replace(self.make_second_event(first), previous_event_hash="wrong")

            append_audit_event_jsonl(Path(tmpdir), first)
            with self.assertRaises(AuditEventChainBlockedError):
                append_audit_event_jsonl(Path(tmpdir), bad_second)
            self.assertEqual(len(self.read_lines(Path(tmpdir))), 1)

    def test_runtime_does_not_add_forbidden_capabilities(self) -> None:
        forbidden_modules = {
            "subprocess",
            "pty",
            "pexpect",
            "requests",
            "urllib",
            "http.client",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "openai",
            "anthropic",
            "google.cloud",
            "google.generativeai",
            "dotenv",
            "sqlite3",
            "shutil",
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
            "os.environ",
            "safe_file_writer",
            "workspace_registry",
        )

        source = AUDIT_LOGGER_RUNTIME_FILE.read_text(encoding="utf-8")
        for term in forbidden_text:
            self.assertNotIn(term, source)
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for module_name in imports:
            self.assertNotIn(module_name, forbidden_modules)
            self.assertFalse(any(module_name == item or module_name.startswith(item + ".") for item in forbidden_modules))

    def make_first_event(self) -> AuditEvent:
        proposal = create_human_review_only_proposal(
            title="Durable audit",
            description="Record first audit event.",
            proposed_by="unit-test",
            payload_summary="summary",
            exact_payload="payload",
            proposal_id="proposal-audit-persistence",
        )
        return create_action_proposal_audit_event(proposal)

    def make_second_event(self, first: AuditEvent) -> AuditEvent:
        proposal = create_human_review_only_proposal(
            title="Durable audit",
            description="Record second audit event.",
            proposed_by="unit-test",
            payload_summary="summary",
            exact_payload="payload",
            proposal_id="proposal-audit-persistence",
        )
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved for audit")
        return create_approval_decision_audit_event(decision, previous_event_hash=first.event_hash)

    def read_lines(self, audit_dir: Path) -> list[str]:
        return (audit_dir / AUDIT_LOG_FILENAME).read_text(encoding="utf-8").splitlines()


if __name__ == "__main__":
    unittest.main()
