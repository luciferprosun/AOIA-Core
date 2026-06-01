from __future__ import annotations

import json
import os
from pathlib import Path

from runtime_paths import runtime_state_dir

from .filesystem_tools import resolve_path


IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "logs",
    ".pytest_cache",
}

ENTRYPOINT_NAMES = {
    "main.py",
    "app.py",
    "server.py",
    "server.mjs",
    "index.js",
    "index.html",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "run.sh",
    "run_web.sh",
}


def scan_project(path_text: str, cwd: Path, max_files: int = 400) -> dict:
    """Map a project tree and identify likely entrypoints."""
    root = resolve_path(path_text, cwd)
    if not root.exists() or not root.is_dir():
        return {
            "success": False,
            "path": str(root),
            "message": f"Project path does not exist or is not a directory: {root}",
        }

    files: list[str] = []
    entrypoints: list[str] = []
    directories: set[str] = set()
    extension_counts: dict[str, int] = {}

    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        current_path = Path(current_root)
        rel_dir = current_path.relative_to(root)
        if rel_dir.parts and len(rel_dir.parts) <= 2:
            directories.add(str(rel_dir))

        for filename in sorted(filenames):
            file_path = current_path / filename
            if not file_path.is_file():
                continue
            rel = str(file_path.relative_to(root))
            if len(files) < max_files:
                files.append(rel)
            suffix = file_path.suffix.lower() or "(none)"
            extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
            if file_path.name in ENTRYPOINT_NAMES:
                entrypoints.append(rel)

        total_seen = sum(extension_counts.values())
        if total_seen >= max_files * 3:
            break

    architecture = _summarize_architecture(root, entrypoints, extension_counts)
    report = {
        "root": str(root),
        "directories": sorted(directories)[:80],
        "entrypoints": sorted(entrypoints),
        "extension_counts": dict(sorted(extension_counts.items())),
        "sample_files": files,
        "architecture_summary": architecture,
    }

    report_path = runtime_state_dir(root) / "state" / "project_scan.json"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        report_path = None

    return {
        "success": True,
        "path": str(root),
        "project_scan": report,
        "scan_report_path": str(report_path) if report_path else "",
        "message": f"Scanned {root}. Found {len(entrypoints)} likely entrypoints.",
    }


def _summarize_architecture(root: Path, entrypoints: list[str], extension_counts: dict[str, int]) -> str:
    markers = []
    if (root / "package.json").exists():
        markers.append("JavaScript/Node project")
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        markers.append("Python project")
    if (root / "index.html").exists():
        markers.append("static/web frontend")
    if (root / "README.md").exists():
        markers.append("README present")
    if not markers:
        markers.append("generic file tree")

    top_extensions = ", ".join(
        f"{extension}:{count}"
        for extension, count in sorted(extension_counts.items(), key=lambda item: item[1], reverse=True)[:6]
    )
    return (
        f"{'; '.join(markers)}. "
        f"Likely entrypoints: {', '.join(entrypoints[:8]) or 'none detected'}. "
        f"Dominant file types: {top_extensions or 'none'}."
    )
