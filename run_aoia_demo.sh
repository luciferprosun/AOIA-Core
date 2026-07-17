#!/usr/bin/env bash
# Launcher for AOIA Control Chat — Competition Demo.
# Resolves its own directory, picks a Python 3.12+ interpreter, and
# launches the demo module. Sets no secrets. Does not require sudo.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN=""
for candidate in python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: no suitable Python 3 interpreter found on PATH." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c "import tkinter" >/dev/null 2>&1; then
    echo "ERROR: tkinter is not available for $PYTHON_BIN." >&2
    echo "Install the system package that provides Tkinter for your distribution" >&2
    echo "(for example, on Debian/Ubuntu/Linux Mint: 'sudo apt install python3-tk')" >&2
    echo "and re-run this script. This launcher will not install it automatically." >&2
    exit 1
fi

exec "$PYTHON_BIN" -m apps.aoia_desktop_demo
