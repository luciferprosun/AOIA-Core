from __future__ import annotations

from datetime import UTC, datetime

from runtime.schemas.action_proposal import ActionProposal
from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
    hash_action_proposal_payload,
)


EXECUTION_BLOCKED_M4_A = "execution_blocked_m4_a"


class ApprovalDecisionBlockedError(RuntimeError):
    pass


class ApprovalDoesNotExecuteError(ApprovalDecisionBlockedError):
    pass


class ProviderApprovalBlockedError(ApprovalDecisionBlockedError):
    pass


class ApprovalTimeoutBlockedError(ApprovalDecisionBlockedError):
    pass


def _parse_optional_utc(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def assert_approval_decision_does_not_execute(decision: ApprovalDecision) -> None:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    if decision.execution_permitted or decision.execution_triggered:
        raise ApprovalDoesNotExecuteError("ApprovalDecision cannot permit or trigger runtime execution in M4-A")
    raise ApprovalDoesNotExecuteError("ApprovalDecision is review data only in M4-A")


def assert_provider_cannot_approve(decision: ApprovalDecision) -> None:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    if decision.provider_generated or decision.actor_type is ApprovalActorType.PROVIDER_MODEL:
        if decision.decision_type is ApprovalDecisionType.APPROVE:
            raise ProviderApprovalBlockedError("provider/model generated decisions cannot approve actions")


def assert_unknown_actor_cannot_approve(decision: ApprovalDecision) -> None:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    if decision.actor_type is ApprovalActorType.UNKNOWN and decision.decision_type is ApprovalDecisionType.APPROVE:
        raise ApprovalDecisionBlockedError("unknown actors cannot approve actions")


def assert_timeout_does_not_approve(decision_or_none: ApprovalDecision | None) -> None:
    if decision_or_none is None:
        raise ApprovalTimeoutBlockedError("missing approval decision cannot become approval")
    if not isinstance(decision_or_none, ApprovalDecision):
        raise TypeError("decision_or_none must be an ApprovalDecision or None")
    expires_at = _parse_optional_utc(decision_or_none.expires_at)
    if expires_at is not None and expires_at <= datetime.now(UTC):
        raise ApprovalTimeoutBlockedError("expired approval decision cannot become approval")


def assert_approval_requires_human(decision: ApprovalDecision) -> None:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    if decision.decision_type is not ApprovalDecisionType.APPROVE:
        return
    if decision.actor_type is not ApprovalActorType.HUMAN_REVIEWER or not decision.human_reviewed:
        raise ApprovalDecisionBlockedError("approval decisions require a human reviewer")
    if decision.decision_state is not ApprovalDecisionState.RECORDED:
        raise ApprovalDecisionBlockedError("invalid approval decisions cannot approve actions")


def assert_decision_matches_proposal(decision: ApprovalDecision, proposal: ActionProposal) -> None:
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision")
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    if decision.proposal_id != proposal.proposal_id:
        raise ApprovalDecisionBlockedError("approval decision proposal_id does not match proposal")
    if decision.proposal_type != proposal.proposal_type.value:
        raise ApprovalDecisionBlockedError("approval decision proposal_type does not match proposal")
    if decision.reviewed_exact_payload_hash != hash_action_proposal_payload(proposal):
        raise ApprovalDecisionBlockedError("approval decision payload hash does not match proposal")


def evaluate_approval_decision_for_execution(
    decision: ApprovalDecision | None,
    proposal: ActionProposal,
) -> str:
    if not isinstance(proposal, ActionProposal):
        raise TypeError("proposal must be an ActionProposal")
    if decision is None:
        return EXECUTION_BLOCKED_M4_A
    if not isinstance(decision, ApprovalDecision):
        raise TypeError("decision must be an ApprovalDecision or None")
    return EXECUTION_BLOCKED_M4_A
