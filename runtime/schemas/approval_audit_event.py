from __future__ import annotations

from dataclasses import dataclass

from runtime.schemas.approval_decision import ApprovalDecision
from runtime.schemas.command_proposal import CommandProposal

APPROVAL_AUDIT_EVENT_TYPE = "approval_decision_dry_run"


@dataclass(frozen=True)
class ApprovalAuditEvent:
    event_id: str
    event_type: str
    created_at_utc: str
    source: str
    raw_command: str
    normalized_command: str
    classification: str
    proposal_approval_state: str
    decision_approval_state: str
    decision_allowed: bool
    execution_permitted: bool
    dry_run: bool
    requires_human_review: bool
    proposal_reason: str
    decision_reason: str

    def __post_init__(self) -> None:
        string_fields = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "created_at_utc": self.created_at_utc,
            "source": self.source,
            "raw_command": self.raw_command,
            "normalized_command": self.normalized_command,
            "classification": self.classification,
            "proposal_approval_state": self.proposal_approval_state,
            "decision_approval_state": self.decision_approval_state,
            "proposal_reason": self.proposal_reason,
            "decision_reason": self.decision_reason,
        }
        for name, value in string_fields.items():
            if not isinstance(value, str):
                raise TypeError(f"{name} must be a string")
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if self.event_type != APPROVAL_AUDIT_EVENT_TYPE:
            raise ValueError("event_type must be approval_decision_dry_run")
        if not self.created_at_utc:
            raise ValueError("created_at_utc must be non-empty")
        if not isinstance(self.decision_allowed, bool):
            raise TypeError("decision_allowed must be bool")
        if not isinstance(self.execution_permitted, bool):
            raise TypeError("execution_permitted must be bool")
        if self.execution_permitted:
            raise ValueError("execution_permitted must remain False in GT-RUNTIME-8F")
        if not isinstance(self.dry_run, bool):
            raise TypeError("dry_run must be bool")
        if not isinstance(self.requires_human_review, bool):
            raise TypeError("requires_human_review must be bool")


def from_proposal_and_decision(
    proposal: CommandProposal,
    decision: ApprovalDecision,
    *,
    event_id: str,
    created_at_utc: str,
) -> ApprovalAuditEvent:
    if not isinstance(proposal, CommandProposal):
        raise TypeError("proposal must be a CommandProposal")
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    return ApprovalAuditEvent(
        event_id=event_id,
        event_type=APPROVAL_AUDIT_EVENT_TYPE,
        created_at_utc=created_at_utc,
        source=proposal.source,
        raw_command=proposal.raw_command,
        normalized_command=proposal.normalized_command,
        classification=proposal.classification,
        proposal_approval_state=proposal.approval_state,
        decision_approval_state=decision.approval_state,
        decision_allowed=decision.allowed,
        execution_permitted=decision.execution_permitted,
        dry_run=decision.dry_run,
        requires_human_review=decision.requires_human_review,
        proposal_reason=proposal.reason,
        decision_reason=decision.reason,
    )
