from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
    approval_decision_to_dict,
)
from runtime.schemas.audit_event import create_approval_decision_audit_event
from runtime.safety import audit_event_logger
from runtime.safety.approval_decision_policy import assert_approval_requires_human, assert_provider_cannot_approve


class ApprovalDecisionAuditHandoffPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovalDecisionAuditHandoffResult:
    completed: bool
    approval_decision_id: str
    approval_decision_type: str
    audit_log_path: str | None
    audit_event_id: str | None
    audit_event_hash: str | None
    approval_decision_payload_hash: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed": self.completed,
            "approval_decision_id": self.approval_decision_id,
            "approval_decision_type": self.approval_decision_type,
            "audit_log_path": self.audit_log_path,
            "audit_event_id": self.audit_event_id,
            "audit_event_hash": self.audit_event_hash,
            "approval_decision_payload_hash": self.approval_decision_payload_hash,
            "reason": self.reason,
        }


def record_approval_decision_to_durable_audit(
    *,
    approval_decision: ApprovalDecision,
    audit_dir: str | Path,
    expected_previous_hash: str | None = None,
) -> ApprovalDecisionAuditHandoffResult:
    decision = _validated_approval_decision(approval_decision)
    audit_root = _validate_explicit_absolute_audit_dir(audit_dir)
    previous_hash = expected_previous_hash or ""
    event = create_approval_decision_audit_event(decision, previous_event_hash=previous_hash)

    try:
        write_result = audit_event_logger.append_audit_event_jsonl(
            audit_root,
            event,
            expected_previous_hash=expected_previous_hash,
        )
    except Exception as exc:
        return ApprovalDecisionAuditHandoffResult(
            completed=False,
            approval_decision_id=decision.decision_id,
            approval_decision_type=decision.decision_type.value,
            audit_log_path=None,
            audit_event_id=None,
            audit_event_hash=None,
            approval_decision_payload_hash=event.payload_hash,
            reason=f"audit handoff blocked: {exc}",
        )

    return ApprovalDecisionAuditHandoffResult(
        completed=write_result.write_completed,
        approval_decision_id=decision.decision_id,
        approval_decision_type=decision.decision_type.value,
        audit_log_path=write_result.audit_log_path,
        audit_event_id=write_result.event_id,
        audit_event_hash=write_result.event_hash,
        approval_decision_payload_hash=event.payload_hash,
        reason="approval decision recorded to durable audit",
    )


def approval_decision_audit_handoff_result_to_dict(
    result: ApprovalDecisionAuditHandoffResult,
) -> dict[str, Any]:
    if not isinstance(result, ApprovalDecisionAuditHandoffResult):
        raise TypeError("result must be an ApprovalDecisionAuditHandoffResult")
    return result.to_dict()


def _validated_approval_decision(decision: ApprovalDecision) -> ApprovalDecision:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("approval_decision must be an ApprovalDecision")
    try:
        validated = ApprovalDecision(**approval_decision_to_dict(decision))
    except (TypeError, ValueError) as exc:
        raise ApprovalDecisionAuditHandoffPolicyError("approval decision is not valid for durable audit handoff") from exc

    if validated.decision_type not in (ApprovalDecisionType.APPROVE, ApprovalDecisionType.REJECT):
        raise ApprovalDecisionAuditHandoffPolicyError("approval decision type must be APPROVE or REJECT")
    if validated.decision_state is not ApprovalDecisionState.RECORDED:
        raise ApprovalDecisionAuditHandoffPolicyError("approval decision state must be RECORDED")
    if validated.actor_type is not ApprovalActorType.HUMAN_REVIEWER or not validated.human_reviewed:
        raise ApprovalDecisionAuditHandoffPolicyError("approval decision audit handoff requires a human reviewer")
    if validated.provider_generated:
        raise ApprovalDecisionAuditHandoffPolicyError("provider-generated approval decisions cannot be handed off")
    if validated.execution_permitted or validated.execution_triggered:
        raise ApprovalDecisionAuditHandoffPolicyError("approval decision audit handoff cannot carry execution flags")

    assert_provider_cannot_approve(validated)
    if validated.decision_type is ApprovalDecisionType.APPROVE:
        assert_approval_requires_human(validated)
    return validated


def _validate_explicit_absolute_audit_dir(audit_dir: str | Path) -> Path:
    if isinstance(audit_dir, Path):
        path = audit_dir
    elif isinstance(audit_dir, str):
        path = Path(audit_dir)
    else:
        raise TypeError("audit_dir must be a string or Path")
    if not str(path).strip():
        raise ValueError("audit_dir must be explicit")
    if not path.is_absolute():
        raise ValueError("audit_dir must be absolute")
    return path
