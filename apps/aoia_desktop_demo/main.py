"""Entrypoint module for AOIA Control Chat — Competition Demo.

Launch with either:
    python3 -m apps.aoia_desktop_demo
    ./run_aoia_demo.sh

The tkinter availability check happens here, before anything imports
``ui.main_window`` (which imports ``tkinter`` at module scope) — this
keeps "tkinter missing" a clean, friendly one-line message instead of a
raw traceback.
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        import tkinter  # noqa: F401
    except ModuleNotFoundError:
        print(
            "ERROR: tkinter is not available on this Python installation.\n"
            "Install the system package that provides Tkinter for your distribution "
            "(for example, on Debian/Ubuntu/Linux Mint: 'python3-tk') and re-run this demo.\n"
            "This script will not install it automatically.",
            file=sys.stderr,
        )
        return 1

    from .ui.main_window import run_app

    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
