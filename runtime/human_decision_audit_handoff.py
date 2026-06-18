from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runtime.human_decision_approval_bridge import (
    APPROVAL_BRIDGE_PROPOSAL_TYPE,
    BRIDGED_APPROVE,
    BRIDGED_REJECT,
    CaptureApprovalBridgeResult,
)
from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
)
from runtime.safety.approval_decision_audit_handoff import (
    ApprovalDecisionAuditHandoffResult,
    record_approval_decision_to_durable_audit,
)


HANDOFF_COMPLETE_APPROVE = "HANDOFF_COMPLETE_APPROVE"
HANDOFF_COMPLETE_REJECT = "HANDOFF_COMPLETE_REJECT"
BLOCKED_INVALID_BRIDGE = "BLOCKED_INVALID_BRIDGE"
BLOCKED_MISSING_PACKET_HASH = "BLOCKED_MISSING_PACKET_HASH"
BLOCKED_STALE_OR_MISMATCHED_STATE = "BLOCKED_STALE_OR_MISMATCHED_STATE"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"


@dataclass(frozen=True)
class DurableApprovalAuditHandoff:
    status: str
    handoff_created: bool
    handoff_id: str | None
    event_hash: str | None
    audit_log_path: str | None
    decision: str
    packet_hash: str | None
    artifact_hash: str | None
    blocking: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    provider_output_trusted: bool
    metadata_authority: bool
    reason: str
    audit_handoff: ApprovalDecisionAuditHandoffResult | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "handoff_created": self.handoff_created,
            "handoff_id": self.handoff_id,
            "event_hash": self.event_hash,
            "audit_log_path": self.audit_log_path,
            "decision": self.decision,
            "packet_hash": self.packet_hash,
            "artifact_hash": self.artifact_hash,
            "blocking": self.blocking,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "provider_output_trusted": self.provider_output_trusted,
            "metadata_authority": self.metadata_authority,
            "reason": self.reason,
            "audit_handoff": (
                self.audit_handoff.to_dict() if self.audit_handoff is not None else None
            ),
        }


def create_durable_approval_audit_handoff(
    *,
    bridge_result: CaptureApprovalBridgeResult | Mapping[str, Any],
    audit_dir: str | Path,
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    expected_previous_hash: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> DurableApprovalAuditHandoff:
    del metadata
    try:
        bridge = _bridge_mapping(bridge_result)
        packet_hash = _full_hash(bridge.get("packet_hash"))
        artifact_hash = _full_hash(bridge.get("artifact_hash"))
        expected_packet = _optional_expected_hash(expected_packet_hash)
        expected_artifact = _optional_expected_hash(expected_artifact_hash)

        if packet_hash is None:
            return _blocked(
                status=BLOCKED_MISSING_PACKET_HASH,
                reason="bridge result must contain a full packet hash",
            )
        if expected_packet is not None and packet_hash != expected_packet:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_STATE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="bridge packet hash does not match expected packet hash",
            )
        if expected_artifact is not None and artifact_hash != expected_artifact:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_STATE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="bridge artifact hash does not match expected artifact hash",
            )
        if not _bridge_boundary_flags_are_safe(bridge):
            return _blocked(
                status=BLOCKED_INVALID_BRIDGE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="bridge safety boundary flags are invalid",
            )

        decision_text = bridge.get("decision")
        bridge_status = bridge.get("status")
        if decision_text == "APPROVE" and bridge_status == BRIDGED_APPROVE:
            decision_type = ApprovalDecisionType.APPROVE
            completed_status = HANDOFF_COMPLETE_APPROVE
        elif decision_text == "REJECT" and bridge_status == BRIDGED_REJECT:
            decision_type = ApprovalDecisionType.REJECT
            completed_status = HANDOFF_COMPLETE_REJECT
        else:
            return _blocked(
                status=BLOCKED_INVALID_BRIDGE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="bridge status is not an explicit captured human decision",
            )

        decision = _approval_decision(bridge.get("approval_decision"))
        capture_id = _validate_decision_binding(
            decision=decision,
            decision_type=decision_type,
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
        )
        expected_decision_id = _approval_decision_id(
            capture_id=capture_id,
            decision=decision_text,
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
        )
        if decision.decision_id != expected_decision_id:
            return _blocked(
                status=BLOCKED_INVALID_BRIDGE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="approval decision id does not match bridge provenance",
            )

        audit_result = record_approval_decision_to_durable_audit(
            approval_decision=decision,
            audit_dir=audit_dir,
            expected_previous_hash=expected_previous_hash,
        )
        if not audit_result.completed:
            return DurableApprovalAuditHandoff(
                status=ERROR_FAIL_CLOSED,
                handoff_created=False,
                handoff_id=None,
                event_hash=None,
                audit_log_path=None,
                decision=decision_text,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                blocking=True,
                durable_handoff_complete=False,
                pre_artifact_gate_passed=False,
                artifact_write_occurred=False,
                provider_output_trusted=False,
                metadata_authority=False,
                reason=audit_result.reason,
                audit_handoff=audit_result,
            )

        return DurableApprovalAuditHandoff(
            status=completed_status,
            handoff_created=True,
            handoff_id=audit_result.audit_event_id,
            event_hash=audit_result.audit_event_hash,
            audit_log_path=audit_result.audit_log_path,
            decision=decision_text,
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
            blocking=True,
            durable_handoff_complete=True,
            pre_artifact_gate_passed=False,
            artifact_write_occurred=False,
            provider_output_trusted=False,
            metadata_authority=False,
            reason=(
                "durable approval audit handoff complete; pre-artifact gate remains required"
                if decision_text == "APPROVE"
                else "durable rejection audit handoff complete; REJECT remains blocking"
            ),
            audit_handoff=audit_result,
        )
    except (TypeError, ValueError):
        return _blocked(
            status=ERROR_FAIL_CLOSED,
            reason="durable approval audit handoff failed closed",
        )


def _bridge_mapping(
    bridge_result: CaptureApprovalBridgeResult | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(bridge_result, CaptureApprovalBridgeResult):
        return bridge_result.to_dict()
    if isinstance(bridge_result, Mapping):
        return dict(bridge_result)
    raise TypeError("bridge_result must be a CaptureApprovalBridgeResult or mapping")


def _bridge_boundary_flags_are_safe(bridge: Mapping[str, Any]) -> bool:
    return (
        bridge.get("approval_decision_created") is True
        and bridge.get("durable_handoff_required") is True
        and bridge.get("pre_artifact_gate_passed") is False
        and bridge.get("artifact_write_occurred") is False
        and bridge.get("provider_output_trusted") is False
        and bridge.get("metadata_authority") is False
        and bridge.get("blocking") is True
    )


def _approval_decision(value: Any) -> ApprovalDecision:
    if isinstance(value, ApprovalDecision):
        return ApprovalDecision(**value.to_dict())
    if isinstance(value, Mapping):
        return ApprovalDecision(**dict(value))
    raise TypeError("bridge result must contain an ApprovalDecision")


def _validate_decision_binding(
    *,
    decision: ApprovalDecision,
    decision_type: ApprovalDecisionType,
    packet_hash: str,
    artifact_hash: str | None,
) -> str:
    if decision.decision_type is not decision_type:
        raise ValueError("approval decision type does not match bridge decision")
    if decision.decision_state is not ApprovalDecisionState.RECORDED:
        raise ValueError("approval decision must be recorded")
    if decision.actor_type is not ApprovalActorType.HUMAN_REVIEWER or not decision.human_reviewed:
        raise ValueError("approval decision must come from a human reviewer")
    if decision.provider_generated or decision.execution_permitted or decision.execution_triggered:
        raise ValueError("approval decision carries forbidden authority flags")
    if decision.proposal_type != APPROVAL_BRIDGE_PROPOSAL_TYPE:
        raise ValueError("approval decision does not come from the M6-F1 bridge")
    if decision.reviewed_exact_payload_hash != packet_hash:
        raise ValueError("approval decision packet hash does not match bridge packet hash")

    notes = _notes_mapping(decision.notes)
    capture_id = notes.get("human_decision_capture_id")
    if not capture_id:
        raise ValueError("approval decision lacks explicit human capture provenance")
    if notes.get("packet_hash") != packet_hash:
        raise ValueError("approval decision notes packet hash does not match")
    if notes.get("artifact_hash", "") != (artifact_hash or ""):
        raise ValueError("approval decision notes artifact hash does not match")
    if notes.get("durable_audit_handoff_required") != "True":
        raise ValueError("approval decision does not require durable handoff")
    if notes.get("pre_artifact_gate_passed") != "False":
        raise ValueError("approval decision incorrectly claims gate passage")
    if notes.get("artifact_write_occurred") != "False":
        raise ValueError("approval decision incorrectly claims artifact write")
    return capture_id


def _notes_mapping(notes: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in notes.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise ValueError("approval decision notes are malformed")
        result[key] = value
    return result


def _approval_decision_id(
    *,
    capture_id: str,
    decision: str,
    packet_hash: str,
    artifact_hash: str | None,
) -> str:
    material = json.dumps(
        {
            "capture_id": capture_id,
            "decision": decision,
            "packet_hash": packet_hash,
            "artifact_hash": artifact_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "approval-decision-from-capture-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _blocked(
    *,
    status: str,
    reason: str,
    packet_hash: str | None = None,
    artifact_hash: str | None = None,
) -> DurableApprovalAuditHandoff:
    return DurableApprovalAuditHandoff(
        status=status,
        handoff_created=False,
        handoff_id=None,
        event_hash=None,
        audit_log_path=None,
        decision="BLOCKED",
        packet_hash=packet_hash,
        artifact_hash=artifact_hash,
        blocking=True,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        provider_output_trusted=False,
        metadata_authority=False,
        reason=reason,
        audit_handoff=None,
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
