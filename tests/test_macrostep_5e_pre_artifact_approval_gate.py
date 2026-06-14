from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import capture_human_decision
from runtime.safety import audit_event_logger, dry_run_artifact_integration, local_agent_entrypoint, sandbox_artifact_runner
from runtime.safety.approval_artifact_gate import (
    PreArtifactApprovalGateResult,
    evaluate_pre_artifact_approval_gate,
)
from runtime.safety.approval_decision_audit_handoff import (
    ApprovalDecisionAuditHandoffResult,
    record_approval_decision_to_durable_audit,
)
from runtime.safety.human_decision_to_approval_policy import create_approval_decision_from_human_capture


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py"


class Macrostep5EPreArtifactApprovalGateTests(unittest.TestCase):
    def test_gate_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(evaluate_pre_artifact_approval_gate))

    def test_gate_accepts_approve_with_completed_durable_handoff(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")

        result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=handoff,
        )

        self.assertIsInstance(result, PreArtifactApprovalGateResult)
        self.assertTrue(result.allowed)
        self.assertEqual(result.approval_decision_id, decision.decision_id)
        self.assertEqual(result.approval_decision_type, "APPROVE")
        self.assertEqual(result.audit_event_id, handoff.audit_event_id)
        self.assertEqual(result.audit_event_hash, handoff.audit_event_hash)

    def test_gate_rejects_reject_decision_for_artifact_write(self) -> None:
        decision, handoff = self.make_decision_and_handoff("deny")

        result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=handoff,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.approval_decision_type, "REJECT")
        self.assertIn("not APPROVE", result.reason)

    def test_gate_rejects_missing_durable_handoff(self) -> None:
        decision, _handoff = self.make_decision_and_handoff("approve")

        result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=None,  # type: ignore[arg-type]
        )

        self.assertFalse(result.allowed)
        self.assertIn("handoff", result.reason)

    def test_gate_rejects_failed_durable_handoff(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")
        failed = replace(handoff, completed=False, audit_event_id=None, audit_event_hash=None)

        result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=failed,
        )

        self.assertFalse(result.allowed)
        self.assertIn("not completed", result.reason)

    def test_gate_rejects_mismatched_handoff_decision_id(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")
        forged = replace(handoff, approval_decision_id="approval-decision-forged")

        result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=forged,
        )

        self.assertFalse(result.allowed)
        self.assertIn("id mismatch", result.reason)

    def test_gate_rejects_missing_or_malformed_event_id_and_hash(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")
        missing_id = replace(handoff, audit_event_id="")
        bad_hash = replace(handoff, audit_event_hash="not-a-sha256")

        id_result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=missing_id,
        )
        hash_result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=bad_hash,
        )

        self.assertFalse(id_result.allowed)
        self.assertFalse(hash_result.allowed)
        self.assertIn("event id", id_result.reason)
        self.assertIn("event hash", hash_result.reason)

    def test_gate_result_is_deterministic_for_deterministic_inputs(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")

        first = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=handoff,
        )
        second = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=handoff,
        )

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_gate_does_not_write_artifacts_audit_or_run_entrypoint(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")
        with TemporaryDirectory() as unrelated:
            before = self.snapshot(unrelated)
            with patch.object(
                sandbox_artifact_runner,
                "write_sandbox_artifact",
                side_effect=AssertionError("gate must not write artifacts"),
            ), patch.object(
                local_agent_entrypoint,
                "run_durable_local_agent_entrypoint",
                side_effect=AssertionError("gate must not run local entrypoint"),
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("gate must not use old non-durable path"),
            ), patch.object(
                audit_event_logger,
                "append_audit_event_jsonl",
                side_effect=AssertionError("gate must not append audit logs"),
            ):
                result = evaluate_pre_artifact_approval_gate(
                    approval_decision=decision,
                    approval_audit_handoff_result=handoff,
                )
            after = self.snapshot(unrelated)

        self.assertTrue(result.allowed)
        self.assertEqual(before, after)

    def test_gate_runtime_does_not_call_forbidden_capabilities(self) -> None:
        self.assert_runtime_file_does_not_call_forbidden_capabilities()

    def make_decision_and_handoff(self, capture_decision: str):
        packet = create_human_approval_review_packet(
            goal="Gate artifact writing on durable approval audit.",
            proposal_id=f"proposal-pre-artifact-gate-{capture_decision}",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id=f"pre_artifact_gate_{capture_decision}_run",
            artifact_relative_path=f"pre-artifact-gate-{capture_decision}.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="unit-test",
        )
        capture = capture_human_decision(
            review_packet=packet,
            decision=capture_decision,
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T18:41:00Z",
            reason="Reviewed the packet.",
        )
        decision = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=capture,
        )
        with TemporaryDirectory() as tmpdir:
            handoff = record_approval_decision_to_durable_audit(
                approval_decision=decision,
                audit_dir=Path(tmpdir),
            )
        self.assertIsInstance(handoff, ApprovalDecisionAuditHandoffResult)
        self.assertTrue(handoff.completed)
        return decision, handoff

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
            "append_audit_event_jsonl(",
            "write_sandbox_artifact(",
            "run_durable_local_agent_entrypoint(",
            "run_dry_run_agent_and_write_artifact(",
            "input(",
            "readline(",
        )
        source = GATE_RUNTIME_FILE.read_text(encoding="utf-8")
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
