from __future__ import annotations

"""Explicit, bounded truth returned by AOIA runtime boundaries.

The contract is deliberately additive.  Existing subsystem receipts remain the
canonical evidence for their own domains; :class:`NZOutcome` is a safe boundary
projection and is never accepted from model or client input as authority.
"""

import json
import re
import sys
import uuid
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


if __name__ == "runtime.outcomes":
    sys.modules.setdefault("outcomes", sys.modules[__name__])
elif __name__ == "outcomes":
    sys.modules.setdefault("runtime.outcomes", sys.modules[__name__])


NZ_OUTCOME_SCHEMA_VERSION = "AOIA_NZ_OUTCOME_1A"
MAX_OUTCOME_MESSAGE_CHARS = 1024
MAX_OUTCOME_REASON_CHARS = 160
MAX_OUTCOME_STRUCTURED_BYTES = 32 * 1024
MAX_OUTCOME_DEPTH = 6
MAX_OUTCOME_CONTAINER_ITEMS = 128
MAX_OUTCOME_STRING_CHARS = 4096

_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,159}$")
_RUNTIME_ID_PREFIXES: Mapping[str, str] = MappingProxyType({
    "request_id": "request",
    "trace_id": "trace",
    "model_call_id": "model_call",
    "action_id": "action",
    "task_id": "task",
    "recovery_attempt_id": "recovery_attempt",
})


class NZOutcomeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CONFLICT = "CONFLICT"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class NZReasonCode(str, Enum):
    """Shared reason vocabulary for critical runtime boundaries.

    Existing versioned subsystems may project their own canonical uppercase
    reason code through ``NZOutcome``.  This enum names the cross-boundary codes
    introduced by P0.11; normalization still preserves validated subsystem
    codes rather than flattening them.
    """

    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    REQUEST_FAILED = "REQUEST_FAILED"
    REQUEST_DEGRADED = "REQUEST_DEGRADED"
    TASK_PARTIAL = "TASK_PARTIAL"
    TASK_BLOCKED = "TASK_BLOCKED"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_FAILED = "TASK_FAILED"
    STEP_BUDGET_EXHAUSTED = "STEP_BUDGET_EXHAUSTED"
    HUMAN_APPROVAL_DECLINED = "HUMAN_APPROVAL_DECLINED"
    CAPABILITY_POLICY_DENIED = "CAPABILITY_POLICY_DENIED"
    ACTION_HANDLER_MISSING = "ACTION_HANDLER_MISSING"
    ACTION_FAILED = "ACTION_FAILED"
    PROCESS_TIMEOUT = "PROCESS_TIMEOUT"
    SUBPROCESS_HARD_TIMEOUT = "SUBPROCESS_HARD_TIMEOUT"
    PROCESS_CPU_LIMIT = "PROCESS_CPU_LIMIT"
    PROCESS_MEMORY_LIMIT = "PROCESS_MEMORY_LIMIT"
    PROCESS_FILE_LIMIT = "PROCESS_FILE_LIMIT"
    PROCESS_COUNT_LIMIT = "PROCESS_COUNT_LIMIT"
    PROCESS_TREE_TERMINATED = "PROCESS_TREE_TERMINATED"
    PROCESS_CONTAINMENT_SETUP_FAILED = "PROCESS_CONTAINMENT_SETUP_FAILED"
    PROCESS_CONTAINMENT_LOST = "PROCESS_CONTAINMENT_LOST"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    IDEMPOTENCY_IN_PROGRESS = "IDEMPOTENCY_IN_PROGRESS"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    BROWSER_FALLBACK_UNVERIFIED = "BROWSER_FALLBACK_UNVERIFIED"
    MODEL_RESPONSE_MALFORMED = "MODEL_RESPONSE_MALFORMED"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_QUOTA = "MODEL_QUOTA"
    MODEL_NETWORK_FAILURE = "MODEL_NETWORK_FAILURE"
    MODEL_PROVIDER_ERROR = "MODEL_PROVIDER_ERROR"
    PROVIDER_DRY_RUN_PREVIEW = "PROVIDER_DRY_RUN_PREVIEW"
    PROVIDER_POLICY_BLOCKED = "PROVIDER_POLICY_BLOCKED"
    RUNTIME_ERROR = "RUNTIME_ERROR"


_SAFE_MESSAGES: Mapping[NZOutcomeStatus, str] = MappingProxyType({
    NZOutcomeStatus.SUCCESS: "The runtime completed the operation.",
    NZOutcomeStatus.PARTIAL: "The runtime completed only part of the operation.",
    NZOutcomeStatus.DEGRADED: "The runtime completed with explicitly degraded assurance.",
    NZOutcomeStatus.BLOCKED: "The runtime blocked the operation.",
    NZOutcomeStatus.CANCELLED: "The operation was cancelled before completion.",
    NZOutcomeStatus.FAILED: "The runtime could not complete the operation.",
    NZOutcomeStatus.TIMEOUT: "The operation reached its enforced timeout.",
    NZOutcomeStatus.CONFLICT: "The operation conflicts with authoritative runtime state.",
    NZOutcomeStatus.UNKNOWN_OUTCOME: "The operation outcome is uncertain and was not repeated.",
    NZOutcomeStatus.MANUAL_REVIEW_REQUIRED: "The operation requires manual review.",
})


def normalize_reason_code(value: NZReasonCode | str | None, *, required: bool) -> str | None:
    if isinstance(value, NZReasonCode):
        return value.value
    if value is None:
        if required:
            raise ValueError("reason_code is required for non-success outcomes")
        return None
    if not isinstance(value, str):
        raise ValueError("reason_code must be a canonical string")
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_OUTCOME_REASON_CHARS or not _REASON_CODE.fullmatch(normalized):
        raise ValueError("reason_code must be a bounded uppercase canonical code")
    return normalized


def safe_message_for(status: NZOutcomeStatus | str) -> str:
    return _SAFE_MESSAGES[_coerce_status(status)]


@dataclass(frozen=True)
class NZOutcome:
    status: NZOutcomeStatus
    reason_code: NZReasonCode | str | None
    message_safe: str
    request_id: str | None = None
    trace_id: str | None = None
    model_call_id: str | None = None
    action_id: str | None = None
    task_id: str | None = None
    recovery_attempt_id: str | None = None
    replayed: bool = False
    degraded: bool = False
    data: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        status = _coerce_status(self.status)
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "reason_code",
            normalize_reason_code(
                self.reason_code,
                required=status is not NZOutcomeStatus.SUCCESS,
            ),
        )
        if not isinstance(self.message_safe, str) or not self.message_safe.strip():
            raise ValueError("message_safe must be a non-empty safe string")
        message = self.message_safe.strip()
        if len(message) > MAX_OUTCOME_MESSAGE_CHARS:
            raise ValueError("message_safe exceeds the outcome bound")
        object.__setattr__(self, "message_safe", message)
        if not isinstance(self.replayed, bool) or not isinstance(self.degraded, bool):
            raise ValueError("replayed and degraded must be boolean")
        if status is NZOutcomeStatus.DEGRADED and not self.degraded:
            object.__setattr__(self, "degraded", True)
        if status is NZOutcomeStatus.SUCCESS and self.degraded:
            raise ValueError("SUCCESS cannot claim degraded execution")
        for field_name, prefix in _RUNTIME_ID_PREFIXES.items():
            value = getattr(self, field_name)
            if value is not None:
                _validate_runtime_id(value, prefix)
        object.__setattr__(self, "data", _freeze_structured(self.data, "data"))
        object.__setattr__(self, "metadata", _freeze_structured(self.metadata, "metadata"))

    @classmethod
    def build(
        cls,
        status: NZOutcomeStatus | str,
        reason_code: NZReasonCode | str | None = None,
        *,
        message_safe: str | None = None,
        **fields: Any,
    ) -> "NZOutcome":
        normalized_status = _coerce_status(status)
        return cls(
            status=normalized_status,
            reason_code=reason_code,
            message_safe=(
                safe_message_for(normalized_status)
                if message_safe is None
                else message_safe
            ),
            **fields,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NZOutcome":
        if not isinstance(payload, Mapping):
            raise ValueError("NZ outcome payload must be a mapping")
        allowed = {
            "schema_version",
            "status",
            "reason_code",
            "message_safe",
            "request_id",
            "trace_id",
            "model_call_id",
            "action_id",
            "task_id",
            "recovery_attempt_id",
            "replayed",
            "degraded",
            "data",
            "metadata",
        }
        if set(payload) - allowed:
            raise ValueError("NZ outcome payload contains unknown fields")
        if payload.get("schema_version") != NZ_OUTCOME_SCHEMA_VERSION:
            raise ValueError("unsupported NZ outcome schema")
        return cls(
            status=payload.get("status"),  # type: ignore[arg-type]
            reason_code=payload.get("reason_code"),  # type: ignore[arg-type]
            message_safe=payload.get("message_safe"),  # type: ignore[arg-type]
            request_id=payload.get("request_id"),  # type: ignore[arg-type]
            trace_id=payload.get("trace_id"),  # type: ignore[arg-type]
            model_call_id=payload.get("model_call_id"),  # type: ignore[arg-type]
            action_id=payload.get("action_id"),  # type: ignore[arg-type]
            task_id=payload.get("task_id"),  # type: ignore[arg-type]
            recovery_attempt_id=payload.get("recovery_attempt_id"),  # type: ignore[arg-type]
            replayed=payload.get("replayed", False),  # type: ignore[arg-type]
            degraded=payload.get("degraded", False),  # type: ignore[arg-type]
            data=payload.get("data"),  # type: ignore[arg-type]
            metadata=payload.get("metadata"),  # type: ignore[arg-type]
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": NZ_OUTCOME_SCHEMA_VERSION,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "message_safe": self.message_safe,
            "replayed": self.replayed,
            "degraded": self.degraded,
        }
        for field_name in _RUNTIME_ID_PREFIXES:
            value = getattr(self, field_name)
            if value is not None:
                payload[field_name] = value
        if self.data is not None:
            payload["data"] = _thaw(self.data)
        if self.metadata is not None:
            payload["metadata"] = _thaw(self.metadata)
        return payload


def outcome_from_tool_result(
    result: Mapping[str, Any],
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    task_id: str | None = None,
    model_call_id: str | None = None,
    action_id: str | None = None,
) -> NZOutcome:
    """Project one executor result without trusting handler-supplied outcome fields."""

    identities = {
        "request_id": request_id,
        "trace_id": trace_id,
        "task_id": task_id,
        "model_call_id": model_call_id,
        "action_id": action_id,
    }
    replayed = result.get("replayed") is True
    reason = _first_reason(result)
    if result.get("idempotency_conflict") is True or str(result.get("idempotency_state", "")) == "CONFLICT":
        status = NZOutcomeStatus.CONFLICT
        reason = reason or NZReasonCode.IDEMPOTENCY_CONFLICT.value
    elif result.get("unknown_outcome") is True:
        status = NZOutcomeStatus.UNKNOWN_OUTCOME
        reason = reason or NZReasonCode.UNKNOWN_OUTCOME.value
    elif result.get("timed_out") is True:
        # A fresh, bounded child timeout is explicit.  A replay or a record that
        # itself reports UNKNOWN_OUTCOME remains uncertain and is never retried.
        if replayed or str(result.get("idempotency_state", "")) == "UNKNOWN_OUTCOME":
            status = NZOutcomeStatus.UNKNOWN_OUTCOME
            reason = reason or NZReasonCode.UNKNOWN_OUTCOME.value
        else:
            status = NZOutcomeStatus.TIMEOUT
            reason = reason or NZReasonCode.PROCESS_TIMEOUT.value
    elif result.get("cancelled") is True:
        status = NZOutcomeStatus.CANCELLED
        reason = reason or NZReasonCode.HUMAN_APPROVAL_DECLINED.value
    elif result.get("manual_review_required") is True:
        status = NZOutcomeStatus.MANUAL_REVIEW_REQUIRED
        reason = reason or NZReasonCode.MANUAL_REVIEW_REQUIRED.value
    elif result.get("blocked") is True or result.get("allowed") is False:
        status = NZOutcomeStatus.BLOCKED
        reason = reason or NZReasonCode.CAPABILITY_POLICY_DENIED.value
    elif result.get("browser_mode") == "fallback" or result.get("degraded") is True:
        status = NZOutcomeStatus.DEGRADED
        reason = reason or NZReasonCode.BROWSER_FALLBACK_UNVERIFIED.value
    elif result.get("success") is True:
        status = NZOutcomeStatus.SUCCESS
        reason = None
    else:
        status = NZOutcomeStatus.FAILED
        reason = reason or NZReasonCode.ACTION_FAILED.value
    return NZOutcome.build(
        status,
        reason,
        replayed=replayed,
        degraded=status is NZOutcomeStatus.DEGRADED,
        metadata={"legacy_success": result.get("success") is True},
        **{key: value for key, value in identities.items() if value is not None},
    )


def attach_outcome(
    result: Mapping[str, Any],
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    task_id: str | None = None,
    model_call_id: str | None = None,
    action_id: str | None = None,
) -> dict[str, Any]:
    payload = dict(result)
    payload["outcome"] = outcome_from_tool_result(
        payload,
        request_id=request_id,
        trace_id=trace_id,
        task_id=task_id,
        model_call_id=model_call_id,
        action_id=action_id,
    ).to_dict()
    return payload


def outcome_from_task_state(
    task_state: str,
    *,
    reason_code: NZReasonCode | str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    task_id: str | None = None,
    recovery_attempt_id: str | None = None,
    replayed: bool = False,
) -> NZOutcome:
    mapping: dict[str, tuple[NZOutcomeStatus, str | None]] = {
        "COMPLETED": (NZOutcomeStatus.SUCCESS, None),
        "PARTIAL": (NZOutcomeStatus.PARTIAL, NZReasonCode.TASK_PARTIAL.value),
        "BLOCKED": (NZOutcomeStatus.BLOCKED, NZReasonCode.TASK_BLOCKED.value),
        "CANCELLED": (NZOutcomeStatus.CANCELLED, NZReasonCode.TASK_CANCELLED.value),
        "FAILED": (NZOutcomeStatus.FAILED, NZReasonCode.TASK_FAILED.value),
        "RECOVERY_REQUIRED": (NZOutcomeStatus.UNKNOWN_OUTCOME, NZReasonCode.UNKNOWN_OUTCOME.value),
        "WAITING_FOR_APPROVAL": (NZOutcomeStatus.BLOCKED, "FRESH_APPROVAL_REQUIRED"),
        "PAUSED": (NZOutcomeStatus.MANUAL_REVIEW_REQUIRED, NZReasonCode.MANUAL_REVIEW_REQUIRED.value),
        "CREATED": (NZOutcomeStatus.PARTIAL, "TASK_NOT_STARTED"),
        "RUNNING": (NZOutcomeStatus.PARTIAL, "TASK_NOT_TERMINAL"),
    }
    try:
        status, default_reason = mapping[task_state]
    except KeyError as exc:
        raise ValueError("unknown task state for NZ outcome") from exc
    return NZOutcome.build(
        status,
        reason_code if reason_code is not None else default_reason,
        request_id=request_id,
        trace_id=trace_id,
        task_id=task_id,
        recovery_attempt_id=recovery_attempt_id,
        replayed=replayed,
        degraded=status is NZOutcomeStatus.DEGRADED,
    )


def outcome_from_exception(
    error: BaseException,
    *,
    request_id: str | None = None,
    trace_id: str | None = None,
    task_id: str | None = None,
    model_call_id: str | None = None,
    action_id: str | None = None,
    recovery_attempt_id: str | None = None,
) -> NZOutcome:
    """Translate typed local failures without exposing their raw text."""

    raw_reason = getattr(error, "reason_code", None)
    try:
        reason = normalize_reason_code(raw_reason, required=False)
    except ValueError:
        reason = None
    reason = reason or NZReasonCode.RUNTIME_ERROR.value
    if (
        reason in {
            NZReasonCode.MODEL_TIMEOUT.value,
            NZReasonCode.PROCESS_TIMEOUT.value,
            NZReasonCode.SUBPROCESS_HARD_TIMEOUT.value,
        }
        or reason == "STATE_LOCK_TIMEOUT"
        or reason.endswith("_LOCK_TIMEOUT")
    ):
        status = NZOutcomeStatus.TIMEOUT
    elif (
        "CORRUPT" in reason
        or "UNSUPPORTED_SCHEMA" in reason
        or reason.endswith("_SCHEMA_UNSUPPORTED")
        or reason in {"RECOVERY_IN_PROGRESS", "IDEMPOTENCY_IN_PROGRESS"}
    ):
        status = NZOutcomeStatus.MANUAL_REVIEW_REQUIRED
    elif "CONFLICT" in reason or "FENCED" in reason:
        status = NZOutcomeStatus.CONFLICT
    elif reason == NZReasonCode.TASK_CANCELLED.value:
        status = NZOutcomeStatus.CANCELLED
    elif "UNKNOWN_OUTCOME" in reason or reason.endswith("_UNKNOWN"):
        status = NZOutcomeStatus.UNKNOWN_OUTCOME
    elif reason in {
        NZReasonCode.PROCESS_CPU_LIMIT.value,
        NZReasonCode.PROCESS_MEMORY_LIMIT.value,
        NZReasonCode.PROCESS_FILE_LIMIT.value,
        NZReasonCode.PROCESS_COUNT_LIMIT.value,
        NZReasonCode.PROCESS_TREE_TERMINATED.value,
        NZReasonCode.PROCESS_CONTAINMENT_LOST.value,
    }:
        # The resource cause is exact, but a mutation-capable child may have
        # produced partial effects before containment intervened. Canonical P0.7
        # evidence, not this projection, decides whether reconciliation is safe.
        status = NZOutcomeStatus.UNKNOWN_OUTCOME
    elif reason in {"TASK_BUDGET_EXHAUSTED", "STEP_BUDGET_EXHAUSTED"}:
        status = NZOutcomeStatus.PARTIAL
    elif isinstance(error, TimeoutError):
        status = NZOutcomeStatus.TIMEOUT
        reason = NZReasonCode.PROCESS_TIMEOUT.value
    else:
        status = NZOutcomeStatus.FAILED
    return NZOutcome.build(
        status,
        reason,
        request_id=request_id,
        trace_id=trace_id,
        task_id=task_id,
        model_call_id=model_call_id,
        action_id=action_id,
        recovery_attempt_id=recovery_attempt_id,
    )


def without_outcome_identities(outcome: Mapping[str, Any]) -> dict[str, Any]:
    """Keep runtime truth in model feedback without disclosing identity controls."""

    return {
        key: value
        for key, value in outcome.items()
        if key not in _RUNTIME_ID_PREFIXES
    }


def _coerce_status(value: NZOutcomeStatus | str) -> NZOutcomeStatus:
    if isinstance(value, NZOutcomeStatus):
        return value
    if isinstance(value, str):
        try:
            return NZOutcomeStatus(value)
        except ValueError as exc:
            raise ValueError("unsupported NZ outcome status") from exc
    raise ValueError("NZ outcome status is required")


def _validate_runtime_id(value: object, prefix: str) -> str:
    if not isinstance(value, str) or not value.startswith(f"{prefix}_"):
        raise ValueError(f"invalid runtime-owned {prefix} identity")
    suffix = value[len(prefix) + 1 :]
    if len(suffix) != 32:
        raise ValueError(f"invalid runtime-owned {prefix} identity")
    try:
        uuid.UUID(hex=suffix)
    except ValueError as exc:
        raise ValueError(f"invalid runtime-owned {prefix} identity") from exc
    return value


def _first_reason(result: Mapping[str, Any]) -> str | None:
    for key in ("result_reason_code", "policy_reason_code", "idempotency_reason_code"):
        value = result.get(key)
        try:
            normalized = normalize_reason_code(value, required=False)
        except ValueError:
            continue
        if normalized:
            return normalized
    return None


def _freeze_structured(value: Mapping[str, Any] | None, field_name: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    frozen = _freeze_value(value, depth=0)
    serialized = json.dumps(_thaw(frozen), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(serialized.encode("utf-8")) > MAX_OUTCOME_STRUCTURED_BYTES:
        raise ValueError(f"{field_name} exceeds the outcome byte bound")
    assert isinstance(frozen, Mapping)
    return frozen


def _freeze_value(value: Any, *, depth: int) -> Any:
    if depth > MAX_OUTCOME_DEPTH:
        raise ValueError("outcome structured value exceeds maximum depth")
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
            raise ValueError("outcome structured values must be finite JSON")
        if isinstance(value, str) and len(value) > MAX_OUTCOME_STRING_CHARS:
            raise ValueError("outcome structured string exceeds maximum length")
        return value
    if isinstance(value, Mapping):
        if len(value) > MAX_OUTCOME_CONTAINER_ITEMS:
            raise ValueError("outcome mapping has too many items")
        normalized: dict[str, Any] = {}
        for raw_key, item in value.items():
            if not isinstance(raw_key, str) or not raw_key or len(raw_key) > 128:
                raise ValueError("outcome mapping keys must be bounded non-empty strings")
            normalized[raw_key] = _freeze_value(item, depth=depth + 1)
        return MappingProxyType(normalized)
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_OUTCOME_CONTAINER_ITEMS:
            raise ValueError("outcome sequence has too many items")
        return tuple(_freeze_value(item, depth=depth + 1) for item in value)
    raise ValueError("outcome structured values must be JSON-compatible")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value
