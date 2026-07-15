from __future__ import annotations

import ast
import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.audit_event import AuditEventType
from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import capture_human_decision
from runtime.safety import approval_artifact_gate, approval_decision_audit_handoff, dry_run_artifact_integration
from runtime.safety.gated_durable_artifact_flow import (
    GatedDurableArtifactFlowResult,
    run_gated_durable_artifact_flow,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FLOW_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "gated_durable_artifact_flow.py"


class Macrostep5FGatedDurableArtifactFlowTests(unittest.TestCase):
    def test_gated_flow_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(run_gated_durable_artifact_flow))

    def test_gated_flow_writes_artifact_only_after_approve_gate(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")

            result = run_gated_durable_artifact_flow(
                review_packet=packet,
                decision_capture=capture,
                workspace_root=Path(workspace),
                audit_dir=Path(audit_dir),
                relative_output_path=packet.artifact_relative_path,
            )

            artifact_path = Path(result.artifact_path or "")
            events = self.read_events(Path(audit_dir))
            artifact_exists = artifact_path.is_file()

        self.assertIsInstance(result, GatedDurableArtifactFlowResult)
        self.assertFalse(result.completed)
        self.assertTrue(result.gate_allowed)
        self.assertFalse(result.artifact_write_completed)
        self.assertEqual(result.approval_decision_type, "APPROVE")
        self.assertFalse(artifact_exists)
        self.assertEqual(events[0]["event_type"], AuditEventType.APPROVAL_DECISION_RECORDED.value)
        self.assertEqual(events[0]["event_id"], result.approval_audit_event_id)
        self.assertEqual(events[0]["event_hash"], result.approval_audit_event_hash)

    def test_gated_flow_requires_valid_packet_and_capture(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")

            missing_packet = run_gated_durable_artifact_flow(
                review_packet=None,  # type: ignore[arg-type]
                decision_capture=capture,
                workspace_root=workspace,
                audit_dir=audit_dir,
                relative_output_path=packet.artifact_relative_path,
            )
            missing_capture = run_gated_durable_artifact_flow(
                review_packet=packet,
                decision_capture=None,  # type: ignore[arg-type]
                workspace_root=workspace,
                audit_dir=audit_dir,
                relative_output_path=packet.artifact_relative_path,
            )

        self.assertFalse(missing_packet.completed)
        self.assertFalse(missing_capture.completed)
        self.assertFalse(missing_packet.artifact_write_completed)
        self.assertFalse(missing_capture.artifact_write_completed)

    def test_gated_flow_creates_approval_decision_records_handoff_and_evaluates_gate(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            with patch.object(
                approval_decision_audit_handoff,
                "record_approval_decision_to_durable_audit",
                wraps=approval_decision_audit_handoff.record_approval_decision_to_durable_audit,
            ) as handoff_spy, patch.object(
                approval_artifact_gate,
                "evaluate_pre_artifact_approval_gate",
                wraps=approval_artifact_gate.evaluate_pre_artifact_approval_gate,
            ) as gate_spy:
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

        self.assertFalse(result.completed)
        self.assertTrue(result.approval_decision_id)
        self.assertTrue(result.approval_audit_event_id)
        self.assertEqual(handoff_spy.call_count, 1)
        self.assertEqual(gate_spy.call_count, 1)

    def test_gated_flow_writes_no_artifact_when_decision_is_reject(self) -> None:
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
        self.assertFalse(result.gate_allowed)
        self.assertFalse(result.artifact_write_completed)
        self.assertEqual(result.approval_decision_type, "REJECT")

    def test_gated_flow_writes_no_artifact_when_approval_handoff_fails(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            original_handoff = approval_decision_audit_handoff.record_approval_decision_to_durable_audit

            def failed_handoff(*args, **kwargs):
                real = original_handoff(*args, **kwargs)
                return replace(real, completed=False, audit_event_id=None, audit_event_hash=None)

            with patch.object(
                approval_decision_audit_handoff,
                "record_approval_decision_to_durable_audit",
                side_effect=failed_handoff,
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("durable artifact path must not run after failed handoff"),
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
        self.assertFalse(result.gate_allowed)

    def test_gated_flow_writes_no_artifact_when_gate_denies(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            denied_gate = approval_artifact_gate.PreArtifactApprovalGateResult(
                allowed=False,
                approval_decision_id="approval-denied",
                approval_decision_type="APPROVE",
                audit_event_id=None,
                audit_event_hash=None,
                reason="forced denial",
            )

            with patch.object(
                approval_artifact_gate,
                "evaluate_pre_artifact_approval_gate",
                return_value=denied_gate,
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                side_effect=AssertionError("durable artifact path must not run after gate denial"),
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
        self.assertFalse(result.artifact_write_completed)

    def test_gated_flow_uses_existing_durable_path_after_gate_and_not_old_non_durable_path(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            with patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("old non-durable path must not be called"),
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact_with_durable_audit",
                wraps=dry_run_artifact_integration.run_dry_run_agent_and_write_artifact_with_durable_audit,
            ) as durable_spy:
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

        self.assertFalse(result.completed)
        self.assertEqual(durable_spy.call_count, 1)

    def test_gated_flow_records_approval_event_before_artifact_write(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            output_path = Path(workspace) / packet.artifact_relative_path
            audit_log_path = Path(audit_dir) / "events.jsonl"
            original_writer = dry_run_artifact_integration.write_sandbox_artifact

            def assert_approval_audit_exists_before_write(request, workspace_root):
                self.assertTrue(audit_log_path.is_file())
                events = self.read_events(Path(audit_dir))
                self.assertGreaterEqual(len(events), 1)
                self.assertEqual(events[0]["event_type"], AuditEventType.APPROVAL_DECISION_RECORDED.value)
                self.assertFalse(output_path.exists())
                return original_writer(request, workspace_root)

            with patch.object(
                dry_run_artifact_integration,
                "write_sandbox_artifact",
                side_effect=assert_approval_audit_exists_before_write,
            ):
                result = run_gated_durable_artifact_flow(
                    review_packet=packet,
                    decision_capture=capture,
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                    relative_output_path=packet.artifact_relative_path,
                )

        self.assertFalse(result.completed)

    def test_gated_flow_result_contains_expected_fields(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            packet, capture = self.make_packet_and_capture("approve")
            result = run_gated_durable_artifact_flow(
                review_packet=packet,
                decision_capture=capture,
                workspace_root=workspace,
                audit_dir=audit_dir,
                relative_output_path=packet.artifact_relative_path,
            )

        serialized = result.to_dict()
        self.assertFalse(serialized["completed"])
        self.assertTrue(serialized["approval_decision_id"])
        self.assertEqual(serialized["approval_decision_type"], "APPROVE")
        self.assertTrue(serialized["approval_audit_event_id"])
        self.assertTrue(serialized["approval_audit_event_hash"])
        self.assertTrue(serialized["gate_allowed"])
        self.assertFalse(serialized["artifact_write_completed"])
        self.assertFalse(serialized["artifact_path"])
        self.assertTrue(serialized["audit_log_path"])
        self.assertTrue(serialized["reason"])

    def test_old_compatibility_paths_remain_unchanged(self) -> None:
        from runtime.schemas.action_proposal import ActionProposalType
        from runtime.schemas.dry_run_agent import create_dry_run_agent_request, create_dry_run_plan_step
        from runtime.schemas.sandbox_artifact import SandboxArtifactState

        step = create_dry_run_plan_step(
            title="Compatibility path",
            description="Create one legacy compatibility artifact.",
            proposed_action_type=ActionProposalType.HUMAN_REVIEW_ONLY.value,
            payload_summary="legacy compatibility artifact",
            exact_payload="legacy_compatibility=unchanged",
            step_id="macrostep-5f-compatibility-step",
        )
        request = create_dry_run_agent_request(
            goal_text="Create a compatibility artifact.",
            requested_by="unit-test",
            plan_steps=(step,),
            run_id="macrostep-5f-compatibility-run",
        )
        with TemporaryDirectory() as workspace:
            result = dry_run_artifact_integration.run_dry_run_agent_and_write_artifact(
                request,
                workspace,
                relative_output_path="legacy-compatibility.md",
            )
            artifact_result = result[-1]

        self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)

    def test_gated_flow_runtime_does_not_call_forbidden_capabilities(self) -> None:
        self.assert_runtime_file_does_not_call_forbidden_capabilities()

    def make_packet_and_capture(self, decision: str, relative_output_path: str = "aoia_agent_v0_result.md"):
        packet = create_human_approval_review_packet(
            goal="Create a gated durable artifact.",
            proposal_id=f"proposal-gated-durable-artifact-{decision}",
            proposed_action_summary="workspace-bound gated durable artifact",
            run_id=f"gated_durable_artifact_{decision}_run",
            artifact_relative_path=relative_output_path,
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="unit-test",
        )
        capture = capture_human_decision(
            review_packet=packet,
            decision=decision,
            reviewer_id="reviewer-1",
            captured_at="2026-06-14T06:49:00Z",
            reason="Reviewed and decided.",
        )
        return packet, capture

    def read_events(self, audit_dir: Path) -> list[dict[str, object]]:
        lines = (audit_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

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


if __name__ == "__main__":
    unittest.main()
