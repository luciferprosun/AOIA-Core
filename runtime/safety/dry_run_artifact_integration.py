from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.safety.dry_run_agent_loop import run_dry_run_agent_loop
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.safety.sandbox_policy import assert_sandbox_contract_does_not_execute
from runtime.schemas.audit_event import AuditEvent
from runtime.schemas.dry_run_agent import DryRunAgentRequest, DryRunAgentState, DryRunAgentTrace
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactRequest,
    SandboxArtifactResult,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)
from runtime.schemas.sandbox_contract import SandboxPolicyDecision, SandboxRequest, SandboxResult


@dataclass(frozen=True)
class DryRunArtifactIntegrationResult:
    run_id: str
    trace_state: str
    artifact_request_id: str
    artifact_result_id: str
    workspace_root: str
    relative_output_path: str
    resolved_output_path: str
    content_hash: str
    write_attempted: bool
    write_completed: bool
    execution_permitted: bool
    execution_triggered: bool
    provider_call_permitted: bool
    filesystem_scope: str
    reason: str
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _coerce_text("run_id", self.run_id))
        object.__setattr__(self, "trace_state", _coerce_text("trace_state", self.trace_state))
        object.__setattr__(self, "artifact_request_id", _coerce_text("artifact_request_id", self.artifact_request_id))
        object.__setattr__(self, "artifact_result_id", _coerce_text("artifact_result_id", self.artifact_result_id))
        object.__setattr__(self, "workspace_root", _coerce_text("workspace_root", self.workspace_root))
        object.__setattr__(self, "relative_output_path", _coerce_text("relative_output_path", self.relative_output_path))
        object.__setattr__(self, "resolved_output_path", _coerce_text("resolved_output_path", self.resolved_output_path))
        object.__setattr__(self, "content_hash", _coerce_text("content_hash", self.content_hash))
        object.__setattr__(self, "filesystem_scope", _coerce_text("filesystem_scope", self.filesystem_scope))
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))
        if self.write_attempted is not True and self.write_attempted is not False:
            raise TypeError("write_attempted must be bool")
        if self.write_completed is not True and self.write_completed is not False:
            raise TypeError("write_completed must be bool")
        if self.execution_permitted is not False:
            raise ValueError("execution_permitted must remain False in M9-A")
        if self.execution_triggered is not False:
            raise ValueError("execution_triggered must remain False in M9-A")
        if self.provider_call_permitted is not False:
            raise ValueError("provider_call_permitted must remain False in M9-A")
        object.__setattr__(self, "execution_permitted", False)
        object.__setattr__(self, "execution_triggered", False)
        object.__setattr__(self, "provider_call_permitted", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "trace_state": self.trace_state,
            "artifact_request_id": self.artifact_request_id,
            "artifact_result_id": self.artifact_result_id,
            "workspace_root": self.workspace_root,
            "relative_output_path": self.relative_output_path,
            "resolved_output_path": self.resolved_output_path,
            "content_hash": self.content_hash,
            "write_attempted": self.write_attempted,
            "write_completed": self.write_completed,
            "execution_permitted": self.execution_permitted,
            "execution_triggered": self.execution_triggered,
            "provider_call_permitted": self.provider_call_permitted,
            "filesystem_scope": self.filesystem_scope,
            "reason": self.reason,
            "notes": self.notes,
        }


def build_agent_demo_artifact_content(
    trace: DryRunAgentTrace,
    sandbox_request: SandboxRequest,
    sandbox_decision: SandboxPolicyDecision,
    sandbox_result: SandboxResult,
) -> str:
    _assert_trace_and_sandbox_match(trace, sandbox_request, sandbox_decision, sandbox_result)
    lines = (
        "# AOIA Controlled Agent v0 Dry-run Artifact",
        "",
        "This artifact is a local summary only.",
        "",
        f"run_id: {trace.run_id}",
        f"trace_state: {trace.state.value}",
        f"final_state: {trace.final_state.value}",
        f"goal_hash: {trace.goal_hash}",
        f"proposal_id: {trace.proposal_id}",
        f"decision_id: {trace.decision_id}",
        f"audit_chain_length: {trace.audit_chain_length}",
        f"sandbox_request_id: {sandbox_request.sandbox_request_id}",
        f"sandbox_action_type: {sandbox_request.requested_action_type.value}",
        f"sandbox_policy_decision_id: {sandbox_decision.decision_id}",
        f"sandbox_decision_type: {sandbox_decision.decision_type.value}",
        f"sandbox_result_id: {sandbox_result.result_id}",
        f"sandbox_result_state: {sandbox_result.result_state.value}",
        f"execution_permitted: {trace.execution_permitted}",
        f"execution_triggered: {trace.execution_triggered}",
        f"provider_call_permitted: {trace.provider_call_permitted}",
        "filesystem_scope: explicit_sandbox_workspace_only",
    )
    return "\n".join(lines) + "\n"


def create_artifact_request_from_dry_run(
    trace: DryRunAgentTrace,
    sandbox_request: SandboxRequest,
    sandbox_result: SandboxResult,
    relative_output_path: str,
    requested_by: str = "aoia-dry-run-agent",
    notes: str = "",
    sandbox_decision: SandboxPolicyDecision | None = None,
) -> SandboxArtifactRequest:
    if sandbox_decision is None:
        _assert_trace_and_sandbox_match(trace, sandbox_request, None, sandbox_result)
        content_text = "\n".join(
            (
                "# AOIA Controlled Agent v0 Dry-run Artifact",
                "",
                "This artifact is a local summary only.",
                "",
                f"run_id: {trace.run_id}",
                f"trace_state: {trace.state.value}",
                f"final_state: {trace.final_state.value}",
                f"goal_hash: {trace.goal_hash}",
                f"sandbox_request_id: {sandbox_request.sandbox_request_id}",
                f"sandbox_result_id: {sandbox_result.result_id}",
                f"sandbox_result_state: {sandbox_result.result_state.value}",
                f"execution_permitted: {trace.execution_permitted}",
                f"execution_triggered: {trace.execution_triggered}",
                f"provider_call_permitted: {trace.provider_call_permitted}",
                "filesystem_scope: explicit_sandbox_workspace_only",
            )
        ) + "\n"
    else:
        content_text = build_agent_demo_artifact_content(trace, sandbox_request, sandbox_decision, sandbox_result)
    sandbox_policy_decision_id = (
        sandbox_decision.decision_id if sandbox_decision is not None else sandbox_result.policy_decision_id
    )
    return create_sandbox_artifact_request(
        run_id=trace.run_id,
        sandbox_request_id=sandbox_request.sandbox_request_id,
        sandbox_result_id=sandbox_result.result_id,
        artifact_type=_artifact_type_from_relative_path(relative_output_path),
        relative_output_path=relative_output_path,
        content_text=content_text,
        requested_by=requested_by,
        human_approved=sandbox_request.human_approved,
        dry_run_trace_id=trace.run_id,
        audit_event_id=sandbox_result.audit_event_id,
        notes=notes,
        artifact_write_allowed=sandbox_request.human_approved,
        approval_decision_id=trace.decision_id,
        sandbox_policy_decision_id=sandbox_policy_decision_id,
        sandbox_result_state=sandbox_result.result_state.value,
        contract_audit_event_id=sandbox_result.audit_event_id,
    )


def run_dry_run_agent_and_write_artifact(
    dry_run_request: DryRunAgentRequest,
    workspace_root: str,
    relative_output_path: str = "aoia_agent_v0_result.md",
    approval_actor_id: str = "human-reviewer",
    existing_audit_events: tuple[AuditEvent, ...] | list[AuditEvent] = (),
) -> tuple[
    DryRunArtifactIntegrationResult,
    DryRunAgentTrace,
    tuple[AuditEvent, ...],
    SandboxRequest,
    SandboxPolicyDecision,
    SandboxResult,
    SandboxArtifactRequest,
    SandboxArtifactResult,
]:
    trace, audit_events, sandbox_request, sandbox_decision, sandbox_result = run_dry_run_agent_loop(
        dry_run_request,
        approval_actor_id=approval_actor_id,
        existing_audit_events=existing_audit_events,
    )
    _assert_trace_has_no_authority(trace)
    assert_sandbox_contract_does_not_execute(sandbox_request, sandbox_decision, sandbox_result)

    artifact_request = create_artifact_request_from_dry_run(
        trace,
        sandbox_request,
        sandbox_result,
        relative_output_path,
        sandbox_decision=sandbox_decision,
        notes="M9-A dry-run artifact integration request",
    )
    artifact_result = write_sandbox_artifact(artifact_request, workspace_root)
    integration_result = DryRunArtifactIntegrationResult(
        run_id=trace.run_id,
        trace_state=DryRunAgentState(trace.state).value,
        artifact_request_id=artifact_request.artifact_request_id,
        artifact_result_id=artifact_result.artifact_result_id,
        workspace_root=artifact_result.workspace_root,
        relative_output_path=artifact_result.relative_output_path,
        resolved_output_path=artifact_result.resolved_output_path,
        content_hash=artifact_result.content_hash,
        write_attempted=artifact_result.write_attempted,
        write_completed=artifact_result.write_completed,
        execution_permitted=False,
        execution_triggered=False,
        provider_call_permitted=False,
        filesystem_scope="explicit_sandbox_workspace_only",
        reason=artifact_result.blocked_reason or "workspace-bound artifact write completed",
        notes="M9-A one-shot local dry-run artifact integration",
    )
    return (
        integration_result,
        trace,
        audit_events,
        sandbox_request,
        sandbox_decision,
        sandbox_result,
        artifact_request,
        artifact_result,
    )


def dry_run_artifact_integration_result_to_dict(result: DryRunArtifactIntegrationResult) -> dict[str, Any]:
    if not isinstance(result, DryRunArtifactIntegrationResult):
        raise TypeError("result must be a DryRunArtifactIntegrationResult")
    return result.to_dict()


def _assert_trace_and_sandbox_match(
    trace: DryRunAgentTrace,
    sandbox_request: SandboxRequest,
    sandbox_decision: SandboxPolicyDecision | None,
    sandbox_result: SandboxResult,
) -> None:
    if not isinstance(trace, DryRunAgentTrace):
        raise TypeError("trace must be a DryRunAgentTrace")
    if not isinstance(sandbox_request, SandboxRequest):
        raise TypeError("sandbox_request must be a SandboxRequest")
    if sandbox_decision is not None and not isinstance(sandbox_decision, SandboxPolicyDecision):
        raise TypeError("sandbox_decision must be a SandboxPolicyDecision or None")
    if not isinstance(sandbox_result, SandboxResult):
        raise TypeError("sandbox_result must be a SandboxResult")
    _assert_trace_has_no_authority(trace)
    if trace.sandbox_request_id != sandbox_request.sandbox_request_id:
        raise ValueError("trace sandbox request id must match sandbox request")
    if sandbox_decision is not None and trace.sandbox_policy_decision_id != sandbox_decision.decision_id:
        raise ValueError("trace sandbox decision id must match sandbox decision")
    if trace.sandbox_result_id != sandbox_result.result_id:
        raise ValueError("trace sandbox result id must match sandbox result")
    if sandbox_result.sandbox_request_id != sandbox_request.sandbox_request_id:
        raise ValueError("sandbox result must match sandbox request")
    if sandbox_decision is not None and sandbox_decision.sandbox_request_id != sandbox_request.sandbox_request_id:
        raise ValueError("sandbox decision must match sandbox request")


def _assert_trace_has_no_authority(trace: DryRunAgentTrace) -> None:
    if trace.execution_permitted or trace.execution_triggered:
        raise ValueError("M9-A dry-run trace cannot authorize execution")
    if trace.provider_call_permitted:
        raise ValueError("M9-A dry-run trace cannot permit provider calls")
    if trace.filesystem_persistence_permitted:
        raise ValueError("M9-A dry-run trace cannot permit persistence")


def _artifact_type_from_relative_path(relative_output_path: str) -> SandboxArtifactType:
    if relative_output_path.lower().endswith(".json"):
        return SandboxArtifactType.JSON_SUMMARY
    return SandboxArtifactType.TEXT_REPORT


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
