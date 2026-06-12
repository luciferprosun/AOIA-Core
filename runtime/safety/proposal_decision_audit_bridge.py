from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.safety.action_proposal_policy import assert_action_proposal_is_inert
from runtime.safety.approval_decision_policy import (
    ApprovalDoesNotExecuteError,
    assert_approval_requires_human,
    assert_decision_matches_proposal,
    assert_provider_cannot_approve,
    assert_timeout_does_not_approve,
    assert_unknown_actor_cannot_approve,
    evaluate_approval_decision_for_execution,
)
from runtime.safety.audit_event_policy import (
    AuditEventExecutionBlockedError,
    append_audit_event_in_memory,
    assert_audit_event_hash_valid,
)
from runtime.schemas.action_proposal import ActionProposal
from runtime.schemas.approval_decision import ApprovalDecision, ApprovalDecisionType
from runtime.schemas.audit_event import (
    AuditEvent,
    create_action_proposal_audit_event,
    create_approval_decision_audit_event,
    create_execution_blocked_audit_event,
    create_policy_block_audit_event,
)


BRIDGE_STATUS_PROPOSAL_RECORDED = "proposal_audited_m5_b"
BRIDGE_STATUS_DECISION_RECORDED = "decision_audited_m5_b"
BRIDGE_STATUS_POLICY_BLOCK_RECORDED = "policy_block_audited_m5_b"
BRIDGE_STATUS_EXECUTION_BLOCKED_RECORDED = "execution_blocked_audited_m5_b"


@dataclass(frozen=True)
class ProposalDecisionAuditResult:
    proposal_id: str
    decision_id: str
    audit_event_id: str
    bridge_status: str
    execution_permitted: bool
    execution_triggered: bool
    audit_chain_length: int
    latest_event_hash: str
    reason: str

    def __post_init__(self) -> None:
        if self.execution_permitted is not False:
            raise ValueError("execution_permitted must remain False in M5-B")
        if self.execution_triggered is not False:
            raise ValueError("execution_triggered must remain False in M5-B")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "decision_id": self.decision_id,
            "audit_event_id": self.audit_event_id,
            "bridge_status": self.bridge_status,
            "execution_permitted": self.execution_permitted,
            "execution_triggered": self.execution_triggered,
            "audit_chain_length": self.audit_chain_length,
            "latest_event_hash": self.latest_event_hash,
            "reason": self.reason,
        }


def _previous_event_hash(existing_events: tuple[AuditEvent, ...] | list[AuditEvent]) -> str:
    existing_tuple = tuple(existing_events)
    if not existing_tuple:
        return ""
    latest = existing_tuple[-1]
    if not isinstance(latest, AuditEvent):
        raise TypeError("existing_events must contain AuditEvent objects")
    assert_audit_event_hash_valid(latest)
    return latest.event_hash


def _result(
    *,
    proposal_id: str = "",
    decision_id: str = "",
    event: AuditEvent,
    bridge_status: str,
    audit_chain_length: int,
    reason: str,
) -> ProposalDecisionAuditResult:
    return ProposalDecisionAuditResult(
        proposal_id=proposal_id,
        decision_id=decision_id,
        audit_event_id=event.event_id,
        bridge_status=bridge_status,
        execution_permitted=False,
        execution_triggered=False,
        audit_chain_length=audit_chain_length,
        latest_event_hash=event.event_hash,
        reason=reason,
    )


def _assert_decision_flags_safe(decision: ApprovalDecision) -> None:
    if decision.execution_permitted or decision.execution_triggered:
        raise ApprovalDoesNotExecuteError("ApprovalDecision cannot permit or trigger execution in M5-B")


def _assert_events_do_not_authorize(events: tuple[AuditEvent, ...]) -> None:
    for event in events:
        if event.execution_authorized or event.execution_triggered or event.canonical_write_authorized:
            raise AuditEventExecutionBlockedError("AuditEvent authority flags are blocked in M5-B")


def record_proposal_with_audit(
    proposal: ActionProposal,
    existing_events: tuple[AuditEvent, ...] | list[AuditEvent] = (),
) -> tuple[ProposalDecisionAuditResult, tuple[AuditEvent, ...]]:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    assert_action_proposal_is_inert(proposal)
    event = create_action_proposal_audit_event(
        proposal,
        previous_event_hash=_previous_event_hash(existing_events),
    )
    new_events = append_audit_event_in_memory(existing_events, event)
    result = _result(
        proposal_id=proposal.proposal_id,
        event=event,
        bridge_status=BRIDGE_STATUS_PROPOSAL_RECORDED,
        audit_chain_length=len(new_events),
        reason="action proposal recorded for audit only",
    )
    assert_bridge_does_not_execute(result, new_events)
    return result, new_events


def record_decision_with_audit(
    proposal: ActionProposal,
    decision: ApprovalDecision,
    existing_events: tuple[AuditEvent, ...] | list[AuditEvent] = (),
) -> tuple[ProposalDecisionAuditResult, tuple[AuditEvent, ...]]:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    assert_action_proposal_is_inert(proposal)
    _assert_decision_flags_safe(decision)
    assert_provider_cannot_approve(decision)
    assert_unknown_actor_cannot_approve(decision)
    assert_timeout_does_not_approve(decision)
    assert_decision_matches_proposal(decision, proposal)
    if decision.decision_type is ApprovalDecisionType.APPROVE:
        assert_approval_requires_human(decision)
    execution_status = evaluate_approval_decision_for_execution(decision, proposal)
    event = create_approval_decision_audit_event(
        decision,
        previous_event_hash=_previous_event_hash(existing_events),
    )
    new_events = append_audit_event_in_memory(existing_events, event)
    result = _result(
        proposal_id=proposal.proposal_id,
        decision_id=decision.decision_id,
        event=event,
        bridge_status=BRIDGE_STATUS_DECISION_RECORDED,
        audit_chain_length=len(new_events),
        reason=execution_status,
    )
    assert_bridge_does_not_execute(result, new_events)
    return result, new_events


def record_policy_block_with_audit(
    subject_id: str,
    subject_type: str,
    reason: str,
    existing_events: tuple[AuditEvent, ...] | list[AuditEvent] = (),
) -> tuple[ProposalDecisionAuditResult, tuple[AuditEvent, ...]]:
    event = create_policy_block_audit_event(
        subject_id,
        subject_type,
        reason,
        previous_event_hash=_previous_event_hash(existing_events),
    )
    new_events = append_audit_event_in_memory(existing_events, event)
    result = _result(
        event=event,
        bridge_status=BRIDGE_STATUS_POLICY_BLOCK_RECORDED,
        audit_chain_length=len(new_events),
        reason=reason,
    )
    assert_bridge_does_not_execute(result, new_events)
    return result, new_events


def record_execution_blocked_with_audit(
    subject_id: str,
    subject_type: str,
    reason: str,
    existing_events: tuple[AuditEvent, ...] | list[AuditEvent] = (),
) -> tuple[ProposalDecisionAuditResult, tuple[AuditEvent, ...]]:
    event = create_execution_blocked_audit_event(
        subject_id,
        subject_type,
        reason,
        previous_event_hash=_previous_event_hash(existing_events),
    )
    new_events = append_audit_event_in_memory(existing_events, event)
    result = _result(
        event=event,
        bridge_status=BRIDGE_STATUS_EXECUTION_BLOCKED_RECORDED,
        audit_chain_length=len(new_events),
        reason="execution blocked: " + reason,
    )
    assert_bridge_does_not_execute(result, new_events)
    return result, new_events


def assert_bridge_does_not_execute(
    result: ProposalDecisionAuditResult,
    events: tuple[AuditEvent, ...] | list[AuditEvent],
) -> None:
    if not isinstance(result, ProposalDecisionAuditResult):
        raise TypeError("result must be a ProposalDecisionAuditResult")
    if result.execution_permitted or result.execution_triggered:
        raise AuditEventExecutionBlockedError("bridge result cannot permit or trigger execution")
    event_tuple = tuple(events)
    _assert_events_do_not_authorize(event_tuple)
    for event in event_tuple:
        assert_audit_event_hash_valid(event)


def proposal_decision_audit_result_to_dict(result: ProposalDecisionAuditResult) -> dict[str, Any]:
    if not isinstance(result, ProposalDecisionAuditResult):
        raise TypeError("result must be a ProposalDecisionAuditResult")
    return result.to_dict()
