from __future__ import annotations

import posixpath
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.safety.sandbox_workspace import (
    SandboxWorkspaceViolationError,
    normalize_relative_artifact_path,
)


WORKSPACE_GUARD_ALLOWED = "WORKSPACE_GUARD_ALLOWED"
WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT = "WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT"
WORKSPACE_GUARD_BLOCKED_EMPTY_WORKSPACE_ROOT = "WORKSPACE_GUARD_BLOCKED_EMPTY_WORKSPACE_ROOT"
WORKSPACE_GUARD_BLOCKED_NULL_BYTE = "WORKSPACE_GUARD_BLOCKED_NULL_BYTE"
WORKSPACE_GUARD_BLOCKED_RELATIVE_WORKSPACE_ROOT = "WORKSPACE_GUARD_BLOCKED_RELATIVE_WORKSPACE_ROOT"
WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT_PATH = "WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT_PATH"
WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_NOT_DIRECTORY = "WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_NOT_DIRECTORY"
WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_SYMLINK = "WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_SYMLINK"
WORKSPACE_GUARD_BLOCKED_UNRESOLVED_WORKSPACE_ROOT = "WORKSPACE_GUARD_BLOCKED_UNRESOLVED_WORKSPACE_ROOT"
WORKSPACE_GUARD_BLOCKED_TARGET_EMPTY = "WORKSPACE_GUARD_BLOCKED_TARGET_EMPTY"
WORKSPACE_GUARD_BLOCKED_ABSOLUTE_TARGET_PATH = "WORKSPACE_GUARD_BLOCKED_ABSOLUTE_TARGET_PATH"
WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL = "WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL"
WORKSPACE_GUARD_BLOCKED_BACKSLASH_TRAVERSAL = "WORKSPACE_GUARD_BLOCKED_BACKSLASH_TRAVERSAL"
WORKSPACE_GUARD_BLOCKED_TARGET_NULL_BYTE = "WORKSPACE_GUARD_BLOCKED_TARGET_NULL_BYTE"
WORKSPACE_GUARD_BLOCKED_DOT_GIT_TARGET = "WORKSPACE_GUARD_BLOCKED_DOT_GIT_TARGET"
WORKSPACE_GUARD_BLOCKED_WORKSPACE_ESCAPE = "WORKSPACE_GUARD_BLOCKED_WORKSPACE_ESCAPE"
WORKSPACE_GUARD_BLOCKED_SYMLINK_TARGET = "WORKSPACE_GUARD_BLOCKED_SYMLINK_TARGET"
WORKSPACE_GUARD_BLOCKED_PARENT_SYMLINK = "WORKSPACE_GUARD_BLOCKED_PARENT_SYMLINK"
WORKSPACE_GUARD_BLOCKED_DIRECTORY_TARGET = "WORKSPACE_GUARD_BLOCKED_DIRECTORY_TARGET"
WORKSPACE_GUARD_BLOCKED_TARGET_POLICY = "WORKSPACE_GUARD_BLOCKED_TARGET_POLICY"


class WorkspaceGuardStatus(str, Enum):
    ALLOWED = WORKSPACE_GUARD_ALLOWED
    BLOCKED_MISSING_WORKSPACE_ROOT = WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT
    BLOCKED_EMPTY_WORKSPACE_ROOT = WORKSPACE_GUARD_BLOCKED_EMPTY_WORKSPACE_ROOT
    BLOCKED_NULL_BYTE = WORKSPACE_GUARD_BLOCKED_NULL_BYTE
    BLOCKED_RELATIVE_WORKSPACE_ROOT = WORKSPACE_GUARD_BLOCKED_RELATIVE_WORKSPACE_ROOT
    BLOCKED_MISSING_WORKSPACE_ROOT_PATH = WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT_PATH
    BLOCKED_WORKSPACE_ROOT_NOT_DIRECTORY = WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_NOT_DIRECTORY
    BLOCKED_WORKSPACE_ROOT_SYMLINK = WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_SYMLINK
    BLOCKED_UNRESOLVED_WORKSPACE_ROOT = WORKSPACE_GUARD_BLOCKED_UNRESOLVED_WORKSPACE_ROOT
    BLOCKED_TARGET_EMPTY = WORKSPACE_GUARD_BLOCKED_TARGET_EMPTY
    BLOCKED_ABSOLUTE_TARGET_PATH = WORKSPACE_GUARD_BLOCKED_ABSOLUTE_TARGET_PATH
    BLOCKED_TARGET_TRAVERSAL = WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL
    BLOCKED_BACKSLASH_TRAVERSAL = WORKSPACE_GUARD_BLOCKED_BACKSLASH_TRAVERSAL
    BLOCKED_TARGET_NULL_BYTE = WORKSPACE_GUARD_BLOCKED_TARGET_NULL_BYTE
    BLOCKED_DOT_GIT_TARGET = WORKSPACE_GUARD_BLOCKED_DOT_GIT_TARGET
    BLOCKED_WORKSPACE_ESCAPE = WORKSPACE_GUARD_BLOCKED_WORKSPACE_ESCAPE
    BLOCKED_SYMLINK_TARGET = WORKSPACE_GUARD_BLOCKED_SYMLINK_TARGET
    BLOCKED_PARENT_SYMLINK = WORKSPACE_GUARD_BLOCKED_PARENT_SYMLINK
    BLOCKED_DIRECTORY_TARGET = WORKSPACE_GUARD_BLOCKED_DIRECTORY_TARGET
    BLOCKED_TARGET_POLICY = WORKSPACE_GUARD_BLOCKED_TARGET_POLICY


@dataclass(frozen=True)
class WorkspaceGuardResult:
    status: WorkspaceGuardStatus
    allowed: bool
    reason_code: str
    reason: str
    workspace_root: str | None
    normalized_relative_target_path: str | None
    resolved_absolute_target_path: str | None
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
        status = WorkspaceGuardStatus(self.status)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "allowed", status is WorkspaceGuardStatus.ALLOWED)
        object.__setattr__(self, "reason_code", status.value)
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
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "workspace_root": self.workspace_root,
            "normalized_relative_target_path": self.normalized_relative_target_path,
            "resolved_absolute_target_path": self.resolved_absolute_target_path,
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


def validate_workspace_root(workspace_root: str | Path | None) -> WorkspaceGuardResult:
    root = _coerce_path_text(workspace_root)
    if root is None:
        return _blocked(
            WorkspaceGuardStatus.BLOCKED_MISSING_WORKSPACE_ROOT,
            "workspace_root must be explicit",
            None,
            None,
            None,
        )
    if not root.strip():
        return _blocked(
            WorkspaceGuardStatus.BLOCKED_EMPTY_WORKSPACE_ROOT,
            "workspace_root must be explicit",
            None,
            None,
            None,
        )
    if "\x00" in root:
        return _blocked(
            WorkspaceGuardStatus.BLOCKED_NULL_BYTE,
            "workspace_root contains a null byte",
            None,
            None,
            None,
        )

    path = Path(root.strip())
    if not path.is_absolute():
        return _blocked(
            WorkspaceGuardStatus.BLOCKED_RELATIVE_WORKSPACE_ROOT,
            "workspace_root must be absolute",
            str(path),
            None,
            None,
        )
    try:
        if path.is_symlink():
            return _blocked(
                WorkspaceGuardStatus.BLOCKED_WORKSPACE_ROOT_SYMLINK,
                "workspace_root must not be a symlink",
                str(path),
                None,
                None,
            )
        if not path.exists():
            return _blocked(
                WorkspaceGuardStatus.BLOCKED_MISSING_WORKSPACE_ROOT_PATH,
                "workspace_root must be an existing directory",
                str(path),
                None,
                None,
            )
        if not path.is_dir():
            return _blocked(
                WorkspaceGuardStatus.BLOCKED_WORKSPACE_ROOT_NOT_DIRECTORY,
                "workspace_root must be an existing directory",
                str(path),
                None,
                None,
            )
        resolved = path.resolve(strict=True)
    except OSError:
        return _blocked(
            WorkspaceGuardStatus.BLOCKED_UNRESOLVED_WORKSPACE_ROOT,
            "workspace_root cannot be resolved safely",
            str(path),
            None,
            None,
        )

    return WorkspaceGuardResult(
        status=WorkspaceGuardStatus.ALLOWED,
        allowed=True,
        reason_code=WORKSPACE_GUARD_ALLOWED,
        reason="workspace root is a resolved existing directory",
        workspace_root=str(resolved),
        normalized_relative_target_path=None,
        resolved_absolute_target_path=None,
    )


def validate_workspace_target_path(
    workspace_root: str | Path | None,
    target_path: str | Path | None,
) -> WorkspaceGuardResult:
    root_result = validate_workspace_root(workspace_root)
    if not root_result.allowed:
        return root_result

    raw_target = _coerce_path_text(target_path)
    if raw_target is None:
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_TARGET_EMPTY,
            "artifact path must not be empty",
            root_result.workspace_root,
        )
    if not raw_target.strip():
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_TARGET_EMPTY,
            "artifact path must not be empty",
            root_result.workspace_root,
        )
    if "\x00" in raw_target:
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_TARGET_NULL_BYTE,
            "artifact path contains control characters",
            root_result.workspace_root,
        )
    if "\\" in raw_target:
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_BACKSLASH_TRAVERSAL,
            "artifact path contains blocked characters",
            root_result.workspace_root,
        )
    if posixpath.isabs(raw_target.strip()):
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_ABSOLUTE_TARGET_PATH,
            "absolute artifact paths are blocked",
            root_result.workspace_root,
        )

    parts = tuple(raw_target.strip().split("/"))
    if any(part == ".." for part in parts):
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_TARGET_TRAVERSAL,
            "artifact path traversal is blocked",
            root_result.workspace_root,
        )
    if any(part == ".git" for part in parts):
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_DOT_GIT_TARGET,
            "artifact writes into .git are blocked",
            root_result.workspace_root,
        )

    try:
        normalized = normalize_relative_artifact_path(raw_target)
    except SandboxWorkspaceViolationError as exc:
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_TARGET_POLICY,
            str(exc),
            root_result.workspace_root,
        )
    except TypeError as exc:
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_TARGET_POLICY,
            str(exc),
            root_result.workspace_root,
        )

    root = Path(root_result.workspace_root or "")
    candidate = root / normalized
    parent_check = _existing_parent_symlink_check(root, normalized)
    if parent_check is not None:
        return parent_check
    if candidate.is_symlink():
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_SYMLINK_TARGET,
            "artifact output path is a symlink",
            root_result.workspace_root,
            normalized,
            str(candidate),
        )
    if candidate.exists() and candidate.is_dir():
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_DIRECTORY_TARGET,
            "artifact output path is a directory",
            root_result.workspace_root,
            normalized,
            str(candidate),
        )

    resolved_target = candidate.resolve(strict=False)
    if not _is_relative_to(resolved_target, root):
        return _target_blocked(
            WorkspaceGuardStatus.BLOCKED_WORKSPACE_ESCAPE,
            "resolved artifact path escapes sandbox workspace",
            root_result.workspace_root,
            normalized,
            str(resolved_target),
        )

    return WorkspaceGuardResult(
        status=WorkspaceGuardStatus.ALLOWED,
        allowed=True,
        reason_code=WORKSPACE_GUARD_ALLOWED,
        reason="workspace target path is a safe write precondition",
        workspace_root=root_result.workspace_root,
        normalized_relative_target_path=normalized,
        resolved_absolute_target_path=str(resolved_target),
    )


def require_workspace_guard_allowed(
    workspace_root: str | Path | None,
    target_path: str | Path | None,
) -> WorkspaceGuardResult:
    result = validate_workspace_target_path(workspace_root, target_path)
    if not result.allowed:
        raise SandboxWorkspaceViolationError(result.reason)
    return result


def _existing_parent_symlink_check(
    workspace_root: Path,
    normalized_target_path: str,
) -> WorkspaceGuardResult | None:
    current = workspace_root
    for part in normalized_target_path.split("/")[:-1]:
        current = current / part
        if current.is_symlink():
            return _target_blocked(
                WorkspaceGuardStatus.BLOCKED_PARENT_SYMLINK,
                "artifact parent path contains a symlink",
                str(workspace_root),
                normalized_target_path,
                str(current.resolve(strict=False)),
            )
        if current.exists() and not current.is_dir():
            return _target_blocked(
                WorkspaceGuardStatus.BLOCKED_TARGET_POLICY,
                "artifact parent path is not a directory",
                str(workspace_root),
                normalized_target_path,
                str(current),
            )
    return None


def _coerce_path_text(value: str | Path | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        return value
    return None


def _blocked(
    status: WorkspaceGuardStatus,
    reason: str,
    workspace_root: str | None,
    normalized_relative_target_path: str | None,
    resolved_absolute_target_path: str | None,
) -> WorkspaceGuardResult:
    return WorkspaceGuardResult(
        status=status,
        allowed=False,
        reason_code=status.value,
        reason=reason,
        workspace_root=workspace_root,
        normalized_relative_target_path=normalized_relative_target_path,
        resolved_absolute_target_path=resolved_absolute_target_path,
    )


def _target_blocked(
    status: WorkspaceGuardStatus,
    reason: str,
    workspace_root: str | None,
    normalized_relative_target_path: str | None = None,
    resolved_absolute_target_path: str | None = None,
) -> WorkspaceGuardResult:
    return _blocked(
        status,
        reason,
        workspace_root,
        normalized_relative_target_path,
        resolved_absolute_target_path,
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
