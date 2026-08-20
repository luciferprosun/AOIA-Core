from __future__ import annotations

import uuid
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping


if __name__ == "runtime.trace_context":
    sys.modules.setdefault("trace_context", sys.modules[__name__])
elif __name__ == "trace_context":
    sys.modules.setdefault("runtime.trace_context", sys.modules[__name__])


UNTRUSTED_IDENTITY_FIELDS = frozenset(
    {
        "request_id",
        "trace_id",
        "task_id",
        "checkpoint_id",
        "checkpoint_version",
        "checkpoint_hash",
        "checkpoint_event_id",
        "checkpoint_parent_hash",
        "root_request_id",
        "root_trace_id",
        "latest_request_id",
        "latest_trace_id",
        "task_state",
        "task_phase",
        "max_steps",
        "step_index",
        "recovery_attempt_id",
        "claim_generation",
        "claim_owner",
        "claim_owner_id",
        "claim_expires_at",
        "lease_expires_at",
        "recovery_claim_id",
        "recovery_state",
        "safe_resume_classification",
        "approval_state",
        "remaining_steps",
        "remaining_retry_budget",
        "provider_attempts_used",
        "current_model_call_id",
        "current_action_id",
        "current_idempotency_key",
        "current_action_fingerprint",
        "current_idempotency_state",
        "current_action_name",
        "current_capability_class",
        "current_policy_reason_code",
        "latest_provenance_event_id",
        "causal_provenance_event_id",
        "transitions",
        "transition_hash",
        "from_state",
        "from_phase",
        "to_state",
        "to_phase",
        "phase",
        "safe_context",
        "request_hash",
        "context_hashes",
        "model_call_id",
        "action_id",
        "idempotency_key",
        "operation_key",
        "provenance_event_id",
        "event_id",
        "event_type",
        "timestamp_utc",
        "timestamp",
        "status",
        "actor_type",
        "safe_payload_metadata",
        "payload",
        "action_fingerprint",
        "idempotency_state",
        "idempotency_reason_code",
        "idempotency_conflict",
        "replayed",
        "dispatched",
        "manual_review_required",
        "unknown_outcome",
        "original_request_id",
        "original_trace_id",
        "original_model_call_id",
        "original_action_id",
        "runtime_requires_confirmation",
        "model_requests_confirmation",
        "policy_reason_code",
        "result_reason_code",
        "reason_code",
        "outcome",
        "actor",
        "capability_class",
        "action_name",
        "approval_required",
        "allowed",
        "blocked",
        "cancelled",
        "success",
        "policy_allowed",
        "stop_loop",
        "timed_out",
        "bytes_written",
        "exit_code",
        "page_count",
        "omitted_field_count",
        "terminal_receipt",
        "receipt_schema_version",
        "result_hash",
        "project_scope",
        "created_at",
        "updated_at",
        "state",
        "prev_hash",
        "previous_hash",
        "payload_hash",
        "entry_hash",
        "event_hash",
        "chain_hash",
        "authority",
        "classification",
        "retention",
        "non_authoritative",
        "canonical_evidence",
        "provider_authenticity_verified",
        "trust_status",
        "ingress",
        "request_length",
        "slash_command",
        "requested_provider_hash",
        "requested_model_hash",
        "retry_attempt",
        "provider_attempt",
        "recovered_count",
        "sequence",
        "schema_version",
    }
)


class TraceIdentityError(RuntimeError):
    """Raised when an execution boundary receives missing or inconsistent identity."""


def _new_identifier(prefix: str) -> str:
    """Generate a collision-resistant, runtime-owned opaque identifier."""

    return f"{prefix}_{uuid.uuid4().hex}"


def _require_identifier(value: str, prefix: str) -> str:
    if not isinstance(value, str) or not value.startswith(f"{prefix}_"):
        raise TraceIdentityError(f"Missing or invalid runtime-owned {prefix} identity.")
    suffix = value[len(prefix) + 1 :]
    if len(suffix) != 32:
        raise TraceIdentityError(f"Missing or invalid runtime-owned {prefix} identity.")
    try:
        uuid.UUID(hex=suffix)
    except ValueError as error:
        raise TraceIdentityError(
            f"Missing or invalid runtime-owned {prefix} identity."
        ) from error
    return value


@dataclass(frozen=True)
class TaskContext:
    """Stable runtime-owned identity for one logical AOIA task."""

    task_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.task_id, "task")

    @classmethod
    def new_task(cls) -> "TaskContext":
        return cls(task_id=_new_identifier("task"))

    def identity_fields(self) -> dict[str, str]:
        return {"task_id": self.task_id}


@dataclass(frozen=True)
class TraceContext:
    """Runtime-owned identity shared by every step of one top-level request."""

    request_id: str
    trace_id: str
    task_id: str = field(default_factory=lambda: _new_identifier("task"))

    def __post_init__(self) -> None:
        _require_identifier(self.request_id, "request")
        _require_identifier(self.trace_id, "trace")
        _require_identifier(self.task_id, "task")

    @classmethod
    def new_request(cls, task_context: TaskContext | None = None) -> "TraceContext":
        return cls(
            request_id=_new_identifier("request"),
            trace_id=_new_identifier("trace"),
            task_id=(task_context or TaskContext.new_task()).task_id,
        )

    def new_model_call(self) -> "ModelCallContext":
        return ModelCallContext(
            request_id=self.request_id,
            trace_id=self.trace_id,
            task_id=self.task_id,
            model_call_id=_new_identifier("model_call"),
        )

    def new_action(
        self,
        model_call: "ModelCallContext | None" = None,
    ) -> "ActionContext":
        if model_call is not None and (
            model_call.request_id != self.request_id
            or model_call.trace_id != self.trace_id
            or model_call.task_id != self.task_id
        ):
            raise TraceIdentityError(
                "Model-call identity does not belong to the current request trace."
            )
        return ActionContext(
            request_id=self.request_id,
            trace_id=self.trace_id,
            task_id=self.task_id,
            action_id=_new_identifier("action"),
            model_call_id=model_call.model_call_id if model_call else None,
        )

    def identity_fields(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "task_id": self.task_id,
        }


@dataclass(frozen=True)
class ModelCallContext:
    """Identity of one actual provider invocation within a request trace."""

    request_id: str
    trace_id: str
    task_id: str
    model_call_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.request_id, "request")
        _require_identifier(self.trace_id, "trace")
        _require_identifier(self.task_id, "task")
        _require_identifier(self.model_call_id, "model_call")

    def identity_fields(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "model_call_id": self.model_call_id,
        }


@dataclass(frozen=True)
class ActionContext:
    """Authoritative identity assigned before policy evaluation and dispatch."""

    request_id: str
    trace_id: str
    task_id: str
    action_id: str
    model_call_id: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.request_id, "request")
        _require_identifier(self.trace_id, "trace")
        _require_identifier(self.task_id, "task")
        _require_identifier(self.action_id, "action")
        if self.model_call_id is not None:
            _require_identifier(self.model_call_id, "model_call")

    def identity_fields(self) -> dict[str, str]:
        fields = {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "action_id": self.action_id,
        }
        if self.model_call_id is not None:
            fields["model_call_id"] = self.model_call_id
        return fields


@dataclass(frozen=True)
class TracedModelOutput:
    """Model text paired with the identity of the provider call that produced it."""

    text: str
    model_call: ModelCallContext
    provider: str = ""
    model: str = ""


def strip_untrusted_identity_fields(action: Mapping[str, Any]) -> dict[str, Any]:
    """Remove model/client-supplied correlation fields before runtime dispatch."""

    return {
        key: value
        for key, value in action.items()
        if key not in UNTRUSTED_IDENTITY_FIELDS
    }
