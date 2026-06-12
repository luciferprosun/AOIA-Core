from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from runtime.schemas.action_proposal import ActionProposal
from runtime.schemas.approval_decision import ApprovalDecision
from runtime.schemas.evidence_memory import EvidenceMemoryRecord
from runtime.schemas.provider_critic import ProviderCritiqueRecord


class AuditEventType(str, Enum):
    PROVIDER_CRITIQUE_RECORDED = "PROVIDER_CRITIQUE_RECORDED"
    PROVIDER_CALL_BLOCKED = "PROVIDER_CALL_BLOCKED"
    EVIDENCE_RECORD_CREATED = "EVIDENCE_RECORD_CREATED"
    EVIDENCE_WRITE_BLOCKED = "EVIDENCE_WRITE_BLOCKED"
    ACTION_PROPOSAL_CREATED = "ACTION_PROPOSAL_CREATED"
    APPROVAL_DECISION_RECORDED = "APPROVAL_DECISION_RECORDED"
    APPROVAL_BLOCKED = "APPROVAL_BLOCKED"
    EXECUTION_BLOCKED = "EXECUTION_BLOCKED"
    POLICY_BLOCK_RECORDED = "POLICY_BLOCK_RECORDED"


class AuditEventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
    CRITICAL = "CRITICAL"


class AuditEventTrustState(str, Enum):
    LOCAL_SYSTEM_RECORDED = "LOCAL_SYSTEM_RECORDED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    POLICY_RECORDED = "POLICY_RECORDED"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_mapping(value: dict[str, Any]) -> str:
    return _hash_text(_canonical_json(value))


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _coerce_bool(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")
    return value


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    created_at: str
    event_type: AuditEventType
    severity: AuditEventSeverity
    trust_state: AuditEventTrustState
    subject_id: str
    subject_type: str
    actor_id: str
    actor_type: str
    action: str
    result: str
    reason: str
    previous_event_hash: str = ""
    event_hash: str = ""
    payload_hash: str = ""
    redaction_applied: bool = False
    provider_generated: bool = False
    execution_authorized: bool = False
    execution_triggered: bool = False
    canonical_write_authorized: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        event_type = AuditEventType(self.event_type)
        severity = AuditEventSeverity(self.severity)
        trust_state = AuditEventTrustState(self.trust_state)

        object.__setattr__(self, "event_id", _coerce_text("event_id", self.event_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "trust_state", trust_state)
        object.__setattr__(self, "subject_id", _coerce_text("subject_id", self.subject_id))
        object.__setattr__(self, "subject_type", _coerce_text("subject_type", self.subject_type))
        object.__setattr__(self, "actor_id", _coerce_text("actor_id", self.actor_id))
        object.__setattr__(self, "actor_type", _coerce_text("actor_type", self.actor_type))
        object.__setattr__(self, "action", _coerce_text("action", self.action))
        object.__setattr__(self, "result", _coerce_text("result", self.result))
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))
        object.__setattr__(self, "previous_event_hash", _coerce_text("previous_event_hash", self.previous_event_hash))
        object.__setattr__(self, "payload_hash", _coerce_text("payload_hash", self.payload_hash))
        object.__setattr__(self, "redaction_applied", _coerce_bool("redaction_applied", self.redaction_applied))
        object.__setattr__(self, "provider_generated", _coerce_bool("provider_generated", self.provider_generated))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

        if self.execution_authorized is not False:
            raise ValueError("execution_authorized must remain False in M5-A")
        if self.execution_triggered is not False:
            raise ValueError("execution_triggered must remain False in M5-A")
        if self.canonical_write_authorized is not False:
            raise ValueError("canonical_write_authorized must remain False in M5-A")
        object.__setattr__(self, "execution_authorized", False)
        object.__setattr__(self, "execution_triggered", False)
        object.__setattr__(self, "canonical_write_authorized", False)

        if self.provider_generated:
            object.__setattr__(self, "trust_state", AuditEventTrustState.PROVIDER_UNTRUSTED)

        computed_hash = compute_audit_event_hash(self)
        object.__setattr__(self, "event_hash", computed_hash)
        if not self.event_id:
            object.__setattr__(self, "event_id", "audit-event-" + computed_hash[:24])

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "created_at": self.created_at,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "trust_state": self.trust_state.value,
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "action": self.action,
            "result": self.result,
            "reason": self.reason,
            "previous_event_hash": self.previous_event_hash,
            "event_hash": self.event_hash,
            "payload_hash": self.payload_hash,
            "redaction_applied": self.redaction_applied,
            "provider_generated": self.provider_generated,
            "execution_authorized": self.execution_authorized,
            "execution_triggered": self.execution_triggered,
            "canonical_write_authorized": self.canonical_write_authorized,
            "notes": self.notes,
        }


def _hash_payload(event: AuditEvent) -> dict[str, Any]:
    return {
        "created_at": event.created_at,
        "event_type": AuditEventType(event.event_type).value,
        "severity": AuditEventSeverity(event.severity).value,
        "trust_state": AuditEventTrustState(event.trust_state).value,
        "subject_id": event.subject_id,
        "subject_type": event.subject_type,
        "actor_id": event.actor_id,
        "actor_type": event.actor_type,
        "action": event.action,
        "result": event.result,
        "reason": event.reason,
        "previous_event_hash": event.previous_event_hash,
        "payload_hash": event.payload_hash,
        "redaction_applied": event.redaction_applied,
        "provider_generated": event.provider_generated,
        "execution_authorized": False,
        "execution_triggered": False,
        "canonical_write_authorized": False,
        "notes": event.notes,
    }


def compute_audit_event_hash(event: AuditEvent) -> str:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    return _hash_mapping(_hash_payload(event))


def _base_event(
    *,
    event_type: AuditEventType,
    severity: AuditEventSeverity,
    trust_state: AuditEventTrustState,
    subject_id: str,
    subject_type: str,
    actor_id: str,
    actor_type: str,
    action: str,
    result: str,
    reason: str,
    previous_event_hash: str = "",
    payload_hash: str = "",
    redaction_applied: bool = False,
    provider_generated: bool = False,
    notes: str = "",
    created_at: str | None = None,
    event_id: str = "",
) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        created_at=created_at or _utc_now_iso(),
        event_type=event_type,
        severity=severity,
        trust_state=trust_state,
        subject_id=subject_id,
        subject_type=subject_type,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        result=result,
        reason=reason,
        previous_event_hash=previous_event_hash,
        payload_hash=payload_hash,
        redaction_applied=redaction_applied,
        provider_generated=provider_generated,
        execution_authorized=False,
        execution_triggered=False,
        canonical_write_authorized=False,
        notes=notes,
    )


def create_action_proposal_audit_event(
    proposal: ActionProposal,
    previous_event_hash: str = "",
) -> AuditEvent:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    return _base_event(
        event_type=AuditEventType.ACTION_PROPOSAL_CREATED,
        severity=AuditEventSeverity.INFO,
        trust_state=AuditEventTrustState.LOCAL_SYSTEM_RECORDED,
        subject_id=proposal.proposal_id,
        subject_type="ActionProposal",
        actor_id=proposal.proposed_by,
        actor_type="proposal_source",
        action="record_action_proposal",
        result=proposal.state.value,
        reason=proposal.description,
        previous_event_hash=previous_event_hash,
        payload_hash=_hash_text(proposal.exact_payload),
        provider_generated=proposal.provider_generated,
        notes=proposal.notes,
    )


def create_approval_decision_audit_event(
    decision: ApprovalDecision,
    previous_event_hash: str = "",
) -> AuditEvent:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    severity = AuditEventSeverity.INFO
    trust_state = AuditEventTrustState.HUMAN_REVIEWED if decision.human_reviewed else AuditEventTrustState.POLICY_RECORDED
    if decision.policy_blocked:
        severity = AuditEventSeverity.BLOCKED
    if decision.provider_generated:
        trust_state = AuditEventTrustState.PROVIDER_UNTRUSTED
    return _base_event(
        event_type=AuditEventType.APPROVAL_DECISION_RECORDED,
        severity=severity,
        trust_state=trust_state,
        subject_id=decision.decision_id,
        subject_type="ApprovalDecision",
        actor_id=decision.actor_id,
        actor_type=decision.actor_type.value,
        action="record_approval_decision",
        result=decision.decision_type.value,
        reason=decision.reason,
        previous_event_hash=previous_event_hash,
        payload_hash=_hash_mapping(decision.to_dict()),
        provider_generated=decision.provider_generated,
        notes=decision.notes,
    )


def create_policy_block_audit_event(
    subject_id: str,
    subject_type: str,
    reason: str,
    previous_event_hash: str = "",
) -> AuditEvent:
    return _base_event(
        event_type=AuditEventType.POLICY_BLOCK_RECORDED,
        severity=AuditEventSeverity.BLOCKED,
        trust_state=AuditEventTrustState.POLICY_RECORDED,
        subject_id=subject_id,
        subject_type=subject_type,
        actor_id="system-policy",
        actor_type="SYSTEM_POLICY",
        action="record_policy_block",
        result="blocked",
        reason=reason,
        previous_event_hash=previous_event_hash,
        payload_hash=_hash_text("\n".join([subject_id, subject_type, reason])),
    )


def create_execution_blocked_audit_event(
    subject_id: str,
    subject_type: str,
    reason: str,
    previous_event_hash: str = "",
) -> AuditEvent:
    return _base_event(
        event_type=AuditEventType.EXECUTION_BLOCKED,
        severity=AuditEventSeverity.BLOCKED,
        trust_state=AuditEventTrustState.POLICY_RECORDED,
        subject_id=subject_id,
        subject_type=subject_type,
        actor_id="runtime-policy",
        actor_type="SYSTEM_POLICY",
        action="block_execution",
        result="execution_blocked",
        reason=reason,
        previous_event_hash=previous_event_hash,
        payload_hash=_hash_text("\n".join([subject_id, subject_type, reason])),
    )


def create_provider_critique_audit_event(
    record: ProviderCritiqueRecord,
    previous_event_hash: str = "",
) -> AuditEvent:
    if not isinstance(record, ProviderCritiqueRecord):
        raise TypeError("record must be a ProviderCritiqueRecord")
    return _base_event(
        event_type=AuditEventType.PROVIDER_CRITIQUE_RECORDED,
        severity=AuditEventSeverity.WARNING,
        trust_state=AuditEventTrustState.PROVIDER_UNTRUSTED,
        subject_id=record.record_id,
        subject_type="ProviderCritiqueRecord",
        actor_id=record.source_provider,
        actor_type="PROVIDER_MODEL",
        action="record_provider_critique",
        result=record.trust_level.value,
        reason=record.prompt_summary,
        previous_event_hash=previous_event_hash,
        payload_hash=_hash_mapping(record.to_dict()),
        redaction_applied=record.redaction_applied,
        provider_generated=True,
        notes=record.notes,
    )


def create_evidence_record_audit_event(
    record: EvidenceMemoryRecord,
    previous_event_hash: str = "",
) -> AuditEvent:
    if not isinstance(record, EvidenceMemoryRecord):
        raise TypeError("record must be an EvidenceMemoryRecord")
    return _base_event(
        event_type=AuditEventType.EVIDENCE_RECORD_CREATED,
        severity=AuditEventSeverity.INFO,
        trust_state=AuditEventTrustState.LOCAL_SYSTEM_RECORDED,
        subject_id=record.evidence_id,
        subject_type="EvidenceMemoryRecord",
        actor_id=record.provenance.collector,
        actor_type=record.source_type.value,
        action="record_evidence_candidate",
        result=record.trust_state.value,
        reason=record.provenance.notes,
        previous_event_hash=previous_event_hash,
        payload_hash=record.content_hash,
        provider_generated=record.provider_generated,
        notes=record.notes,
    )


def audit_event_to_dict(event: AuditEvent) -> dict[str, Any]:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    return event.to_dict()
