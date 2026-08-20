from __future__ import annotations

import datetime as dt
import errno
import hashlib
import json
import os
import re
import stat
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    InterProcessFileLock,
    PersistenceError,
    locked_unlink,
    locked_update_json,
    state_resource_lock_path,
    validate_lock_timeout_seconds,
)


GENESIS_PREV_HASH = "0" * 64
RUNTIME_PROVENANCE_SCHEMA_VERSION = "AOIA_RUNTIME_PROVENANCE_1A"
RUNTIME_PROVENANCE_AUTHORITY = {
    "classification": "L1_SECURITY_RECEIPT",
    "non_authoritative": True,
    "canonical_evidence": False,
    "provider_authenticity_verified": False,
    "trust_status": "UNTRUSTED",
}
MAX_PROVENANCE_LOG_BYTES = 64 * 1024 * 1024
MAX_PROVENANCE_RECORD_BYTES = 64 * 1024
MAX_PROVENANCE_OUTBOX_ENTRIES = 1024
MAX_PROVENANCE_RECOVERY_BATCH = 128
RUNTIME_PROVENANCE_ACTOR = "AOIA_RUNTIME"
RUNTIME_PROVENANCE_ACTOR_TYPE = "RUNTIME"

_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ACTION_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ID_PREFIXES = {
    "request_id": "request",
    "trace_id": "trace",
    "model_call_id": "model_call",
    "action_id": "action",
    "operation_key": "operation",
    "event_id": "provenance_event",
}


class RuntimeProvenanceEventType(str, Enum):
    REQUEST_STARTED = "REQUEST_STARTED"
    REQUEST_COMPLETED = "REQUEST_COMPLETED"
    MODEL_CALL_STARTED = "MODEL_CALL_STARTED"
    MODEL_CALL_COMPLETED = "MODEL_CALL_COMPLETED"
    MODEL_CALL_FAILED = "MODEL_CALL_FAILED"
    CAPABILITY_DECISION = "CAPABILITY_DECISION"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_DENIED = "APPROVAL_DENIED"
    IDEMPOTENCY_RESERVED = "IDEMPOTENCY_RESERVED"
    IDEMPOTENCY_REPLAYED = "IDEMPOTENCY_REPLAYED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    ACTION_DISPATCH_STARTED = "ACTION_DISPATCH_STARTED"
    ACTION_DISPATCH_SUCCEEDED = "ACTION_DISPATCH_SUCCEEDED"
    ACTION_DISPATCH_FAILED = "ACTION_DISPATCH_FAILED"
    ACTION_DISPATCH_TIMED_OUT = "ACTION_DISPATCH_TIMED_OUT"
    ACTION_DISPATCH_BLOCKED = "ACTION_DISPATCH_BLOCKED"
    ACTION_DISPATCH_CANCELLED = "ACTION_DISPATCH_CANCELLED"
    UNKNOWN_OUTCOME_DETECTED = "UNKNOWN_OUTCOME_DETECTED"
    PERSISTENCE_FAILURE = "PERSISTENCE_FAILURE"
    PROVENANCE_RECOVERY = "PROVENANCE_RECOVERY"


RUNTIME_PROVENANCE_EVENT_TYPES = frozenset(item.value for item in RuntimeProvenanceEventType)
RUNTIME_PROVENANCE_EVENT_FIELDS = frozenset(
    {
        "schema_version", "event_id", "timestamp_utc", "event_type",
        "actor", "actor_type", "status", "outcome",
        "request_id", "trace_id", "model_call_id", "action_id", "operation_key",
        "ingress", "request_length", "slash_command",
        "requested_provider_hash", "requested_model_hash",
        "retry_attempt", "provider_attempt", "action_name", "action_fingerprint",
        "capability_class",
        "policy_allowed", "approval_required", "idempotency_state",
        "replayed", "dispatched", "success", "reason_code", "recovered_count",
        "authority",
    }
)
RUNTIME_PROVENANCE_RECORD_FIELDS = frozenset(
    {*RUNTIME_PROVENANCE_EVENT_FIELDS, "sequence", "prev_hash", "event_hash", "entry_hash"}
)
RUNTIME_PROVENANCE_OUTBOX_FIELDS = frozenset(
    {*RUNTIME_PROVENANCE_EVENT_FIELDS, "event_hash"}
)
LEGACY_PROVENANCE_RECORD_FIELDS = frozenset(
    {"timestamp", "event_type", "payload_hash", "prev_hash", "entry_hash", "payload"}
)
_BASE_IDS = frozenset({"request_id", "trace_id"})
_ACTION_FIELDS = frozenset(
    {
        "request_id", "trace_id", "model_call_id", "action_id", "operation_key",
        "action_name", "action_fingerprint", "capability_class",
    }
)
_EVENT_ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    "REQUEST_STARTED": _BASE_IDS | {"ingress", "request_length", "slash_command", "reason_code"},
    "REQUEST_COMPLETED": _BASE_IDS | {"ingress", "success", "reason_code"},
    "MODEL_CALL_STARTED": _BASE_IDS | {
        "model_call_id", "requested_provider_hash", "requested_model_hash",
        "retry_attempt", "provider_attempt", "reason_code",
    },
    "MODEL_CALL_COMPLETED": _BASE_IDS | {
        "model_call_id", "requested_provider_hash", "requested_model_hash",
        "retry_attempt", "provider_attempt", "success", "reason_code",
    },
    "MODEL_CALL_FAILED": _BASE_IDS | {
        "model_call_id", "requested_provider_hash", "requested_model_hash",
        "retry_attempt", "provider_attempt", "success", "reason_code",
    },
    "CAPABILITY_DECISION": _ACTION_FIELDS | {
        "policy_allowed", "approval_required", "reason_code",
    },
    "APPROVAL_GRANTED": _ACTION_FIELDS | {
        "approval_required", "success", "reason_code",
    },
    "APPROVAL_DENIED": _ACTION_FIELDS | {
        "approval_required", "success", "reason_code",
    },
    "IDEMPOTENCY_RESERVED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "reason_code",
    },
    "IDEMPOTENCY_REPLAYED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "IDEMPOTENCY_CONFLICT": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "ACTION_DISPATCH_STARTED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "reason_code",
    },
    "ACTION_DISPATCH_SUCCEEDED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "ACTION_DISPATCH_FAILED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "ACTION_DISPATCH_TIMED_OUT": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "ACTION_DISPATCH_BLOCKED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "ACTION_DISPATCH_CANCELLED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "UNKNOWN_OUTCOME_DETECTED": _ACTION_FIELDS | {
        "idempotency_state", "replayed", "dispatched", "success", "reason_code",
    },
    "PERSISTENCE_FAILURE": _ACTION_FIELDS | {
        "idempotency_state", "dispatched", "success", "reason_code",
    },
    "PROVENANCE_RECOVERY": frozenset({"success", "reason_code", "recovered_count"}),
}
_REQUIRED_ACTION = frozenset(
    {
        "request_id", "trace_id", "action_id", "operation_key",
        "action_name", "capability_class",
    }
)
_REQUIRED_IDEMPOTENT_ACTION = _REQUIRED_ACTION | {
    "action_fingerprint", "idempotency_state", "replayed", "dispatched",
}
_EVENT_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "REQUEST_STARTED": _BASE_IDS | {
        "ingress", "request_length", "slash_command", "reason_code",
    },
    "REQUEST_COMPLETED": _BASE_IDS | {"ingress", "success", "reason_code"},
    "MODEL_CALL_STARTED": _BASE_IDS | {
        "model_call_id", "requested_provider_hash", "requested_model_hash",
        "retry_attempt", "provider_attempt", "reason_code",
    },
    "MODEL_CALL_COMPLETED": _BASE_IDS | {
        "model_call_id", "requested_provider_hash", "requested_model_hash",
        "retry_attempt", "provider_attempt", "success", "reason_code",
    },
    "MODEL_CALL_FAILED": _BASE_IDS | {
        "model_call_id", "requested_provider_hash", "requested_model_hash",
        "retry_attempt", "provider_attempt", "success", "reason_code",
    },
    "CAPABILITY_DECISION": _REQUIRED_ACTION | {
        "policy_allowed", "approval_required", "reason_code",
    },
    "APPROVAL_GRANTED": _REQUIRED_ACTION | {
        "approval_required", "success", "reason_code",
    },
    "APPROVAL_DENIED": _REQUIRED_ACTION | {
        "approval_required", "success", "reason_code",
    },
    "IDEMPOTENCY_RESERVED": _REQUIRED_IDEMPOTENT_ACTION | {"reason_code"},
    "IDEMPOTENCY_REPLAYED": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "IDEMPOTENCY_CONFLICT": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "ACTION_DISPATCH_STARTED": _REQUIRED_IDEMPOTENT_ACTION | {"reason_code"},
    "ACTION_DISPATCH_SUCCEEDED": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "ACTION_DISPATCH_FAILED": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "ACTION_DISPATCH_TIMED_OUT": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "ACTION_DISPATCH_BLOCKED": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "ACTION_DISPATCH_CANCELLED": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "UNKNOWN_OUTCOME_DETECTED": _REQUIRED_IDEMPOTENT_ACTION | {
        "success", "reason_code",
    },
    "PERSISTENCE_FAILURE": frozenset({"success", "reason_code"}),
    "PROVENANCE_RECOVERY": frozenset({"success", "reason_code", "recovered_count"}),
}
_EVENT_FIXED_VALUES: dict[str, dict[str, Any]] = {
    "MODEL_CALL_COMPLETED": {"success": True},
    "MODEL_CALL_FAILED": {"success": False},
    "APPROVAL_GRANTED": {"approval_required": True, "success": True},
    "APPROVAL_DENIED": {"approval_required": True, "success": False},
    "IDEMPOTENCY_RESERVED": {
        "idempotency_state": "RESERVED", "replayed": False, "dispatched": False,
    },
    "IDEMPOTENCY_REPLAYED": {"replayed": True, "dispatched": False},
    "IDEMPOTENCY_CONFLICT": {
        "idempotency_state": "CONFLICT", "replayed": False,
        "dispatched": False, "success": False,
    },
    "ACTION_DISPATCH_STARTED": {
        "idempotency_state": "RESERVED", "replayed": False, "dispatched": True,
    },
    "ACTION_DISPATCH_SUCCEEDED": {
        "idempotency_state": "SUCCEEDED", "replayed": False,
        "dispatched": True, "success": True,
    },
    "ACTION_DISPATCH_TIMED_OUT": {
        "idempotency_state": "TIMED_OUT_OR_UNKNOWN", "replayed": False,
        "dispatched": True, "success": False,
    },
    "ACTION_DISPATCH_BLOCKED": {
        "idempotency_state": "BLOCKED", "replayed": False,
        "dispatched": False, "success": False,
    },
    "ACTION_DISPATCH_CANCELLED": {
        "idempotency_state": "CANCELLED", "replayed": False,
        "dispatched": False, "success": False,
    },
    "PERSISTENCE_FAILURE": {"success": False},
    "PROVENANCE_RECOVERY": {"success": True},
}
_CAPABILITY_REASON_CODES = frozenset(
    {
        "READ_ONLY_ALLOWED", "FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        "LOCAL_STATE_CHANGE_REQUIRES_CONFIRMATION",
        "EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        "MODEL_ESCALATION_REQUIRES_CONFIRMATION", "SHELL_RUNTIME_CLASSIFIER",
        "SHELL_COMMAND_BLOCKED", "SHELL_RUNTIME_CONFIRMATION_REQUIRED",
        "SHELL_RUNTIME_POLICY_ALLOWED", "ACTION_NOT_CLASSIFIED",
    }
)
_EVENT_REASON_CODES: dict[str, frozenset[str]] = {
    "REQUEST_STARTED": frozenset({"REQUEST_STARTED"}),
    "REQUEST_COMPLETED": frozenset({"REQUEST_COMPLETED", "REQUEST_FAILED"}),
    "MODEL_CALL_STARTED": frozenset({"MODEL_CALL_STARTED"}),
    "MODEL_CALL_COMPLETED": frozenset({"MODEL_CALL_COMPLETED"}),
    "MODEL_CALL_FAILED": frozenset({"MODEL_CALL_FAILED"}),
    "CAPABILITY_DECISION": _CAPABILITY_REASON_CODES,
    "APPROVAL_GRANTED": frozenset({"APPROVAL_GRANTED"}),
    "APPROVAL_DENIED": frozenset({"APPROVAL_DENIED"}),
    "IDEMPOTENCY_RESERVED": frozenset({"IDEMPOTENCY_RESERVED"}),
    "IDEMPOTENCY_REPLAYED": frozenset({"IDEMPOTENCY_RESULT_REPLAYED"}),
    "IDEMPOTENCY_CONFLICT": frozenset({"IDEMPOTENCY_KEY_CONFLICT"}),
    "ACTION_DISPATCH_STARTED": frozenset({"ACTION_DISPATCH_STARTED"}),
    "ACTION_DISPATCH_SUCCEEDED": frozenset({"ACTION_SUCCEEDED"}),
    "ACTION_DISPATCH_FAILED": frozenset(
        {"ACTION_FAILED_BEFORE_DISPATCH", "ACTION_FAILED_REPORTED"}
    ),
    "ACTION_DISPATCH_TIMED_OUT": frozenset({"ACTION_TIMED_OUT_OR_UNKNOWN"}),
    "ACTION_DISPATCH_BLOCKED": frozenset({"ACTION_BLOCKED_BY_POLICY"}),
    "ACTION_DISPATCH_CANCELLED": frozenset({"HUMAN_APPROVAL_DECLINED"}),
    "UNKNOWN_OUTCOME_DETECTED": frozenset(
        {"IDEMPOTENCY_OPERATION_IN_PROGRESS", "IDEMPOTENCY_UNKNOWN_OUTCOME"}
    ),
    "PERSISTENCE_FAILURE": frozenset(
        {
            "PROVENANCE_APPEND_FAILED", "IDEMPOTENCY_TRANSITION_FAILED",
            "OPERATIONAL_LOG_PERSISTENCE_FAILED",
        }
    ),
    "PROVENANCE_RECOVERY": frozenset({"PROVENANCE_OUTBOX_RECOVERED"}),
}
_SAFE_REASON_CODES = frozenset(
    RUNTIME_PROVENANCE_EVENT_TYPES
    | {
        "REQUEST_FAILED", "MODEL_CALL_FAILED", "READ_ONLY_ALLOWED",
        "FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
        "LOCAL_STATE_CHANGE_REQUIRES_CONFIRMATION",
        "EXTERNAL_INTERACTION_REQUIRES_CONFIRMATION",
        "MODEL_ESCALATION_REQUIRES_CONFIRMATION", "SHELL_RUNTIME_CLASSIFIER",
        "SHELL_COMMAND_BLOCKED", "SHELL_RUNTIME_CONFIRMATION_REQUIRED",
        "SHELL_RUNTIME_POLICY_ALLOWED", "ACTION_NOT_CLASSIFIED",
        "IDEMPOTENCY_RESERVED", "IDEMPOTENCY_RESULT_REPLAYED",
        "IDEMPOTENCY_KEY_CONFLICT", "IDEMPOTENCY_OPERATION_IN_PROGRESS",
        "IDEMPOTENCY_UNKNOWN_OUTCOME", "IDEMPOTENCY_DISPATCH_STARTED",
        "ACTION_SUCCEEDED", "ACTION_BLOCKED_BY_POLICY",
        "HUMAN_APPROVAL_DECLINED", "ACTION_FAILED_BEFORE_DISPATCH",
        "ACTION_FAILED_REPORTED", "ACTION_TIMED_OUT_OR_UNKNOWN",
        "PROVENANCE_OUTBOX_RECOVERED", "PROVENANCE_APPEND_FAILED",
        "IDEMPOTENCY_TRANSITION_FAILED", "OPERATIONAL_LOG_PERSISTENCE_FAILED",
    }
)
_INGRESS_VALUES = frozenset({"CLI", "TUI", "WEB", "OPERATOR_API", "RUNTIME"})
_CAPABILITY_VALUES = frozenset(
    {
        "READ_ONLY", "LOCAL_STATE_CHANGE", "FILESYSTEM_MUTATION",
        "EXTERNAL_INTERACTION", "CODE_EXECUTION", "PRIVILEGED",
    }
)
_IDEMPOTENCY_VALUES = frozenset(
    {
        "RESERVED", "DISPATCH_STARTED", "SUCCEEDED", "BLOCKED", "CANCELLED",
        "FAILED_BEFORE_DISPATCH", "FAILED_REPORTED", "TIMED_OUT_OR_UNKNOWN",
        "UNKNOWN_OUTCOME", "CONFLICT",
    }
)
_TERMINAL_EVENT_TYPES = frozenset(
    {
        "REQUEST_COMPLETED", "MODEL_CALL_COMPLETED", "MODEL_CALL_FAILED",
        "ACTION_DISPATCH_SUCCEEDED", "ACTION_DISPATCH_FAILED",
        "ACTION_DISPATCH_TIMED_OUT", "ACTION_DISPATCH_BLOCKED",
        "ACTION_DISPATCH_CANCELLED", "UNKNOWN_OUTCOME_DETECTED",
        "PERSISTENCE_FAILURE",
    }
)


class ProvenanceError(PersistenceError):
    reason_code = "PROVENANCE_ERROR"


class ProvenanceChainError(ProvenanceError):
    reason_code = "PROVENANCE_CHAIN_INVALID"


class ProvenanceEventConflictError(ProvenanceError):
    reason_code = "PROVENANCE_EVENT_CONFLICT"


class ProvenanceAppendError(ProvenanceError):
    reason_code = "PROVENANCE_APPEND_FAILED"


class ProvenanceSchemaError(ProvenanceError):
    reason_code = "PROVENANCE_SCHEMA_INVALID"


class ProvenanceOutboxError(ProvenanceError):
    reason_code = "PROVENANCE_OUTBOX_INVALID"


class ProvenanceAppendStatus(str, Enum):
    APPENDED = "APPENDED"
    ALREADY_PRESENT = "ALREADY_PRESENT"


@dataclass(frozen=True)
class ProvenanceAppendResult:
    status: ProvenanceAppendStatus
    record: dict[str, Any]

    @property
    def appended(self) -> bool:
        return self.status is ProvenanceAppendStatus.APPENDED


@dataclass(frozen=True)
class ProvenanceRecoveryResult:
    recovered_count: int
    pending_count: int
    degraded: bool = False


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def hash_payload(payload: dict[str, Any]) -> str:
    return _sha256(payload)


def hash_entry(timestamp: str, event_type: str, payload_hash: str, prev_hash: str) -> str:
    return _sha256(
        {
            "timestamp": timestamp, "event_type": event_type,
            "payload_hash": payload_hash, "prev_hash": prev_hash,
        }
    )


def _event_hash(event_document: Mapping[str, Any]) -> str:
    return _sha256(dict(event_document))


def _entry_hash(record_without_entry_hash: Mapping[str, Any]) -> str:
    return _sha256(dict(record_without_entry_hash))


def _hash_requested_label(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProvenanceSchemaError("Requested provider/model labels must be text.")
    encoded = value.encode("utf-8", errors="strict")
    if not encoded or len(encoded) > 512:
        raise ProvenanceSchemaError("Requested provider/model labels are outside policy bounds.")
    return hashlib.sha256(encoded).hexdigest()


def _validate_id(field: str, value: object | None, *, required: bool = False) -> None:
    if value is None and not required:
        return
    prefix = _ID_PREFIXES[field]
    if not isinstance(value, str) or not value.startswith(prefix + "_"):
        raise ProvenanceSchemaError(f"Runtime provenance {field} is invalid.")
    suffix = value[len(prefix) + 1 :]
    if len(suffix) != 32:
        raise ProvenanceSchemaError(f"Runtime provenance {field} is invalid.")
    try:
        uuid.UUID(hex=suffix)
    except ValueError as exc:
        raise ProvenanceSchemaError(f"Runtime provenance {field} is invalid.") from exc


def _event_type_value(value: RuntimeProvenanceEventType | str) -> str:
    text = getattr(value, "value", value)
    if not isinstance(text, str) or text not in RUNTIME_PROVENANCE_EVENT_TYPES:
        raise ProvenanceSchemaError("Runtime provenance event type is not allowed.")
    return text


def _timestamp_value(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 40:
        raise ProvenanceSchemaError("Runtime provenance timestamp is invalid.")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProvenanceSchemaError("Runtime provenance timestamp is invalid.") from exc
    if parsed.tzinfo is None:
        raise ProvenanceSchemaError("Runtime provenance timestamp must be timezone-aware.")
    return parsed.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def _runtime_status_outcome(
    event_type: str,
    *,
    success: bool | None,
    policy_allowed: bool | None,
) -> tuple[str, str]:
    fixed: dict[str, tuple[str, str]] = {
        "REQUEST_STARTED": ("STARTED", "PENDING"),
        "MODEL_CALL_STARTED": ("STARTED", "PENDING"),
        "CAPABILITY_DECISION": (
            "DECIDED",
            "ALLOWED" if policy_allowed is True else "BLOCKED",
        ),
        "APPROVAL_GRANTED": ("GRANTED", "ALLOWED"),
        "APPROVAL_DENIED": ("DENIED", "CANCELLED"),
        "IDEMPOTENCY_RESERVED": ("RESERVED", "PENDING"),
        "IDEMPOTENCY_REPLAYED": ("REPLAYED", "REPLAYED"),
        "IDEMPOTENCY_CONFLICT": ("CONFLICT", "CONFLICT"),
        "ACTION_DISPATCH_STARTED": ("STARTED", "PENDING"),
        "ACTION_DISPATCH_SUCCEEDED": ("COMPLETED", "SUCCEEDED"),
        "ACTION_DISPATCH_FAILED": ("FAILED", "FAILED"),
        "ACTION_DISPATCH_TIMED_OUT": ("TIMED_OUT", "UNKNOWN"),
        "ACTION_DISPATCH_BLOCKED": ("BLOCKED", "BLOCKED"),
        "ACTION_DISPATCH_CANCELLED": ("CANCELLED", "CANCELLED"),
        "UNKNOWN_OUTCOME_DETECTED": ("UNKNOWN", "UNKNOWN"),
        "PERSISTENCE_FAILURE": ("DEGRADED", "FAILED"),
        "PROVENANCE_RECOVERY": ("RECOVERED", "RECOVERED"),
    }
    if event_type == "REQUEST_COMPLETED":
        return ("COMPLETED", "SUCCEEDED") if success else ("FAILED", "FAILED")
    if event_type == "MODEL_CALL_COMPLETED":
        return "COMPLETED", "SUCCEEDED"
    if event_type == "MODEL_CALL_FAILED":
        return "FAILED", "FAILED"
    return fixed[event_type]


@dataclass(frozen=True)
class RuntimeProvenanceEvent:
    event_id: str
    timestamp_utc: str
    event_type: str
    request_id: str | None = None
    trace_id: str | None = None
    model_call_id: str | None = None
    action_id: str | None = None
    operation_key: str | None = None
    ingress: str | None = None
    request_length: int | None = None
    slash_command: bool | None = None
    requested_provider_hash: str | None = None
    requested_model_hash: str | None = None
    retry_attempt: int | None = None
    provider_attempt: int | None = None
    action_name: str | None = None
    action_fingerprint: str | None = None
    capability_class: str | None = None
    policy_allowed: bool | None = None
    approval_required: bool | None = None
    idempotency_state: str | None = None
    replayed: bool | None = None
    dispatched: bool | None = None
    success: bool | None = None
    reason_code: str | None = None
    recovered_count: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", _event_type_value(self.event_type))
        object.__setattr__(self, "timestamp_utc", _timestamp_value(self.timestamp_utc))
        for field in _ID_PREFIXES:
            _validate_id(field, getattr(self, field))
        for field in (
            "slash_command", "policy_allowed", "approval_required",
            "replayed", "dispatched", "success",
        ):
            value = getattr(self, field)
            if value is not None and not isinstance(value, bool):
                raise ProvenanceSchemaError(f"Runtime provenance {field} must be boolean or null.")
        for field, maximum in (
            ("request_length", 10_000_000), ("retry_attempt", 1_000),
            ("provider_attempt", 1_000), ("recovered_count", 1_000_000),
        ):
            value = getattr(self, field)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int)
                or value < 0 or value > maximum
            ):
                raise ProvenanceSchemaError(f"Runtime provenance {field} is outside policy bounds.")
        if self.ingress is not None and self.ingress not in _INGRESS_VALUES:
            raise ProvenanceSchemaError("Runtime provenance ingress is invalid.")
        if self.action_name is not None and not _SAFE_ACTION_NAME.fullmatch(self.action_name):
            raise ProvenanceSchemaError("Runtime provenance action name is invalid.")
        if self.action_fingerprint is not None and (
            not isinstance(self.action_fingerprint, str)
            or not _HEX_DIGEST.fullmatch(self.action_fingerprint)
        ):
            raise ProvenanceSchemaError("Runtime provenance action fingerprint is invalid.")
        if self.capability_class is not None and self.capability_class not in _CAPABILITY_VALUES:
            raise ProvenanceSchemaError("Runtime provenance capability class is invalid.")
        if self.idempotency_state is not None and self.idempotency_state not in _IDEMPOTENCY_VALUES:
            raise ProvenanceSchemaError("Runtime provenance idempotency state is invalid.")
        for field in ("requested_provider_hash", "requested_model_hash"):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, str) or not _HEX_DIGEST.fullmatch(value)
            ):
                raise ProvenanceSchemaError(f"Runtime provenance {field} is invalid.")
        if self.reason_code not in _SAFE_REASON_CODES:
            raise ProvenanceSchemaError("Runtime provenance reason code is not allowed.")
        if self.reason_code not in _EVENT_REASON_CODES[self.event_type]:
            raise ProvenanceSchemaError(
                "Runtime provenance reason code contradicts its event type."
            )
        self._validate_shape()

    def _validate_shape(self) -> None:
        values = asdict(self)
        populated = {
            name
            for name, value in values.items()
            if name not in {"event_id", "timestamp_utc", "event_type"}
            and value is not None
        }
        if populated - _EVENT_ALLOWED_FIELDS[self.event_type]:
            raise ProvenanceSchemaError(
                "Runtime provenance event contains fields outside its exact schema."
            )
        missing = {
            name
            for name in _EVENT_REQUIRED_FIELDS[self.event_type]
            if values.get(name) is None
        }
        if missing:
            raise ProvenanceSchemaError(
                "Runtime provenance event is missing required typed fields."
            )
        for name, expected in _EVENT_FIXED_VALUES.get(self.event_type, {}).items():
            if values.get(name) != expected:
                raise ProvenanceSchemaError(
                    "Runtime provenance event contradicts its fixed semantics."
                )
        if self.event_type.startswith("REQUEST_"):
            _validate_id("request_id", self.request_id, required=True)
            _validate_id("trace_id", self.trace_id, required=True)
            if self.ingress is None:
                raise ProvenanceSchemaError("Request provenance requires ingress.")
        elif self.event_type.startswith("MODEL_CALL_"):
            for field in ("request_id", "trace_id", "model_call_id"):
                _validate_id(field, getattr(self, field), required=True)
        elif self.event_type not in {"PERSISTENCE_FAILURE", "PROVENANCE_RECOVERY"}:
            for field in ("request_id", "trace_id", "action_id", "operation_key"):
                _validate_id(field, getattr(self, field), required=True)
            if self.action_name is None or self.capability_class is None:
                raise ProvenanceSchemaError(
                    "Action provenance requires action and capability class."
                )
        if self.event_type == "REQUEST_STARTED" and (
            self.request_length is None or self.slash_command is None
        ):
            raise ProvenanceSchemaError("Request start provenance is incomplete.")
        if self.event_type == "CAPABILITY_DECISION" and (
            self.policy_allowed is None or self.approval_required is None
        ):
            raise ProvenanceSchemaError("Capability decision provenance is incomplete.")
        if self.event_type in {"APPROVAL_GRANTED", "APPROVAL_DENIED"} and (
            self.approval_required is not True or self.success is None
        ):
            raise ProvenanceSchemaError("Approval provenance is incomplete.")
        if self.event_type == "PROVENANCE_RECOVERY" and (
            self.success is not True or self.recovered_count is None
            or self.recovered_count < 1
        ):
            raise ProvenanceSchemaError("Recovery provenance is incomplete.")
        if self.event_type in _TERMINAL_EVENT_TYPES and self.success is None:
            raise ProvenanceSchemaError("Terminal provenance requires a success boolean.")
        if self.event_type == "REQUEST_COMPLETED":
            expected = "REQUEST_COMPLETED" if self.success else "REQUEST_FAILED"
            if self.reason_code != expected:
                raise ProvenanceSchemaError(
                    "Request completion reason contradicts its outcome."
                )
        if self.event_type in {"MODEL_CALL_STARTED", "MODEL_CALL_COMPLETED"} and (
            self.reason_code != self.event_type
        ):
            raise ProvenanceSchemaError(
                "Model-call provenance reason contradicts its event type."
            )
        if self.event_type == "MODEL_CALL_FAILED" and self.reason_code != "MODEL_CALL_FAILED":
            raise ProvenanceSchemaError(
                "Model-call failure provenance reason is invalid."
            )
        if self.event_type == "ACTION_DISPATCH_FAILED" and (
            self.success is not False
            or self.replayed is not False
            or self.idempotency_state
            not in {"FAILED_BEFORE_DISPATCH", "FAILED_REPORTED"}
            or self.dispatched
            != (self.idempotency_state == "FAILED_REPORTED")
        ):
            raise ProvenanceSchemaError(
                "Action failure provenance contradicts its idempotency state."
            )
        if self.event_type == "ACTION_DISPATCH_FAILED":
            expected_reason = {
                "FAILED_BEFORE_DISPATCH": "ACTION_FAILED_BEFORE_DISPATCH",
                "FAILED_REPORTED": "ACTION_FAILED_REPORTED",
            }[str(self.idempotency_state)]
            if self.reason_code != expected_reason:
                raise ProvenanceSchemaError(
                    "Action failure reason contradicts its idempotency state."
                )
        if self.event_type == "UNKNOWN_OUTCOME_DETECTED" and (
            self.success is not False
            or self.replayed is not False
            or self.idempotency_state
            not in {
                "RESERVED", "DISPATCH_STARTED", "TIMED_OUT_OR_UNKNOWN",
                "UNKNOWN_OUTCOME",
            }
        ):
            raise ProvenanceSchemaError(
                "Unknown-outcome provenance contradicts its fixed semantics."
            )
        if self.event_type == "UNKNOWN_OUTCOME_DETECTED":
            expected_reason = (
                "IDEMPOTENCY_OPERATION_IN_PROGRESS"
                if self.idempotency_state == "RESERVED"
                else "IDEMPOTENCY_UNKNOWN_OUTCOME"
            )
            if self.reason_code != expected_reason:
                raise ProvenanceSchemaError(
                    "Unknown-outcome reason contradicts its idempotency state."
                )
        if self.event_type == "IDEMPOTENCY_REPLAYED":
            replayable_states = {
                "SUCCEEDED", "BLOCKED", "CANCELLED",
                "FAILED_BEFORE_DISPATCH", "FAILED_REPORTED",
            }
            if self.idempotency_state not in replayable_states or (
                self.success != (self.idempotency_state == "SUCCEEDED")
            ):
                raise ProvenanceSchemaError(
                    "Idempotency replay provenance contradicts its terminal receipt."
                )
        if self.event_type == "CAPABILITY_DECISION" and (
            self.policy_allowed is False and self.approval_required is not False
        ):
            raise ProvenanceSchemaError(
                "A blocked capability decision cannot require later approval."
            )

    def event_document(self) -> dict[str, Any]:
        status, outcome = _runtime_status_outcome(
            self.event_type,
            success=self.success,
            policy_allowed=self.policy_allowed,
        )
        return {
            "schema_version": RUNTIME_PROVENANCE_SCHEMA_VERSION,
            **asdict(self),
            "actor": RUNTIME_PROVENANCE_ACTOR,
            "actor_type": RUNTIME_PROVENANCE_ACTOR_TYPE,
            "status": status,
            "outcome": outcome,
            "authority": dict(RUNTIME_PROVENANCE_AUTHORITY),
        }

    def outbox_document(self) -> dict[str, Any]:
        document = self.event_document()
        return {**document, "event_hash": _event_hash(document)}

    @classmethod
    def from_event_document(
        cls, document: Mapping[str, Any]
    ) -> "RuntimeProvenanceEvent":
        if frozenset(document) != RUNTIME_PROVENANCE_EVENT_FIELDS:
            raise ProvenanceSchemaError(
                "Runtime provenance event document has an inexact schema."
            )
        if document.get("schema_version") != RUNTIME_PROVENANCE_SCHEMA_VERSION:
            raise ProvenanceSchemaError("Runtime provenance schema version is invalid.")
        if document.get("authority") != RUNTIME_PROVENANCE_AUTHORITY:
            raise ProvenanceSchemaError("Runtime provenance authority block is invalid.")
        event = cls(
            **{
                field: document[field]
                for field in RuntimeProvenanceEvent.__dataclass_fields__
            }
        )
        status, outcome = _runtime_status_outcome(
            event.event_type,
            success=event.success,
            policy_allowed=event.policy_allowed,
        )
        if (
            document.get("actor") != RUNTIME_PROVENANCE_ACTOR
            or document.get("actor_type") != RUNTIME_PROVENANCE_ACTOR_TYPE
            or document.get("status") != status
            or document.get("outcome") != outcome
        ):
            raise ProvenanceSchemaError(
                "Runtime provenance fixed runtime-owned fields are invalid."
            )
        return event


def new_runtime_provenance_event(
    event_type: RuntimeProvenanceEventType | str,
    *,
    trace_context: object | None = None,
    model_call: object | None = None,
    action_context: object | None = None,
    operation_context: object | None = None,
    ingress: str | None = None,
    request_length: int | None = None,
    slash_command: bool | None = None,
    requested_provider: str | None = None,
    requested_model: str | None = None,
    retry_attempt: int | None = None,
    provider_attempt: int | None = None,
    action_name: str | None = None,
    action_fingerprint: str | None = None,
    capability_class: object | None = None,
    policy_allowed: bool | None = None,
    approval_required: bool | None = None,
    idempotency_state: object | None = None,
    replayed: bool | None = None,
    dispatched: bool | None = None,
    success: bool | None = None,
    reason_code: str | None = None,
    recovered_count: int | None = None,
    clock: Callable[[], dt.datetime] | None = None,
) -> RuntimeProvenanceEvent:
    """Build one runtime-owned event without accepting generic metadata."""
    identities: dict[str, str] = {}
    for context in (trace_context, model_call, action_context):
        if context is None:
            continue
        method = getattr(context, "identity_fields", None)
        if not callable(method):
            raise ProvenanceSchemaError("Provenance received an invalid runtime context.")
        for key, value in method().items():
            if key in identities and identities[key] != value:
                raise ProvenanceSchemaError("Provenance runtime contexts do not correlate.")
            identities[key] = value
    event_name = _event_type_value(event_type)
    timestamp = (clock or (lambda: dt.datetime.now(dt.UTC)))()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.UTC)
    return RuntimeProvenanceEvent(
        event_id=f"provenance_event_{uuid.uuid4().hex}",
        timestamp_utc=timestamp.astimezone(dt.UTC).isoformat().replace("+00:00", "Z"),
        event_type=event_name,
        request_id=identities.get("request_id"),
        trace_id=identities.get("trace_id"),
        model_call_id=identities.get("model_call_id"),
        action_id=identities.get("action_id"),
        operation_key=getattr(operation_context, "operation_key", None),
        ingress=ingress,
        request_length=request_length,
        slash_command=slash_command,
        requested_provider_hash=_hash_requested_label(requested_provider),
        requested_model_hash=_hash_requested_label(requested_model),
        retry_attempt=retry_attempt,
        provider_attempt=provider_attempt,
        action_name=action_name,
        action_fingerprint=action_fingerprint,
        capability_class=getattr(capability_class, "value", capability_class),
        policy_allowed=policy_allowed,
        approval_required=approval_required,
        idempotency_state=getattr(idempotency_state, "value", idempotency_state),
        replayed=replayed,
        dispatched=dispatched,
        success=success,
        reason_code=reason_code or event_name,
        recovered_count=recovered_count,
    )


@dataclass(frozen=True)
class ProvenanceVerificationResult:
    ok: bool
    entry_count: int
    terminal_hash: str
    issues: tuple[str, ...]


def _strict_json_loads(text: str) -> Any:
    def pairs_to_dict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON object key")
            value[key] = item
        return value

    return json.loads(text, object_pairs_hook=pairs_to_dict)


def _decode_lines(payload: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    if not payload:
        return [], []
    if len(payload) > MAX_PROVENANCE_LOG_BYTES:
        return [], ["ledger exceeds the bounded verification size"]
    if not payload.endswith(b"\n"):
        return [], ["ledger contains a partial final line"]
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeError:
        return [], ["ledger is not valid UTF-8"]
    entries: list[dict[str, Any]] = []
    issues: list[str] = []
    for index, line in enumerate(text.splitlines()):
        if not line:
            issues.append(f"entry[{index}]: blank line is not allowed")
            continue
        if len(line.encode("utf-8")) > MAX_PROVENANCE_RECORD_BYTES:
            issues.append(f"entry[{index}]: record exceeds size bound")
            continue
        try:
            value = _strict_json_loads(line)
        except (json.JSONDecodeError, ValueError):
            issues.append(f"entry[{index}]: malformed JSON")
            continue
        if not isinstance(value, dict):
            issues.append(f"entry[{index}]: not a dictionary")
            continue
        entries.append(value)
    return entries, issues


def _verify_entries(
    entries: Iterable[dict[str, Any]], parse_issues: Iterable[str] = ()
) -> ProvenanceVerificationResult:
    values = list(entries)
    issues = list(parse_issues)
    previous_hash = GENESIS_PREV_HASH
    runtime_mode: bool | None = None
    seen_ids: dict[str, str] = {}
    for index, entry in enumerate(values):
        runtime = entry.get("schema_version") == RUNTIME_PROVENANCE_SCHEMA_VERSION
        if runtime_mode is None:
            runtime_mode = runtime
        elif runtime_mode != runtime:
            issues.append(f"entry[{index}]: legacy and runtime schemas cannot be mixed")
        if runtime:
            if frozenset(entry) != RUNTIME_PROVENANCE_RECORD_FIELDS:
                issues.append(f"entry[{index}]: runtime record schema mismatch")
                continue
            try:
                event_doc = {key: entry[key] for key in RUNTIME_PROVENANCE_EVENT_FIELDS}
                RuntimeProvenanceEvent.from_event_document(event_doc)
            except ProvenanceError as exc:
                issues.append(f"entry[{index}]: {exc.reason_code}")
                continue
            if entry.get("sequence") != index + 1:
                issues.append(f"entry[{index}]: sequence mismatch")
            if entry.get("prev_hash") != previous_hash:
                marker = (
                    "first entry prev_hash must be genesis"
                    if index == 0 else "prev_hash mismatch"
                )
                issues.append(f"entry[{index}]: {marker}")
            expected_event_hash = _event_hash(event_doc)
            if entry.get("event_hash") != expected_event_hash:
                issues.append(f"entry[{index}]: event_hash mismatch")
            without_entry = {key: value for key, value in entry.items() if key != "entry_hash"}
            expected_entry_hash = _entry_hash(without_entry)
            if entry.get("entry_hash") != expected_entry_hash:
                issues.append(f"entry[{index}]: entry_hash mismatch")
            event_id = str(entry.get("event_id", ""))
            if event_id in seen_ids:
                issues.append(f"entry[{index}]: duplicate event_id")
                if seen_ids[event_id] != expected_event_hash:
                    issues.append(f"entry[{index}]: conflicting event_id")
            seen_ids[event_id] = expected_event_hash
            previous_hash = expected_entry_hash
            continue

        if frozenset(entry) != LEGACY_PROVENANCE_RECORD_FIELDS:
            issues.append(f"entry[{index}]: legacy record schema mismatch")
        timestamp = entry.get("timestamp")
        event_type = entry.get("event_type")
        payload = entry.get("payload")
        stored_payload_hash = entry.get("payload_hash")
        stored_prev_hash = entry.get("prev_hash")
        stored_entry_hash = entry.get("entry_hash")
        if index == 0 and stored_prev_hash != GENESIS_PREV_HASH:
            issues.append(f"entry[{index}]: first entry prev_hash must be genesis")
        elif index > 0 and stored_prev_hash != previous_hash:
            issues.append(f"entry[{index}]: prev_hash mismatch")
        if not isinstance(payload, dict):
            issues.append(f"entry[{index}]: payload is not a dictionary")
            computed_payload_hash = ""
        else:
            computed_payload_hash = hash_payload(payload)
            if stored_payload_hash != computed_payload_hash:
                issues.append(f"entry[{index}]: payload_hash mismatch")
        if not isinstance(timestamp, str) or not timestamp.strip():
            issues.append(f"entry[{index}]: missing timestamp")
        if not isinstance(event_type, str) or not event_type.strip():
            issues.append(f"entry[{index}]: missing event_type")
        if not isinstance(stored_prev_hash, str) or not stored_prev_hash.strip():
            issues.append(f"entry[{index}]: missing prev_hash")
        if not isinstance(stored_entry_hash, str) or not stored_entry_hash.strip():
            issues.append(f"entry[{index}]: missing entry_hash")
        if (
            isinstance(timestamp, str) and isinstance(event_type, str)
            and computed_payload_hash and isinstance(stored_prev_hash, str)
        ):
            expected = hash_entry(
                timestamp, event_type.strip(), computed_payload_hash, stored_prev_hash
            )
            if stored_entry_hash != expected:
                issues.append(f"entry[{index}]: entry_hash mismatch")
            previous_hash = expected
        elif isinstance(stored_entry_hash, str):
            previous_hash = stored_entry_hash
    return ProvenanceVerificationResult(
        ok=not issues,
        entry_count=len(values),
        terminal_hash=previous_hash,
        issues=tuple(issues),
    )


def _public_ledger_lock_path(path: Path) -> Path:
    state_root = path.parent.parent if path.parent.name == "provenance" else path.parent
    return state_resource_lock_path(state_root, path)


def _read_safe_regular_file(path: Path, *, maximum_bytes: int) -> bytes | None:
    try:
        expected = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(expected.st_mode) or not stat.S_ISREG(expected.st_mode):
        raise ProvenanceChainError(
            "Provenance target is not a safe regular file.", target_path=path
        )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ProvenanceChainError(
            "Provenance target could not be opened safely.", target_path=path
        ) from exc
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
        ):
            raise ProvenanceChainError(
                "Provenance target changed during locked open.", target_path=path
            )
        if opened.st_size > maximum_bytes:
            raise ProvenanceChainError(
                "Provenance target exceeds its bounded size.", target_path=path
            )
        chunks: list[bytes] = []
        remaining = opened.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise ProvenanceChainError(
                    "Provenance target changed during locked read.", target_path=path
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def load_provenance_entries(log_path: Path) -> list[dict[str, Any]]:
    path = Path(log_path)
    with InterProcessFileLock(
        _public_ledger_lock_path(path),
        timeout_seconds=DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    ):
        payload = _read_safe_regular_file(
            path, maximum_bytes=MAX_PROVENANCE_LOG_BYTES
        )
    if payload is None:
        return []
    entries, issues = _decode_lines(payload)
    if issues:
        raise ProvenanceChainError(issues[0], target_path=path)
    return entries


def verify_provenance_chain(
    source: Path | Iterable[dict[str, Any]]
) -> ProvenanceVerificationResult:
    if not isinstance(source, Path):
        return _verify_entries(source)
    path = Path(source)
    try:
        with InterProcessFileLock(
            _public_ledger_lock_path(path),
            timeout_seconds=DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
        ):
            payload = _read_safe_regular_file(
                path, maximum_bytes=MAX_PROVENANCE_LOG_BYTES
            )
    except PersistenceError as exc:
        return _verify_entries((), (exc.reason_code,))
    if payload is None:
        return _verify_entries(())
    entries, issues = _decode_lines(payload)
    return _verify_entries(entries, issues)


class AppendOnlyProvenanceStore:
    """Locked local chain for typed receipts and historical legacy fixtures.

    The unsigned local chain detects in-place alteration and partial writes. It
    cannot detect deletion of a complete suffix without an external anchor.
    """

    def __init__(
        self,
        root_dir: Path,
        clock: Callable[[], dt.datetime] | None = None,
        *,
        lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
        recover_on_init: bool = True,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.provenance_dir = self.root_dir / "provenance"
        self.legacy_log_path = self.provenance_dir / "provenance_log.jsonl"
        self.runtime_log_path = (
            self.provenance_dir / "runtime_provenance_log.jsonl"
        )
        # Historical compatibility keeps log_path bound to the legacy ledger.
        # Runtime callers use the explicit immutable runtime_log_path.
        self.log_path = self.legacy_log_path
        self.outbox_dir = self.provenance_dir / "outbox"
        self._clock = clock or (lambda: dt.datetime.now(dt.UTC))
        self.lock_timeout_seconds = validate_lock_timeout_seconds(lock_timeout_seconds)
        self._safe_directory(self.provenance_dir)
        self._safe_directory(self.outbox_dir)
        self.lock_path = state_resource_lock_path(self.root_dir, self.log_path)
        self.outbox_lock_path = state_resource_lock_path(
            self.root_dir, self.outbox_dir / ".queue"
        )
        if recover_on_init:
            self._require_recovery_complete(self.recover_pending_events())

    @staticmethod
    def _safe_directory(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ProvenanceChainError(
                "Provenance state directory is unsafe.", target_path=path
            )

    def _bounded_outbox_paths(self) -> list[Path]:
        paths: list[Path] = []
        try:
            with os.scandir(self.outbox_dir) as entries:
                for entry in entries:
                    paths.append(Path(entry.path))
                    if len(paths) > MAX_PROVENANCE_OUTBOX_ENTRIES:
                        break
        except OSError as exc:
            raise ProvenanceOutboxError(
                "Provenance outbox could not be scanned safely.",
                target_path=self.outbox_dir,
            ) from exc
        return sorted(paths, key=lambda item: item.name)

    def _open_ledger(self, ledger_path: Path) -> tuple[int, bool]:
        existed = False
        try:
            before = ledger_path.lstat()
            existed = True
            if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
                raise ProvenanceChainError(
                    "Provenance ledger target is unsafe.", target_path=ledger_path
                )
        except FileNotFoundError:
            pass
        flags = (
            os.O_RDWR | os.O_CREAT | os.O_APPEND
            | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(ledger_path, flags, 0o600)
        except OSError as exc:
            raise ProvenanceChainError(
                "Provenance ledger could not be opened safely.",
                target_path=ledger_path,
            ) from exc
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            os.close(descriptor)
            raise ProvenanceChainError(
                "Provenance ledger is not a regular file.", target_path=ledger_path
            )
        try:
            current = ledger_path.lstat()
        except OSError as exc:
            os.close(descriptor)
            raise ProvenanceChainError(
                "Provenance ledger path changed while locked.",
                target_path=ledger_path,
            ) from exc
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            os.close(descriptor)
            raise ProvenanceChainError(
                "Provenance ledger path changed while locked.",
                target_path=ledger_path,
            )
        return descriptor, existed

    @staticmethod
    def _read_descriptor(descriptor: int) -> bytes:
        size = os.fstat(descriptor).st_size
        if size > MAX_PROVENANCE_LOG_BYTES:
            raise ProvenanceChainError(
                "Provenance ledger exceeds verification size bound."
            )
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise ProvenanceChainError(
                    "Provenance ledger changed during verification."
                )
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _locked_snapshot(
        self,
        ledger_path: Path,
    ) -> tuple[list[dict[str, Any]], ProvenanceVerificationResult]:
        lock_path = state_resource_lock_path(self.root_dir, ledger_path)
        with InterProcessFileLock(
            lock_path, timeout_seconds=self.lock_timeout_seconds
        ):
            descriptor, _ = self._open_ledger(ledger_path)
            try:
                entries, parse_issues = _decode_lines(
                    self._read_descriptor(descriptor)
                )
                result = _verify_entries(entries, parse_issues)
            finally:
                os.close(descriptor)
        return entries, result

    def read_all(self) -> list[dict[str, Any]]:
        entries, result = self._locked_snapshot(self.legacy_log_path)
        if not result.ok:
            raise ProvenanceChainError(
                result.issues[0], target_path=self.legacy_log_path
            )
        return entries

    def read_runtime_all(self) -> list[dict[str, Any]]:
        entries, result = self._locked_snapshot(self.runtime_log_path)
        if not result.ok:
            raise ProvenanceChainError(
                result.issues[0], target_path=self.runtime_log_path
            )
        return entries

    def read_legacy_all(self) -> list[dict[str, Any]]:
        return self.read_all()

    def latest_hash(self) -> str:
        _, result = self._locked_snapshot(self.legacy_log_path)
        if not result.ok:
            raise ProvenanceChainError(
                result.issues[0], target_path=self.legacy_log_path
            )
        return result.terminal_hash

    def latest_runtime_hash(self) -> str:
        _, result = self._locked_snapshot(self.runtime_log_path)
        if not result.ok:
            raise ProvenanceChainError(
                result.issues[0], target_path=self.runtime_log_path
            )
        return result.terminal_hash

    def _append_locked(
        self,
        ledger_path: Path,
        build: Callable[
            [list[dict[str, Any]], str],
            tuple[dict[str, Any] | None, dict[str, Any]],
        ],
    ) -> tuple[bool, dict[str, Any]]:
        lock_path = state_resource_lock_path(self.root_dir, ledger_path)
        with InterProcessFileLock(
            lock_path, timeout_seconds=self.lock_timeout_seconds
        ):
            descriptor, existed = self._open_ledger(ledger_path)
            original_size = os.fstat(descriptor).st_size
            try:
                entries, parse_issues = _decode_lines(
                    self._read_descriptor(descriptor)
                )
                verification = _verify_entries(entries, parse_issues)
                if not verification.ok:
                    raise ProvenanceChainError(
                        verification.issues[0], target_path=ledger_path
                    )
                record, returned = build(entries, verification.terminal_hash)
                if record is None:
                    return False, returned
                line = (_canonical_json(record) + "\n").encode("utf-8")
                if len(line) > MAX_PROVENANCE_RECORD_BYTES:
                    raise ProvenanceSchemaError(
                        "Provenance record exceeds size bound."
                    )
                view = memoryview(line)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("short provenance append")
                    view = view[written:]
                os.fsync(descriptor)
                durable = os.fstat(descriptor)
                try:
                    canonical = ledger_path.lstat()
                except OSError as exc:
                    raise ProvenanceChainError(
                        "Provenance ledger path disappeared after durable append.",
                        target_path=ledger_path,
                    ) from exc
                if (
                    durable.st_size != original_size + len(line)
                    or (durable.st_dev, durable.st_ino)
                    != (canonical.st_dev, canonical.st_ino)
                    or not stat.S_ISREG(canonical.st_mode)
                ):
                    raise ProvenanceChainError(
                        "Provenance ledger path changed during durable append.",
                        target_path=ledger_path,
                    )
                if not existed:
                    _fsync_directory(self.provenance_dir)
                return True, returned
            except Exception as exc:
                try:
                    os.ftruncate(descriptor, original_size)
                    os.fsync(descriptor)
                except OSError:
                    pass
                if isinstance(exc, PersistenceError):
                    raise
                raise ProvenanceAppendError(
                    "Provenance append did not reach its durable boundary.",
                    target_path=ledger_path,
                ) from exc
            finally:
                os.close(descriptor)

    def append_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Compatibility API for historical ingestion ledgers only."""
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("Provenance event_type must be a non-empty string")
        if not isinstance(payload, dict):
            raise TypeError("Provenance payload must be a dictionary")
        payload_hash = hash_payload(payload)
        timestamp = self._clock().isoformat()

        def build(
            entries: list[dict[str, Any]], previous_hash: str
        ) -> tuple[dict[str, Any], dict[str, Any]]:
            if entries and entries[0].get("schema_version") == RUNTIME_PROVENANCE_SCHEMA_VERSION:
                raise ProvenanceSchemaError(
                    "Legacy events cannot be appended to a runtime provenance ledger."
                )
            record = {
                "timestamp": timestamp,
                "event_type": event_type.strip(),
                "payload_hash": payload_hash,
                "prev_hash": previous_hash,
                "entry_hash": hash_entry(
                    timestamp, event_type.strip(), payload_hash, previous_hash
                ),
                "payload": payload,
            }
            return record, record

        _, record = self._append_locked(self.legacy_log_path, build)
        return record

    def append_many(
        self, events: Iterable[tuple[str, dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        return [self.append_event(kind, payload) for kind, payload in events]

    def _append_runtime_without_recovery(
        self, event: RuntimeProvenanceEvent
    ) -> ProvenanceAppendResult:
        if not isinstance(event, RuntimeProvenanceEvent):
            raise TypeError("Runtime provenance append requires a typed event.")
        event_document = event.event_document()
        event_hash = _event_hash(event_document)

        def build(
            entries: list[dict[str, Any]], previous_hash: str
        ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
            if entries and entries[0].get("schema_version") != RUNTIME_PROVENANCE_SCHEMA_VERSION:
                raise ProvenanceSchemaError(
                    "Runtime events cannot be appended to a legacy provenance ledger."
                )
            for existing in entries:
                if existing.get("event_id") != event.event_id:
                    continue
                if existing.get("event_hash") == event_hash:
                    return None, existing
                raise ProvenanceEventConflictError(
                    "Runtime provenance event ID conflicts with different content.",
                    target_path=self.runtime_log_path,
                )
            without_entry = {
                **event_document,
                "sequence": len(entries) + 1,
                "prev_hash": previous_hash,
                "event_hash": event_hash,
            }
            record = {
                **without_entry,
                "entry_hash": _entry_hash(without_entry),
            }
            return record, record

        appended, record = self._append_locked(self.runtime_log_path, build)
        status_value = (
            ProvenanceAppendStatus.APPENDED
            if appended else ProvenanceAppendStatus.ALREADY_PRESENT
        )
        return ProvenanceAppendResult(status_value, record)

    def append_runtime_event(
        self, event: RuntimeProvenanceEvent
    ) -> ProvenanceAppendResult:
        self._require_recovery_complete(self.recover_pending_events())
        return self._append_runtime_without_recovery(event)

    def append_terminal_event(
        self, event: RuntimeProvenanceEvent
    ) -> ProvenanceAppendResult:
        if event.event_type not in _TERMINAL_EVENT_TYPES:
            raise ProvenanceSchemaError(
                "Only terminal runtime events may use the provenance outbox."
            )
        self._require_recovery_complete(self.recover_pending_events())
        pending_path = self.outbox_dir / f"{event.event_id}.json"
        document = event.outbox_document()

        def stage(current: Any | None) -> tuple[dict[str, Any], None]:
            if current is not None and current != document:
                raise ProvenanceEventConflictError(
                    "Provenance outbox event ID conflicts with different content.",
                    target_path=pending_path,
                )
            return document, None

        with InterProcessFileLock(
            self.outbox_lock_path, timeout_seconds=self.lock_timeout_seconds
        ):
            queue_entries = self._bounded_outbox_paths()
            if len(queue_entries) > MAX_PROVENANCE_OUTBOX_ENTRIES:
                raise ProvenanceOutboxError(
                    "Provenance outbox exceeds its bounded queue limit.",
                    target_path=self.outbox_dir,
                )
            unexpected = [
                item for item in queue_entries if not item.name.endswith(".json")
            ]
            if unexpected:
                raise ProvenanceOutboxError(
                    "Provenance outbox contains an unexpected entry.",
                    target_path=unexpected[0],
                )
            if (
                not pending_path.exists()
                and len(queue_entries) >= MAX_PROVENANCE_OUTBOX_ENTRIES
            ):
                raise ProvenanceOutboxError(
                    "Provenance outbox reached its bounded queue limit.",
                    target_path=self.outbox_dir,
                )
            locked_update_json(
                pending_path,
                stage,
                lock_path=state_resource_lock_path(self.root_dir, pending_path),
                lock_timeout_seconds=self.lock_timeout_seconds,
                indent=None,
                sort_keys=True,
                trailing_newline=True,
            )
            result = self._append_runtime_without_recovery(event)
            locked_unlink(
                pending_path,
                lock_path=state_resource_lock_path(self.root_dir, pending_path),
                lock_timeout_seconds=self.lock_timeout_seconds,
            )
        return result

    append_terminal = append_terminal_event

    def recover_pending_events(self) -> ProvenanceRecoveryResult:
        self._safe_directory(self.outbox_dir)
        recovered = 0
        with InterProcessFileLock(
            self.outbox_lock_path, timeout_seconds=self.lock_timeout_seconds
        ):
            paths = self._bounded_outbox_paths()
            unexpected = [item for item in paths if not item.name.endswith(".json")]
            if unexpected:
                raise ProvenanceOutboxError(
                    "Provenance outbox contains an unexpected entry.",
                    target_path=unexpected[0],
                )
            if len(paths) > MAX_PROVENANCE_OUTBOX_ENTRIES:
                raise ProvenanceOutboxError(
                    "Provenance outbox exceeds its bounded queue limit.",
                    target_path=self.outbox_dir,
                )
            for pending_path in paths[:MAX_PROVENANCE_RECOVERY_BATCH]:
                try:
                    payload = _read_safe_regular_file(
                        pending_path, maximum_bytes=MAX_PROVENANCE_RECORD_BYTES
                    )
                except ProvenanceError as exc:
                    raise ProvenanceOutboxError(
                        "Provenance outbox entry could not be read safely.",
                        target_path=pending_path,
                    ) from exc
                if payload is None:
                    continue
                try:
                    raw = payload.decode("utf-8", errors="strict")
                    document = _strict_json_loads(raw)
                except (
                    UnicodeError, json.JSONDecodeError, ValueError
                ) as exc:
                    raise ProvenanceOutboxError(
                        "Provenance outbox entry is malformed.",
                        target_path=pending_path,
                    ) from exc
                if (
                    not isinstance(document, dict)
                    or frozenset(document) != RUNTIME_PROVENANCE_OUTBOX_FIELDS
                ):
                    raise ProvenanceOutboxError(
                        "Provenance outbox entry has an inexact schema.",
                        target_path=pending_path,
                    )
                event_document = {
                    key: document[key] for key in RUNTIME_PROVENANCE_EVENT_FIELDS
                }
                if document.get("event_hash") != _event_hash(event_document):
                    raise ProvenanceOutboxError(
                        "Provenance outbox event hash is invalid.",
                        target_path=pending_path,
                    )
                try:
                    event = RuntimeProvenanceEvent.from_event_document(event_document)
                except ProvenanceError as exc:
                    raise ProvenanceOutboxError(
                        "Provenance outbox event is invalid.",
                        target_path=pending_path,
                    ) from exc
                if event.event_type not in _TERMINAL_EVENT_TYPES:
                    raise ProvenanceOutboxError(
                        "Provenance outbox contains a non-terminal event.",
                        target_path=pending_path,
                    )
                if pending_path.name != f"{event.event_id}.json":
                    raise ProvenanceOutboxError(
                        "Provenance outbox filename does not match its event ID.",
                        target_path=pending_path,
                    )
                self._append_runtime_without_recovery(event)
                locked_unlink(
                    pending_path,
                    lock_path=state_resource_lock_path(self.root_dir, pending_path),
                    lock_timeout_seconds=self.lock_timeout_seconds,
                )
                recovered += 1
            if recovered:
                recovery_event = new_runtime_provenance_event(
                    RuntimeProvenanceEventType.PROVENANCE_RECOVERY,
                    success=True,
                    reason_code="PROVENANCE_OUTBOX_RECOVERED",
                    recovered_count=recovered,
                    clock=self._clock,
                )
                self._append_runtime_without_recovery(recovery_event)
            remaining_paths = self._bounded_outbox_paths()
            if len(remaining_paths) > MAX_PROVENANCE_OUTBOX_ENTRIES:
                raise ProvenanceOutboxError(
                    "Provenance outbox exceeds its bounded queue limit.",
                    target_path=self.outbox_dir,
                )
            remaining = sum(
                1 for item in remaining_paths if item.name.endswith(".json")
            )
        return ProvenanceRecoveryResult(recovered, remaining, remaining > 0)

    @staticmethod
    def _require_recovery_complete(result: ProvenanceRecoveryResult) -> None:
        if result.degraded:
            raise ProvenanceOutboxError(
                "Provenance recovery is incomplete; durable pending events remain."
            )


def _fsync_directory(directory: Path) -> None:
    flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        descriptor = os.open(directory, flags)
    except OSError as exc:
        unsupported = {
            errno.EBADF, errno.EINVAL, getattr(errno, "ENOTSUP", errno.EINVAL),
            getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        }
        if exc.errno in unsupported:
            return
        raise
    try:
        try:
            os.fsync(descriptor)
        except OSError as exc:
            unsupported = {
                errno.EBADF, errno.EINVAL,
                getattr(errno, "ENOTSUP", errno.EINVAL),
                getattr(errno, "EOPNOTSUPP", errno.EINVAL),
            }
            if exc.errno not in unsupported:
                raise
    finally:
        os.close(descriptor)
