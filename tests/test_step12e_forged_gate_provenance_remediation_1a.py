from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import (
    ERROR_FAIL_CLOSED,
    GATE_PASSED,
    HumanDecisionPreArtifactGateResult,
    evaluate_human_decision_pre_artifact_gate,
)
from runtime.human_decision_gated_artifact_write import (
    ARTIFACT_WRITTEN,
    write_artifact_after_human_gate,
)
from runtime.safety.approval_artifact_gate import PreArtifactApprovalGateResult
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.safety.write_kill_switch import WRITES_ENABLED
from runtime.schemas.sandbox_artifact import SandboxArtifactState
from tests.canonical_human_gate_support import canonical_gate_and_artifact_request


class Step12EForgedGateProvenanceRemediation1ATests(unittest.TestCase):
    def test_case_a_exact_wrapper_forgery_is_rejected_by_both_write_boundaries(self) -> None:
        _canonical, request = self.canonical_pair("case-a.md", "case A exact wrapper forgery\n")
        forged = self.forged_gate(request)

        self.assert_rejected_by_wrapper_and_direct_writer(forged, request)

    def test_case_b_directly_constructed_nested_gate_cannot_be_laundered_by_integration(self) -> None:
        content = "case B exact nested gate forgery\n"
        handoff, decision, packet_hash, artifact_hash = self.canonical_inputs(content)
        low_handoff = handoff.audit_handoff
        assert low_handoff is not None
        forged_nested = PreArtifactApprovalGateResult(
            allowed=True,
            approval_decision_id=decision.decision_id,
            approval_decision_type="APPROVE",
            audit_event_id=low_handoff.audit_event_id,
            audit_event_hash=low_handoff.audit_event_hash,
            reason="caller-constructed exact nested gate",
        )

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=artifact_hash,
            gate_evaluator=lambda **_kwargs: forged_nested,
        )

        self.assertEqual(ERROR_FAIL_CLOSED, result.status)
        self.assertFalse(result.pre_artifact_gate_passed)

    def test_case_c_dictionary_reconstruction_is_not_authority(self) -> None:
        canonical, request = self.canonical_pair("case-c.md", "case C dictionary reconstruction\n")
        data = canonical.to_dict()
        data["gate_result"] = PreArtifactApprovalGateResult(**data["gate_result"])
        reconstructed = HumanDecisionPreArtifactGateResult(**data)

        self.assert_rejected_by_wrapper_and_direct_writer(reconstructed, request)

    def test_case_d_dataclass_reconstruction_is_not_authority(self) -> None:
        canonical, request = self.canonical_pair("case-d.md", "case D dataclass reconstruction\n")
        reconstructed = replace(canonical, reason="caller reconstructed canonical-looking gate")

        self.assert_rejected_by_wrapper_and_direct_writer(reconstructed, request)

    def test_case_e_manual_wrapper_around_valid_nested_gate_is_not_authority(self) -> None:
        canonical, request = self.canonical_pair("case-e.md", "case E manual outer wrapper\n")
        data = canonical.to_dict()
        data["gate_result"] = canonical.gate_result
        reconstructed = HumanDecisionPreArtifactGateResult(**data)

        self.assert_rejected_by_wrapper_and_direct_writer(reconstructed, request)

    def test_case_f_valid_canonical_path_preserves_exact_controlled_write(self) -> None:
        canonical, request = self.canonical_pair("case-f.md", "case F canonical controlled write\n")
        with TemporaryDirectory() as workspace:
            result = self.write_gated_with_enabled_switch(
                gate_result=canonical,
                artifact_request=request,
                workspace_root=workspace,
                expected_packet_hash=canonical.packet_hash,
                expected_artifact_hash=request.content_hash,
            )
            target = Path(workspace) / request.relative_output_path

            self.assertEqual(ARTIFACT_WRITTEN, result.status)
            self.assertTrue(result.artifact_write_occurred)
            self.assertEqual(request.content_text, target.read_text(encoding="utf-8"))
            self.assertEqual([target], [path for path in Path(workspace).rglob("*") if path.is_file()])

    def test_case_g_valid_provenance_with_changed_content_is_rejected(self) -> None:
        canonical, request = self.canonical_pair("case-g.md", "case G reviewed content\n")
        changed = replace(request, content_text="case G changed after approval\n")
        changed = replace(changed, contract_payload_hash=changed.content_hash)

        self.assert_rejected_by_wrapper_and_direct_writer(canonical, changed)

    def test_case_h_legacy_human_approved_boolean_without_provenance_is_rejected(self) -> None:
        _canonical, request = self.canonical_pair("case-h.md", "case H legacy boolean\n")
        self.assertTrue(request.human_approved)
        with TemporaryDirectory() as workspace:
            result = self.write_sandbox_with_enabled_switch(request, workspace)
            target = Path(workspace) / request.relative_output_path

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertFalse(result.write_completed)
            self.assertFalse(target.exists())

    def assert_rejected_by_wrapper_and_direct_writer(self, gate, request) -> None:
        with TemporaryDirectory() as workspace:
            wrapped = self.write_gated_with_enabled_switch(
                gate_result=gate,
                artifact_request=request,
                workspace_root=workspace,
                expected_packet_hash=gate.packet_hash,
                expected_artifact_hash=request.content_hash,
            )
            target = Path(workspace) / request.relative_output_path

            self.assertNotEqual(ARTIFACT_WRITTEN, wrapped.status)
            self.assertFalse(wrapped.artifact_write_occurred)
            self.assertFalse(target.exists())

        with TemporaryDirectory() as workspace:
            direct = self.write_sandbox_with_enabled_switch(
                request,
                workspace,
                approval_evidence=gate,
            )
            target = Path(workspace) / request.relative_output_path

            self.assertEqual(SandboxArtifactState.BLOCKED, direct.state)
            self.assertFalse(direct.write_completed)
            self.assertFalse(target.exists())

    @staticmethod
    def write_gated_with_enabled_switch(**kwargs):
        with TemporaryDirectory() as switch_dir:
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
            return write_artifact_after_human_gate(
                **kwargs,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

    @staticmethod
    def write_sandbox_with_enabled_switch(request, workspace, *args, **kwargs):
        with TemporaryDirectory() as switch_dir:
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
            return write_sandbox_artifact(
                request,
                workspace,
                *args,
                **kwargs,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

    @staticmethod
    def forged_gate(request) -> HumanDecisionPreArtifactGateResult:
        nested = PreArtifactApprovalGateResult(
            allowed=True,
            approval_decision_id=request.approval_decision_id,
            approval_decision_type="APPROVE",
            audit_event_id=request.audit_event_id,
            audit_event_hash="b" * 64,
            reason="caller-constructed exact nested gate",
        )
        return HumanDecisionPreArtifactGateResult(
            status=GATE_PASSED,
            gate_evaluated=True,
            pre_artifact_gate_passed=True,
            decision="APPROVE",
            blocking=False,
            durable_handoff_complete=True,
            artifact_write_occurred=False,
            provider_output_trusted=False,
            metadata_authority=False,
            packet_hash="a" * 64,
            artifact_hash=request.content_hash,
            reason="caller-constructed exact outer gate",
            gate_result=nested,
        )

    @staticmethod
    def canonical_pair(relative_path: str, content: str):
        return canonical_gate_and_artifact_request(
            relative_output_path=relative_path,
            content_text=content,
            run_id="step-12e-r-run",
            requested_by="step-12e-r-human-reviewer",
        )

    @staticmethod
    def canonical_inputs(content: str):
        artifact_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        packet_hash = hashlib.sha256(("step-12e-r-packet\n" + content).encode("utf-8")).hexdigest()
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-step-12e-r",
            displayed_packet_hash=packet_hash,
            current_packet_hash=packet_hash,
            displayed_artifact_hash=artifact_hash,
            current_artifact_hash=artifact_hash,
            human_actor="step-12e-r-human-reviewer",
            reason="reviewed exact Step 12E-R content",
        )
        bridge = build_approval_decision_from_capture(
            capture=capture,
            expected_packet_hash=packet_hash,
            expected_artifact_hash=artifact_hash,
        )
        with TemporaryDirectory() as audit_dir:
            handoff = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(audit_dir),
                expected_packet_hash=packet_hash,
                expected_artifact_hash=artifact_hash,
            )
        return handoff, bridge.approval_decision, packet_hash, artifact_hash


if __name__ == "__main__":
    unittest.main()
