from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


CAPTURED_APPROVE = "CAPTURED_APPROVE"
CAPTURED_REJECT = "CAPTURED_REJECT"
BLOCKED_STALE_OR_MISMATCHED_PACKET = "BLOCKED_STALE_OR_MISMATCHED_PACKET"
BLOCKED_MISSING_PACKET_HASH = "BLOCKED_MISSING_PACKET_HASH"
BLOCKED_INVALID_DECISION = "BLOCKED_INVALID_DECISION"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"

ALLOWED_CAPTURE_OUTCOMES = frozenset(
    {
        CAPTURED_APPROVE,
        CAPTURED_REJECT,
        BLOCKED_STALE_OR_MISMATCHED_PACKET,
        BLOCKED_MISSING_PACKET_HASH,
        BLOCKED_INVALID_DECISION,
        ERROR_FAIL_CLOSED,
    }
)

EXPLICIT_DECISIONS = frozenset({"APPROVE", "REJECT"})


@dataclass(frozen=True)
class HumanDecisionCaptureIntent:
    capture_id: str | None
    outcome_state: str
    decision: str | None
    decision_captured: bool
    blocking: bool
    packet_id: str | None
    packet_hash: str | None
    artifact_hash: str | None
    displayed_packet_hash: str | None
    displayed_artifact_hash: str | None
    current_packet_hash: str | None
    current_artifact_hash: str | None
    human_actor: str | None
    reason: str | None
    metadata_ignored: bool
    is_approval_authority: bool
    durable_audit_handoff_required: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    messages: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "outcome_state": self.outcome_state,
            "decision": self.decision,
            "decision_captured": self.decision_captured,
            "blocking": self.blocking,
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "artifact_hash": self.artifact_hash,
            "displayed_packet_hash": self.displayed_packet_hash,
            "displayed_artifact_hash": self.displayed_artifact_hash,
            "current_packet_hash": self.current_packet_hash,
            "current_artifact_hash": self.current_artifact_hash,
            "human_actor": self.human_actor,
            "reason": self.reason,
            "metadata_ignored": self.metadata_ignored,
            "is_approval_authority": self.is_approval_authority,
            "durable_audit_handoff_required": self.durable_audit_handoff_required,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "messages": self.messages,
        }


def capture_human_decision_intent(
    *,
    decision: str | None = None,
    displayed_packet_hash: str | None = None,
    current_packet_hash: str | None = None,
    packet_id: str | None = None,
    displayed_artifact_hash: str | None = None,
    current_artifact_hash: str | None = None,
    human_actor: str | None = None,
    reason: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> HumanDecisionCaptureIntent:
    normalized_packet_id, packet_id_valid = _optional_text(packet_id)
    normalized_actor, actor_valid = _optional_text(human_actor)
    normalized_reason, reason_valid = _optional_text(reason)
    if not packet_id_valid or not actor_valid or not reason_valid:
        return _result(
            outcome_state=ERROR_FAIL_CLOSED,
            decision=None,
            packet_id=normalized_packet_id,
            displayed_packet_hash=None,
            current_packet_hash=None,
            displayed_artifact_hash=None,
            current_artifact_hash=None,
            human_actor=normalized_actor,
            reason=normalized_reason,
            metadata_ignored=metadata is not None,
            messages=("invalid non-decision input; capture failed closed",),
        )
    if metadata is not None and not isinstance(metadata, Mapping):
        return _result(
            outcome_state=ERROR_FAIL_CLOSED,
            decision=None,
            packet_id=normalized_packet_id,
            displayed_packet_hash=None,
            current_packet_hash=None,
            displayed_artifact_hash=None,
            current_artifact_hash=None,
            human_actor=normalized_actor,
            reason=normalized_reason,
            metadata_ignored=True,
            messages=("metadata input is malformed; capture failed closed",),
        )

    normalized_decision = _explicit_decision(decision)
    if normalized_decision is None:
        return _result(
            outcome_state=BLOCKED_INVALID_DECISION,
            decision=None,
            packet_id=normalized_packet_id,
            displayed_packet_hash=_full_hash(displayed_packet_hash),
            current_packet_hash=_full_hash(current_packet_hash),
            displayed_artifact_hash=_full_hash(displayed_artifact_hash),
            current_artifact_hash=_full_hash(current_artifact_hash),
            human_actor=normalized_actor,
            reason=normalized_reason,
            metadata_ignored=bool(metadata),
            messages=("decision must be explicitly APPROVE or REJECT",),
        )

    displayed_packet = _full_hash(displayed_packet_hash)
    current_packet = _full_hash(current_packet_hash)
    if displayed_packet is None or current_packet is None:
        return _result(
            outcome_state=BLOCKED_MISSING_PACKET_HASH,
            decision=normalized_decision,
            packet_id=normalized_packet_id,
            displayed_packet_hash=displayed_packet,
            current_packet_hash=current_packet,
            displayed_artifact_hash=_full_hash(displayed_artifact_hash),
            current_artifact_hash=_full_hash(current_artifact_hash),
            human_actor=normalized_actor,
            reason=normalized_reason,
            metadata_ignored=bool(metadata),
            messages=("full displayed and current packet hashes are required",),
        )
    if displayed_packet != current_packet:
        return _result(
            outcome_state=BLOCKED_STALE_OR_MISMATCHED_PACKET,
            decision=normalized_decision,
            packet_id=normalized_packet_id,
            displayed_packet_hash=displayed_packet,
            current_packet_hash=current_packet,
            displayed_artifact_hash=_full_hash(displayed_artifact_hash),
            current_artifact_hash=_full_hash(current_artifact_hash),
            human_actor=normalized_actor,
            reason=normalized_reason,
            metadata_ignored=bool(metadata),
            messages=("displayed packet hash does not match current packet hash",),
        )

    artifact_context_present = displayed_artifact_hash is not None or current_artifact_hash is not None
    displayed_artifact = _full_hash(displayed_artifact_hash)
    current_artifact = _full_hash(current_artifact_hash)
    if artifact_context_present and (
        displayed_artifact is None
        or current_artifact is None
        or displayed_artifact != current_artifact
    ):
        return _result(
            outcome_state=BLOCKED_STALE_OR_MISMATCHED_PACKET,
            decision=normalized_decision,
            packet_id=normalized_packet_id,
            displayed_packet_hash=displayed_packet,
            current_packet_hash=current_packet,
            displayed_artifact_hash=displayed_artifact,
            current_artifact_hash=current_artifact,
            human_actor=normalized_actor,
            reason=normalized_reason,
            metadata_ignored=bool(metadata),
            messages=("displayed artifact hash does not match current artifact hash",),
        )

    outcome_state = CAPTURED_APPROVE if normalized_decision == "APPROVE" else CAPTURED_REJECT
    messages = [
        "capture intent is not approval authority",
        "durable audit handoff is still required",
        "pre-artifact gate is not passed by capture",
        "no artifact write occurred",
    ]
    if metadata:
        messages.append("metadata was ignored for decision authority")
    if normalized_decision == "REJECT":
        messages.append("REJECT is blocking")

    return _result(
        outcome_state=outcome_state,
        decision=normalized_decision,
        packet_id=normalized_packet_id,
        displayed_packet_hash=displayed_packet,
        current_packet_hash=current_packet,
        displayed_artifact_hash=displayed_artifact,
        current_artifact_hash=current_artifact,
        human_actor=normalized_actor,
        reason=normalized_reason,
        metadata_ignored=bool(metadata),
        messages=tuple(messages),
    )


def _result(
    *,
    outcome_state: str,
    decision: str | None,
    packet_id: str | None,
    displayed_packet_hash: str | None,
    current_packet_hash: str | None,
    displayed_artifact_hash: str | None,
    current_artifact_hash: str | None,
    human_actor: str | None,
    reason: str | None,
    metadata_ignored: bool,
    messages: tuple[str, ...],
) -> HumanDecisionCaptureIntent:
    if outcome_state not in ALLOWED_CAPTURE_OUTCOMES:
        outcome_state = ERROR_FAIL_CLOSED
        messages = ("unknown capture outcome; capture failed closed",)

    decision_captured = outcome_state in {CAPTURED_APPROVE, CAPTURED_REJECT}
    capture_id = None
    if decision_captured and decision is not None and current_packet_hash is not None:
        capture_id = _capture_id(
            decision=decision,
            packet_id=packet_id,
            packet_hash=current_packet_hash,
            artifact_hash=current_artifact_hash,
            human_actor=human_actor,
            reason=reason,
        )

    return HumanDecisionCaptureIntent(
        capture_id=capture_id,
        outcome_state=outcome_state,
        decision=decision,
        decision_captured=decision_captured,
        blocking=True,
        packet_id=packet_id,
        packet_hash=current_packet_hash,
        artifact_hash=current_artifact_hash,
        displayed_packet_hash=displayed_packet_hash,
        displayed_artifact_hash=displayed_artifact_hash,
        current_packet_hash=current_packet_hash,
        current_artifact_hash=current_artifact_hash,
        human_actor=human_actor,
        reason=reason,
        metadata_ignored=metadata_ignored,
        is_approval_authority=False,
        durable_audit_handoff_required=True,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        messages=messages,
    )


def _capture_id(
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


def _explicit_decision(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    decision = value.strip()
    if decision not in EXPLICIT_DECISIONS:
        return None
    return decision


def _full_hash(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) != 64:
        return None
    if any(character.lower() not in "0123456789abcdef" for character in text):
        return None
    return text.lower()


def _optional_text(value: str | None) -> tuple[str | None, bool]:
    if value is None:
        return None, True
    if not isinstance(value, str):
        return None, False
    text = value.strip()
    return (text or None), True
