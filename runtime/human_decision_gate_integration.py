from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from runtime.human_decision_audit_handoff import (
    HANDOFF_COMPLETE_APPROVE,
    HANDOFF_COMPLETE_REJECT,
    DurableApprovalAuditHandoff,
)
from runtime.schemas.approval_decision import ApprovalDecision, ApprovalDecisionType
from runtime.safety.approval_artifact_gate import (
    PreArtifactApprovalGateResult,
    evaluate_pre_artifact_approval_gate,
    is_canonically_issued_pre_artifact_gate_result,
)
from runtime.safety.approval_decision_audit_handoff import (
    ApprovalDecisionAuditHandoffResult,
)


GATE_PASSED = "GATE_PASSED"
GATE_DENIED = "GATE_DENIED"
BLOCKED_REJECT = "BLOCKED_REJECT"
BLOCKED_INVALID_HANDOFF = "BLOCKED_INVALID_HANDOFF"
BLOCKED_MISSING_PACKET_HASH = "BLOCKED_MISSING_PACKET_HASH"
BLOCKED_STALE_OR_MISMATCHED_STATE = "BLOCKED_STALE_OR_MISMATCHED_STATE"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"

GateEvaluator = Callable[..., PreArtifactApprovalGateResult]


@dataclass(frozen=True)
class HumanDecisionPreArtifactGateResult:
    status: str
    gate_evaluated: bool
    pre_artifact_gate_passed: bool
    decision: str
    blocking: bool
    durable_handoff_complete: bool
    artifact_write_occurred: bool
    provider_output_trusted: bool
    metadata_authority: bool
    packet_hash: str | None
    artifact_hash: str | None
    reason: str
    gate_result: PreArtifactApprovalGateResult | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "gate_evaluated": self.gate_evaluated,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "decision": self.decision,
            "blocking": self.blocking,
            "durable_handoff_complete": self.durable_handoff_complete,
            "artifact_write_occurred": self.artifact_write_occurred,
            "provider_output_trusted": self.provider_output_trusted,
            "metadata_authority": self.metadata_authority,
            "packet_hash": self.packet_hash,
            "artifact_hash": self.artifact_hash,
            "reason": self.reason,
            "gate_result": self.gate_result.to_dict() if self.gate_result is not None else None,
        }


_ISSUED_HUMAN_GATE_RESULTS: dict[
    int,
    tuple[
        weakref.ReferenceType[HumanDecisionPreArtifactGateResult],
        tuple[Any, ...],
    ],
] = {}


def evaluate_human_decision_pre_artifact_gate(
    *,
    handoff_result: DurableApprovalAuditHandoff | Mapping[str, Any],
    approval_decision: ApprovalDecision | Mapping[str, Any],
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    gate_evaluator: GateEvaluator = evaluate_pre_artifact_approval_gate,
) -> HumanDecisionPreArtifactGateResult:
    result = _evaluate_human_decision_pre_artifact_gate(
        handoff_result=handoff_result,
        approval_decision=approval_decision,
        expected_packet_hash=expected_packet_hash,
        expected_artifact_hash=expected_artifact_hash,
        metadata=metadata,
        gate_evaluator=gate_evaluator,
    )
    return _record_canonical_human_gate_issuance(result)


def validate_canonical_human_gate_authority(
    gate_result: Any,
    *,
    expected_artifact_hash: str,
    expected_approval_decision_id: str,
    expected_audit_event_id: str,
    expected_contract_audit_event_id: str,
    expected_packet_hash: str | None = None,
) -> str:
    if type(gate_result) is not HumanDecisionPreArtifactGateResult:
        return "artifact write requires exact canonical human gate evidence"
    if not _is_canonically_issued_human_gate_result(gate_result):
        return "human gate evidence lacks canonical issuance provenance"
    if (
        gate_result.status != GATE_PASSED
        or gate_result.gate_evaluated is not True
        or gate_result.pre_artifact_gate_passed is not True
        or gate_result.decision != "APPROVE"
        or gate_result.blocking is not False
        or gate_result.durable_handoff_complete is not True
        or gate_result.artifact_write_occurred is not False
        or gate_result.provider_output_trusted is not False
        or gate_result.metadata_authority is not False
    ):
        return "canonical human gate evidence did not pass the pre-artifact boundary"

    packet_hash = _strict_full_hash(gate_result.packet_hash)
    artifact_hash = _strict_full_hash(gate_result.artifact_hash)
    expected_artifact = _strict_full_hash(expected_artifact_hash)
    if packet_hash is None or artifact_hash is None or expected_artifact is None:
        return "canonical human gate evidence lacks full packet or artifact hash binding"
    if expected_packet_hash is not None and packet_hash != _strict_full_hash(expected_packet_hash):
        return "canonical human gate packet hash does not match expected packet hash"
    if artifact_hash != expected_artifact:
        return "canonical human gate artifact hash does not match artifact content"

    nested_gate = gate_result.gate_result
    if type(nested_gate) is not PreArtifactApprovalGateResult:
        return "canonical human gate evidence lacks exact pre-artifact gate result"
    if not is_canonically_issued_pre_artifact_gate_result(nested_gate):
        return "pre-artifact gate evidence lacks canonical issuance provenance"
    if (
        nested_gate.allowed is not True
        or nested_gate.approval_decision_type != "APPROVE"
        or _nonempty_text(nested_gate.approval_decision_id) is None
        or _nonempty_text(nested_gate.audit_event_id) is None
        or _strict_full_hash(nested_gate.audit_event_hash) is None
    ):
        return "canonical human gate result is incomplete or not approved"
    if expected_approval_decision_id != nested_gate.approval_decision_id:
        return "artifact approval decision does not match canonical human gate"
    if expected_audit_event_id != nested_gate.audit_event_id:
        return "artifact audit event does not match canonical human gate"
    if expected_contract_audit_event_id != nested_gate.audit_event_id:
        return "artifact contract audit event does not match canonical human gate"
    return ""


def _evaluate_human_decision_pre_artifact_gate(
    *,
    handoff_result: DurableApprovalAuditHandoff | Mapping[str, Any],
    approval_decision: ApprovalDecision | Mapping[str, Any],
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    gate_evaluator: GateEvaluator = evaluate_pre_artifact_approval_gate,
) -> HumanDecisionPreArtifactGateResult:
    del metadata
    try:
        handoff = _handoff_mapping(handoff_result)
        packet_hash = _full_hash(handoff.get("packet_hash"))
        artifact_hash = _full_hash(handoff.get("artifact_hash"))
        expected_packet = _optional_expected_hash(expected_packet_hash)
        expected_artifact = _optional_expected_hash(expected_artifact_hash)

        if packet_hash is None:
            return _blocked(
                status=BLOCKED_MISSING_PACKET_HASH,
                reason="durable handoff must contain a full packet hash",
            )
        if expected_packet is not None and packet_hash != expected_packet:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_STATE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="durable handoff packet hash does not match expected packet hash",
            )
        if expected_artifact is not None and artifact_hash != expected_artifact:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_STATE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="durable handoff artifact hash does not match expected artifact hash",
            )
        if not _handoff_boundary_flags_are_safe(handoff):
            return _blocked(
                status=BLOCKED_INVALID_HANDOFF,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="durable handoff safety boundary flags are invalid",
            )

        decision_text = handoff.get("decision")
        status = handoff.get("status")
        if decision_text == "APPROVE" and status == HANDOFF_COMPLETE_APPROVE:
            expected_decision_type = ApprovalDecisionType.APPROVE
        elif decision_text == "REJECT" and status == HANDOFF_COMPLETE_REJECT:
            expected_decision_type = ApprovalDecisionType.REJECT
        else:
            return _blocked(
                status=BLOCKED_INVALID_HANDOFF,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="handoff is not a completed explicit human decision handoff",
            )

        decision = _approval_decision(approval_decision)
        low_level_handoff = _audit_handoff(handoff.get("audit_handoff"))
        _validate_binding(
            handoff=handoff,
            decision=decision,
            expected_decision_type=expected_decision_type,
            audit_handoff=low_level_handoff,
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
        )

        if expected_decision_type is ApprovalDecisionType.REJECT:
            return HumanDecisionPreArtifactGateResult(
                status=BLOCKED_REJECT,
                gate_evaluated=False,
                pre_artifact_gate_passed=False,
                decision="REJECT",
                blocking=True,
                durable_handoff_complete=True,
                artifact_write_occurred=False,
                provider_output_trusted=False,
                metadata_authority=False,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="human REJECT remains blocking and cannot reach pre-artifact gate",
                gate_result=None,
            )
        gate_result = gate_evaluator(
            approval_decision=decision,
            approval_audit_handoff_result=low_level_handoff,
        )
        if not isinstance(gate_result, PreArtifactApprovalGateResult):
            raise TypeError("gate evaluator must return PreArtifactApprovalGateResult")

        passed = gate_result.allowed is True
        if passed and not is_canonically_issued_pre_artifact_gate_result(gate_result):
            raise ValueError("pre-artifact gate result lacks canonical issuance provenance")
        if passed and (
            gate_result.approval_decision_id != decision.decision_id
            or gate_result.approval_decision_type != decision.decision_type.value
            or gate_result.audit_event_id != low_level_handoff.audit_event_id
            or gate_result.audit_event_hash != low_level_handoff.audit_event_hash
        ):
            raise ValueError("gate result does not match approval decision and durable handoff")
        return HumanDecisionPreArtifactGateResult(
            status=GATE_PASSED if passed else GATE_DENIED,
            gate_evaluated=True,
            pre_artifact_gate_passed=passed,
            decision="APPROVE",
            blocking=not passed,
            durable_handoff_complete=True,
            artifact_write_occurred=False,
            provider_output_trusted=False,
            metadata_authority=False,
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
            reason=gate_result.reason,
            gate_result=gate_result,
        )
    except Exception:
        return _blocked(
            status=ERROR_FAIL_CLOSED,
            reason="pre-artifact approval gate integration failed closed",
        )


def _record_canonical_human_gate_issuance(
    result: HumanDecisionPreArtifactGateResult,
) -> HumanDecisionPreArtifactGateResult:
    identity = id(result)

    def discard(reference: weakref.ReferenceType[HumanDecisionPreArtifactGateResult]) -> None:
        issuance = _ISSUED_HUMAN_GATE_RESULTS.get(identity)
        if issuance is not None and issuance[0] is reference:
            _ISSUED_HUMAN_GATE_RESULTS.pop(identity, None)

    _ISSUED_HUMAN_GATE_RESULTS[identity] = (
        weakref.ref(result, discard),
        _human_gate_fingerprint(result),
    )
    return result


def _is_canonically_issued_human_gate_result(value: Any) -> bool:
    if type(value) is not HumanDecisionPreArtifactGateResult:
        return False
    issuance = _ISSUED_HUMAN_GATE_RESULTS.get(id(value))
    if issuance is None:
        return False
    reference, fingerprint = issuance
    return reference() is value and fingerprint == _human_gate_fingerprint(value)


def _human_gate_fingerprint(
    result: HumanDecisionPreArtifactGateResult,
) -> tuple[Any, ...]:
    return (
        result.status,
        result.gate_evaluated,
        result.pre_artifact_gate_passed,
        result.decision,
        result.blocking,
        result.durable_handoff_complete,
        result.artifact_write_occurred,
        result.provider_output_trusted,
        result.metadata_authority,
        result.packet_hash,
        result.artifact_hash,
        result.reason,
        id(result.gate_result),
    )


def _handoff_mapping(
    handoff_result: DurableApprovalAuditHandoff | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(handoff_result, DurableApprovalAuditHandoff):
        return handoff_result.to_dict()
    if isinstance(handoff_result, Mapping):
        return dict(handoff_result)
    raise TypeError("handoff_result must be a DurableApprovalAuditHandoff or mapping")


def _handoff_boundary_flags_are_safe(handoff: Mapping[str, Any]) -> bool:
    return (
        handoff.get("handoff_created") is True
        and handoff.get("durable_handoff_complete") is True
        and handoff.get("pre_artifact_gate_passed") is False
        and handoff.get("artifact_write_occurred") is False
        and handoff.get("provider_output_trusted") is False
        and handoff.get("metadata_authority") is False
        and handoff.get("blocking") is True
    )


def _approval_decision(value: ApprovalDecision | Mapping[str, Any]) -> ApprovalDecision:
    if isinstance(value, ApprovalDecision):
        return ApprovalDecision(**value.to_dict())
    if isinstance(value, Mapping):
        return ApprovalDecision(**dict(value))
    raise TypeError("approval_decision must be an ApprovalDecision or mapping")


def _audit_handoff(value: Any) -> ApprovalDecisionAuditHandoffResult:
    if isinstance(value, ApprovalDecisionAuditHandoffResult):
        return ApprovalDecisionAuditHandoffResult(**value.to_dict())
    if isinstance(value, Mapping):
        return ApprovalDecisionAuditHandoffResult(**dict(value))
    raise TypeError("handoff result lacks approval audit handoff evidence")


def _validate_binding(
    *,
    handoff: Mapping[str, Any],
    decision: ApprovalDecision,
    expected_decision_type: ApprovalDecisionType,
    audit_handoff: ApprovalDecisionAuditHandoffResult,
    packet_hash: str,
    artifact_hash: str | None,
) -> None:
    if decision.decision_type is not expected_decision_type:
        raise ValueError("approval decision type does not match handoff")
    if decision.reviewed_exact_payload_hash != packet_hash:
        raise ValueError("approval decision packet hash does not match handoff")
    notes = _notes_mapping(decision.notes)
    if notes.get("packet_hash") != packet_hash:
        raise ValueError("approval decision notes packet hash does not match handoff")
    if notes.get("artifact_hash", "") != (artifact_hash or ""):
        raise ValueError("approval decision notes artifact hash does not match handoff")
    if notes.get("pre_artifact_gate_passed") != "False":
        raise ValueError("approval decision incorrectly claims gate passage")
    if notes.get("artifact_write_occurred") != "False":
        raise ValueError("approval decision incorrectly claims artifact write")
    if not notes.get("human_decision_capture_id"):
        raise ValueError("approval decision lacks human capture provenance")

    if not audit_handoff.completed:
        raise ValueError("approval audit handoff is not completed")
    if audit_handoff.approval_decision_id != decision.decision_id:
        raise ValueError("approval audit handoff decision id mismatch")
    if audit_handoff.approval_decision_type != decision.decision_type.value:
        raise ValueError("approval audit handoff decision type mismatch")
    if handoff.get("handoff_id") != audit_handoff.audit_event_id:
        raise ValueError("handoff event id mismatch")
    if handoff.get("event_hash") != audit_handoff.audit_event_hash:
        raise ValueError("handoff event hash mismatch")


def _notes_mapping(notes: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in notes.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise ValueError("approval decision notes are malformed")
        result[key] = value
    return result


def _blocked(
    *,
    status: str,
    reason: str,
    packet_hash: str | None = None,
    artifact_hash: str | None = None,
) -> HumanDecisionPreArtifactGateResult:
    return HumanDecisionPreArtifactGateResult(
        status=status,
        gate_evaluated=False,
        pre_artifact_gate_passed=False,
        decision="BLOCKED",
        blocking=True,
        durable_handoff_complete=False,
        artifact_write_occurred=False,
        provider_output_trusted=False,
        metadata_authority=False,
        packet_hash=packet_hash,
        artifact_hash=artifact_hash,
        reason=reason,
        gate_result=None,
    )


def _optional_expected_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _full_hash(value)
    if normalized is None:
        raise ValueError("expected hash must be a full SHA-256 value")
    return normalized


def _full_hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        return None
    return text


def _strict_full_hash(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) != 64:
        return None
    if value.strip() != value or any(
        character not in "0123456789abcdef" for character in value
    ):
        return None
    return value


def _nonempty_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
