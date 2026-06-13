from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.approval_decision import ApprovalDecisionType
from runtime.schemas.audit_event import AuditEventType
from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import capture_human_decision
from runtime.safety import dry_run_artifact_integration, local_agent_entrypoint, sandbox_artifact_runner
from runtime.safety.approval_decision_audit_handoff import (
    ApprovalDecisionAuditHandoffResult,
    record_approval_decision_to_durable_audit,
)
from runtime.safety.audit_event_logger import AUDIT_LOG_FILENAME
from runtime.safety.human_decision_to_approval_policy import create_approval_decision_from_human_capture


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "approval_decision_audit_handoff.py"


class Macrostep5DApprovalDecisionAuditHandoffTests(unittest.TestCase):
    def test_handoff_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(record_approval_decision_to_durable_audit))

    def test_handoff_consumes_valid_approval_decision(self) -> None:
        with TemporaryDirectory() as tmpdir:
            decision = self.make_approval_decision("approve")

            result = record_approval_decision_to_durable_audit(
                approval_decision=decision,
                audit_dir=Path(tmpdir),
            )

        self.assertIsInstance(result, ApprovalDecisionAuditHandoffResult)
        self.assertTrue(result.completed)
        self.assertEqual(result.approval_decision_id, decision.decision_id)

    def test_handoff_requires_explicit_absolute_audit_directory(self) -> None:
        with self.assertRaises(ValueError):
            record_approval_decision_to_durable_audit(
                approval_decision=self.make_approval_decision("approve"),
                audit_dir="relative-audit",
            )

    def test_handoff_writes_one_durable_audit_jsonl_line(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_approval_decision("approve"),
                audit_dir=Path(tmpdir),
            )
            lines = (Path(tmpdir) / AUDIT_LOG_FILENAME).read_text(encoding="utf-8").splitlines()

        self.assertTrue(result.completed)
        self.assertEqual(len(lines), 1)
        decoded = json.loads(lines[0])
        self.assertEqual(decoded["event_id"], result.audit_event_id)
        self.assertEqual(decoded["event_hash"], result.audit_event_hash)

    def test_handoff_uses_existing_audit_logger_and_inherits_fsync(self) -> None:
        calls = []

        def fake_fsync(fd: int) -> None:
            calls.append(fd)

        with TemporaryDirectory() as tmpdir, patch("runtime.safety.audit_event_logger.posix.fsync", fake_fsync):
            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_approval_decision("approve"),
                audit_dir=Path(tmpdir),
            )

        self.assertTrue(result.completed)
        self.assertEqual(len(calls), 1)

    def test_handoff_supports_approve_decision(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_approval_decision("approve"),
                audit_dir=Path(tmpdir),
            )
            event = self.read_first_event(Path(tmpdir))

        self.assertTrue(result.completed)
        self.assertEqual(result.approval_decision_type, "APPROVE")
        self.assertEqual(event["result"], "APPROVE")

    def test_handoff_supports_reject_decision(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_approval_decision("deny"),
                audit_dir=Path(tmpdir),
            )
            event = self.read_first_event(Path(tmpdir))

        self.assertTrue(result.completed)
        self.assertEqual(result.approval_decision_type, "REJECT")
        self.assertEqual(event["result"], "REJECT")

    def test_handoff_preserves_decision_id_type_and_provenance_in_event(self) -> None:
        with TemporaryDirectory() as tmpdir:
            decision = self.make_approval_decision("approve")
            result = record_approval_decision_to_durable_audit(
                approval_decision=decision,
                audit_dir=Path(tmpdir),
            )
            event = self.read_first_event(Path(tmpdir))

        self.assertEqual(event["event_type"], AuditEventType.APPROVAL_DECISION_RECORDED.value)
        self.assertEqual(event["subject_id"], decision.decision_id)
        self.assertEqual(event["subject_type"], "ApprovalDecision")
        self.assertEqual(event["actor_id"], decision.actor_id)
        self.assertEqual(event["result"], decision.decision_type.value)
        self.assertEqual(event["payload_hash"], result.approval_decision_payload_hash)
        self.assertIn("review_packet_id=", event["notes"])
        self.assertIn("human_decision_capture_id=", event["notes"])

    def test_handoff_result_contains_expected_fields(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_approval_decision("approve"),
                audit_dir=Path(tmpdir),
            )

        self.assertTrue(result.completed)
        self.assertTrue(result.audit_log_path)
        self.assertTrue(result.audit_event_id)
        self.assertTrue(result.audit_event_hash)
        self.assertTrue(result.approval_decision_id)
        self.assertEqual(result.reason, "approval decision recorded to durable audit")

    def test_handoff_does_not_write_artifacts_or_call_agent_paths(self) -> None:
        with TemporaryDirectory() as tmpdir, TemporaryDirectory() as unrelated:
            before = self.snapshot(unrelated)
            with patch.object(
                sandbox_artifact_runner,
                "write_sandbox_artifact",
                side_effect=AssertionError("handoff must not write artifacts"),
            ), patch.object(
                local_agent_entrypoint,
                "run_durable_local_agent_entrypoint",
                side_effect=AssertionError("handoff must not run local entrypoint"),
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("handoff must not use old non-durable path"),
            ):
                record_approval_decision_to_durable_audit(
                    approval_decision=self.make_approval_decision("approve"),
                    audit_dir=Path(tmpdir),
                )
            after = self.snapshot(unrelated)

        self.assertEqual(before, after)

    def test_handoff_runtime_does_not_call_forbidden_capabilities(self) -> None:
        self.assert_runtime_file_does_not_call_forbidden_capabilities()

    def make_approval_decision(self, capture_decision: str):
        packet = create_human_approval_review_packet(
            goal="Record approval decision to durable audit.",
            proposal_id="proposal-audit-handoff-1",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="audit_handoff_run",
            artifact_relative_path="audit-handoff.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="unit-test",
        )
        capture = capture_human_decision(
            review_packet=packet,
            decision=capture_decision,
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T18:15:00Z",
            reason="Reviewed the packet.",
        )
        return create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=capture,
        )

    def read_first_event(self, audit_dir: Path) -> dict[str, object]:
        lines = (audit_dir / AUDIT_LOG_FILENAME).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        return json.loads(lines[0])

    def snapshot(self, base: str) -> list[str]:
        return sorted(str(path.relative_to(base)) for path in Path(base).rglob("*"))

    def assert_runtime_file_does_not_call_forbidden_capabilities(self) -> None:
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
            "write_sandbox_artifact(",
            "run_durable_local_agent_entrypoint(",
            "run_dry_run_agent_and_write_artifact(",
            "input(",
            "readline(",
        )
        source = HANDOFF_RUNTIME_FILE.read_text(encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
