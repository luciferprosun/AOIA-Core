from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from runtime.safety.provider_redaction import (
    contains_unredacted_provider_secret,
    redact_provider_secret,
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _require_nonnegative_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


@dataclass(frozen=True)
class ProviderAttemptAuditRecord:
    audit_event_id: str
    created_at: str
    provider_name: str
    model_name: str
    request_hash: str
    attempted: bool
    blocked: bool
    block_reason: str
    enabled_flag_present: bool
    network_allowed: bool
    estimated_tokens: int
    estimated_cost: str
    redaction_applied: bool
    secret_present_after_redaction: bool
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "audit_event_id", _require_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "created_at", _require_text("created_at", self.created_at))
        object.__setattr__(self, "provider_name", _require_text("provider_name", self.provider_name))
        object.__setattr__(self, "model_name", _require_text("model_name", self.model_name))
        object.__setattr__(self, "request_hash", _require_text("request_hash", self.request_hash))
        object.__setattr__(self, "attempted", bool(self.attempted))
        object.__setattr__(self, "blocked", True)
        object.__setattr__(self, "block_reason", _require_text("block_reason", self.block_reason))
        object.__setattr__(self, "enabled_flag_present", bool(self.enabled_flag_present))
        object.__setattr__(self, "network_allowed", False)
        object.__setattr__(self, "estimated_tokens", _require_nonnegative_int("estimated_tokens", self.estimated_tokens))
        object.__setattr__(self, "estimated_cost", _require_text("estimated_cost", self.estimated_cost))
        object.__setattr__(self, "redaction_applied", bool(self.redaction_applied))
        object.__setattr__(self, "secret_present_after_redaction", bool(self.secret_present_after_redaction))
        object.__setattr__(self, "notes", _require_text("notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_blocked_provider_attempt_audit(
    *,
    provider_name: str,
    model_name: str,
    request_text: str,
    block_reason: str,
    enabled_flag_present: bool = False,
    network_allowed: bool = False,
    estimated_tokens: int = 0,
    estimated_cost: str = "0",
    notes: str = "",
    known_secrets: list[str] | None = None,
    created_at: str | None = None,
    audit_event_id: str | None = None,
) -> ProviderAttemptAuditRecord:
    provider_value = redact_provider_secret(_require_text("provider_name", provider_name), known_secrets)
    model_value = redact_provider_secret(_require_text("model_name", model_name), known_secrets)
    reason_value = redact_provider_secret(_require_text("block_reason", block_reason), known_secrets)
    notes_value = redact_provider_secret(_require_text("notes", notes), known_secrets)
    request_value = _require_text("request_text", request_text)
    created_at_value = created_at or _utc_now_iso()
    event_id_value = audit_event_id or "provider-attempt-" + _hash_text(
        "\n".join([provider_value, model_value, _hash_text(request_value), created_at_value])
    )[:24]
    redaction_applied = (
        provider_value != provider_name
        or model_value != model_name
        or reason_value != block_reason
        or notes_value != notes
    )
    combined_redacted = "\n".join([provider_value, model_value, reason_value, notes_value])

    return ProviderAttemptAuditRecord(
        audit_event_id=event_id_value,
        created_at=created_at_value,
        provider_name=provider_value,
        model_name=model_value,
        request_hash=_hash_text(request_value),
        attempted=True,
        blocked=True,
        block_reason=reason_value,
        enabled_flag_present=enabled_flag_present,
        network_allowed=network_allowed,
        estimated_tokens=estimated_tokens,
        estimated_cost=estimated_cost,
        redaction_applied=redaction_applied,
        secret_present_after_redaction=contains_unredacted_provider_secret(combined_redacted, known_secrets),
        notes=notes_value,
    )


def audit_record_to_dict(record: ProviderAttemptAuditRecord) -> dict[str, Any]:
    if not isinstance(record, ProviderAttemptAuditRecord):
        raise TypeError("record must be a ProviderAttemptAuditRecord")
    return record.to_dict()
