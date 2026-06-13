from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.safety.dry_run_artifact_integration import run_dry_run_agent_and_write_artifact_with_durable_audit
from runtime.schemas.action_proposal import ActionProposalType
from runtime.schemas.dry_run_agent import (
    create_dry_run_agent_request,
    create_dry_run_plan_step,
)


MAX_LOCAL_AGENT_GOAL_CHARS = 4096


@dataclass(frozen=True)
class LocalAgentEntrypointResult:
    completed: bool
    durable_audit_required: bool
    durable_audit_completed: bool
    artifact_write_completed: bool
    workspace_root: str
    audit_log_path: str | None
    artifact_path: str | None
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.completed, bool):
            raise TypeError("completed must be bool")
        if self.durable_audit_required is not True:
            raise ValueError("durable_audit_required must be True")
        if not isinstance(self.durable_audit_completed, bool):
            raise TypeError("durable_audit_completed must be bool")
        if not isinstance(self.artifact_write_completed, bool):
            raise TypeError("artifact_write_completed must be bool")
        object.__setattr__(self, "workspace_root", _coerce_text("workspace_root", self.workspace_root))
        if self.audit_log_path is not None:
            object.__setattr__(self, "audit_log_path", _coerce_text("audit_log_path", self.audit_log_path))
        if self.artifact_path is not None:
            object.__setattr__(self, "artifact_path", _coerce_text("artifact_path", self.artifact_path))
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed": self.completed,
            "durable_audit_required": self.durable_audit_required,
            "durable_audit_completed": self.durable_audit_completed,
            "artifact_write_completed": self.artifact_write_completed,
            "workspace_root": self.workspace_root,
            "audit_log_path": self.audit_log_path,
            "artifact_path": self.artifact_path,
            "reason": self.reason,
        }


def run_durable_local_agent_entrypoint(
    *,
    goal: str,
    workspace_root: str | Path,
    audit_dir: str | Path,
    relative_output_path: str = "aoia_agent_v0_result.md",
    approval_actor_id: str = "human-reviewer",
) -> LocalAgentEntrypointResult:
    normalized_goal = _normalize_goal(goal)
    workspace_path = _require_absolute_path("workspace_root", workspace_root)
    audit_path = _require_absolute_path("audit_dir", audit_dir)
    dry_run_request = _create_local_agent_request(normalized_goal)

    (
        durable_result,
        _trace,
        _audit_events,
        _sandbox_request,
        _sandbox_decision,
        _sandbox_result,
        _artifact_request,
        artifact_result,
        _durable_writes,
    ) = run_dry_run_agent_and_write_artifact_with_durable_audit(
        dry_run_request,
        str(workspace_path),
        str(audit_path),
        relative_output_path=relative_output_path,
        approval_actor_id=approval_actor_id,
    )
    completed = bool(durable_result.durable_audit_write_completed and artifact_result.write_completed)
    return LocalAgentEntrypointResult(
        completed=completed,
        durable_audit_required=True,
        durable_audit_completed=durable_result.durable_audit_write_completed,
        artifact_write_completed=artifact_result.write_completed,
        workspace_root=artifact_result.workspace_root or str(workspace_path),
        audit_log_path=durable_result.durable_audit_path or None,
        artifact_path=artifact_result.resolved_output_path if artifact_result.write_completed else None,
        reason=durable_result.reason,
    )


def local_agent_entrypoint_result_to_dict(result: LocalAgentEntrypointResult) -> dict[str, Any]:
    if not isinstance(result, LocalAgentEntrypointResult):
        raise TypeError("result must be a LocalAgentEntrypointResult")
    return result.to_dict()


def _create_local_agent_request(goal: str):
    goal_hash = _hash_text(goal)
    exact_payload = "\n".join(
        (
            "local_agent_entrypoint=v0",
            "planning_mode=deterministic_local_template",
            "requested_action=durable_workspace_bound_summary_artifact",
            f"goal_hash={goal_hash}",
        )
    )
    step = create_dry_run_plan_step(
        title="Durable local controlled-agent artifact",
        description="Create a local dry-run trace and one durable-audit-bound workspace artifact.",
        proposed_action_type=ActionProposalType.HUMAN_REVIEW_ONLY.value,
        payload_summary="deterministic local durable-agent entrypoint plan",
        exact_payload=exact_payload,
        step_index=0,
        step_id="local-agent-entrypoint-step-" + goal_hash[:24],
        notes="Macrostep 3A local template plan; no provider planning",
    )
    return create_dry_run_agent_request(
        goal_text=goal,
        requested_by="human-local-entrypoint",
        plan_steps=(step,),
        human_review_required=True,
        provider_generated=False,
        notes="Macrostep 3A durable local agent entrypoint request",
        run_id="local-agent-entrypoint-" + goal_hash[:24],
    )


def _normalize_goal(goal: str) -> str:
    normalized = _coerce_text("goal", goal).strip()
    if not normalized:
        raise ValueError("Macrostep 3A local agent entrypoint requires a non-empty human goal")
    if len(normalized) > MAX_LOCAL_AGENT_GOAL_CHARS:
        raise ValueError("Macrostep 3A local agent entrypoint goal is too long")
    for character in normalized:
        codepoint = ord(character)
        if (codepoint < 32 and character not in ("\n", "\t")) or codepoint == 127:
            raise ValueError("Macrostep 3A local agent entrypoint goal contains a blocked control character")
    return normalized


def _require_absolute_path(name: str, value: str | Path) -> Path:
    if isinstance(value, Path):
        raw_path = value
    elif isinstance(value, str):
        raw_path = Path(value)
    else:
        raise TypeError(f"{name} must be a string or Path")
    if not str(raw_path).strip():
        raise ValueError(f"{name} must be explicit")
    if not raw_path.is_absolute():
        raise ValueError(f"{name} must be absolute")
    return raw_path


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
