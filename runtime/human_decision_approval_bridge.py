from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.human_decision_capture_helper import (
    CAPTURED_APPROVE,
    CAPTURED_REJECT,
    HumanDecisionCaptureIntent,
)
from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
)


BRIDGED_APPROVE = "BRIDGED_APPROVE"
BRIDGED_REJECT = "BRIDGED_REJECT"
BLOCKED_INVALID_CAPTURE = "BLOCKED_INVALID_CAPTURE"
BLOCKED_MISSING_PACKET_HASH = "BLOCKED_MISSING_PACKET_HASH"
BLOCKED_STALE_OR_MISMATCHED_CAPTURE = "BLOCKED_STALE_OR_MISMATCHED_CAPTURE"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"

APPROVAL_BRIDGE_PROPOSAL_TYPE = "human_decision_capture_intent"


@dataclass(frozen=True)
class CaptureApprovalBridgeResult:
    status: str
    decision: str | None
    approval_decision_created: bool
    approval_decision: ApprovalDecision | None
    packet_hash: str | None
    artifact_hash: str | None
    durable_handoff_required: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    provider_output_trusted: bool
    metadata_authority: bool
    blocking: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "decision": self.decision,
            "approval_decision_created": self.approval_decision_created,
            "approval_decision": (
                self.approval_decision.to_dict() if self.approval_decision is not None else None
            ),
            "packet_hash": self.packet_hash,
            "artifact_hash": self.artifact_hash,
            "durable_handoff_required": self.durable_handoff_required,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "provider_output_trusted": self.provider_output_trusted,
            "metadata_authority": self.metadata_authority,
            "blocking": self.blocking,
            "reason": self.reason,
        }


def build_approval_decision_from_capture(
    *,
    capture: HumanDecisionCaptureIntent | Mapping[str, Any],
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    review_packet_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CaptureApprovalBridgeResult:
    del metadata
    try:
        capture_data = _capture_mapping(capture)
        packet_hash = _full_hash(capture_data.get("packet_hash"))
        artifact_hash = _full_hash(capture_data.get("artifact_hash"))
        expected_packet = _optional_expected_hash(expected_packet_hash)
        expected_artifact = _optional_expected_hash(expected_artifact_hash)

        if packet_hash is None:
            return _blocked(
                status=BLOCKED_MISSING_PACKET_HASH,
                reason="capture must contain a full packet hash",
            )
        if not _capture_hashes_are_current(capture_data, packet_hash, artifact_hash):
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_CAPTURE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="capture contains stale or mismatched displayed/current hashes",
            )
        if expected_packet is not None and packet_hash != expected_packet:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_CAPTURE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="capture packet hash does not match expected packet hash",
            )
        if expected_artifact is not None and artifact_hash != expected_artifact:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_CAPTURE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="capture artifact hash does not match expected artifact hash",
            )
        if not _capture_boundary_flags_are_safe(capture_data):
            return _blocked(
                status=BLOCKED_INVALID_CAPTURE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="capture safety boundary flags are invalid",
            )

        decision = capture_data.get("decision")
        outcome_state = capture_data.get("outcome_state")
        if decision == "APPROVE" and outcome_state == CAPTURED_APPROVE:
            decision_type = ApprovalDecisionType.APPROVE
            status = BRIDGED_APPROVE
        elif decision == "REJECT" and outcome_state == CAPTURED_REJECT:
            decision_type = ApprovalDecisionType.REJECT
            status = BRIDGED_REJECT
        else:
            return _blocked(
                status=BLOCKED_INVALID_CAPTURE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="capture decision and outcome are not an explicit captured decision",
            )

        capture_id = _nonempty_text(capture_data.get("capture_id"))
        if capture_id is None:
            return _blocked(
                status=BLOCKED_INVALID_CAPTURE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="captured decision must have a capture id",
            )
        if capture_id != _expected_capture_id(
            decision=decision,
            packet_id=_nonempty_text(capture_data.get("packet_id")),
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
            human_actor=_nonempty_text(capture_data.get("human_actor")),
            reason=_nonempty_text(capture_data.get("reason")),
        ):
            return _blocked(
                status=BLOCKED_INVALID_CAPTURE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="capture id does not match capture content",
            )

        packet_id = _nonempty_text(review_packet_id) or _nonempty_text(capture_data.get("packet_id"))
        actor_id = _nonempty_text(capture_data.get("human_actor")) or ""
        reason = _nonempty_text(capture_data.get("reason")) or f"explicit human {decision} capture"
        approval_decision = ApprovalDecision(
            decision_id=_approval_decision_id(
                capture_id=capture_id,
                decision=decision,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
            ),
            created_at="",
            proposal_id=packet_id or packet_hash,
            proposal_type=APPROVAL_BRIDGE_PROPOSAL_TYPE,
            decision_type=decision_type,
            decision_state=ApprovalDecisionState.RECORDED,
            actor_type=ApprovalActorType.HUMAN_REVIEWER,
            actor_id=actor_id,
            reason=reason,
            reviewed_exact_payload_hash=packet_hash,
            reviewed_payload_summary=_reviewed_summary(packet_hash, artifact_hash),
            human_reviewed=True,
            provider_generated=False,
            policy_blocked=False,
            execution_permitted=False,
            execution_triggered=False,
            expires_at="",
            audit_event_id="",
            notes=_approval_notes(capture_id, packet_hash, artifact_hash),
            allowed=False,
            approval_state="requires_human_review",
            dry_run=True,
            requires_human_review=True,
        )
        return CaptureApprovalBridgeResult(
            status=status,
            decision=decision,
            approval_decision_created=True,
            approval_decision=approval_decision,
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
            durable_handoff_required=True,
            pre_artifact_gate_passed=False,
            artifact_write_occurred=False,
            provider_output_trusted=False,
            metadata_authority=False,
            blocking=True,
            reason=(
                "approval decision created; durable handoff is still required"
                if decision == "APPROVE"
                else "human REJECT captured as a blocking approval decision"
            ),
        )
    except (TypeError, ValueError):
        return _blocked(
            status=ERROR_FAIL_CLOSED,
            reason="capture approval bridge failed closed",
        )


def _capture_mapping(
    capture: HumanDecisionCaptureIntent | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(capture, HumanDecisionCaptureIntent):
        return capture.to_dict()
    if isinstance(capture, Mapping):
        return dict(capture)
    raise TypeError("capture must be a HumanDecisionCaptureIntent or mapping")


def _capture_hashes_are_current(
    capture: Mapping[str, Any],
    packet_hash: str,
    artifact_hash: str | None,
) -> bool:
    displayed_packet = _full_hash(capture.get("displayed_packet_hash"))
    current_packet = _full_hash(capture.get("current_packet_hash"))
    if displayed_packet != packet_hash or current_packet != packet_hash:
        return False

    displayed_artifact_raw = capture.get("displayed_artifact_hash")
    current_artifact_raw = capture.get("current_artifact_hash")
    if artifact_hash is None:
        return displayed_artifact_raw is None and current_artifact_raw is None
    return (
        _full_hash(displayed_artifact_raw) == artifact_hash
        and _full_hash(current_artifact_raw) == artifact_hash
    )


def _capture_boundary_flags_are_safe(capture: Mapping[str, Any]) -> bool:
    return (
        capture.get("decision_captured") is True
        and capture.get("is_approval_authority") is False
        and capture.get("durable_audit_handoff_required") is True
        and capture.get("pre_artifact_gate_passed") is False
        and capture.get("artifact_write_occurred") is False
    )


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


def _expected_capture_id(
    *,
    decision: str,
    packet_id: str | None,
    packet_hash: str,
    artifact_hash: str | None,
    human_actor: str | None,
    reason: str | None,
) -> str:
    material = json.dumps(
        {
            "decision": decision,
            "packet_id": packet_id,
            "packet_hash": packet_hash,
            "artifact_hash": artifact_hash,
            "human_actor": human_actor,
            "reason": reason,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "human-decision-intent-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _reviewed_summary(packet_hash: str, artifact_hash: str | None) -> str:
    summary = f"human decision capture bound to packet_hash={packet_hash}"
    if artifact_hash is not None:
        summary += f" artifact_hash={artifact_hash}"
    return summary


def _approval_notes(capture_id: str, packet_hash: str, artifact_hash: str | None) -> str:
    return "\n".join(
        (
            f"human_decision_capture_id={capture_id}",
            f"packet_hash={packet_hash}",
            f"artifact_hash={artifact_hash or ''}",
            "durable_audit_handoff_required=True",
            "pre_artifact_gate_passed=False",
            "artifact_write_occurred=False",
        )
    )


def _blocked(
    *,
    status: str,
    reason: str,
    packet_hash: str | None = None,
    artifact_hash: str | None = None,
) -> CaptureApprovalBridgeResult:
    return CaptureApprovalBridgeResult(
        status=status,
        decision=None,
        approval_decision_created=False,
        approval_decision=None,
        packet_hash=packet_hash,
        artifact_hash=artifact_hash,
        durable_handoff_required=True,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        provider_output_trusted=False,
        metadata_authority=False,
        blocking=True,
        reason=reason,
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


def _nonempty_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
