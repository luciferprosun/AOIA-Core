from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.schemas.action_proposal import ActionProposal, ActionProposalKind


ACTION_PROPOSAL_SAFE_PROJECTION_READY = "ACTION_PROPOSAL_SAFE_PROJECTION_READY"
ACTION_PROPOSAL_SAFE_PROJECTION_BLOCKED_INVALID_PROPOSAL = (
    "ACTION_PROPOSAL_SAFE_PROJECTION_BLOCKED_INVALID_PROPOSAL"
)

METADATA_ONLY_WARNING = (
    "Review metadata only. This projection is not approval, gate evidence, "
    "write authority, execution authority, provider trust, commit authority, or push authority."
)

_SAFE_DISPLAY_KIND_BY_ACTION_KIND = {
    ActionProposalKind.FILE_WRITE: "proposed_file_write_metadata",
    ActionProposalKind.TEST_RUN: "proposed_test_run_metadata",
    ActionProposalKind.SHELL_COMMAND: "proposed_shell_command_metadata",
    ActionProposalKind.GIT_COMMIT: "proposed_git_commit_metadata",
    ActionProposalKind.GIT_PUSH: "proposed_git_push_metadata",
    ActionProposalKind.PACKAGE_INSTALL: "proposed_package_install_metadata",
    ActionProposalKind.PROVIDER_CALL: "proposed_provider_call_metadata",
    ActionProposalKind.BROWSER_ACTION: "proposed_browser_action_metadata",
    ActionProposalKind.UNKNOWN: "unknown_proposed_action_metadata",
}


@dataclass(frozen=True)
class ActionProposalSafeProjection:
    status: str
    projection_ready: bool
    reason_code: str
    reason: str
    original_proposal_id: str | None = None
    original_proposal_hash: str | None = None
    original_action_kind: str | None = None
    safe_display_kind: str | None = None
    safe_display_name: str | None = None
    source_trust: str | None = None
    risk_flags: tuple[str, ...] = ()
    target_refs_summary: tuple[str, ...] = ()
    human_review_required: bool = True
    execution_status_summary: str = "not executable by projection"
    metadata_only_warning: str = METADATA_ONLY_WARNING
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "can_approve",
            "can_write",
            "can_execute",
            "can_commit",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "write_authority_granted",
            "execution_authority_granted",
            "provider_authority_granted",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "projection_ready": self.projection_ready,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "original_proposal_id": self.original_proposal_id,
            "original_proposal_hash": self.original_proposal_hash,
            "original_action_kind": self.original_action_kind,
            "safe_display_kind": self.safe_display_kind,
            "safe_display_name": self.safe_display_name,
            "source_trust": self.source_trust,
            "risk_flags": list(self.risk_flags),
            "target_refs_summary": list(self.target_refs_summary),
            "human_review_required": self.human_review_required,
            "execution_status_summary": self.execution_status_summary,
            "metadata_only_warning": self.metadata_only_warning,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "write_authority_granted": self.write_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
        }


def project_action_proposal_for_review(proposal: ActionProposal) -> ActionProposalSafeProjection:
    if not isinstance(proposal, ActionProposal):
        return ActionProposalSafeProjection(
            status=ACTION_PROPOSAL_SAFE_PROJECTION_BLOCKED_INVALID_PROPOSAL,
            projection_ready=False,
            reason_code=ACTION_PROPOSAL_SAFE_PROJECTION_BLOCKED_INVALID_PROPOSAL,
            reason="safe projection requires an ActionProposal",
            original_proposal_id=None,
            original_proposal_hash=None,
            original_action_kind=None,
            safe_display_kind="invalid_action_proposal_metadata",
            safe_display_name="Invalid action proposal metadata",
            source_trust=None,
            risk_flags=(),
            target_refs_summary=(),
            human_review_required=True,
        )

    safe_kind = _safe_display_kind(proposal.action_kind)
    return ActionProposalSafeProjection(
        status=ACTION_PROPOSAL_SAFE_PROJECTION_READY,
        projection_ready=True,
        reason_code=ACTION_PROPOSAL_SAFE_PROJECTION_READY,
        reason="action proposal projected as review metadata only",
        original_proposal_id=proposal.proposal_id,
        original_proposal_hash=proposal.proposal_hash,
        original_action_kind=proposal.action_kind.value,
        safe_display_kind=safe_kind,
        safe_display_name=_safe_display_name(safe_kind),
        source_trust=proposal.source_trust.value,
        risk_flags=tuple(flag.value for flag in proposal.risk_flags),
        target_refs_summary=tuple(proposal.target_refs),
        human_review_required=proposal.human_review_required,
        execution_status_summary=_execution_status_summary(proposal),
    )


def _safe_display_kind(action_kind: ActionProposalKind) -> str:
    return _SAFE_DISPLAY_KIND_BY_ACTION_KIND.get(action_kind, "unknown_proposed_action_metadata")


def _safe_display_name(safe_kind: str) -> str:
    return " ".join(safe_kind.split("_")).title()


def _execution_status_summary(proposal: ActionProposal) -> str:
    if proposal.execution_permitted or proposal.execution_implemented:
        return "proposal execution flags are normalized inert; projection cannot execute"
    return "proposal is review metadata only; projection cannot execute"
