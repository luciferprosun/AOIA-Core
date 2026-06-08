from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class ProviderAuditEvent:
    event_id: str
    timestamp_utc: str
    provider_id: str
    model_id: str
    status: str
    reason: str
    call_made: bool = False
    human_approved: bool = False
    provider_call_permitted: bool = False
    provider_output_trusted: bool = False
    execution_triggered: bool = False
    canonical_promotion_triggered: bool = False
    automatic_fallback_used: bool = False
    secrets_redacted: bool = True

    def __post_init__(self) -> None:
        if self.provider_output_trusted is not False:
            raise ValueError("provider output must remain untrusted")
        if self.execution_triggered is not False:
            raise ValueError("provider output must not trigger execution")
        if self.canonical_promotion_triggered is not False:
            raise ValueError("provider output must not trigger canonical promotion")
        if self.automatic_fallback_used is not False:
            raise ValueError("automatic fallback must remain disabled")
        if self.secrets_redacted is not True:
            raise ValueError("audit events must keep secrets redacted")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def make_provider_audit_event(
    *,
    provider_id: str,
    model_id: str,
    status: str,
    reason: str,
    call_made: bool = False,
    human_approved: bool = False,
    provider_call_permitted: bool = False,
) -> ProviderAuditEvent:
    return ProviderAuditEvent(
        event_id=f"provider-audit-{uuid4().hex}",
        timestamp_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        provider_id=provider_id,
        model_id=model_id,
        status=status,
        reason=reason,
        call_made=call_made,
        human_approved=human_approved,
        provider_call_permitted=provider_call_permitted,
    )
