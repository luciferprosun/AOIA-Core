from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping


DURABLE_AUDIT_SCHEMA_VERSION = "AOIA_DURABLE_AUDIT_LEDGER_1A"
DURABLE_AUDIT_GENESIS_PREVIOUS_HASH = None
_REQUIRED_EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "event_id",
        "event_type",
        "created_at",
        "payload_hash",
        "payload",
        "previous_event_hash",
        "event_hash",
    }
)
_AUTHORITY_FALSE_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "write_authority_granted",
    "execution_authority_granted",
    "provider_authority_granted",
)


@dataclass(frozen=True)
class DurableAuditEvent:
    schema_version: str
    event_id: str
    event_type: str
    created_at: str
    payload_hash: str
    payload: Any
    previous_event_hash: str | None
    event_hash: str
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text(self.schema_version, "schema_version"))
        object.__setattr__(self, "event_id", _text(self.event_id, "event_id"))
        object.__setattr__(self, "event_type", _text(self.event_type, "event_type"))
        object.__setattr__(self, "created_at", _text(self.created_at, "created_at"))
        object.__setattr__(self, "payload_hash", _full_hash(self.payload_hash, "payload_hash"))
        if self.previous_event_hash is not None:
            object.__setattr__(
                self,
                "previous_event_hash",
                _full_hash(self.previous_event_hash, "previous_event_hash"),
            )
        object.__setattr__(self, "event_hash", _full_hash(self.event_hash, "event_hash"))
        _assert_json_serializable(self.payload)
        for field_name in _AUTHORITY_FALSE_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "payload_hash": self.payload_hash,
            "payload": self.payload,
            "previous_event_hash": self.previous_event_hash,
            "event_hash": self.event_hash,
        }
        result.update({field_name: False for field_name in _AUTHORITY_FALSE_FIELDS})
        return result


@dataclass(frozen=True)
class DurableAuditAppendResult:
    appended: bool
    blocking: bool
    ledger_path: str | None
    event: DurableAuditEvent | None
    event_hash: str | None
    previous_event_hash: str | None
    reason: str
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        for field_name in _AUTHORITY_FALSE_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "appended": self.appended,
            "blocking": self.blocking,
            "ledger_path": self.ledger_path,
            "event": self.event.to_dict() if self.event is not None else None,
            "event_hash": self.event_hash,
            "previous_event_hash": self.previous_event_hash,
            "reason": self.reason,
            **{field_name: False for field_name in _AUTHORITY_FALSE_FIELDS},
        }


@dataclass(frozen=True)
class DurableAuditVerificationResult:
    valid: bool
    blocking: bool
    ledger_path: str | None
    event_count: int
    final_event_hash: str | None
    issues: tuple[str, ...]
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        for field_name in _AUTHORITY_FALSE_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "blocking": self.blocking,
            "ledger_path": self.ledger_path,
            "event_count": self.event_count,
            "final_event_hash": self.final_event_hash,
            "issues": list(self.issues),
            **{field_name: False for field_name in _AUTHORITY_FALSE_FIELDS},
        }


def canonical_audit_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def compute_audit_event_hash(event_material: Mapping[str, Any] | DurableAuditEvent) -> str:
    if isinstance(event_material, DurableAuditEvent):
        material = _event_hash_material(event_material.to_dict())
    elif isinstance(event_material, Mapping):
        material = _event_hash_material(event_material)
    else:
        raise TypeError("event_material must be a mapping or DurableAuditEvent")
    return _sha256(canonical_audit_json(material))


def append_durable_audit_event(
    *,
    ledger_dir: str | Path,
    ledger_filename: str,
    event_type: str,
    payload: Any,
    created_at: str | None = None,
    event_id: str | None = None,
) -> DurableAuditAppendResult:
    try:
        ledger_path = _resolve_ledger_path(ledger_dir, ledger_filename, create_dir=True)
        verified = verify_durable_audit_log(
            ledger_dir=ledger_dir,
            ledger_filename=ledger_filename,
        )
        if not verified.valid:
            return _append_blocked(str(ledger_path), "existing durable audit ledger failed verification")

        previous_hash = verified.final_event_hash
        timestamp = created_at or _utc_now_iso()
        payload_hash = _hash_payload(payload)
        record_id = event_id or _event_id(
            event_type=event_type,
            created_at=timestamp,
            payload_hash=payload_hash,
            previous_event_hash=previous_hash,
        )
        material = {
            "schema_version": DURABLE_AUDIT_SCHEMA_VERSION,
            "event_id": record_id,
            "event_type": _text(event_type, "event_type"),
            "created_at": _text(timestamp, "created_at"),
            "payload_hash": payload_hash,
            "payload": payload,
            "previous_event_hash": previous_hash,
            **{field_name: False for field_name in _AUTHORITY_FALSE_FIELDS},
        }
        event = DurableAuditEvent(
            **material,
            event_hash=compute_audit_event_hash(material),
        )

        if ledger_path.exists() and not ledger_path.is_file():
            return _append_blocked(str(ledger_path), "durable audit ledger path is not a regular file")
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_audit_json(event.to_dict()) + "\n")
        return DurableAuditAppendResult(
            appended=True,
            blocking=False,
            ledger_path=str(ledger_path),
            event=event,
            event_hash=event.event_hash,
            previous_event_hash=event.previous_event_hash,
            reason="durable audit event appended",
        )
    except Exception as exc:
        return _append_blocked(None, str(exc))


def verify_durable_audit_log(
    *,
    ledger_dir: str | Path,
    ledger_filename: str,
    expected_final_event_hash: str | None = None,
) -> DurableAuditVerificationResult:
    try:
        ledger_path = _resolve_ledger_path(ledger_dir, ledger_filename, create_dir=False)
        expected_final = _optional_hash(expected_final_event_hash, "expected_final_event_hash")
    except Exception as exc:
        return _verification_blocked(None, 0, None, str(exc))

    if not ledger_path.exists():
        if expected_final_event_hash is not None:
            return _verification_blocked(
                str(ledger_path),
                0,
                None,
                "durable audit ledger is truncated or missing expected final event",
            )
        return DurableAuditVerificationResult(
            valid=True,
            blocking=False,
            ledger_path=str(ledger_path),
            event_count=0,
            final_event_hash=None,
            issues=(),
        )
    if ledger_path.is_symlink():
        return _verification_blocked(str(ledger_path), 0, None, "durable audit ledger symlink is blocked")
    if not ledger_path.is_file():
        return _verification_blocked(str(ledger_path), 0, None, "durable audit ledger path is not a regular file")

    issues: list[str] = []
    previous_hash: str | None = DURABLE_AUDIT_GENESIS_PREVIOUS_HASH
    final_hash: str | None = None
    count = 0
    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return _verification_blocked(str(ledger_path), 0, None, str(exc))

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        count += 1
        try:
            decoded = json.loads(raw_line)
        except json.JSONDecodeError:
            issues.append(f"line {line_number}: malformed JSONL")
            continue
        if not isinstance(decoded, dict):
            issues.append(f"line {line_number}: event must be a JSON object")
            continue

        missing = sorted(_REQUIRED_EVENT_FIELDS - set(decoded))
        if missing:
            issues.append(f"line {line_number}: missing required field {missing[0]}")
            continue
        if decoded.get("schema_version") != DURABLE_AUDIT_SCHEMA_VERSION:
            issues.append(f"line {line_number}: invalid schema_version")

        for field_name in _AUTHORITY_FALSE_FIELDS:
            if decoded.get(field_name, False) is not False:
                issues.append(f"line {line_number}: authority field {field_name} must be false")

        payload_hash = _hash_payload(decoded.get("payload"))
        if decoded.get("payload_hash") != payload_hash:
            issues.append(f"line {line_number}: payload_hash mismatch")

        if decoded.get("previous_event_hash") != previous_hash:
            issues.append(f"line {line_number}: previous_event_hash mismatch")

        try:
            expected_hash = compute_audit_event_hash(decoded)
        except Exception as exc:
            issues.append(f"line {line_number}: event hash material invalid: {exc}")
            continue

        if decoded.get("event_hash") != expected_hash:
            issues.append(f"line {line_number}: event_hash mismatch")
        final_hash = decoded.get("event_hash") if isinstance(decoded.get("event_hash"), str) else final_hash
        previous_hash = decoded.get("event_hash") if isinstance(decoded.get("event_hash"), str) else None

    if expected_final is not None and final_hash != expected_final:
        issues.append("durable audit ledger truncated before expected final event")

    return DurableAuditVerificationResult(
        valid=not issues,
        blocking=bool(issues),
        ledger_path=str(ledger_path),
        event_count=count,
        final_event_hash=final_hash,
        issues=tuple(issues),
    )


def _resolve_ledger_path(
    ledger_dir: str | Path,
    ledger_filename: str,
    *,
    create_dir: bool,
) -> Path:
    directory = Path(ledger_dir) if isinstance(ledger_dir, str) else ledger_dir
    if not isinstance(directory, Path):
        raise TypeError("ledger_dir must be a string or Path")
    if not str(directory).strip():
        raise ValueError("ledger directory must be explicit")
    if not directory.is_absolute():
        raise ValueError("ledger directory must be absolute")
    if directory.exists() and directory.is_symlink():
        raise ValueError("ledger directory symlink is blocked")
    if create_dir:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not directory.exists() or not directory.is_dir():
        raise ValueError("ledger directory must exist")
    if directory.is_symlink():
        raise ValueError("ledger directory symlink is blocked")

    filename = _ledger_filename(ledger_filename)
    candidate = directory / filename
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("durable audit ledger symlink is blocked")
    resolved_dir = directory.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=False)
    if resolved_dir not in (resolved_candidate, *resolved_candidate.parents):
        raise ValueError("durable audit ledger path escapes ledger directory")
    if candidate.exists() and candidate.is_dir():
        raise ValueError("durable audit ledger path is a directory")
    return candidate


def _ledger_filename(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("ledger_filename must be a string")
    filename = value.strip()
    if not filename:
        raise ValueError("ledger filename must not be empty")
    if "\x00" in filename:
        raise ValueError("ledger filename contains a null byte")
    normalized = filename.replace("\\", "/")
    if PurePosixPath(normalized).is_absolute() or PureWindowsPath(filename).is_absolute():
        raise ValueError("ledger filename must be relative")
    parts = PurePosixPath(normalized).parts
    if len(parts) != 1 or parts[0] in {"", "."} or ".." in parts:
        raise ValueError("ledger filename must not contain traversal or directories")
    return parts[0]


def _event_hash_material(value: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(value)
    material.pop("event_hash", None)
    return material


def _hash_payload(payload: Any) -> str:
    _assert_json_serializable(payload)
    return _sha256(canonical_audit_json(payload))


def _event_id(
    *,
    event_type: str,
    created_at: str,
    payload_hash: str,
    previous_event_hash: str | None,
) -> str:
    material = {
        "schema_version": DURABLE_AUDIT_SCHEMA_VERSION,
        "event_type": event_type,
        "created_at": created_at,
        "payload_hash": payload_hash,
        "previous_event_hash": previous_event_hash,
    }
    return "durable-audit-event-" + _sha256(canonical_audit_json(material))[:24]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _full_hash(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a full SHA-256 string")
    text = value.strip().lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{field_name} must be a full SHA-256 string")
    return text


def _optional_hash(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _full_hash(value, field_name)


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty text")
    return text


def _assert_json_serializable(value: Any) -> None:
    canonical_audit_json(value)


def _append_blocked(ledger_path: str | None, reason: str) -> DurableAuditAppendResult:
    return DurableAuditAppendResult(
        appended=False,
        blocking=True,
        ledger_path=ledger_path,
        event=None,
        event_hash=None,
        previous_event_hash=None,
        reason=reason,
    )


def _verification_blocked(
    ledger_path: str | None,
    event_count: int,
    final_event_hash: str | None,
    reason: str,
) -> DurableAuditVerificationResult:
    return DurableAuditVerificationResult(
        valid=False,
        blocking=True,
        ledger_path=ledger_path,
        event_count=event_count,
        final_event_hash=final_event_hash,
        issues=(reason,),
    )
