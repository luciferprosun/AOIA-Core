from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class DryRunAgentState(str, Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    PROPOSAL_RECORDED = "PROPOSAL_RECORDED"
    DECISION_RECORDED = "DECISION_RECORDED"
    AUDITED = "AUDITED"
    SANDBOX_EVALUATED = "SANDBOX_EVALUATED"
    COMPLETED_BLOCKED = "COMPLETED_BLOCKED"
    INVALID = "INVALID"


class DryRunStepType(str, Enum):
    GOAL_RECEIVED = "GOAL_RECEIVED"
    PLAN_STEP_CREATED = "PLAN_STEP_CREATED"
    ACTION_PROPOSAL_CREATED = "ACTION_PROPOSAL_CREATED"
    APPROVAL_DECISION_RECORDED = "APPROVAL_DECISION_RECORDED"
    AUDIT_EVENT_APPENDED = "AUDIT_EVENT_APPENDED"
    SANDBOX_REQUEST_CREATED = "SANDBOX_REQUEST_CREATED"
    SANDBOX_POLICY_EVALUATED = "SANDBOX_POLICY_EVALUATED"
    SANDBOX_RESULT_RECORDED = "SANDBOX_RESULT_RECORDED"
    EXECUTION_BLOCKED = "EXECUTION_BLOCKED"


class DryRunAgentFinalState(str, Enum):
    BLOCKED_NO_EXECUTION = "BLOCKED_NO_EXECUTION"
    NOT_IMPLEMENTED_NO_EXECUTION = "NOT_IMPLEMENTED_NO_EXECUTION"
    INVALID_NO_EXECUTION = "INVALID_NO_EXECUTION"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _coerce_bool(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")
    return value


def _coerce_int(name: str, value: int) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    return value


@dataclass(frozen=True)
class DryRunPlanStep:
    step_id: str
    step_index: int
    step_type: str
    title: str
    description: str
    proposed_action_type: str
    payload_summary: str
    exact_payload: str
    execution_intended: bool
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _coerce_text("step_id", self.step_id))
        object.__setattr__(self, "step_index", _coerce_int("step_index", self.step_index))
        object.__setattr__(self, "step_type", _coerce_text("step_type", self.step_type))
        object.__setattr__(self, "title", _coerce_text("title", self.title))
        object.__setattr__(self, "description", _coerce_text("description", self.description))
        object.__setattr__(self, "proposed_action_type", _coerce_text("proposed_action_type", self.proposed_action_type))
        object.__setattr__(self, "payload_summary", _coerce_text("payload_summary", self.payload_summary))
        object.__setattr__(self, "exact_payload", _coerce_text("exact_payload", self.exact_payload))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))
        if self.step_index < 0:
            raise ValueError("step_index must be non-negative")
        if self.execution_intended is not False:
            raise ValueError("execution_intended must remain False in M7-A")
        object.__setattr__(self, "execution_intended", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_index": self.step_index,
            "step_type": self.step_type,
            "title": self.title,
            "description": self.description,
            "proposed_action_type": self.proposed_action_type,
            "payload_summary": self.payload_summary,
            "exact_payload": self.exact_payload,
            "execution_intended": self.execution_intended,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class DryRunAgentRequest:
    run_id: str
    created_at: str
    goal_text: str
    requested_by: str
    plan_steps: tuple[DryRunPlanStep, ...]
    human_review_required: bool
    provider_generated: bool
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _coerce_text("run_id", self.run_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "goal_text", _coerce_text("goal_text", self.goal_text))
        object.__setattr__(self, "requested_by", _coerce_text("requested_by", self.requested_by))
        plan_steps = tuple(self.plan_steps)
        for step in plan_steps:
            if not isinstance(step, DryRunPlanStep):
                raise TypeError("plan_steps must contain DryRunPlanStep objects")
        if not plan_steps:
            raise ValueError("M7-A dry-run requests require at least one plan step")
        object.__setattr__(self, "plan_steps", plan_steps)
        object.__setattr__(self, "human_review_required", _coerce_bool("human_review_required", self.human_review_required))
        object.__setattr__(self, "provider_generated", _coerce_bool("provider_generated", self.provider_generated))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "goal_text": self.goal_text,
            "requested_by": self.requested_by,
            "plan_steps": [step.to_dict() for step in self.plan_steps],
            "human_review_required": self.human_review_required,
            "provider_generated": self.provider_generated,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class DryRunAgentTrace:
    run_id: str
    created_at: str
    state: DryRunAgentState
    final_state: DryRunAgentFinalState
    goal_hash: str
    proposal_id: str
    decision_id: str
    latest_audit_event_id: str
    latest_audit_event_hash: str
    sandbox_request_id: str
    sandbox_policy_decision_id: str
    sandbox_result_id: str
    execution_permitted: bool
    execution_triggered: bool
    provider_call_permitted: bool
    filesystem_persistence_permitted: bool
    audit_chain_length: int
    reason: str
    notes: str

    def __post_init__(self) -> None:
        state = DryRunAgentState(self.state)
        final_state = DryRunAgentFinalState(self.final_state)
        object.__setattr__(self, "run_id", _coerce_text("run_id", self.run_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "final_state", final_state)
        object.__setattr__(self, "goal_hash", _coerce_text("goal_hash", self.goal_hash))
        object.__setattr__(self, "proposal_id", _coerce_text("proposal_id", self.proposal_id))
        object.__setattr__(self, "decision_id", _coerce_text("decision_id", self.decision_id))
        object.__setattr__(self, "latest_audit_event_id", _coerce_text("latest_audit_event_id", self.latest_audit_event_id))
        object.__setattr__(self, "latest_audit_event_hash", _coerce_text("latest_audit_event_hash", self.latest_audit_event_hash))
        object.__setattr__(self, "sandbox_request_id", _coerce_text("sandbox_request_id", self.sandbox_request_id))
        object.__setattr__(
            self,
            "sandbox_policy_decision_id",
            _coerce_text("sandbox_policy_decision_id", self.sandbox_policy_decision_id),
        )
        object.__setattr__(self, "sandbox_result_id", _coerce_text("sandbox_result_id", self.sandbox_result_id))
        object.__setattr__(self, "audit_chain_length", _coerce_int("audit_chain_length", self.audit_chain_length))
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))
        if self.execution_permitted is not False:
            raise ValueError("execution_permitted must remain False in M7-A")
        if self.execution_triggered is not False:
            raise ValueError("execution_triggered must remain False in M7-A")
        if self.provider_call_permitted is not False:
            raise ValueError("provider_call_permitted must remain False in M7-A")
        if self.filesystem_persistence_permitted is not False:
            raise ValueError("filesystem_persistence_permitted must remain False in M7-A")
        object.__setattr__(self, "execution_permitted", False)
        object.__setattr__(self, "execution_triggered", False)
        object.__setattr__(self, "provider_call_permitted", False)
        object.__setattr__(self, "filesystem_persistence_permitted", False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "state": self.state.value,
            "final_state": self.final_state.value,
            "goal_hash": self.goal_hash,
            "proposal_id": self.proposal_id,
            "decision_id": self.decision_id,
            "latest_audit_event_id": self.latest_audit_event_id,
            "latest_audit_event_hash": self.latest_audit_event_hash,
            "sandbox_request_id": self.sandbox_request_id,
            "sandbox_policy_decision_id": self.sandbox_policy_decision_id,
            "sandbox_result_id": self.sandbox_result_id,
            "execution_permitted": self.execution_permitted,
            "execution_triggered": self.execution_triggered,
            "provider_call_permitted": self.provider_call_permitted,
            "filesystem_persistence_permitted": self.filesystem_persistence_permitted,
            "audit_chain_length": self.audit_chain_length,
            "reason": self.reason,
            "notes": self.notes,
        }


def create_dry_run_plan_step(
    *,
    title: str,
    description: str,
    proposed_action_type: str,
    payload_summary: str,
    exact_payload: str,
    step_index: int = 0,
    step_type: str = DryRunStepType.PLAN_STEP_CREATED.value,
    execution_intended: bool = False,
    notes: str = "",
    step_id: str | None = None,
) -> DryRunPlanStep:
    if execution_intended is not False:
        raise ValueError("execution_intended must remain False in M7-A")
    record_id = step_id or "dry-run-step-" + _hash_text(
        "\n".join([str(step_index), step_type, proposed_action_type, payload_summary, exact_payload])
    )[:24]
    return DryRunPlanStep(
        step_id=record_id,
        step_index=step_index,
        step_type=step_type,
        title=title,
        description=description,
        proposed_action_type=proposed_action_type,
        payload_summary=payload_summary,
        exact_payload=exact_payload,
        execution_intended=False,
        notes=notes,
    )


def create_dry_run_agent_request(
    *,
    goal_text: str,
    requested_by: str,
    plan_steps: tuple[DryRunPlanStep, ...] | list[DryRunPlanStep],
    human_review_required: bool = True,
    provider_generated: bool = False,
    notes: str = "",
    created_at: str | None = None,
    run_id: str | None = None,
) -> DryRunAgentRequest:
    steps = tuple(plan_steps)
    if not steps:
        raise ValueError("M7-A dry-run requests require at least one plan step")
    timestamp = created_at or _utc_now_iso()
    goal = _coerce_text("goal_text", goal_text)
    record_id = run_id or "dry-run-agent-" + _hash_text(
        "\n".join([goal, requested_by, steps[0].step_id, timestamp])
    )[:24]
    return DryRunAgentRequest(
        run_id=record_id,
        created_at=timestamp,
        goal_text=goal,
        requested_by=requested_by,
        plan_steps=steps,
        human_review_required=human_review_required,
        provider_generated=provider_generated,
        notes=notes,
    )


def dry_run_agent_trace_to_dict(trace: DryRunAgentTrace) -> dict[str, Any]:
    if not isinstance(trace, DryRunAgentTrace):
        raise TypeError("trace must be a DryRunAgentTrace")
    return trace.to_dict()


def hash_dry_run_goal(goal_text: str) -> str:
    return _hash_text(_coerce_text("goal_text", goal_text))
