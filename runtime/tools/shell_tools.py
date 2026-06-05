from __future__ import annotations

import time
from pathlib import Path


def shell_execute(
    command: str,
    cwd: Path,
    interactive: bool = False,
    timeout_seconds: int = 600,
) -> dict:
    """Block shell execution in reviewer-safe mode.

    Legacy runtime paths still call this function, so the lock lives here at the
    final subprocess boundary. A separately audited lab mode can replace this
    behavior later; the reviewer-safe default must not execute command text.
    """
    started = time.monotonic()
    duration = round(time.monotonic() - started, 3)
    return {
        "success": False,
        "blocked": True,
        "command": command,
        "cwd": str(cwd),
        "mode": "reviewer_safe_blocked",
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration_seconds": duration,
        "message": "Shell execution is blocked by the reviewer-safe execution lock.",
    }
