from __future__ import annotations

import datetime as dt
import hashlib
import importlib
import json
import math
import os
import re
import stat
import sys
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping


# The installed project supports both ``runtime.*`` imports and the historical
# top-level module layout.  Keep one class/enum identity across both spellings;
# otherwise ``TaskPhase.TERMINAL`` from one spelling fails identity checks in
# code imported through the other spelling.
if __name__ == "runtime.task_checkpoints":
    sys.modules.setdefault("task_checkpoints", sys.modules[__name__])
elif __name__ == "task_checkpoints":
    sys.modules.setdefault("runtime.task_checkpoints", sys.modules[__name__])

from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    InterProcessFileLock,
    PersistenceError,
    StateCorruptionError,
    locked_update_json,
    read_json_snapshot,
    state_resource_lock_path,
    validate_lock_timeout_seconds,
)


TASK_CHECKPOINT_SCHEMA_VERSION = "AOIA_TASK_CHECKPOINT_1A"
TASK_TRANSITION_SCHEMA_VERSION = "AOIA_TASK_TRANSITION_1A"
MAX_TASK_TRANSITIONS = 4096
MAX_SAFE_CONTEXT_HASHES = 128
MAX_TASK_STEPS = 10_000
MAX_PROVIDER_ATTEMPTS = 1_000_000
MAX_TASK_CHECKPOINT_BYTES = 2 * 1024 * 1024
GENESIS_TRANSITION_HASH = "0" * 64

_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SAFE_REASON = re.compile(r"^[A-Z0-9_.:-]{1,160}$")


class TaskCheckpointError(PersistenceError):
    reason_code = "TASK_CHECKPOINT_ERROR"


class TaskCheckpointCorruptionError(TaskCheckpointError):
    reason_code = "TASK_CHECKPOINT_CORRUPT"


class TaskCheckpointSchemaError(TaskCheckpointError):
    reason_code = "TASK_CHECKPOINT_UNSUPPORTED_SCHEMA"


class TaskTransitionError(TaskCheckpointError):
    reason_code = "TASK_ILLEGAL_TRANSITION"


class TaskCheckpointConflictError(TaskCheckpointError):
    reason_code = "TASK_CHECKPOINT_VERSION_CONFLICT"


class TaskBudgetError(TaskCheckpointError):
    reason_code = "TASK_BUDGET_EXHAUSTED"


class TaskStepReservationError(TaskCheckpointError):
    reason_code = "TASK_STEP_RESERVATION_INVALID"


class TaskState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class TaskPhase(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    BETWEEN_STEPS = "BETWEEN_STEPS"
    BEFORE_MODEL_CALL = "BEFORE_MODEL_CALL"
    AFTER_MODEL_CALL = "AFTER_MODEL_CALL"
    BEFORE_ACTION_POLICY = "BEFORE_ACTION_POLICY"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    BEFORE_DISPATCH = "BEFORE_DISPATCH"
    IDEMPOTENCY_RESERVED = "IDEMPOTENCY_RESERVED"
    PROVENANCE_DISPATCH_RECORDED = "PROVENANCE_DISPATCH_RECORDED"
    DISPATCH_IN_FLIGHT = "DISPATCH_IN_FLIGHT"
    AFTER_ACTION = "AFTER_ACTION"
    TERMINAL = "TERMINAL"


class ApprovalState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"
    WAITING = "WAITING"
    GRANTED_IN_PROCESS = "GRANTED_IN_PROCESS"
    DENIED = "DENIED"
    FRESH_APPROVAL_REQUIRED = "FRESH_APPROVAL_REQUIRED"


class SafeResumeClassification(str, Enum):
    SAFE_TO_RESUME = "SAFE_TO_RESUME"
    WAITING_FOR_FRESH_APPROVAL = "WAITING_FOR_FRESH_APPROVAL"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    TERMINAL_NO_RESUME = "TERMINAL_NO_RESUME"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"
    CORRUPT_CHECKPOINT = "CORRUPT_CHECKPOINT"
    UNSUPPORTED_SCHEMA = "UNSUPPORTED_SCHEMA"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"


@dataclass(frozen=True)
class StepReservation:
    """Opaque in-process proof that one durable logical step was debited."""

    task_id: str
    step_index: int
    checkpoint_version: int
    checkpoint_hash: str
    checkpoint_event_id: str
    _nonce: str
    recovery_attempt_id: str | None = None


@dataclass(frozen=True)
class ModelContinuation:
    """Opaque live-process proof for a second provider call in one step."""

    task_id: str
    prior_model_call_id: str
    checkpoint_version: int
    checkpoint_hash: str
    checkpoint_event_id: str
    _nonce: str


TERMINAL_TASK_STATES = frozenset(
    {
        TaskState.COMPLETED,
        TaskState.PARTIAL,
        TaskState.BLOCKED,
        TaskState.CANCELLED,
        TaskState.FAILED,
    }
)

LEGAL_STATE_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.CREATED: frozenset(
        {
            TaskState.RUNNING,
            TaskState.COMPLETED,
            TaskState.PARTIAL,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
            TaskState.FAILED,
        }
    ),
    TaskState.RUNNING: frozenset(
        {
            TaskState.RUNNING,
            TaskState.WAITING_FOR_APPROVAL,
            TaskState.PAUSED,
            TaskState.COMPLETED,
            TaskState.PARTIAL,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
            TaskState.FAILED,
            TaskState.RECOVERY_REQUIRED,
        }
    ),
    TaskState.WAITING_FOR_APPROVAL: frozenset(
        {
            TaskState.RUNNING,
            TaskState.BLOCKED,
            TaskState.CANCELLED,
            TaskState.FAILED,
            TaskState.RECOVERY_REQUIRED,
        }
    ),
    TaskState.PAUSED: frozenset(
        {TaskState.RUNNING, TaskState.CANCELLED, TaskState.FAILED, TaskState.RECOVERY_REQUIRED}
    ),
    TaskState.RECOVERY_REQUIRED: frozenset(
        {TaskState.PAUSED, TaskState.CANCELLED, TaskState.FAILED}
    ),
}

TERMINAL_ACTION_OUTCOMES: dict[TaskState, frozenset[str]] = {
    TaskState.COMPLETED: frozenset({"SUCCEEDED"}),
    TaskState.BLOCKED: frozenset({"BLOCKED"}),
    TaskState.CANCELLED: frozenset({"CANCELLED"}),
    TaskState.FAILED: frozenset(
        {"FAILED_BEFORE_DISPATCH", "FAILED_REPORTED"}
    ),
    # A partial task is a task-level aggregate.  One action outcome cannot by
    # itself prove that aggregate terminal state.
    TaskState.PARTIAL: frozenset(),
}


def _terminal_action_outcome_matches(
    task_state: TaskState,
    reason_code: str,
    idempotency_state: str,
) -> bool:
    if reason_code == "TASK_IDEMPOTENCY_CONFLICT":
        return (
            task_state is TaskState.BLOCKED
            and idempotency_state == "CONFLICT"
        )
    if idempotency_state == "CONFLICT":
        return False
    return idempotency_state in TERMINAL_ACTION_OUTCOMES.get(
        task_state,
        frozenset(),
    )

TASK_REASON_CODES = frozenset(
    {
        "TASK_CREATED",
        "STANDALONE_ACTION_TASK_CREATED",
        "TASK_STARTED",
        "TASK_STEP_RESERVED",
        "TASK_BEFORE_MODEL_CALL",
        "TASK_MODEL_ATTEMPT_STARTED",
        "TASK_MODEL_CONTINUATION_STARTED",
        "TASK_MODEL_CALL_COMPLETED",
        "TASK_MODEL_CALL_FAILED",
        "TASK_RECOVERY_STEP_REMINTED",
        "TASK_RECOVERY_RESUME_PREPARED",
        "TASK_AFTER_MODEL_RESULT",
        "TASK_BEFORE_ACTION_POLICY",
        "TASK_WAITING_FOR_APPROVAL",
        "TASK_APPROVAL_GRANTED_IN_PROCESS",
        "TASK_APPROVAL_DENIED",
        "TASK_BEFORE_DISPATCH",
        "TASK_IDEMPOTENCY_RESERVED",
        "TASK_PROVENANCE_DISPATCH_RECORDED",
        "TASK_DISPATCH_IN_FLIGHT",
        "TASK_ACTION_COMPLETED",
        "TASK_ACTION_BLOCKED",
        "TASK_ACTION_CANCELLED",
        "TASK_ACTION_UNKNOWN_OUTCOME",
        "TASK_IDEMPOTENCY_CONFLICT",
        "TASK_BETWEEN_STEPS",
        "TASK_COMPLETED",
        "TASK_PARTIAL",
        "TASK_BLOCKED",
        "TASK_CANCELLED",
        "TASK_FAILED",
        "TASK_RECOVERY_REQUIRED",
        "TASK_PAUSED",
    }
)

TASK_STATE_PHASE_REASONS: dict[
    tuple[TaskState, TaskPhase], frozenset[str]
] = {
    (TaskState.CREATED, TaskPhase.TASK_CREATED): frozenset(
        {"TASK_CREATED", "STANDALONE_ACTION_TASK_CREATED"}
    ),
    (TaskState.RUNNING, TaskPhase.BETWEEN_STEPS): frozenset(
        {"TASK_STARTED", "TASK_BETWEEN_STEPS", "TASK_RECOVERY_RESUME_PREPARED"}
    ),
    (TaskState.RUNNING, TaskPhase.BEFORE_MODEL_CALL): frozenset(
        {
            "TASK_STEP_RESERVED",
            "TASK_BEFORE_MODEL_CALL",
            "TASK_MODEL_ATTEMPT_STARTED",
            "TASK_MODEL_CONTINUATION_STARTED",
            "TASK_MODEL_CALL_FAILED",
            "TASK_RECOVERY_STEP_REMINTED",
        }
    ),
    (TaskState.RUNNING, TaskPhase.AFTER_MODEL_CALL): frozenset(
        {"TASK_MODEL_CALL_COMPLETED", "TASK_AFTER_MODEL_RESULT"}
    ),
    (TaskState.RUNNING, TaskPhase.BEFORE_ACTION_POLICY): frozenset(
        {"TASK_BEFORE_ACTION_POLICY"}
    ),
    (TaskState.WAITING_FOR_APPROVAL, TaskPhase.WAITING_FOR_APPROVAL): frozenset(
        {"TASK_WAITING_FOR_APPROVAL"}
    ),
    (TaskState.RUNNING, TaskPhase.BEFORE_DISPATCH): frozenset(
        {"TASK_BEFORE_DISPATCH", "TASK_APPROVAL_GRANTED_IN_PROCESS"}
    ),
    (TaskState.RUNNING, TaskPhase.IDEMPOTENCY_RESERVED): frozenset(
        {"TASK_IDEMPOTENCY_RESERVED"}
    ),
    (TaskState.RUNNING, TaskPhase.PROVENANCE_DISPATCH_RECORDED): frozenset(
        {"TASK_PROVENANCE_DISPATCH_RECORDED"}
    ),
    (TaskState.RUNNING, TaskPhase.DISPATCH_IN_FLIGHT): frozenset(
        {"TASK_DISPATCH_IN_FLIGHT"}
    ),
    (TaskState.RUNNING, TaskPhase.AFTER_ACTION): frozenset(
        {"TASK_ACTION_COMPLETED"}
    ),
    (TaskState.PAUSED, TaskPhase.BETWEEN_STEPS): frozenset({"TASK_PAUSED"}),
    (TaskState.RECOVERY_REQUIRED, TaskPhase.IDEMPOTENCY_RESERVED): frozenset(
        {"TASK_RECOVERY_REQUIRED"}
    ),
    (TaskState.RECOVERY_REQUIRED, TaskPhase.PROVENANCE_DISPATCH_RECORDED): frozenset(
        {"TASK_RECOVERY_REQUIRED"}
    ),
    (TaskState.RECOVERY_REQUIRED, TaskPhase.DISPATCH_IN_FLIGHT): frozenset(
        {"TASK_RECOVERY_REQUIRED", "TASK_ACTION_UNKNOWN_OUTCOME"}
    ),
    (TaskState.RECOVERY_REQUIRED, TaskPhase.AFTER_ACTION): frozenset(
        {"TASK_RECOVERY_REQUIRED", "TASK_ACTION_UNKNOWN_OUTCOME"}
    ),
    (TaskState.COMPLETED, TaskPhase.TERMINAL): frozenset({"TASK_COMPLETED"}),
    (TaskState.PARTIAL, TaskPhase.TERMINAL): frozenset({"TASK_PARTIAL"}),
    (TaskState.BLOCKED, TaskPhase.TERMINAL): frozenset(
        {"TASK_BLOCKED", "TASK_ACTION_BLOCKED", "TASK_IDEMPOTENCY_CONFLICT"}
    ),
    (TaskState.CANCELLED, TaskPhase.TERMINAL): frozenset(
        {"TASK_CANCELLED", "TASK_APPROVAL_DENIED", "TASK_ACTION_CANCELLED"}
    ),
    (TaskState.FAILED, TaskPhase.TERMINAL): frozenset({"TASK_FAILED"}),
}

_STEP_RESERVATION_SOURCES = frozenset(
    {
        (TaskState.CREATED, TaskPhase.TASK_CREATED),
        (TaskState.RUNNING, TaskPhase.BETWEEN_STEPS),
        (TaskState.RUNNING, TaskPhase.AFTER_ACTION),
    }
)


def _validate_transition_edge(
    prior: "TaskTransition | None",
    current: "TaskTransition",
) -> None:
    if prior is None:
        if (
            current.from_state is not None
            or current.from_phase is not None
            or current.to_state != TaskState.CREATED.value
            or current.to_phase != TaskPhase.TASK_CREATED.value
        ):
            raise TaskCheckpointCorruptionError(
                "Task transition genesis edge is invalid."
            )
        return

    source = (TaskState(prior.to_state), TaskPhase(prior.to_phase))
    target = (TaskState(current.to_state), TaskPhase(current.to_phase))
    terminal_target = target[0] in TERMINAL_TASK_STATES and target[1] is TaskPhase.TERMINAL
    legal = False
    if current.reason_code == "TASK_STEP_RESERVED":
        legal = source in _STEP_RESERVATION_SOURCES and target == (
            TaskState.RUNNING,
            TaskPhase.BEFORE_MODEL_CALL,
        )
    elif current.reason_code in {
        "TASK_MODEL_ATTEMPT_STARTED",
        "TASK_MODEL_CALL_FAILED",
        "TASK_BEFORE_MODEL_CALL",
        "TASK_RECOVERY_STEP_REMINTED",
    }:
        legal = source == (TaskState.RUNNING, TaskPhase.BEFORE_MODEL_CALL) and target == source
    elif current.reason_code == "TASK_RECOVERY_RESUME_PREPARED":
        legal = source == (TaskState.RUNNING, TaskPhase.BETWEEN_STEPS) and target == source
    elif current.reason_code in {"TASK_MODEL_CALL_COMPLETED", "TASK_AFTER_MODEL_RESULT"}:
        legal = source in {
            (TaskState.RUNNING, TaskPhase.BEFORE_MODEL_CALL),
            (TaskState.RUNNING, TaskPhase.AFTER_MODEL_CALL),
        } and target == (TaskState.RUNNING, TaskPhase.AFTER_MODEL_CALL)
    elif current.reason_code == "TASK_MODEL_CONTINUATION_STARTED":
        legal = source == (TaskState.RUNNING, TaskPhase.AFTER_MODEL_CALL) and target == (
            TaskState.RUNNING,
            TaskPhase.BEFORE_MODEL_CALL,
        )
    elif current.reason_code == "TASK_STARTED":
        legal = source == (TaskState.CREATED, TaskPhase.TASK_CREATED) and target == (
            TaskState.RUNNING,
            TaskPhase.BETWEEN_STEPS,
        )
    elif current.reason_code == "TASK_BEFORE_ACTION_POLICY":
        legal = source in {
            (TaskState.RUNNING, TaskPhase.BEFORE_MODEL_CALL),
            (TaskState.RUNNING, TaskPhase.AFTER_MODEL_CALL),
        } and target == (TaskState.RUNNING, TaskPhase.BEFORE_ACTION_POLICY)
    elif current.reason_code == "TASK_WAITING_FOR_APPROVAL":
        legal = source == (TaskState.RUNNING, TaskPhase.BEFORE_ACTION_POLICY) and target == (
            TaskState.WAITING_FOR_APPROVAL,
            TaskPhase.WAITING_FOR_APPROVAL,
        )
    elif current.reason_code == "TASK_APPROVAL_GRANTED_IN_PROCESS":
        legal = source in {
            (
                TaskState.WAITING_FOR_APPROVAL,
                TaskPhase.WAITING_FOR_APPROVAL,
            ),
            # Direct trusted compatibility calls may obtain the real callback
            # before their first durable task checkpoint.  They still persist
            # the granted-in-process truth before any dispatch work.
            (TaskState.RUNNING, TaskPhase.BEFORE_ACTION_POLICY),
        } and target == (TaskState.RUNNING, TaskPhase.BEFORE_DISPATCH)
    elif current.reason_code == "TASK_BEFORE_DISPATCH":
        legal = source == (TaskState.RUNNING, TaskPhase.BEFORE_ACTION_POLICY) and target == (
            TaskState.RUNNING,
            TaskPhase.BEFORE_DISPATCH,
        )
    elif current.reason_code == "TASK_IDEMPOTENCY_RESERVED":
        legal = source == (TaskState.RUNNING, TaskPhase.BEFORE_DISPATCH) and target == (
            TaskState.RUNNING,
            TaskPhase.IDEMPOTENCY_RESERVED,
        )
    elif current.reason_code == "TASK_PROVENANCE_DISPATCH_RECORDED":
        legal = source == (TaskState.RUNNING, TaskPhase.IDEMPOTENCY_RESERVED) and target == (
            TaskState.RUNNING,
            TaskPhase.PROVENANCE_DISPATCH_RECORDED,
        )
    elif current.reason_code == "TASK_DISPATCH_IN_FLIGHT":
        legal = source == (
            TaskState.RUNNING,
            TaskPhase.PROVENANCE_DISPATCH_RECORDED,
        ) and target == (TaskState.RUNNING, TaskPhase.DISPATCH_IN_FLIGHT)
    elif current.reason_code == "TASK_ACTION_COMPLETED":
        legal = source in {
            (TaskState.RUNNING, TaskPhase.DISPATCH_IN_FLIGHT),
            (TaskState.RUNNING, TaskPhase.IDEMPOTENCY_RESERVED),
        } and target == (TaskState.RUNNING, TaskPhase.AFTER_ACTION)
    elif current.reason_code in {"TASK_RECOVERY_REQUIRED", "TASK_ACTION_UNKNOWN_OUTCOME"}:
        legal = source[1] in {
            TaskPhase.BEFORE_DISPATCH,
            TaskPhase.IDEMPOTENCY_RESERVED,
            TaskPhase.PROVENANCE_DISPATCH_RECORDED,
            TaskPhase.DISPATCH_IN_FLIGHT,
            TaskPhase.AFTER_ACTION,
        } and target[0] is TaskState.RECOVERY_REQUIRED and (
            target[1] == source[1]
            or (
                source[1] is TaskPhase.BEFORE_DISPATCH
                and target[1] is TaskPhase.IDEMPOTENCY_RESERVED
            )
        )
    elif current.reason_code == "TASK_BETWEEN_STEPS":
        legal = source == (TaskState.RUNNING, TaskPhase.AFTER_ACTION) and target == (
            TaskState.RUNNING,
            TaskPhase.BETWEEN_STEPS,
        )
    elif current.reason_code == "TASK_PAUSED":
        legal = source in {
            (TaskState.RUNNING, TaskPhase.BETWEEN_STEPS),
            (TaskState.RUNNING, TaskPhase.AFTER_ACTION),
        } and target == (TaskState.PAUSED, TaskPhase.BETWEEN_STEPS)
    elif current.reason_code == "TASK_COMPLETED":
        legal = terminal_target and source in {
            (TaskState.CREATED, TaskPhase.TASK_CREATED),
            (TaskState.RUNNING, TaskPhase.BETWEEN_STEPS),
            (TaskState.RUNNING, TaskPhase.AFTER_MODEL_CALL),
            (TaskState.RUNNING, TaskPhase.AFTER_ACTION),
            (TaskState.RUNNING, TaskPhase.BEFORE_DISPATCH),
        }
    elif current.reason_code == "TASK_PARTIAL":
        legal = terminal_target and source in {
            (TaskState.CREATED, TaskPhase.TASK_CREATED),
            (TaskState.RUNNING, TaskPhase.BETWEEN_STEPS),
            (TaskState.RUNNING, TaskPhase.BEFORE_MODEL_CALL),
            (TaskState.RUNNING, TaskPhase.AFTER_MODEL_CALL),
            (TaskState.RUNNING, TaskPhase.AFTER_ACTION),
            (TaskState.RUNNING, TaskPhase.BEFORE_DISPATCH),
        }
    elif current.reason_code in {
        "TASK_BLOCKED",
        "TASK_CANCELLED",
        "TASK_FAILED",
        "TASK_APPROVAL_DENIED",
        "TASK_ACTION_BLOCKED",
        "TASK_ACTION_CANCELLED",
        "TASK_IDEMPOTENCY_CONFLICT",
    }:
        legal = terminal_target and source[1] not in {
            TaskPhase.PROVENANCE_DISPATCH_RECORDED,
            TaskPhase.DISPATCH_IN_FLIGHT,
        }
    if not legal:
        raise TaskCheckpointCorruptionError(
            "Task transition edge is not allowed by the lifecycle graph."
        )

    step_delta = current.step_index - prior.step_index
    remaining_delta = current.remaining_steps - prior.remaining_steps
    attempt_delta = current.provider_attempts_used - prior.provider_attempts_used
    retry_delta = current.remaining_retry_budget - prior.remaining_retry_budget
    if current.reason_code == "TASK_STEP_RESERVED":
        if (step_delta, remaining_delta) != (1, -1):
            raise TaskCheckpointCorruptionError(
                "Task step budget was not reserved exactly once."
            )
    elif (step_delta, remaining_delta) != (0, 0):
        raise TaskCheckpointCorruptionError(
            "Task step budget changed outside its reservation edge."
        )
    if current.reason_code in {
        "TASK_MODEL_ATTEMPT_STARTED",
        "TASK_MODEL_CONTINUATION_STARTED",
    }:
        if (attempt_delta, retry_delta) != (1, -1):
            raise TaskCheckpointCorruptionError(
                "Task provider budget was not consumed exactly once."
            )
    elif (attempt_delta, retry_delta) != (0, 0):
        raise TaskCheckpointCorruptionError(
            "Task provider budget changed outside its attempt edge."
        )


def _derive_resume_classification(
    state: TaskState,
    phase: TaskPhase,
    approval_state: ApprovalState,
    reason_code: str = "",
) -> SafeResumeClassification:
    if reason_code == "TASK_IDEMPOTENCY_CONFLICT":
        return SafeResumeClassification.CONFLICT
    if state is TaskState.COMPLETED:
        return SafeResumeClassification.ALREADY_COMPLETED
    if state is TaskState.BLOCKED:
        return SafeResumeClassification.BLOCKED
    if state in {TaskState.CANCELLED, TaskState.FAILED, TaskState.PARTIAL}:
        return SafeResumeClassification.TERMINAL_NO_RESUME
    if state is TaskState.RECOVERY_REQUIRED:
        return SafeResumeClassification.UNKNOWN_OUTCOME
    if phase in {
        TaskPhase.PROVENANCE_DISPATCH_RECORDED,
        TaskPhase.DISPATCH_IN_FLIGHT,
    }:
        return SafeResumeClassification.UNKNOWN_OUTCOME
    if approval_state in {
        ApprovalState.WAITING,
        ApprovalState.GRANTED_IN_PROCESS,
        ApprovalState.FRESH_APPROVAL_REQUIRED,
    }:
        return SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL
    if state is TaskState.PAUSED:
        return SafeResumeClassification.MANUAL_REVIEW_REQUIRED
    if phase in {
        TaskPhase.IDEMPOTENCY_RESERVED,
        TaskPhase.AFTER_MODEL_CALL,
    }:
        return SafeResumeClassification.MANUAL_REVIEW_REQUIRED
    if state in {TaskState.CREATED, TaskState.RUNNING} and phase in {
        TaskPhase.TASK_CREATED,
        TaskPhase.BETWEEN_STEPS,
        TaskPhase.BEFORE_MODEL_CALL,
        TaskPhase.BEFORE_ACTION_POLICY,
        TaskPhase.BEFORE_DISPATCH,
        TaskPhase.AFTER_ACTION,
    }:
        return SafeResumeClassification.SAFE_TO_RESUME
    return SafeResumeClassification.MANUAL_REVIEW_REQUIRED


def _validate_checkpoint_semantics(
    state: TaskState,
    phase: TaskPhase,
    reason_code: str,
    approval_state: ApprovalState,
    safe_resume: SafeResumeClassification,
) -> None:
    allowed_reasons = TASK_STATE_PHASE_REASONS.get((state, phase))
    if allowed_reasons is None or reason_code not in allowed_reasons:
        raise TaskCheckpointCorruptionError(
            "Task state, phase, and reason code are contradictory."
        )
    approval_allowed: dict[TaskPhase, frozenset[ApprovalState]] = {
        TaskPhase.WAITING_FOR_APPROVAL: frozenset({ApprovalState.WAITING}),
        TaskPhase.BEFORE_DISPATCH: frozenset(
            {
                ApprovalState.NOT_REQUIRED,
                ApprovalState.GRANTED_IN_PROCESS,
                ApprovalState.FRESH_APPROVAL_REQUIRED,
            }
        ),
        TaskPhase.IDEMPOTENCY_RESERVED: frozenset(
            {ApprovalState.NOT_REQUIRED, ApprovalState.FRESH_APPROVAL_REQUIRED}
        ),
        TaskPhase.PROVENANCE_DISPATCH_RECORDED: frozenset(
            {ApprovalState.NOT_REQUIRED, ApprovalState.FRESH_APPROVAL_REQUIRED}
        ),
        TaskPhase.DISPATCH_IN_FLIGHT: frozenset(
            {ApprovalState.NOT_REQUIRED, ApprovalState.FRESH_APPROVAL_REQUIRED}
        ),
        TaskPhase.TERMINAL: frozenset(
            {
                ApprovalState.NOT_APPLICABLE,
                ApprovalState.DENIED,
                ApprovalState.NOT_REQUIRED,
                ApprovalState.FRESH_APPROVAL_REQUIRED,
            }
        ),
    }
    allowed_approval = approval_allowed.get(
        phase,
        frozenset({ApprovalState.NOT_APPLICABLE, ApprovalState.NOT_REQUIRED}),
    )
    if approval_state not in allowed_approval:
        raise TaskCheckpointCorruptionError(
            "Task phase and approval state are contradictory."
        )
    expected_resume = _derive_resume_classification(
        state, phase, approval_state, reason_code
    )
    if safe_resume is not expected_resume:
        raise TaskCheckpointCorruptionError(
            "Task safe-resume classification contradicts durable task truth."
        )


def _validate_action_metadata(checkpoint: "TaskCheckpoint") -> None:
    """Validate cross-module action truth without trusting arbitrary strings."""

    from tools.capability_policy import ACTION_POLICY_RULES, CapabilityClass
    from tools.idempotency import IdempotencyState
    from tools.validator import ALLOWED_ACTIONS

    action_fields = (
        checkpoint.current_action_id,
        checkpoint.current_idempotency_key,
        checkpoint.current_action_fingerprint,
        checkpoint.current_idempotency_state,
        checkpoint.current_action_name,
        checkpoint.current_capability_class,
        checkpoint.current_policy_reason_code,
    )
    action_phase = checkpoint.phase in {
        TaskPhase.BEFORE_ACTION_POLICY,
        TaskPhase.WAITING_FOR_APPROVAL,
        TaskPhase.BEFORE_DISPATCH,
        TaskPhase.IDEMPOTENCY_RESERVED,
        TaskPhase.PROVENANCE_DISPATCH_RECORDED,
        TaskPhase.DISPATCH_IN_FLIGHT,
        TaskPhase.AFTER_ACTION,
    }
    terminal_action = (
        checkpoint.phase is TaskPhase.TERMINAL
        and checkpoint.current_action_id is not None
    )
    if action_phase or terminal_action:
        if (
            checkpoint.current_action_id is None
            or checkpoint.current_idempotency_key is None
            or checkpoint.current_action_name is None
        ):
            raise TaskCheckpointCorruptionError(
                "Task action lifecycle metadata is incomplete."
            )
    elif any(value is not None for value in action_fields):
        raise TaskCheckpointCorruptionError(
            "Task checkpoint contains action metadata outside an action lifecycle."
        )

    if checkpoint.current_action_name is not None:
        if checkpoint.current_action_name not in ALLOWED_ACTIONS | {"unknown_action"}:
            raise TaskCheckpointCorruptionError("Task action name is not canonical.")
    if checkpoint.current_capability_class is not None:
        try:
            capability = CapabilityClass(checkpoint.current_capability_class)
        except ValueError as exc:
            raise TaskCheckpointCorruptionError(
                "Task capability class is not canonical."
            ) from exc
        rule = ACTION_POLICY_RULES.get(checkpoint.current_action_name or "")
        if rule is not None and capability is not rule.capability_class:
            raise TaskCheckpointCorruptionError(
                "Task capability class contradicts the canonical action policy."
            )
    if checkpoint.current_idempotency_state is not None:
        try:
            IdempotencyState(checkpoint.current_idempotency_state)
        except ValueError as exc:
            raise TaskCheckpointCorruptionError(
                "Task idempotency state is not canonical."
            ) from exc
        if (
            checkpoint.current_action_fingerprint is None
            or checkpoint.current_idempotency_key is None
        ):
            raise TaskCheckpointCorruptionError(
                "Task idempotency truth lacks its operation identity."
            )
    if checkpoint.phase in {
        TaskPhase.WAITING_FOR_APPROVAL,
        TaskPhase.BEFORE_DISPATCH,
        TaskPhase.IDEMPOTENCY_RESERVED,
        TaskPhase.PROVENANCE_DISPATCH_RECORDED,
        TaskPhase.DISPATCH_IN_FLIGHT,
        TaskPhase.AFTER_ACTION,
    } and (
        checkpoint.current_action_fingerprint is None
        or checkpoint.current_capability_class is None
        or checkpoint.current_policy_reason_code is None
    ):
        raise TaskCheckpointCorruptionError(
            "Task action policy metadata is incomplete."
        )
    if checkpoint.phase in {
        TaskPhase.IDEMPOTENCY_RESERVED,
        TaskPhase.PROVENANCE_DISPATCH_RECORDED,
        TaskPhase.DISPATCH_IN_FLIGHT,
        TaskPhase.AFTER_ACTION,
    } and checkpoint.current_idempotency_state is None:
        raise TaskCheckpointCorruptionError(
            "Task dispatch lifecycle lacks an idempotency state."
        )

    if terminal_action:
        if checkpoint.current_idempotency_state is None:
            if not (
                checkpoint.state is TaskState.BLOCKED
                and checkpoint.reason_code == "TASK_BLOCKED"
                and checkpoint.current_policy_reason_code
                in {
                    "ACTION_NOT_CLASSIFIED",
                    "SHELL_COMMAND_BLOCKED",
                    "ACTION_HANDLER_MISSING",
                }
            ):
                raise TaskCheckpointCorruptionError(
                    "Action-bearing terminal task lacks durable outcome truth."
                )
        else:
            if not _terminal_action_outcome_matches(
                checkpoint.state,
                checkpoint.reason_code,
                checkpoint.current_idempotency_state,
            ):
                raise TaskCheckpointCorruptionError(
                    "Task terminal state contradicts its idempotency outcome."
                )

    allowed_policy_reasons = {
        rule.reason_code for rule in ACTION_POLICY_RULES.values()
    } | {
        "ACTION_NOT_CLASSIFIED",
        "SHELL_COMMAND_BLOCKED",
        "SHELL_RUNTIME_CONFIRMATION_REQUIRED",
        "SHELL_RUNTIME_POLICY_ALLOWED",
        "MODEL_ESCALATION_REQUIRES_CONFIRMATION",
        "ACTION_HANDLER_MISSING",
    }
    if (
        checkpoint.current_policy_reason_code is not None
        and checkpoint.current_policy_reason_code not in allowed_policy_reasons
    ):
        raise TaskCheckpointCorruptionError(
            "Task capability-policy reason is not canonical."
        )

TASK_TRANSITION_FIELDS = frozenset(
    {
        "schema_version",
        "sequence",
        "timestamp_utc",
        "from_state",
        "from_phase",
        "to_state",
        "to_phase",
        "reason_code",
        "step_index",
        "remaining_steps",
        "provider_attempts_used",
        "remaining_retry_budget",
        "provenance_event_id",
        "prev_hash",
        "transition_hash",
    }
)

SAFE_CONTEXT_FIELDS = frozenset(
    {"request_hash", "request_length", "context_hashes"}
)

TASK_CHECKPOINT_FIELDS = frozenset(
    {
        "schema_version",
        "task_id",
        "project_scope",
        "checkpoint_version",
        "state",
        "phase",
        "created_at",
        "updated_at",
        "root_request_id",
        "root_trace_id",
        "latest_request_id",
        "latest_trace_id",
        "recovery_attempt_id",
        "step_index",
        "max_steps",
        "remaining_steps",
        "provider_attempts_used",
        "remaining_retry_budget",
        "current_model_call_id",
        "current_action_id",
        "current_idempotency_key",
        "current_action_fingerprint",
        "current_idempotency_state",
        "latest_provenance_event_id",
        "causal_provenance_event_id",
        "current_action_name",
        "current_capability_class",
        "current_policy_reason_code",
        "approval_state",
        "safe_resume_classification",
        "reason_code",
        "safe_context",
        "transitions",
        "checkpoint_hash",
    }
)


def new_task_id() -> str:
    return f"task_{uuid.uuid4().hex}"


def new_checkpoint_event_id() -> str:
    return f"provenance_event_{uuid.uuid4().hex}"


def checkpoint_prepare_event_id(checkpoint_event_id: str) -> str:
    _validate_identifier(checkpoint_event_id, "provenance_event")
    suffix = hashlib.sha256(
        f"AOIA_TASK_CHECKPOINT_PREPARE:{checkpoint_event_id}".encode("ascii")
    ).hexdigest()[:32]
    return f"provenance_event_{suffix}"


def checkpoint_abort_event_id(checkpoint_event_id: str) -> str:
    _validate_identifier(checkpoint_event_id, "provenance_event")
    suffix = hashlib.sha256(
        f"AOIA_TASK_CHECKPOINT_ABORT:{checkpoint_event_id}".encode("ascii")
    ).hexdigest()[:32]
    return f"provenance_event_{suffix}"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _hash_document(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _timestamp(clock: Callable[[], dt.datetime]) -> str:
    value = clock()
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise TaskCheckpointCorruptionError("Task checkpoint timestamp is invalid.")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TaskCheckpointCorruptionError("Task checkpoint timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        raise TaskCheckpointCorruptionError("Task checkpoint timestamp lacks a UTC offset.")
    return value


def _validate_identifier(value: object, prefix: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.startswith(f"{prefix}_"):
        raise TaskCheckpointCorruptionError(f"Task checkpoint {prefix} identity is invalid.")
    suffix = value[len(prefix) + 1 :]
    if len(suffix) != 32:
        raise TaskCheckpointCorruptionError(f"Task checkpoint {prefix} identity is invalid.")
    try:
        uuid.UUID(hex=suffix)
    except ValueError as exc:
        raise TaskCheckpointCorruptionError(
            f"Task checkpoint {prefix} identity is invalid."
        ) from exc
    return value


def _validate_budget(value: object, *, maximum: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
        raise TaskCheckpointCorruptionError(f"Task checkpoint {field} is invalid.")
    return value


def safe_context_metadata(
    request_text: str = "", context_hashes: tuple[str, ...] | list[str] = ()
) -> dict[str, Any]:
    if not isinstance(request_text, str):
        raise TypeError("task request text must be a string")
    hashes = list(context_hashes)
    if len(hashes) > MAX_SAFE_CONTEXT_HASHES or any(
        not isinstance(item, str) or not _HEX_DIGEST.fullmatch(item) for item in hashes
    ):
        raise ValueError("task safe context hashes are invalid")
    return {
        "request_hash": hashlib.sha256(request_text.encode("utf-8")).hexdigest(),
        "request_length": len(request_text),
        "context_hashes": hashes,
    }


def _validate_safe_context(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or frozenset(value) != SAFE_CONTEXT_FIELDS:
        raise TaskCheckpointCorruptionError("Task checkpoint safe context has an inexact schema.")
    request_hash = value.get("request_hash")
    if not isinstance(request_hash, str) or not _HEX_DIGEST.fullmatch(request_hash):
        raise TaskCheckpointCorruptionError("Task checkpoint request hash is invalid.")
    request_length = value.get("request_length")
    _validate_budget(request_length, maximum=10_000_000, field="request length")
    hashes = value.get("context_hashes")
    if not isinstance(hashes, list) or len(hashes) > MAX_SAFE_CONTEXT_HASHES:
        raise TaskCheckpointCorruptionError("Task checkpoint safe context is outside bounds.")
    if any(not isinstance(item, str) or not _HEX_DIGEST.fullmatch(item) for item in hashes):
        raise TaskCheckpointCorruptionError("Task checkpoint context hash is invalid.")
    return {"request_hash": request_hash, "request_length": request_length, "context_hashes": list(hashes)}


@dataclass(frozen=True)
class TaskTransition:
    schema_version: str
    sequence: int
    timestamp_utc: str
    from_state: str | None
    from_phase: str | None
    to_state: str
    to_phase: str
    reason_code: str
    step_index: int
    remaining_steps: int
    provider_attempts_used: int
    remaining_retry_budget: int
    provenance_event_id: str
    prev_hash: str
    transition_hash: str

    def to_payload(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def build(
        cls,
        *,
        sequence: int,
        timestamp_utc: str,
        from_state: TaskState | None,
        from_phase: TaskPhase | None,
        to_state: TaskState,
        to_phase: TaskPhase,
        reason_code: str,
        step_index: int,
        remaining_steps: int,
        provider_attempts_used: int,
        remaining_retry_budget: int,
        provenance_event_id: str,
        prev_hash: str,
    ) -> TaskTransition:
        payload = {
            "schema_version": TASK_TRANSITION_SCHEMA_VERSION,
            "sequence": sequence,
            "timestamp_utc": timestamp_utc,
            "from_state": from_state.value if from_state else None,
            "from_phase": from_phase.value if from_phase else None,
            "to_state": to_state.value,
            "to_phase": to_phase.value,
            "reason_code": reason_code,
            "step_index": step_index,
            "remaining_steps": remaining_steps,
            "provider_attempts_used": provider_attempts_used,
            "remaining_retry_budget": remaining_retry_budget,
            "provenance_event_id": provenance_event_id,
            "prev_hash": prev_hash,
        }
        return cls(**payload, transition_hash=_hash_document(payload))

    @classmethod
    def from_payload(cls, payload: object) -> TaskTransition:
        if not isinstance(payload, dict) or frozenset(payload) != TASK_TRANSITION_FIELDS:
            raise TaskCheckpointCorruptionError("Task transition has an inexact schema.")
        try:
            transition = cls(**payload)
        except TypeError as exc:
            raise TaskCheckpointCorruptionError("Task transition is malformed.") from exc
        transition.validate()
        return transition

    def validate(self) -> None:
        if self.schema_version != TASK_TRANSITION_SCHEMA_VERSION:
            raise TaskCheckpointSchemaError("Task transition schema is unsupported.")
        _validate_budget(self.sequence, maximum=MAX_TASK_TRANSITIONS, field="transition sequence")
        if self.sequence < 1:
            raise TaskCheckpointCorruptionError("Task transition sequence is invalid.")
        _validate_timestamp(self.timestamp_utc)
        if self.from_state is not None:
            TaskState(self.from_state)
        if self.from_phase is not None:
            TaskPhase(self.from_phase)
        TaskState(self.to_state)
        TaskPhase(self.to_phase)
        if self.reason_code not in TASK_REASON_CODES:
            raise TaskCheckpointCorruptionError("Task transition reason is not allowed.")
        _validate_budget(self.step_index, maximum=MAX_TASK_STEPS, field="step index")
        _validate_budget(self.remaining_steps, maximum=MAX_TASK_STEPS, field="remaining steps")
        _validate_budget(
            self.provider_attempts_used,
            maximum=MAX_PROVIDER_ATTEMPTS,
            field="provider attempts",
        )
        _validate_budget(
            self.remaining_retry_budget,
            maximum=MAX_PROVIDER_ATTEMPTS,
            field="remaining retry budget",
        )
        _validate_identifier(self.provenance_event_id, "provenance_event")
        if not _HEX_DIGEST.fullmatch(self.prev_hash) or not _HEX_DIGEST.fullmatch(
            self.transition_hash
        ):
            raise TaskCheckpointCorruptionError("Task transition hash is invalid.")
        without_hash = self.to_payload()
        without_hash.pop("transition_hash")
        if _hash_document(without_hash) != self.transition_hash:
            raise TaskCheckpointCorruptionError("Task transition hash does not verify.")


@dataclass(frozen=True)
class TaskCheckpoint:
    schema_version: str
    task_id: str
    project_scope: str
    checkpoint_version: int
    state: TaskState
    phase: TaskPhase
    created_at: str
    updated_at: str
    root_request_id: str
    root_trace_id: str
    latest_request_id: str
    latest_trace_id: str
    recovery_attempt_id: str | None
    step_index: int
    max_steps: int
    remaining_steps: int
    provider_attempts_used: int
    remaining_retry_budget: int
    current_model_call_id: str | None
    current_action_id: str | None
    current_idempotency_key: str | None
    current_action_fingerprint: str | None
    current_idempotency_state: str | None
    latest_provenance_event_id: str
    causal_provenance_event_id: str | None
    current_action_name: str | None
    current_capability_class: str | None
    current_policy_reason_code: str | None
    approval_state: ApprovalState
    safe_resume_classification: SafeResumeClassification
    reason_code: str
    safe_context: dict[str, Any]
    transitions: tuple[TaskTransition, ...]
    checkpoint_hash: str

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "project_scope": self.project_scope,
            "checkpoint_version": self.checkpoint_version,
            "state": self.state.value,
            "phase": self.phase.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "root_request_id": self.root_request_id,
            "root_trace_id": self.root_trace_id,
            "latest_request_id": self.latest_request_id,
            "latest_trace_id": self.latest_trace_id,
            "recovery_attempt_id": self.recovery_attempt_id,
            "step_index": self.step_index,
            "max_steps": self.max_steps,
            "remaining_steps": self.remaining_steps,
            "provider_attempts_used": self.provider_attempts_used,
            "remaining_retry_budget": self.remaining_retry_budget,
            "current_model_call_id": self.current_model_call_id,
            "current_action_id": self.current_action_id,
            "current_idempotency_key": self.current_idempotency_key,
            "current_action_fingerprint": self.current_action_fingerprint,
            "current_idempotency_state": self.current_idempotency_state,
            "latest_provenance_event_id": self.latest_provenance_event_id,
            "causal_provenance_event_id": self.causal_provenance_event_id,
            "current_action_name": self.current_action_name,
            "current_capability_class": self.current_capability_class,
            "current_policy_reason_code": self.current_policy_reason_code,
            "approval_state": self.approval_state.value,
            "safe_resume_classification": self.safe_resume_classification.value,
            "reason_code": self.reason_code,
            "safe_context": {
                **self.safe_context,
                "context_hashes": list(self.safe_context["context_hashes"]),
            },
            "transitions": [item.to_payload() for item in self.transitions],
        }
        if include_hash:
            payload["checkpoint_hash"] = self.checkpoint_hash
        return payload

    def with_hash(self) -> TaskCheckpoint:
        return replace(self, checkpoint_hash=_hash_document(self.to_payload(include_hash=False)))

    @classmethod
    def from_payload(cls, payload: object) -> TaskCheckpoint:
        if not isinstance(payload, dict):
            raise TaskCheckpointCorruptionError("Task checkpoint must be one JSON object.")
        schema = payload.get("schema_version")
        if schema != TASK_CHECKPOINT_SCHEMA_VERSION:
            raise TaskCheckpointSchemaError("Task checkpoint schema is unsupported.")
        if frozenset(payload) != TASK_CHECKPOINT_FIELDS:
            raise TaskCheckpointCorruptionError("Task checkpoint has an inexact schema.")
        try:
            checkpoint = cls(
                schema_version=schema,
                task_id=payload["task_id"],
                project_scope=payload["project_scope"],
                checkpoint_version=payload["checkpoint_version"],
                state=TaskState(payload["state"]),
                phase=TaskPhase(payload["phase"]),
                created_at=payload["created_at"],
                updated_at=payload["updated_at"],
                root_request_id=payload["root_request_id"],
                root_trace_id=payload["root_trace_id"],
                latest_request_id=payload["latest_request_id"],
                latest_trace_id=payload["latest_trace_id"],
                recovery_attempt_id=payload["recovery_attempt_id"],
                step_index=payload["step_index"],
                max_steps=payload["max_steps"],
                remaining_steps=payload["remaining_steps"],
                provider_attempts_used=payload["provider_attempts_used"],
                remaining_retry_budget=payload["remaining_retry_budget"],
                current_model_call_id=payload["current_model_call_id"],
                current_action_id=payload["current_action_id"],
                current_idempotency_key=payload["current_idempotency_key"],
                current_action_fingerprint=payload["current_action_fingerprint"],
                current_idempotency_state=payload["current_idempotency_state"],
                latest_provenance_event_id=payload["latest_provenance_event_id"],
                causal_provenance_event_id=payload["causal_provenance_event_id"],
                current_action_name=payload["current_action_name"],
                current_capability_class=payload["current_capability_class"],
                current_policy_reason_code=payload["current_policy_reason_code"],
                approval_state=ApprovalState(payload["approval_state"]),
                safe_resume_classification=SafeResumeClassification(
                    payload["safe_resume_classification"]
                ),
                reason_code=payload["reason_code"],
                safe_context=_validate_safe_context(payload["safe_context"]),
                transitions=tuple(
                    TaskTransition.from_payload(item) for item in payload["transitions"]
                ),
                checkpoint_hash=payload["checkpoint_hash"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, TaskCheckpointError):
                raise
            raise TaskCheckpointCorruptionError("Task checkpoint is malformed.") from exc
        checkpoint.validate()
        return checkpoint

    def validate(self) -> None:
        if self.schema_version != TASK_CHECKPOINT_SCHEMA_VERSION:
            raise TaskCheckpointSchemaError("Task checkpoint schema is unsupported.")
        _validate_identifier(self.task_id, "task")
        if not _HEX_DIGEST.fullmatch(self.project_scope):
            raise TaskCheckpointCorruptionError("Task project scope is invalid.")
        _validate_budget(
            self.checkpoint_version,
            maximum=MAX_TASK_TRANSITIONS,
            field="checkpoint version",
        )
        if self.checkpoint_version < 1:
            raise TaskCheckpointCorruptionError("Task checkpoint version is invalid.")
        _validate_timestamp(self.created_at)
        _validate_timestamp(self.updated_at)
        _validate_identifier(self.root_request_id, "request")
        _validate_identifier(self.root_trace_id, "trace")
        _validate_identifier(self.latest_request_id, "request")
        _validate_identifier(self.latest_trace_id, "trace")
        _validate_identifier(self.recovery_attempt_id, "recovery_attempt", optional=True)
        _validate_identifier(self.current_model_call_id, "model_call", optional=True)
        _validate_identifier(self.current_action_id, "action", optional=True)
        _validate_identifier(self.current_idempotency_key, "operation", optional=True)
        _validate_identifier(self.latest_provenance_event_id, "provenance_event")
        _validate_identifier(
            self.causal_provenance_event_id, "provenance_event", optional=True
        )
        for value, field in (
            (self.current_action_fingerprint, "action fingerprint"),
            (self.checkpoint_hash, "checkpoint hash"),
        ):
            if value is not None and (not isinstance(value, str) or not _HEX_DIGEST.fullmatch(value)):
                raise TaskCheckpointCorruptionError(f"Task {field} is invalid.")
        for value, field in (
            (self.current_action_name, "action name"),
            (self.current_capability_class, "capability class"),
            (self.current_policy_reason_code, "policy reason"),
            (self.current_idempotency_state, "idempotency state"),
        ):
            if value is not None and (
                not isinstance(value, str) or not value or len(value) > 160
            ):
                raise TaskCheckpointCorruptionError(f"Task {field} is invalid.")
        if self.reason_code not in TASK_REASON_CODES:
            raise TaskCheckpointCorruptionError("Task checkpoint reason is not allowed.")
        _validate_checkpoint_semantics(
            self.state,
            self.phase,
            self.reason_code,
            self.approval_state,
            self.safe_resume_classification,
        )
        _validate_action_metadata(self)
        _validate_budget(self.max_steps, maximum=MAX_TASK_STEPS, field="maximum steps")
        if self.max_steps < 1:
            raise TaskCheckpointCorruptionError("Task maximum steps is invalid.")
        _validate_budget(self.step_index, maximum=self.max_steps, field="step index")
        _validate_budget(self.remaining_steps, maximum=self.max_steps, field="remaining steps")
        if self.step_index + self.remaining_steps != self.max_steps:
            raise TaskCheckpointCorruptionError("Task step budget algebra is inconsistent.")
        _validate_budget(
            self.provider_attempts_used,
            maximum=MAX_PROVIDER_ATTEMPTS,
            field="provider attempts",
        )
        _validate_budget(
            self.remaining_retry_budget,
            maximum=MAX_PROVIDER_ATTEMPTS,
            field="remaining retry budget",
        )
        _validate_safe_context(self.safe_context)
        if len(self.transitions) != self.checkpoint_version or len(self.transitions) > MAX_TASK_TRANSITIONS:
            raise TaskCheckpointCorruptionError("Task transition history is inconsistent.")
        previous_hash = GENESIS_TRANSITION_HASH
        prior: TaskTransition | None = None
        for index, transition in enumerate(self.transitions, start=1):
            transition.validate()
            _validate_transition_edge(prior, transition)
            if transition.sequence != index or transition.prev_hash != previous_hash:
                raise TaskCheckpointCorruptionError("Task transition chain is invalid.")
            if prior is not None and (
                transition.from_state != prior.to_state
                or transition.from_phase != prior.to_phase
                or transition.step_index < prior.step_index
                or transition.remaining_steps > prior.remaining_steps
                or transition.provider_attempts_used < prior.provider_attempts_used
                or transition.remaining_retry_budget > prior.remaining_retry_budget
            ):
                raise TaskCheckpointCorruptionError("Task transition history is not monotonic.")
            previous_hash = transition.transition_hash
            prior = transition
        last = self.transitions[-1]
        if (
            last.to_state != self.state.value
            or last.to_phase != self.phase.value
            or last.sequence != self.checkpoint_version
            or last.timestamp_utc != self.updated_at
            or last.step_index != self.step_index
            or last.remaining_steps != self.remaining_steps
            or last.provider_attempts_used != self.provider_attempts_used
            or last.remaining_retry_budget != self.remaining_retry_budget
            or last.provenance_event_id != self.latest_provenance_event_id
            or last.reason_code != self.reason_code
        ):
            raise TaskCheckpointCorruptionError("Task checkpoint does not match its final transition.")
        if self.checkpoint_hash != _hash_document(self.to_payload(include_hash=False)):
            raise TaskCheckpointCorruptionError("Task checkpoint hash does not verify.")
        if len(_canonical_json(self.to_payload()).encode("utf-8")) > MAX_TASK_CHECKPOINT_BYTES:
            raise TaskCheckpointCorruptionError("Task checkpoint exceeds its bounded size.")
        if self.state in TERMINAL_TASK_STATES and self.phase is not TaskPhase.TERMINAL:
            raise TaskCheckpointCorruptionError("Terminal task checkpoint is resumable or non-terminal.")


def _project_scope(project_dir: Path) -> str:
    return hashlib.sha256(str(Path(project_dir).resolve()).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _OpenTaskResource:
    task_path: Path
    task_name: str
    root_descriptor: int
    task_descriptor: int
    task_identity: tuple[int, int]


class DurableTaskCheckpointStore:
    """Per-task atomic snapshots with an embedded hash-chained transition journal."""

    def __init__(
        self,
        state_dir: Path,
        *,
        project_dir: Path,
        provenance_store: Any | None = None,
        lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
        clock: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self.state_dir = Path(state_dir).resolve()
        self.project_dir = Path(project_dir).resolve()
        self.project_scope = _project_scope(self.project_dir)
        self.root_dir = self.state_dir / "tasks"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        metadata = self.root_dir.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise TaskCheckpointCorruptionError("Task checkpoint root is not a safe directory.")
        parent_descriptor: int | None = None
        try:
            parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            parent_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(
                os, "O_NOFOLLOW", 0
            )
            parent_descriptor = os.open(self.state_dir, parent_flags)
            os.fsync(parent_descriptor)
        except OSError as exc:
            raise TaskCheckpointError(
                "Task checkpoint root directory was not made durable.",
                target_path=self.state_dir,
            ) from exc
        finally:
            if parent_descriptor is not None:
                os.close(parent_descriptor)
        self._root_identity = (metadata.st_dev, metadata.st_ino)
        self.lock_timeout_seconds = validate_lock_timeout_seconds(lock_timeout_seconds)
        self._clock = clock or (lambda: dt.datetime.now(dt.UTC))
        if provenance_store is None:
            from tools.provenance import AppendOnlyProvenanceStore

            provenance_store = AppendOnlyProvenanceStore(
                self.state_dir, lock_timeout_seconds=self.lock_timeout_seconds
            )
        self.provenance_store = provenance_store
        self._directory_lock = threading.Lock()
        self._durable_task_directories: set[str] = set()
        self._reservation_lock = threading.Lock()
        self._active_step_reservations: dict[str, StepReservation] = {}
        self._active_model_continuations: dict[str, ModelContinuation] = {}

    def _open_verified_root(self) -> int:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            metadata = self.root_dir.lstat()
            descriptor = os.open(self.root_dir, flags)
        except OSError as exc:
            raise TaskCheckpointCorruptionError(
                "Task checkpoint root binding changed."
            ) from exc
        opened = os.fstat(descriptor)
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISDIR(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino) != self._root_identity
            or (opened.st_dev, opened.st_ino) != self._root_identity
        ):
            os.close(descriptor)
            raise TaskCheckpointCorruptionError(
                "Task checkpoint root binding changed."
            )
        return descriptor

    @contextmanager
    def _open_task_resource(
        self,
        task_id: str,
        *,
        create: bool = True,
    ) -> Iterator[_OpenTaskResource | None]:
        """Pin the verified tasks root and one no-follow task directory.

        Both descriptors stay open for the caller's complete read or atomic
        read/modify/write.  Checkpoint I/O is performed relative to the pinned
        task descriptor, while ``validate_identity`` below proves that the
        root path and root→task membership have not changed.
        """

        _validate_identifier(task_id, "task")
        digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
        path = self.root_dir / digest
        root_descriptor = self._open_verified_root()
        task_descriptor: int | None = None
        try:
            try:
                created_task_directory = False
                try:
                    metadata = os.stat(
                        digest,
                        dir_fd=root_descriptor,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    if not create:
                        yield None
                        return
                    try:
                        os.mkdir(digest, mode=0o700, dir_fd=root_descriptor)
                        created_task_directory = True
                    except FileExistsError:
                        pass
                    metadata = os.stat(
                        digest,
                        dir_fd=root_descriptor,
                        follow_symlinks=False,
                    )
                with self._directory_lock:
                    if (
                        created_task_directory
                        or digest not in self._durable_task_directories
                    ):
                        try:
                            # A fresh store syncs an existing leaf once too. This
                            # repairs the safe retry path after an earlier mkdir
                            # succeeded but its root fsync reported failure.
                            os.fsync(root_descriptor)
                        except OSError as exc:
                            raise TaskCheckpointError(
                                "Task checkpoint resource directory was not made durable.",
                                target_path=self.root_dir,
                            ) from exc
                        self._durable_task_directories.add(digest)
                if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(
                    metadata.st_mode
                ):
                    raise TaskCheckpointCorruptionError(
                        "Task checkpoint resource is not a safe directory.",
                        target_path=path,
                    )
                flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                flags |= getattr(os, "O_CLOEXEC", 0) | getattr(
                    os, "O_NOFOLLOW", 0
                )
                task_descriptor = os.open(
                    digest,
                    flags,
                    dir_fd=root_descriptor,
                )
                opened_task = os.fstat(task_descriptor)
                if (
                    not stat.S_ISDIR(opened_task.st_mode)
                    or (opened_task.st_dev, opened_task.st_ino)
                    != (metadata.st_dev, metadata.st_ino)
                ):
                    raise TaskCheckpointCorruptionError(
                        "Task checkpoint resource binding changed.",
                        target_path=path,
                    )
                resource = _OpenTaskResource(
                    task_path=path,
                    task_name=digest,
                    root_descriptor=root_descriptor,
                    task_descriptor=task_descriptor,
                    task_identity=(opened_task.st_dev, opened_task.st_ino),
                )
                self._validate_task_resource_identity(resource)
            except PersistenceError:
                raise
            except OSError as exc:
                raise TaskCheckpointCorruptionError(
                    "Task checkpoint resource binding changed.",
                    target_path=path,
                ) from exc
            yield resource
        finally:
            if task_descriptor is not None:
                os.close(task_descriptor)
            os.close(root_descriptor)

    def _validate_task_resource_identity(
        self,
        resource: _OpenTaskResource,
    ) -> None:
        """Fail closed if the visible root or pinned root→task edge changed."""

        try:
            opened_root = os.fstat(resource.root_descriptor)
            opened_task = os.fstat(resource.task_descriptor)
            visible_root = self.root_dir.lstat()
            child = os.stat(
                resource.task_name,
                dir_fd=resource.root_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise TaskCheckpointCorruptionError(
                "Task checkpoint directory binding changed."
            ) from exc
        if (
            stat.S_ISLNK(visible_root.st_mode)
            or not stat.S_ISDIR(visible_root.st_mode)
            or not stat.S_ISDIR(opened_root.st_mode)
            or not stat.S_ISDIR(child.st_mode)
            or not stat.S_ISDIR(opened_task.st_mode)
            or (visible_root.st_dev, visible_root.st_ino) != self._root_identity
            or (opened_root.st_dev, opened_root.st_ino) != self._root_identity
            or (child.st_dev, child.st_ino) != resource.task_identity
            or (opened_task.st_dev, opened_task.st_ino) != resource.task_identity
        ):
            raise TaskCheckpointCorruptionError(
                "Task checkpoint directory binding changed."
            )

    def task_dir(self, task_id: str) -> Path:
        with self._open_task_resource(task_id) as resource:
            return resource.task_path

    def checkpoint_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "checkpoint.json"

    def checkpoint_lock_path(self, task_id: str) -> Path:
        _validate_identifier(task_id, "task")
        digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
        path = self.root_dir / digest / "checkpoint.json"
        return state_resource_lock_path(self.state_dir, path)

    def load(self, task_id: str) -> TaskCheckpoint | None:
        checkpoint: TaskCheckpoint | None = None
        try:
            try:
                with self._open_task_resource(task_id) as resource:
                    path = resource.task_path / "checkpoint.json"
                    with InterProcessFileLock(
                        self.checkpoint_lock_path(task_id),
                        timeout_seconds=self.lock_timeout_seconds,
                    ):
                        payload = read_json_snapshot(
                            path,
                            reject_duplicate_keys=True,
                            maximum_bytes=MAX_TASK_CHECKPOINT_BYTES,
                            expected_parent_identity=resource.task_identity,
                            parent_directory_descriptor=resource.task_descriptor,
                            directory_identity_validator=lambda: (
                                self._validate_task_resource_identity(resource)
                            ),
                        )
            except StateCorruptionError as exc:
                raise TaskCheckpointCorruptionError(
                    "Task checkpoint JSON is corrupt."
                ) from exc
            if payload is None:
                return None
            checkpoint = TaskCheckpoint.from_payload(payload)
            if (
                checkpoint.task_id != task_id
                or checkpoint.project_scope != self.project_scope
            ):
                raise TaskCheckpointCorruptionError(
                    "Task checkpoint resource identity is inconsistent."
                )
            self.ensure_checkpoint_event(checkpoint)
            if checkpoint.phase is TaskPhase.AFTER_ACTION or (
                checkpoint.state in TERMINAL_TASK_STATES
                and checkpoint.current_action_id is not None
                and checkpoint.current_idempotency_state is not None
            ):
                self._validate_terminal_causal_event(
                    task_state=checkpoint.state,
                    task_reason_code=checkpoint.reason_code,
                    task_id=checkpoint.task_id,
                    action_id=checkpoint.current_action_id,
                    operation_key=checkpoint.current_idempotency_key,
                    action_fingerprint=checkpoint.current_action_fingerprint,
                    idempotency_state=checkpoint.current_idempotency_state,
                    event_id=checkpoint.causal_provenance_event_id,
                )
            return checkpoint
        except PersistenceError as exc:
            identity: dict[str, object] = {"task_id": task_id}
            if checkpoint is not None:
                identity.update(
                    {
                        "request_id": checkpoint.latest_request_id,
                        "trace_id": checkpoint.latest_trace_id,
                        "action_id": checkpoint.current_action_id,
                        "model_call_id": checkpoint.current_model_call_id,
                    }
                )
            raise exc.attach_correlation(identity)

    def load_snapshot_unanchored(self, task_id: str) -> TaskCheckpoint | None:
        """Read one pinned, fully validated snapshot without provenance repair.

        Recovery discovery uses this read-only boundary so inspecting a crash
        gap cannot create a task directory or auto-append a missing checkpoint
        event.  The returned snapshot is not, by itself, resume authority.
        """

        try:
            with self._open_task_resource(task_id, create=False) as resource:
                if resource is None:
                    return None
                path = resource.task_path / "checkpoint.json"
                with InterProcessFileLock(
                    self.checkpoint_lock_path(task_id),
                    timeout_seconds=self.lock_timeout_seconds,
                ):
                    payload = read_json_snapshot(
                        path,
                        reject_duplicate_keys=True,
                        maximum_bytes=MAX_TASK_CHECKPOINT_BYTES,
                        expected_parent_identity=resource.task_identity,
                        parent_directory_descriptor=resource.task_descriptor,
                        directory_identity_validator=lambda: (
                            self._validate_task_resource_identity(resource)
                        ),
                    )
        except StateCorruptionError as exc:
            raise TaskCheckpointCorruptionError(
                "Task checkpoint JSON is corrupt."
            ) from exc
        if payload is None:
            return None
        checkpoint = TaskCheckpoint.from_payload(payload)
        if (
            checkpoint.task_id != task_id
            or checkpoint.project_scope != self.project_scope
        ):
            raise TaskCheckpointCorruptionError(
                "Task checkpoint resource identity is inconsistent."
            )
        return checkpoint

    def load_snapshot_resource_unanchored(
        self, resource_id: str
    ) -> TaskCheckpoint | None:
        """Read a discovered task resource through pinned directory FDs."""

        if not isinstance(resource_id, str) or not _HEX_DIGEST.fullmatch(resource_id):
            raise TaskCheckpointCorruptionError(
                "Task checkpoint discovery resource identity is invalid."
            )
        root_descriptor = self._open_verified_root()
        task_descriptor: int | None = None
        try:
            try:
                metadata = os.stat(
                    resource_id,
                    dir_fd=root_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return None
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise TaskCheckpointCorruptionError(
                    "Task checkpoint discovery resource is unsafe."
                )
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            task_descriptor = os.open(
                resource_id, flags, dir_fd=root_descriptor
            )
            opened = os.fstat(task_descriptor)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or (opened.st_dev, opened.st_ino)
                != (metadata.st_dev, metadata.st_ino)
            ):
                raise TaskCheckpointCorruptionError(
                    "Task checkpoint discovery binding changed."
                )
            resource = _OpenTaskResource(
                task_path=self.root_dir / resource_id,
                task_name=resource_id,
                root_descriptor=root_descriptor,
                task_descriptor=task_descriptor,
                task_identity=(opened.st_dev, opened.st_ino),
            )
            self._validate_task_resource_identity(resource)
            path = resource.task_path / "checkpoint.json"
            with InterProcessFileLock(
                state_resource_lock_path(self.state_dir, path),
                timeout_seconds=self.lock_timeout_seconds,
            ):
                payload = read_json_snapshot(
                    path,
                    reject_duplicate_keys=True,
                    maximum_bytes=MAX_TASK_CHECKPOINT_BYTES,
                    expected_parent_identity=resource.task_identity,
                    parent_directory_descriptor=resource.task_descriptor,
                    directory_identity_validator=lambda: (
                        self._validate_task_resource_identity(resource)
                    ),
                )
        except StateCorruptionError as exc:
            raise TaskCheckpointCorruptionError(
                "Task checkpoint JSON is corrupt."
            ) from exc
        finally:
            if task_descriptor is not None:
                os.close(task_descriptor)
            os.close(root_descriptor)
        if payload is None:
            return None
        checkpoint = TaskCheckpoint.from_payload(payload)
        if (
            hashlib.sha256(checkpoint.task_id.encode("utf-8")).hexdigest()
            != resource_id
            or checkpoint.project_scope != self.project_scope
        ):
            raise TaskCheckpointCorruptionError(
                "Task checkpoint discovery identity is inconsistent."
            )
        return checkpoint

    def create_task(
        self,
        trace_context: Any,
        *,
        max_steps: int,
        retry_budget: int,
        safe_context: Mapping[str, Any] | None = None,
        reason_code: str = "TASK_CREATED",
    ) -> TaskCheckpoint:
        task_id = trace_context.task_id
        _validate_identifier(task_id, "task")
        _validate_budget(max_steps, maximum=MAX_TASK_STEPS, field="maximum steps")
        _validate_budget(retry_budget, maximum=MAX_PROVIDER_ATTEMPTS, field="retry budget")
        if max_steps < 1:
            raise ValueError("task max_steps must be positive")
        context = _validate_safe_context(dict(safe_context or safe_context_metadata()))
        now = _timestamp(self._clock)
        event_id = new_checkpoint_event_id()
        transition = TaskTransition.build(
            sequence=1,
            timestamp_utc=now,
            from_state=None,
            from_phase=None,
            to_state=TaskState.CREATED,
            to_phase=TaskPhase.TASK_CREATED,
            reason_code=reason_code,
            step_index=0,
            remaining_steps=max_steps,
            provider_attempts_used=0,
            remaining_retry_budget=retry_budget,
            provenance_event_id=event_id,
            prev_hash=GENESIS_TRANSITION_HASH,
        )
        candidate = TaskCheckpoint(
            schema_version=TASK_CHECKPOINT_SCHEMA_VERSION,
            task_id=task_id,
            project_scope=self.project_scope,
            checkpoint_version=1,
            state=TaskState.CREATED,
            phase=TaskPhase.TASK_CREATED,
            created_at=now,
            updated_at=now,
            root_request_id=trace_context.request_id,
            root_trace_id=trace_context.trace_id,
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            recovery_attempt_id=None,
            step_index=0,
            max_steps=max_steps,
            remaining_steps=max_steps,
            provider_attempts_used=0,
            remaining_retry_budget=retry_budget,
            current_model_call_id=None,
            current_action_id=None,
            current_idempotency_key=None,
            current_action_fingerprint=None,
            current_idempotency_state=None,
            latest_provenance_event_id=event_id,
            causal_provenance_event_id=None,
            current_action_name=None,
            current_capability_class=None,
            current_policy_reason_code=None,
            approval_state=ApprovalState.NOT_APPLICABLE,
            safe_resume_classification=SafeResumeClassification.SAFE_TO_RESUME,
            reason_code=reason_code,
            safe_context=context,
            transitions=(transition,),
            checkpoint_hash="0" * 64,
        ).with_hash()
        candidate.validate()
        def update(current: object | None) -> tuple[object, TaskCheckpoint]:
            if current is not None:
                existing = TaskCheckpoint.from_payload(current)
                if (
                    existing.task_id != task_id
                    or existing.project_scope != self.project_scope
                ):
                    raise TaskCheckpointCorruptionError(
                        "Task checkpoint resource identity is inconsistent."
                    )
                return existing.to_payload(), existing
            self._stage_checkpoint_event(candidate, parent_checkpoint_hash=GENESIS_TRANSITION_HASH)
            return candidate.to_payload(), candidate

        try:
            with self._open_task_resource(task_id) as resource:
                path = resource.task_path / "checkpoint.json"
                checkpoint = locked_update_json(
                    path,
                    update,
                    lock_path=self.checkpoint_lock_path(task_id),
                    lock_timeout_seconds=self.lock_timeout_seconds,
                    sort_keys=True,
                    trailing_newline=True,
                    reject_duplicate_keys=True,
                    maximum_bytes=MAX_TASK_CHECKPOINT_BYTES,
                    expected_parent_identity=resource.task_identity,
                    parent_directory_descriptor=resource.task_descriptor,
                    directory_identity_validator=lambda: (
                        self._validate_task_resource_identity(resource)
                    ),
                )
        except Exception as error:
            self._abort_preparation_if_snapshot_absent(candidate)
            if isinstance(error, PersistenceError):
                identity_fields = getattr(trace_context, "identity_fields", None)
                identity = (
                    identity_fields()
                    if callable(identity_fields)
                    else {"task_id": task_id}
                )
                raise error.attach_correlation(identity)
            raise
        try:
            self.ensure_checkpoint_event(checkpoint)
        except PersistenceError as exc:
            identity_fields = getattr(trace_context, "identity_fields", None)
            identity = (
                identity_fields()
                if callable(identity_fields)
                else {"task_id": task_id}
            )
            raise exc.attach_correlation(identity)
        return checkpoint

    def ensure_for_action(self, action_context: Any) -> TaskCheckpoint:
        checkpoint = self.load(action_context.task_id)
        if checkpoint is not None:
            return checkpoint
        return self.create_task(
            action_context,
            max_steps=1,
            retry_budget=0,
            safe_context=safe_context_metadata(),
            reason_code="STANDALONE_ACTION_TASK_CREATED",
        )

    def transition(
        self,
        task_id: str,
        *,
        expected_version: int,
        state: TaskState,
        phase: TaskPhase,
        reason_code: str,
        latest_request_id: str | None = None,
        latest_trace_id: str | None = None,
        recovery_attempt_id: str | None = None,
        step_index: int | None = None,
        remaining_steps: int | None = None,
        provider_attempts_used: int | None = None,
        remaining_retry_budget: int | None = None,
        current_model_call_id: str | None = None,
        current_action_id: str | None = None,
        current_idempotency_key: str | None = None,
        current_action_fingerprint: str | None = None,
        current_idempotency_state: str | None = None,
        causal_provenance_event_id: str | None = None,
        current_action_name: str | None = None,
        current_capability_class: str | None = None,
        current_policy_reason_code: str | None = None,
        approval_state: ApprovalState | None = None,
        safe_resume_classification: SafeResumeClassification | None = None,
        safe_context: Mapping[str, Any] | None = None,
        model_continuation: ModelContinuation | None = None,
    ) -> TaskCheckpoint:
        if reason_code not in TASK_REASON_CODES:
            raise ValueError("task checkpoint reason code is not allowed")
        existing = self.load(task_id)
        if existing is None:
            raise TaskCheckpointConflictError("Task checkpoint does not exist.")
        if reason_code == "TASK_MODEL_CONTINUATION_STARTED":
            self._consume_model_continuation(
                model_continuation,
                checkpoint=existing,
            )
        elif model_continuation is not None:
            raise TaskStepReservationError(
                "Model continuation proof is invalid for this transition."
            )
        now = _timestamp(self._clock)
        event_id = new_checkpoint_event_id()
        def update(current: object | None) -> tuple[object, TaskCheckpoint]:
            if current is None:
                raise TaskCheckpointConflictError("Task checkpoint disappeared during transition.")
            old = TaskCheckpoint.from_payload(current)
            if old.task_id != task_id or old.project_scope != self.project_scope:
                raise TaskCheckpointCorruptionError("Task checkpoint resource identity is inconsistent.")
            if old.checkpoint_version != expected_version:
                raise TaskCheckpointConflictError("Task checkpoint version changed concurrently.")
            if old.state in TERMINAL_TASK_STATES:
                raise TaskTransitionError("Terminal task cannot transition back into execution.")
            if state not in LEGAL_STATE_TRANSITIONS.get(old.state, frozenset()):
                raise TaskTransitionError("Task state transition is not legal.")
            next_step = old.step_index if step_index is None else step_index
            next_remaining = old.remaining_steps if remaining_steps is None else remaining_steps
            next_attempts = (
                old.provider_attempts_used
                if provider_attempts_used is None
                else provider_attempts_used
            )
            next_retry = (
                old.remaining_retry_budget
                if remaining_retry_budget is None
                else remaining_retry_budget
            )
            if (
                next_step < old.step_index
                or next_remaining > old.remaining_steps
                or next_attempts < old.provider_attempts_used
                or next_retry > old.remaining_retry_budget
                or next_step + next_remaining != old.max_steps
            ):
                raise TaskBudgetError("Task transition would reset or corrupt a budget.")
            aggregate_terminal = (
                state is TaskState.PARTIAL
                and phase is TaskPhase.TERMINAL
                and reason_code == "TASK_PARTIAL"
            )
            if aggregate_terminal and old.current_action_id is not None:
                if (
                    old.state is not TaskState.RUNNING
                    or old.phase is not TaskPhase.AFTER_ACTION
                    or old.reason_code != "TASK_ACTION_COMPLETED"
                ):
                    raise TaskTransitionError(
                        "Aggregate task terminalization cannot discard an "
                        "unfinished action lifecycle."
                    )
                # PARTIAL is a task-level aggregate, not the outcome of its
                # final action.  Revalidate that completed action's exact P0.7
                # and P0.8 proof inside the locked CAS before atomically
                # clearing its live action context in the terminal snapshot.
                self._validate_terminal_causal_event(
                    task_state=old.state,
                    task_reason_code=old.reason_code,
                    task_id=task_id,
                    action_id=old.current_action_id,
                    operation_key=old.current_idempotency_key,
                    action_fingerprint=old.current_action_fingerprint,
                    idempotency_state=old.current_idempotency_state,
                    event_id=old.causal_provenance_event_id,
                )
            clear_action_context = (
                (
                    state in {TaskState.RUNNING, TaskState.PAUSED}
                    and phase is TaskPhase.BETWEEN_STEPS
                )
                or reason_code == "TASK_STEP_RESERVED"
                or aggregate_terminal
            )
            next_approval = (
                ApprovalState.NOT_APPLICABLE
                if clear_action_context
                else (
                    approval_state
                    if approval_state is not None
                    else old.approval_state
                )
            )
            next_causal_event_id = (
                causal_provenance_event_id
                if causal_provenance_event_id is not None
                else old.causal_provenance_event_id
            )
            _ = safe_resume_classification
            if state in TERMINAL_TASK_STATES:
                if phase is not TaskPhase.TERMINAL:
                    raise TaskTransitionError("Terminal task state requires terminal phase.")
            next_resume = _derive_resume_classification(
                state, phase, next_approval, reason_code
            )
            try:
                _validate_checkpoint_semantics(
                    state,
                    phase,
                    reason_code,
                    next_approval,
                    next_resume,
                )
            except TaskCheckpointCorruptionError as exc:
                raise TaskTransitionError(str(exc)) from exc
            next_action_id = None if clear_action_context else (
                current_action_id
                if current_action_id is not None
                else old.current_action_id
            )
            next_operation_key = None if clear_action_context else (
                current_idempotency_key
                if current_idempotency_key is not None
                else old.current_idempotency_key
            )
            next_fingerprint = None if clear_action_context else (
                current_action_fingerprint
                if current_action_fingerprint is not None
                else old.current_action_fingerprint
            )
            next_idempotency_state = None if clear_action_context else (
                current_idempotency_state
                if current_idempotency_state is not None
                else old.current_idempotency_state
            )
            if reason_code == "TASK_ACTION_COMPLETED" or (
                state in TERMINAL_TASK_STATES
                and next_action_id is not None
                and next_idempotency_state is not None
            ):
                self._validate_terminal_causal_event(
                    task_state=state,
                    task_reason_code=reason_code,
                    task_id=task_id,
                    action_id=next_action_id,
                    operation_key=next_operation_key,
                    action_fingerprint=next_fingerprint,
                    idempotency_state=next_idempotency_state,
                    event_id=next_causal_event_id,
                )
            transition = TaskTransition.build(
                sequence=old.checkpoint_version + 1,
                timestamp_utc=now,
                from_state=old.state,
                from_phase=old.phase,
                to_state=state,
                to_phase=phase,
                reason_code=reason_code,
                step_index=next_step,
                remaining_steps=next_remaining,
                provider_attempts_used=next_attempts,
                remaining_retry_budget=next_retry,
                provenance_event_id=event_id,
                prev_hash=old.transitions[-1].transition_hash,
            )
            try:
                _validate_transition_edge(old.transitions[-1], transition)
            except TaskCheckpointCorruptionError as exc:
                raise TaskTransitionError(str(exc)) from exc
            checkpoint = replace(
                old,
                checkpoint_version=old.checkpoint_version + 1,
                state=state,
                phase=phase,
                updated_at=now,
                latest_request_id=latest_request_id or old.latest_request_id,
                latest_trace_id=latest_trace_id or old.latest_trace_id,
                recovery_attempt_id=(
                    recovery_attempt_id
                    if recovery_attempt_id is not None
                    else old.recovery_attempt_id
                ),
                step_index=next_step,
                remaining_steps=next_remaining,
                provider_attempts_used=next_attempts,
                remaining_retry_budget=next_retry,
                current_model_call_id=(None if clear_action_context else (
                    current_model_call_id
                    if current_model_call_id is not None
                    else old.current_model_call_id
                )),
                current_action_id=next_action_id,
                current_idempotency_key=next_operation_key,
                current_action_fingerprint=next_fingerprint,
                current_idempotency_state=next_idempotency_state,
                latest_provenance_event_id=event_id,
                causal_provenance_event_id=(
                    None if clear_action_context else next_causal_event_id
                ),
                current_action_name=(None if clear_action_context else (
                    current_action_name
                    if current_action_name is not None
                    else old.current_action_name
                )),
                current_capability_class=(None if clear_action_context else (
                    current_capability_class
                    if current_capability_class is not None
                    else old.current_capability_class
                )),
                current_policy_reason_code=(None if clear_action_context else (
                    current_policy_reason_code
                    if current_policy_reason_code is not None
                    else old.current_policy_reason_code
                )),
                approval_state=(
                    next_approval
                ),
                safe_resume_classification=next_resume,
                reason_code=reason_code,
                safe_context=(
                    _validate_safe_context(dict(safe_context))
                    if safe_context is not None
                    else old.safe_context
                ),
                transitions=(*old.transitions, transition),
                checkpoint_hash="0" * 64,
            ).with_hash()
            checkpoint.validate()
            self._stage_checkpoint_event(
                checkpoint,
                parent_checkpoint_hash=old.checkpoint_hash,
            )
            return checkpoint.to_payload(), checkpoint

        candidate_holder: list[TaskCheckpoint] = []

        original_update = update

        def capturing_update(current: object | None) -> tuple[object, TaskCheckpoint]:
            payload, candidate = original_update(current)
            candidate_holder.append(candidate)
            return payload, candidate

        try:
            with self._open_task_resource(task_id) as resource:
                path = resource.task_path / "checkpoint.json"
                checkpoint = locked_update_json(
                    path,
                    capturing_update,
                    lock_path=self.checkpoint_lock_path(task_id),
                    lock_timeout_seconds=self.lock_timeout_seconds,
                    sort_keys=True,
                    trailing_newline=True,
                    reject_duplicate_keys=True,
                    maximum_bytes=MAX_TASK_CHECKPOINT_BYTES,
                    expected_parent_identity=resource.task_identity,
                    parent_directory_descriptor=resource.task_descriptor,
                    directory_identity_validator=lambda: (
                        self._validate_task_resource_identity(resource)
                    ),
                )
        except Exception as error:
            if candidate_holder:
                self._abort_preparation_if_snapshot_absent(candidate_holder[-1])
            if isinstance(error, PersistenceError):
                raise error.attach_correlation(
                    {
                        "task_id": task_id,
                        "request_id": latest_request_id
                        or existing.latest_request_id,
                        "trace_id": latest_trace_id or existing.latest_trace_id,
                        "action_id": current_action_id
                        or existing.current_action_id,
                        "model_call_id": current_model_call_id
                        or existing.current_model_call_id,
                    }
                )
            raise
        try:
            self.ensure_checkpoint_event(checkpoint)
        except PersistenceError as exc:
            raise exc.attach_correlation(
                {
                    "task_id": task_id,
                    "request_id": checkpoint.latest_request_id,
                    "trace_id": checkpoint.latest_trace_id,
                    "action_id": checkpoint.current_action_id,
                    "model_call_id": checkpoint.current_model_call_id,
                }
            )
        return checkpoint

    def reserve_step(self, task_id: str) -> StepReservation:
        checkpoint = self.load(task_id)
        if checkpoint is None:
            raise TaskCheckpointConflictError("Task checkpoint does not exist.")
        if checkpoint.remaining_steps <= 0:
            raise TaskBudgetError("Task step budget is exhausted.")
        reserved = self.transition(
            task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_MODEL_CALL,
            reason_code="TASK_STEP_RESERVED",
            step_index=checkpoint.step_index + 1,
            remaining_steps=checkpoint.remaining_steps - 1,
            safe_resume_classification=SafeResumeClassification.SAFE_TO_RESUME,
        )

        nonce = uuid.uuid4().hex
        token = StepReservation(
            task_id=reserved.task_id,
            step_index=reserved.step_index,
            checkpoint_version=reserved.checkpoint_version,
            checkpoint_hash=reserved.checkpoint_hash,
            checkpoint_event_id=reserved.latest_provenance_event_id,
            _nonce=nonce,
        )
        with self._reservation_lock:
            self._active_step_reservations[nonce] = token
        return token

    def remint_step_reservation_for_recovery(
        self,
        task_id: str,
        *,
        recovery_token: object,
    ) -> StepReservation:
        """Recreate only the process-local proof for an already-debited step.

        This edge never changes ``step_index`` or either remaining budget.  The
        caller must first validate the exact active recovery token through
        ``TaskRecoveryService.classify_under_claim``; the token is then bound
        into the new durable checkpoint and into the one-shot reservation.
        """

        # Import lazily to avoid a module cycle during checkpoint bootstrap.
        from runtime.task_recovery import RecoveryExecutionToken

        if (
            not isinstance(recovery_token, RecoveryExecutionToken)
            or recovery_token.task_id != task_id
            or recovery_token._owner_process_id != os.getpid()
            or recovery_token._owner_thread_id != threading.get_ident()
        ):
            raise TaskStepReservationError(
                "Recovery step remint requires its exact active owner token."
            )
        recovery_token._validate_active_owner(task_id)
        checkpoint = self.load(task_id)
        if checkpoint is None:
            raise TaskCheckpointConflictError("Task checkpoint does not exist.")
        failed_model_boundary = checkpoint.reason_code in {
            "TASK_MODEL_ATTEMPT_STARTED",
            "TASK_MODEL_CONTINUATION_STARTED",
        }
        if failed_model_boundary:
            recovery_token._validate_failed_model_remint(checkpoint)
        if (
            checkpoint.state is not TaskState.RUNNING
            or checkpoint.phase is not TaskPhase.BEFORE_MODEL_CALL
            or checkpoint.reason_code
            not in {
                "TASK_STEP_RESERVED",
                "TASK_BEFORE_MODEL_CALL",
                "TASK_MODEL_CALL_FAILED",
                "TASK_MODEL_ATTEMPT_STARTED",
                "TASK_MODEL_CONTINUATION_STARTED",
                "TASK_RECOVERY_STEP_REMINTED",
            }
            or checkpoint.checkpoint_hash != recovery_token.checkpoint_hash
            or checkpoint.recovery_attempt_id
            == recovery_token.recovery_attempt_id
        ):
            raise TaskStepReservationError(
                "Task is not at an exact safe already-debited model boundary."
            )
        reminted = self.transition(
            task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_MODEL_CALL,
            reason_code="TASK_RECOVERY_STEP_REMINTED",
            latest_request_id=recovery_token.request_id,
            latest_trace_id=recovery_token.trace_id,
            recovery_attempt_id=recovery_token.recovery_attempt_id,
            step_index=checkpoint.step_index,
            remaining_steps=checkpoint.remaining_steps,
            provider_attempts_used=checkpoint.provider_attempts_used,
            remaining_retry_budget=checkpoint.remaining_retry_budget,
            approval_state=checkpoint.approval_state,
        )
        nonce = uuid.uuid4().hex
        token = StepReservation(
            task_id=reminted.task_id,
            step_index=reminted.step_index,
            checkpoint_version=reminted.checkpoint_version,
            checkpoint_hash=reminted.checkpoint_hash,
            checkpoint_event_id=reminted.latest_provenance_event_id,
            _nonce=nonce,
            recovery_attempt_id=recovery_token.recovery_attempt_id,
        )
        with self._reservation_lock:
            self._active_step_reservations[nonce] = token
        return token

    def validate_step_reservation(
        self,
        token: StepReservation,
        *,
        task_id: str,
    ) -> TaskCheckpoint:
        if not isinstance(token, StepReservation) or token.task_id != task_id:
            raise TaskStepReservationError("Task step reservation is not authoritative.")
        with self._reservation_lock:
            authoritative = self._active_step_reservations.get(token._nonce)
        if authoritative != token:
            raise TaskStepReservationError("Task step reservation is absent or already consumed.")
        checkpoint = self.load(task_id)
        if (
            checkpoint is None
            or checkpoint.step_index != token.step_index
            or checkpoint.checkpoint_version < token.checkpoint_version
            or token.checkpoint_hash == ""
            or token.checkpoint_event_id == ""
            or (
                token.recovery_attempt_id is not None
                and checkpoint.recovery_attempt_id
                != token.recovery_attempt_id
            )
        ):
            raise TaskStepReservationError("Task step reservation no longer matches durable state.")
        return checkpoint

    def consume_step_reservation(
        self,
        token: StepReservation,
        *,
        task_id: str,
    ) -> TaskCheckpoint:
        checkpoint = self.validate_step_reservation(token, task_id=task_id)
        with self._reservation_lock:
            authoritative = self._active_step_reservations.get(token._nonce)
            if authoritative != token:
                raise TaskStepReservationError("Task step reservation was already consumed.")
            del self._active_step_reservations[token._nonce]
        return checkpoint

    def close_step_reservation(self, token: StepReservation) -> None:
        if not isinstance(token, StepReservation):
            raise TaskStepReservationError("Task step reservation is not authoritative.")
        with self._reservation_lock:
            authoritative = self._active_step_reservations.get(token._nonce)
            if authoritative != token:
                raise TaskStepReservationError("Task step reservation is absent.")
            del self._active_step_reservations[token._nonce]

    def authorize_model_continuation(
        self,
        step_reservation: StepReservation,
        *,
        completed_model_call: Any,
    ) -> ModelContinuation:
        """Bind one live-process planner→worker continuation to durable truth."""

        checkpoint = self.validate_step_reservation(
            step_reservation,
            task_id=completed_model_call.task_id,
        )
        if (
            checkpoint.phase is not TaskPhase.AFTER_MODEL_CALL
            or checkpoint.state is not TaskState.RUNNING
            or checkpoint.current_model_call_id
            != completed_model_call.model_call_id
        ):
            raise TaskStepReservationError(
                "Model continuation lacks a matching completed model checkpoint."
            )
        nonce = uuid.uuid4().hex
        proof = ModelContinuation(
            task_id=checkpoint.task_id,
            prior_model_call_id=completed_model_call.model_call_id,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            checkpoint_event_id=checkpoint.latest_provenance_event_id,
            _nonce=nonce,
        )
        with self._reservation_lock:
            self._active_model_continuations[nonce] = proof
        return proof

    def _consume_model_continuation(
        self,
        proof: ModelContinuation | None,
        *,
        checkpoint: TaskCheckpoint,
    ) -> None:
        if not isinstance(proof, ModelContinuation):
            raise TaskStepReservationError(
                "Model continuation requires a runtime-owned proof."
            )
        with self._reservation_lock:
            authoritative = self._active_model_continuations.get(proof._nonce)
            if authoritative != proof:
                raise TaskStepReservationError(
                    "Model continuation proof is absent or already consumed."
                )
            if (
                proof.task_id != checkpoint.task_id
                or proof.prior_model_call_id != checkpoint.current_model_call_id
                or proof.checkpoint_version != checkpoint.checkpoint_version
                or proof.checkpoint_hash != checkpoint.checkpoint_hash
                or proof.checkpoint_event_id
                != checkpoint.latest_provenance_event_id
            ):
                raise TaskStepReservationError(
                    "Model continuation proof does not match durable state."
                )
            del self._active_model_continuations[proof._nonce]

    def close_model_continuation(self, proof: ModelContinuation) -> None:
        """Discard one unused live-process continuation proof exactly once."""

        if not isinstance(proof, ModelContinuation):
            raise TaskStepReservationError(
                "Model continuation proof is not authoritative."
            )
        with self._reservation_lock:
            authoritative = self._active_model_continuations.get(proof._nonce)
            if authoritative != proof:
                raise TaskStepReservationError(
                    "Model continuation proof is absent or already consumed."
                )
            del self._active_model_continuations[proof._nonce]

    def consume_provider_attempt(
        self,
        model_call: Any,
        *,
        step_reservation: StepReservation,
        model_continuation: ModelContinuation | None = None,
    ) -> TaskCheckpoint:
        self.validate_step_reservation(
            step_reservation,
            task_id=model_call.task_id,
        )
        checkpoint = self.load(model_call.task_id)
        if checkpoint is None:
            raise TaskCheckpointConflictError("Task checkpoint does not exist.")
        if checkpoint.remaining_retry_budget <= 0:
            raise TaskBudgetError("Task provider-attempt budget is exhausted.")
        continuing = checkpoint.phase is TaskPhase.AFTER_MODEL_CALL
        if continuing and model_continuation is None:
            raise TaskStepReservationError(
                "A second model call requires a live continuation proof."
            )
        if not continuing and model_continuation is not None:
            raise TaskStepReservationError(
                "Model continuation proof is not valid at this checkpoint."
            )
        return self.transition(
            model_call.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_MODEL_CALL,
            reason_code=(
                "TASK_MODEL_CONTINUATION_STARTED"
                if continuing
                else "TASK_MODEL_ATTEMPT_STARTED"
            ),
            provider_attempts_used=checkpoint.provider_attempts_used + 1,
            remaining_retry_budget=checkpoint.remaining_retry_budget - 1,
            current_model_call_id=model_call.model_call_id,
            safe_resume_classification=SafeResumeClassification.MANUAL_REVIEW_REQUIRED,
            model_continuation=model_continuation,
        )

    def ensure_checkpoint_event(self, checkpoint: TaskCheckpoint) -> None:
        event = self._checkpoint_event(checkpoint)
        expected_document = event.event_document()
        records = self.provenance_store.read_runtime_all()
        for record in records:
            if record.get("event_id") != event.event_id:
                continue
            actual = {field: record[field] for field in expected_document}
            if actual != expected_document:
                raise TaskCheckpointCorruptionError(
                    "Task checkpoint provenance identity conflicts with durable content."
                )
            return

        prepared_record = next(
            (
                record
                for record in records
                if record.get("event_type") == "TASK_CHECKPOINT_PREPARED"
                and record.get("checkpoint_event_id") == event.event_id
            ),
            None,
        )
        if prepared_record is None:
            raise TaskCheckpointCorruptionError(
                "Task checkpoint lacks a matching durable preparation anchor."
            )
        expected_prepare = self._checkpoint_prepared_event(
            checkpoint,
            parent_checkpoint_hash=str(prepared_record.get("checkpoint_parent_hash")),
        ).event_document()
        actual_prepare = {field: prepared_record[field] for field in expected_prepare}
        if actual_prepare != expected_prepare:
            raise TaskCheckpointCorruptionError(
                "Task checkpoint preparation does not match the snapshot."
            )
        self.provenance_store.append_terminal(event)

    def _checkpoint_event(self, checkpoint: TaskCheckpoint) -> Any:
        RuntimeProvenanceEvent = self._runtime_provenance_event_type()

        return RuntimeProvenanceEvent(
            event_id=checkpoint.latest_provenance_event_id,
            timestamp_utc=checkpoint.updated_at,
            event_type="TASK_CHECKPOINTED",
            task_id=checkpoint.task_id,
            request_id=checkpoint.latest_request_id,
            trace_id=checkpoint.latest_trace_id,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            success=True,
            reason_code="TASK_CHECKPOINTED",
        )

    def _checkpoint_prepared_event(
        self,
        checkpoint: TaskCheckpoint,
        *,
        parent_checkpoint_hash: str,
    ) -> Any:
        RuntimeProvenanceEvent = self._runtime_provenance_event_type()

        return RuntimeProvenanceEvent(
            event_id=checkpoint_prepare_event_id(
                checkpoint.latest_provenance_event_id
            ),
            timestamp_utc=checkpoint.updated_at,
            event_type="TASK_CHECKPOINT_PREPARED",
            task_id=checkpoint.task_id,
            request_id=checkpoint.latest_request_id,
            trace_id=checkpoint.latest_trace_id,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            checkpoint_parent_hash=parent_checkpoint_hash,
            checkpoint_event_id=checkpoint.latest_provenance_event_id,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            reason_code="TASK_CHECKPOINT_PREPARED",
        )

    def _checkpoint_aborted_event(
        self,
        checkpoint: TaskCheckpoint,
        *,
        parent_checkpoint_hash: str,
    ) -> Any:
        RuntimeProvenanceEvent = self._runtime_provenance_event_type()

        return RuntimeProvenanceEvent(
            event_id=checkpoint_abort_event_id(
                checkpoint.latest_provenance_event_id
            ),
            timestamp_utc=checkpoint.updated_at,
            event_type="TASK_CHECKPOINT_ABORTED",
            task_id=checkpoint.task_id,
            request_id=checkpoint.latest_request_id,
            trace_id=checkpoint.latest_trace_id,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            checkpoint_parent_hash=parent_checkpoint_hash,
            checkpoint_event_id=checkpoint.latest_provenance_event_id,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            success=False,
            reason_code="TASK_CHECKPOINT_ABORTED",
        )

    def _runtime_provenance_event_type(self) -> type[Any]:
        """Use the event class from the store's canonical module namespace."""

        module = importlib.import_module(type(self.provenance_store).__module__)
        event_type = getattr(module, "RuntimeProvenanceEvent", None)
        if not isinstance(event_type, type):
            raise TaskCheckpointError(
                "Task checkpoint provenance store has no runtime event type."
            )
        return event_type

    def _stage_checkpoint_event(
        self,
        checkpoint: TaskCheckpoint,
        *,
        parent_checkpoint_hash: str,
    ) -> None:
        self.provenance_store.append_runtime_event(
            self._checkpoint_prepared_event(
                checkpoint,
                parent_checkpoint_hash=parent_checkpoint_hash,
            )
        )

    def _abort_preparation_if_snapshot_absent(
        self,
        checkpoint: TaskCheckpoint,
    ) -> None:
        """Abort a handled failed CAS only when the candidate is not current."""

        records = self.provenance_store.read_runtime_all()
        prepared = next(
            (
                item
                for item in records
                if item.get("event_type") == "TASK_CHECKPOINT_PREPARED"
                and item.get("checkpoint_event_id")
                == checkpoint.latest_provenance_event_id
            ),
            None,
        )
        if prepared is None:
            return
        if any(
            item.get("event_id") == checkpoint.latest_provenance_event_id
            for item in records
        ):
            return
        try:
            with self._open_task_resource(checkpoint.task_id) as resource:
                current = read_json_snapshot(
                    resource.task_path / "checkpoint.json",
                    reject_duplicate_keys=True,
                    maximum_bytes=MAX_TASK_CHECKPOINT_BYTES,
                    expected_parent_identity=resource.task_identity,
                    parent_directory_descriptor=resource.task_descriptor,
                    directory_identity_validator=lambda: (
                        self._validate_task_resource_identity(resource)
                    ),
                )
        except PersistenceError:
            return
        if current == checkpoint.to_payload():
            return
        parent_hash = str(prepared.get("checkpoint_parent_hash"))
        self.provenance_store.append_runtime_event(
            self._checkpoint_aborted_event(
                checkpoint,
                parent_checkpoint_hash=parent_hash,
            )
        )

    def _validate_terminal_causal_event(
        self,
        *,
        task_state: TaskState,
        task_reason_code: str,
        task_id: str,
        action_id: str | None,
        operation_key: str | None,
        action_fingerprint: str | None,
        idempotency_state: str | None,
        event_id: str | None,
    ) -> None:
        if None in {
            action_id,
            operation_key,
            action_fingerprint,
            idempotency_state,
            event_id,
        }:
            raise TaskTransitionError(
                "Completed action checkpoint lacks terminal causal evidence."
            )
        if task_state in TERMINAL_TASK_STATES and not (
            _terminal_action_outcome_matches(
                task_state,
                task_reason_code,
                str(idempotency_state),
            )
        ):
            raise TaskTransitionError(
                "Task terminal state contradicts its persisted action outcome."
            )
        event_types_by_outcome = {
            "SUCCEEDED": {
                "ACTION_DISPATCH_SUCCEEDED",
                "IDEMPOTENCY_REPLAYED",
                "RECOVERY_TERMINAL_RECONCILED",
            },
            "FAILED_BEFORE_DISPATCH": {
                "ACTION_DISPATCH_FAILED",
                "IDEMPOTENCY_REPLAYED",
                "RECOVERY_TERMINAL_RECONCILED",
            },
            "FAILED_REPORTED": {
                "ACTION_DISPATCH_FAILED",
                "IDEMPOTENCY_REPLAYED",
                "RECOVERY_TERMINAL_RECONCILED",
            },
            "BLOCKED": {
                "ACTION_DISPATCH_BLOCKED",
                "IDEMPOTENCY_REPLAYED",
                "RECOVERY_TERMINAL_RECONCILED",
            },
            "CANCELLED": {
                "ACTION_DISPATCH_CANCELLED",
                "IDEMPOTENCY_REPLAYED",
                "RECOVERY_TERMINAL_RECONCILED",
            },
            "CONFLICT": {"IDEMPOTENCY_CONFLICT"},
        }
        allowed_types = event_types_by_outcome.get(str(idempotency_state), set())
        match = next(
            (
                record
                for record in self.provenance_store.read_runtime_all()
                if record.get("event_id") == event_id
            ),
            None,
        )
        if (
            match is None
            or match.get("event_type") not in allowed_types
            or match.get("task_id") != task_id
            or match.get("action_id") != action_id
            or match.get("operation_key") != operation_key
            or match.get("action_fingerprint") != action_fingerprint
            or match.get("idempotency_state") != idempotency_state
        ):
            raise TaskTransitionError(
                "Completed action checkpoint lacks matching P0.7/P0.8 terminal proof."
            )
