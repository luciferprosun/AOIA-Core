from __future__ import annotations

from runtime.schemas.action_proposal import (
    ActionProposal,
    ActionProposalRisk,
    ActionProposalType,
)
from runtime.schemas.evidence_memory import EvidenceMemoryRecord
from runtime.schemas.provider_critic import ProviderCritiqueRecord


class ActionProposalExecutionBlockedError(RuntimeError):
    pass


class ProviderGeneratedActionBlockedError(ActionProposalExecutionBlockedError):
    pass


class EvidenceOnlyActionBlockedError(ActionProposalExecutionBlockedError):
    pass


class HumanApprovalIsNotExecutionError(ActionProposalExecutionBlockedError):
    pass


_FORBIDDEN_PROPOSAL_TYPES = frozenset(
    {
        ActionProposalType.SHELL_COMMAND,
        ActionProposalType.BROWSER_ACTION,
        ActionProposalType.FILESYSTEM_ACTION,
        ActionProposalType.GIT_ACTION,
        ActionProposalType.PROVIDER_CALL,
        ActionProposalType.CLOUD_ACTION,
    }
)


def classify_action_proposal_risk(proposal: ActionProposal) -> ActionProposalRisk:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    if proposal.proposal_type in _FORBIDDEN_PROPOSAL_TYPES:
        return ActionProposalRisk.FORBIDDEN
    if proposal.provider_generated:
        return ActionProposalRisk.FORBIDDEN
    if proposal.proposal_type is ActionProposalType.HUMAN_REVIEW_ONLY:
        return ActionProposalRisk.LOW
    return ActionProposalRisk.UNKNOWN


def assert_action_proposal_is_inert(proposal: ActionProposal) -> None:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    if proposal.execution_permitted or proposal.execution_implemented:
        raise ActionProposalExecutionBlockedError("M3-A ActionProposal objects must remain non-executable")
    if proposal.provider_generated:
        raise ProviderGeneratedActionBlockedError("provider-generated proposals cannot become executable")


def assert_action_proposal_cannot_execute(proposal: ActionProposal) -> None:
    assert_action_proposal_is_inert(proposal)
    raise ActionProposalExecutionBlockedError("M3-A does not implement action execution")


def assert_provider_output_cannot_create_executable_action(provider_critique_record: object) -> None:
    if isinstance(provider_critique_record, ProviderCritiqueRecord):
        raise ProviderGeneratedActionBlockedError("ProviderCritiqueRecord cannot create executable actions")
    if getattr(provider_critique_record, "untrusted", False) is True:
        raise ProviderGeneratedActionBlockedError("untrusted provider output cannot create executable actions")
    if getattr(provider_critique_record, "provider_generated", False) is True:
        raise ProviderGeneratedActionBlockedError("provider-generated content cannot create executable actions")
    if isinstance(provider_critique_record, dict):
        if provider_critique_record.get("untrusted") is True:
            raise ProviderGeneratedActionBlockedError("serialized untrusted provider output cannot create executable actions")
        if {"source_provider", "source_model", "response_text"}.issubset(provider_critique_record.keys()):
            raise ProviderGeneratedActionBlockedError("serialized provider critique cannot create executable actions")


def assert_evidence_cannot_execute_as_action(evidence_record: object) -> None:
    if isinstance(evidence_record, EvidenceMemoryRecord):
        raise EvidenceOnlyActionBlockedError("EvidenceMemoryRecord is evidence data, not an executable action")
    if getattr(evidence_record, "execution_allowed", False) is False and hasattr(evidence_record, "content_hash"):
        raise EvidenceOnlyActionBlockedError("evidence-like records cannot execute as actions")
    if isinstance(evidence_record, dict) and "evidence_id" in evidence_record:
        raise EvidenceOnlyActionBlockedError("serialized evidence records cannot execute as actions")


def assert_human_approval_does_not_execute(proposal: ActionProposal) -> None:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    if proposal.human_approved:
        raise HumanApprovalIsNotExecutionError("human approval records review intent only")
    raise ActionProposalExecutionBlockedError("M3-A has no execution path")
