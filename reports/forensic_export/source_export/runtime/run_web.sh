#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
WEB_FILE="$PROJECT_DIR/webapp.py"

if [[ -x "$VENV_PYTHON" ]]; then
  exec "$VENV_PYTHON" "$WEB_FILE" "$@"
fi

echo "Virtual environment not found. Using system python3 for the web runtime."
exec python3 "$WEB_FILE" "$@"
