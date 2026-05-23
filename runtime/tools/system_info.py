from __future__ import annotations

import os
from pathlib import Path


def detect_desktop_dir(home: Path | None = None) -> Path:
    """Detect the real desktop directory on Linux Mint/XDG systems."""
    home = home or Path.home()
    xdg_config = home / ".config" / "user-dirs.dirs"
    desktop = home / "Desktop"
    pulpit = home / "Pulpit"

    if xdg_config.exists():
        for raw in xdg_config.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line.startswith("XDG_DESKTOP_DIR="):
                continue

            _, value = line.split("=", 1)
            value = value.strip().strip('"').replace("$HOME", str(home))
            path = Path(os.path.expanduser(value))
            if path.exists():
                return path

    if desktop.exists():
        return desktop
    if pulpit.exists():
        return pulpit
    return home


def build_runtime_context(project_dir: Path, cwd: Path) -> dict:
    """Build a compact runtime snapshot for prompting and logs."""
    home = Path.home()
    return {
        "home_dir": str(home),
        "desktop_dir": str(detect_desktop_dir(home)),
        "current_cwd": str(cwd),
        "current_project": str(project_dir),
    }
