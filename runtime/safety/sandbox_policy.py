from __future__ import annotations

from runtime.schemas.approval_decision import ApprovalDecision
from runtime.schemas.audit_event import AuditEvent
from runtime.schemas.sandbox_contract import (
    SandboxActionType,
    SandboxDecisionType,
    SandboxPolicyDecision,
    SandboxRequest,
    SandboxResult,
    create_blocked_sandbox_policy_decision,
    create_blocked_sandbox_result,
    create_not_implemented_sandbox_policy_decision,
)


class SandboxExecutionBlockedError(RuntimeError):
    pass


class SandboxNotImplementedError(SandboxExecutionBlockedError):
    pass


class SandboxPolicyViolationError(SandboxExecutionBlockedError):
    pass


class SandboxApprovalDoesNotExecuteError(SandboxExecutionBlockedError):
    pass


_BLOCKED_BY_DEFAULT_ACTIONS = frozenset(
    {
        SandboxActionType.SHELL_COMMAND,
        SandboxActionType.BROWSER_ACTION,
        SandboxActionType.FILESYSTEM_ACTION,
        SandboxActionType.GIT_ACTION,
        SandboxActionType.PROVIDER_CALL,
        SandboxActionType.CLOUD_ACTION,
    }
)


def assert_sandbox_contract_does_not_execute(
    request: SandboxRequest,
    decision: SandboxPolicyDecision | None = None,
    result: SandboxResult | None = None,
) -> None:
    if not isinstance(request, SandboxRequest):
        raise TypeError("request must be a SandboxRequest")
    if decision is not None:
        if not isinstance(decision, SandboxPolicyDecision):
            raise TypeError("decision must be a SandboxPolicyDecision or None")
        if decision.sandbox_request_id != request.sandbox_request_id:
            raise SandboxPolicyViolationError("sandbox decision must match request")
        if decision.execution_allowed or decision.execution_implemented:
            raise SandboxExecutionBlockedError("sandbox decision cannot allow or implement execution in M6-A")
    if result is not None:
        if not isinstance(result, SandboxResult):
            raise TypeError("result must be a SandboxResult or None")
        if result.sandbox_request_id != request.sandbox_request_id:
            raise SandboxPolicyViolationError("sandbox result must match request")
        if result.execution_attempted or result.execution_completed:
            raise SandboxExecutionBlockedError("sandbox result cannot attempt or complete execution in M6-A")


def assert_sandbox_execution_not_implemented(decision: SandboxPolicyDecision) -> None:
    if not isinstance(decision, SandboxPolicyDecision):
        raise TypeError("decision must be a SandboxPolicyDecision")
    if decision.execution_allowed or decision.execution_implemented:
        raise SandboxNotImplementedError("M6-A has no sandbox runner")
    raise SandboxNotImplementedError("sandbox execution is not implemented in M6-A")


def assert_human_approval_does_not_enable_sandbox_execution(
    request: SandboxRequest,
    approval_decision: ApprovalDecision | None = None,
) -> None:
    if not isinstance(request, SandboxRequest):
        raise TypeError("request must be a SandboxRequest")
    if approval_decision is not None and not isinstance(approval_decision, ApprovalDecision):
        raise TypeError("approval_decision must be an ApprovalDecision or None")
    if request.human_approved or approval_decision is not None:
        raise SandboxApprovalDoesNotExecuteError("human approval records review only; it does not run sandbox actions")
    raise SandboxExecutionBlockedError("sandbox execution is unavailable in M6-A")


def assert_sandbox_action_blocked_by_default(request: SandboxRequest) -> None:
    if not isinstance(request, SandboxRequest):
        raise TypeError("request must be a SandboxRequest")
    if request.requested_action_type in _BLOCKED_BY_DEFAULT_ACTIONS:
        raise SandboxExecutionBlockedError("sandbox action type is blocked by default in M6-A")
    raise SandboxNotImplementedError("sandbox action type has no M6-A runner")


def assert_audit_event_does_not_enable_sandbox_execution(event: AuditEvent) -> None:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    if event.execution_authorized or event.execution_triggered:
        raise SandboxPolicyViolationError("audit events cannot authorize sandbox execution")
    raise SandboxExecutionBlockedError("AuditEvent is a record only; it does not run sandbox actions")


def evaluate_sandbox_request(request: SandboxRequest) -> SandboxPolicyDecision:
    if not isinstance(request, SandboxRequest):
        raise TypeError("request must be a SandboxRequest")
    if request.requested_action_type in _BLOCKED_BY_DEFAULT_ACTIONS:
        return _create_blocked_by_default_decision(request)
    if request.requested_action_type is SandboxActionType.HUMAN_REVIEW_ONLY:
        return create_not_implemented_sandbox_policy_decision(
            request,
            "human-review-only sandbox records remain local and non-running",
        )
    if request.requested_action_type is SandboxActionType.DOCUMENT_PARSE:
        return _create_future_sandbox_required_decision(request)
    return create_not_implemented_sandbox_policy_decision(
        request,
        "sandbox execution is not implemented in M6-A",
    )


def _create_future_sandbox_required_decision(request: SandboxRequest) -> SandboxPolicyDecision:
    decision = create_not_implemented_sandbox_policy_decision(
        request,
        "future sandbox design is required before document parsing can run",
    )
    return SandboxPolicyDecision(
        decision_id=decision.decision_id,
        created_at=decision.created_at,
        sandbox_request_id=decision.sandbox_request_id,
        decision_type=SandboxDecisionType.REQUIRES_FUTURE_SANDBOX,
        reason=decision.reason,
        execution_allowed=False,
        execution_implemented=False,
        requires_future_sandbox=True,
        policy_blocked=True,
        audit_event_id=decision.audit_event_id,
        notes=decision.notes,
    )


def _create_blocked_by_default_decision(request: SandboxRequest) -> SandboxPolicyDecision:
    decision = create_blocked_sandbox_policy_decision(
        request,
        "sandbox action is blocked by default in M6-A",
    )
    return SandboxPolicyDecision(
        decision_id=decision.decision_id,
        created_at=decision.created_at,
        sandbox_request_id=decision.sandbox_request_id,
        decision_type=SandboxDecisionType.BLOCKED_BY_DEFAULT,
        reason=decision.reason,
        execution_allowed=False,
        execution_implemented=False,
        requires_future_sandbox=True,
        policy_blocked=True,
        audit_event_id=decision.audit_event_id,
        notes=decision.notes,
    )


def create_sandbox_not_run_result(
    request: SandboxRequest,
    decision: SandboxPolicyDecision,
) -> SandboxResult:
    assert_sandbox_contract_does_not_execute(request, decision)
    return create_blocked_sandbox_result(request, decision, decision.reason)
