from __future__ import annotations

from runtime.schemas.audit_event import (
    AuditEvent,
    AuditEventTrustState,
    audit_event_to_dict,
    compute_audit_event_hash,
)


class AuditEventMutationBlockedError(RuntimeError):
    pass


class AuditEventExecutionBlockedError(RuntimeError):
    pass


class AuditEventChainBlockedError(RuntimeError):
    pass


class ProviderAuditAuthorityBlockedError(RuntimeError):
    pass


def assert_audit_event_does_not_execute(event: AuditEvent) -> None:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    if event.execution_authorized or event.execution_triggered:
        raise AuditEventExecutionBlockedError("AuditEvent cannot authorize or trigger execution")
    raise AuditEventExecutionBlockedError("AuditEvent records only; it does not execute")


def assert_audit_event_cannot_authorize_execution(event: AuditEvent) -> None:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    if event.execution_authorized or event.execution_triggered:
        raise AuditEventExecutionBlockedError("AuditEvent execution authority is blocked")
    raise AuditEventExecutionBlockedError("AuditEvent cannot authorize execution in M5-A")


def assert_provider_event_has_no_authority(event: AuditEvent) -> None:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    if not event.provider_generated:
        return
    if event.trust_state is not AuditEventTrustState.PROVIDER_UNTRUSTED:
        raise ProviderAuditAuthorityBlockedError("provider-generated audit events must remain untrusted")
    if event.execution_authorized or event.execution_triggered or event.canonical_write_authorized:
        raise ProviderAuditAuthorityBlockedError("provider-generated audit events have no authority")


def assert_append_only_chain(previous_event: AuditEvent, next_event: AuditEvent) -> None:
    if not isinstance(previous_event, AuditEvent):
        raise TypeError("previous_event must be an AuditEvent")
    if not isinstance(next_event, AuditEvent):
        raise TypeError("next_event must be an AuditEvent")
    assert_audit_event_hash_valid(previous_event)
    assert_audit_event_hash_valid(next_event)
    if next_event.previous_event_hash != previous_event.event_hash:
        raise AuditEventChainBlockedError("next event previous_event_hash must match previous event_hash")


def assert_audit_event_hash_valid(event: AuditEvent) -> None:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    if event.event_hash != compute_audit_event_hash(event):
        raise AuditEventChainBlockedError("audit event hash mismatch")


def append_audit_event_in_memory(
    existing_events: tuple[AuditEvent, ...] | list[AuditEvent],
    new_event: AuditEvent,
) -> tuple[AuditEvent, ...]:
    if not isinstance(new_event, AuditEvent):
        raise TypeError("new_event must be an AuditEvent")
    existing_tuple = tuple(existing_events)
    for event in existing_tuple:
        if not isinstance(event, AuditEvent):
            raise TypeError("existing_events must contain AuditEvent objects")
        assert_audit_event_hash_valid(event)
    assert_audit_event_hash_valid(new_event)
    if existing_tuple:
        assert_append_only_chain(existing_tuple[-1], new_event)
    if new_event.execution_authorized or new_event.execution_triggered or new_event.canonical_write_authorized:
        raise AuditEventExecutionBlockedError("audit event authority flags are blocked")
    if new_event.provider_generated:
        assert_provider_event_has_no_authority(new_event)
    audit_event_to_dict(new_event)
    return existing_tuple + (new_event,)
