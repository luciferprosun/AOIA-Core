from __future__ import annotations

from runtime.schemas.human_approval_review import (
    ALLOWED_HUMAN_REVIEW_DECISIONS,
    DEFAULT_SAFETY_BOUNDARIES,
    HUMAN_APPROVAL_REVIEW_PACKET_VERSION,
    PENDING_DECISION_STATUS,
    HumanApprovalReviewPacket,
)


class HumanApprovalReviewPolicyError(ValueError):
    pass


class HumanApprovalReviewInvalidPacketError(HumanApprovalReviewPolicyError):
    pass


class HumanApprovalReviewNotApprovalError(HumanApprovalReviewPolicyError):
    pass


def validate_human_approval_review_packet(packet: HumanApprovalReviewPacket) -> None:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("packet must be a HumanApprovalReviewPacket")
    if packet.packet_version != HUMAN_APPROVAL_REVIEW_PACKET_VERSION:
        raise HumanApprovalReviewInvalidPacketError("unsupported review packet version")
    assert_review_packet_is_not_approval(packet)
    assert_review_packet_does_not_execute(packet)
    assert_review_packet_does_not_write(packet)
    if packet.allowed_decisions != ALLOWED_HUMAN_REVIEW_DECISIONS:
        raise HumanApprovalReviewInvalidPacketError("review packet allowed decisions changed")
    missing = set(DEFAULT_SAFETY_BOUNDARIES).difference(packet.safety_boundaries)
    if missing:
        raise HumanApprovalReviewInvalidPacketError("review packet is missing required safety boundaries")


def assert_review_packet_is_not_approval(packet: HumanApprovalReviewPacket) -> None:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("packet must be a HumanApprovalReviewPacket")
    if packet.decision_status != PENDING_DECISION_STATUS:
        raise HumanApprovalReviewNotApprovalError("review packet is not an approval and must remain pending")
    if packet.decision_required is not True:
        raise HumanApprovalReviewNotApprovalError("review packet must require a separate human decision")


def assert_review_packet_does_not_execute(packet: HumanApprovalReviewPacket) -> None:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("packet must be a HumanApprovalReviewPacket")
    required = {"no_shell_execution", "no_provider_api_network", "no_browser_git_cloud", "no_db_sqlite_orm"}
    if not required.issubset(set(packet.safety_boundaries)):
        raise HumanApprovalReviewInvalidPacketError("review packet execution safety boundaries are incomplete")


def assert_review_packet_does_not_write(packet: HumanApprovalReviewPacket) -> None:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("packet must be a HumanApprovalReviewPacket")
    if "durable_audit_required" not in packet.safety_boundaries:
        raise HumanApprovalReviewInvalidPacketError("review packet must require durable audit before later artifact flow")
    if "artifact_write_only" not in packet.safety_boundaries:
        raise HumanApprovalReviewInvalidPacketError("review packet must restrict future action to artifact write only")
