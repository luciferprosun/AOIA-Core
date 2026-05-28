from __future__ import annotations

import os
import hashlib
from pathlib import Path


def aoia_state_home(project_dir: Path | None = None) -> Path:
    """Return the local writable AOIA runtime-state root.

    Source checkouts should stay clean during normal boot. Operators can set
    AOIA_HOME to override the default local state directory.
    """
    raw_home = os.getenv("AOIA_HOME", "").strip()
    if raw_home:
        return Path(raw_home).expanduser()
    return Path.home() / ".local" / "state" / "aoia"


def runtime_state_dir(project_dir: Path, namespace: str = "runtime") -> Path:
    root = aoia_state_home(project_dir)
    resolved = project_dir.resolve()
    name = resolved.name or "AOIA-Core"
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
    return root / f"{name}-{digest}" / namespace
