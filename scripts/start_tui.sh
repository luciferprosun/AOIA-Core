#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/runtime"
VENV_DIR="$RUNTIME_DIR/.venv"

echo "AOIA Core TUI"
echo "Root: $ROOT_DIR"
echo "Controls: enter request or /model NAME, /clear, /status, Ctrl+A approve, Ctrl+X reject, Ctrl+C/Q quit"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Missing runtime virtualenv: $VENV_DIR"
  echo "Create it first and install runtime/requirements.txt."
  exit 1
fi

export PYTHONPATH="$RUNTIME_DIR:$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV_DIR/bin/python" -m tui.app
