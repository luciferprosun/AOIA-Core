from __future__ import annotations

import datetime as dt
import hashlib
import importlib
import json
import os
import re
import stat
import sys
import threading
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Protocol, runtime_checkable


if __name__ == "runtime.task_recovery":
    sys.modules.setdefault("task_recovery", sys.modules[__name__])
elif __name__ == "task_recovery":
    sys.modules.setdefault("runtime.task_recovery", sys.modules[__name__])

from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    InterProcessFileLock,
    PersistenceError,
    StateCorruptionError,
    StateLockTimeoutError,
    locked_update_json,
    read_json_snapshot,
    validate_lock_timeout_seconds,
)
from runtime.task_checkpoints import (
    ApprovalState,
    DurableTaskCheckpointStore,
    StepReservation,
    TaskCheckpoint,
    TaskCheckpointCorruptionError,
    TaskCheckpointSchemaError,
    TaskStepReservationError,
    TaskPhase,
    TaskState,
    TERMINAL_TASK_STATES,
)
from runtime.trace_context import TaskContext, TraceContext, strip_untrusted_identity_fields
from runtime.outcomes import (
    NZOutcome,
    NZOutcomeStatus,
    NZReasonCode,
    outcome_from_task_state,
)


RECOVERY_CLAIM_SCHEMA_VERSION = "AOIA_RECOVERY_CLAIM_1A"
RECOVERY_DECISION_SCHEMA_VERSION = "AOIA_RECOVERY_DECISION_1A"
MAX_RECOVERY_DISCOVERY_BATCH = 128
MAX_RECOVERY_DISCOVERY_LIMIT = 256
MAX_RECOVERY_CLAIM_BYTES = 16 * 1024
MAX_RECOVERY_IDEMPOTENCY_SCAN_RECORDS = 1024
MAX_TRUSTED_RESUME_INPUTS = 128
MAX_TRUSTED_ACTION_BYTES = 64 * 1024
MIN_RECOVERY_LEASE_SECONDS = 1.0
MAX_RECOVERY_LEASE_SECONDS = 300.0
DEFAULT_RECOVERY_LEASE_SECONDS = 30.0

_HEX = re.compile(r"^[0-9a-f]{64}$")
_UUID_IDS = {
    "task_id": "task",
    "owner_id": "recovery_owner",
    "recovery_attempt_id": "recovery_attempt",
}


class RecoveryError(PersistenceError):
    reason_code = "RECOVERY_ERROR"


class RecoveryClaimConflictError(RecoveryError):
    reason_code = "RECOVERY_CLAIM_CONFLICT"


class RecoveryInProgressError(RecoveryError):
    reason_code = "RECOVERY_IN_PROGRESS"


class RecoveryFencedError(RecoveryError):
    reason_code = "RECOVERY_GENERATION_FENCED"


class RecoveryInputError(RecoveryError):
    reason_code = "RECOVERY_TRUSTED_INPUT_INVALID"


class RecoveryCorruptionError(RecoveryError):
    reason_code = "RECOVERY_STATE_CORRUPT"


class RecoveryClassification(str, Enum):
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


class RecoveryDirective(str, Enum):
    NO_ACTION = "NO_ACTION"
    RESUME_MODEL = "RESUME_MODEL"
    REVALIDATE_ACTION = "REVALIDATE_ACTION"
    RECONCILE_CHECKPOINT = "RECONCILE_CHECKPOINT"
    RECONCILE_TERMINAL_PROVENANCE = "RECONCILE_TERMINAL_PROVENANCE"
    REQUIRE_FRESH_APPROVAL = "REQUIRE_FRESH_APPROVAL"
    REQUIRE_OPERATOR_ACK = "REQUIRE_OPERATOR_ACK"
    CANCEL_TASK = "CANCEL_TASK"


# Compatibility spelling for the design-stage API.
RecoveryAction = RecoveryDirective


RECOVERY_CLASSIFICATION_DIRECTIVES = {
    RecoveryClassification.SAFE_TO_RESUME: frozenset(
        {
            RecoveryDirective.RESUME_MODEL,
            RecoveryDirective.REVALIDATE_ACTION,
            RecoveryDirective.RECONCILE_CHECKPOINT,
            RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
            RecoveryDirective.CANCEL_TASK,
        }
    ),
    RecoveryClassification.WAITING_FOR_FRESH_APPROVAL: frozenset(
        {RecoveryDirective.REQUIRE_FRESH_APPROVAL, RecoveryDirective.CANCEL_TASK}
    ),
    RecoveryClassification.ALREADY_COMPLETED: frozenset({RecoveryDirective.NO_ACTION}),
    RecoveryClassification.TERMINAL_NO_RESUME: frozenset({RecoveryDirective.NO_ACTION}),
    RecoveryClassification.BLOCKED: frozenset({RecoveryDirective.NO_ACTION}),
    RecoveryClassification.CONFLICT: frozenset(
        {RecoveryDirective.NO_ACTION, RecoveryDirective.REQUIRE_OPERATOR_ACK}
    ),
    RecoveryClassification.CORRUPT_CHECKPOINT: frozenset(
        {RecoveryDirective.REQUIRE_OPERATOR_ACK}
    ),
    RecoveryClassification.UNSUPPORTED_SCHEMA: frozenset(
        {RecoveryDirective.REQUIRE_OPERATOR_ACK}
    ),
    RecoveryClassification.UNKNOWN_OUTCOME: frozenset(
        {RecoveryDirective.REQUIRE_OPERATOR_ACK, RecoveryDirective.CANCEL_TASK}
    ),
    RecoveryClassification.MANUAL_REVIEW_REQUIRED: frozenset(
        {
            RecoveryDirective.REQUIRE_OPERATOR_ACK,
            RecoveryDirective.CANCEL_TASK,
            RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
            RecoveryDirective.RECONCILE_CHECKPOINT,
        }
    ),
    RecoveryClassification.RECOVERY_IN_PROGRESS: frozenset(
        {RecoveryDirective.NO_ACTION}
    ),
}
RECOVERY_REASON_CODES = frozenset(
    {
        "RECOVERY_CHECKPOINT_MISSING", "RECOVERY_CHECKPOINT_SCHEMA_UNSUPPORTED",
        "RECOVERY_CHECKPOINT_CORRUPT", "RECOVERY_ACTIVE_CLAIM",
        "RECOVERY_IDEMPOTENCY_CORRUPT",
        "RECOVERY_IDEMPOTENCY_STATE_MISSING",
        "RECOVERY_CHECKPOINT_ROLLBACK_DETECTED",
        "RECOVERY_CLAIM_LOCK_BINDING_CORRUPT",
        "RECOVERY_CHECKPOINT_EVENT_PENDING", "RECOVERY_CHECKPOINT_UNANCHORED",
        "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT", "RECOVERY_TASK_ALREADY_COMPLETED",
        "RECOVERY_TASK_CONFLICT", "RECOVERY_TASK_BLOCKED", "RECOVERY_TASK_TERMINAL",
        "RECOVERY_ACTION_OUTCOME_UNKNOWN", "RECOVERY_TERMINAL_PROVENANCE_PENDING",
        "RECOVERY_RESERVED_ACTION_REQUIRES_REVALIDATION",
        "RECOVERY_RESERVED_ACTION_FRESH_APPROVAL_REQUIRED",
        "RECOVERY_FRESH_APPROVAL_REQUIRED", "RECOVERY_STEP_BUDGET_EXHAUSTED",
        "RECOVERY_PROVIDER_BUDGET_EXHAUSTED", "RECOVERY_MODEL_OUTCOME_UNKNOWN",
        "RECOVERY_MODEL_OUTPUT_NOT_DURABLE",
        "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
        "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE", "RECOVERY_TRUSTED_REQUEST_REQUIRED",
        "RECOVERY_MANUAL_REVIEW_REQUIRED", "RECOVERY_DISCOVERY_RESOURCE_INVALID",
        "RECOVERY_DISCOVERY_CHECKPOINT_INVALID", "RECOVERY_RECONCILIATION_COMPLETED",
        "RECOVERY_PROVENANCE_CORRUPT", "RECOVERY_TASK_CHECKPOINT_PENDING",
        "RECOVERY_TERMINAL_WITHOUT_DISPATCH_START",
        "RECOVERY_RESERVED_CHECKPOINT_PENDING",
        "RECOVERY_RESERVED_PROVENANCE_PENDING",
        "RECOVERY_PRE_DISPATCH_ACTION_REQUIRES_REVALIDATION",
        "RECOVERY_SAFE_TASK_CANCEL_REQUESTED",
        "RECOVERY_SAFE_ACTION_CANCEL_REQUESTED",
        "RECOVERY_WAITING_ACTION_CANCEL_REQUESTED",
    }
)
_RECOVERY_REASON_SEMANTICS: dict[
    str, tuple[RecoveryClassification, RecoveryDirective, bool, bool]
] = {
    "RECOVERY_CHECKPOINT_MISSING": (
        RecoveryClassification.CORRUPT_CHECKPOINT, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_CHECKPOINT_SCHEMA_UNSUPPORTED": (
        RecoveryClassification.UNSUPPORTED_SCHEMA, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_CHECKPOINT_CORRUPT": (
        RecoveryClassification.CORRUPT_CHECKPOINT, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_IDEMPOTENCY_CORRUPT": (
        RecoveryClassification.CORRUPT_CHECKPOINT,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_IDEMPOTENCY_STATE_MISSING": (
        RecoveryClassification.CORRUPT_CHECKPOINT,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_CHECKPOINT_ROLLBACK_DETECTED": (
        RecoveryClassification.CORRUPT_CHECKPOINT,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_PROVENANCE_CORRUPT": (
        RecoveryClassification.CORRUPT_CHECKPOINT, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_ACTIVE_CLAIM": (
        RecoveryClassification.RECOVERY_IN_PROGRESS, RecoveryDirective.NO_ACTION, False, False
    ),
    "RECOVERY_CLAIM_LOCK_BINDING_CORRUPT": (
        RecoveryClassification.CORRUPT_CHECKPOINT,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_CHECKPOINT_EVENT_PENDING": (
        RecoveryClassification.SAFE_TO_RESUME, RecoveryDirective.RECONCILE_CHECKPOINT, False, False
    ),
    "RECOVERY_CHECKPOINT_UNANCHORED": (
        RecoveryClassification.CORRUPT_CHECKPOINT, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT": (
        RecoveryClassification.CORRUPT_CHECKPOINT, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_TASK_ALREADY_COMPLETED": (
        RecoveryClassification.ALREADY_COMPLETED, RecoveryDirective.NO_ACTION, False, False
    ),
    "RECOVERY_TASK_CONFLICT": (
        RecoveryClassification.CONFLICT, RecoveryDirective.NO_ACTION, False, False
    ),
    "RECOVERY_TASK_BLOCKED": (
        RecoveryClassification.BLOCKED, RecoveryDirective.NO_ACTION, False, False
    ),
    "RECOVERY_TASK_TERMINAL": (
        RecoveryClassification.TERMINAL_NO_RESUME, RecoveryDirective.NO_ACTION, False, False
    ),
    "RECOVERY_ACTION_OUTCOME_UNKNOWN": (
        RecoveryClassification.UNKNOWN_OUTCOME, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_TERMINAL_PROVENANCE_PENDING": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE, False, False
    ),
    "RECOVERY_TASK_CHECKPOINT_PENDING": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.RECONCILE_CHECKPOINT, False, False
    ),
    "RECOVERY_TERMINAL_WITHOUT_DISPATCH_START": (
        RecoveryClassification.CORRUPT_CHECKPOINT,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_RESERVED_CHECKPOINT_PENDING": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.RECONCILE_CHECKPOINT, False, False
    ),
    "RECOVERY_RESERVED_PROVENANCE_PENDING": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_PRE_DISPATCH_ACTION_REQUIRES_REVALIDATION": (
        RecoveryClassification.SAFE_TO_RESUME,
        RecoveryDirective.REVALIDATE_ACTION, True, False
    ),
    "RECOVERY_RESERVED_ACTION_REQUIRES_REVALIDATION": (
        RecoveryClassification.SAFE_TO_RESUME, RecoveryDirective.REVALIDATE_ACTION, True, False
    ),
    "RECOVERY_RESERVED_ACTION_FRESH_APPROVAL_REQUIRED": (
        RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
        RecoveryDirective.REQUIRE_FRESH_APPROVAL, True, True
    ),
    "RECOVERY_FRESH_APPROVAL_REQUIRED": (
        RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
        RecoveryDirective.REQUIRE_FRESH_APPROVAL, True, True
    ),
    "RECOVERY_STEP_BUDGET_EXHAUSTED": (
        RecoveryClassification.BLOCKED, RecoveryDirective.NO_ACTION, False, False
    ),
    "RECOVERY_PROVIDER_BUDGET_EXHAUSTED": (
        RecoveryClassification.BLOCKED, RecoveryDirective.NO_ACTION, False, False
    ),
    "RECOVERY_MODEL_OUTCOME_UNKNOWN": (
        RecoveryClassification.UNKNOWN_OUTCOME, RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_MODEL_OUTPUT_NOT_DURABLE": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_REQUEST_EXECUTION_UNCERTAIN": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_TRUSTED_REQUEST_REQUIRED": (
        RecoveryClassification.SAFE_TO_RESUME, RecoveryDirective.RESUME_MODEL, True, False
    ),
    "RECOVERY_MANUAL_REVIEW_REQUIRED": (
        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_DISCOVERY_RESOURCE_INVALID": (
        RecoveryClassification.CORRUPT_CHECKPOINT,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_DISCOVERY_CHECKPOINT_INVALID": (
        RecoveryClassification.CORRUPT_CHECKPOINT,
        RecoveryDirective.REQUIRE_OPERATOR_ACK, False, False
    ),
    "RECOVERY_RECONCILIATION_COMPLETED": (
        RecoveryClassification.SAFE_TO_RESUME,
        RecoveryDirective.RECONCILE_CHECKPOINT, False, False
    ),
    "RECOVERY_SAFE_TASK_CANCEL_REQUESTED": (
        RecoveryClassification.SAFE_TO_RESUME,
        RecoveryDirective.CANCEL_TASK, False, False
    ),
    "RECOVERY_SAFE_ACTION_CANCEL_REQUESTED": (
        RecoveryClassification.SAFE_TO_RESUME,
        RecoveryDirective.CANCEL_TASK, False, False
    ),
    "RECOVERY_WAITING_ACTION_CANCEL_REQUESTED": (
        RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
        RecoveryDirective.CANCEL_TASK, False, False
    ),
}


class RecoveryClaimStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class RecoveryPurpose(str, Enum):
    LIVE = "LIVE"
    RECOVERY = "RECOVERY"
    RECONCILIATION = "RECONCILIATION"
    OPERATOR = "OPERATOR"


RECOVERY_DECISION_FIELDS = frozenset(
    {
        "schema_version", "task_id", "resource_id", "project_scope",
        "checkpoint_version", "checkpoint_hash", "task_state", "task_phase",
        "classification", "directive", "reason_code", "idempotency_state",
        "provenance_event_id", "requires_trusted_input",
        "requires_fresh_approval", "provider_dispatch_allowed",
        "handler_dispatch_allowed",
    }
)


@dataclass(frozen=True)
class RecoveryDecision:
    schema_version: str
    task_id: str | None
    resource_id: str
    project_scope: str
    checkpoint_version: int | None
    checkpoint_hash: str | None
    task_state: str | None
    task_phase: str | None
    classification: RecoveryClassification
    directive: RecoveryDirective
    reason_code: str
    idempotency_state: str | None = None
    provenance_event_id: str | None = None
    requires_trusted_input: bool = False
    requires_fresh_approval: bool = False
    provider_dispatch_allowed: bool = False
    handler_dispatch_allowed: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != RECOVERY_DECISION_SCHEMA_VERSION:
            raise RecoveryCorruptionError("Recovery decision schema is unsupported.")
        if not _HEX.fullmatch(self.resource_id) or not _HEX.fullmatch(self.project_scope):
            raise RecoveryCorruptionError("Recovery decision resource identity is invalid.")
        if self.task_id is not None:
            _validate_runtime_id(self.task_id, "task")
        if self.checkpoint_hash is not None and not _HEX.fullmatch(self.checkpoint_hash):
            raise RecoveryCorruptionError("Recovery decision checkpoint hash is invalid.")
        for value in (
            self.requires_trusted_input,
            self.requires_fresh_approval,
            self.provider_dispatch_allowed,
            self.handler_dispatch_allowed,
        ):
            if not isinstance(value, bool):
                raise RecoveryCorruptionError("Recovery decision boolean is invalid.")
        if self.provider_dispatch_allowed or self.handler_dispatch_allowed:
            raise RecoveryCorruptionError(
                "Classification alone cannot authorize external dispatch."
            )
        if self.directive not in RECOVERY_CLASSIFICATION_DIRECTIVES[self.classification]:
            raise RecoveryCorruptionError(
                "Recovery directive contradicts its classification."
            )
        if self.reason_code not in RECOVERY_REASON_CODES:
            raise RecoveryCorruptionError("Recovery decision reason is not canonical.")
        expected = _RECOVERY_REASON_SEMANTICS[self.reason_code]
        actual = (
            self.classification,
            self.directive,
            self.requires_trusted_input,
            self.requires_fresh_approval,
        )
        if actual != expected:
            raise RecoveryCorruptionError(
                "Recovery decision fields contradict its fixed reason semantics."
            )

    def to_payload(self) -> dict[str, Any]:
        payload = {
            **self.__dict__,
            "classification": self.classification.value,
            "directive": self.directive.value,
        }
        if frozenset(payload) != RECOVERY_DECISION_FIELDS:
            raise RecoveryCorruptionError("Recovery decision schema is inexact.")
        return payload


@dataclass(frozen=True)
class RecoveryDiscoveryResult:
    decisions: tuple[RecoveryDecision, ...]
    scanned_count: int
    pending_count: int
    malformed_count: int
    truncated: bool
    degraded: bool = False
    reason_code: str = "RECOVERY_DISCOVERY_COMPLETE"


class RecoveryOperationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


@dataclass(frozen=True)
class RecoveryOperationResult:
    """Bounded operator receipt; dispatcher content is deliberately omitted."""

    task_id: str
    recovery_attempt_id: str
    request_id: str
    trace_id: str
    classification: RecoveryClassification
    directive: RecoveryDirective
    status: RecoveryOperationStatus
    success: bool
    task_state: str
    task_phase: str
    checkpoint_version: int
    checkpoint_hash: str

    def __post_init__(self) -> None:
        _validate_runtime_id(self.task_id, "task")
        _validate_runtime_id(self.recovery_attempt_id, "recovery_attempt")
        _validate_runtime_id(self.request_id, "request")
        _validate_runtime_id(self.trace_id, "trace")
        if not _HEX.fullmatch(self.checkpoint_hash):
            raise RecoveryCorruptionError("Recovery receipt checkpoint hash is invalid.")
        if isinstance(self.checkpoint_version, bool) or self.checkpoint_version < 1:
            raise RecoveryCorruptionError("Recovery receipt checkpoint version is invalid.")
        if self.success is not (self.status is RecoveryOperationStatus.COMPLETED):
            raise RecoveryCorruptionError("Recovery receipt status contradicts success.")

    @property
    def outcome(self) -> NZOutcome:
        """Noncanonical projection of task truth; controller success is unchanged."""

        if self.classification is RecoveryClassification.CONFLICT:
            return NZOutcome.build(
                NZOutcomeStatus.CONFLICT,
                "RECOVERY_CONFLICT",
                request_id=self.request_id,
                trace_id=self.trace_id,
                task_id=self.task_id,
                recovery_attempt_id=self.recovery_attempt_id,
            )
        if self.classification is RecoveryClassification.UNKNOWN_OUTCOME:
            return NZOutcome.build(
                NZOutcomeStatus.UNKNOWN_OUTCOME,
                NZReasonCode.UNKNOWN_OUTCOME,
                request_id=self.request_id,
                trace_id=self.trace_id,
                task_id=self.task_id,
                recovery_attempt_id=self.recovery_attempt_id,
            )
        if self.classification in {
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            RecoveryClassification.CORRUPT_CHECKPOINT,
            RecoveryClassification.UNSUPPORTED_SCHEMA,
            RecoveryClassification.RECOVERY_IN_PROGRESS,
        }:
            reason = {
                RecoveryClassification.CORRUPT_CHECKPOINT: "STATE_CORRUPT",
                RecoveryClassification.UNSUPPORTED_SCHEMA: "STATE_SCHEMA_UNSUPPORTED",
                RecoveryClassification.RECOVERY_IN_PROGRESS: "RECOVERY_IN_PROGRESS",
            }.get(
                self.classification,
                NZReasonCode.MANUAL_REVIEW_REQUIRED.value,
            )
            return NZOutcome.build(
                NZOutcomeStatus.MANUAL_REVIEW_REQUIRED,
                reason,
                request_id=self.request_id,
                trace_id=self.trace_id,
                task_id=self.task_id,
                recovery_attempt_id=self.recovery_attempt_id,
            )
        return outcome_from_task_state(
            self.task_state,
            request_id=self.request_id,
            trace_id=self.trace_id,
            task_id=self.task_id,
            recovery_attempt_id=self.recovery_attempt_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "recovery_attempt_id": self.recovery_attempt_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "classification": self.classification.value,
            "directive": self.directive.value,
            "status": self.status.value,
            "success": self.success,
            "task_state": self.task_state,
            "task_phase": self.task_phase,
            "checkpoint_version": self.checkpoint_version,
            "checkpoint_hash": self.checkpoint_hash,
            "outcome": self.outcome.to_dict(),
        }


@runtime_checkable
class TrustedRecoveryDispatcher(Protocol):
    """Runtime-injected recovery execution surface.

    Operator methods never accept a callback.  A single trusted runtime object
    is installed when the service is constructed and receives only process-local
    digest-validated candidates plus an active fenced token.
    """

    def resume_model(
        self,
        request_text: str,
        *,
        trace_context: TraceContext,
        step_reservation: StepReservation | None,
        recovery_token: "RecoveryExecutionToken",
    ) -> Mapping[str, Any]: ...

    def resume_reserved_action(
        self,
        action: Mapping[str, Any],
        *,
        trace_context: TraceContext,
        recovery_token: "RecoveryExecutionToken",
    ) -> Mapping[str, Any]: ...

    def resume_waiting_action(
        self,
        action: Mapping[str, Any],
        *,
        trace_context: TraceContext,
        recovery_token: "RecoveryExecutionToken",
    ) -> Mapping[str, Any]: ...

    def cancel_recoverable_action(
        self,
        *,
        trace_context: TraceContext,
        recovery_token: "RecoveryExecutionToken",
    ) -> Mapping[str, Any]: ...


RECOVERY_CLAIM_FIELDS = frozenset(
    {
        "schema_version", "task_id", "project_scope", "generation", "status",
        "purpose", "owner_id", "recovery_attempt_id", "claimed_at",
        "lease_expires_at", "released_at", "checkpoint_version",
        "checkpoint_hash", "execution_lock_device", "execution_lock_inode",
        "reason_code", "claim_hash",
    }
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate_runtime_id(value: object, prefix: str) -> str:
    if not isinstance(value, str) or not value.startswith(prefix + "_"):
        raise RecoveryCorruptionError("Recovery runtime identity is invalid.")
    suffix = value[len(prefix) + 1 :]
    if len(suffix) != 32:
        raise RecoveryCorruptionError("Recovery runtime identity is invalid.")
    try:
        uuid.UUID(hex=suffix)
    except ValueError as exc:
        raise RecoveryCorruptionError("Recovery runtime identity is invalid.") from exc
    return value


def _timestamp(value: dt.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> dt.datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise RecoveryCorruptionError("Recovery claim timestamp is invalid.")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RecoveryCorruptionError("Recovery claim timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        raise RecoveryCorruptionError("Recovery claim timestamp lacks an offset.")
    return parsed.astimezone(dt.UTC)


@dataclass(frozen=True)
class RecoveryClaim:
    schema_version: str
    task_id: str
    project_scope: str
    generation: int
    status: RecoveryClaimStatus
    purpose: RecoveryPurpose
    owner_id: str
    recovery_attempt_id: str
    claimed_at: str
    lease_expires_at: str
    released_at: str | None
    checkpoint_version: int | None
    checkpoint_hash: str | None
    execution_lock_device: int
    execution_lock_inode: int
    reason_code: str
    claim_hash: str

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "project_scope": self.project_scope,
            "generation": self.generation,
            "status": self.status.value,
            "purpose": self.purpose.value,
            "owner_id": self.owner_id,
            "recovery_attempt_id": self.recovery_attempt_id,
            "claimed_at": self.claimed_at,
            "lease_expires_at": self.lease_expires_at,
            "released_at": self.released_at,
            "checkpoint_version": self.checkpoint_version,
            "checkpoint_hash": self.checkpoint_hash,
            "execution_lock_device": self.execution_lock_device,
            "execution_lock_inode": self.execution_lock_inode,
            "reason_code": self.reason_code,
        }
        if include_hash:
            payload["claim_hash"] = self.claim_hash
        return payload

    def with_hash(self) -> "RecoveryClaim":
        return replace(self, claim_hash=_hash(self.to_payload(include_hash=False)))

    @classmethod
    def from_payload(cls, payload: object) -> "RecoveryClaim":
        if not isinstance(payload, dict) or frozenset(payload) != RECOVERY_CLAIM_FIELDS:
            raise RecoveryCorruptionError("Recovery claim has an inexact schema.")
        try:
            claim = cls(
                schema_version=payload["schema_version"],
                task_id=payload["task_id"],
                project_scope=payload["project_scope"],
                generation=payload["generation"],
                status=RecoveryClaimStatus(payload["status"]),
                purpose=RecoveryPurpose(payload["purpose"]),
                owner_id=payload["owner_id"],
                recovery_attempt_id=payload["recovery_attempt_id"],
                claimed_at=payload["claimed_at"],
                lease_expires_at=payload["lease_expires_at"],
                released_at=payload["released_at"],
                checkpoint_version=payload["checkpoint_version"],
                checkpoint_hash=payload["checkpoint_hash"],
                execution_lock_device=payload["execution_lock_device"],
                execution_lock_inode=payload["execution_lock_inode"],
                reason_code=payload["reason_code"],
                claim_hash=payload["claim_hash"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RecoveryCorruptionError("Recovery claim is malformed.") from exc
        claim.validate()
        return claim

    def validate(self) -> None:
        if self.schema_version != RECOVERY_CLAIM_SCHEMA_VERSION:
            raise RecoveryCorruptionError("Recovery claim schema is unsupported.")
        _validate_runtime_id(self.task_id, "task")
        _validate_runtime_id(self.owner_id, "recovery_owner")
        _validate_runtime_id(self.recovery_attempt_id, "recovery_attempt")
        if not _HEX.fullmatch(self.project_scope):
            raise RecoveryCorruptionError("Recovery claim project scope is invalid.")
        if isinstance(self.generation, bool) or not 1 <= self.generation <= 1_000_000:
            raise RecoveryCorruptionError("Recovery claim generation is invalid.")
        claimed = _parse_timestamp(self.claimed_at)
        expires = _parse_timestamp(self.lease_expires_at)
        if expires <= claimed or (expires - claimed).total_seconds() > MAX_RECOVERY_LEASE_SECONDS:
            raise RecoveryCorruptionError("Recovery claim lease is invalid.")
        if self.status is RecoveryClaimStatus.ACTIVE:
            if self.released_at is not None or self.reason_code != "RECOVERY_CLAIM_ACQUIRED":
                raise RecoveryCorruptionError("Active recovery claim semantics are invalid.")
        else:
            if self.released_at is None or self.reason_code != "RECOVERY_CLAIM_RELEASED":
                raise RecoveryCorruptionError("Released recovery claim semantics are invalid.")
            if _parse_timestamp(self.released_at) < claimed:
                raise RecoveryCorruptionError(
                    "Recovery claim release precedes its acquisition."
                )
        if self.checkpoint_version is not None and (
            isinstance(self.checkpoint_version, bool)
            or not 1 <= self.checkpoint_version <= 4096
        ):
            raise RecoveryCorruptionError("Recovery claim checkpoint version is invalid.")
        if (self.checkpoint_version is None) != (self.checkpoint_hash is None):
            raise RecoveryCorruptionError("Recovery claim checkpoint binding is incomplete.")
        if self.checkpoint_hash is not None and not _HEX.fullmatch(self.checkpoint_hash):
            raise RecoveryCorruptionError("Recovery claim checkpoint hash is invalid.")
        for value in (self.execution_lock_device, self.execution_lock_inode):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= (2**64 - 1)
            ):
                raise RecoveryCorruptionError(
                    "Recovery claim execution lock identity is invalid."
                )
        if self.claim_hash != _hash(self.to_payload(include_hash=False)):
            raise RecoveryCorruptionError("Recovery claim hash does not verify.")


class TrustedResumeInput:
    """Process-local, nonserializable candidate bound to one checkpoint digest."""

    __slots__ = (
        "task_id", "checkpoint_hash", "request_hash", "action_fingerprint",
        "_request_text", "_action_json", "_nonce", "_sealed",
    )

    def __init__(
        self,
        *,
        task_id: str,
        checkpoint_hash: str,
        request_hash: str | None,
        action_fingerprint: str | None,
        request_text: str | None,
        action: Mapping[str, Any] | None,
        nonce: str,
    ) -> None:
        object.__setattr__(self, "task_id", task_id)
        object.__setattr__(self, "checkpoint_hash", checkpoint_hash)
        object.__setattr__(self, "request_hash", request_hash)
        object.__setattr__(self, "action_fingerprint", action_fingerprint)
        object.__setattr__(self, "_request_text", request_text)
        object.__setattr__(
            self,
            "_action_json",
            _canonical_json(dict(action)) if action is not None else None,
        )
        object.__setattr__(self, "_nonce", nonce)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("TrustedResumeInput is immutable.")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("TrustedResumeInput is immutable.")

    def __repr__(self) -> str:
        return "TrustedResumeInput(<runtime-owned redacted capability>)"

    def __reduce__(self) -> object:
        raise TypeError("TrustedResumeInput cannot be serialized.")

    @property
    def request_text(self) -> str | None:
        return self._request_text

    @property
    def action(self) -> dict[str, Any] | None:
        return None if self._action_json is None else json.loads(self._action_json)


class RecoveryExecutionToken:
    __slots__ = (
        "task_id", "project_scope", "generation", "owner_id",
        "recovery_attempt_id", "request_id", "trace_id", "checkpoint_hash",
        "execution_lock_device", "execution_lock_inode", "purpose",
        "_nonce", "_owner_process_id", "_owner_thread_id", "_authority",
        "_sealed",
    )

    def __init__(
        self,
        claim: RecoveryClaim,
        trace: TraceContext,
        nonce: str,
        authority: "TaskRecoveryService",
    ) -> None:
        object.__setattr__(self, "task_id", claim.task_id)
        object.__setattr__(self, "project_scope", claim.project_scope)
        object.__setattr__(self, "generation", claim.generation)
        object.__setattr__(self, "owner_id", claim.owner_id)
        object.__setattr__(self, "recovery_attempt_id", claim.recovery_attempt_id)
        object.__setattr__(self, "request_id", trace.request_id)
        object.__setattr__(self, "trace_id", trace.trace_id)
        object.__setattr__(self, "checkpoint_hash", claim.checkpoint_hash)
        object.__setattr__(self, "purpose", claim.purpose)
        object.__setattr__(
            self, "execution_lock_device", claim.execution_lock_device
        )
        object.__setattr__(
            self, "execution_lock_inode", claim.execution_lock_inode
        )
        object.__setattr__(self, "_nonce", nonce)
        object.__setattr__(self, "_owner_process_id", os.getpid())
        object.__setattr__(self, "_owner_thread_id", threading.get_ident())
        object.__setattr__(self, "_authority", authority)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("RecoveryExecutionToken is immutable.")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("RecoveryExecutionToken is immutable.")

    def __repr__(self) -> str:
        return "RecoveryExecutionToken(<runtime-owned fenced capability>)"

    def __reduce__(self) -> object:
        raise TypeError("RecoveryExecutionToken cannot be serialized.")

    def _validate_active_owner(self, task_id: str) -> None:
        """Prove this exact object remains the authority's active owner."""

        if self.task_id != task_id:
            raise RecoveryFencedError(
                "Recovery execution token belongs to another task."
            )
        self._authority.classify_under_claim(task_id, self)

    def _validate_failed_model_remint(
        self, checkpoint: TaskCheckpoint
    ) -> None:
        """Authorize one remint only from exact terminal provider failure."""

        self._authority._validate_failed_model_remint(self, checkpoint)


@dataclass(frozen=True)
class _DispatchAuthorization:
    """Ephemeral exact authority for one trusted dispatcher callback."""

    token: RecoveryExecutionToken
    directive: RecoveryDirective
    process_id: int
    thread_id: int


def _event_id(*parts: object) -> str:
    digest = hashlib.sha256(":".join(str(item) for item in parts).encode("utf-8")).hexdigest()
    return f"provenance_event_{digest[:32]}"


@dataclass(frozen=True)
class _RecoveryResources:
    state_descriptor: int
    recovery_descriptor: int
    claims_descriptor: int
    claim_scope_descriptor: int
    execution_descriptor: int
    execution_scope_descriptor: int


class TaskRecoveryService:
    """Host-local restart classification, claims, and fenced execution."""

    def __init__(
        self,
        state_dir: Path,
        *,
        project_dir: Path,
        checkpoint_store: DurableTaskCheckpointStore | None = None,
        idempotency_store: Any | None = None,
        provenance_store: Any | None = None,
        lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
        lease_seconds: object = DEFAULT_RECOVERY_LEASE_SECONDS,
        clock: Callable[[], dt.datetime] | None = None,
        dispatcher: TrustedRecoveryDispatcher | None = None,
    ) -> None:
        self.state_dir = Path(state_dir).resolve()
        self.project_dir = Path(project_dir).resolve()
        self.project_scope = hashlib.sha256(
            str(self.project_dir).encode("utf-8")
        ).hexdigest()
        self.lock_timeout_seconds = validate_lock_timeout_seconds(lock_timeout_seconds)
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, (int, float)):
            raise ValueError("recovery lease must be a finite number of seconds")
        self.lease_seconds = float(lease_seconds)
        if not MIN_RECOVERY_LEASE_SECONDS <= self.lease_seconds <= MAX_RECOVERY_LEASE_SECONDS:
            raise ValueError("recovery lease is outside runtime policy bounds")
        self._clock = clock or (lambda: dt.datetime.now(dt.UTC))
        if dispatcher is not None and not isinstance(
            dispatcher, TrustedRecoveryDispatcher
        ):
            raise TypeError(
                "recovery dispatcher does not implement the trusted runtime protocol"
            )
        self._dispatcher = dispatcher
        if provenance_store is None:
            from runtime.tools.provenance import AppendOnlyProvenanceStore

            provenance_store = AppendOnlyProvenanceStore(
                self.state_dir, lock_timeout_seconds=self.lock_timeout_seconds
            )
        self.provenance_store = provenance_store
        if checkpoint_store is None:
            checkpoint_store = DurableTaskCheckpointStore(
                self.state_dir,
                project_dir=self.project_dir,
                provenance_store=self.provenance_store,
                lock_timeout_seconds=self.lock_timeout_seconds,
            )
        self.checkpoint_store = checkpoint_store
        if idempotency_store is None:
            from runtime.tools.idempotency import DurableIdempotencyStore

            idempotency_store = DurableIdempotencyStore(
                self.state_dir, lock_timeout_seconds=self.lock_timeout_seconds
            )
        self.idempotency_store = idempotency_store
        self.recovery_root = self.state_dir / "recovery"
        self.claim_root = self.recovery_root / "claims" / self.project_scope
        self.execution_root = self.recovery_root / "execution" / self.project_scope
        self._trusted_inputs: dict[str, TrustedResumeInput] = {}
        self._trusted_lock = threading.Lock()
        self._active_tokens: dict[str, RecoveryExecutionToken] = {}
        self._active_execution_locks: dict[str, InterProcessFileLock] = {}
        self._active_lock = threading.RLock()
        self._dispatch_authorization: ContextVar[
            _DispatchAuthorization | None
        ] = ContextVar(
            f"aoia_recovery_dispatch_authorization_{id(self)}",
            default=None,
        )
        self._initialize_recovery_roots()

    @contextmanager
    def _dispatch_authorization_scope(
        self,
        token: RecoveryExecutionToken,
        directive: RecoveryDirective,
    ) -> Iterator[None]:
        """Authorize only the exact service-selected dispatcher callback."""

        if not isinstance(directive, RecoveryDirective):
            raise RecoveryFencedError(
                "Recovery dispatch directive is not runtime-owned."
            )
        self.classify_under_claim(token.task_id, token)
        if token.purpose is RecoveryPurpose.RECOVERY:
            allowed = {
                RecoveryDirective.RESUME_MODEL,
                RecoveryDirective.REVALIDATE_ACTION,
                RecoveryDirective.REQUIRE_FRESH_APPROVAL,
            }
        elif token.purpose is RecoveryPurpose.OPERATOR:
            allowed = {RecoveryDirective.CANCEL_TASK}
        else:
            allowed = set()
        if directive not in allowed:
            raise RecoveryFencedError(
                "Recovery claim purpose does not authorize this dispatcher callback."
            )
        if self._dispatch_authorization.get() is not None:
            raise RecoveryFencedError(
                "A recovery dispatcher authorization is already active."
            )
        authorization = _DispatchAuthorization(
            token=token,
            directive=directive,
            process_id=os.getpid(),
            thread_id=threading.get_ident(),
        )
        binding = self._dispatch_authorization.set(authorization)
        try:
            yield
        finally:
            self._dispatch_authorization.reset(binding)

    def validate_dispatch_authorization(
        self,
        token: RecoveryExecutionToken,
        allowed_directives: frozenset[RecoveryDirective],
    ) -> RecoveryDirective:
        """Validate an exact, currently active service-to-runtime dispatch edge."""

        if (
            not isinstance(allowed_directives, frozenset)
            or not allowed_directives
            or any(
                not isinstance(item, RecoveryDirective)
                for item in allowed_directives
            )
        ):
            raise RecoveryFencedError(
                "Recovery dispatch validation requires explicit directives."
            )
        if not isinstance(token, RecoveryExecutionToken):
            raise RecoveryFencedError(
                "Recovery dispatch authorization requires its exact token."
            )
        self.classify_under_claim(token.task_id, token)
        authorization = self._dispatch_authorization.get()
        if (
            authorization is None
            or authorization.token is not token
            or authorization.directive not in allowed_directives
            or authorization.process_id != os.getpid()
            or authorization.thread_id != threading.get_ident()
        ):
            raise RecoveryFencedError(
                "Recovery dispatch was not authorized by the active service operation."
            )
        return authorization.directive

    @staticmethod
    def _directory_flags() -> int:
        return (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )

    @classmethod
    def _open_child_directory(
        cls,
        parent_descriptor: int,
        name: str,
        *,
        create: bool,
        expected_identity: tuple[int, int] | None = None,
    ) -> tuple[int, tuple[int, int]]:
        try:
            metadata = os.stat(
                name, dir_fd=parent_descriptor, follow_symlinks=False
            )
        except FileNotFoundError:
            if not create:
                raise RecoveryCorruptionError(
                    "Recovery directory binding disappeared."
                )
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
            except FileExistsError:
                pass
            metadata = os.stat(
                name, dir_fd=parent_descriptor, follow_symlinks=False
            )
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RecoveryCorruptionError(
                "Recovery directory chain contains an unsafe component."
            )
        try:
            descriptor = os.open(
                name, cls._directory_flags(), dir_fd=parent_descriptor
            )
        except OSError as exc:
            raise RecoveryCorruptionError(
                "Recovery directory could not be opened without following links."
            ) from exc
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or identity != (metadata.st_dev, metadata.st_ino)
            or (expected_identity is not None and identity != expected_identity)
        ):
            os.close(descriptor)
            raise RecoveryCorruptionError("Recovery directory binding changed.")
        return descriptor, identity

    def _initialize_recovery_roots(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        metadata = self.state_dir.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RecoveryCorruptionError("Recovery state root is unsafe.")
        try:
            state_descriptor = os.open(self.state_dir, self._directory_flags())
        except OSError as exc:
            raise RecoveryCorruptionError("Recovery state root could not be pinned.") from exc
        descriptors = [state_descriptor]
        try:
            opened = os.fstat(state_descriptor)
            self._state_identity = (opened.st_dev, opened.st_ino)
            if self._state_identity != (metadata.st_dev, metadata.st_ino):
                raise RecoveryCorruptionError("Recovery state root binding changed.")
            recovery, self._recovery_identity = self._open_child_directory(
                state_descriptor, "recovery", create=True
            )
            descriptors.append(recovery)
            claims, self._claims_identity = self._open_child_directory(
                recovery, "claims", create=True
            )
            descriptors.append(claims)
            claim_scope, self._claim_scope_identity = self._open_child_directory(
                claims, self.project_scope, create=True
            )
            descriptors.append(claim_scope)
            execution, self._execution_identity = self._open_child_directory(
                recovery, "execution", create=True
            )
            descriptors.append(execution)
            execution_scope, self._execution_scope_identity = (
                self._open_child_directory(
                    execution, self.project_scope, create=True
                )
            )
            descriptors.append(execution_scope)
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    @contextmanager
    def _open_recovery_resources(self) -> Iterator[_RecoveryResources]:
        try:
            metadata = self.state_dir.lstat()
            state_descriptor = os.open(self.state_dir, self._directory_flags())
        except OSError as exc:
            raise RecoveryCorruptionError("Recovery state root binding changed.") from exc
        descriptors = [state_descriptor]
        try:
            opened = os.fstat(state_descriptor)
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISDIR(metadata.st_mode)
                or (opened.st_dev, opened.st_ino) != self._state_identity
                or (metadata.st_dev, metadata.st_ino) != self._state_identity
            ):
                raise RecoveryCorruptionError("Recovery state root binding changed.")
            recovery, _ = self._open_child_directory(
                state_descriptor,
                "recovery",
                create=False,
                expected_identity=self._recovery_identity,
            )
            descriptors.append(recovery)
            claims, _ = self._open_child_directory(
                recovery,
                "claims",
                create=False,
                expected_identity=self._claims_identity,
            )
            descriptors.append(claims)
            claim_scope, _ = self._open_child_directory(
                claims,
                self.project_scope,
                create=False,
                expected_identity=self._claim_scope_identity,
            )
            descriptors.append(claim_scope)
            execution, _ = self._open_child_directory(
                recovery,
                "execution",
                create=False,
                expected_identity=self._execution_identity,
            )
            descriptors.append(execution)
            execution_scope, _ = self._open_child_directory(
                execution,
                self.project_scope,
                create=False,
                expected_identity=self._execution_scope_identity,
            )
            descriptors.append(execution_scope)
            resources = _RecoveryResources(
                state_descriptor,
                recovery,
                claims,
                claim_scope,
                execution,
                execution_scope,
            )
            self._validate_recovery_resources(resources)
            yield resources
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def _validate_recovery_resources(
        self, resources: _RecoveryResources
    ) -> None:
        expected = (
            (resources.state_descriptor, self._state_identity),
            (resources.recovery_descriptor, self._recovery_identity),
            (resources.claims_descriptor, self._claims_identity),
            (resources.claim_scope_descriptor, self._claim_scope_identity),
            (resources.execution_descriptor, self._execution_identity),
            (resources.execution_scope_descriptor, self._execution_scope_identity),
        )
        try:
            visible_state = self.state_dir.lstat()
            if (
                stat.S_ISLNK(visible_state.st_mode)
                or not stat.S_ISDIR(visible_state.st_mode)
                or (visible_state.st_dev, visible_state.st_ino)
                != self._state_identity
            ):
                raise RecoveryCorruptionError(
                    "Recovery state root binding changed."
                )
            for descriptor, identity in expected:
                opened = os.fstat(descriptor)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or (opened.st_dev, opened.st_ino) != identity
                ):
                    raise RecoveryCorruptionError(
                        "Pinned recovery directory binding changed."
                    )
            edges = (
                (resources.state_descriptor, "recovery", self._recovery_identity),
                (resources.recovery_descriptor, "claims", self._claims_identity),
                (
                    resources.claims_descriptor,
                    self.project_scope,
                    self._claim_scope_identity,
                ),
                (
                    resources.recovery_descriptor,
                    "execution",
                    self._execution_identity,
                ),
                (
                    resources.execution_descriptor,
                    self.project_scope,
                    self._execution_scope_identity,
                ),
            )
            for parent, name, identity in edges:
                child = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if (
                    stat.S_ISLNK(child.st_mode)
                    or not stat.S_ISDIR(child.st_mode)
                    or (child.st_dev, child.st_ino) != identity
                ):
                    raise RecoveryCorruptionError(
                        "Recovery directory chain binding changed."
                    )
        except RecoveryCorruptionError:
            raise
        except OSError as exc:
            raise RecoveryCorruptionError(
                "Recovery directory chain binding changed."
            ) from exc

    def _ensure_roots(self) -> None:
        with self._open_recovery_resources():
            pass

    @staticmethod
    def _resource_id(task_id: str) -> str:
        _validate_runtime_id(task_id, "task")
        return hashlib.sha256(task_id.encode("ascii")).hexdigest()

    def claim_path(self, task_id: str) -> Path:
        return self.claim_root / f"{self._resource_id(task_id)}.json"

    def execution_lock_path(self, task_id: str) -> Path:
        return self.execution_root / f"{self._resource_id(task_id)}.lock"

    def claim_lock_path(self, task_id: str) -> Path:
        return self.claim_root / f"{self._resource_id(task_id)}.claim.lock"

    def _read_claim(
        self,
        task_id: str,
        *,
        _resources: _RecoveryResources | None = None,
    ) -> RecoveryClaim | None:
        if _resources is None:
            with self._open_recovery_resources() as resources:
                return self._read_claim(task_id, _resources=resources)
        self._validate_recovery_resources(_resources)
        path = self.claim_path(task_id)
        with InterProcessFileLock(
            self.claim_lock_path(task_id),
            timeout_seconds=self.lock_timeout_seconds,
            parent_directory_descriptor=_resources.claim_scope_descriptor,
            directory_identity_validator=lambda: (
                self._validate_recovery_resources(_resources)
            ),
        ):
            try:
                payload = read_json_snapshot(
                    path,
                    reject_duplicate_keys=True,
                    maximum_bytes=MAX_RECOVERY_CLAIM_BYTES,
                    expected_parent_identity=self._claim_scope_identity,
                    parent_directory_descriptor=(
                        _resources.claim_scope_descriptor
                    ),
                    directory_identity_validator=lambda: (
                        self._validate_recovery_resources(_resources)
                    ),
                )
            except StateCorruptionError as exc:
                raise RecoveryCorruptionError("Recovery claim JSON is corrupt.") from exc
        return None if payload is None else RecoveryClaim.from_payload(payload)

    def _read_checkpoint(self, task_id: str) -> TaskCheckpoint | None:
        return self.checkpoint_store.load_snapshot_unanchored(task_id)

    def _claim_is_active(self, task_id: str) -> bool:
        claim = self._read_claim(task_id)
        if claim is None or claim.status is not RecoveryClaimStatus.ACTIVE:
            return False
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.UTC)
        if _parse_timestamp(claim.lease_expires_at) > now.astimezone(dt.UTC):
            return True
        with self._open_recovery_resources() as resources:
            try:
                with InterProcessFileLock(
                    self.execution_lock_path(task_id),
                    timeout_seconds=0.0,
                    parent_directory_descriptor=(
                        resources.execution_scope_descriptor
                    ),
                    directory_identity_validator=lambda: (
                        self._validate_recovery_resources(resources)
                    ),
                ) as held_lock:
                    if held_lock.validate_binding() != (
                        claim.execution_lock_device,
                        claim.execution_lock_inode,
                    ):
                        raise RecoveryCorruptionError(
                            "Expired recovery claim references a replaced execution lock."
                        )
                    return False
            except StateLockTimeoutError:
                return True

    def _provenance_module(self) -> Any:
        return importlib.import_module(type(self.provenance_store).__module__)

    def _idempotency_record(self, checkpoint: TaskCheckpoint) -> Any | None:
        if checkpoint.current_idempotency_key is None:
            return None
        module = importlib.import_module(type(self.idempotency_store).__module__)
        operation_type = getattr(module, "OperationContext")
        try:
            record = self.idempotency_store.load(
                operation_type(checkpoint.current_idempotency_key)
            )
        except getattr(module, "IdempotencyStoreCorruptionError") as exc:
            raise RecoveryCorruptionError(
                "Durable idempotency evidence is corrupt."
            ) from exc
        if record is None:
            return None
        conflict_checkpoint = (
            checkpoint.state is TaskState.BLOCKED
            and checkpoint.phase is TaskPhase.TERMINAL
            and checkpoint.reason_code == "TASK_IDEMPOTENCY_CONFLICT"
            and checkpoint.current_idempotency_state == "CONFLICT"
        )
        if (
            record.task_id != checkpoint.task_id
            or record.project_scope != checkpoint.project_scope
            or (
                checkpoint.current_action_fingerprint is not None
                and record.action_fingerprint != checkpoint.current_action_fingerprint
                and not conflict_checkpoint
            )
        ):
            raise RecoveryCorruptionError(
                "Idempotency evidence conflicts with the task checkpoint."
            )
        return record

    @staticmethod
    def _checkpoint_requires_idempotency_record(
        checkpoint: TaskCheckpoint,
    ) -> bool:
        if checkpoint.current_idempotency_key is None:
            return False
        if checkpoint.phase in {
            TaskPhase.IDEMPOTENCY_RESERVED,
            TaskPhase.PROVENANCE_DISPATCH_RECORDED,
            TaskPhase.DISPATCH_IN_FLIGHT,
            TaskPhase.AFTER_ACTION,
        }:
            return True
        return (
            checkpoint.state in TERMINAL_TASK_STATES
            and checkpoint.current_action_id is not None
            and checkpoint.current_idempotency_state is not None
        )

    @staticmethod
    def _checkpoint_is_latest_committed(
        checkpoint: TaskCheckpoint,
        records: list[dict[str, Any]],
    ) -> bool:
        """Reject replay of an older valid snapshot that would remint budget."""

        committed = [
            item
            for item in records
            if item.get("event_type") == "TASK_CHECKPOINTED"
            and item.get("task_id") == checkpoint.task_id
        ]
        if not committed:
            return False
        versions = [item.get("checkpoint_version") for item in committed]
        if any(
            isinstance(version, bool) or not isinstance(version, int)
            for version in versions
        ):
            return False
        if versions != list(range(1, len(versions) + 1)):
            return False
        latest = committed[-1]
        return (
            latest.get("event_id") == checkpoint.latest_provenance_event_id
            and latest.get("checkpoint_version") == checkpoint.checkpoint_version
            and latest.get("checkpoint_hash") == checkpoint.checkpoint_hash
        )

    @staticmethod
    def _conflict_event(
        checkpoint: TaskCheckpoint,
        record: Any,
        records: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Bind a losing attempted fingerprint to its canonical P0.8 receipt."""

        matches = [
            item
            for item in records
            if item.get("event_type") == "IDEMPOTENCY_CONFLICT"
            and item.get("task_id") == checkpoint.task_id
            and item.get("action_id") == checkpoint.current_action_id
            and item.get("operation_key") == checkpoint.current_idempotency_key
            and item.get("action_fingerprint")
            == checkpoint.current_action_fingerprint
            and item.get("capability_class")
            == checkpoint.current_capability_class
            and item.get("idempotency_state") == "CONFLICT"
            and item.get("replayed") is False
            and item.get("dispatched") is False
            and item.get("success") is False
            and item.get("reason_code") == "IDEMPOTENCY_KEY_CONFLICT"
        ]
        if (
            len(matches) != 1
            or record.task_id != checkpoint.task_id
            or record.project_scope != checkpoint.project_scope
            or record.operation_key != checkpoint.current_idempotency_key
            or checkpoint.causal_provenance_event_id
            != matches[0].get("event_id")
        ):
            return None
        return matches[0]

    def _unrepresented_execution_evidence(
        self,
        checkpoint: TaskCheckpoint,
        records: list[dict[str, Any]],
    ) -> bool:
        execution_types = {
            "REQUEST_STARTED",
            "MODEL_CALL_STARTED",
            "MODEL_CALL_COMPLETED",
            "MODEL_CALL_FAILED",
            "CAPABILITY_DECISION",
            "APPROVAL_GRANTED",
            "APPROVAL_DENIED",
            "IDEMPOTENCY_RESERVED",
            "IDEMPOTENCY_REPLAYED",
            "IDEMPOTENCY_CONFLICT",
            "ACTION_DISPATCH_STARTED",
            "ACTION_DISPATCH_SUCCEEDED",
            "ACTION_DISPATCH_FAILED",
            "ACTION_DISPATCH_TIMED_OUT",
            "ACTION_DISPATCH_BLOCKED",
            "ACTION_DISPATCH_CANCELLED",
            "UNKNOWN_OUTCOME_DETECTED",
        }
        if any(
            item.get("task_id") == checkpoint.task_id
            and item.get("event_type") in execution_types
            for item in records
        ):
            return True
        return self._unrepresented_idempotency_evidence(checkpoint)

    def _unrepresented_idempotency_evidence(
        self, checkpoint: TaskCheckpoint
    ) -> bool:
        """Boundedly find P0.7 truth not represented by this checkpoint.

        A crash can durably reserve a P0.7 operation before its matching P0.8
        receipt or checkpoint transition. In that window provenance alone is
        insufficient to rule out prior action work, so model recovery must
        fail closed. The scan is flat, bounded, no-follow, and treats an
        unreadable record set as uncertain rather than authorizing execution.
        """

        try:
            module = importlib.import_module(type(self.idempotency_store).__module__)
            record_type = getattr(module, "IdempotencyRecord")
            maximum_bytes = int(
                getattr(module, "MAX_IDEMPOTENCY_RECORD_BYTES", 64 * 1024)
            )
            root = Path(self.idempotency_store.root_dir)
            metadata = root.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                return True
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(root, flags)
            try:
                opened = os.fstat(descriptor)
                identity = (opened.st_dev, opened.st_ino)
                if identity != (metadata.st_dev, metadata.st_ino):
                    return True

                def validate_root() -> None:
                    visible = root.lstat()
                    current = os.fstat(descriptor)
                    if (
                        stat.S_ISLNK(visible.st_mode)
                        or not stat.S_ISDIR(visible.st_mode)
                        or not stat.S_ISDIR(current.st_mode)
                        or (visible.st_dev, visible.st_ino) != identity
                        or (current.st_dev, current.st_ino) != identity
                    ):
                        raise RecoveryCorruptionError(
                            "Idempotency recovery scan root binding changed."
                        )

                record_count = 0
                with os.scandir(descriptor) as iterator:
                    for entry in iterator:
                        stem, suffix = os.path.splitext(entry.name)
                        if suffix != ".json" or not _HEX.fullmatch(stem):
                            continue
                        record_count += 1
                        if record_count > MAX_RECOVERY_IDEMPOTENCY_SCAN_RECORDS:
                            return True
                        if entry.is_symlink() or not entry.is_file(
                            follow_symlinks=False
                        ):
                            return True
                        payload = read_json_snapshot(
                            root / entry.name,
                            reject_duplicate_keys=True,
                            maximum_bytes=maximum_bytes,
                            expected_parent_identity=identity,
                            parent_directory_descriptor=descriptor,
                            directory_identity_validator=validate_root,
                        )
                        if payload is None:
                            return True
                        record = record_type.from_payload(payload)
                        if (
                            self.idempotency_store.record_path(
                                record.operation_key
                            ).name
                            != entry.name
                        ):
                            return True
                        if (
                            record.task_id == checkpoint.task_id
                            and record.operation_key
                            != checkpoint.current_idempotency_key
                        ):
                            return True
                validate_root()
            finally:
                os.close(descriptor)
        except (OSError, PersistenceError, RuntimeError, TypeError, ValueError):
            return True
        return False

    @staticmethod
    def _terminal_event_matches(record: Any, event: Mapping[str, Any]) -> bool:
        state = getattr(record.state, "value", record.state)
        expected = {
            "SUCCEEDED": ("ACTION_DISPATCH_SUCCEEDED", True, True),
            "BLOCKED": ("ACTION_DISPATCH_BLOCKED", False, False),
            "CANCELLED": ("ACTION_DISPATCH_CANCELLED", False, False),
            "FAILED_BEFORE_DISPATCH": ("ACTION_DISPATCH_FAILED", False, False),
            "FAILED_REPORTED": ("ACTION_DISPATCH_FAILED", False, True),
        }.get(state)
        if expected is None:
            return False
        event_type, success, dispatched = expected
        common = (
            event.get("task_id") == record.task_id
            and event.get("action_id") == record.action_id
            and event.get("operation_key") == record.operation_key
            and event.get("action_fingerprint") == record.action_fingerprint
            and event.get("idempotency_state") == state
        )
        if not common:
            return False
        if event.get("event_type") == "RECOVERY_TERMINAL_RECONCILED":
            return (
                event.get("terminal_receipt_hash") == _hash(record.terminal_receipt)
                and event.get("success") is True
                and event.get("recovery_directive")
                == RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE.value
            )
        return (
            event.get("event_type") == event_type
            and event.get("success") is success
            and event.get("dispatched") is dispatched
            and event.get("replayed") is False
            and event.get("reason_code") == record.reason_code
        )

    def _matching_terminal_event(
        self,
        checkpoint: TaskCheckpoint,
        record: Any,
        records: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in reversed(records)
                if self._terminal_event_matches(record, item)
            ),
            None,
        )

    @staticmethod
    def _reserved_resolution_event(
        record: Any,
        records: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        matches = [
            item
            for item in records
            if item.get("event_type") == "IDEMPOTENCY_RESERVED"
            and item.get("task_id") == record.task_id
            and item.get("request_id") == record.request_id
            and item.get("trace_id") == record.trace_id
            and item.get("model_call_id") == record.model_call_id
            and item.get("action_id") == record.action_id
            and item.get("operation_key") == record.operation_key
            and item.get("action_fingerprint") == record.action_fingerprint
            and item.get("capability_class") == record.capability_class
            and item.get("idempotency_state") == "RESERVED"
            and item.get("replayed") is False
            and item.get("dispatched") is False
        ]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _definitive_model_failure(
        checkpoint: TaskCheckpoint,
        records: list[dict[str, Any]],
    ) -> bool:
        """Require an ordered P0.8 start/failure pair for the current attempt."""

        model_call_id = checkpoint.current_model_call_id
        if model_call_id is None:
            return False
        matching: list[tuple[int, dict[str, Any]]] = [
            (index, item)
            for index, item in enumerate(records)
            if item.get("task_id") == checkpoint.task_id
            and item.get("request_id") == checkpoint.latest_request_id
            and item.get("trace_id") == checkpoint.latest_trace_id
            and item.get("model_call_id") == model_call_id
        ]
        starts = [
            index
            for index, item in matching
            if item.get("event_type") == "MODEL_CALL_STARTED"
            and item.get("reason_code") == "MODEL_CALL_STARTED"
        ]
        failures = [
            index
            for index, item in matching
            if item.get("event_type") == "MODEL_CALL_FAILED"
            and item.get("reason_code") == "MODEL_CALL_FAILED"
            and item.get("success") is False
        ]
        completed = any(
            item.get("event_type") == "MODEL_CALL_COMPLETED"
            for _index, item in matching
        )
        return (
            len(starts) == 1
            and len(failures) == 1
            and starts[0] < failures[0]
            and not completed
        )

    @staticmethod
    def _model_terminal_evidence(
        checkpoint: TaskCheckpoint,
        records: list[dict[str, Any]],
    ) -> str | None:
        """Return one exact terminal provider fact after its matching start."""

        model_call_id = checkpoint.current_model_call_id
        if model_call_id is None:
            return None
        matching = [
            (index, item)
            for index, item in enumerate(records)
            if item.get("task_id") == checkpoint.task_id
            and item.get("request_id") == checkpoint.latest_request_id
            and item.get("trace_id") == checkpoint.latest_trace_id
            and item.get("model_call_id") == model_call_id
        ]
        starts = [
            index
            for index, item in matching
            if item.get("event_type") == "MODEL_CALL_STARTED"
            and item.get("reason_code") == "MODEL_CALL_STARTED"
        ]
        terminals = [
            (index, item.get("event_type"))
            for index, item in matching
            if (
                item.get("event_type") == "MODEL_CALL_FAILED"
                and item.get("reason_code") == "MODEL_CALL_FAILED"
                and item.get("success") is False
            )
            or (
                item.get("event_type") == "MODEL_CALL_COMPLETED"
                and item.get("reason_code") == "MODEL_CALL_COMPLETED"
                and item.get("success") is True
            )
        ]
        if (
            len(starts) != 1
            or len(terminals) != 1
            or starts[0] >= terminals[0][0]
        ):
            return None
        return str(terminals[0][1])

    def _between_steps_read_only_proven(
        self,
        checkpoint: TaskCheckpoint,
        records: list[dict[str, Any]],
    ) -> bool:
        """Prove every completed prior step was a terminal read-only dispatch."""

        starts = [
            item
            for item in records
            if item.get("event_type") == "ACTION_DISPATCH_STARTED"
            and item.get("task_id") == checkpoint.task_id
        ]
        if len(starts) != checkpoint.step_index or not starts:
            return False
        operation_keys = [item.get("operation_key") for item in starts]
        if (
            any(not isinstance(key, str) for key in operation_keys)
            or len(set(operation_keys)) != len(operation_keys)
        ):
            return False
        module = importlib.import_module(type(self.idempotency_store).__module__)
        operation_type = getattr(module, "OperationContext")
        for start in starts:
            if (
                start.get("capability_class") != "READ_ONLY"
                or start.get("idempotency_state") != "RESERVED"
                or start.get("dispatched") is not True
                or start.get("replayed") is not False
            ):
                return False
            try:
                record = self.idempotency_store.load(
                    operation_type(str(start["operation_key"]))
                )
            except Exception as exc:
                raise RecoveryCorruptionError(
                    "Prior-step idempotency evidence is corrupt."
                ) from exc
            if (
                record is None
                or record.task_id != checkpoint.task_id
                or record.project_scope != checkpoint.project_scope
                or record.action_id != start.get("action_id")
                or record.action_fingerprint != start.get("action_fingerprint")
                or record.capability_class != "READ_ONLY"
                or getattr(record.state, "value", record.state) != "SUCCEEDED"
            ):
                return False
            terminal = next(
                (
                    item
                    for item in reversed(records)
                    if item.get("capability_class") == "READ_ONLY"
                    and self._terminal_event_matches(record, item)
                ),
                None,
            )
            if terminal is None:
                return False
        return True

    @staticmethod
    def _request_execution_started(
        checkpoint: TaskCheckpoint,
        records: list[dict[str, Any]],
    ) -> bool:
        """Detect an ingress that may already have executed a local command."""

        return any(
            item.get("event_type") == "REQUEST_STARTED"
            and item.get("task_id") == checkpoint.task_id
            and item.get("request_id") == checkpoint.latest_request_id
            and item.get("trace_id") == checkpoint.latest_trace_id
            for item in records
        )

    @staticmethod
    def _pristine_read_only_pre_dispatch_proven(
        checkpoint: TaskCheckpoint,
        records: list[dict[str, Any]],
    ) -> bool:
        """Prove policy completed but P0.7 reservation/dispatch never began."""

        if (
            checkpoint.state is not TaskState.RUNNING
            or checkpoint.phase is not TaskPhase.BEFORE_DISPATCH
            or checkpoint.reason_code != "TASK_BEFORE_DISPATCH"
            or checkpoint.approval_state is not ApprovalState.NOT_REQUIRED
            or checkpoint.current_capability_class != "READ_ONLY"
            or checkpoint.current_action_id is None
            or checkpoint.current_idempotency_key is None
            or checkpoint.current_action_name is None
            or checkpoint.current_action_fingerprint is None
            or checkpoint.current_policy_reason_code is None
            or checkpoint.current_idempotency_state is not None
        ):
            return False
        matching = [
            item
            for item in records
            if item.get("task_id") == checkpoint.task_id
            and item.get("action_id") == checkpoint.current_action_id
            and item.get("operation_key") == checkpoint.current_idempotency_key
        ]
        policy = [
            item
            for item in matching
            if item.get("event_type") == "CAPABILITY_DECISION"
            and item.get("request_id") == checkpoint.latest_request_id
            and item.get("trace_id") == checkpoint.latest_trace_id
            and item.get("model_call_id") == checkpoint.current_model_call_id
            and item.get("action_name") == checkpoint.current_action_name
            and item.get("capability_class") == "READ_ONLY"
            and item.get("policy_allowed") is True
            and item.get("approval_required") is False
            and item.get("reason_code")
            == checkpoint.current_policy_reason_code
        ]
        unsafe_types = {
            "IDEMPOTENCY_RESERVED",
            "IDEMPOTENCY_REPLAYED",
            "IDEMPOTENCY_CONFLICT",
            "ACTION_DISPATCH_STARTED",
            "ACTION_DISPATCH_SUCCEEDED",
            "ACTION_DISPATCH_FAILED",
            "ACTION_DISPATCH_TIMED_OUT",
            "ACTION_DISPATCH_BLOCKED",
            "ACTION_DISPATCH_CANCELLED",
            "UNKNOWN_OUTCOME_DETECTED",
            "PERSISTENCE_FAILURE",
            "RECOVERY_TERMINAL_RECONCILED",
        }
        return len(policy) == 1 and not any(
            item.get("event_type") in unsafe_types for item in matching
        )

    def _classify_reserved_record(
        self,
        checkpoint: TaskCheckpoint,
        record: Any,
        records: list[dict[str, Any]],
    ) -> RecoveryDecision:
        reservation_event = self._reserved_resolution_event(record, records)
        if checkpoint.phase is not TaskPhase.IDEMPOTENCY_RESERVED:
            if (
                checkpoint.state is TaskState.RUNNING
                and checkpoint.phase is TaskPhase.BEFORE_DISPATCH
                and reservation_event is not None
            ):
                return self._decision(
                    checkpoint,
                    RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.RECONCILE_CHECKPOINT,
                    "RECOVERY_RESERVED_CHECKPOINT_PENDING",
                    idempotency_state="RESERVED",
                    provenance_event_id=str(reservation_event["event_id"]),
                )
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_RESERVED_PROVENANCE_PENDING",
                idempotency_state="RESERVED",
            )
        if (
            reservation_event is None
            or checkpoint.causal_provenance_event_id
            != reservation_event.get("event_id")
            or checkpoint.current_idempotency_state != "RESERVED"
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_RESERVED_PROVENANCE_PENDING",
                idempotency_state="RESERVED",
            )
        needs_approval = checkpoint.approval_state is not ApprovalState.NOT_REQUIRED
        return self._decision(
            checkpoint,
            RecoveryClassification.WAITING_FOR_FRESH_APPROVAL
            if needs_approval
            else RecoveryClassification.SAFE_TO_RESUME,
            RecoveryDirective.REQUIRE_FRESH_APPROVAL
            if needs_approval
            else RecoveryDirective.REVALIDATE_ACTION,
            "RECOVERY_RESERVED_ACTION_FRESH_APPROVAL_REQUIRED"
            if needs_approval
            else "RECOVERY_RESERVED_ACTION_REQUIRES_REVALIDATION",
            idempotency_state="RESERVED",
            requires_trusted_input=True,
            requires_fresh_approval=needs_approval,
        )

    def _decision(
        self,
        checkpoint: TaskCheckpoint,
        classification: RecoveryClassification,
        directive: RecoveryDirective,
        reason_code: str,
        *,
        idempotency_state: str | None = None,
        provenance_event_id: str | None = None,
        requires_trusted_input: bool = False,
        requires_fresh_approval: bool = False,
    ) -> RecoveryDecision:
        return RecoveryDecision(
            schema_version=RECOVERY_DECISION_SCHEMA_VERSION,
            task_id=checkpoint.task_id,
            resource_id=self._resource_id(checkpoint.task_id),
            project_scope=checkpoint.project_scope,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            classification=classification,
            directive=directive,
            reason_code=reason_code,
            idempotency_state=idempotency_state,
            provenance_event_id=provenance_event_id,
            requires_trusted_input=requires_trusted_input,
            requires_fresh_approval=requires_fresh_approval,
        )

    def _terminal_checkpoint_decision(
        self,
        checkpoint: TaskCheckpoint,
        record: Any | None,
        records: list[dict[str, Any]],
    ) -> RecoveryDecision | None:
        """Validate canonical P0.7/P0.8 truth before trusting a terminal task."""

        if checkpoint.state not in TERMINAL_TASK_STATES:
            return None
        if checkpoint.reason_code == "TASK_IDEMPOTENCY_CONFLICT":
            if record is None or self._conflict_event(
                checkpoint, record, records
            ) is None:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_IDEMPOTENCY_CORRUPT",
                )
            return self._decision(
                checkpoint,
                RecoveryClassification.CONFLICT,
                RecoveryDirective.NO_ACTION,
                "RECOVERY_TASK_CONFLICT",
                idempotency_state="CONFLICT",
                provenance_event_id=checkpoint.causal_provenance_event_id,
            )
        if record is not None:
            state = getattr(record.state, "value", record.state)
            terminal_states = {
                "SUCCEEDED", "BLOCKED", "CANCELLED",
                "FAILED_BEFORE_DISPATCH", "FAILED_REPORTED",
            }
            if (
                state not in terminal_states
                or checkpoint.current_idempotency_state != state
            ):
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_IDEMPOTENCY_CORRUPT",
                    idempotency_state=state,
                )
            matching = [
                item
                for item in records
                if item.get("task_id") == checkpoint.task_id
                and item.get("operation_key") == record.operation_key
            ]
            has_start = any(
                item.get("event_type") == "ACTION_DISPATCH_STARTED"
                and item.get("action_id") == record.action_id
                and item.get("action_fingerprint") == record.action_fingerprint
                and item.get("dispatched") is True
                for item in matching
            )
            if state in {"SUCCEEDED", "FAILED_REPORTED"} and not has_start:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_TERMINAL_WITHOUT_DISPATCH_START",
                    idempotency_state=state,
                )
            if state in {
                "BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH"
            } and has_start:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT",
                    idempotency_state=state,
                )
            terminal = self._matching_terminal_event(
                checkpoint, record, matching
            )
            if (
                terminal is None
                or checkpoint.causal_provenance_event_id
                != terminal.get("event_id")
            ):
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT",
                    idempotency_state=state,
                )
        if checkpoint.state is TaskState.COMPLETED:
            return self._decision(
                checkpoint,
                RecoveryClassification.ALREADY_COMPLETED,
                RecoveryDirective.NO_ACTION,
                "RECOVERY_TASK_ALREADY_COMPLETED",
            )
        if checkpoint.state is TaskState.BLOCKED:
            return self._decision(
                checkpoint,
                RecoveryClassification.BLOCKED,
                RecoveryDirective.NO_ACTION,
                "RECOVERY_TASK_BLOCKED",
            )
        return self._decision(
            checkpoint,
            RecoveryClassification.TERMINAL_NO_RESUME,
            RecoveryDirective.NO_ACTION,
            "RECOVERY_TASK_TERMINAL",
        )

    def _corrupt_decision(
        self, task_id: str | None, resource_id: str, classification: RecoveryClassification,
        reason_code: str,
    ) -> RecoveryDecision:
        return RecoveryDecision(
            schema_version=RECOVERY_DECISION_SCHEMA_VERSION,
            task_id=task_id,
            resource_id=resource_id,
            project_scope=self.project_scope,
            checkpoint_version=None,
            checkpoint_hash=None,
            task_state=None,
            task_phase=None,
            classification=classification,
            directive=RecoveryDirective.REQUIRE_OPERATOR_ACK,
            reason_code=reason_code,
        )

    def classify(self, task_id: str) -> RecoveryDecision:
        resource_id = self._resource_id(task_id)
        try:
            checkpoint = self._read_checkpoint(task_id)
            if checkpoint is None:
                return self._corrupt_decision(
                    task_id, resource_id,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    "RECOVERY_CHECKPOINT_MISSING",
                )
            records = self.provenance_store.read_runtime_all()
        except TaskCheckpointSchemaError:
            return self._corrupt_decision(
                task_id, resource_id, RecoveryClassification.UNSUPPORTED_SCHEMA,
                "RECOVERY_CHECKPOINT_SCHEMA_UNSUPPORTED",
            )
        except (TaskCheckpointCorruptionError, RecoveryCorruptionError):
            return self._corrupt_decision(
                task_id, resource_id, RecoveryClassification.CORRUPT_CHECKPOINT,
                "RECOVERY_CHECKPOINT_CORRUPT",
            )
        except PersistenceError:
            return self._corrupt_decision(
                task_id, resource_id, RecoveryClassification.CORRUPT_CHECKPOINT,
                "RECOVERY_PROVENANCE_CORRUPT",
            )

        try:
            claim_is_active = self._claim_is_active(task_id)
        except RecoveryCorruptionError:
            return self._decision(
                checkpoint,
                RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CLAIM_LOCK_BINDING_CORRUPT",
            )
        if claim_is_active:
            return self._decision(
                checkpoint, RecoveryClassification.RECOVERY_IN_PROGRESS,
                RecoveryDirective.NO_ACTION, "RECOVERY_ACTIVE_CLAIM",
            )

        anchor = next(
            (
                item for item in records
                if item.get("event_id") == checkpoint.latest_provenance_event_id
            ),
            None,
        )
        prepared = next(
            (
                item for item in reversed(records)
                if item.get("event_type") == "TASK_CHECKPOINT_PREPARED"
                and item.get("checkpoint_event_id")
                == checkpoint.latest_provenance_event_id
            ),
            None,
        )
        if anchor is None:
            if (
                prepared is not None
                and prepared.get("checkpoint_hash") == checkpoint.checkpoint_hash
                and prepared.get("checkpoint_version") == checkpoint.checkpoint_version
            ):
                return self._decision(
                    checkpoint, RecoveryClassification.SAFE_TO_RESUME,
                    RecoveryDirective.RECONCILE_CHECKPOINT,
                    "RECOVERY_CHECKPOINT_EVENT_PENDING",
                )
            return self._decision(
                checkpoint, RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CHECKPOINT_UNANCHORED",
            )
        if (
            anchor.get("event_type") != "TASK_CHECKPOINTED"
            or anchor.get("checkpoint_hash") != checkpoint.checkpoint_hash
            or anchor.get("checkpoint_version") != checkpoint.checkpoint_version
            or anchor.get("task_id") != checkpoint.task_id
        ):
            return self._decision(
                checkpoint, RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT",
            )
        if not self._checkpoint_is_latest_committed(checkpoint, records):
            return self._decision(
                checkpoint,
                RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CHECKPOINT_ROLLBACK_DETECTED",
            )

        try:
            record = self._idempotency_record(checkpoint)
        except (PersistenceError, RecoveryCorruptionError, TypeError, ValueError):
            return self._decision(
                checkpoint,
                RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_IDEMPOTENCY_CORRUPT",
            )
        if (
            record is None
            and self._checkpoint_requires_idempotency_record(checkpoint)
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_IDEMPOTENCY_STATE_MISSING",
            )
        terminal_decision = self._terminal_checkpoint_decision(
            checkpoint, record, records
        )
        if terminal_decision is not None:
            return terminal_decision
        if checkpoint.state is TaskState.PAUSED:
            return self._decision(
                checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_MANUAL_REVIEW_REQUIRED",
            )
        state = getattr(getattr(record, "state", None), "value", None)
        terminal_states = {
            "SUCCEEDED", "BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH",
            "FAILED_REPORTED",
        }
        if record is not None:
            matching_events = [
                item for item in records
                if item.get("task_id") == checkpoint.task_id
                and item.get("operation_key") == checkpoint.current_idempotency_key
                and item.get("action_id") == checkpoint.current_action_id
                and item.get("action_fingerprint")
                == checkpoint.current_action_fingerprint
            ]
            has_start = any(
                item.get("event_type") == "ACTION_DISPATCH_STARTED"
                and item.get("task_id") == record.task_id
                and item.get("action_id") == record.action_id
                and item.get("operation_key") == record.operation_key
                and item.get("action_fingerprint") == record.action_fingerprint
                and item.get("dispatched") is True
                for item in matching_events
            )
            terminal = self._matching_terminal_event(
                checkpoint, record, matching_events
            )
            if state in {"SUCCEEDED", "FAILED_REPORTED"} and not has_start:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_TERMINAL_WITHOUT_DISPATCH_START",
                    idempotency_state=state,
                )
            if state in {
                "BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH"
            } and has_start:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT",
                    idempotency_state=state,
                )
            if state in {"DISPATCH_STARTED", "TIMED_OUT_OR_UNKNOWN", "UNKNOWN_OUTCOME"} or (
                has_start and terminal is None and state not in terminal_states
            ):
                return self._decision(
                    checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_ACTION_OUTCOME_UNKNOWN",
                    idempotency_state=state,
                )
            if state in terminal_states and terminal is None:
                return self._decision(
                    checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
                    "RECOVERY_TERMINAL_PROVENANCE_PENDING",
                    idempotency_state=state,
                    requires_trusted_input=False,
                )
            if state in terminal_states and terminal is not None and (
                checkpoint.current_idempotency_state != state
                or checkpoint.phase is not TaskPhase.AFTER_ACTION
                or checkpoint.causal_provenance_event_id != terminal.get("event_id")
            ):
                return self._decision(
                    checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.RECONCILE_CHECKPOINT,
                    "RECOVERY_TASK_CHECKPOINT_PENDING",
                    idempotency_state=state,
                    provenance_event_id=str(terminal.get("event_id")),
                )
            if state == "RESERVED":
                return self._classify_reserved_record(
                    checkpoint, record, records
                )

        if (
            record is None
            and checkpoint.phase is TaskPhase.BEFORE_DISPATCH
        ):
            if self._pristine_read_only_pre_dispatch_proven(
                checkpoint, records
            ):
                return self._decision(
                    checkpoint,
                    RecoveryClassification.SAFE_TO_RESUME,
                    RecoveryDirective.REVALIDATE_ACTION,
                    "RECOVERY_PRE_DISPATCH_ACTION_REQUIRES_REVALIDATION",
                    requires_trusted_input=True,
                )
            if checkpoint.approval_state is ApprovalState.NOT_REQUIRED:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_MANUAL_REVIEW_REQUIRED",
                )

        if checkpoint.phase in {
            TaskPhase.PROVENANCE_DISPATCH_RECORDED,
            TaskPhase.DISPATCH_IN_FLIGHT,
        } or checkpoint.state is TaskState.RECOVERY_REQUIRED:
            return self._decision(
                checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_ACTION_OUTCOME_UNKNOWN", idempotency_state=state,
            )
        if checkpoint.phase is TaskPhase.WAITING_FOR_APPROVAL or checkpoint.approval_state in {
            ApprovalState.WAITING, ApprovalState.GRANTED_IN_PROCESS,
            ApprovalState.FRESH_APPROVAL_REQUIRED,
        }:
            return self._decision(
                checkpoint, RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
                RecoveryDirective.REQUIRE_FRESH_APPROVAL,
                "RECOVERY_FRESH_APPROVAL_REQUIRED", requires_trusted_input=True,
                requires_fresh_approval=True,
            )
        if (
            checkpoint.phase is TaskPhase.TASK_CREATED
            and checkpoint.reason_code == "STANDALONE_ACTION_TASK_CREATED"
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE",
            )
        if (
            checkpoint.phase in {TaskPhase.TASK_CREATED, TaskPhase.BETWEEN_STEPS}
            and checkpoint.step_index == 0
            and self._unrepresented_execution_evidence(checkpoint, records)
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
            )
        if checkpoint.remaining_steps <= 0 and checkpoint.phase in {
            TaskPhase.CREATED if hasattr(TaskPhase, "CREATED") else TaskPhase.TASK_CREATED,
            TaskPhase.BETWEEN_STEPS,
        }:
            return self._decision(
                checkpoint, RecoveryClassification.BLOCKED,
                RecoveryDirective.NO_ACTION, "RECOVERY_STEP_BUDGET_EXHAUSTED",
            )
        if (
            checkpoint.phase is TaskPhase.BEFORE_MODEL_CALL
            and checkpoint.reason_code == "TASK_MODEL_CALL_FAILED"
            and not self._definitive_model_failure(checkpoint, records)
        ):
            return self._decision(
                checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_MODEL_OUTCOME_UNKNOWN",
            )
        model_started = checkpoint.reason_code in {
            "TASK_MODEL_ATTEMPT_STARTED", "TASK_MODEL_CONTINUATION_STARTED"
        }
        if model_started:
            terminal_model = self._model_terminal_evidence(checkpoint, records)
            if terminal_model == "MODEL_CALL_COMPLETED":
                return self._decision(
                    checkpoint,
                    RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_MODEL_OUTPUT_NOT_DURABLE",
                )
            if terminal_model != "MODEL_CALL_FAILED":
                return self._decision(
                    checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_MODEL_OUTCOME_UNKNOWN",
                )
        if (
            checkpoint.phase is TaskPhase.BEFORE_MODEL_CALL
            and checkpoint.step_index > 1
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE",
            )
        if checkpoint.remaining_retry_budget <= 0 and checkpoint.phase is TaskPhase.BEFORE_MODEL_CALL:
            return self._decision(
                checkpoint, RecoveryClassification.BLOCKED,
                RecoveryDirective.NO_ACTION, "RECOVERY_PROVIDER_BUDGET_EXHAUSTED",
            )
        if checkpoint.phase is TaskPhase.AFTER_MODEL_CALL:
            return self._decision(
                checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_MODEL_OUTPUT_NOT_DURABLE",
            )
        if (
            checkpoint.phase is TaskPhase.BETWEEN_STEPS
            and checkpoint.step_index == 0
            and self._request_execution_started(checkpoint, records)
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
            )
        if checkpoint.phase is TaskPhase.BETWEEN_STEPS and checkpoint.step_index > 0:
            try:
                prior_steps_safe = self._between_steps_read_only_proven(
                    checkpoint, records
                )
            except RecoveryCorruptionError:
                return self._decision(
                    checkpoint, RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_CHECKPOINT_CORRUPT",
                )
            if prior_steps_safe:
                return self._decision(
                    checkpoint, RecoveryClassification.SAFE_TO_RESUME,
                    RecoveryDirective.RESUME_MODEL,
                    "RECOVERY_TRUSTED_REQUEST_REQUIRED",
                    requires_trusted_input=True,
                )
            return self._decision(
                checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE",
            )
        if checkpoint.phase in {TaskPhase.TASK_CREATED, TaskPhase.BETWEEN_STEPS, TaskPhase.BEFORE_MODEL_CALL}:
            return self._decision(
                checkpoint, RecoveryClassification.SAFE_TO_RESUME,
                RecoveryDirective.RESUME_MODEL,
                "RECOVERY_TRUSTED_REQUEST_REQUIRED", requires_trusted_input=True,
            )
        return self._decision(
            checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            RecoveryDirective.REQUIRE_OPERATOR_ACK,
            "RECOVERY_MANUAL_REVIEW_REQUIRED",
        )

    def discover(self, *, limit: int = MAX_RECOVERY_DISCOVERY_BATCH) -> RecoveryDiscoveryResult:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RECOVERY_DISCOVERY_LIMIT:
            raise ValueError("recovery discovery limit is outside policy bounds")
        root = self.checkpoint_store.root_dir
        metadata = root.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RecoveryCorruptionError("Task discovery root is unsafe.")
        decisions: list[RecoveryDecision] = []
        malformed = 0
        candidates: list[tuple[str, bool, bool]] = []
        with os.scandir(root) as iterator:
            for entry in iterator:
                candidates.append(
                    (
                        entry.name,
                        entry.is_symlink(),
                        entry.is_dir(follow_symlinks=False),
                    )
                )
                if len(candidates) > limit:
                    break
        if len(candidates) > limit:
            return RecoveryDiscoveryResult(
                decisions=(),
                scanned_count=len(candidates),
                pending_count=0,
                malformed_count=0,
                truncated=True,
                degraded=True,
                reason_code="RECOVERY_DISCOVERY_LIMIT_EXCEEDED",
            )
        for resource_id, is_symlink, is_directory in sorted(candidates):
                if (
                    not _HEX.fullmatch(resource_id)
                    or is_symlink
                    or not is_directory
                ):
                    malformed += 1
                    decisions.append(
                        self._corrupt_decision(
                            None,
                            resource_id if _HEX.fullmatch(resource_id) else "0" * 64,
                            RecoveryClassification.CORRUPT_CHECKPOINT,
                            "RECOVERY_DISCOVERY_RESOURCE_INVALID",
                        )
                    )
                    continue
                try:
                    # Read through the checkpoint store's pinned no-follow
                    # boundary; the directory name alone is never authority.
                    checkpoint = (
                        self.checkpoint_store.load_snapshot_resource_unanchored(
                            resource_id
                        )
                    )
                    if checkpoint is None:
                        raise TaskCheckpointCorruptionError(
                            "Task discovery checkpoint disappeared."
                        )
                    if self._resource_id(checkpoint.task_id) != resource_id:
                        raise TaskCheckpointCorruptionError(
                            "Task directory identity does not match checkpoint."
                        )
                    decisions.append(self.classify(checkpoint.task_id))
                except TaskCheckpointSchemaError:
                    malformed += 1
                    decisions.append(
                        self._corrupt_decision(
                            None, resource_id,
                            RecoveryClassification.UNSUPPORTED_SCHEMA,
                            "RECOVERY_CHECKPOINT_SCHEMA_UNSUPPORTED",
                        )
                    )
                except (PersistenceError, TypeError, ValueError):
                    malformed += 1
                    decisions.append(
                        self._corrupt_decision(
                            None, resource_id,
                            RecoveryClassification.CORRUPT_CHECKPOINT,
                            "RECOVERY_DISCOVERY_CHECKPOINT_INVALID",
                        )
                    )
        pending = sum(
            item.classification not in {
                RecoveryClassification.ALREADY_COMPLETED,
                RecoveryClassification.TERMINAL_NO_RESUME,
                RecoveryClassification.BLOCKED,
                RecoveryClassification.CONFLICT,
            }
            for item in decisions
        )
        return RecoveryDiscoveryResult(
            tuple(decisions), len(candidates), pending, malformed, False,
            False, "RECOVERY_DISCOVERY_COMPLETE",
        )

    def list_incomplete_tasks(
        self, *, limit: int = MAX_RECOVERY_DISCOVERY_BATCH
    ) -> tuple[RecoveryDecision, ...]:
        """Return a bounded metadata-only view of nonterminal recovery work."""

        discovery = self.discover(limit=limit)
        return tuple(
            decision
            for decision in discovery.decisions
            if decision.classification
            not in {
                RecoveryClassification.ALREADY_COMPLETED,
                RecoveryClassification.TERMINAL_NO_RESUME,
                RecoveryClassification.BLOCKED,
                RecoveryClassification.CONFLICT,
            }
        )

    def show(self, task_id: str) -> RecoveryDecision:
        """Return one metadata-only recovery decision without changing state."""

        return self.classify(task_id)

    def bind_trusted_input(
        self,
        task_id: str,
        *,
        request_text: str | None = None,
        action: Mapping[str, Any] | None = None,
    ) -> TrustedResumeInput:
        checkpoint = self._read_checkpoint(task_id)
        if checkpoint is None:
            raise RecoveryInputError("Recovery input has no matching checkpoint.")
        request_hash: str | None = None
        if request_text is not None:
            if not isinstance(request_text, str):
                raise RecoveryInputError("Recovery request candidate is invalid.")
            request_hash = hashlib.sha256(request_text.encode("utf-8")).hexdigest()
            if (
                request_hash != checkpoint.safe_context["request_hash"]
                or len(request_text) != checkpoint.safe_context["request_length"]
            ):
                raise RecoveryInputError("Recovery request digest does not match.")
        fingerprint: str | None = None
        safe_action: Mapping[str, Any] | None = None
        if action is not None:
            from runtime.tools.capability_policy import evaluate_action_policy
            from runtime.tools.idempotency import canonical_action_fingerprint
            from runtime.tools.validator import validate_action

            safe_action = validate_action(strip_untrusted_identity_fields(dict(action)))
            try:
                encoded_action = _canonical_json(safe_action).encode("utf-8")
            except (TypeError, ValueError, UnicodeError) as exc:
                raise RecoveryInputError("Recovery action is not bounded JSON.") from exc
            if len(encoded_action) > MAX_TRUSTED_ACTION_BYTES:
                raise RecoveryInputError("Recovery action exceeds its memory bound.")
            decision = evaluate_action_policy(safe_action)
            fingerprint = canonical_action_fingerprint(
                safe_action,
                project_dir=self.project_dir,
                capability_class=decision.capability_class,
            )
            if (
                checkpoint.current_action_name != safe_action.get("action")
                or checkpoint.current_action_fingerprint != fingerprint
                or checkpoint.current_capability_class != decision.capability_class.value
            ):
                raise RecoveryInputError("Recovery action digest does not match.")
        if request_text is None and action is None:
            raise RecoveryInputError("Recovery input contains no trusted candidate.")
        nonce = uuid.uuid4().hex
        capability = TrustedResumeInput(
            task_id=task_id,
            checkpoint_hash=checkpoint.checkpoint_hash,
            request_hash=request_hash,
            action_fingerprint=fingerprint,
            request_text=request_text,
            action=safe_action,
            nonce=nonce,
        )
        with self._trusted_lock:
            if len(self._trusted_inputs) >= MAX_TRUSTED_RESUME_INPUTS:
                raise RecoveryInputError(
                    "Recovery trusted-input registry reached its bound."
                )
            self._trusted_inputs[nonce] = capability
        return capability

    def consume_trusted_input(
        self, task_id: str, capability: TrustedResumeInput
    ) -> TaskCheckpoint:
        if not isinstance(capability, TrustedResumeInput) or capability.task_id != task_id:
            raise RecoveryInputError("Recovery input is not runtime-owned.")
        with self._trusted_lock:
            authoritative = self._trusted_inputs.pop(capability._nonce, None)
        if authoritative is not capability:
            raise RecoveryInputError("Recovery input capability is absent or forged.")
        checkpoint = self._read_checkpoint(task_id)
        if checkpoint is None or checkpoint.checkpoint_hash != capability.checkpoint_hash:
            raise RecoveryInputError("Recovery input is stale.")
        request_candidate = authoritative.request_text
        if request_candidate is not None:
            if not isinstance(request_candidate, str):
                raise RecoveryInputError("Recovery request capability was altered.")
            request_hash = hashlib.sha256(
                request_candidate.encode("utf-8")
            ).hexdigest()
            if (
                request_hash != authoritative.request_hash
                or request_hash != checkpoint.safe_context["request_hash"]
                or len(request_candidate)
                != checkpoint.safe_context["request_length"]
            ):
                raise RecoveryInputError("Recovery request capability was altered.")
        try:
            action_candidate = authoritative.action
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RecoveryInputError(
                "Recovery action capability was altered."
            ) from exc
        if action_candidate is not None:
            from runtime.tools.capability_policy import evaluate_action_policy
            from runtime.tools.idempotency import canonical_action_fingerprint
            from runtime.tools.validator import validate_action

            try:
                encoded_action = _canonical_json(action_candidate).encode("utf-8")
            except (TypeError, ValueError, UnicodeError) as exc:
                raise RecoveryInputError(
                    "Recovery action capability was altered."
                ) from exc
            if len(encoded_action) > MAX_TRUSTED_ACTION_BYTES:
                raise RecoveryInputError("Recovery action capability was altered.")
            safe_action = validate_action(
                strip_untrusted_identity_fields(action_candidate)
            )
            decision = evaluate_action_policy(safe_action)
            fingerprint = canonical_action_fingerprint(
                safe_action,
                project_dir=self.project_dir,
                capability_class=decision.capability_class,
            )
            if (
                fingerprint != authoritative.action_fingerprint
                or checkpoint.current_action_name != safe_action.get("action")
                or checkpoint.current_action_fingerprint != fingerprint
                or checkpoint.current_capability_class
                != decision.capability_class.value
            ):
                raise RecoveryInputError("Recovery action capability was altered.")
        if request_candidate is None and action_candidate is None:
            raise RecoveryInputError("Recovery input capability has no candidate.")
        return checkpoint

    validate_trusted_input = consume_trusted_input

    def _require_dispatcher(self) -> TrustedRecoveryDispatcher:
        dispatcher = self._dispatcher
        if dispatcher is None:
            raise RecoveryInputError(
                "Recovery execution requires the runtime-injected dispatcher."
            )
        return dispatcher

    @staticmethod
    def _trace_for_token(token: RecoveryExecutionToken) -> TraceContext:
        return TraceContext(
            request_id=token.request_id,
            trace_id=token.trace_id,
            task_id=token.task_id,
        )

    def _operator_result(
        self,
        token: RecoveryExecutionToken,
        decision: RecoveryDecision,
        checkpoint: TaskCheckpoint,
        *,
        status: RecoveryOperationStatus,
    ) -> RecoveryOperationResult:
        return RecoveryOperationResult(
            task_id=checkpoint.task_id,
            recovery_attempt_id=token.recovery_attempt_id,
            request_id=token.request_id,
            trace_id=token.trace_id,
            classification=decision.classification,
            directive=decision.directive,
            status=status,
            success=status is RecoveryOperationStatus.COMPLETED,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
        )

    def _prepare_model_resume(
        self,
        checkpoint: TaskCheckpoint,
        token: RecoveryExecutionToken,
    ) -> tuple[TaskCheckpoint, StepReservation | None]:
        """Bind recovery identity without minting any execution budget."""

        # Revalidate the active fenced owner immediately before the durable edge.
        self.classify_under_claim(checkpoint.task_id, token)
        if checkpoint.phase is TaskPhase.BEFORE_MODEL_CALL:
            if checkpoint.step_index <= 0:
                raise RecoveryCorruptionError(
                    "Before-model recovery lacks an already-debited task step."
                )
            reservation = (
                self.checkpoint_store.remint_step_reservation_for_recovery(
                    checkpoint.task_id,
                    recovery_token=token,
                )
            )
            reminted = self._read_checkpoint(checkpoint.task_id)
            if reminted is None:
                raise RecoveryCorruptionError(
                    "Recovery step remint lost its durable checkpoint."
                )
            return reminted, reservation
        if checkpoint.phase is TaskPhase.BETWEEN_STEPS:
            prepared = self.checkpoint_store.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.BETWEEN_STEPS,
                reason_code="TASK_RECOVERY_RESUME_PREPARED",
                latest_request_id=token.request_id,
                latest_trace_id=token.trace_id,
                recovery_attempt_id=token.recovery_attempt_id,
                approval_state=ApprovalState.NOT_APPLICABLE,
            )
            return prepared, None
        if (
            checkpoint.state is TaskState.CREATED
            and checkpoint.phase is TaskPhase.TASK_CREATED
        ):
            # Bind the new operator invocation and recovery attempt before the
            # dispatcher can perform any provider work.  The normal runtime
            # start helper observes the already-running task and therefore
            # cannot accidentally drop recovery causation from the checkpoint.
            prepared = self.checkpoint_store.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.BETWEEN_STEPS,
                reason_code="TASK_STARTED",
                latest_request_id=token.request_id,
                latest_trace_id=token.trace_id,
                recovery_attempt_id=token.recovery_attempt_id,
                approval_state=ApprovalState.NOT_APPLICABLE,
            )
            return prepared, None
        raise RecoveryFencedError(
            "Recovery model dispatch is not at an explicit safe boundary."
        )

    def _validate_failed_model_remint(
        self,
        token: RecoveryExecutionToken,
        checkpoint: TaskCheckpoint,
    ) -> None:
        """Narrowly authorize remint after a durably failed provider attempt."""

        decision = self.classify_under_claim(checkpoint.task_id, token)
        if (
            checkpoint.checkpoint_hash != token.checkpoint_hash
            or checkpoint.phase is not TaskPhase.BEFORE_MODEL_CALL
            or checkpoint.reason_code
            not in {
                "TASK_MODEL_ATTEMPT_STARTED",
                "TASK_MODEL_CONTINUATION_STARTED",
            }
            or decision.classification is not RecoveryClassification.SAFE_TO_RESUME
            or decision.directive is not RecoveryDirective.RESUME_MODEL
        ):
            raise RecoveryFencedError(
                "Recovery step remint lacks an exact failed-model decision."
            )
        records = self.provenance_store.read_runtime_all()
        if self._model_terminal_evidence(checkpoint, records) != "MODEL_CALL_FAILED":
            raise RecoveryFencedError(
                "Recovery step remint lacks terminal provider-failure proof."
            )

    def _close_recovery_reservation(
        self, reservation: StepReservation | None
    ) -> None:
        if reservation is None:
            return
        try:
            self.checkpoint_store.close_step_reservation(reservation)
        except TaskStepReservationError:
            # A conforming dispatcher consumes or closes the opaque proof.
            return

    def resume(
        self,
        task_id: str,
        trusted_input: TrustedResumeInput,
    ) -> RecoveryOperationResult:
        """Resume one exactly classified task through the injected dispatcher."""

        # Consume the process-local capability before every other fallible
        # operator check.  A terminal/stale/policy-changed request must not
        # leave a replayable entry in the bounded trusted-input registry.
        checkpoint = self.consume_trusted_input(task_id, trusted_input)
        dispatcher = self._require_dispatcher()
        initial = self.show(task_id)
        if initial.classification not in {
            RecoveryClassification.SAFE_TO_RESUME,
            RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
        } or initial.directive not in {
            RecoveryDirective.RESUME_MODEL,
            RecoveryDirective.REVALIDATE_ACTION,
            RecoveryDirective.REQUIRE_FRESH_APPROVAL,
        }:
            raise RecoveryInputError(
                "Recovery decision does not authorize executable resume work."
            )
        if checkpoint.checkpoint_hash != initial.checkpoint_hash:
            raise RecoveryInputError("Recovery decision became stale before resume.")
        request_candidate = trusted_input.request_text
        action_candidate = trusted_input.action
        if initial.directive is RecoveryDirective.RESUME_MODEL:
            if request_candidate is None or action_candidate is not None:
                raise RecoveryInputError(
                    "Model recovery requires only the exact trusted request."
                )
        elif action_candidate is None or request_candidate is not None:
            raise RecoveryInputError(
                "Action recovery requires only the exact trusted action."
            )

        with self.execution_guard(
            task_id,
            purpose=RecoveryPurpose.RECOVERY,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            current = self._read_checkpoint(task_id)
            if current is None:
                raise RecoveryCorruptionError("Recovery checkpoint disappeared.")
            decision = self.classify_under_claim(task_id, token)
            if (
                decision.classification != initial.classification
                or decision.directive != initial.directive
                or decision.checkpoint_hash != checkpoint.checkpoint_hash
            ):
                raise RecoveryClaimConflictError(
                    "Recovery classification changed under the exact claim."
                )
            self._append_recovery_event(
                "RECOVERY_DECISION", token, current, decision
            )
            trace = self._trace_for_token(token)
            reservation: StepReservation | None = None
            try:
                if decision.directive is RecoveryDirective.RESUME_MODEL:
                    current, reservation = self._prepare_model_resume(
                        current, token
                    )
                self._append_recovery_event(
                    "RECOVERY_RESUME_STARTED", token, current, decision
                )
                with self._dispatch_authorization_scope(
                    token,
                    decision.directive,
                ):
                    if decision.directive is RecoveryDirective.RESUME_MODEL:
                        dispatched = dispatcher.resume_model(
                            request_candidate or "",
                            trace_context=trace,
                            step_reservation=reservation,
                            recovery_token=token,
                        )
                    elif decision.idempotency_state == "RESERVED":
                        dispatched = dispatcher.resume_reserved_action(
                            action_candidate or {},
                            trace_context=trace,
                            recovery_token=token,
                        )
                    else:
                        dispatched = dispatcher.resume_waiting_action(
                            action_candidate or {},
                            trace_context=trace,
                            recovery_token=token,
                        )
                if not isinstance(dispatched, Mapping):
                    raise RecoveryCorruptionError(
                        "Trusted recovery dispatcher returned an invalid result."
                    )
                final_checkpoint = self.checkpoint_store.load(task_id)
                if final_checkpoint is None:
                    raise RecoveryCorruptionError(
                        "Recovery dispatcher lost the task checkpoint."
                    )
                succeeded = dispatched.get("success") is True
                if succeeded and (
                    final_checkpoint.state not in TERMINAL_TASK_STATES
                    or final_checkpoint.phase is not TaskPhase.TERMINAL
                ):
                    raise RecoveryCorruptionError(
                        "Successful recovery dispatch lacks terminal durable task truth."
                    )
            except BaseException as error:
                failed_checkpoint = self._read_checkpoint(task_id) or current
                try:
                    self._append_recovery_event(
                        "RECOVERY_FAILED",
                        token,
                        failed_checkpoint,
                        decision,
                        terminal=True,
                        success=False,
                    )
                except BaseException as terminal_error:
                    error.add_note(
                        "Recovery failure provenance also failed; secondary "
                        f"failure type: {type(terminal_error).__name__}."
                    )
                raise
            finally:
                self._close_recovery_reservation(reservation)
            self._append_recovery_event(
                "RECOVERY_COMPLETED" if succeeded else "RECOVERY_FAILED",
                token,
                final_checkpoint,
                decision,
                terminal=True,
                success=succeeded,
            )
            return self._operator_result(
                token,
                decision,
                final_checkpoint,
                status=(
                    RecoveryOperationStatus.COMPLETED
                    if succeeded
                    else RecoveryOperationStatus.FAILED
                ),
            )

    def _cancellation_decision(
        self,
        checkpoint: TaskCheckpoint,
        classified: RecoveryDecision,
    ) -> RecoveryDecision:
        has_action = checkpoint.current_action_id is not None
        if classified.classification is RecoveryClassification.SAFE_TO_RESUME:
            reason = (
                "RECOVERY_SAFE_ACTION_CANCEL_REQUESTED"
                if has_action
                else "RECOVERY_SAFE_TASK_CANCEL_REQUESTED"
            )
        elif (
            classified.classification
            is RecoveryClassification.WAITING_FOR_FRESH_APPROVAL
            and has_action
        ):
            reason = "RECOVERY_WAITING_ACTION_CANCEL_REQUESTED"
        else:
            raise RecoveryInputError(
                "Only safe, non-uncertain recovery work can be cancelled."
            )
        return self._decision(
            checkpoint,
            classified.classification,
            RecoveryDirective.CANCEL_TASK,
            reason,
            idempotency_state=classified.idempotency_state,
            requires_trusted_input=False,
            requires_fresh_approval=False,
        )

    def cancel(self, task_id: str) -> RecoveryOperationResult:
        """Cancel only work proven not to have an uncertain external outcome."""

        initial = self.show(task_id)
        if initial.classification in {
            RecoveryClassification.UNKNOWN_OUTCOME,
            RecoveryClassification.CORRUPT_CHECKPOINT,
            RecoveryClassification.UNSUPPORTED_SCHEMA,
            RecoveryClassification.RECOVERY_IN_PROGRESS,
        }:
            raise RecoveryInputError(
                "Uncertain recovery work can only be acknowledged for manual review."
            )
        checkpoint = self._read_checkpoint(task_id)
        if checkpoint is None or checkpoint.checkpoint_hash != initial.checkpoint_hash:
            raise RecoveryInputError("Cancellation lacks an exact valid checkpoint.")
        cancellation = self._cancellation_decision(checkpoint, initial)
        dispatcher: TrustedRecoveryDispatcher | None = None
        if checkpoint.current_action_id is not None:
            dispatcher = self._require_dispatcher()

        with self.execution_guard(
            task_id,
            purpose=RecoveryPurpose.OPERATOR,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            current = self._read_checkpoint(task_id)
            if current is None:
                raise RecoveryCorruptionError("Cancellation checkpoint disappeared.")
            classified = self.classify_under_claim(task_id, token)
            decision = self._cancellation_decision(current, classified)
            self._append_recovery_event(
                "RECOVERY_DECISION", token, current, decision
            )
            try:
                if current.current_action_id is not None:
                    assert dispatcher is not None
                    with self._dispatch_authorization_scope(
                        token,
                        RecoveryDirective.CANCEL_TASK,
                    ):
                        result = dispatcher.cancel_recoverable_action(
                            trace_context=self._trace_for_token(token),
                            recovery_token=token,
                        )
                    if not isinstance(result, Mapping):
                        raise RecoveryCorruptionError(
                            "Trusted cancellation dispatcher returned an invalid result."
                        )
                    final_checkpoint = self._read_checkpoint(task_id)
                    if (
                        final_checkpoint is None
                        or final_checkpoint.state is not TaskState.CANCELLED
                    ):
                        raise RecoveryCorruptionError(
                            "Action cancellation did not persist a cancelled outcome."
                        )
                else:
                    final_checkpoint = self.checkpoint_store.transition(
                        task_id,
                        expected_version=current.checkpoint_version,
                        state=TaskState.CANCELLED,
                        phase=TaskPhase.TERMINAL,
                        reason_code="TASK_CANCELLED",
                        latest_request_id=token.request_id,
                        latest_trace_id=token.trace_id,
                        recovery_attempt_id=token.recovery_attempt_id,
                        approval_state=ApprovalState.DENIED,
                    )
            except BaseException as error:
                failed_checkpoint = self._read_checkpoint(task_id) or current
                try:
                    self._append_recovery_event(
                        "RECOVERY_FAILED", token, failed_checkpoint, decision,
                        terminal=True, success=False,
                    )
                except BaseException as terminal_error:
                    error.add_note(
                        "Cancellation failure provenance also failed; secondary "
                        f"failure type: {type(terminal_error).__name__}."
                    )
                raise
            self._append_recovery_event(
                "RECOVERY_CANCELLED", token, final_checkpoint, decision,
                terminal=True, success=False,
            )
            return self._operator_result(
                token,
                decision,
                final_checkpoint,
                status=RecoveryOperationStatus.CANCELLED,
            )

    def acknowledge_manual_review(
        self, task_id: str
    ) -> RecoveryOperationResult:
        """Record operator awareness without changing or resolving the outcome."""

        initial = self.show(task_id)
        if (
            initial.directive is not RecoveryDirective.REQUIRE_OPERATOR_ACK
            or initial.checkpoint_hash is None
        ):
            raise RecoveryInputError(
                "Task classification does not accept manual-review acknowledgement."
            )
        with self.execution_guard(
            task_id,
            purpose=RecoveryPurpose.OPERATOR,
            expected_checkpoint_hash=initial.checkpoint_hash,
        ) as token:
            checkpoint = self._read_checkpoint(task_id)
            if checkpoint is None:
                raise RecoveryCorruptionError(
                    "Manual-review checkpoint disappeared."
                )
            decision = self.classify_under_claim(task_id, token)
            if decision.directive is not RecoveryDirective.REQUIRE_OPERATOR_ACK:
                raise RecoveryClaimConflictError(
                    "Manual-review classification changed under claim."
                )
            before = (
                checkpoint.state,
                checkpoint.phase,
                checkpoint.checkpoint_version,
                checkpoint.checkpoint_hash,
            )
            self._append_recovery_event(
                "RECOVERY_DECISION", token, checkpoint, decision
            )
            self._append_recovery_event(
                "RECOVERY_ACKNOWLEDGED", token, checkpoint, decision,
                terminal=True, success=False,
            )
            unchanged = self._read_checkpoint(task_id)
            if unchanged is None or (
                unchanged.state,
                unchanged.phase,
                unchanged.checkpoint_version,
                unchanged.checkpoint_hash,
            ) != before:
                raise RecoveryCorruptionError(
                    "Manual acknowledgement changed canonical task truth."
                )
            return self._operator_result(
                token,
                decision,
                unchanged,
                status=RecoveryOperationStatus.ACKNOWLEDGED,
            )

    def _acquire_claim(
        self,
        task_id: str,
        purpose: RecoveryPurpose,
        *,
        expected_checkpoint_hash: str | None,
        execution_lock_identity: tuple[int, int],
        _resources: _RecoveryResources | None = None,
    ) -> RecoveryClaim:
        if _resources is None:
            with self._open_recovery_resources() as resources:
                return self._acquire_claim(
                    task_id,
                    purpose,
                    expected_checkpoint_hash=expected_checkpoint_hash,
                    execution_lock_identity=execution_lock_identity,
                    _resources=resources,
                )
        self._validate_recovery_resources(_resources)
        if expected_checkpoint_hash is not None and not _HEX.fullmatch(
            expected_checkpoint_hash
        ):
            raise RecoveryClaimConflictError("Expected checkpoint hash is invalid.")
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.UTC)
        now = now.astimezone(dt.UTC)
        owner_id = f"recovery_owner_{uuid.uuid4().hex}"
        attempt_id = f"recovery_attempt_{uuid.uuid4().hex}"
        path = self.claim_path(task_id)

        def update(current: Any | None) -> tuple[dict[str, Any], RecoveryClaim]:
            generation = 1
            if current is not None:
                existing = RecoveryClaim.from_payload(current)
                if existing.task_id != task_id or existing.project_scope != self.project_scope:
                    raise RecoveryCorruptionError("Recovery claim identity conflicts.")
                if (
                    existing.execution_lock_device,
                    existing.execution_lock_inode,
                ) != execution_lock_identity:
                    raise RecoveryCorruptionError(
                        "Recovery execution lock binding changed."
                    )
                if (
                    existing.status is RecoveryClaimStatus.ACTIVE
                    and _parse_timestamp(existing.lease_expires_at) > now
                ):
                    raise RecoveryInProgressError("A valid recovery claim is active.")
                generation = existing.generation + 1
            candidate = RecoveryClaim(
                schema_version=RECOVERY_CLAIM_SCHEMA_VERSION,
                task_id=task_id,
                project_scope=self.project_scope,
                generation=generation,
                status=RecoveryClaimStatus.ACTIVE,
                purpose=purpose,
                owner_id=owner_id,
                recovery_attempt_id=attempt_id,
                claimed_at=_timestamp(now),
                lease_expires_at=_timestamp(
                    now + dt.timedelta(seconds=self.lease_seconds)
                ),
                released_at=None,
                checkpoint_version=None,
                checkpoint_hash=None,
                execution_lock_device=execution_lock_identity[0],
                execution_lock_inode=execution_lock_identity[1],
                reason_code="RECOVERY_CLAIM_ACQUIRED",
                claim_hash="0" * 64,
            ).with_hash()
            candidate.validate()
            return candidate.to_payload(), candidate

        claim = locked_update_json(
            path,
            update,
            lock_path=self.claim_lock_path(task_id),
            lock_timeout_seconds=self.lock_timeout_seconds,
            sort_keys=True,
            trailing_newline=True,
            reject_duplicate_keys=True,
            maximum_bytes=MAX_RECOVERY_CLAIM_BYTES,
            expected_parent_identity=self._claim_scope_identity,
            parent_directory_descriptor=_resources.claim_scope_descriptor,
            directory_identity_validator=lambda: (
                self._validate_recovery_resources(_resources)
            ),
            lock_parent_directory_descriptor=(
                _resources.claim_scope_descriptor
            ),
            lock_directory_identity_validator=lambda: (
                self._validate_recovery_resources(_resources)
            ),
        )
        return claim

    def _bind_claim_checkpoint(
        self,
        claim: RecoveryClaim,
        checkpoint: TaskCheckpoint,
        *,
        _resources: _RecoveryResources | None = None,
    ) -> RecoveryClaim:
        if _resources is None:
            with self._open_recovery_resources() as resources:
                return self._bind_claim_checkpoint(
                    claim, checkpoint, _resources=resources
                )
        self._validate_recovery_resources(_resources)
        if checkpoint.checkpoint_hash != claim.checkpoint_hash and claim.checkpoint_hash is not None:
            raise RecoveryClaimConflictError("Recovery claim checkpoint changed.")
        path = self.claim_path(claim.task_id)

        def update(current: Any | None) -> tuple[dict[str, Any], RecoveryClaim]:
            existing = RecoveryClaim.from_payload(current)
            if (
                existing.status is not RecoveryClaimStatus.ACTIVE
                or existing.generation != claim.generation
                or existing.owner_id != claim.owner_id
                or existing.recovery_attempt_id != claim.recovery_attempt_id
            ):
                raise RecoveryFencedError("Recovery claim was fenced before binding.")
            bound = replace(
                existing,
                checkpoint_version=checkpoint.checkpoint_version,
                checkpoint_hash=checkpoint.checkpoint_hash,
                claim_hash="0" * 64,
            ).with_hash()
            bound.validate()
            return bound.to_payload(), bound

        return locked_update_json(
            path, update,
            lock_path=self.claim_lock_path(claim.task_id),
            lock_timeout_seconds=self.lock_timeout_seconds,
            sort_keys=True, trailing_newline=True, reject_duplicate_keys=True,
            maximum_bytes=MAX_RECOVERY_CLAIM_BYTES,
            expected_parent_identity=self._claim_scope_identity,
            parent_directory_descriptor=_resources.claim_scope_descriptor,
            directory_identity_validator=lambda: (
                self._validate_recovery_resources(_resources)
            ),
            lock_parent_directory_descriptor=(
                _resources.claim_scope_descriptor
            ),
            lock_directory_identity_validator=lambda: (
                self._validate_recovery_resources(_resources)
            ),
        )

    def _release_claim(
        self,
        token: RecoveryExecutionToken,
        *,
        _resources: _RecoveryResources | None = None,
    ) -> RecoveryClaim:
        if _resources is None:
            with self._open_recovery_resources() as resources:
                return self._release_claim(token, _resources=resources)
        self._validate_recovery_resources(_resources)
        with self._active_lock:
            execution_lock = self._active_execution_locks.get(token.task_id)
            if (
                self._active_tokens.get(token.task_id) is not token
                or execution_lock is None
                or token._owner_process_id != os.getpid()
                or token._owner_thread_id != threading.get_ident()
            ):
                raise RecoveryFencedError(
                    "Only the active owner process and thread can release a claim."
                )
        try:
            lock_identity = execution_lock.validate_binding()
        except PersistenceError as exc:
            raise RecoveryFencedError(
                "Recovery execution lock binding changed before release."
            ) from exc
        if lock_identity != (
            token.execution_lock_device,
            token.execution_lock_inode,
        ):
            raise RecoveryFencedError(
                "Recovery token execution lock identity was fenced."
            )
        path = self.claim_path(token.task_id)
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=dt.UTC)

        def update(current: Any | None) -> tuple[dict[str, Any], RecoveryClaim]:
            existing = RecoveryClaim.from_payload(current)
            if (
                existing.status is not RecoveryClaimStatus.ACTIVE
                or existing.generation != token.generation
                or existing.owner_id != token.owner_id
                or existing.recovery_attempt_id != token.recovery_attempt_id
                or existing.execution_lock_device
                != token.execution_lock_device
                or existing.execution_lock_inode != token.execution_lock_inode
            ):
                raise RecoveryFencedError("Stale recovery owner cannot release a claim.")
            released = replace(
                existing,
                status=RecoveryClaimStatus.RELEASED,
                released_at=_timestamp(now),
                reason_code="RECOVERY_CLAIM_RELEASED",
                claim_hash="0" * 64,
            ).with_hash()
            released.validate()
            return released.to_payload(), released

        return locked_update_json(
            path, update,
            lock_path=self.claim_lock_path(token.task_id),
            lock_timeout_seconds=self.lock_timeout_seconds,
            sort_keys=True, trailing_newline=True, reject_duplicate_keys=True,
            maximum_bytes=MAX_RECOVERY_CLAIM_BYTES,
            expected_parent_identity=self._claim_scope_identity,
            parent_directory_descriptor=_resources.claim_scope_descriptor,
            directory_identity_validator=lambda: (
                self._validate_recovery_resources(_resources)
            ),
            lock_parent_directory_descriptor=(
                _resources.claim_scope_descriptor
            ),
            lock_directory_identity_validator=lambda: (
                self._validate_recovery_resources(_resources)
            ),
        )

    def _append_recovery_event(
        self,
        event_type: str,
        token: RecoveryExecutionToken,
        checkpoint: TaskCheckpoint,
        decision: RecoveryDecision,
        *,
        terminal: bool = False,
        success: bool | None = None,
    ) -> None:
        module = self._provenance_module()
        event_class = getattr(module, "RuntimeProvenanceEvent")
        now = self._clock()
        event = event_class(
            event_id=_event_id(
                "AOIA_RECOVERY", token.task_id, token.generation, event_type
            ),
            timestamp_utc=_timestamp(now),
            event_type=event_type,
            task_id=token.task_id,
            request_id=token.request_id,
            trace_id=token.trace_id,
            project_scope=token.project_scope,
            recovery_attempt_id=token.recovery_attempt_id,
            recovery_generation=token.generation,
            recovery_classification=decision.classification.value,
            recovery_directive=decision.directive.value,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            success=success,
            reason_code={
                "RECOVERY_CLAIMED": "RECOVERY_CLAIM_ACQUIRED",
                "RECOVERY_DECISION": "RECOVERY_DECISION_RECORDED",
                "RECOVERY_RESUME_STARTED": "RECOVERY_RESUME_STARTED",
                "RECOVERY_COMPLETED": "RECOVERY_COMPLETED",
                "RECOVERY_FAILED": "RECOVERY_FAILED",
                "RECOVERY_ACKNOWLEDGED": "RECOVERY_MANUAL_ACKNOWLEDGED",
                "RECOVERY_CANCELLED": "RECOVERY_CANCELLED",
            }[event_type],
        )
        if terminal:
            self.provenance_store.append_terminal_event(event)
        else:
            self.provenance_store.append_runtime_event(event)

    @contextmanager
    def _task_execution_lock(
        self,
        task_id: str,
        resources: _RecoveryResources,
    ) -> Iterator[InterProcessFileLock]:
        """Translate only contention on the per-task owner lock."""

        lock = InterProcessFileLock(
            self.execution_lock_path(task_id),
            timeout_seconds=self.lock_timeout_seconds,
            parent_directory_descriptor=(
                resources.execution_scope_descriptor
            ),
            directory_identity_validator=lambda: (
                self._validate_recovery_resources(resources)
            ),
        )
        try:
            acquired = lock.__enter__()
        except StateLockTimeoutError as exc:
            error = RecoveryInProgressError(
                "Another process already owns recovery for this task."
            )
            raise error.attach_correlation({"task_id": task_id}) from exc
        try:
            yield acquired
        finally:
            lock.__exit__(None, None, None)

    @contextmanager
    def execution_guard(
        self,
        task_id: str,
        *,
        purpose: RecoveryPurpose = RecoveryPurpose.RECOVERY,
        expected_checkpoint_hash: str | None = None,
        existing_token: RecoveryExecutionToken | None = None,
    ) -> Iterator[RecoveryExecutionToken]:
        self._ensure_roots()
        with self._active_lock:
            nested = self._active_tokens.get(task_id)
        if existing_token is not None:
            if (
                nested is not existing_token
                or existing_token.task_id != task_id
                or existing_token.project_scope != self.project_scope
                or existing_token._owner_process_id != os.getpid()
                or existing_token._owner_thread_id != threading.get_ident()
            ):
                raise RecoveryFencedError(
                    "Nested recovery guard requires its exact owner-thread token."
                )
            self.classify_under_claim(task_id, existing_token)
            yield existing_token
            return
        if nested is not None:
            raise RecoveryInProgressError(
                "Recovery task already has an active in-process owner."
            )
        with self._open_recovery_resources() as resources:
            with self._task_execution_lock(
                task_id, resources
            ) as execution_lock:
                token: RecoveryExecutionToken | None = None
                primary_error: BaseException | None = None
                try:
                    claim = self._acquire_claim(
                        task_id,
                        RecoveryPurpose(getattr(purpose, "value", purpose)),
                        expected_checkpoint_hash=expected_checkpoint_hash,
                        execution_lock_identity=execution_lock.validate_binding(),
                        _resources=resources,
                    )
                    trace = TraceContext.new_request(TaskContext(task_id))
                    token = RecoveryExecutionToken(
                        claim, trace, uuid.uuid4().hex, self
                    )
                    with self._active_lock:
                        self._active_tokens[task_id] = token
                        self._active_execution_locks[task_id] = execution_lock
                    checkpoint = self._read_checkpoint(task_id)
                    if checkpoint is None:
                        raise RecoveryCorruptionError(
                            "Recovery checkpoint is missing."
                        )
                    if (
                        expected_checkpoint_hash is not None
                        and checkpoint.checkpoint_hash
                        != expected_checkpoint_hash
                    ):
                        raise RecoveryClaimConflictError(
                            "Recovery checkpoint changed before claim."
                        )
                    claim = self._bind_claim_checkpoint(
                        claim, checkpoint, _resources=resources
                    )
                    bound_token = RecoveryExecutionToken(
                        claim, trace, uuid.uuid4().hex, self
                    )
                    with self._active_lock:
                        if self._active_tokens.get(task_id) is not token:
                            raise RecoveryFencedError(
                                "Recovery owner changed before checkpoint binding."
                            )
                        self._active_tokens[task_id] = bound_token
                    token = bound_token
                    decision = self.classify_under_claim(task_id, token)
                    self._append_recovery_event(
                        "RECOVERY_CLAIMED", token, checkpoint, decision
                    )
                    yield token
                except BaseException as exc:
                    primary_error = exc
                    raise
                finally:
                    release_error: BaseException | None = None
                    if token is not None:
                        try:
                            self._release_claim(
                                token, _resources=resources
                            )
                        except BaseException as exc:
                            release_error = exc
                        finally:
                            with self._active_lock:
                                if self._active_tokens.get(task_id) is token:
                                    del self._active_tokens[task_id]
                                if (
                                    self._active_execution_locks.get(task_id)
                                    is execution_lock
                                ):
                                    del self._active_execution_locks[task_id]
                    if release_error is not None:
                        if primary_error is not None:
                            primary_error.add_note(
                                "Recovery claim release also failed; secondary "
                                "failure type: "
                                f"{type(release_error).__name__}."
                            )
                        else:
                            raise release_error

    def classify_under_claim(
        self, task_id: str, token: RecoveryExecutionToken
    ) -> RecoveryDecision:
        with self._active_lock:
            execution_lock = self._active_execution_locks.get(task_id)
            if (
                self._active_tokens.get(task_id) is not token
                or execution_lock is None
                or token._owner_process_id != os.getpid()
                or token._owner_thread_id != threading.get_ident()
            ):
                raise RecoveryFencedError("Recovery execution token is not active.")
        try:
            lock_identity = execution_lock.validate_binding()
        except PersistenceError as exc:
            raise RecoveryFencedError(
                "Recovery execution lock binding changed."
            ) from exc
        if lock_identity != (
            token.execution_lock_device,
            token.execution_lock_inode,
        ):
            raise RecoveryFencedError(
                "Recovery execution token lock identity was fenced."
            )
        claim = self._read_claim(task_id)
        if (
            claim is None
            or claim.status is not RecoveryClaimStatus.ACTIVE
            or claim.generation != token.generation
            or claim.owner_id != token.owner_id
            or claim.recovery_attempt_id != token.recovery_attempt_id
            or claim.execution_lock_device != token.execution_lock_device
            or claim.execution_lock_inode != token.execution_lock_inode
        ):
            raise RecoveryFencedError("Recovery execution token was fenced.")
        # Temporarily classify without treating this exact claim as a competing owner.
        checkpoint = self._read_checkpoint(task_id)
        if checkpoint is None:
            raise RecoveryCorruptionError("Recovery checkpoint is missing.")
        records = self.provenance_store.read_runtime_all()
        anchor = next(
            (item for item in records if item.get("event_id") == checkpoint.latest_provenance_event_id),
            None,
        )
        if anchor is None:
            prepared = next(
                (
                    item for item in reversed(records)
                    if item.get("event_type") == "TASK_CHECKPOINT_PREPARED"
                    and item.get("checkpoint_event_id") == checkpoint.latest_provenance_event_id
                ),
                None,
            )
            if prepared is not None and prepared.get("checkpoint_hash") == checkpoint.checkpoint_hash:
                return self._decision(
                    checkpoint, RecoveryClassification.SAFE_TO_RESUME,
                    RecoveryDirective.RECONCILE_CHECKPOINT,
                    "RECOVERY_CHECKPOINT_EVENT_PENDING",
                )
            return self._decision(
                checkpoint, RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CHECKPOINT_UNANCHORED",
            )
        # Release-neutral classification: temporarily hide the active-claim branch.
        return self._classify_checkpoint_evidence(checkpoint, records)

    def _classify_checkpoint_evidence(
        self, checkpoint: TaskCheckpoint, records: list[dict[str, Any]]
    ) -> RecoveryDecision:
        # Reuse the public classifier by releasing no state is deliberately avoided.
        # The cases needed for guarded reconciliation are narrower and fail closed.
        if not self._checkpoint_is_latest_committed(checkpoint, records):
            return self._decision(
                checkpoint,
                RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CHECKPOINT_ROLLBACK_DETECTED",
            )
        try:
            record = self._idempotency_record(checkpoint)
        except (PersistenceError, RecoveryCorruptionError, TypeError, ValueError):
            return self._decision(
                checkpoint,
                RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_IDEMPOTENCY_CORRUPT",
            )
        if (
            record is None
            and self._checkpoint_requires_idempotency_record(checkpoint)
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.CORRUPT_CHECKPOINT,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_IDEMPOTENCY_STATE_MISSING",
            )
        terminal_decision = self._terminal_checkpoint_decision(
            checkpoint, record, records
        )
        if terminal_decision is not None:
            return terminal_decision
        if checkpoint.state is TaskState.PAUSED:
            return self._decision(
                checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_MANUAL_REVIEW_REQUIRED",
            )
        state = getattr(getattr(record, "state", None), "value", None)
        if record is not None:
            matching = [
                item for item in records
                if item.get("task_id") == checkpoint.task_id
                and item.get("operation_key") == checkpoint.current_idempotency_key
                and item.get("action_id") == checkpoint.current_action_id
                and item.get("action_fingerprint") == checkpoint.current_action_fingerprint
            ]
            terminal = self._matching_terminal_event(
                checkpoint, record, matching
            )
            has_start = any(
                item.get("event_type") == "ACTION_DISPATCH_STARTED"
                and item.get("task_id") == record.task_id
                and item.get("action_id") == record.action_id
                and item.get("operation_key") == record.operation_key
                and item.get("action_fingerprint") == record.action_fingerprint
                and item.get("dispatched") is True
                for item in matching
            )
            if state in {"SUCCEEDED", "FAILED_REPORTED"} and not has_start:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_TERMINAL_WITHOUT_DISPATCH_START",
                    idempotency_state=state,
                )
            if state in {
                "BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH"
            } and has_start:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT",
                    idempotency_state=state,
                )
            if state in {"DISPATCH_STARTED", "TIMED_OUT_OR_UNKNOWN", "UNKNOWN_OUTCOME"} or (
                has_start
                and terminal is None
                and state
                not in {
                    "SUCCEEDED", "BLOCKED", "CANCELLED",
                    "FAILED_BEFORE_DISPATCH", "FAILED_REPORTED",
                }
            ):
                return self._decision(
                    checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_ACTION_OUTCOME_UNKNOWN", idempotency_state=state,
                )
            if state in {
                "SUCCEEDED", "BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH",
                "FAILED_REPORTED",
            } and terminal is None:
                return self._decision(
                    checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
                    "RECOVERY_TERMINAL_PROVENANCE_PENDING", idempotency_state=state,
                )
            if state in {
                "SUCCEEDED", "BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH",
                "FAILED_REPORTED",
            } and terminal is not None and (
                checkpoint.current_idempotency_state != state
                or checkpoint.phase is not TaskPhase.AFTER_ACTION
                or checkpoint.causal_provenance_event_id != terminal.get("event_id")
            ):
                return self._decision(
                    checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.RECONCILE_CHECKPOINT,
                    "RECOVERY_TASK_CHECKPOINT_PENDING", idempotency_state=state,
                    provenance_event_id=str(terminal.get("event_id")),
                )
            if state == "RESERVED":
                return self._classify_reserved_record(
                    checkpoint, record, records
                )
        if (
            record is None
            and checkpoint.phase is TaskPhase.BEFORE_DISPATCH
        ):
            if self._pristine_read_only_pre_dispatch_proven(
                checkpoint, records
            ):
                return self._decision(
                    checkpoint,
                    RecoveryClassification.SAFE_TO_RESUME,
                    RecoveryDirective.REVALIDATE_ACTION,
                    "RECOVERY_PRE_DISPATCH_ACTION_REQUIRES_REVALIDATION",
                    requires_trusted_input=True,
                )
            if checkpoint.approval_state is ApprovalState.NOT_REQUIRED:
                return self._decision(
                    checkpoint,
                    RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_MANUAL_REVIEW_REQUIRED",
                )
        if checkpoint.phase in {TaskPhase.PROVENANCE_DISPATCH_RECORDED, TaskPhase.DISPATCH_IN_FLIGHT}:
            return self._decision(
                checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_ACTION_OUTCOME_UNKNOWN", idempotency_state=state,
            )
        if checkpoint.state is TaskState.RECOVERY_REQUIRED:
            return self._decision(
                checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_ACTION_OUTCOME_UNKNOWN", idempotency_state=state,
            )
        if checkpoint.phase is TaskPhase.WAITING_FOR_APPROVAL or checkpoint.approval_state in {
            ApprovalState.WAITING,
            ApprovalState.GRANTED_IN_PROCESS,
            ApprovalState.FRESH_APPROVAL_REQUIRED,
        }:
            return self._decision(
                checkpoint, RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
                RecoveryDirective.REQUIRE_FRESH_APPROVAL,
                "RECOVERY_FRESH_APPROVAL_REQUIRED",
                requires_trusted_input=True,
                requires_fresh_approval=True,
            )
        if (
            checkpoint.phase is TaskPhase.TASK_CREATED
            and checkpoint.reason_code == "STANDALONE_ACTION_TASK_CREATED"
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE",
            )
        if (
            checkpoint.phase in {TaskPhase.TASK_CREATED, TaskPhase.BETWEEN_STEPS}
            and checkpoint.step_index == 0
            and self._unrepresented_execution_evidence(checkpoint, records)
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
            )
        if checkpoint.remaining_steps <= 0 and checkpoint.phase in {
            TaskPhase.TASK_CREATED,
            TaskPhase.BETWEEN_STEPS,
        }:
            return self._decision(
                checkpoint, RecoveryClassification.BLOCKED,
                RecoveryDirective.NO_ACTION, "RECOVERY_STEP_BUDGET_EXHAUSTED",
            )
        if (
            checkpoint.phase is TaskPhase.BEFORE_MODEL_CALL
            and checkpoint.reason_code == "TASK_MODEL_CALL_FAILED"
            and not self._definitive_model_failure(checkpoint, records)
        ):
            return self._decision(
                checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_MODEL_OUTCOME_UNKNOWN",
            )
        if checkpoint.reason_code in {
            "TASK_MODEL_ATTEMPT_STARTED",
            "TASK_MODEL_CONTINUATION_STARTED",
        }:
            terminal_model = self._model_terminal_evidence(checkpoint, records)
            if terminal_model == "MODEL_CALL_COMPLETED":
                return self._decision(
                    checkpoint,
                    RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_MODEL_OUTPUT_NOT_DURABLE",
                )
            if terminal_model != "MODEL_CALL_FAILED":
                return self._decision(
                    checkpoint, RecoveryClassification.UNKNOWN_OUTCOME,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_MODEL_OUTCOME_UNKNOWN",
                )
        if (
            checkpoint.phase is TaskPhase.BEFORE_MODEL_CALL
            and checkpoint.step_index > 1
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE",
            )
        if (
            checkpoint.remaining_retry_budget <= 0
            and checkpoint.phase is TaskPhase.BEFORE_MODEL_CALL
        ):
            return self._decision(
                checkpoint, RecoveryClassification.BLOCKED,
                RecoveryDirective.NO_ACTION,
                "RECOVERY_PROVIDER_BUDGET_EXHAUSTED",
            )
        if checkpoint.phase is TaskPhase.AFTER_MODEL_CALL:
            return self._decision(
                checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_MODEL_OUTPUT_NOT_DURABLE",
            )
        if (
            checkpoint.phase is TaskPhase.BETWEEN_STEPS
            and checkpoint.step_index == 0
            and self._request_execution_started(checkpoint, records)
        ):
            return self._decision(
                checkpoint,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
            )
        if checkpoint.phase is TaskPhase.BETWEEN_STEPS and checkpoint.step_index > 0:
            try:
                prior_steps_safe = self._between_steps_read_only_proven(
                    checkpoint, records
                )
            except RecoveryCorruptionError:
                return self._decision(
                    checkpoint, RecoveryClassification.CORRUPT_CHECKPOINT,
                    RecoveryDirective.REQUIRE_OPERATOR_ACK,
                    "RECOVERY_CHECKPOINT_CORRUPT",
                )
            if prior_steps_safe:
                return self._decision(
                    checkpoint, RecoveryClassification.SAFE_TO_RESUME,
                    RecoveryDirective.RESUME_MODEL,
                    "RECOVERY_TRUSTED_REQUEST_REQUIRED",
                    requires_trusted_input=True,
                )
            return self._decision(
                checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                RecoveryDirective.REQUIRE_OPERATOR_ACK,
                "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE",
            )
        if checkpoint.phase in {TaskPhase.TASK_CREATED, TaskPhase.BETWEEN_STEPS, TaskPhase.BEFORE_MODEL_CALL}:
            return self._decision(
                checkpoint, RecoveryClassification.SAFE_TO_RESUME,
                RecoveryDirective.RESUME_MODEL,
                "RECOVERY_TRUSTED_REQUEST_REQUIRED", requires_trusted_input=True,
            )
        return self._decision(
            checkpoint, RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            RecoveryDirective.REQUIRE_OPERATOR_ACK,
            "RECOVERY_MANUAL_REVIEW_REQUIRED",
        )

    def reconcile(self, task_id: str) -> RecoveryDecision:
        initial = self.classify(task_id)
        if initial.directive not in {
            RecoveryDirective.RECONCILE_CHECKPOINT,
            RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
        }:
            return initial
        with self.execution_guard(
            task_id,
            purpose=RecoveryPurpose.RECONCILIATION,
            expected_checkpoint_hash=initial.checkpoint_hash,
        ) as token:
            checkpoint = self._read_checkpoint(task_id)
            if checkpoint is None:
                raise RecoveryCorruptionError("Recovery checkpoint is missing.")
            decision = self.classify_under_claim(task_id, token)
            self._append_recovery_event(
                "RECOVERY_DECISION", token, checkpoint, decision
            )
            if decision.directive is RecoveryDirective.RECONCILE_CHECKPOINT:
                if decision.reason_code == "RECOVERY_CHECKPOINT_EVENT_PENDING":
                    self.checkpoint_store.ensure_checkpoint_event(checkpoint)
                elif decision.reason_code == "RECOVERY_TASK_CHECKPOINT_PENDING":
                    record = self._idempotency_record(checkpoint)
                    if record is None or decision.provenance_event_id is None:
                        raise RecoveryCorruptionError(
                            "Checkpoint reconciliation lacks terminal evidence."
                        )
                    checkpoint = self._reconcile_action_checkpoint(
                        checkpoint,
                        record=record,
                        causal_event_id=decision.provenance_event_id,
                        token=token,
                    )
                elif decision.reason_code == "RECOVERY_RESERVED_CHECKPOINT_PENDING":
                    record = self._idempotency_record(checkpoint)
                    if (
                        record is None
                        or getattr(record.state, "value", record.state)
                        != "RESERVED"
                        or decision.provenance_event_id is None
                        or checkpoint.phase is not TaskPhase.BEFORE_DISPATCH
                    ):
                        raise RecoveryCorruptionError(
                            "Reserved checkpoint reconciliation lacks exact pre-dispatch evidence."
                        )
                    checkpoint = self.checkpoint_store.transition(
                        checkpoint.task_id,
                        expected_version=checkpoint.checkpoint_version,
                        state=TaskState.RUNNING,
                        phase=TaskPhase.IDEMPOTENCY_RESERVED,
                        reason_code="TASK_IDEMPOTENCY_RESERVED",
                        latest_request_id=token.request_id,
                        latest_trace_id=token.trace_id,
                        recovery_attempt_id=token.recovery_attempt_id,
                        current_idempotency_state="RESERVED",
                        causal_provenance_event_id=decision.provenance_event_id,
                        approval_state=(
                            ApprovalState.NOT_REQUIRED
                            if checkpoint.approval_state
                            is ApprovalState.NOT_REQUIRED
                            else ApprovalState.FRESH_APPROVAL_REQUIRED
                        ),
                    )
                else:
                    raise RecoveryCorruptionError(
                        "Checkpoint reconciliation directive is ambiguous."
                    )
            elif decision.directive is RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE:
                causal_event_id = self._reconcile_terminal_provenance(
                    checkpoint, token=token, decision=decision
                )
                record = self._idempotency_record(checkpoint)
                if record is None:
                    raise RecoveryCorruptionError(
                        "Terminal reconciliation lost idempotency evidence."
                    )
                checkpoint = self._reconcile_action_checkpoint(
                    checkpoint,
                    record=record,
                    causal_event_id=causal_event_id,
                    token=token,
                )
            else:
                return decision
            if decision.directive is RecoveryDirective.RECONCILE_CHECKPOINT:
                completed = self._decision(
                    checkpoint, RecoveryClassification.SAFE_TO_RESUME,
                    decision.directive, "RECOVERY_RECONCILIATION_COMPLETED",
                    idempotency_state=decision.idempotency_state,
                )
                self._append_recovery_event(
                    "RECOVERY_COMPLETED", token, checkpoint, completed,
                    terminal=True, success=True,
                )
        return self.classify(task_id)

    def _reconcile_terminal_provenance(
        self,
        checkpoint: TaskCheckpoint,
        *,
        token: RecoveryExecutionToken,
        decision: RecoveryDecision,
    ) -> str:
        record = self._idempotency_record(checkpoint)
        if record is None:
            raise RecoveryCorruptionError("Terminal reconciliation lacks idempotency evidence.")
        state = getattr(record.state, "value", record.state)
        if state not in {
            "SUCCEEDED", "BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH",
            "FAILED_REPORTED",
        }:
            raise RecoveryCorruptionError("Idempotency state is not terminal-reconcilable.")
        module = self._provenance_module()
        event_class = getattr(module, "RuntimeProvenanceEvent")
        event = event_class(
            event_id=_event_id(
                "AOIA_RECOVERY_TERMINAL_RECONCILED", checkpoint.task_id,
                record.operation_key, state,
            ),
            timestamp_utc=_timestamp(self._clock()),
            event_type="RECOVERY_TERMINAL_RECONCILED",
            task_id=checkpoint.task_id,
            request_id=token.request_id,
            trace_id=token.trace_id,
            model_call_id=record.model_call_id,
            action_id=record.action_id,
            operation_key=record.operation_key,
            action_name=checkpoint.current_action_name,
            action_fingerprint=record.action_fingerprint,
            capability_class=record.capability_class,
            idempotency_state=state,
            project_scope=token.project_scope,
            recovery_attempt_id=token.recovery_attempt_id,
            recovery_generation=token.generation,
            recovery_classification=decision.classification.value,
            recovery_directive=decision.directive.value,
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            terminal_receipt_hash=_hash(record.terminal_receipt),
            success=True,
            reason_code="RECOVERY_TERMINAL_RECONCILED",
        )
        self.provenance_store.append_terminal_event(event)
        return event.event_id

    def _reconcile_action_checkpoint(
        self,
        checkpoint: TaskCheckpoint,
        *,
        record: Any,
        causal_event_id: str,
        token: RecoveryExecutionToken,
    ) -> TaskCheckpoint:
        state = str(getattr(record.state, "value", record.state))
        terminal_approval = (
            ApprovalState.DENIED
            if state == "CANCELLED"
            else ApprovalState.NOT_APPLICABLE
        )
        terminal_state, terminal_reason = {
            "SUCCEEDED": (TaskState.COMPLETED, "TASK_COMPLETED"),
            "BLOCKED": (TaskState.BLOCKED, "TASK_ACTION_BLOCKED"),
            "CANCELLED": (TaskState.CANCELLED, "TASK_ACTION_CANCELLED"),
            "FAILED_BEFORE_DISPATCH": (TaskState.FAILED, "TASK_FAILED"),
            "FAILED_REPORTED": (TaskState.FAILED, "TASK_FAILED"),
        }[state]
        # A pre-dispatch terminal P0.7/P0.8 receipt proves that the handler did
        # not run.  Preserve that chronology instead of fabricating an
        # AFTER_ACTION edge.  AFTER_ACTION may also be closed directly when the
        # snapshot merely lagged its exact terminal evidence.
        if (
            state in {"BLOCKED", "CANCELLED", "FAILED_BEFORE_DISPATCH"}
            and checkpoint.phase in {
                TaskPhase.WAITING_FOR_APPROVAL,
                TaskPhase.BEFORE_DISPATCH,
                TaskPhase.IDEMPOTENCY_RESERVED,
            }
        ) or checkpoint.phase is TaskPhase.AFTER_ACTION:
            if (
                state == "SUCCEEDED"
                and checkpoint.max_steps > 1
                and checkpoint.remaining_steps > 0
            ):
                terminal_state = TaskState.PARTIAL
                terminal_reason = "TASK_PARTIAL"
            return self.checkpoint_store.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=terminal_state,
                phase=TaskPhase.TERMINAL,
                reason_code=terminal_reason,
                latest_request_id=token.request_id,
                latest_trace_id=token.trace_id,
                recovery_attempt_id=token.recovery_attempt_id,
                current_idempotency_state=state,
                causal_provenance_event_id=causal_event_id,
                approval_state=terminal_approval,
            )
        if checkpoint.phase is not TaskPhase.AFTER_ACTION or (
            checkpoint.current_idempotency_state != state
            or checkpoint.causal_provenance_event_id != causal_event_id
        ):
            checkpoint = self.checkpoint_store.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.AFTER_ACTION,
                reason_code="TASK_ACTION_COMPLETED",
                latest_request_id=token.request_id,
                latest_trace_id=token.trace_id,
                recovery_attempt_id=token.recovery_attempt_id,
                current_idempotency_state=state,
                causal_provenance_event_id=causal_event_id,
                approval_state=ApprovalState.NOT_APPLICABLE,
            )
        if (
            state == "SUCCEEDED"
            and checkpoint.max_steps > 1
            and checkpoint.remaining_steps > 0
        ):
            terminal_state = TaskState.PARTIAL
            terminal_reason = "TASK_PARTIAL"
        return self.checkpoint_store.transition(
            checkpoint.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=terminal_state,
            phase=TaskPhase.TERMINAL,
            reason_code=terminal_reason,
            latest_request_id=token.request_id,
            latest_trace_id=token.trace_id,
            recovery_attempt_id=token.recovery_attempt_id,
            approval_state=terminal_approval,
        )


__all__ = [
    "MAX_RECOVERY_DISCOVERY_BATCH",
    "MAX_RECOVERY_DISCOVERY_LIMIT",
    "RECOVERY_CLAIM_FIELDS",
    "RECOVERY_CLAIM_SCHEMA_VERSION",
    "RECOVERY_DECISION_FIELDS",
    "RECOVERY_DECISION_SCHEMA_VERSION",
    "RecoveryAction",
    "RecoveryClaim",
    "RecoveryClaimConflictError",
    "RecoveryClaimStatus",
    "RecoveryClassification",
    "RecoveryCorruptionError",
    "RecoveryDecision",
    "RecoveryDirective",
    "RecoveryDiscoveryResult",
    "RecoveryError",
    "RecoveryExecutionToken",
    "RecoveryFencedError",
    "RecoveryInProgressError",
    "RecoveryInputError",
    "RecoveryOperationResult",
    "RecoveryOperationStatus",
    "RecoveryPurpose",
    "TaskRecoveryService",
    "TrustedRecoveryDispatcher",
    "TrustedResumeInput",
]
