from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ProviderTrustLevel(str, Enum):
    UNTRUSTED = "UNTRUSTED"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _coerce_nonnegative_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


@dataclass(frozen=True)
class ProviderCritiqueRecord:
    record_id: str
    created_at: str
    source_provider: str
    source_model: str
    request_hash: str
    prompt_summary: str
    response_text: str
    trust_level: ProviderTrustLevel = ProviderTrustLevel.UNTRUSTED
    untrusted: bool = True
    human_reviewed: bool = False
    evidence_write_allowed: bool = False
    canonical_write_allowed: bool = False
    action_approval_allowed: bool = False
    execution_allowed: bool = False
    cost_estimate: str = "UNKNOWN"
    token_estimate: int = 0
    redaction_applied: bool = False
    audit_event_id: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _coerce_text("record_id", self.record_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "source_provider", _coerce_text("source_provider", self.source_provider))
        object.__setattr__(self, "source_model", _coerce_text("source_model", self.source_model))
        object.__setattr__(self, "request_hash", _coerce_text("request_hash", self.request_hash))
        object.__setattr__(self, "prompt_summary", _coerce_text("prompt_summary", self.prompt_summary))
        object.__setattr__(self, "response_text", _coerce_text("response_text", self.response_text))
        object.__setattr__(self, "cost_estimate", _coerce_text("cost_estimate", self.cost_estimate))
        object.__setattr__(self, "token_estimate", _coerce_nonnegative_int("token_estimate", self.token_estimate))
        object.__setattr__(self, "redaction_applied", bool(self.redaction_applied))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

        object.__setattr__(self, "trust_level", ProviderTrustLevel.UNTRUSTED)
        object.__setattr__(self, "untrusted", True)
        object.__setattr__(self, "human_reviewed", False)
        object.__setattr__(self, "evidence_write_allowed", False)
        object.__setattr__(self, "canonical_write_allowed", False)
        object.__setattr__(self, "action_approval_allowed", False)
        object.__setattr__(self, "execution_allowed", False)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["trust_level"] = self.trust_level.value
        return payload


def create_inert_provider_critique_record(
    *,
    source_provider: str,
    source_model: str,
    request_text: str = "",
    request_hash: str | None = None,
    prompt_summary: str = "",
    response_text: str = "",
    cost_estimate: str = "UNKNOWN",
    token_estimate: int = 0,
    redaction_applied: bool = False,
    audit_event_id: str = "",
    notes: str = "",
    created_at: str | None = None,
    record_id: str | None = None,
    **attempted_safety_flags: Any,
) -> ProviderCritiqueRecord:
    created_at_value = created_at or _utc_now_iso()
    request_hash_value = request_hash or _hash_text(request_text)
    record_id_value = record_id or "provider-critic-" + _hash_text(
        "\n".join(
            [
                source_provider,
                source_model,
                request_hash_value,
                response_text,
                created_at_value,
                audit_event_id,
            ]
        )
    )[:24]
    attempted_notes = notes
    if attempted_safety_flags:
        attempted = ",".join(sorted(attempted_safety_flags))
        attempted_notes = f"{notes} attempted_flags={attempted}".strip()

    payload: dict[str, Any] = {
        "record_id": record_id_value,
        "created_at": created_at_value,
        "source_provider": source_provider,
        "source_model": source_model,
        "request_hash": request_hash_value,
        "prompt_summary": prompt_summary,
        "response_text": response_text,
        "cost_estimate": cost_estimate,
        "token_estimate": token_estimate,
        "redaction_applied": redaction_applied,
        "audit_event_id": audit_event_id,
        "notes": attempted_notes,
    }
    payload.update(attempted_safety_flags)
    return ProviderCritiqueRecord(**payload)
