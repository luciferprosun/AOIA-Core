from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Mapping


UNTRUSTED_IDENTITY_FIELDS = frozenset(
    {
        "request_id",
        "trace_id",
        "model_call_id",
        "action_id",
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
class TraceContext:
    """Runtime-owned identity shared by every step of one top-level request."""

    request_id: str
    trace_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.request_id, "request")
        _require_identifier(self.trace_id, "trace")

    @classmethod
    def new_request(cls) -> "TraceContext":
        return cls(
            request_id=_new_identifier("request"),
            trace_id=_new_identifier("trace"),
        )

    def new_model_call(self) -> "ModelCallContext":
        return ModelCallContext(
            request_id=self.request_id,
            trace_id=self.trace_id,
            model_call_id=_new_identifier("model_call"),
        )

    def new_action(
        self,
        model_call: "ModelCallContext | None" = None,
    ) -> "ActionContext":
        if model_call is not None and (
            model_call.request_id != self.request_id
            or model_call.trace_id != self.trace_id
        ):
            raise TraceIdentityError(
                "Model-call identity does not belong to the current request trace."
            )
        return ActionContext(
            request_id=self.request_id,
            trace_id=self.trace_id,
            action_id=_new_identifier("action"),
            model_call_id=model_call.model_call_id if model_call else None,
        )

    def identity_fields(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
        }


@dataclass(frozen=True)
class ModelCallContext:
    """Identity of one actual provider invocation within a request trace."""

    request_id: str
    trace_id: str
    model_call_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.request_id, "request")
        _require_identifier(self.trace_id, "trace")
        _require_identifier(self.model_call_id, "model_call")

    def identity_fields(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "model_call_id": self.model_call_id,
        }


@dataclass(frozen=True)
class ActionContext:
    """Authoritative identity assigned before policy evaluation and dispatch."""

    request_id: str
    trace_id: str
    action_id: str
    model_call_id: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.request_id, "request")
        _require_identifier(self.trace_id, "trace")
        _require_identifier(self.action_id, "action")
        if self.model_call_id is not None:
            _require_identifier(self.model_call_id, "model_call")

    def identity_fields(self) -> dict[str, str]:
        fields = {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
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
