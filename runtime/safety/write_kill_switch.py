from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


WRITES_ENABLED = "WRITES_ENABLED"
WRITES_DISABLED = "WRITES_DISABLED"
DEFAULT_WRITE_KILL_SWITCH_FILENAME = "write_kill_switch.state"

WRITE_KILL_SWITCH_ALLOWED = "WRITE_KILL_SWITCH_ALLOWED"
WRITE_KILL_SWITCH_BLOCKED_DISABLED = "WRITE_KILL_SWITCH_BLOCKED_DISABLED"
WRITE_KILL_SWITCH_BLOCKED_MISSING = "WRITE_KILL_SWITCH_BLOCKED_MISSING"
WRITE_KILL_SWITCH_BLOCKED_EMPTY = "WRITE_KILL_SWITCH_BLOCKED_EMPTY"
WRITE_KILL_SWITCH_BLOCKED_UNKNOWN = "WRITE_KILL_SWITCH_BLOCKED_UNKNOWN"
WRITE_KILL_SWITCH_BLOCKED_MALFORMED = "WRITE_KILL_SWITCH_BLOCKED_MALFORMED"
WRITE_KILL_SWITCH_BLOCKED_UNREADABLE = "WRITE_KILL_SWITCH_BLOCKED_UNREADABLE"
WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH = "WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH"


class WriteKillSwitchStatus(str, Enum):
    ALLOWED = WRITE_KILL_SWITCH_ALLOWED
    BLOCKED_DISABLED = WRITE_KILL_SWITCH_BLOCKED_DISABLED
    BLOCKED_MISSING = WRITE_KILL_SWITCH_BLOCKED_MISSING
    BLOCKED_EMPTY = WRITE_KILL_SWITCH_BLOCKED_EMPTY
    BLOCKED_UNKNOWN = WRITE_KILL_SWITCH_BLOCKED_UNKNOWN
    BLOCKED_MALFORMED = WRITE_KILL_SWITCH_BLOCKED_MALFORMED
    BLOCKED_UNREADABLE = WRITE_KILL_SWITCH_BLOCKED_UNREADABLE
    BLOCKED_UNSAFE_PATH = WRITE_KILL_SWITCH_BLOCKED_UNSAFE_PATH


@dataclass(frozen=True)
class WriteKillSwitchCheckResult:
    status: WriteKillSwitchStatus
    writes_allowed: bool
    reason: str
    source_path: str | None
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
        object.__setattr__(self, "status", WriteKillSwitchStatus(self.status))
        object.__setattr__(self, "writes_allowed", self.status is WriteKillSwitchStatus.ALLOWED)
        for field_name in (
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
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "writes_allowed": self.writes_allowed,
            "reason": self.reason,
            "source_path": self.source_path,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "write_authority_granted": self.write_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
        }


def resolve_required_write_kill_switch(
    switch_file_path: object | None = None,
    *,
    switch_directory: object | None = None,
) -> WriteKillSwitchCheckResult:
    if switch_file_path is None:
        if switch_directory is None:
            return _blocked(
                WriteKillSwitchStatus.BLOCKED_MISSING,
                "write kill-switch configuration is missing",
                None,
            )
        return check_write_kill_switch_in_directory(
            switch_directory=switch_directory,
        )
    return check_write_kill_switch_file(
        switch_file_path,
        allowed_switch_directory=switch_directory,
    )


def check_write_kill_switch_file(
    switch_file_path: object,
    *,
    allowed_switch_directory: object | None = None,
) -> WriteKillSwitchCheckResult:
    path_error = _switch_file_path_error(
        switch_file_path,
        allowed_switch_directory=allowed_switch_directory,
    )
    if path_error is not None:
        return path_error

    path = Path(switch_file_path)
    if allowed_switch_directory is not None and not path.is_absolute():
        path = Path(allowed_switch_directory) / path

    source_path = str(path)
    if not path.exists():
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_MISSING,
            "write kill-switch file is missing",
            source_path,
        )
    if path.is_symlink():
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch file must not be a symlink",
            source_path,
        )
    if path.is_dir():
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch path is a directory",
            source_path,
        )

    try:
        raw_value = path.read_text(encoding="utf-8")
    except OSError:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNREADABLE,
            "write kill-switch file is unreadable",
            source_path,
        )

    return evaluate_write_kill_switch_value(raw_value, source_path=source_path)


def check_write_kill_switch_in_directory(
    *,
    switch_directory: object,
    switch_filename: object = DEFAULT_WRITE_KILL_SWITCH_FILENAME,
) -> WriteKillSwitchCheckResult:
    directory_error = _switch_directory_error(switch_directory)
    if directory_error is not None:
        return directory_error
    directory = Path(switch_directory)
    filename_error = _switch_filename_error(switch_filename)
    if filename_error is not None:
        return filename_error
    return check_write_kill_switch_file(
        directory / switch_filename,
        allowed_switch_directory=directory,
    )


def evaluate_write_kill_switch_value(
    raw_value: object,
    *,
    source_path: str | None = None,
) -> WriteKillSwitchCheckResult:
    if not isinstance(raw_value, str):
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_MALFORMED,
            "write kill-switch value must be text",
            source_path,
        )
    stripped = raw_value.strip()
    if not stripped:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_EMPTY,
            "write kill-switch value is empty",
            source_path,
        )
    if "\n" in stripped or "\r" in stripped:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_MALFORMED,
            "write kill-switch value must be a single explicit state",
            source_path,
        )
    if stripped == WRITES_ENABLED:
        return WriteKillSwitchCheckResult(
            status=WriteKillSwitchStatus.ALLOWED,
            writes_allowed=True,
            reason="write kill-switch explicitly allows controlled writes to continue",
            source_path=source_path,
        )
    if stripped == WRITES_DISABLED:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_DISABLED,
            "write kill-switch explicitly disables controlled writes",
            source_path,
        )
    return _blocked(
        WriteKillSwitchStatus.BLOCKED_UNKNOWN,
        "write kill-switch value is unknown",
        source_path,
    )


def _switch_file_path_error(
    switch_file_path: object,
    *,
    allowed_switch_directory: object | None,
) -> WriteKillSwitchCheckResult | None:
    if not isinstance(switch_file_path, (str, Path)):
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_MALFORMED,
            "write kill-switch path must be text or a Path",
            None,
        )
    text = str(switch_file_path)
    if not text.strip():
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch path is empty",
            None,
        )
    if "\x00" in text:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch path contains a null byte",
            None,
        )
    path = Path(switch_file_path)
    if allowed_switch_directory is None:
        return None

    directory_error = _switch_directory_error(allowed_switch_directory)
    if directory_error is not None:
        return directory_error
    allowed_directory = Path(allowed_switch_directory)

    candidate = path if path.is_absolute() else allowed_directory / path
    try:
        allowed_resolved = allowed_directory.resolve(strict=False)
        candidate_resolved = candidate.resolve(strict=False)
    except OSError:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch path cannot be resolved safely",
            str(candidate),
        )
    if not _is_relative_to(candidate_resolved, allowed_resolved):
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch path escapes the allowed directory",
            str(candidate),
        )
    return None


def _switch_directory_error(
    switch_directory: object,
) -> WriteKillSwitchCheckResult | None:
    if not isinstance(switch_directory, (str, Path)):
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_MALFORMED,
            "write kill-switch directory must be text or a Path",
            None,
        )
    text = str(switch_directory)
    if not text.strip() or "\x00" in text:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch directory is unsafe",
            None,
        )
    directory = Path(switch_directory)
    try:
        if not directory.exists():
            return _blocked(
                WriteKillSwitchStatus.BLOCKED_MISSING,
                "write kill-switch directory is missing",
                str(directory),
            )
        if directory.is_symlink() or not directory.is_dir():
            return _blocked(
                WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
                "write kill-switch directory must be a non-symlink directory",
                str(directory),
            )
    except OSError:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNREADABLE,
            "write kill-switch directory cannot be inspected safely",
            str(directory),
        )
    return None


def _switch_filename_error(switch_filename: object) -> WriteKillSwitchCheckResult | None:
    if not isinstance(switch_filename, str) or not switch_filename.strip():
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch filename is empty",
            None,
        )
    if "\x00" in switch_filename:
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch filename contains a null byte",
            None,
        )
    filename = Path(switch_filename)
    if filename.is_absolute():
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch filename must be relative",
            None,
        )
    if any(part == ".." for part in filename.parts):
        return _blocked(
            WriteKillSwitchStatus.BLOCKED_UNSAFE_PATH,
            "write kill-switch filename must not traverse parents",
            None,
        )
    return None


def _blocked(
    status: WriteKillSwitchStatus,
    reason: str,
    source_path: str | None,
) -> WriteKillSwitchCheckResult:
    return WriteKillSwitchCheckResult(
        status=status,
        writes_allowed=False,
        reason=reason,
        source_path=source_path,
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
