#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
MAIN_FILE="$PROJECT_DIR/main.py"
VENV_DIR="$PROJECT_DIR/.venv"

if [[ -x "$VENV_PYTHON" ]]; then
  exec "$VENV_PYTHON" "$MAIN_FILE" "$@"
fi

echo "Virtual environment not found. Using system python3 for the local runtime."
exec python3 "$MAIN_FILE" "$@"
