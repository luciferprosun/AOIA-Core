from __future__ import annotations

import ast
import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.approval_decision import ApprovalDecisionType
from runtime.schemas.audit_event import create_policy_block_audit_event
from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import capture_human_decision
from runtime.safety import audit_event_logger, dry_run_artifact_integration, local_agent_entrypoint, sandbox_artifact_runner
from runtime.safety.approval_decision_audit_handoff import (
    ApprovalDecisionAuditHandoffPolicyError,
    record_approval_decision_to_durable_audit,
)
from runtime.safety.audit_event_logger import AUDIT_LOG_FILENAME, append_audit_event_jsonl
from runtime.safety.audit_event_policy import AuditEventChainBlockedError
from runtime.safety.human_decision_to_approval_policy import create_approval_decision_from_human_capture


REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFF_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "approval_decision_audit_handoff.py"


class ApprovalDecisionAuditHandoffPolicyTests(unittest.TestCase):
    def test_missing_approval_decision_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            record_approval_decision_to_durable_audit(
                approval_decision=None,  # type: ignore[arg-type]
                audit_dir="/tmp/aoia-audit",
            )

    def test_malformed_approval_decision_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            record_approval_decision_to_durable_audit(
                approval_decision=object(),  # type: ignore[arg-type]
                audit_dir="/tmp/aoia-audit",
            )

    def test_relative_audit_directory_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            record_approval_decision_to_durable_audit(
                approval_decision=self.make_decision("approve"),
                audit_dir="relative-audit",
            )

    def test_symlink_audit_directory_is_rejected_through_logger(self) -> None:
        with TemporaryDirectory() as tmpdir, TemporaryDirectory() as outside:
            link_path = Path(tmpdir) / "audit-link"
            try:
                link_path.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_decision("approve"),
                audit_dir=link_path,
            )

        self.assertFalse(result.completed)
        self.assertIn("blocked", result.reason)

    def test_symlink_log_escape_is_rejected_through_logger(self) -> None:
        with TemporaryDirectory() as tmpdir, TemporaryDirectory() as outside:
            audit_dir = Path(tmpdir) / "audit"
            audit_dir.mkdir()
            outside_log = Path(outside) / AUDIT_LOG_FILENAME
            try:
                (audit_dir / AUDIT_LOG_FILENAME).symlink_to(outside_log)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_decision("approve"),
                audit_dir=audit_dir,
            )

            self.assertFalse(result.completed)
            self.assertFalse(outside_log.exists())

    def test_invalid_existing_audit_hash_chain_blocks_handoff(self) -> None:
        with TemporaryDirectory() as tmpdir:
            audit_dir = Path(tmpdir)
            first = create_policy_block_audit_event("subject-1", "test", "first")
            append_audit_event_jsonl(audit_dir, first)
            bad = replace(create_policy_block_audit_event("subject-2", "test", "second"), previous_event_hash="wrong")
            with self.assertRaises(AuditEventChainBlockedError):
                append_audit_event_jsonl(audit_dir, bad)
            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_decision("approve"),
                audit_dir=audit_dir,
            )

        self.assertFalse(result.completed)
        self.assertIn("previous hash mismatch", result.reason)

    def test_logger_failure_returns_failed_result_and_does_not_claim_success(self) -> None:
        with TemporaryDirectory() as tmpdir, patch.object(
            audit_event_logger,
            "append_audit_event_jsonl",
            side_effect=RuntimeError("forced logger failure"),
        ):
            result = record_approval_decision_to_durable_audit(
                approval_decision=self.make_decision("approve"),
                audit_dir=Path(tmpdir),
            )

        self.assertFalse(result.completed)
        self.assertIsNone(result.audit_log_path)
        self.assertIsNone(result.audit_event_id)
        self.assertIn("forced logger failure", result.reason)

    def test_approve_cannot_be_silently_changed_to_reject(self) -> None:
        with TemporaryDirectory() as tmpdir:
            decision = self.make_decision("approve")
            result = record_approval_decision_to_durable_audit(
                approval_decision=decision,
                audit_dir=Path(tmpdir),
            )
            event = self.read_first_event(Path(tmpdir))

        self.assertEqual(result.approval_decision_type, "APPROVE")
        self.assertEqual(event["result"], "APPROVE")
        self.assertNotEqual(event["result"], "REJECT")

    def test_reject_cannot_be_silently_changed_to_approve(self) -> None:
        with TemporaryDirectory() as tmpdir:
            decision = self.make_decision("deny")
            result = record_approval_decision_to_durable_audit(
                approval_decision=decision,
                audit_dir=Path(tmpdir),
            )
            event = self.read_first_event(Path(tmpdir))

        self.assertEqual(result.approval_decision_type, "REJECT")
        self.assertEqual(event["result"], "REJECT")
        self.assertNotEqual(event["result"], "APPROVE")

    def test_handoff_rejects_ambiguous_decision_type(self) -> None:
        decision = replace(self.make_decision("approve"), decision_type=ApprovalDecisionType.DEFER)

        with self.assertRaises(ApprovalDecisionAuditHandoffPolicyError):
            record_approval_decision_to_durable_audit(
                approval_decision=decision,
                audit_dir="/tmp/aoia-audit",
            )

    def test_handoff_cannot_execute_write_artifact_or_run_entrypoint(self) -> None:
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
                result = record_approval_decision_to_durable_audit(
                    approval_decision=self.make_decision("approve"),
                    audit_dir=Path(tmpdir),
                )
            after = self.snapshot(unrelated)

        self.assertTrue(result.completed)
        self.assertEqual(before, after)

    def test_no_forbidden_runtime_capability_is_introduced(self) -> None:
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

    def make_decision(self, capture_decision: str):
        packet = create_human_approval_review_packet(
            goal="Record approval decision to durable audit.",
            proposal_id="proposal-audit-handoff-policy",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="audit_handoff_policy_run",
            artifact_relative_path="audit-handoff-policy.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="policy-test",
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


if __name__ == "__main__":
    unittest.main()
