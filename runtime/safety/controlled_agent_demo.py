from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from runtime.safety.dry_run_artifact_integration import run_dry_run_agent_and_write_artifact
from runtime.schemas.action_proposal import ActionProposalType
from runtime.schemas.audit_event import AuditEvent
from runtime.schemas.dry_run_agent import (
    DryRunAgentRequest,
    DryRunAgentTrace,
    DryRunPlanStep,
    create_dry_run_agent_request,
    create_dry_run_plan_step,
)
from runtime.schemas.sandbox_artifact import SandboxArtifactRequest, SandboxArtifactResult
from runtime.schemas.sandbox_contract import SandboxPolicyDecision, SandboxRequest, SandboxResult


@dataclass(frozen=True)
class ControlledAgentDemoResult:
    demo_id: str
    created_at: str
    goal_hash: str
    run_id: str
    trace_state: str
    final_state: str
    artifact_result_id: str
    workspace_root: str
    relative_output_path: str
    resolved_output_path: str
    write_completed: bool
    execution_permitted: bool
    execution_triggered: bool
    provider_call_permitted: bool
    filesystem_scope: str
    summary: str
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "demo_id", _coerce_text("demo_id", self.demo_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "goal_hash", _coerce_text("goal_hash", self.goal_hash))
        object.__setattr__(self, "run_id", _coerce_text("run_id", self.run_id))
        object.__setattr__(self, "trace_state", _coerce_text("trace_state", self.trace_state))
        object.__setattr__(self, "final_state", _coerce_text("final_state", self.final_state))
        object.__setattr__(self, "artifact_result_id", _coerce_text("artifact_result_id", self.artifact_result_id))
        object.__setattr__(self, "workspace_root", _coerce_text("workspace_root", self.workspace_root))
        object.__setattr__(self, "relative_output_path", _coerce_text("relative_output_path", self.relative_output_path))
        object.__setattr__(self, "resolved_output_path", _coerce_text("resolved_output_path", self.resolved_output_path))
        object.__setattr__(self, "filesystem_scope", _coerce_text("filesystem_scope", self.filesystem_scope))
        object.__setattr__(self, "summary", _coerce_text("summary", self.summary))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))
        if self.write_completed is not True and self.write_completed is not False:
            raise TypeError("write_completed must be bool")
        if self.execution_permitted is not False:
            raise ValueError("execution_permitted must remain False in M10-A")
        if self.execution_triggered is not False:
            raise ValueError("execution_triggered must remain False in M10-A")
        if self.provider_call_permitted is not False:
            raise ValueError("provider_call_permitted must remain False in M10-A")
        object.__setattr__(self, "execution_permitted", False)
        object.__setattr__(self, "execution_triggered", False)
        object.__setattr__(self, "provider_call_permitted", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "demo_id": self.demo_id,
            "created_at": self.created_at,
            "goal_hash": self.goal_hash,
            "run_id": self.run_id,
            "trace_state": self.trace_state,
            "final_state": self.final_state,
            "artifact_result_id": self.artifact_result_id,
            "workspace_root": self.workspace_root,
            "relative_output_path": self.relative_output_path,
            "resolved_output_path": self.resolved_output_path,
            "write_completed": self.write_completed,
            "execution_permitted": self.execution_permitted,
            "execution_triggered": self.execution_triggered,
            "provider_call_permitted": self.provider_call_permitted,
            "filesystem_scope": self.filesystem_scope,
            "summary": self.summary,
            "notes": self.notes,
        }


def build_demo_plan_from_goal(goal_text: str) -> DryRunPlanStep:
    goal = _normalize_goal(goal_text)
    goal_hash = _hash_text(goal)
    exact_payload = "\n".join(
        (
            "controlled_agent_demo_task=v0",
            "planning_mode=deterministic_local_template",
            "requested_action=human_review_only_summary_artifact",
            f"goal_hash={goal_hash}",
        )
    )
    return create_dry_run_plan_step(
        title="Controlled agent v0 local summary artifact",
        description="Create a dry-run record and one workspace-bound summary artifact.",
        proposed_action_type=ActionProposalType.HUMAN_REVIEW_ONLY.value,
        payload_summary="deterministic local controlled-agent demo plan",
        exact_payload=exact_payload,
        step_index=0,
        step_id="controlled-agent-demo-step-" + goal_hash[:24],
        notes="M10-A local template plan; no provider planning",
    )


def create_controlled_agent_demo_request(
    goal_text: str,
    requested_by: str = "human-demo-user",
    notes: str = "",
) -> DryRunAgentRequest:
    goal = _normalize_goal(goal_text)
    requester = _coerce_text("requested_by", requested_by)
    step = build_demo_plan_from_goal(goal)
    goal_hash = _hash_text(goal)
    return create_dry_run_agent_request(
        goal_text=goal,
        requested_by=requester,
        plan_steps=(step,),
        human_review_required=True,
        provider_generated=False,
        notes=notes,
        run_id="controlled-agent-demo-" + _hash_text(goal + "\n" + requester)[:24],
    )


def run_controlled_agent_demo(
    goal_text: str,
    workspace_root: str,
    relative_output_path: str = "aoia_controlled_agent_v0_demo.md",
    requested_by: str = "human-demo-user",
    notes: str = "",
) -> tuple[
    ControlledAgentDemoResult,
    DryRunAgentTrace,
    tuple[AuditEvent, ...],
    SandboxRequest,
    SandboxPolicyDecision,
    SandboxResult,
    SandboxArtifactRequest,
    SandboxArtifactResult,
]:
    request = create_controlled_agent_demo_request(goal_text, requested_by=requested_by, notes=notes)
    (
        integration_result,
        trace,
        audit_events,
        sandbox_request,
        sandbox_decision,
        sandbox_result,
        artifact_request,
        artifact_result,
    ) = run_dry_run_agent_and_write_artifact(
        request,
        workspace_root,
        relative_output_path=relative_output_path,
    )
    result = ControlledAgentDemoResult(
        demo_id="controlled-agent-demo-result-" + _hash_text(
            "\n".join([request.run_id, artifact_result.artifact_result_id, artifact_result.content_hash])
        )[:24],
        created_at=_utc_now_iso(),
        goal_hash=trace.goal_hash,
        run_id=trace.run_id,
        trace_state=trace.state.value,
        final_state=trace.final_state.value,
        artifact_result_id=artifact_result.artifact_result_id,
        workspace_root=artifact_result.workspace_root,
        relative_output_path=artifact_result.relative_output_path,
        resolved_output_path=artifact_result.resolved_output_path,
        write_completed=artifact_result.write_completed,
        execution_permitted=False,
        execution_triggered=False,
        provider_call_permitted=False,
        filesystem_scope=integration_result.filesystem_scope,
        summary=integration_result.reason,
        notes="M10-A one-shot controlled agent demo flow",
    )
    return (
        result,
        trace,
        audit_events,
        sandbox_request,
        sandbox_decision,
        sandbox_result,
        artifact_request,
        artifact_result,
    )


def controlled_agent_demo_result_to_dict(result: ControlledAgentDemoResult) -> dict[str, Any]:
    if not isinstance(result, ControlledAgentDemoResult):
        raise TypeError("result must be a ControlledAgentDemoResult")
    return result.to_dict()


def _normalize_goal(goal_text: str) -> str:
    goal = _coerce_text("goal_text", goal_text).strip()
    if not goal:
        raise ValueError("M10-A controlled agent demo requires a non-empty human goal")
    return goal


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
