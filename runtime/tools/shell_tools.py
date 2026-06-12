from __future__ import annotations

import os
import time
from pathlib import Path


LEGACY_SHELL_EXECUTOR_SURFACE = True
APPROVED_RUNTIME_SHELL_EXECUTION_FLOW = False
SHELL_EXECUTION_FROZEN = True
AOIA_SHELL_EXECUTION_ENABLED = os.environ.get("AOIA_SHELL_EXECUTION_ENABLED") == "1"


def _legacy_shell_execution_enabled() -> bool:
    return AOIA_SHELL_EXECUTION_ENABLED or os.environ.get("AOIA_SHELL_EXECUTION_ENABLED") == "1"


def _require_legacy_shell_execution_enabled() -> None:
    if not _legacy_shell_execution_enabled():
        raise RuntimeError(
            "Legacy shell/executor surface is frozen and not approved for runtime use. "
            "Set AOIA_SHELL_EXECUTION_ENABLED=1 only for isolated legacy/manual testing."
        )


def shell_execution_blocked_result(command: str, cwd: Path) -> dict:
    duration = 0.0
    return {
        "success": False,
        "blocked": True,
        "frozen": True,
        "approved_runtime_shell_execution": False,
        "command": command,
        "cwd": str(cwd),
        "mode": "reviewer_safe_blocked",
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration_seconds": duration,
        "message": (
            "Legacy shell/executor surface is frozen and not approved by default. "
            "allowed=True or human approval does not authorize execution."
        ),
    }


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
    if not _legacy_shell_execution_enabled():
        result = shell_execution_blocked_result(command, cwd)
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        return result

    duration = round(time.monotonic() - started, 3)
    return {
        "success": False,
        "blocked": True,
        "frozen": True,
        "approved_runtime_shell_execution": False,
        "command": command,
        "cwd": str(cwd),
        "mode": "reviewer_safe_blocked",
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration_seconds": duration,
        "message": "No approved shell execution backend exists in AOIA production flow.",
    }
