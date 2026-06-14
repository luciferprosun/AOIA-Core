from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.schemas.action_proposal import ActionProposalType
from runtime.schemas.audit_event import AuditEvent
from runtime.schemas.dry_run_agent import create_dry_run_agent_request, create_dry_run_plan_step
from runtime.schemas.human_approval_review import HumanApprovalReviewPacket
from runtime.schemas.human_decision_capture import HumanDecisionCapture
from runtime.safety import approval_artifact_gate, approval_decision_audit_handoff, dry_run_artifact_integration
from runtime.safety import human_decision_to_approval_policy


@dataclass(frozen=True)
class GatedDurableArtifactFlowResult:
    completed: bool
    approval_decision_id: str | None
    approval_decision_type: str | None
    approval_audit_event_id: str | None
    approval_audit_event_hash: str | None
    gate_allowed: bool
    artifact_write_completed: bool
    artifact_path: str | None
    audit_log_path: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed": self.completed,
            "approval_decision_id": self.approval_decision_id,
            "approval_decision_type": self.approval_decision_type,
            "approval_audit_event_id": self.approval_audit_event_id,
            "approval_audit_event_hash": self.approval_audit_event_hash,
            "gate_allowed": self.gate_allowed,
            "artifact_write_completed": self.artifact_write_completed,
            "artifact_path": self.artifact_path,
            "audit_log_path": self.audit_log_path,
            "reason": self.reason,
        }


def run_gated_durable_artifact_flow(
    *,
    review_packet: HumanApprovalReviewPacket,
    decision_capture: HumanDecisionCapture,
    workspace_root: str | Path,
    audit_dir: str | Path,
    relative_output_path: str = "aoia_agent_v0_result.md",
) -> GatedDurableArtifactFlowResult:
    workspace_path, workspace_error = _absolute_path_or_error("workspace_root", workspace_root)
    if workspace_error:
        return _failed_result(workspace_error)
    audit_path, audit_error = _absolute_path_or_error("audit_dir", audit_dir)
    if audit_error:
        return _failed_result(audit_error)

    if not isinstance(review_packet, HumanApprovalReviewPacket):
        return _failed_result("review packet is required")
    if not isinstance(decision_capture, HumanDecisionCapture):
        return _failed_result("human decision capture is required")
    if relative_output_path != review_packet.artifact_relative_path:
        return _failed_result("relative output path must match the reviewed artifact path")

    try:
        approval_decision = human_decision_to_approval_policy.create_approval_decision_from_human_capture(
            review_packet=review_packet,
            decision_capture=decision_capture,
        )
    except (TypeError, ValueError) as exc:
        return _failed_result(f"approval decision conversion blocked: {exc}")

    try:
        approval_handoff = approval_decision_audit_handoff.record_approval_decision_to_durable_audit(
            approval_decision=approval_decision,
            audit_dir=audit_path,
        )
    except (TypeError, ValueError) as exc:
        return _failed_result(
            f"approval audit handoff blocked: {exc}",
            approval_decision_id=approval_decision.decision_id,
            approval_decision_type=approval_decision.decision_type.value,
        )

    if not approval_handoff.completed:
        return _failed_result(
            approval_handoff.reason,
            approval_decision_id=approval_handoff.approval_decision_id,
            approval_decision_type=approval_handoff.approval_decision_type,
            approval_audit_event_id=approval_handoff.audit_event_id,
            approval_audit_event_hash=approval_handoff.audit_event_hash,
            audit_log_path=approval_handoff.audit_log_path,
        )

    gate_result = approval_artifact_gate.evaluate_pre_artifact_approval_gate(
        approval_decision=approval_decision,
        approval_audit_handoff_result=approval_handoff,
    )
    if not gate_result.allowed:
        return _failed_result(
            gate_result.reason,
            approval_decision_id=approval_handoff.approval_decision_id,
            approval_decision_type=approval_handoff.approval_decision_type,
            approval_audit_event_id=approval_handoff.audit_event_id,
            approval_audit_event_hash=approval_handoff.audit_event_hash,
            gate_allowed=False,
            audit_log_path=approval_handoff.audit_log_path,
        )

    try:
        approval_audit_event = _read_approval_handoff_event(approval_handoff)
        dry_run_request = _create_gated_dry_run_request(review_packet, decision_capture)
        (
            durable_result,
            _trace,
            _audit_events,
            _sandbox_request,
            _sandbox_decision,
            _sandbox_result,
            _artifact_request,
            artifact_result,
            _durable_writes,
        ) = dry_run_artifact_integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
            dry_run_request,
            str(workspace_path),
            str(audit_path),
            relative_output_path=relative_output_path,
            approval_actor_id=approval_decision.actor_id,
            existing_audit_events=(approval_audit_event,),
            expected_first_previous_hash=approval_handoff.audit_event_hash,
            append_existing_audit_events=False,
        )
    except Exception as exc:
        return _failed_result(
            f"durable artifact path blocked: {exc}",
            approval_decision_id=approval_handoff.approval_decision_id,
            approval_decision_type=approval_handoff.approval_decision_type,
            approval_audit_event_id=approval_handoff.audit_event_id,
            approval_audit_event_hash=approval_handoff.audit_event_hash,
            gate_allowed=True,
            audit_log_path=approval_handoff.audit_log_path,
        )

    completed = bool(gate_result.allowed and durable_result.write_completed and artifact_result.write_completed)
    return GatedDurableArtifactFlowResult(
        completed=completed,
        approval_decision_id=approval_handoff.approval_decision_id,
        approval_decision_type=approval_handoff.approval_decision_type,
        approval_audit_event_id=approval_handoff.audit_event_id,
        approval_audit_event_hash=approval_handoff.audit_event_hash,
        gate_allowed=True,
        artifact_write_completed=artifact_result.write_completed,
        artifact_path=artifact_result.resolved_output_path if artifact_result.write_completed else None,
        audit_log_path=approval_handoff.audit_log_path,
        reason=durable_result.reason if completed else artifact_result.blocked_reason or durable_result.reason,
    )


def gated_durable_artifact_flow_result_to_dict(result: GatedDurableArtifactFlowResult) -> dict[str, Any]:
    if not isinstance(result, GatedDurableArtifactFlowResult):
        raise TypeError("result must be a GatedDurableArtifactFlowResult")
    return result.to_dict()


def _create_gated_dry_run_request(
    packet: HumanApprovalReviewPacket,
    capture: HumanDecisionCapture,
):
    material = "\n".join((packet.packet_id, capture.decision_id, capture.decision_hash, packet.artifact_relative_path))
    flow_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
    exact_payload = "\n".join(
        (
            "gated_durable_artifact_flow=v1",
            f"review_packet_id={packet.packet_id}",
            f"human_decision_capture_id={capture.decision_id}",
            f"human_decision_capture_hash={capture.decision_hash}",
            f"artifact_relative_path={packet.artifact_relative_path}",
        )
    )
    step = create_dry_run_plan_step(
        title="Gated durable artifact",
        description="Create one durable-audit-bound artifact after explicit human approval gate.",
        proposed_action_type=ActionProposalType.HUMAN_REVIEW_ONLY.value,
        payload_summary=packet.proposed_action_summary,
        exact_payload=exact_payload,
        step_index=0,
        step_id="gated-durable-artifact-step-" + flow_hash[:24],
        notes="Macrostep 5F explicit gated durable artifact flow",
    )
    return create_dry_run_agent_request(
        goal_text=packet.goal,
        requested_by=capture.reviewer_id,
        plan_steps=(step,),
        human_review_required=True,
        provider_generated=False,
        notes="Macrostep 5F gated durable artifact request",
        created_at=capture.captured_at,
        run_id=packet.run_id or "gated-durable-artifact-flow-" + flow_hash[:24],
    )


def _read_approval_handoff_event(handoff) -> AuditEvent:
    if not handoff.audit_log_path:
        raise ValueError("approval handoff audit log path is missing")
    log_path = Path(handoff.audit_log_path)
    last_line = ""
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last_line = line
    if not last_line:
        raise ValueError("approval handoff audit log is empty")
    decoded = json.loads(last_line)
    if decoded.get("event_id") != handoff.audit_event_id:
        raise ValueError("approval handoff event id does not match durable log")
    if decoded.get("event_hash") != handoff.audit_event_hash:
        raise ValueError("approval handoff event hash does not match durable log")
    event = AuditEvent(**decoded)
    if event.event_id != handoff.audit_event_id or event.event_hash != handoff.audit_event_hash:
        raise ValueError("approval handoff event is not valid")
    return event


def _absolute_path_or_error(name: str, value: str | Path) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        path = Path(value)
    else:
        return None, f"{name} must be a string or Path"
    if not str(path).strip():
        return None, f"{name} must be explicit"
    if not path.is_absolute():
        return None, f"{name} must be absolute"
    return path, None


def _failed_result(
    reason: str,
    *,
    approval_decision_id: str | None = None,
    approval_decision_type: str | None = None,
    approval_audit_event_id: str | None = None,
    approval_audit_event_hash: str | None = None,
    gate_allowed: bool = False,
    audit_log_path: str | None = None,
) -> GatedDurableArtifactFlowResult:
    return GatedDurableArtifactFlowResult(
        completed=False,
        approval_decision_id=approval_decision_id,
        approval_decision_type=approval_decision_type,
        approval_audit_event_id=approval_audit_event_id,
        approval_audit_event_hash=approval_audit_event_hash,
        gate_allowed=gate_allowed,
        artifact_write_completed=False,
        artifact_path=None,
        audit_log_path=audit_log_path,
        reason=reason,
    )
