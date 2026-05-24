from __future__ import annotations

import subprocess
import time
from pathlib import Path


def shell_execute(
    command: str,
    cwd: Path,
    interactive: bool = False,
    timeout_seconds: int = 600,
) -> dict:
    """Execute a shell command through bash.

    `bash -lc` is used intentionally so the runtime can support:
    - quoted strings
    - redirects
    - pipes
    - `&&` and `;`

    Interactive mode is reserved for commands that may prompt the user, such as
    `sudo apt install ...`.
    """
    started = time.monotonic()
    process_args = ["bash", "-lc", command]

    if interactive:
        completed = subprocess.run(
            process_args,
            cwd=str(cwd),
            text=True,
        )
        stdout = ""
        stderr = ""
    else:
        completed = subprocess.run(
            process_args,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr

    duration = round(time.monotonic() - started, 3)
    return {
        "success": completed.returncode == 0,
        "command": command,
        "cwd": str(cwd),
        "mode": "interactive" if interactive else "captured",
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": completed.returncode,
        "duration_seconds": duration,
    }
