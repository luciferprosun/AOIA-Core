from __future__ import annotations

from runtime.schemas.dry_run_agent import DryRunAgentRequest, DryRunAgentTrace


class DryRunAgentExecutionBlockedError(RuntimeError):
    pass


class DryRunAgentProviderCallBlockedError(RuntimeError):
    pass


class DryRunAgentPersistenceBlockedError(RuntimeError):
    pass


class DryRunAgentInvalidRequestError(ValueError):
    pass


def assert_dry_run_agent_does_not_execute(trace_or_request: DryRunAgentTrace | DryRunAgentRequest) -> None:
    if isinstance(trace_or_request, DryRunAgentTrace):
        if trace_or_request.execution_permitted or trace_or_request.execution_triggered:
            raise DryRunAgentExecutionBlockedError("M7-A trace cannot permit or trigger execution")
        raise DryRunAgentExecutionBlockedError("M7-A dry-run traces are non-executing records")
    if isinstance(trace_or_request, DryRunAgentRequest):
        assert_plan_steps_are_inert(trace_or_request)
        raise DryRunAgentExecutionBlockedError("M7-A dry-run requests cannot execute")
    raise TypeError("trace_or_request must be a DryRunAgentTrace or DryRunAgentRequest")


def assert_dry_run_agent_does_not_call_provider(trace_or_request: DryRunAgentTrace | DryRunAgentRequest) -> None:
    if isinstance(trace_or_request, DryRunAgentTrace):
        if trace_or_request.provider_call_permitted:
            raise DryRunAgentProviderCallBlockedError("M7-A trace cannot permit provider calls")
        raise DryRunAgentProviderCallBlockedError("M7-A dry-run traces do not call providers")
    if isinstance(trace_or_request, DryRunAgentRequest):
        if trace_or_request.provider_generated:
            raise DryRunAgentProviderCallBlockedError("provider-generated dry-run requests cannot gain authority")
        raise DryRunAgentProviderCallBlockedError("M7-A dry-run requests do not call providers")
    raise TypeError("trace_or_request must be a DryRunAgentTrace or DryRunAgentRequest")


def assert_dry_run_agent_does_not_persist(trace_or_request: DryRunAgentTrace | DryRunAgentRequest) -> None:
    if isinstance(trace_or_request, DryRunAgentTrace):
        if trace_or_request.filesystem_persistence_permitted:
            raise DryRunAgentPersistenceBlockedError("M7-A trace cannot permit persistence")
        raise DryRunAgentPersistenceBlockedError("M7-A dry-run traces do not persist state")
    if isinstance(trace_or_request, DryRunAgentRequest):
        raise DryRunAgentPersistenceBlockedError("M7-A dry-run requests do not persist state")
    raise TypeError("trace_or_request must be a DryRunAgentTrace or DryRunAgentRequest")


def assert_dry_run_request_valid(request: DryRunAgentRequest) -> None:
    if not isinstance(request, DryRunAgentRequest):
        raise TypeError("request must be a DryRunAgentRequest")
    if not request.plan_steps:
        raise DryRunAgentInvalidRequestError("M7-A dry-run requests require at least one plan step")
    if not request.goal_text.strip():
        raise DryRunAgentInvalidRequestError("M7-A dry-run requests require a non-empty goal")
    assert_plan_steps_are_inert(request)


def assert_plan_steps_are_inert(request: DryRunAgentRequest) -> None:
    if not isinstance(request, DryRunAgentRequest):
        raise TypeError("request must be a DryRunAgentRequest")
    for step in request.plan_steps:
        if step.execution_intended:
            raise DryRunAgentExecutionBlockedError("M7-A plan steps cannot authorize execution")
