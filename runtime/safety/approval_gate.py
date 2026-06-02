from __future__ import annotations

from dataclasses import dataclass

from runtime.safety.bash_parser import parse_bash_command
from runtime.schemas.command_proposal import APPROVAL_STATES, CommandProposal


@dataclass(frozen=True)
class ApprovalDecision:
    allowed: bool
    approval_state: str
    reason: str
    dry_run: bool
    requires_human_review: bool

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise TypeError("allowed must be bool")
        if self.approval_state not in APPROVAL_STATES:
            raise ValueError("approval_state must be one of the allowed values")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string")
        if not isinstance(self.dry_run, bool):
            raise TypeError("dry_run must be bool")
        if not isinstance(self.requires_human_review, bool):
            raise TypeError("requires_human_review must be bool")


def evaluate_approval(proposal: CommandProposal) -> ApprovalDecision:
    if not isinstance(proposal, CommandProposal):
        raise TypeError("proposal must be a CommandProposal")
    if not proposal.dry_run:
        return ApprovalDecision(
            allowed=False,
            approval_state="denied",
            reason="non-dry-run proposals are not allowed in GT-RUNTIME-8E",
            dry_run=True,
            requires_human_review=True,
        )
    if proposal.classification == "safe":
        return ApprovalDecision(
            allowed=True,
            approval_state="not_required",
            reason="safe proposal may pass only as a dry-run decision",
            dry_run=True,
            requires_human_review=False,
        )
    if proposal.classification == "ambiguous":
        return ApprovalDecision(
            allowed=False,
            approval_state="requires_human_review",
            reason="ambiguous proposals require human review",
            dry_run=True,
            requires_human_review=True,
        )
    if proposal.classification == "dangerous":
        return ApprovalDecision(
            allowed=False,
            approval_state="denied",
            reason="dangerous proposals are denied pending human review",
            dry_run=True,
            requires_human_review=True,
        )
    if proposal.classification == "unknown":
        return ApprovalDecision(
            allowed=False,
            approval_state="requires_human_review",
            reason="unknown proposals require human review",
            dry_run=True,
            requires_human_review=True,
        )
    return ApprovalDecision(
        allowed=False,
        approval_state="requires_human_review",
        reason="unrecognized classification requires human review",
        dry_run=True,
        requires_human_review=True,
    )


def evaluate_command_text(command: str, *, source: str = "user") -> ApprovalDecision:
    proposal = parse_bash_command(command, source=source)
    return evaluate_approval(proposal)
