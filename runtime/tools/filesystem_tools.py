from __future__ import annotations

"""Legacy transitional filesystem mutation surface.

This module is not an approved runtime file-write/delete execution path. It
must not be reachable from model/proposal/public runtime flow. Do not use it as
an executor.
"""

import os
import shutil
from pathlib import Path

LEGACY_FILESYSTEM_SURFACE = True
APPROVED_RUNTIME_FILESYSTEM_FLOW = False
FILESYSTEM_MUTATION_FROZEN = True
AOIA_LEGACY_FILESYSTEM_ENABLED = os.environ.get("AOIA_LEGACY_FILESYSTEM_ENABLED") == "1"


class FilesystemContainmentError(PermissionError):
    """Raised when a filesystem path cannot be kept inside the project root."""

    reason_code = "FILESYSTEM_CONTAINMENT_BLOCKED"


def _legacy_filesystem_enabled() -> bool:
    return AOIA_LEGACY_FILESYSTEM_ENABLED or os.environ.get("AOIA_LEGACY_FILESYSTEM_ENABLED") == "1"


def _require_legacy_filesystem_enabled() -> None:
    if not _legacy_filesystem_enabled():
        raise RuntimeError(
            "Legacy filesystem mutation surface is frozen and not approved for runtime use. "
            "Set AOIA_LEGACY_FILESYSTEM_ENABLED=1 only for isolated legacy/manual testing."
        )


def canonical_project_root(project_root: Path | None) -> Path:
    """Return the stable, real project directory used as the security boundary."""
    if project_root is None:
        raise FilesystemContainmentError(
            "Filesystem containment blocked the operation: a configured project root is required."
        )

    try:
        root = Path(project_root).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise FilesystemContainmentError(
            "Filesystem containment blocked the operation: the configured project root "
            "cannot be resolved safely."
        ) from None

    if not root.is_dir():
        raise FilesystemContainmentError(
            "Filesystem containment blocked the operation: the configured project root "
            "is not a directory."
        )
    return root


def _require_path_within_project(path: Path, project_root: Path, operation: str) -> None:
    try:
        path.relative_to(project_root)
    except ValueError:
        raise FilesystemContainmentError(
            f"Filesystem containment blocked {operation}: the resolved target is outside "
            "the configured project root."
        ) from None


def resolve_path(
    path_text: str | Path,
    cwd: Path,
    project_root: Path | None = None,
    *,
    operation: str = "the filesystem operation",
) -> Path:
    """Resolve a path against cwd and require its real path to stay in project_root."""
    root = canonical_project_root(project_root)

    current = Path(cwd).expanduser()
    if not current.is_absolute():
        current = root / current
    try:
        current = current.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        raise FilesystemContainmentError(
            f"Filesystem containment blocked {operation}: the current working directory "
            "cannot be resolved safely."
        ) from None
    _require_path_within_project(current, root, operation)

    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = current / path
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        raise FilesystemContainmentError(
            f"Filesystem containment blocked {operation}: the target cannot be resolved safely."
        ) from None
    _require_path_within_project(resolved, root, operation)
    return resolved


def ensure_parent(path: Path, project_root: Path | None = None) -> None:
    """Create parents for an already resolved path without crossing the boundary."""
    _require_legacy_filesystem_enabled()
    root = canonical_project_root(project_root)
    safe_path = resolve_path(path, root, root, operation="ensure_parent")
    safe_path.parent.mkdir(parents=True, exist_ok=True)


def create_folder(path_text: str, cwd: Path, project_root: Path | None = None) -> dict:
    """Create a directory and verify it exists."""
    _require_legacy_filesystem_enabled()
    path = resolve_path(path_text, cwd, project_root, operation="create_folder")
    path.mkdir(parents=True, exist_ok=True)
    return {
        "success": path.exists() and path.is_dir(),
        "path": str(path),
        "message": f"Folder ready at {path}",
    }


def create_file(
    path_text: str,
    cwd: Path,
    content: str = "",
    project_root: Path | None = None,
) -> dict:
    """Create a new text file with optional initial content."""
    _require_legacy_filesystem_enabled()
    path = resolve_path(path_text, cwd, project_root, operation="create_file")
    ensure_parent(path, project_root)
    path.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Created file {path}",
    }


def write_file(
    path_text: str,
    content: str,
    cwd: Path,
    project_root: Path | None = None,
) -> dict:
    """Overwrite a text file with exact content."""
    _require_legacy_filesystem_enabled()
    path = resolve_path(path_text, cwd, project_root, operation="write_file")
    ensure_parent(path, project_root)
    path.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Wrote file {path}",
    }


def append_file(
    path_text: str,
    content: str,
    cwd: Path,
    project_root: Path | None = None,
) -> dict:
    """Append text content to an existing file."""
    _require_legacy_filesystem_enabled()
    path = resolve_path(path_text, cwd, project_root, operation="append_file")
    ensure_parent(path, project_root)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Appended to file {path}",
    }


def read_file(path_text: str, cwd: Path, project_root: Path | None = None) -> dict:
    """Read a UTF-8 text file."""
    path = resolve_path(path_text, cwd, project_root, operation="read_file")
    content = path.read_text(encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "content": content,
        "message": f"Read file {path}",
    }


def move_file(
    src_text: str,
    dst_text: str,
    cwd: Path,
    project_root: Path | None = None,
) -> dict:
    """Move or rename a file or directory."""
    _require_legacy_filesystem_enabled()
    src = resolve_path(src_text, cwd, project_root, operation="move_file source")
    dst = resolve_path(dst_text, cwd, project_root, operation="move_file destination")
    ensure_parent(dst, project_root)
    shutil.move(str(src), str(dst))
    return {
        "success": True,
        "src": str(src),
        "dst": str(dst),
        "message": f"Moved {src} to {dst}",
    }


def delete_file(path_text: str, cwd: Path, project_root: Path | None = None) -> dict:
    """Delete a file or an empty directory."""
    _require_legacy_filesystem_enabled()
    path = resolve_path(path_text, cwd, project_root, operation="delete_file")
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()
    return {
        "success": True,
        "path": str(path),
        "message": f"Deleted {path}",
    }


def search_in_project(
    pattern: str,
    path_text: str,
    cwd: Path,
    project_root: Path | None = None,
) -> dict:
    """Search for literal text in project files."""
    root = resolve_path(path_text, cwd, project_root, operation="search_in_project")
    matches: list[dict] = []

    for file_path in root.rglob("*"):
        safe_file_path = resolve_path(
            file_path,
            root,
            project_root,
            operation="search_in_project",
        )
        if not safe_file_path.is_file():
            continue
        try:
            text = safe_file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                matches.append(
                    {
                        "path": str(safe_file_path),
                        "line_number": line_number,
                        "line": line,
                    }
                )
        if len(matches) >= 100:
            break

    return {
        "success": True,
        "root": str(root),
        "pattern": pattern,
        "matches": matches,
        "message": f"Found {len(matches)} matches for {pattern!r}",
    }
