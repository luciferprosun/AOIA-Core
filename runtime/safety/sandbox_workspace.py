from __future__ import annotations

from pathlib import Path


class SandboxWorkspaceViolationError(ValueError):
    pass


class SandboxPathTraversalBlockedError(SandboxWorkspaceViolationError):
    pass


class SandboxSymlinkBlockedError(SandboxWorkspaceViolationError):
    pass


class SandboxOverwriteBlockedError(SandboxWorkspaceViolationError):
    pass


_ALLOWED_ARTIFACT_SUFFIXES = frozenset({".txt", ".json", ".md"})
_BLOCKED_CHARS = frozenset({"\x00", "\n", "\r", "\t", ";", "&", "|", "$", "`", "<", ">", "*", "?", "{", "}", "[", "]", "(", ")", "\\", "!"})


def normalize_relative_artifact_path(relative_path: str) -> str:
    if not isinstance(relative_path, str):
        raise TypeError("relative_path must be a string")
    value = relative_path.strip()
    if not value:
        raise SandboxWorkspaceViolationError("artifact path must not be empty")
    candidate = Path(value)
    if candidate.is_absolute():
        raise SandboxPathTraversalBlockedError("absolute artifact paths are blocked")
    parts = candidate.parts
    if not parts:
        raise SandboxWorkspaceViolationError("artifact path must not be empty")
    for part in parts:
        if part in {"", "."}:
            raise SandboxWorkspaceViolationError("artifact path contains an empty or current-directory segment")
        if part == "..":
            raise SandboxPathTraversalBlockedError("artifact path traversal is blocked")
        if part == ".git":
            raise SandboxWorkspaceViolationError("artifact writes into .git are blocked")
        if any(character in part for character in _BLOCKED_CHARS):
            raise SandboxWorkspaceViolationError("artifact path contains blocked characters")
    if candidate.suffix.lower() not in _ALLOWED_ARTIFACT_SUFFIXES:
        raise SandboxWorkspaceViolationError("artifact extension is not allowed")
    return candidate.as_posix()


def resolve_sandbox_artifact_path(workspace_root: str, relative_path: str) -> str:
    normalized = normalize_relative_artifact_path(relative_path)
    root = _resolved_workspace_root(workspace_root)
    resolved = (root / normalized).resolve(strict=False)
    assert_path_inside_workspace(str(root), str(resolved))
    return str(resolved)


def assert_path_inside_workspace(workspace_root: str, resolved_path: str) -> None:
    root = _resolved_workspace_root(workspace_root)
    path = Path(resolved_path).resolve(strict=False)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SandboxPathTraversalBlockedError("resolved artifact path escapes sandbox workspace") from exc


def assert_safe_artifact_write_path(workspace_root: str, relative_path: str) -> str:
    normalized = normalize_relative_artifact_path(relative_path)
    root = _resolved_workspace_root(workspace_root)
    resolved = (root / normalized).resolve(strict=False)
    assert_path_inside_workspace(str(root), str(resolved))
    _assert_no_symlink_escape(root, normalized)
    return str(resolved)


def _resolved_workspace_root(workspace_root: str) -> Path:
    if not isinstance(workspace_root, str):
        raise TypeError("workspace_root must be a string")
    if not workspace_root.strip():
        raise SandboxWorkspaceViolationError("workspace_root must be explicit")
    root = Path(workspace_root)
    if not root.is_absolute():
        raise SandboxWorkspaceViolationError("workspace_root must be absolute")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise SandboxWorkspaceViolationError("workspace_root must be an existing directory")
    return resolved


def _assert_no_symlink_escape(workspace_root: Path, normalized_relative_path: str) -> None:
    current = workspace_root
    parts = Path(normalized_relative_path).parts
    for part in parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise SandboxSymlinkBlockedError("artifact parent path contains a symlink")
        if current.exists():
            assert_path_inside_workspace(str(workspace_root), str(current.resolve(strict=True)))
    output = workspace_root / normalized_relative_path
    if output.exists() and output.is_symlink():
        raise SandboxSymlinkBlockedError("artifact output path is a symlink")
