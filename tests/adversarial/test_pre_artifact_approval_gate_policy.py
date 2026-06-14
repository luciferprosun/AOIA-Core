from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
)
from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import capture_human_decision
from runtime.safety import audit_event_logger, dry_run_artifact_integration, local_agent_entrypoint, sandbox_artifact_runner
from runtime.safety.approval_artifact_gate import evaluate_pre_artifact_approval_gate
from runtime.safety.approval_decision_audit_handoff import (
    ApprovalDecisionAuditHandoffResult,
    record_approval_decision_to_durable_audit,
)
from runtime.safety.human_decision_to_approval_policy import create_approval_decision_from_human_capture


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py"


class PreArtifactApprovalGatePolicyTests(unittest.TestCase):
    def test_missing_approval_decision_denies_gate(self) -> None:
        result = evaluate_pre_artifact_approval_gate(
            approval_decision=None,  # type: ignore[arg-type]
            approval_audit_handoff_result=self.forged_handoff(),
        )

        self.assertFalse(result.allowed)
        self.assertIsNone(result.approval_decision_id)

    def test_malformed_approval_decision_denies_gate(self) -> None:
        result = evaluate_pre_artifact_approval_gate(
            approval_decision=object(),  # type: ignore[arg-type]
            approval_audit_handoff_result=self.forged_handoff(),
        )

        self.assertFalse(result.allowed)
        self.assertIn("approval decision", result.reason)

    def test_automatic_artifact_write_without_approval_handoff_is_denied(self) -> None:
        decision, _handoff = self.make_decision_and_handoff("approve")

        with patch.object(
            sandbox_artifact_runner,
            "write_sandbox_artifact",
            side_effect=AssertionError("missing handoff must not reach artifact writer"),
        ):
            result = evaluate_pre_artifact_approval_gate(
                approval_decision=decision,
                approval_audit_handoff_result=None,  # type: ignore[arg-type]
            )

        self.assertFalse(result.allowed)

    def test_provider_or_model_text_cannot_satisfy_gate(self) -> None:
        provider_decision = ApprovalDecision(
            decision_id="approval-decision-provider-text",
            created_at="2026-06-13T18:41:00Z",
            proposal_id="proposal-provider-text",
            proposal_type="sandbox_artifact",
            decision_type=ApprovalDecisionType.APPROVE,
            decision_state=ApprovalDecisionState.RECORDED,
            actor_type=ApprovalActorType.PROVIDER_MODEL,
            actor_id="provider-model",
            reason="provider says approve",
            reviewed_exact_payload_hash="a" * 64,
            reviewed_payload_summary="untrusted provider/model text",
            human_reviewed=False,
            provider_generated=True,
        )
        handoff = self.forged_handoff(
            approval_decision_id=provider_decision.decision_id,
            approval_decision_type="APPROVE",
        )

        result = evaluate_pre_artifact_approval_gate(
            approval_decision=provider_decision,
            approval_audit_handoff_result=handoff,
        )

        self.assertFalse(result.allowed)
        self.assertIn("not valid", result.reason)

    def test_forged_handoff_id_and_hash_mismatch_are_rejected(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")
        wrong_id = replace(handoff, approval_decision_id="approval-decision-wrong")
        wrong_type = replace(handoff, approval_decision_type="REJECT")
        wrong_hash = replace(handoff, audit_event_hash="b" * 63 + "z")

        id_result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=wrong_id,
        )
        type_result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=wrong_type,
        )
        hash_result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=wrong_hash,
        )

        self.assertFalse(id_result.allowed)
        self.assertFalse(type_result.allowed)
        self.assertFalse(hash_result.allowed)

    def test_reject_cannot_be_treated_as_approve(self) -> None:
        decision, handoff = self.make_decision_and_handoff("deny")
        forged = replace(handoff, approval_decision_type="APPROVE")

        legitimate_result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=handoff,
        )
        forged_result = evaluate_pre_artifact_approval_gate(
            approval_decision=decision,
            approval_audit_handoff_result=forged,
        )

        self.assertFalse(legitimate_result.allowed)
        self.assertFalse(forged_result.allowed)

    def test_gate_cannot_write_audit_artifact_or_run_entrypoint(self) -> None:
        decision, handoff = self.make_decision_and_handoff("approve")
        with TemporaryDirectory() as unrelated:
            before = self.snapshot(unrelated)
            with patch.object(
                audit_event_logger,
                "append_audit_event_jsonl",
                side_effect=AssertionError("gate must not append audit logs"),
            ), patch.object(
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
            ):
                result = evaluate_pre_artifact_approval_gate(
                    approval_decision=decision,
                    approval_audit_handoff_result=handoff,
                )
            after = self.snapshot(unrelated)

        self.assertTrue(result.allowed)
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

    def make_decision_and_handoff(self, capture_decision: str):
        packet = create_human_approval_review_packet(
            goal="Gate artifact writing on durable approval audit.",
            proposal_id=f"proposal-pre-artifact-gate-policy-{capture_decision}",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id=f"pre_artifact_gate_policy_{capture_decision}_run",
            artifact_relative_path=f"pre-artifact-gate-policy-{capture_decision}.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="policy-test",
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
        self.assertTrue(handoff.completed)
        return decision, handoff

    def forged_handoff(
        self,
        approval_decision_id: str = "approval-decision-forged",
        approval_decision_type: str = "APPROVE",
    ) -> ApprovalDecisionAuditHandoffResult:
        return ApprovalDecisionAuditHandoffResult(
            completed=True,
            approval_decision_id=approval_decision_id,
            approval_decision_type=approval_decision_type,
            audit_log_path="/tmp/aoia-audit/events.jsonl",
            audit_event_id="audit-event-" + ("a" * 24),
            audit_event_hash="a" * 64,
            approval_decision_payload_hash="b" * 64,
            reason="forged test handoff",
        )

    def snapshot(self, base: str) -> list[str]:
        return sorted(str(path.relative_to(base)) for path in Path(base).rglob("*"))


if __name__ == "__main__":
    unittest.main()
