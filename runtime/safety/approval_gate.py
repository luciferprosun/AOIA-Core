from __future__ import annotations

from runtime.schemas.approval_decision import ApprovalDecision
from runtime.schemas.command_proposal import CommandProposal


def evaluate_approval(proposal: CommandProposal) -> ApprovalDecision:
    if not isinstance(proposal, CommandProposal):
        raise TypeError("proposal must be a CommandProposal")
    if not proposal.dry_run:
        return ApprovalDecision(
            allowed=False,
            approval_state="requires_human_review",
            reason="non-dry-run proposals are not allowed in GT-RUNTIME-8E",
            dry_run=False,
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
            approval_state="requires_human_review",
            reason="dangerous proposals require human review",
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
        reason="unknown or invalid classification requires human review",
        dry_run=True,
        requires_human_review=True,
    )
