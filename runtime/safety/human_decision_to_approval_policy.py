from __future__ import annotations

import hashlib

from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
)
from runtime.schemas.human_approval_review import (
    PENDING_DECISION_STATUS,
    HumanApprovalReviewPacket,
    human_approval_review_packet_to_dict,
)
from runtime.schemas.human_decision_capture import (
    ALLOWED_HUMAN_DECISIONS,
    HumanDecisionCapture,
    hash_human_approval_review_packet,
    human_decision_capture_to_dict,
)
from runtime.safety.human_approval_review_policy import validate_human_approval_review_packet
from runtime.safety.human_decision_capture_policy import validate_human_decision_capture


APPROVAL_BRIDGE_PROPOSAL_TYPE = "human_approval_review_packet"


class HumanDecisionToApprovalPolicyError(ValueError):
    pass


def create_approval_decision_from_human_capture(
    *,
    review_packet: HumanApprovalReviewPacket,
    decision_capture: HumanDecisionCapture,
) -> ApprovalDecision:
    packet = _validated_review_packet(review_packet)
    capture = _validated_decision_capture(decision_capture)
    expected_packet_hash = hash_human_approval_review_packet(packet)

    if packet.decision_status != PENDING_DECISION_STATUS:
        raise HumanDecisionToApprovalPolicyError("review packet must still be pending")
    if capture.review_packet_id != packet.packet_id:
        raise HumanDecisionToApprovalPolicyError("decision capture review packet id does not match")
    if capture.review_packet_hash != expected_packet_hash:
        raise HumanDecisionToApprovalPolicyError("decision capture review packet hash does not match")
    if capture.decision not in ALLOWED_HUMAN_DECISIONS:
        raise HumanDecisionToApprovalPolicyError("decision capture must be approve or deny")

    decision_type = ApprovalDecisionType.APPROVE if capture.decision == "approve" else ApprovalDecisionType.REJECT
    decision_id = _approval_decision_id(packet=packet, capture=capture, decision_type=decision_type)
    notes = _approval_notes(packet=packet, capture=capture, packet_hash=expected_packet_hash)

    return ApprovalDecision(
        decision_id=decision_id,
        created_at=capture.captured_at,
        proposal_id=packet.proposal_id or packet.packet_id,
        proposal_type=APPROVAL_BRIDGE_PROPOSAL_TYPE,
        decision_type=decision_type,
        decision_state=ApprovalDecisionState.RECORDED,
        actor_type=ApprovalActorType.HUMAN_REVIEWER,
        actor_id=capture.reviewer_id,
        reason=capture.reason or f"human decision capture: {capture.decision}",
        reviewed_exact_payload_hash=expected_packet_hash,
        reviewed_payload_summary=packet.proposed_action_summary,
        human_reviewed=True,
        provider_generated=False,
        policy_blocked=False,
        execution_permitted=False,
        execution_triggered=False,
        expires_at="",
        audit_event_id="",
        notes=notes,
        allowed=False,
        approval_state="requires_human_review",
        dry_run=True,
        requires_human_review=True,
    )


def _validated_review_packet(packet: HumanApprovalReviewPacket) -> HumanApprovalReviewPacket:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("review_packet must be a HumanApprovalReviewPacket")
    try:
        validated = HumanApprovalReviewPacket(**human_approval_review_packet_to_dict(packet))
        validate_human_approval_review_packet(validated)
    except (TypeError, ValueError) as exc:
        raise HumanDecisionToApprovalPolicyError("review packet is not valid for approval bridge") from exc
    return validated


def _validated_decision_capture(capture: HumanDecisionCapture) -> HumanDecisionCapture:
    if not isinstance(capture, HumanDecisionCapture):
        raise TypeError("decision_capture must be a HumanDecisionCapture")
    try:
        validated = HumanDecisionCapture(**human_decision_capture_to_dict(capture))
        validate_human_decision_capture(validated)
    except (TypeError, ValueError) as exc:
        raise HumanDecisionToApprovalPolicyError("decision capture is not valid for approval bridge") from exc
    return validated


def _approval_decision_id(
    *,
    packet: HumanApprovalReviewPacket,
    capture: HumanDecisionCapture,
    decision_type: ApprovalDecisionType,
) -> str:
    material = "\n".join(
        (
            packet.packet_id,
            capture.review_packet_hash,
            capture.decision_id,
            capture.decision_hash,
            decision_type.value,
            capture.reviewer_id,
            capture.captured_at,
        )
    )
    return "approval-decision-from-human-capture-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _approval_notes(
    *,
    packet: HumanApprovalReviewPacket,
    capture: HumanDecisionCapture,
    packet_hash: str,
) -> str:
    return "\n".join(
        (
            f"review_packet_id={packet.packet_id}",
            f"review_packet_hash={packet_hash}",
            f"human_decision_capture_id={capture.decision_id}",
            f"human_decision_capture_hash={capture.decision_hash}",
            f"human_decision={capture.decision}",
            "execution_permitted=False",
            "execution_triggered=False",
        )
    )
