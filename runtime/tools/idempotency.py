from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    StateCorruptionError,
    locked_update_json,
    read_json_snapshot,
    state_resource_lock_path,
    validate_lock_timeout_seconds,
)

from .capability_policy import CapabilityClass
from .validator import ALLOWED_ACTIONS


IDEMPOTENCY_SCHEMA_VERSION = "AOIA_IDEMPOTENCY_1A"
IDEMPOTENCY_KEY_CONFLICT_REASON_CODE = "IDEMPOTENCY_KEY_CONFLICT"
IDEMPOTENCY_OPERATION_IN_PROGRESS_REASON_CODE = "IDEMPOTENCY_OPERATION_IN_PROGRESS"
IDEMPOTENCY_UNKNOWN_OUTCOME_REASON_CODE = "IDEMPOTENCY_UNKNOWN_OUTCOME"
IDEMPOTENCY_REPLAYED_REASON_CODE = "IDEMPOTENCY_RESULT_REPLAYED"
IDEMPOTENCY_RESERVED_REASON_CODE = "IDEMPOTENCY_RESERVED"
IDEMPOTENCY_OWNER_MISMATCH_REASON_CODE = "IDEMPOTENCY_OWNER_MISMATCH"
IDEMPOTENCY_ILLEGAL_TRANSITION_REASON_CODE = "IDEMPOTENCY_ILLEGAL_TRANSITION"
IDEMPOTENCY_STORE_CORRUPT_REASON_CODE = "IDEMPOTENCY_STORE_CORRUPT"


_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SAFE_REASON_CODE = re.compile(r"^[A-Z0-9_.:-]{1,160}$")
IDEMPOTENCY_RECEIPT_FIELDS = frozenset(
    {
        "receipt_schema_version",
        "result_hash",
        "success",
        "blocked",
        "cancelled",
        "timed_out",
        "unknown_outcome",
        "stop_loop",
        "exit_code",
        "bytes_written",
        "page_count",
        "omitted_field_count",
    }
)
IDEMPOTENCY_RECORD_FIELDS = frozenset(
    {
        "schema_version",
        "operation_key",
        "project_scope",
        "request_id",
        "trace_id",
        "action_id",
        "model_call_id",
        "action_fingerprint",
        "capability_class",
        "state",
        "created_at",
        "updated_at",
        "reason_code",
        "terminal_receipt",
    }
)


# Only fields consumed by the corresponding runtime handler participate in the
# semantic action fingerprint. Runtime correlation, model explanations,
# confidence, confirmation requests, operation keys, and future provenance
# metadata are deliberately excluded.
ACTION_SEMANTIC_FIELDS: dict[str, tuple[str, ...]] = {
    "respond": ("message",),
    "shell_execute": ("command",),
    "write_file": ("path", "content"),
    "append_file": ("path", "content"),
    "read_file": ("path",),
    "create_file": ("path", "content"),
    "create_folder": ("path",),
    "move_file": ("src", "dst"),
    "delete_file": ("path",),
    "search_in_project": ("path", "pattern"),
    "change_directory": ("path",),
    "browser_start": (),
    "browser_open": ("url",),
    "browser_click": ("selector",),
    "browser_type": ("selector", "text"),
    "browser_press": ("key",),
    "browser_read_html": (),
    "browser_get_visible_text": (),
    "browser_screenshot": ("path",),
    "browser_close": (),
    "browser_current_url": (),
    "scan_project": ("path",),
}


class IdempotencyError(RuntimeError):
    reason_code = "IDEMPOTENCY_ERROR"


class IdempotencyStoreCorruptionError(IdempotencyError):
    reason_code = IDEMPOTENCY_STORE_CORRUPT_REASON_CODE


class IdempotencyTransitionError(IdempotencyError):
    reason_code = IDEMPOTENCY_ILLEGAL_TRANSITION_REASON_CODE


class IdempotencyOwnerMismatchError(IdempotencyError):
    reason_code = IDEMPOTENCY_OWNER_MISMATCH_REASON_CODE


class IdempotencyState(str, Enum):
    RESERVED = "RESERVED"
    DISPATCH_STARTED = "DISPATCH_STARTED"
    SUCCEEDED = "SUCCEEDED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    FAILED_BEFORE_DISPATCH = "FAILED_BEFORE_DISPATCH"
    FAILED_REPORTED = "FAILED_REPORTED"
    TIMED_OUT_OR_UNKNOWN = "TIMED_OUT_OR_UNKNOWN"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    CONFLICT = "CONFLICT"


IDEMPOTENCY_STATE_REASON_CODES: dict[IdempotencyState, str] = {
    IdempotencyState.RESERVED: IDEMPOTENCY_RESERVED_REASON_CODE,
    IdempotencyState.DISPATCH_STARTED: "IDEMPOTENCY_DISPATCH_STARTED",
    IdempotencyState.SUCCEEDED: "ACTION_SUCCEEDED",
    IdempotencyState.BLOCKED: "ACTION_BLOCKED_BY_POLICY",
    IdempotencyState.CANCELLED: "HUMAN_APPROVAL_DECLINED",
    IdempotencyState.FAILED_BEFORE_DISPATCH: "ACTION_FAILED_BEFORE_DISPATCH",
    IdempotencyState.FAILED_REPORTED: "ACTION_FAILED_REPORTED",
    IdempotencyState.TIMED_OUT_OR_UNKNOWN: "ACTION_TIMED_OUT_OR_UNKNOWN",
    IdempotencyState.UNKNOWN_OUTCOME: IDEMPOTENCY_UNKNOWN_OUTCOME_REASON_CODE,
}


class IdempotencyResolutionKind(str, Enum):
    RESERVED = "RESERVED"
    REPLAYED = "REPLAYED"
    CONFLICT = "CONFLICT"
    IN_PROGRESS = "IN_PROGRESS"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


TERMINAL_STATES = frozenset(
    {
        IdempotencyState.SUCCEEDED,
        IdempotencyState.BLOCKED,
        IdempotencyState.CANCELLED,
        IdempotencyState.FAILED_BEFORE_DISPATCH,
        IdempotencyState.FAILED_REPORTED,
        IdempotencyState.TIMED_OUT_OR_UNKNOWN,
        IdempotencyState.UNKNOWN_OUTCOME,
    }
)


VALID_TRANSITIONS: dict[IdempotencyState, frozenset[IdempotencyState]] = {
    IdempotencyState.RESERVED: frozenset(
        {
            IdempotencyState.DISPATCH_STARTED,
            IdempotencyState.BLOCKED,
            IdempotencyState.CANCELLED,
            IdempotencyState.FAILED_BEFORE_DISPATCH,
        }
    ),
    IdempotencyState.DISPATCH_STARTED: frozenset(
        {
            IdempotencyState.SUCCEEDED,
            IdempotencyState.FAILED_REPORTED,
            IdempotencyState.TIMED_OUT_OR_UNKNOWN,
            IdempotencyState.UNKNOWN_OUTCOME,
        }
    ),
}


def _new_operation_key() -> str:
    return f"operation_{uuid.uuid4().hex}"


def _validate_operation_key(value: object) -> str:
    if not isinstance(value, str) or not value.startswith("operation_"):
        raise ValueError("Missing or invalid runtime-owned operation key.")
    suffix = value[len("operation_") :]
    if len(suffix) != 32:
        raise ValueError("Missing or invalid runtime-owned operation key.")
    try:
        uuid.UUID(hex=suffix)
    except (TypeError, ValueError) as exc:
        raise ValueError("Missing or invalid runtime-owned operation key.") from exc
    return value


def _validate_runtime_identity(value: str, prefix: str) -> None:
    if not isinstance(value, str) or not value.startswith(f"{prefix}_"):
        raise IdempotencyStoreCorruptionError(
            f"Idempotency {prefix} identity is invalid."
        )
    suffix = value[len(prefix) + 1 :]
    if len(suffix) != 32:
        raise IdempotencyStoreCorruptionError(
            f"Idempotency {prefix} identity is invalid."
        )
    try:
        uuid.UUID(hex=suffix)
    except ValueError as exc:
        raise IdempotencyStoreCorruptionError(
            f"Idempotency {prefix} identity is invalid."
        ) from exc


def _parse_record_timestamp(value: str) -> dt.datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise IdempotencyStoreCorruptionError(
            "Idempotency record timestamp is invalid."
        )
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IdempotencyStoreCorruptionError(
            "Idempotency record timestamp is invalid."
        ) from exc
    if parsed.tzinfo is None:
        raise IdempotencyStoreCorruptionError(
            "Idempotency record timestamp must include UTC offset information."
        )
    return parsed.astimezone(dt.UTC)


@dataclass(frozen=True)
class OperationContext:
    """Runtime-owned logical-operation identity reusable across trusted retries."""

    operation_key: str

    def __post_init__(self) -> None:
        _validate_operation_key(self.operation_key)

    @classmethod
    def new_operation(cls) -> OperationContext:
        return cls(_new_operation_key())

    def identity_fields(self) -> dict[str, str]:
        return {"operation_key": self.operation_key}


@dataclass(frozen=True)
class IdempotencyRecord:
    schema_version: str
    operation_key: str
    project_scope: str
    request_id: str
    trace_id: str
    action_id: str
    model_call_id: str | None
    action_fingerprint: str
    capability_class: str
    state: IdempotencyState
    created_at: str
    updated_at: str
    reason_code: str
    terminal_receipt: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation_key": self.operation_key,
            "project_scope": self.project_scope,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "action_id": self.action_id,
            "model_call_id": self.model_call_id,
            "action_fingerprint": self.action_fingerprint,
            "capability_class": self.capability_class,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reason_code": self.reason_code,
            "terminal_receipt": self.terminal_receipt,
        }

    @classmethod
    def from_payload(cls, payload: object) -> IdempotencyRecord:
        if not isinstance(payload, dict):
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record must be one JSON object."
            )
        if set(payload) != IDEMPOTENCY_RECORD_FIELDS:
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record fields do not match its exact schema."
            )
        string_fields = IDEMPOTENCY_RECORD_FIELDS - {
            "model_call_id",
            "terminal_receipt",
        }
        if any(not isinstance(payload[field], str) for field in string_fields):
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record fields have invalid types."
            )
        if payload["model_call_id"] is not None and not isinstance(
            payload["model_call_id"], str
        ):
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency model-call identity has an invalid type."
            )
        if payload["terminal_receipt"] is not None and not isinstance(
            payload["terminal_receipt"], dict
        ):
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency terminal receipt has an invalid type."
            )
        try:
            record = cls(
                schema_version=payload["schema_version"],
                operation_key=payload["operation_key"],
                project_scope=payload["project_scope"],
                request_id=payload["request_id"],
                trace_id=payload["trace_id"],
                action_id=payload["action_id"],
                model_call_id=(
                    payload["model_call_id"]
                    if payload.get("model_call_id") is not None
                    else None
                ),
                action_fingerprint=payload["action_fingerprint"],
                capability_class=payload["capability_class"],
                state=IdempotencyState(payload["state"]),
                created_at=payload["created_at"],
                updated_at=payload["updated_at"],
                reason_code=payload["reason_code"],
                terminal_receipt=(
                    dict(payload["terminal_receipt"])
                    if payload.get("terminal_receipt") is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record does not match its schema."
            ) from exc
        record.validate()
        return record

    def validate(self) -> None:
        if self.schema_version != IDEMPOTENCY_SCHEMA_VERSION:
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record has an unsupported schema version."
            )
        try:
            _validate_operation_key(self.operation_key)
        except (TypeError, ValueError) as exc:
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record has an invalid operation key."
            ) from exc
        if not _HEX_DIGEST.fullmatch(self.project_scope):
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record has an invalid project scope."
            )
        if not _HEX_DIGEST.fullmatch(self.action_fingerprint):
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record has an invalid action fingerprint."
            )
        if self.state is IdempotencyState.CONFLICT:
            raise IdempotencyStoreCorruptionError(
                "A conflict resolution cannot replace the authoritative operation record."
            )
        _validate_runtime_identity(self.request_id, "request")
        _validate_runtime_identity(self.trace_id, "trace")
        _validate_runtime_identity(self.action_id, "action")
        if self.model_call_id is not None:
            _validate_runtime_identity(self.model_call_id, "model_call")
        if self.capability_class not in {item.value for item in CapabilityClass}:
            raise IdempotencyStoreCorruptionError(
                "Idempotency capability class is invalid."
            )
        if not _SAFE_REASON_CODE.fullmatch(self.reason_code):
            raise IdempotencyStoreCorruptionError(
                "Idempotency reason code is invalid."
            )
        expected_reason = IDEMPOTENCY_STATE_REASON_CODES.get(self.state)
        if expected_reason is None or self.reason_code != expected_reason:
            raise IdempotencyStoreCorruptionError(
                "Idempotency reason code does not match the authoritative state."
            )
        created_at = _parse_record_timestamp(self.created_at)
        updated_at = _parse_record_timestamp(self.updated_at)
        if updated_at < created_at:
            raise IdempotencyStoreCorruptionError(
                "Idempotency record update time precedes creation time."
            )
        if self.terminal_receipt is not None and self.state not in TERMINAL_STATES:
            raise IdempotencyStoreCorruptionError(
                "Non-terminal idempotency state contains a terminal receipt."
            )
        if self.state in TERMINAL_STATES and self.terminal_receipt is None:
            raise IdempotencyStoreCorruptionError(
                "Terminal idempotency state is missing its bounded receipt."
            )
        if self.terminal_receipt is not None:
            _validate_safe_receipt(self.terminal_receipt)
            _validate_state_receipt_invariants(self.state, self.terminal_receipt)


@dataclass(frozen=True)
class IdempotencyResolution:
    kind: IdempotencyResolutionKind
    record: IdempotencyRecord
    dispatch_allowed: bool
    replayed: bool
    reason_code: str


def project_scope_fingerprint(project_dir: Path) -> str:
    canonical = str(Path(project_dir).resolve()).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def canonical_action_fingerprint(
    action: Mapping[str, Any],
    *,
    project_dir: Path,
    capability_class: CapabilityClass,
) -> str:
    """Hash only semantic handler inputs plus project and capability scope."""

    action_name = str(action.get("action", "")).strip()
    semantic_fields = ACTION_SEMANTIC_FIELDS.get(action_name)
    if semantic_fields is None:
        raise IdempotencyError(
            "Unclassified actions cannot receive an idempotency fingerprint."
        )
    semantic_parameters = {
        field: _json_safe_hash_value(action.get(field)) for field in semantic_fields
    }
    try:
        capability_value = CapabilityClass(
            getattr(capability_class, "value", capability_class)
        ).value
    except (TypeError, ValueError) as exc:
        raise IdempotencyError(
            "Unclassified capability cannot receive an idempotency fingerprint."
        ) from exc
    canonical = {
        "schema_version": IDEMPOTENCY_SCHEMA_VERSION,
        "project_scope": project_scope_fingerprint(project_dir),
        "capability_class": capability_value,
        "action": action_name,
        "parameters": semantic_parameters,
    }
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_safe_receipt(receipt: Mapping[str, Any]) -> None:
    if set(receipt) - IDEMPOTENCY_RECEIPT_FIELDS:
        raise IdempotencyStoreCorruptionError(
            "Idempotency terminal receipt contains non-allowlisted fields."
        )
    if receipt.get("receipt_schema_version") != "AOIA_IDEMPOTENCY_RECEIPT_1A":
        raise IdempotencyStoreCorruptionError(
            "Idempotency terminal receipt has an unsupported schema version."
        )
    result_hash = receipt.get("result_hash")
    if result_hash is not None and (
        not isinstance(result_hash, str) or not _HEX_DIGEST.fullmatch(result_hash)
    ):
        raise IdempotencyStoreCorruptionError(
            "Idempotency terminal receipt has an invalid result hash."
        )
    for field in (
        "success",
        "blocked",
        "cancelled",
        "timed_out",
        "unknown_outcome",
        "stop_loop",
    ):
        if field in receipt and not isinstance(receipt[field], bool):
            raise IdempotencyStoreCorruptionError(
                "Idempotency terminal receipt has an invalid boolean field."
            )
    for field in (
        "exit_code",
        "bytes_written",
        "page_count",
        "omitted_field_count",
    ):
        if field in receipt and (
            not isinstance(receipt[field], int) or isinstance(receipt[field], bool)
        ):
            raise IdempotencyStoreCorruptionError(
                "Idempotency terminal receipt has an invalid integer field."
            )


def _validate_state_receipt_invariants(
    state: IdempotencyState,
    receipt: Mapping[str, Any],
) -> None:
    success = receipt.get("success")
    if state is IdempotencyState.SUCCEEDED:
        if success is not True:
            raise IdempotencyStoreCorruptionError(
                "SUCCEEDED idempotency state requires a successful receipt."
            )
        if any(
            receipt.get(field) is True
            for field in ("blocked", "cancelled", "timed_out", "unknown_outcome")
        ):
            raise IdempotencyStoreCorruptionError(
                "SUCCEEDED idempotency receipt contains a contradictory outcome."
            )
        return
    if success is not False:
        raise IdempotencyStoreCorruptionError(
            "Non-success idempotency state requires success=false."
        )
    cancelled = receipt.get("cancelled") is True
    timed_out = receipt.get("timed_out") is True
    unknown_outcome = receipt.get("unknown_outcome") is True
    if state is IdempotencyState.CANCELLED and not cancelled:
        raise IdempotencyStoreCorruptionError(
            "CANCELLED idempotency state requires cancelled=true."
        )
    if state is not IdempotencyState.CANCELLED and cancelled:
        raise IdempotencyStoreCorruptionError(
            "Only CANCELLED idempotency state may carry cancelled=true."
        )
    if state is IdempotencyState.BLOCKED and receipt.get("blocked") is not True:
        raise IdempotencyStoreCorruptionError(
            "BLOCKED idempotency state requires blocked=true."
        )
    uncertain_states = {
        IdempotencyState.TIMED_OUT_OR_UNKNOWN,
        IdempotencyState.UNKNOWN_OUTCOME,
    }
    if state not in uncertain_states and (timed_out or unknown_outcome):
        raise IdempotencyStoreCorruptionError(
            "Only uncertain idempotency states may carry uncertainty flags."
        )
    if state is IdempotencyState.TIMED_OUT_OR_UNKNOWN and not (
        timed_out or unknown_outcome
    ):
        raise IdempotencyStoreCorruptionError(
            "Timed/uncertain idempotency state requires an explicit uncertain receipt."
        )
    if state is IdempotencyState.UNKNOWN_OUTCOME and not unknown_outcome:
        raise IdempotencyStoreCorruptionError(
            "UNKNOWN_OUTCOME state requires unknown_outcome=true."
        )


def build_safe_result_receipt(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded replay metadata without raw content, output, or secrets."""

    receipt: dict[str, Any] = {
        "receipt_schema_version": "AOIA_IDEMPOTENCY_RECEIPT_1A",
        "success": result.get("success") is True,
        "result_hash": hashlib.sha256(
            json.dumps(
                _json_safe_hash_value(result),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest(),
    }
    safe_boolean_fields = (
        "success",
        "blocked",
        "cancelled",
        "timed_out",
        "unknown_outcome",
        "stop_loop",
    )
    safe_integer_fields = ("exit_code", "bytes_written", "page_count")
    for field in safe_boolean_fields:
        if isinstance(result.get(field), bool):
            receipt[field] = result[field]
    for field in safe_integer_fields:
        value = result.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            receipt[field] = value
    receipt["omitted_field_count"] = max(0, len(result) - len(receipt) + 2)
    _validate_safe_receipt(receipt)
    return receipt


class DurableIdempotencyStore:
    """Project-scoped, per-operation durable idempotency state machine."""

    def __init__(
        self,
        state_dir: Path,
        *,
        lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
        clock: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self.state_dir = Path(state_dir).resolve()
        self.root_dir = self.state_dir / "idempotency"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.lock_timeout_seconds = validate_lock_timeout_seconds(
            lock_timeout_seconds
        )
        self._clock = clock or (lambda: dt.datetime.now(dt.UTC))

    def record_path(self, operation_key: str) -> Path:
        key = _validate_operation_key(operation_key)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root_dir / f"{digest}.json"

    def load(self, operation: OperationContext) -> IdempotencyRecord | None:
        path = self.record_path(operation.operation_key)
        try:
            payload = read_json_snapshot(path)
        except StateCorruptionError as exc:
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record is corrupt."
            ) from exc
        if payload is None:
            return None
        record = IdempotencyRecord.from_payload(payload)
        if record.operation_key != operation.operation_key:
            raise IdempotencyStoreCorruptionError(
                "Durable idempotency record key does not match its resource."
            )
        return record

    def reserve(
        self,
        operation: OperationContext,
        *,
        action_context: Any,
        action_fingerprint: str,
        capability_class: CapabilityClass,
        project_scope: str,
    ) -> IdempotencyResolution:
        if not _HEX_DIGEST.fullmatch(action_fingerprint):
            raise ValueError("action fingerprint must be a SHA-256 digest")
        if not _HEX_DIGEST.fullmatch(project_scope):
            raise ValueError("project scope must be a SHA-256 digest")
        try:
            capability_value = CapabilityClass(
                getattr(capability_class, "value", capability_class)
            ).value
        except (TypeError, ValueError) as exc:
            raise IdempotencyError(
                "Cannot reserve an operation with an invalid capability class."
            ) from exc
        now = self._timestamp()
        candidate = IdempotencyRecord(
            schema_version=IDEMPOTENCY_SCHEMA_VERSION,
            operation_key=operation.operation_key,
            project_scope=project_scope,
            request_id=action_context.request_id,
            trace_id=action_context.trace_id,
            action_id=action_context.action_id,
            model_call_id=action_context.model_call_id,
            action_fingerprint=action_fingerprint,
            capability_class=capability_value,
            state=IdempotencyState.RESERVED,
            created_at=now,
            updated_at=now,
            reason_code=IDEMPOTENCY_RESERVED_REASON_CODE,
        )
        candidate.validate()
        path = self.record_path(operation.operation_key)

        def update(current: Any | None) -> tuple[Any, IdempotencyResolution]:
            if current is None:
                return candidate.to_payload(), IdempotencyResolution(
                    kind=IdempotencyResolutionKind.RESERVED,
                    record=candidate,
                    dispatch_allowed=True,
                    replayed=False,
                    reason_code=IDEMPOTENCY_RESERVED_REASON_CODE,
                )
            existing = IdempotencyRecord.from_payload(current)
            if existing.operation_key != operation.operation_key:
                raise IdempotencyStoreCorruptionError(
                    "Durable idempotency record key does not match its resource."
                )
            resolution = self._resolve_existing(existing, candidate)
            return existing.to_payload(), resolution

        return locked_update_json(
            path,
            update,
            lock_path=state_resource_lock_path(self.state_dir, path),
            lock_timeout_seconds=self.lock_timeout_seconds,
            sort_keys=True,
        )

    def transition(
        self,
        operation: OperationContext,
        *,
        owner_action_id: str,
        action_fingerprint: str,
        to_state: IdempotencyState,
        reason_code: str,
        terminal_receipt: dict[str, Any] | None = None,
    ) -> IdempotencyRecord:
        try:
            canonical_state = IdempotencyState(getattr(to_state, "value", to_state))
        except (TypeError, ValueError) as exc:
            raise IdempotencyTransitionError(
                "Cannot transition to an invalid idempotency state."
            ) from exc
        if canonical_state is IdempotencyState.CONFLICT:
            raise IdempotencyTransitionError(
                "A conflict cannot replace the authoritative operation record."
            )
        expected_reason_code = IDEMPOTENCY_STATE_REASON_CODES[canonical_state]
        if reason_code != expected_reason_code:
            raise IdempotencyTransitionError(
                "Transition reason must be the fixed runtime-owned code for its state."
            )
        path = self.record_path(operation.operation_key)

        def update(current: Any | None) -> tuple[Any, IdempotencyRecord]:
            if current is None:
                raise IdempotencyTransitionError(
                    "Cannot transition an operation that has not been reserved."
                )
            existing = IdempotencyRecord.from_payload(current)
            if existing.operation_key != operation.operation_key:
                raise IdempotencyStoreCorruptionError(
                    "Durable idempotency record key does not match its resource."
                )
            if existing.action_fingerprint != action_fingerprint:
                raise IdempotencyTransitionError(
                    "Cannot transition an operation using a different fingerprint."
                )
            if existing.action_id != owner_action_id:
                raise IdempotencyOwnerMismatchError(
                    "Only the action that reserved an operation may transition it."
                )
            if existing.state is canonical_state:
                return existing.to_payload(), existing
            allowed = VALID_TRANSITIONS.get(existing.state, frozenset())
            if canonical_state not in allowed:
                raise IdempotencyTransitionError(
                    "Illegal idempotency state transition."
                )
            if canonical_state in TERMINAL_STATES and terminal_receipt is None:
                raise IdempotencyTransitionError(
                    "Terminal idempotency transition requires a bounded receipt."
                )
            if canonical_state not in TERMINAL_STATES and terminal_receipt is not None:
                raise IdempotencyTransitionError(
                    "Non-terminal idempotency transition cannot store a terminal receipt."
                )
            replacement = replace(
                existing,
                state=canonical_state,
                updated_at=self._timestamp(),
                reason_code=expected_reason_code,
                terminal_receipt=terminal_receipt,
            )
            replacement.validate()
            return replacement.to_payload(), replacement

        return locked_update_json(
            path,
            update,
            lock_path=state_resource_lock_path(self.state_dir, path),
            lock_timeout_seconds=self.lock_timeout_seconds,
            sort_keys=True,
        )

    @staticmethod
    def _resolve_existing(
        existing: IdempotencyRecord,
        candidate: IdempotencyRecord,
    ) -> IdempotencyResolution:
        if (
            existing.action_fingerprint != candidate.action_fingerprint
            or existing.project_scope != candidate.project_scope
            or existing.capability_class != candidate.capability_class
        ):
            return IdempotencyResolution(
                kind=IdempotencyResolutionKind.CONFLICT,
                record=existing,
                dispatch_allowed=False,
                replayed=False,
                reason_code=IDEMPOTENCY_KEY_CONFLICT_REASON_CODE,
            )
        if existing.state is IdempotencyState.RESERVED:
            return IdempotencyResolution(
                kind=IdempotencyResolutionKind.IN_PROGRESS,
                record=existing,
                dispatch_allowed=False,
                replayed=False,
                reason_code=IDEMPOTENCY_OPERATION_IN_PROGRESS_REASON_CODE,
            )
        if existing.state in {
            IdempotencyState.DISPATCH_STARTED,
            IdempotencyState.TIMED_OUT_OR_UNKNOWN,
            IdempotencyState.UNKNOWN_OUTCOME,
        }:
            return IdempotencyResolution(
                kind=IdempotencyResolutionKind.UNKNOWN_OUTCOME,
                record=existing,
                dispatch_allowed=False,
                replayed=False,
                reason_code=IDEMPOTENCY_UNKNOWN_OUTCOME_REASON_CODE,
            )
        if existing.state in TERMINAL_STATES:
            return IdempotencyResolution(
                kind=IdempotencyResolutionKind.REPLAYED,
                record=existing,
                dispatch_allowed=False,
                replayed=True,
                reason_code=IDEMPOTENCY_REPLAYED_REASON_CODE,
            )
        raise IdempotencyStoreCorruptionError(
            "Durable idempotency record contains an unsupported state."
        )

    def _timestamp(self) -> str:
        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def _json_safe_hash_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else type(value).__name__
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {"bytes_sha256": hashlib.sha256(value).hexdigest(), "length": len(value)}
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe_hash_value(item)
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe_hash_value(item) for item in value]
    return {"unsupported_type": type(value).__name__}


if set(ACTION_SEMANTIC_FIELDS) != set(ALLOWED_ACTIONS):
    raise RuntimeError(
        "Every canonical action must define explicit idempotency fingerprint semantics."
    )
