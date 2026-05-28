from __future__ import annotations

import shutil
from pathlib import Path


def resolve_path(path_text: str, cwd: Path) -> Path:
    """Resolve user-provided paths against the current working directory."""
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return path.resolve()


def ensure_parent(path: Path) -> None:
    """Create parent directories before writing files."""
    path.parent.mkdir(parents=True, exist_ok=True)


def create_folder(path_text: str, cwd: Path) -> dict:
    """Create a directory and verify it exists."""
    path = resolve_path(path_text, cwd)
    path.mkdir(parents=True, exist_ok=True)
    return {
        "success": path.exists() and path.is_dir(),
        "path": str(path),
        "message": f"Folder ready at {path}",
    }


def create_file(path_text: str, cwd: Path, content: str = "") -> dict:
    """Create a new text file with optional initial content."""
    path = resolve_path(path_text, cwd)
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Created file {path}",
    }


def write_file(path_text: str, content: str, cwd: Path) -> dict:
    """Overwrite a text file with exact content."""
    path = resolve_path(path_text, cwd)
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Wrote file {path}",
    }


def append_file(path_text: str, content: str, cwd: Path) -> dict:
    """Append text content to an existing file."""
    path = resolve_path(path_text, cwd)
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)
    return {
        "success": True,
        "path": str(path),
        "bytes_written": len(content.encode("utf-8")),
        "message": f"Appended to file {path}",
    }


def read_file(path_text: str, cwd: Path) -> dict:
    """Read a UTF-8 text file."""
    path = resolve_path(path_text, cwd)
    content = path.read_text(encoding="utf-8")
    return {
        "success": True,
        "path": str(path),
        "content": content,
        "message": f"Read file {path}",
    }


def move_file(src_text: str, dst_text: str, cwd: Path) -> dict:
    """Move or rename a file or directory."""
    src = resolve_path(src_text, cwd)
    dst = resolve_path(dst_text, cwd)
    ensure_parent(dst)
    shutil.move(str(src), str(dst))
    return {
        "success": True,
        "src": str(src),
        "dst": str(dst),
        "message": f"Moved {src} to {dst}",
    }


def delete_file(path_text: str, cwd: Path) -> dict:
    """Delete a file or an empty directory."""
    path = resolve_path(path_text, cwd)
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()
    return {
        "success": True,
        "path": str(path),
        "message": f"Deleted {path}",
    }


def search_in_project(pattern: str, path_text: str, cwd: Path) -> dict:
    """Search for literal text in project files."""
    root = resolve_path(path_text, cwd)
    matches: list[dict] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                matches.append(
                    {
                        "path": str(file_path),
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
