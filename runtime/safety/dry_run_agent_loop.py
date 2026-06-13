from __future__ import annotations

from runtime.safety.action_proposal_policy import assert_action_proposal_is_inert
from runtime.safety.audit_event_policy import assert_audit_event_hash_valid
from runtime.safety.dry_run_agent_policy import (
    DryRunAgentProviderCallBlockedError,
    assert_dry_run_request_valid,
)
from runtime.safety.proposal_decision_audit_bridge import (
    assert_bridge_does_not_execute,
    record_decision_with_audit,
    record_proposal_with_audit,
)
from runtime.safety.sandbox_policy import (
    assert_sandbox_contract_does_not_execute,
    create_sandbox_not_run_result,
    evaluate_sandbox_request,
)
from runtime.schemas.action_proposal import ActionProposalType, create_inert_action_proposal
from runtime.schemas.approval_decision import create_human_approval_decision, create_policy_block_decision
from runtime.schemas.audit_event import AuditEvent
from runtime.schemas.dry_run_agent import (
    DryRunAgentFinalState,
    DryRunAgentRequest,
    DryRunAgentState,
    DryRunAgentTrace,
    hash_dry_run_goal,
)
from runtime.schemas.sandbox_contract import (
    SandboxDecisionType,
    SandboxPolicyDecision,
    SandboxRequest,
    SandboxResult,
    create_sandbox_request_from_action_proposal,
)


def run_dry_run_agent_loop(
    request: DryRunAgentRequest,
    approval_actor_id: str = "human-reviewer",
    existing_audit_events: tuple[AuditEvent, ...] | list[AuditEvent] = (),
) -> tuple[DryRunAgentTrace, tuple[AuditEvent, ...], SandboxRequest, SandboxPolicyDecision, SandboxResult]:
    assert_dry_run_request_valid(request)
    if request.provider_generated:
        raise DryRunAgentProviderCallBlockedError("provider-generated dry-run requests cannot gain authority")
    existing_events = tuple(existing_audit_events)
    for event in existing_events:
        if not isinstance(event, AuditEvent):
            raise TypeError("existing_audit_events must contain AuditEvent objects")
        assert_audit_event_hash_valid(event)

    plan_step = request.plan_steps[0]
    proposal = create_inert_action_proposal(
        proposal_type=ActionProposalType(plan_step.proposed_action_type),
        title=plan_step.title,
        description=plan_step.description,
        proposed_by=request.requested_by,
        source_record_id=request.run_id,
        source_record_type="DryRunAgentRequest",
        payload_summary=plan_step.payload_summary,
        exact_payload=plan_step.exact_payload,
        human_approved=False,
        provider_generated=False,
        notes="M7-A dry-run proposal data only",
    )
    assert_action_proposal_is_inert(proposal)

    if request.human_review_required:
        decision = create_human_approval_decision(
            proposal,
            approval_actor_id,
            "human review recorded for dry-run only",
            notes="approval does not execute in M7-A",
        )
    else:
        decision = create_policy_block_decision(
            proposal,
            "human review is required before any future phase",
            notes="policy block remains non-executing in M7-A",
        )

    _proposal_audit_result, proposal_events = record_proposal_with_audit(proposal, existing_events)
    decision_audit_result, new_events = record_decision_with_audit(proposal, decision, proposal_events)
    assert_bridge_does_not_execute(decision_audit_result, new_events)

    sandbox_request = create_sandbox_request_from_action_proposal(
        proposal,
        decision,
        audit_event_id=decision_audit_result.audit_event_id,
        notes="M7-A dry-run sandbox request; no runner",
    )
    sandbox_decision = evaluate_sandbox_request(sandbox_request)
    sandbox_result = create_sandbox_not_run_result(sandbox_request, sandbox_decision)
    assert_sandbox_contract_does_not_execute(sandbox_request, sandbox_decision, sandbox_result)

    final_state = (
        DryRunAgentFinalState.NOT_IMPLEMENTED_NO_EXECUTION
        if sandbox_decision.decision_type is SandboxDecisionType.NOT_IMPLEMENTED
        else DryRunAgentFinalState.BLOCKED_NO_EXECUTION
    )
    latest_event = new_events[-1]
    trace = DryRunAgentTrace(
        run_id=request.run_id,
        created_at=request.created_at,
        state=DryRunAgentState.COMPLETED_BLOCKED,
        final_state=final_state,
        goal_hash=hash_dry_run_goal(request.goal_text),
        proposal_id=proposal.proposal_id,
        decision_id=decision.decision_id,
        latest_audit_event_id=latest_event.event_id,
        latest_audit_event_hash=latest_event.event_hash,
        sandbox_request_id=sandbox_request.sandbox_request_id,
        sandbox_policy_decision_id=sandbox_decision.decision_id,
        sandbox_result_id=sandbox_result.result_id,
        execution_permitted=False,
        execution_triggered=False,
        provider_call_permitted=False,
        filesystem_persistence_permitted=False,
        audit_chain_length=len(new_events),
        reason=sandbox_decision.reason,
        notes="M7-A one-shot dry-run trace; no execution",
    )
    return trace, new_events, sandbox_request, sandbox_decision, sandbox_result
