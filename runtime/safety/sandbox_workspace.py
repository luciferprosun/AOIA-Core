from __future__ import annotations

import posixpath
import unicodedata
from pathlib import Path


class SandboxWorkspaceViolationError(ValueError):
    pass


class SandboxPathTraversalBlockedError(SandboxWorkspaceViolationError):
    pass


class SandboxSymlinkBlockedError(SandboxWorkspaceViolationError):
    pass


class SandboxOverwriteBlockedError(SandboxWorkspaceViolationError):
    pass


MAX_ARTIFACT_PATH_DEPTH = 8
MAX_ARTIFACT_FILENAME_BYTES = 128

ALLOWED_ARTIFACT_SUFFIXES = frozenset({".txt", ".json", ".md"})
_BLOCKED_CHARS = frozenset({";", "&", "|", "$", "`", "<", ">", "*", "?", "{", "}", "[", "]", "(", ")", "\\", "!"})


def normalize_relative_artifact_path(relative_path: str) -> str:
    if not isinstance(relative_path, str):
        raise TypeError("relative_path must be a string")
    value = unicodedata.normalize("NFC", relative_path.strip())
    if not value:
        raise SandboxWorkspaceViolationError("artifact path must not be empty")
    if posixpath.isabs(value):
        raise SandboxPathTraversalBlockedError("absolute artifact paths are blocked")
    parts = tuple(value.split("/"))
    if len(parts) > MAX_ARTIFACT_PATH_DEPTH:
        raise SandboxWorkspaceViolationError("artifact path depth exceeds limit")
    for part in parts:
        if part in {"", "."}:
            raise SandboxWorkspaceViolationError("artifact path contains an empty or current-directory segment")
        if part == "..":
            raise SandboxPathTraversalBlockedError("artifact path traversal is blocked")
        if part == ".git":
            raise SandboxWorkspaceViolationError("artifact writes into .git are blocked")
        if _contains_control_character(part):
            raise SandboxWorkspaceViolationError("artifact path contains control characters")
        if len(part.encode("utf-8")) > MAX_ARTIFACT_FILENAME_BYTES:
            raise SandboxWorkspaceViolationError("artifact filename exceeds byte limit")
        if any(character in part for character in _BLOCKED_CHARS):
            raise SandboxWorkspaceViolationError("artifact path contains blocked characters")
    if Path(parts[-1]).suffix.lower() not in ALLOWED_ARTIFACT_SUFFIXES:
        raise SandboxWorkspaceViolationError("artifact extension is not allowed")
    return "/".join(parts)


def resolve_sandbox_artifact_path(workspace_root: str, relative_path: str) -> str:
    normalized = normalize_relative_artifact_path(relative_path)
    root = _resolved_workspace_root(workspace_root)
    resolved = posixpath.realpath(posixpath.join(root, normalized))
    assert_path_inside_workspace(root, resolved)
    return resolved


def assert_path_inside_workspace(workspace_root: str, resolved_path: str) -> None:
    root = _resolved_workspace_root(workspace_root)
    path = posixpath.realpath(resolved_path)
    try:
        inside_workspace = posixpath.commonpath([root, path]) == root
    except ValueError as exc:
        raise SandboxPathTraversalBlockedError("resolved artifact path escapes sandbox workspace") from exc
    if not inside_workspace:
        raise SandboxPathTraversalBlockedError("resolved artifact path escapes sandbox workspace")


def assert_safe_artifact_write_path(workspace_root: str, relative_path: str) -> str:
    normalized = normalize_relative_artifact_path(relative_path)
    root = _resolved_workspace_root(workspace_root)
    resolved = posixpath.realpath(posixpath.join(root, normalized))
    assert_path_inside_workspace(root, resolved)
    _assert_no_symlink_escape(root, normalized)
    return resolved


def _resolved_workspace_root(workspace_root: str) -> str:
    if not isinstance(workspace_root, str):
        raise TypeError("workspace_root must be a string")
    if not workspace_root.strip():
        raise SandboxWorkspaceViolationError("workspace_root must be explicit")
    root = workspace_root.strip()
    if not posixpath.isabs(root):
        raise SandboxWorkspaceViolationError("workspace_root must be absolute")
    resolved = posixpath.realpath(root)
    if not Path(resolved).is_dir():
        raise SandboxWorkspaceViolationError("workspace_root must be an existing directory")
    return resolved


def _assert_no_symlink_escape(workspace_root: str, normalized_relative_path: str) -> None:
    current = Path(workspace_root)
    parts = tuple(normalized_relative_path.split("/"))
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise SandboxSymlinkBlockedError("artifact parent path contains a symlink")
        if current.exists():
            assert_path_inside_workspace(workspace_root, posixpath.realpath(str(current)))
    output = Path(workspace_root) / normalized_relative_path
    if output.is_symlink():
        raise SandboxSymlinkBlockedError("artifact output path is a symlink")


def _contains_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)
