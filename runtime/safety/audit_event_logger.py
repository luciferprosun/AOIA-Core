from __future__ import annotations

import json
import posix
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.safety.audit_event_policy import AuditEventChainBlockedError, assert_audit_event_hash_valid
from runtime.schemas.audit_event import AuditEvent, audit_event_to_dict


AUDIT_LOG_FILENAME = "events.jsonl"
MAX_AUDIT_EVENT_JSONL_BYTES = 64 * 1024


class AuditLogWriteBlockedError(RuntimeError):
    pass


class AuditLogPathBlockedError(AuditLogWriteBlockedError):
    pass


class AuditLogSizeBlockedError(AuditLogWriteBlockedError):
    pass


@dataclass(frozen=True)
class AuditLogWriteResult:
    write_completed: bool
    audit_log_path: str
    event_id: str
    event_hash: str
    previous_hash: str | None
    bytes_written: int
    fsync_completed: bool
    append_only: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "write_completed": self.write_completed,
            "audit_log_path": self.audit_log_path,
            "event_id": self.event_id,
            "event_hash": self.event_hash,
            "previous_hash": self.previous_hash,
            "bytes_written": self.bytes_written,
            "fsync_completed": self.fsync_completed,
            "append_only": self.append_only,
            "reason": self.reason,
        }


def append_audit_event_jsonl(
    audit_dir: str | Path,
    event: AuditEvent,
    *,
    expected_previous_hash: str | None = None,
) -> AuditLogWriteResult:
    if not isinstance(event, AuditEvent):
        raise TypeError("event must be an AuditEvent")
    assert_audit_event_hash_valid(event)
    if expected_previous_hash is not None and event.previous_event_hash != expected_previous_hash:
        raise AuditEventChainBlockedError("event previous_event_hash does not match expected_previous_hash")

    audit_root = _resolve_audit_dir(audit_dir)
    log_path = _resolve_audit_log_path(audit_root)
    _assert_existing_log_chain_allows_append(log_path, event)
    line = _serialize_event_line(event)
    line_bytes = line.encode("utf-8")
    if len(line_bytes) > MAX_AUDIT_EVENT_JSONL_BYTES:
        raise AuditLogSizeBlockedError("serialized audit event exceeds size limit")

    _append_line_and_fsync(log_path, line_bytes)
    return AuditLogWriteResult(
        write_completed=True,
        audit_log_path=str(log_path),
        event_id=event.event_id,
        event_hash=event.event_hash,
        previous_hash=event.previous_event_hash or None,
        bytes_written=len(line_bytes),
        fsync_completed=True,
        append_only=True,
        reason="audit event appended to durable JSONL log",
    )


def audit_log_write_result_to_dict(result: AuditLogWriteResult) -> dict[str, Any]:
    if not isinstance(result, AuditLogWriteResult):
        raise TypeError("result must be an AuditLogWriteResult")
    return result.to_dict()


def _resolve_audit_dir(audit_dir: str | Path) -> Path:
    if isinstance(audit_dir, Path):
        raw_path = audit_dir
    elif isinstance(audit_dir, str):
        raw_path = Path(audit_dir)
    else:
        raise TypeError("audit_dir must be a string or Path")
    if not str(raw_path).strip():
        raise AuditLogPathBlockedError("audit directory must be explicit")
    if not raw_path.is_absolute():
        raise AuditLogPathBlockedError("audit directory must be absolute")
    if raw_path.exists() and raw_path.is_symlink():
        raise AuditLogPathBlockedError("audit directory symlink is blocked")
    raw_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if raw_path.is_symlink():
        raise AuditLogPathBlockedError("audit directory symlink is blocked")
    resolved = Path(posixpath.realpath(str(raw_path)))
    if not resolved.is_dir():
        raise AuditLogPathBlockedError("audit directory must resolve to a directory")
    if posixpath.commonpath([str(resolved), posixpath.realpath(str(resolved))]) != str(resolved):
        raise AuditLogPathBlockedError("audit directory escapes canonical root")
    return resolved


def _resolve_audit_log_path(audit_root: Path) -> Path:
    log_path = audit_root / AUDIT_LOG_FILENAME
    if log_path.is_symlink():
        raise AuditLogPathBlockedError("audit log symlink is blocked")
    resolved = Path(posixpath.realpath(str(log_path)))
    if posixpath.commonpath([str(audit_root), str(resolved)]) != str(audit_root):
        raise AuditLogPathBlockedError("audit log path escapes audit directory")
    return resolved


def _serialize_event_line(event: AuditEvent) -> str:
    serialized = audit_event_to_dict(event)
    return json.dumps(serialized, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _assert_existing_log_chain_allows_append(log_path: Path, event: AuditEvent) -> None:
    if not log_path.exists():
        if event.previous_event_hash:
            raise AuditEventChainBlockedError("first durable audit event cannot declare previous_event_hash")
        return
    if not log_path.is_file():
        raise AuditLogPathBlockedError("audit log path must be a regular file")
    last_hash = _read_last_event_hash(log_path)
    if last_hash != event.previous_event_hash:
        raise AuditEventChainBlockedError("durable audit log previous hash mismatch")


def _read_last_event_hash(log_path: Path) -> str:
    last_line = ""
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last_line = line
    if not last_line:
        return ""
    try:
        decoded = json.loads(last_line)
    except json.JSONDecodeError as exc:
        raise AuditEventChainBlockedError("durable audit log contains invalid JSONL") from exc
    event_hash = decoded.get("event_hash", "")
    if not isinstance(event_hash, str) or not event_hash:
        raise AuditEventChainBlockedError("durable audit log last event hash is missing")
    return event_hash


def _append_line_and_fsync(log_path: Path, line_bytes: bytes) -> None:
    flags = posix.O_APPEND | posix.O_CREAT | posix.O_WRONLY
    if hasattr(posix, "O_NOFOLLOW"):
        flags |= posix.O_NOFOLLOW
    fd = posix.open(str(log_path), flags, 0o600)
    try:
        offset = 0
        while offset < len(line_bytes):
            written = posix.write(fd, line_bytes[offset:])
            if written <= 0:
                raise OSError("audit log write made no progress")
            offset += written
        posix.fsync(fd)
    finally:
        posix.close(fd)
