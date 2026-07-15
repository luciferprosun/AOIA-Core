from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, BinaryIO, Mapping


AUDIT_LEDGER_SCHEMA_VERSION = "audit-ledger-1a"
AUDIT_LEDGER_GENESIS_PREVIOUS_HASH = hashlib.sha256(
    b"AOIA-Core/audit-ledger-1a/genesis"
).hexdigest()
AUDIT_LEDGER_MAX_EVENT_TYPE_LENGTH = 128

_ENTRY_FIELDS = frozenset(
    {
        "schema_version",
        "sequence",
        "event_type",
        "payload",
        "previous_hash",
        "entry_hash",
    }
)
_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class AuditLedgerVerificationStatus(str, Enum):
    VALID = "VALID"
    EMPTY_VALID = "EMPTY_VALID"
    INVALID_PATH = "INVALID_PATH"
    IO_ERROR = "IO_ERROR"
    INVALID_UTF8 = "INVALID_UTF8"
    INCOMPLETE_FINAL_LINE = "INCOMPLETE_FINAL_LINE"
    MALFORMED_JSON = "MALFORMED_JSON"
    NON_CANONICAL_JSON = "NON_CANONICAL_JSON"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    SEQUENCE_MISMATCH = "SEQUENCE_MISMATCH"
    PREVIOUS_HASH_MISMATCH = "PREVIOUS_HASH_MISMATCH"
    ENTRY_HASH_MISMATCH = "ENTRY_HASH_MISMATCH"
    EXPECTED_TIP_MISMATCH = "EXPECTED_TIP_MISMATCH"
    TRUNCATED_LEDGER = "TRUNCATED_LEDGER"


class AuditLedgerAppendStatus(str, Enum):
    APPENDED = "APPENDED"
    INVALID_PATH = "INVALID_PATH"
    INVALID_EVENT_TYPE = "INVALID_EVENT_TYPE"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    EXISTING_LEDGER_INVALID = "EXISTING_LEDGER_INVALID"
    IO_ERROR = "IO_ERROR"


@dataclass(frozen=True, slots=True)
class AuditLedgerEntry:
    schema_version: str
    sequence: int
    event_type: str
    payload: Any
    previous_hash: str
    entry_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != AUDIT_LEDGER_SCHEMA_VERSION:
            raise ValueError("unsupported audit ledger schema version")
        sequence = _positive_integer(self.sequence, "sequence")
        event_type = _validated_event_type(self.event_type)
        previous_hash = _validated_hash(self.previous_hash, "previous_hash")
        entry_hash = _validated_hash(self.entry_hash, "entry_hash")
        payload = _strict_json_copy(self.payload)
        expected_hash = _compute_entry_hash(
            schema_version=self.schema_version,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
            previous_hash=previous_hash,
        )
        if entry_hash != expected_hash:
            raise ValueError("entry_hash does not match canonical entry content")

        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "payload", _freeze_json(payload))
        object.__setattr__(self, "previous_hash", previous_hash)
        object.__setattr__(self, "entry_hash", entry_hash)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "payload": _thaw_json(self.payload),
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


@dataclass(frozen=True, slots=True)
class AuditLedgerTip:
    record_count: int
    last_sequence: int
    last_entry_hash: str

    def __post_init__(self) -> None:
        record_count = _non_negative_integer(self.record_count, "record_count")
        last_sequence = _non_negative_integer(self.last_sequence, "last_sequence")
        last_entry_hash = _validated_hash(self.last_entry_hash, "last_entry_hash")
        if record_count != last_sequence:
            raise ValueError("record_count must equal last_sequence")
        if record_count == 0 and last_entry_hash != AUDIT_LEDGER_GENESIS_PREVIOUS_HASH:
            raise ValueError("empty ledger tip must use the deterministic genesis hash")

        object.__setattr__(self, "record_count", record_count)
        object.__setattr__(self, "last_sequence", last_sequence)
        object.__setattr__(self, "last_entry_hash", last_entry_hash)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_count": self.record_count,
            "last_sequence": self.last_sequence,
            "last_entry_hash": self.last_entry_hash,
        }


@dataclass(frozen=True, slots=True)
class AuditLedgerVerificationResult:
    valid: bool
    status: AuditLedgerVerificationStatus
    record_count: int
    last_sequence: int
    last_entry_hash: str
    failure_line: int | None
    failure_reason: str

    def __post_init__(self) -> None:
        if type(self.valid) is not bool:
            raise TypeError("valid must be bool")
        status = AuditLedgerVerificationStatus(self.status)
        record_count = _non_negative_integer(self.record_count, "record_count")
        last_sequence = _non_negative_integer(self.last_sequence, "last_sequence")
        last_entry_hash = _validated_hash(self.last_entry_hash, "last_entry_hash")
        if record_count != last_sequence:
            raise ValueError("record_count must equal last_sequence")
        if self.failure_line is not None:
            _positive_integer(self.failure_line, "failure_line")
        if type(self.failure_reason) is not str:
            raise TypeError("failure_reason must be a string")
        success_statuses = {
            AuditLedgerVerificationStatus.VALID,
            AuditLedgerVerificationStatus.EMPTY_VALID,
        }
        if self.valid != (status in success_statuses):
            raise ValueError("valid does not match verification status")
        if self.valid and (self.failure_line is not None or self.failure_reason):
            raise ValueError("valid verification cannot contain failure details")
        if not self.valid and not self.failure_reason:
            raise ValueError("invalid verification must contain a failure reason")

        object.__setattr__(self, "status", status)
        object.__setattr__(self, "record_count", record_count)
        object.__setattr__(self, "last_sequence", last_sequence)
        object.__setattr__(self, "last_entry_hash", last_entry_hash)

    @property
    def tip(self) -> AuditLedgerTip:
        return AuditLedgerTip(
            record_count=self.record_count,
            last_sequence=self.last_sequence,
            last_entry_hash=self.last_entry_hash,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "status": self.status.value,
            "record_count": self.record_count,
            "last_sequence": self.last_sequence,
            "last_entry_hash": self.last_entry_hash,
            "failure_line": self.failure_line,
            "failure_reason": self.failure_reason,
        }


@dataclass(frozen=True, slots=True)
class AuditLedgerAppendResult:
    appended: bool
    status: AuditLedgerAppendStatus
    entry: AuditLedgerEntry | None
    tip: AuditLedgerTip | None
    verification_status: AuditLedgerVerificationStatus | None
    failure_reason: str

    def __post_init__(self) -> None:
        if type(self.appended) is not bool:
            raise TypeError("appended must be bool")
        status = AuditLedgerAppendStatus(self.status)
        verification_status = (
            None
            if self.verification_status is None
            else AuditLedgerVerificationStatus(self.verification_status)
        )
        if self.appended:
            if status is not AuditLedgerAppendStatus.APPENDED:
                raise ValueError("successful append must use APPENDED status")
            if self.entry is None or self.tip is None or self.failure_reason:
                raise ValueError("successful append must contain entry and tip only")
        elif status is AuditLedgerAppendStatus.APPENDED or not self.failure_reason:
            raise ValueError("failed append must contain a failure status and reason")

        object.__setattr__(self, "status", status)
        object.__setattr__(self, "verification_status", verification_status)


class AuditLedgerReadError(ValueError):
    def __init__(self, verification: AuditLedgerVerificationResult) -> None:
        self.verification = verification
        super().__init__(verification.failure_reason)


def canonical_audit_ledger_json(value: Any) -> str:
    validated = _strict_json_copy(value)
    return json.dumps(
        validated,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def append_audit_entry(
    ledger_path: str | Path,
    event_type: str,
    payload: Any,
) -> AuditLedgerAppendResult:
    try:
        path = _validated_ledger_path(ledger_path)
    except (TypeError, ValueError, OSError) as exc:
        return _append_failure(AuditLedgerAppendStatus.INVALID_PATH, str(exc))

    try:
        validated_event_type = _validated_event_type(event_type)
    except (TypeError, ValueError, UnicodeError) as exc:
        return _append_failure(AuditLedgerAppendStatus.INVALID_EVENT_TYPE, str(exc))

    try:
        validated_payload = _strict_json_copy(payload)
        canonical_audit_ledger_json(validated_payload).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        return _append_failure(AuditLedgerAppendStatus.INVALID_PAYLOAD, str(exc))

    try:
        handle = _open_append_handle(path)
    except OSError as exc:
        return _append_failure(AuditLedgerAppendStatus.IO_ERROR, str(exc))

    with handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            return _append_failure(AuditLedgerAppendStatus.IO_ERROR, str(exc))
        try:
            handle.seek(0)
            existing_bytes = handle.read()
            verification, entries = _verify_bytes(existing_bytes, expected_tip=None)
            if not verification.valid:
                return _append_failure(
                    AuditLedgerAppendStatus.EXISTING_LEDGER_INVALID,
                    "existing audit ledger failed closed verification: "
                    + verification.failure_reason,
                    verification_status=verification.status,
                )

            previous_hash = (
                entries[-1].entry_hash
                if entries
                else AUDIT_LEDGER_GENESIS_PREVIOUS_HASH
            )
            entry = _create_entry(
                sequence=len(entries) + 1,
                event_type=validated_event_type,
                payload=validated_payload,
                previous_hash=previous_hash,
            )
            encoded_line = (
                canonical_audit_ledger_json(entry.to_dict()).encode("utf-8") + b"\n"
            )
            handle.seek(0, os.SEEK_END)
            written = handle.write(encoded_line)
            if written != len(encoded_line):
                raise OSError("audit ledger append did not write one complete record")
            handle.flush()
            os.fsync(handle.fileno())
            tip = AuditLedgerTip(
                record_count=entry.sequence,
                last_sequence=entry.sequence,
                last_entry_hash=entry.entry_hash,
            )
            return AuditLedgerAppendResult(
                appended=True,
                status=AuditLedgerAppendStatus.APPENDED,
                entry=entry,
                tip=tip,
                verification_status=verification.status,
                failure_reason="",
            )
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def read_audit_ledger(ledger_path: str | Path) -> tuple[AuditLedgerEntry, ...]:
    verification, entries = _load_and_verify(ledger_path, expected_tip=None)
    if not verification.valid:
        raise AuditLedgerReadError(verification)
    return entries


def verify_audit_ledger(
    ledger_path: str | Path,
    expected_tip: AuditLedgerTip | None = None,
) -> AuditLedgerVerificationResult:
    verification, _entries = _load_and_verify(ledger_path, expected_tip=expected_tip)
    return verification


def _load_and_verify(
    ledger_path: str | Path,
    *,
    expected_tip: AuditLedgerTip | None,
) -> tuple[AuditLedgerVerificationResult, tuple[AuditLedgerEntry, ...]]:
    if expected_tip is not None and type(expected_tip) is not AuditLedgerTip:
        return (
            _verification_failure(
                AuditLedgerVerificationStatus.SCHEMA_INVALID,
                "expected_tip must be an AuditLedgerTip",
            ),
            (),
        )
    try:
        path = _validated_ledger_path(ledger_path)
    except (TypeError, ValueError, OSError) as exc:
        return (
            _verification_failure(AuditLedgerVerificationStatus.INVALID_PATH, str(exc)),
            (),
        )

    try:
        if path.is_symlink():
            return (
                _verification_failure(
                    AuditLedgerVerificationStatus.INVALID_PATH,
                    "audit ledger path must not be a symbolic link",
                ),
                (),
            )
        if not path.exists():
            return _verify_bytes(b"", expected_tip=expected_tip)
        if not path.is_file():
            return (
                _verification_failure(
                    AuditLedgerVerificationStatus.INVALID_PATH,
                    "audit ledger path must be a regular file",
                ),
                (),
            )
        handle = _open_read_handle(path)
    except OSError as exc:
        return (
            _verification_failure(AuditLedgerVerificationStatus.IO_ERROR, str(exc)),
            (),
        )

    with handle:
        locked = False
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
            locked = True
            data = handle.read()
        except OSError as exc:
            return (
                _verification_failure(AuditLedgerVerificationStatus.IO_ERROR, str(exc)),
                (),
            )
        finally:
            if locked:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return _verify_bytes(data, expected_tip=expected_tip)


def _verify_bytes(
    data: bytes,
    *,
    expected_tip: AuditLedgerTip | None,
) -> tuple[AuditLedgerVerificationResult, tuple[AuditLedgerEntry, ...]]:
    try:
        decoded = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return (
            _verification_failure(
                AuditLedgerVerificationStatus.INVALID_UTF8,
                "audit ledger is not valid UTF-8",
                failure_line=_line_number_for_offset(data, exc.start),
            ),
            (),
        )

    if not data:
        return _verified_result((), expected_tip=expected_tip)
    if not data.endswith(b"\n"):
        return (
            _verification_failure(
                AuditLedgerVerificationStatus.INCOMPLETE_FINAL_LINE,
                "audit ledger final record is not newline-terminated",
                failure_line=decoded.count("\n") + 1,
            ),
            (),
        )

    entries: list[AuditLedgerEntry] = []
    previous_hash = AUDIT_LEDGER_GENESIS_PREVIOUS_HASH
    lines = decoded.split("\n")[:-1]
    for line_number, line in enumerate(lines, start=1):
        if not line:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.SCHEMA_INVALID,
                    "blank JSONL records are forbidden",
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )
        try:
            decoded_entry = json.loads(
                line,
                object_pairs_hook=_object_without_duplicate_fields,
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.MALFORMED_JSON,
                    f"malformed JSON record: {exc}",
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )
        if type(decoded_entry) is not dict:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.SCHEMA_INVALID,
                    "audit ledger record must be a JSON object",
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )
        if set(decoded_entry) != _ENTRY_FIELDS:
            missing = sorted(_ENTRY_FIELDS - set(decoded_entry))
            extra = sorted(set(decoded_entry) - _ENTRY_FIELDS)
            details = []
            if missing:
                details.append("missing fields: " + ", ".join(missing))
            if extra:
                details.append("unknown fields: " + ", ".join(extra))
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.SCHEMA_INVALID,
                    "; ".join(details),
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )

        schema_version = decoded_entry["schema_version"]
        sequence = decoded_entry["sequence"]
        event_type = decoded_entry["event_type"]
        payload = decoded_entry["payload"]
        record_previous_hash = decoded_entry["previous_hash"]
        entry_hash = decoded_entry["entry_hash"]
        try:
            if schema_version != AUDIT_LEDGER_SCHEMA_VERSION:
                raise ValueError("unsupported audit ledger schema version")
            sequence = _positive_integer(sequence, "sequence")
            event_type = _validated_event_type(event_type)
            payload = _strict_json_copy(payload)
            record_previous_hash = _validated_hash(
                record_previous_hash, "previous_hash"
            )
            entry_hash = _validated_hash(entry_hash, "entry_hash")
        except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.SCHEMA_INVALID,
                    str(exc),
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )

        try:
            canonical_line = canonical_audit_ledger_json(decoded_entry)
        except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.SCHEMA_INVALID,
                    str(exc),
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )
        if line != canonical_line:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.NON_CANONICAL_JSON,
                    "audit ledger record is not canonical JSON",
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )

        expected_sequence = len(entries) + 1
        if sequence != expected_sequence:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.SEQUENCE_MISMATCH,
                    f"expected sequence {expected_sequence}, found {sequence}",
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )
        if record_previous_hash != previous_hash:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.PREVIOUS_HASH_MISMATCH,
                    "previous_hash does not reference the preceding entry",
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )
        expected_entry_hash = _compute_entry_hash(
            schema_version=schema_version,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
            previous_hash=record_previous_hash,
        )
        if entry_hash != expected_entry_hash:
            return (
                _verification_failure_from_entries(
                    AuditLedgerVerificationStatus.ENTRY_HASH_MISMATCH,
                    "entry_hash does not match canonical entry content",
                    entries,
                    failure_line=line_number,
                ),
                tuple(entries),
            )

        entry = AuditLedgerEntry(
            schema_version=schema_version,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
            previous_hash=record_previous_hash,
            entry_hash=entry_hash,
        )
        entries.append(entry)
        previous_hash = entry.entry_hash

    return _verified_result(tuple(entries), expected_tip=expected_tip)


def _verified_result(
    entries: tuple[AuditLedgerEntry, ...],
    *,
    expected_tip: AuditLedgerTip | None,
) -> tuple[AuditLedgerVerificationResult, tuple[AuditLedgerEntry, ...]]:
    tip = (
        EMPTY_AUDIT_LEDGER_TIP
        if not entries
        else AuditLedgerTip(
            record_count=len(entries),
            last_sequence=entries[-1].sequence,
            last_entry_hash=entries[-1].entry_hash,
        )
    )
    if expected_tip is not None and tip != expected_tip:
        if tip.record_count < expected_tip.record_count:
            status = AuditLedgerVerificationStatus.TRUNCATED_LEDGER
            reason = "audit ledger is shorter than the independently retained expected tip"
        else:
            status = AuditLedgerVerificationStatus.EXPECTED_TIP_MISMATCH
            reason = "audit ledger does not match the independently retained expected tip"
        return (
            AuditLedgerVerificationResult(
                valid=False,
                status=status,
                record_count=tip.record_count,
                last_sequence=tip.last_sequence,
                last_entry_hash=tip.last_entry_hash,
                failure_line=None,
                failure_reason=reason,
            ),
            entries,
        )

    status = (
        AuditLedgerVerificationStatus.EMPTY_VALID
        if not entries
        else AuditLedgerVerificationStatus.VALID
    )
    return (
        AuditLedgerVerificationResult(
            valid=True,
            status=status,
            record_count=tip.record_count,
            last_sequence=tip.last_sequence,
            last_entry_hash=tip.last_entry_hash,
            failure_line=None,
            failure_reason="",
        ),
        entries,
    )


def _verification_failure(
    status: AuditLedgerVerificationStatus,
    reason: str,
    *,
    failure_line: int | None = None,
) -> AuditLedgerVerificationResult:
    return AuditLedgerVerificationResult(
        valid=False,
        status=status,
        record_count=0,
        last_sequence=0,
        last_entry_hash=AUDIT_LEDGER_GENESIS_PREVIOUS_HASH,
        failure_line=failure_line,
        failure_reason=reason,
    )


def _verification_failure_from_entries(
    status: AuditLedgerVerificationStatus,
    reason: str,
    entries: list[AuditLedgerEntry],
    *,
    failure_line: int,
) -> AuditLedgerVerificationResult:
    if entries:
        last_sequence = entries[-1].sequence
        last_entry_hash = entries[-1].entry_hash
    else:
        last_sequence = 0
        last_entry_hash = AUDIT_LEDGER_GENESIS_PREVIOUS_HASH
    return AuditLedgerVerificationResult(
        valid=False,
        status=status,
        record_count=len(entries),
        last_sequence=last_sequence,
        last_entry_hash=last_entry_hash,
        failure_line=failure_line,
        failure_reason=reason,
    )


def _append_failure(
    status: AuditLedgerAppendStatus,
    reason: str,
    *,
    verification_status: AuditLedgerVerificationStatus | None = None,
) -> AuditLedgerAppendResult:
    return AuditLedgerAppendResult(
        appended=False,
        status=status,
        entry=None,
        tip=None,
        verification_status=verification_status,
        failure_reason=reason,
    )


def _create_entry(
    *,
    sequence: int,
    event_type: str,
    payload: Any,
    previous_hash: str,
) -> AuditLedgerEntry:
    entry_hash = _compute_entry_hash(
        schema_version=AUDIT_LEDGER_SCHEMA_VERSION,
        sequence=sequence,
        event_type=event_type,
        payload=payload,
        previous_hash=previous_hash,
    )
    return AuditLedgerEntry(
        schema_version=AUDIT_LEDGER_SCHEMA_VERSION,
        sequence=sequence,
        event_type=event_type,
        payload=payload,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )


def _compute_entry_hash(
    *,
    schema_version: str,
    sequence: int,
    event_type: str,
    payload: Any,
    previous_hash: str,
) -> str:
    material = {
        "schema_version": schema_version,
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload,
        "previous_hash": previous_hash,
    }
    canonical_bytes = canonical_audit_ledger_json(material).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def _strict_json_copy(value: Any, active_ids: set[int] | None = None) -> Any:
    if active_ids is None:
        active_ids = set()
    value_type = type(value)
    if value is None or value_type in {bool, int}:
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not supported in audit payloads")
        return value
    if value_type is str:
        value.encode("utf-8", errors="strict")
        return value
    if value_type not in {dict, list}:
        raise TypeError(
            "audit payload values must use exact JSON types; unsupported type: "
            + value_type.__name__
        )

    identity = id(value)
    if identity in active_ids:
        raise ValueError("cyclic audit payloads are not supported")
    active_ids.add(identity)
    try:
        if value_type is list:
            return [_strict_json_copy(item, active_ids) for item in value]
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("audit payload object keys must be strings")
            key.encode("utf-8", errors="strict")
            copied[key] = _strict_json_copy(item, active_ids)
        return copied
    finally:
        active_ids.remove(identity)


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


def _validated_event_type(value: Any) -> str:
    if type(value) is not str:
        raise TypeError("event_type must be a string")
    value.encode("utf-8", errors="strict")
    if not value or not value.strip():
        raise ValueError("event_type must not be empty")
    if value != value.strip():
        raise ValueError("event_type must not contain surrounding whitespace")
    if len(value) > AUDIT_LEDGER_MAX_EVENT_TYPE_LENGTH:
        raise ValueError(
            f"event_type exceeds {AUDIT_LEDGER_MAX_EVENT_TYPE_LENGTH} characters"
        )
    if any(ord(character) < 0x20 for character in value):
        raise ValueError("event_type must not contain control characters")
    return value


def _validated_hash(value: Any, field_name: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a lowercase 64-character SHA-256 hash")
    return value


def _positive_integer(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _non_negative_integer(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _validated_ledger_path(value: Any) -> Path:
    if type(value) is str:
        if not value or "\x00" in value:
            raise ValueError("ledger_path must be a non-empty filesystem path")
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise TypeError("ledger_path must be a string or pathlib.Path")
    if not path.name:
        raise ValueError("ledger_path must identify a file")
    return path


def _open_append_handle(path: Path) -> BinaryIO:
    flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(path, flags, 0o600)
    try:
        return os.fdopen(file_descriptor, "a+b")
    except BaseException:
        os.close(file_descriptor)
        raise


def _open_read_handle(path: Path) -> BinaryIO:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(path, flags)
    try:
        return os.fdopen(file_descriptor, "rb")
    except BaseException:
        os.close(file_descriptor)
        raise


def _object_without_duplicate_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object field: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"non-standard JSON constant is forbidden: {value}")


def _line_number_for_offset(data: bytes, offset: int) -> int:
    return data[:offset].count(b"\n") + 1


EMPTY_AUDIT_LEDGER_TIP = AuditLedgerTip(
    record_count=0,
    last_sequence=0,
    last_entry_hash=AUDIT_LEDGER_GENESIS_PREVIOUS_HASH,
)


__all__ = [
    "AUDIT_LEDGER_GENESIS_PREVIOUS_HASH",
    "AUDIT_LEDGER_MAX_EVENT_TYPE_LENGTH",
    "AUDIT_LEDGER_SCHEMA_VERSION",
    "EMPTY_AUDIT_LEDGER_TIP",
    "AuditLedgerAppendResult",
    "AuditLedgerAppendStatus",
    "AuditLedgerEntry",
    "AuditLedgerReadError",
    "AuditLedgerTip",
    "AuditLedgerVerificationResult",
    "AuditLedgerVerificationStatus",
    "append_audit_entry",
    "canonical_audit_ledger_json",
    "read_audit_ledger",
    "verify_audit_ledger",
]
