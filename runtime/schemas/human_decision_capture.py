from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from runtime.schemas.human_approval_review import (
    ALLOWED_HUMAN_REVIEW_DECISIONS,
    HumanApprovalReviewPacket,
    PENDING_DECISION_STATUS,
    human_approval_review_packet_to_dict,
)


HUMAN_DECISION_CAPTURE_VERSION = "AOIA_HUMAN_DECISION_CAPTURE_V1"
MAX_HUMAN_DECISION_REVIEWER_ID_BYTES = 128
ALLOWED_HUMAN_DECISIONS = ALLOWED_HUMAN_REVIEW_DECISIONS


@dataclass(frozen=True)
class HumanDecisionCapture:
    decision_version: str
    decision_id: str
    decision_hash: str
    review_packet_id: str
    review_packet_hash: str
    decision: str
    reviewer_id: str
    captured_at: str
    decision_status_before: str
    creates_approval_decision: bool
    writes_artifact: bool
    writes_audit: bool
    triggers_execution: bool
    reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_version", _require_text("decision_version", self.decision_version))
        if self.decision_version != HUMAN_DECISION_CAPTURE_VERSION:
            raise ValueError("decision_version is not supported")
        object.__setattr__(self, "review_packet_id", _require_text("review_packet_id", self.review_packet_id))
        object.__setattr__(self, "review_packet_hash", _require_text("review_packet_hash", self.review_packet_hash))
        object.__setattr__(self, "decision", _validate_decision(self.decision))
        object.__setattr__(self, "reviewer_id", _validate_reviewer_id(self.reviewer_id))
        object.__setattr__(self, "captured_at", _require_text("captured_at", self.captured_at))
        _reject_control_characters("captured_at", self.captured_at, allow_tab_newline=False)
        object.__setattr__(
            self,
            "decision_status_before",
            _require_text("decision_status_before", self.decision_status_before),
        )
        if self.decision_status_before != PENDING_DECISION_STATUS:
            raise ValueError("decision_status_before must be pending")
        object.__setattr__(self, "creates_approval_decision", _require_false("creates_approval_decision", self.creates_approval_decision))
        object.__setattr__(self, "writes_artifact", _require_false("writes_artifact", self.writes_artifact))
        object.__setattr__(self, "writes_audit", _require_false("writes_audit", self.writes_audit))
        object.__setattr__(self, "triggers_execution", _require_false("triggers_execution", self.triggers_execution))
        object.__setattr__(self, "reason", _optional_reason(self.reason))

        expected_hash = _decision_hash_for(self)
        supplied_hash = _coerce_text("decision_hash", self.decision_hash)
        if supplied_hash and supplied_hash != expected_hash:
            raise ValueError("decision_hash does not match decision capture content")
        object.__setattr__(self, "decision_hash", expected_hash)

        expected_id = "human-decision-capture-" + expected_hash[:24]
        supplied_id = _coerce_text("decision_id", self.decision_id)
        if supplied_id and supplied_id != expected_id:
            raise ValueError("decision_id does not match decision capture content")
        object.__setattr__(self, "decision_id", expected_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_version": self.decision_version,
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "review_packet_id": self.review_packet_id,
            "review_packet_hash": self.review_packet_hash,
            "decision": self.decision,
            "reviewer_id": self.reviewer_id,
            "captured_at": self.captured_at,
            "decision_status_before": self.decision_status_before,
            "creates_approval_decision": self.creates_approval_decision,
            "writes_artifact": self.writes_artifact,
            "writes_audit": self.writes_audit,
            "triggers_execution": self.triggers_execution,
            "reason": self.reason,
        }


def capture_human_decision(
    *,
    review_packet: HumanApprovalReviewPacket,
    decision: str,
    reviewer_id: str,
    captured_at: str | None = None,
    reason: str | None = None,
) -> HumanDecisionCapture:
    if not isinstance(review_packet, HumanApprovalReviewPacket):
        raise TypeError("review_packet must be a HumanApprovalReviewPacket")
    if review_packet.decision_status != PENDING_DECISION_STATUS:
        raise ValueError("review_packet must still be pending")
    return HumanDecisionCapture(
        decision_version=HUMAN_DECISION_CAPTURE_VERSION,
        decision_id="",
        decision_hash="",
        review_packet_id=review_packet.packet_id,
        review_packet_hash=hash_human_approval_review_packet(review_packet),
        decision=decision,
        reviewer_id=reviewer_id,
        captured_at=captured_at or _utc_now_iso(),
        decision_status_before=review_packet.decision_status,
        creates_approval_decision=False,
        writes_artifact=False,
        writes_audit=False,
        triggers_execution=False,
        reason=reason,
    )


def hash_human_approval_review_packet(packet: HumanApprovalReviewPacket) -> str:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("packet must be a HumanApprovalReviewPacket")
    return _hash_mapping(human_approval_review_packet_to_dict(packet))


def render_human_decision_capture_markdown(capture: HumanDecisionCapture) -> str:
    if not isinstance(capture, HumanDecisionCapture):
        raise TypeError("capture must be a HumanDecisionCapture")
    return "\n".join(
        (
            "# Human Decision Capture",
            "",
            f"Decision version: {capture.decision_version}",
            f"Decision id: {capture.decision_id}",
            f"Review packet id: {capture.review_packet_id}",
            f"Decision: {capture.decision}",
            f"Reviewer id: {capture.reviewer_id}",
            f"Captured at: {capture.captured_at}",
            f"Previous packet decision status: {capture.decision_status_before}",
            "",
            "## Non-Execution Flags",
            f"Creates approval decision: {capture.creates_approval_decision}",
            f"Writes artifact: {capture.writes_artifact}",
            f"Writes audit: {capture.writes_audit}",
            f"Triggers execution: {capture.triggers_execution}",
            "",
            "## Reason",
            capture.reason or "not provided",
            "",
        )
    )


def human_decision_capture_to_dict(capture: HumanDecisionCapture) -> dict[str, Any]:
    if not isinstance(capture, HumanDecisionCapture):
        raise TypeError("capture must be a HumanDecisionCapture")
    return capture.to_dict()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _decision_hash_for(capture: HumanDecisionCapture) -> str:
    return _hash_mapping(
        {
            "decision_version": capture.decision_version,
            "review_packet_id": capture.review_packet_id,
            "review_packet_hash": capture.review_packet_hash,
            "decision": capture.decision,
            "reviewer_id": capture.reviewer_id,
            "captured_at": capture.captured_at,
            "decision_status_before": capture.decision_status_before,
            "creates_approval_decision": capture.creates_approval_decision,
            "writes_artifact": capture.writes_artifact,
            "writes_audit": capture.writes_audit,
            "triggers_execution": capture.triggers_execution,
            "reason": capture.reason,
        }
    )


def _hash_mapping(value: dict[str, Any]) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _validate_decision(value: str) -> str:
    raw = _coerce_text("decision", value)
    _reject_control_characters("decision", raw, allow_tab_newline=False)
    text = raw.strip()
    if not text:
        raise ValueError("decision must not be blank")
    if text not in ALLOWED_HUMAN_DECISIONS:
        raise ValueError("decision must be approve or deny")
    return text


def _validate_reviewer_id(value: str) -> str:
    raw = _coerce_text("reviewer_id", value)
    _reject_control_characters("reviewer_id", raw, allow_tab_newline=False)
    text = raw.strip()
    if not text:
        raise ValueError("reviewer_id must not be blank")
    if len(text.encode("utf-8")) > MAX_HUMAN_DECISION_REVIEWER_ID_BYTES:
        raise ValueError("reviewer_id is too long")
    return text


def _optional_reason(value: str | None) -> str | None:
    if value is None:
        return None
    text = _coerce_text("reason", value).strip()
    if not text:
        return None
    _reject_control_characters("reason", text, allow_tab_newline=True)
    return text


def _require_false(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")
    if value is not False:
        raise ValueError(f"{name} must remain False")
    return False


def _require_text(name: str, value: str) -> str:
    text = _coerce_text(name, value).strip()
    if not text:
        raise ValueError(f"{name} must not be blank")
    return text


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _reject_control_characters(name: str, value: str, *, allow_tab_newline: bool) -> None:
    allowed = ("\n", "\t") if allow_tab_newline else ()
    for character in value:
        codepoint = ord(character)
        if (codepoint < 32 and character not in allowed) or codepoint == 127:
            raise ValueError(f"{name} contains a blocked control character")
