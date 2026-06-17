from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


SAFE_UI_STATES = frozenset(
    {
        "DRAFT_ONLY",
        "REVIEW_PACKET_READY",
        "AWAITING_HUMAN_DECISION",
        "HUMAN_REJECTED",
        "HUMAN_APPROVED_NOT_AUDITED",
        "APPROVED_AND_AUDIT_HANDOFF_COMPLETE",
        "PRE_ARTIFACT_GATE_PASSED",
        "ARTIFACT_WRITE_COMPLETE",
        "ARTIFACT_WRITE_BLOCKED",
        "STALE_OR_MISMATCHED_STATE",
        "ERROR_FAIL_CLOSED",
    }
)

NON_AUTHORITY_CONTEXT_KEYS = (
    "metadata",
    "tags",
    "hats",
    "tetrads",
    "geometry",
)


@dataclass(frozen=True)
class ReviewPacketView:
    display_state: str
    blocking: bool
    packet_id: str | None
    packet_hash: str | None
    artifact_hash: str | None
    human_decision_status: str
    audit_handoff_status: str
    pre_artifact_gate_status: str
    artifact_result_status: str
    artifact_write_occurred: bool
    provider_output_trust: str | None
    warnings: tuple[str, ...]
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_state": self.display_state,
            "blocking": self.blocking,
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "artifact_hash": self.artifact_hash,
            "human_decision_status": self.human_decision_status,
            "audit_handoff_status": self.audit_handoff_status,
            "pre_artifact_gate_status": self.pre_artifact_gate_status,
            "artifact_result_status": self.artifact_result_status,
            "artifact_write_occurred": self.artifact_write_occurred,
            "provider_output_trust": self.provider_output_trust,
            "warnings": self.warnings,
            "evidence": self.evidence,
        }


def render_review_packet_view(
    *,
    review_packet: Any | None = None,
    decision_capture: Any | None = None,
    approval_decision: Any | None = None,
    audit_handoff: Any | None = None,
    pre_artifact_gate: Any | None = None,
    artifact_result: Any | None = None,
    provider_output: Any | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ReviewPacketView:
    warnings: list[str] = []
    evidence: list[str] = []

    packet_id = _first_text(review_packet, ("packet_id", "id"))
    packet_hash = _first_text(review_packet, ("packet_hash", "review_packet_hash", "hash"))
    artifact_hash = _first_text(
        artifact_result,
        ("artifact_hash", "written_artifact_hash", "hash"),
    ) or _first_text(pre_artifact_gate, ("artifact_hash", "expected_artifact_hash"))

    if packet_id:
        evidence.append(f"packet_id:{packet_id}")
    if packet_hash:
        evidence.append(f"packet_hash:{packet_hash}")
    if artifact_hash:
        evidence.append(f"artifact_hash:{artifact_hash}")

    provider_output_trust = None
    if provider_output is not None:
        provider_output_trust = "UNTRUSTED"
        warnings.append("provider/model output is UNTRUSTED and non-authoritative")

    if _has_non_authority_claim(metadata):
        warnings.append("metadata/tags/hats/tetrads/geometry are display context only")

    human_decision_status = _human_decision_status(decision_capture, approval_decision)
    audit_handoff_status = _audit_handoff_status(audit_handoff)
    pre_artifact_gate_status = _gate_status(pre_artifact_gate)
    artifact_result_status = _artifact_result_status(artifact_result)

    display_state = _display_state(
        review_packet=review_packet,
        human_decision_status=human_decision_status,
        audit_handoff_status=audit_handoff_status,
        pre_artifact_gate_status=pre_artifact_gate_status,
        artifact_result_status=artifact_result_status,
    )
    if display_state not in SAFE_UI_STATES:
        display_state = "ERROR_FAIL_CLOSED"

    artifact_write_occurred = display_state == "ARTIFACT_WRITE_COMPLETE"
    blocking = display_state != "ARTIFACT_WRITE_COMPLETE"

    if display_state in {
        "AWAITING_HUMAN_DECISION",
        "HUMAN_REJECTED",
        "HUMAN_APPROVED_NOT_AUDITED",
        "APPROVED_AND_AUDIT_HANDOFF_COMPLETE",
        "PRE_ARTIFACT_GATE_PASSED",
        "ARTIFACT_WRITE_BLOCKED",
        "STALE_OR_MISMATCHED_STATE",
        "ERROR_FAIL_CLOSED",
    }:
        warnings.append(f"{display_state} is not artifact write completion")

    return ReviewPacketView(
        display_state=display_state,
        blocking=blocking,
        packet_id=packet_id,
        packet_hash=packet_hash,
        artifact_hash=artifact_hash,
        human_decision_status=human_decision_status,
        audit_handoff_status=audit_handoff_status,
        pre_artifact_gate_status=pre_artifact_gate_status,
        artifact_result_status=artifact_result_status,
        artifact_write_occurred=artifact_write_occurred,
        provider_output_trust=provider_output_trust,
        warnings=tuple(warnings),
        evidence=tuple(evidence),
    )


def _display_state(
    *,
    review_packet: Any | None,
    human_decision_status: str,
    audit_handoff_status: str,
    pre_artifact_gate_status: str,
    artifact_result_status: str,
) -> str:
    if artifact_result_status == "complete":
        return "ARTIFACT_WRITE_COMPLETE"
    if artifact_result_status == "blocked":
        return "ARTIFACT_WRITE_BLOCKED"
    if pre_artifact_gate_status == "passed":
        return "PRE_ARTIFACT_GATE_PASSED"
    if pre_artifact_gate_status in {"blocked", "mismatch", "stale"}:
        return "ARTIFACT_WRITE_BLOCKED"
    if human_decision_status == "reject":
        return "HUMAN_REJECTED"
    if human_decision_status == "approve" and audit_handoff_status == "complete":
        return "APPROVED_AND_AUDIT_HANDOFF_COMPLETE"
    if human_decision_status == "approve":
        return "HUMAN_APPROVED_NOT_AUDITED"
    if review_packet is not None and human_decision_status == "missing":
        return "AWAITING_HUMAN_DECISION"
    if review_packet is not None:
        return "REVIEW_PACKET_READY"
    return "ERROR_FAIL_CLOSED"


def _human_decision_status(decision_capture: Any | None, approval_decision: Any | None) -> str:
    raw = _first_text(approval_decision, ("decision_type", "decision", "status"))
    if raw is None:
        raw = _first_text(decision_capture, ("decision", "decision_type", "status"))
    value = _normalized(raw)
    if value in {"approve", "approved"}:
        return "approve"
    if value in {"reject", "rejected", "deny", "denied"}:
        return "reject"
    if value in {"blocked", "blocked_by_policy"}:
        return "blocked"
    return "missing"


def _audit_handoff_status(audit_handoff: Any | None) -> str:
    if audit_handoff is None:
        return "missing"
    completed = _read(audit_handoff, "completed")
    if completed is True:
        return "complete"
    status = _normalized(_first_text(audit_handoff, ("status", "audit_handoff_status")))
    if status in {"complete", "completed", "accepted"}:
        return "complete"
    if status in {"mismatch", "stale"}:
        return status
    return "missing"


def _gate_status(pre_artifact_gate: Any | None) -> str:
    if pre_artifact_gate is None:
        return "missing"
    allowed = _read(pre_artifact_gate, "allowed")
    if allowed is True:
        return "passed"
    if allowed is False:
        return "blocked"
    status = _normalized(_first_text(pre_artifact_gate, ("status", "gate_status")))
    if status in {"passed", "pass", "allowed"}:
        return "passed"
    if status in {"blocked", "failed", "deny", "denied"}:
        return "blocked"
    if status in {"mismatch", "stale"}:
        return status
    return "missing"


def _artifact_result_status(artifact_result: Any | None) -> str:
    if artifact_result is None:
        return "missing"
    completed = _read(artifact_result, "completed")
    if completed is True:
        return "complete"
    status = _normalized(_first_text(artifact_result, ("status", "artifact_status", "result")))
    if status in {"complete", "completed", "written", "write_complete"}:
        return "complete"
    if status in {"blocked", "failed", "rejected"}:
        return "blocked"
    return "missing"


def _has_non_authority_claim(metadata: Mapping[str, Any] | None) -> bool:
    if not metadata:
        return False
    for key in NON_AUTHORITY_CONTEXT_KEYS:
        value = metadata.get(key)
        if value:
            return True
    text = repr(metadata).lower()
    return any(token in text for token in ("approved", "canonical", "safe", "trusted"))


def _first_text(source: Any | None, names: tuple[str, ...]) -> str | None:
    for name in names:
        value = _read(source, name)
        if value is None:
            continue
        text = _string_value(value).strip()
        if text:
            return text
    return None


def _read(source: Any | None, name: str) -> Any | None:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _string_value(value: Any) -> str:
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return str(enum_value)
    return str(value)


def _normalized(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()
