from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import Any

from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
    approval_decision_to_dict,
)
from runtime.safety.approval_decision_audit_handoff import ApprovalDecisionAuditHandoffResult
from runtime.safety.approval_decision_policy import assert_approval_requires_human, assert_provider_cannot_approve


@dataclass(frozen=True)
class PreArtifactApprovalGateResult:
    allowed: bool
    approval_decision_id: str | None
    approval_decision_type: str | None
    audit_event_id: str | None
    audit_event_hash: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "approval_decision_id": self.approval_decision_id,
            "approval_decision_type": self.approval_decision_type,
            "audit_event_id": self.audit_event_id,
            "audit_event_hash": self.audit_event_hash,
            "reason": self.reason,
        }


_ISSUED_PRE_ARTIFACT_GATE_RESULTS: dict[
    int,
    tuple[
        weakref.ReferenceType[PreArtifactApprovalGateResult],
        tuple[Any, ...],
    ],
] = {}


def evaluate_pre_artifact_approval_gate(
    *,
    approval_decision: ApprovalDecision,
    approval_audit_handoff_result: ApprovalDecisionAuditHandoffResult,
) -> PreArtifactApprovalGateResult:
    result = _evaluate_pre_artifact_approval_gate(
        approval_decision=approval_decision,
        approval_audit_handoff_result=approval_audit_handoff_result,
    )
    return _record_canonical_pre_artifact_gate_issuance(result)


def is_canonically_issued_pre_artifact_gate_result(value: Any) -> bool:
    if type(value) is not PreArtifactApprovalGateResult:
        return False
    issuance = _ISSUED_PRE_ARTIFACT_GATE_RESULTS.get(id(value))
    if issuance is None:
        return False
    reference, fingerprint = issuance
    return reference() is value and fingerprint == _pre_artifact_gate_fingerprint(value)


def _evaluate_pre_artifact_approval_gate(
    *,
    approval_decision: ApprovalDecision,
    approval_audit_handoff_result: ApprovalDecisionAuditHandoffResult,
) -> PreArtifactApprovalGateResult:
    decision, denied = _validated_approval_decision_or_denial(approval_decision)
    if denied is not None:
        return denied

    handoff = approval_audit_handoff_result
    if not isinstance(handoff, ApprovalDecisionAuditHandoffResult):
        return _deny_for_decision(decision, "missing or malformed approval audit handoff result")

    if not handoff.completed:
        return _deny_for_decision(decision, "approval audit handoff is not completed")
    if handoff.approval_decision_id != decision.decision_id:
        return _deny_for_decision(decision, "approval audit handoff decision id mismatch")
    if handoff.approval_decision_type != decision.decision_type.value:
        return _deny_for_decision(decision, "approval audit handoff decision type mismatch")
    if not _is_valid_event_id(handoff.audit_event_id):
        return _deny_for_decision(decision, "approval audit handoff event id is missing or malformed")
    if not _is_sha256_hex(handoff.audit_event_hash):
        return _deny_for_decision(decision, "approval audit handoff event hash is missing or malformed")

    if decision.decision_type is not ApprovalDecisionType.APPROVE:
        return PreArtifactApprovalGateResult(
            allowed=False,
            approval_decision_id=decision.decision_id,
            approval_decision_type=decision.decision_type.value,
            audit_event_id=handoff.audit_event_id,
            audit_event_hash=handoff.audit_event_hash,
            reason="approval decision is not APPROVE",
        )

    return PreArtifactApprovalGateResult(
        allowed=True,
        approval_decision_id=decision.decision_id,
        approval_decision_type=decision.decision_type.value,
        audit_event_id=handoff.audit_event_id,
        audit_event_hash=handoff.audit_event_hash,
        reason="approval decision durable audit handoff accepted",
    )


def _record_canonical_pre_artifact_gate_issuance(
    result: PreArtifactApprovalGateResult,
) -> PreArtifactApprovalGateResult:
    identity = id(result)

    def discard(reference: weakref.ReferenceType[PreArtifactApprovalGateResult]) -> None:
        issuance = _ISSUED_PRE_ARTIFACT_GATE_RESULTS.get(identity)
        if issuance is not None and issuance[0] is reference:
            _ISSUED_PRE_ARTIFACT_GATE_RESULTS.pop(identity, None)

    _ISSUED_PRE_ARTIFACT_GATE_RESULTS[identity] = (
        weakref.ref(result, discard),
        _pre_artifact_gate_fingerprint(result),
    )
    return result


def _pre_artifact_gate_fingerprint(
    result: PreArtifactApprovalGateResult,
) -> tuple[Any, ...]:
    return (
        result.allowed,
        result.approval_decision_id,
        result.approval_decision_type,
        result.audit_event_id,
        result.audit_event_hash,
        result.reason,
    )


def pre_artifact_approval_gate_result_to_dict(result: PreArtifactApprovalGateResult) -> dict[str, Any]:
    if not isinstance(result, PreArtifactApprovalGateResult):
        raise TypeError("result must be a PreArtifactApprovalGateResult")
    return result.to_dict()


def _validated_approval_decision_or_denial(
    approval_decision: ApprovalDecision,
) -> tuple[ApprovalDecision, None] | tuple[None, PreArtifactApprovalGateResult]:
    if not isinstance(approval_decision, ApprovalDecision):
        return None, _deny_without_decision("missing or malformed approval decision")
    try:
        decision = ApprovalDecision(**approval_decision_to_dict(approval_decision))
    except (TypeError, ValueError):
        return None, _deny_without_decision("missing or malformed approval decision")

    base_denial = PreArtifactApprovalGateResult(
        allowed=False,
        approval_decision_id=decision.decision_id,
        approval_decision_type=decision.decision_type.value,
        audit_event_id=None,
        audit_event_hash=None,
        reason="approval decision is not valid for pre-artifact gate",
    )
    if decision.decision_type not in (ApprovalDecisionType.APPROVE, ApprovalDecisionType.REJECT):
        return None, base_denial
    if decision.decision_state is not ApprovalDecisionState.RECORDED:
        return None, base_denial
    if decision.actor_type is not ApprovalActorType.HUMAN_REVIEWER or not decision.human_reviewed:
        return None, base_denial
    if decision.provider_generated:
        return None, base_denial
    if decision.execution_permitted or decision.execution_triggered:
        return None, base_denial
    try:
        assert_provider_cannot_approve(decision)
        assert_approval_requires_human(decision)
    except Exception:
        return None, base_denial
    return decision, None


def _deny_without_decision(reason: str) -> PreArtifactApprovalGateResult:
    return PreArtifactApprovalGateResult(
        allowed=False,
        approval_decision_id=None,
        approval_decision_type=None,
        audit_event_id=None,
        audit_event_hash=None,
        reason=reason,
    )


def _deny_for_decision(decision: ApprovalDecision, reason: str) -> PreArtifactApprovalGateResult:
    return PreArtifactApprovalGateResult(
        allowed=False,
        approval_decision_id=decision.decision_id,
        approval_decision_type=decision.decision_type.value,
        audit_event_id=None,
        audit_event_hash=None,
        reason=reason,
    )


def _is_valid_event_id(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith("audit-event-") and _is_safe_nonempty_text(value)


def _is_safe_nonempty_text(value: str) -> bool:
    return bool(value.strip()) and all((ord(char) >= 32 and ord(char) != 127) for char in value)


def _is_sha256_hex(value: str | None) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value)
