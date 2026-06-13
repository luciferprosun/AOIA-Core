from __future__ import annotations

from runtime.schemas.human_approval_review import PENDING_DECISION_STATUS
from runtime.schemas.human_decision_capture import (
    ALLOWED_HUMAN_DECISIONS,
    HUMAN_DECISION_CAPTURE_VERSION,
    HumanDecisionCapture,
)


class HumanDecisionCapturePolicyError(ValueError):
    pass


class HumanDecisionCaptureInvalidError(HumanDecisionCapturePolicyError):
    pass


class HumanDecisionCaptureBlockedError(HumanDecisionCapturePolicyError):
    pass


def validate_human_decision_capture(capture: HumanDecisionCapture) -> None:
    if not isinstance(capture, HumanDecisionCapture):
        raise TypeError("capture must be a HumanDecisionCapture")
    if capture.decision_version != HUMAN_DECISION_CAPTURE_VERSION:
        raise HumanDecisionCaptureInvalidError("unsupported decision capture version")
    if capture.decision not in ALLOWED_HUMAN_DECISIONS:
        raise HumanDecisionCaptureInvalidError("decision capture must be approve or deny")
    if capture.decision_status_before != PENDING_DECISION_STATUS:
        raise HumanDecisionCaptureInvalidError("decision capture must bind to a pending review packet")
    if not capture.review_packet_id or not capture.review_packet_hash:
        raise HumanDecisionCaptureInvalidError("decision capture must bind to a review packet id and hash")
    assert_human_decision_capture_does_not_execute(capture)
    assert_human_decision_capture_does_not_write(capture)
    assert_human_decision_capture_is_not_approval_decision(capture)


def assert_human_decision_capture_does_not_execute(capture: HumanDecisionCapture) -> None:
    if not isinstance(capture, HumanDecisionCapture):
        raise TypeError("capture must be a HumanDecisionCapture")
    if capture.triggers_execution:
        raise HumanDecisionCaptureBlockedError("human decision capture cannot trigger execution")


def assert_human_decision_capture_does_not_write(capture: HumanDecisionCapture) -> None:
    if not isinstance(capture, HumanDecisionCapture):
        raise TypeError("capture must be a HumanDecisionCapture")
    if capture.writes_artifact or capture.writes_audit:
        raise HumanDecisionCaptureBlockedError("human decision capture cannot write artifacts or audit logs")


def assert_human_decision_capture_is_not_approval_decision(capture: HumanDecisionCapture) -> None:
    if not isinstance(capture, HumanDecisionCapture):
        raise TypeError("capture must be a HumanDecisionCapture")
    if capture.creates_approval_decision:
        raise HumanDecisionCaptureBlockedError("human decision capture does not create ApprovalDecision automatically")
