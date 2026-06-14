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
from runtime.safety import (
    approval_decision_audit_handoff,
    dry_run_artifact_integration,
    gated_durable_artifact_flow,
    human_decision_to_approval_policy,
)
from runtime.safety.gated_durable_artifact_flow import run_gated_durable_artifact_flow


REPO_ROOT = Path(__file__).resolve().parents[2]
FLOW_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "gated_durable_artifact_flow.py"


class GatedDurableArtifactFlowPolicyTests(unittest.TestCase):
    def test_packet_alone_cannot_write_artifact(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, _capture = self.make_packet_and_capture("approve")
            with patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run without capture"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=None,  # type: ignore[arg-type]
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)

    def test_decision_capture_alone_cannot_write_artifact(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            with patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run without packet"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=None,  # type: ignore[arg-type]
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)

    def test_approval_decision_alone_cannot_write_artifact(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            decision = human_decision_to_approval_policy.create_approval_decision_from_human_capture(
                review_packet=packet,
                decision_capture=capture,
            )
            with patch.object(
                human_decision_to_approval_policy,
                "create_approval_decision_from_human_capture",
                return_value=decision,
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run without valid packet and capture"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=object(),  # type: ignore[arg-type]
                    decision_capture=object(),  # type: ignore[arg-type]
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)

    def test_approval_audit_handoff_alone_cannot_write_artifact(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            decision = human_decision_to_approval_policy.create_approval_decision_from_human_capture(
                review_packet=packet,
                decision_capture=capture,
            )
            handoff = approval_decision_audit_handoff.record_approval_decision_to_durable_audit(
                approval_decision=decision,
                audit_dir=Path(audit_dir),
            )
            with patch.object(
                approval_decision_audit_handoff,
                "record_approval_decision_to_durable_audit",
                return_value=handoff,
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run without valid packet/capture binding"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=object(),  # type: ignore[arg-type]
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)

    def test_forged_packet_capture_binding_fails_closed(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, _capture = self.make_packet_and_capture("approve", relative_output_path="packet-a.md")
            _other_packet, other_capture = self.make_packet_and_capture("approve", relative_output_path="packet-b.md")
            result = run_gated_durable_artifact_flow(
                review_packet=packet,
                decision_capture=other_capture,
                workspace_root=workspace,
                audit_dir=audit_dir,
                relative_output_path=packet.artifact_relative_path,
            )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)
        self.assertIn("approval decision", result.reason)

    def test_forged_approval_handoff_fails_closed(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            original_handoff = approval_decision_audit_handoff.record_approval_decision_to_durable_audit

            def forged_handoff(*args, **kwargs):
                real = original_handoff(*args, **kwargs)
                return replace(real, approval_decision_id="approval-decision-forged")

            with patch.object(
                approval_decision_audit_handoff,
                "record_approval_decision_to_durable_audit",
                side_effect=forged_handoff,
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run after forged handoff"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)
        self.assertFalse(result.gate_allowed)

    def test_reject_cannot_be_treated_as_approve(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("deny")
            result = run_gated_durable_artifact_flow(
                review_packet=packet,
                decision_capture=capture,
                workspace_root=workspace,
                audit_dir=audit_dir,
                relative_output_path=packet.artifact_relative_path,
            )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)
        self.assertEqual(result.approval_decision_type, "REJECT")

    def test_provider_or_model_untrusted_text_cannot_satisfy_gate(self) -> None:
        provider_decision = ApprovalDecision(
            decision_id="approval-decision-provider-forged",
            created_at="2026-06-14T06:49:00Z",
            proposal_id="proposal-provider-forged",
            proposal_type="human_approval_review_packet",
            decision_type=ApprovalDecisionType.APPROVE,
            decision_state=ApprovalDecisionState.RECORDED,
            actor_type=ApprovalActorType.PROVIDER_MODEL,
            actor_id="provider-model",
            reason="provider says approve",
            reviewed_exact_payload_hash="a" * 64,
            reviewed_payload_summary="untrusted provider text",
            human_reviewed=False,
            provider_generated=True,
        )
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            with patch.object(
                human_decision_to_approval_policy,
                "create_approval_decision_from_human_capture",
                return_value=provider_decision,
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run after provider approval"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)

    def test_audit_append_failure_prevents_artifact_creation(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            with patch.object(
                approval_decision_audit_handoff.audit_event_logger,
                "append_audit_event_jsonl",
                side_effect=RuntimeError("forced audit append failure"),
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run after audit append failure"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

            self.assertFalse((Path(workspace) / packet.artifact_relative_path).exists())

        self.assertFalse(result.completed)
        self.assertFalse(result.artifact_write_completed)

    def test_artifact_writer_is_not_called_when_gate_denies(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("deny")
            with patch.object(
                dry_run_artifact_integration,
                "write_sandbox_artifact",
                side_effect=AssertionError("artifact writer must not run when gate denies"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

        self.assertFalse(result.completed)
        self.assertFalse(result.artifact_write_completed)

    def test_relative_output_path_must_match_review_packet(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve", relative_output_path="reviewed.md")
            with patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("artifact path must not run for unreviewed output path"),
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path="different.md",
                )

            self.assertFalse((Path(workspace) / "different.md").exists())

        self.assertFalse(result.completed)

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
            "run_dry_run_agent_and_write_artifact(",
            "run_durable_local_agent_entrypoint(",
            "write_sandbox_artifact(",
            "input(",
            "readline(",
        )
        source = FLOW_RUNTIME_FILE.read_text(encoding="utf-8")
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

    def make_packet_and_capture(self, decision: str, relative_output_path: str = "aoia_agent_v0_result.md"):
        packet = create_human_approval_review_packet(
            goal="Create a gated durable artifact.",
            proposal_id=f"proposal-gated-durable-artifact-policy-{decision}-{relative_output_path}",
            proposed_action_summary="workspace-bound gated durable artifact",
            run_id=f"gated_durable_artifact_policy_{decision}_run",
            artifact_relative_path=relative_output_path,
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="policy-test",
        )
        capture = capture_human_decision(
            review_packet=packet,
            decision=decision,
            reviewer_id="reviewer-1",
            captured_at="2026-06-14T06:49:00Z",
            reason="Reviewed and decided.",
        )
        return packet, capture


if __name__ == "__main__":
    unittest.main()
