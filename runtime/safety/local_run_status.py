from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.safety.audit_event_logger import AUDIT_LOG_FILENAME
from runtime.safety.local_workspace_run_context import (
    ARTIFACTS_DIR_NAME,
    AUDIT_DIR_NAME,
    MAX_LOCAL_RUN_ID_CHARS,
    RUNS_DIR_NAME,
    SAFE_LOCAL_RUN_ID_PATTERN,
)


MAX_LOCAL_RUN_STATUS_AUDIT_LOG_BYTES = 1024 * 1024


@dataclass(frozen=True)
class LocalRunStatus:
    read_successful: bool
    run_complete: bool
    base_workspace_root: str
    run_id: str
    run_root: str
    artifacts_dir: str
    audit_dir: str
    audit_log_path: str
    audit_log_exists: bool
    event_count: int
    hash_chain_valid: bool
    artifact_count: int
    expected_artifact_exists: bool | None
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.read_successful, bool):
            raise TypeError("read_successful must be bool")
        if not isinstance(self.run_complete, bool):
            raise TypeError("run_complete must be bool")
        object.__setattr__(self, "base_workspace_root", _coerce_text("base_workspace_root", self.base_workspace_root))
        object.__setattr__(self, "run_id", _validate_run_id(self.run_id))
        object.__setattr__(self, "run_root", _coerce_text("run_root", self.run_root))
        object.__setattr__(self, "artifacts_dir", _coerce_text("artifacts_dir", self.artifacts_dir))
        object.__setattr__(self, "audit_dir", _coerce_text("audit_dir", self.audit_dir))
        object.__setattr__(self, "audit_log_path", _coerce_text("audit_log_path", self.audit_log_path))
        if not isinstance(self.audit_log_exists, bool):
            raise TypeError("audit_log_exists must be bool")
        if not isinstance(self.event_count, int):
            raise TypeError("event_count must be int")
        if self.event_count < 0:
            raise ValueError("event_count must be non-negative")
        if not isinstance(self.hash_chain_valid, bool):
            raise TypeError("hash_chain_valid must be bool")
        if not isinstance(self.artifact_count, int):
            raise TypeError("artifact_count must be int")
        if self.artifact_count < 0:
            raise ValueError("artifact_count must be non-negative")
        if self.expected_artifact_exists is not None and not isinstance(self.expected_artifact_exists, bool):
            raise TypeError("expected_artifact_exists must be bool or None")
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))

    def to_dict(self) -> dict[str, Any]:
        return {
            "read_successful": self.read_successful,
            "run_complete": self.run_complete,
            "base_workspace_root": self.base_workspace_root,
            "run_id": self.run_id,
            "run_root": self.run_root,
            "artifacts_dir": self.artifacts_dir,
            "audit_dir": self.audit_dir,
            "audit_log_path": self.audit_log_path,
            "audit_log_exists": self.audit_log_exists,
            "event_count": self.event_count,
            "hash_chain_valid": self.hash_chain_valid,
            "artifact_count": self.artifact_count,
            "expected_artifact_exists": self.expected_artifact_exists,
            "reason": self.reason,
        }


def read_local_run_status(
    *,
    base_workspace_root: str | Path,
    run_id: str,
    expected_artifact_filename: str | None = None,
) -> LocalRunStatus:
    base_root = _resolve_base_workspace_root(base_workspace_root)
    safe_run_id = _validate_run_id(run_id)
    expected_artifact = _validate_expected_artifact_filename(expected_artifact_filename)

    runs_root = base_root / RUNS_DIR_NAME
    run_root = runs_root / safe_run_id
    artifacts_dir = run_root / ARTIFACTS_DIR_NAME
    audit_dir = run_root / AUDIT_DIR_NAME
    audit_log_path = audit_dir / AUDIT_LOG_FILENAME

    _assert_inside(base_root, runs_root, "runs directory")
    _assert_inside(base_root, run_root, "run root")
    _assert_inside(run_root, artifacts_dir, "artifacts directory")
    _assert_inside(run_root, audit_dir, "audit directory")
    _assert_inside(audit_dir, audit_log_path, "audit log")

    _reject_symlink_if_exists(base_root, "base workspace root")
    _reject_symlink_if_exists(runs_root, "runs directory")
    _reject_symlink_if_exists(run_root, "run root")
    _reject_symlink_if_exists(artifacts_dir, "artifacts directory")
    _reject_symlink_if_exists(audit_dir, "audit directory")
    _reject_symlink_if_exists(audit_log_path, "audit log")

    artifacts_exists = artifacts_dir.is_dir()
    audit_dir_exists = audit_dir.is_dir()
    audit_log_exists = audit_log_path.is_file()
    artifact_count = _count_artifact_files(artifacts_dir) if artifacts_exists else 0
    expected_artifact_exists = (
        _expected_artifact_exists(artifacts_dir, expected_artifact) if expected_artifact is not None and artifacts_exists else None
    )

    if not run_root.exists():
        return _status(
            read_successful=True,
            run_complete=False,
            base_root=base_root,
            run_id=safe_run_id,
            run_root=run_root,
            artifacts_dir=artifacts_dir,
            audit_dir=audit_dir,
            audit_log_path=audit_log_path,
            audit_log_exists=False,
            event_count=0,
            hash_chain_valid=False,
            artifact_count=0,
            expected_artifact_exists=expected_artifact_exists,
            reason="local run directory is missing",
        )

    if not artifacts_exists:
        return _status(
            read_successful=True,
            run_complete=False,
            base_root=base_root,
            run_id=safe_run_id,
            run_root=run_root,
            artifacts_dir=artifacts_dir,
            audit_dir=audit_dir,
            audit_log_path=audit_log_path,
            audit_log_exists=audit_log_exists,
            event_count=0,
            hash_chain_valid=False,
            artifact_count=0,
            expected_artifact_exists=expected_artifact_exists,
            reason="local run artifacts directory is missing",
        )

    if not audit_dir_exists:
        return _status(
            read_successful=True,
            run_complete=False,
            base_root=base_root,
            run_id=safe_run_id,
            run_root=run_root,
            artifacts_dir=artifacts_dir,
            audit_dir=audit_dir,
            audit_log_path=audit_log_path,
            audit_log_exists=False,
            event_count=0,
            hash_chain_valid=False,
            artifact_count=artifact_count,
            expected_artifact_exists=expected_artifact_exists,
            reason="local run audit directory is missing",
        )

    if not audit_log_exists:
        return _status(
            read_successful=True,
            run_complete=False,
            base_root=base_root,
            run_id=safe_run_id,
            run_root=run_root,
            artifacts_dir=artifacts_dir,
            audit_dir=audit_dir,
            audit_log_path=audit_log_path,
            audit_log_exists=False,
            event_count=0,
            hash_chain_valid=False,
            artifact_count=artifact_count,
            expected_artifact_exists=expected_artifact_exists,
            reason="local run audit log is missing",
        )

    log_status = _read_audit_log_chain_status(audit_log_path)
    run_complete = bool(log_status["hash_chain_valid"] and artifact_count > 0)
    reason = "local run status complete" if run_complete else log_status["reason"]
    return _status(
        read_successful=bool(log_status["read_successful"]),
        run_complete=run_complete,
        base_root=base_root,
        run_id=safe_run_id,
        run_root=run_root,
        artifacts_dir=artifacts_dir,
        audit_dir=audit_dir,
        audit_log_path=audit_log_path,
        audit_log_exists=True,
        event_count=int(log_status["event_count"]),
        hash_chain_valid=bool(log_status["hash_chain_valid"]),
        artifact_count=artifact_count,
        expected_artifact_exists=expected_artifact_exists,
        reason=reason,
    )


def local_run_status_to_dict(status: LocalRunStatus) -> dict[str, Any]:
    if not isinstance(status, LocalRunStatus):
        raise TypeError("status must be a LocalRunStatus")
    return status.to_dict()


def _read_audit_log_chain_status(log_path: Path) -> dict[str, Any]:
    size = log_path.stat().st_size
    if size > MAX_LOCAL_RUN_STATUS_AUDIT_LOG_BYTES:
        return _audit_status(False, 0, False, "local run audit log is too large")

    previous_hash = ""
    event_count = 0
    raw_text = log_path.read_text(encoding="utf-8")
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            return _audit_status(False, event_count, False, f"local run audit log has malformed JSONL at line {line_number}")
        if not isinstance(decoded, dict):
            return _audit_status(False, event_count, False, f"local run audit log line {line_number} is not an object")
        event_hash = decoded.get("event_hash")
        declared_previous = decoded.get("previous_event_hash", "")
        if not isinstance(event_hash, str) or not event_hash:
            return _audit_status(True, event_count, False, f"local run audit log line {line_number} is missing event_hash")
        if not isinstance(declared_previous, str):
            return _audit_status(True, event_count, False, f"local run audit log line {line_number} has invalid previous_event_hash")
        if declared_previous != previous_hash:
            return _audit_status(True, event_count, False, f"local run audit hash chain mismatch at line {line_number}")
        previous_hash = event_hash
        event_count += 1

    if event_count == 0:
        return _audit_status(True, 0, False, "local run audit log is empty")
    return _audit_status(True, event_count, True, "local run audit hash chain is valid")


def _count_artifact_files(artifacts_dir: Path) -> int:
    return sum(1 for child in artifacts_dir.iterdir() if child.is_file() and not child.is_symlink())


def _expected_artifact_exists(artifacts_dir: Path, expected_artifact: str) -> bool:
    candidate = artifacts_dir / expected_artifact
    _assert_inside(artifacts_dir, candidate, "expected artifact")
    if candidate.is_symlink():
        raise ValueError("expected artifact symlink is blocked")
    return candidate.is_file()


def _status(
    *,
    read_successful: bool,
    run_complete: bool,
    base_root: Path,
    run_id: str,
    run_root: Path,
    artifacts_dir: Path,
    audit_dir: Path,
    audit_log_path: Path,
    audit_log_exists: bool,
    event_count: int,
    hash_chain_valid: bool,
    artifact_count: int,
    expected_artifact_exists: bool | None,
    reason: str,
) -> LocalRunStatus:
    return LocalRunStatus(
        read_successful=read_successful,
        run_complete=run_complete,
        base_workspace_root=os.path.realpath(str(base_root)),
        run_id=run_id,
        run_root=os.path.realpath(str(run_root)),
        artifacts_dir=os.path.realpath(str(artifacts_dir)),
        audit_dir=os.path.realpath(str(audit_dir)),
        audit_log_path=os.path.realpath(str(audit_log_path)),
        audit_log_exists=audit_log_exists,
        event_count=event_count,
        hash_chain_valid=hash_chain_valid,
        artifact_count=artifact_count,
        expected_artifact_exists=expected_artifact_exists,
        reason=reason,
    )


def _audit_status(read_successful: bool, event_count: int, hash_chain_valid: bool, reason: str) -> dict[str, Any]:
    return {
        "read_successful": read_successful,
        "event_count": event_count,
        "hash_chain_valid": hash_chain_valid,
        "reason": reason,
    }


def _resolve_base_workspace_root(value: str | Path) -> Path:
    raw_text = _path_value_to_text("base_workspace_root", value)
    _reject_control_characters("base_workspace_root", raw_text)
    raw_path = Path(raw_text)
    if not raw_path.is_absolute():
        raise ValueError("base_workspace_root must be absolute")
    if raw_path.exists() and raw_path.is_symlink():
        raise ValueError("base_workspace_root must not be a symlink")
    return Path(os.path.realpath(str(raw_path)))


def _validate_run_id(run_id: str) -> str:
    value = _coerce_text("run_id", run_id)
    _reject_control_characters("run_id", value)
    if not value:
        raise ValueError("run_id must not be empty")
    if len(value) > MAX_LOCAL_RUN_ID_CHARS:
        raise ValueError("run_id is too long")
    if not SAFE_LOCAL_RUN_ID_PATTERN.fullmatch(value):
        raise ValueError("run_id must contain only lowercase letters, digits, dash, or underscore")
    return value


def _validate_expected_artifact_filename(expected_artifact_filename: str | None) -> str | None:
    if expected_artifact_filename is None:
        return None
    value = _coerce_text("expected_artifact_filename", expected_artifact_filename).strip()
    _reject_control_characters("expected_artifact_filename", value)
    if not value:
        raise ValueError("expected_artifact_filename must not be empty")
    if "\\" in value:
        raise ValueError("expected_artifact_filename must not contain backslashes")
    artifact_path = Path(value)
    if artifact_path.is_absolute() or len(artifact_path.parts) != 1 or artifact_path.name != value:
        raise ValueError("expected_artifact_filename must be a single relative filename")
    if value in (".", "..") or ".." in value:
        raise ValueError("expected_artifact_filename must not contain traversal")
    return value


def _path_value_to_text(name: str, value: str | Path) -> str:
    if isinstance(value, Path):
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError(f"{name} must be a string or Path")
    if not text.strip():
        raise ValueError(f"{name} must be explicit")
    return text


def _reject_control_characters(name: str, value: str) -> None:
    for character in value:
        codepoint = ord(character)
        if codepoint < 32 or codepoint == 127:
            raise ValueError(f"{name} contains a blocked control character")


def _reject_symlink_if_exists(path: Path, label: str) -> None:
    if path.exists() and path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")


def _assert_inside(root: Path, candidate: Path, label: str) -> None:
    root_real = os.path.realpath(str(root))
    candidate_real = os.path.realpath(str(candidate))
    try:
        common = os.path.commonpath((root_real, candidate_real))
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside local run context") from exc
    if common != root_real:
        raise ValueError(f"{label} must stay inside local run context")


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
