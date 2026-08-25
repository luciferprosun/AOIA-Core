#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "AOIA-Core installer"
echo "project_dir=$PROJECT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python3 not found"
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Virtual environment already exists."
fi

echo "Upgrading pip..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip

if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
  echo "Installing Python requirements..."
  "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
fi

echo "Checking optional local PDF tools..."
if command -v pdftotext >/dev/null 2>&1; then
  echo "pdftotext=available"
else
  echo "WARN: pdftotext not found. Install poppler-utils to rebuild raw PDF extraction."
fi

if command -v pdfinfo >/dev/null 2>&1; then
  echo "pdfinfo=available"
else
  echo "WARN: pdfinfo not found. Install poppler-utils to inspect PDF page counts."
fi

echo "Validating bundled JSON artifacts..."
"$VENV_DIR/bin/python" -m json.tool "$PROJECT_DIR/knowledge/canonical/rhcsa_commands.json" >/dev/null
"$VENV_DIR/bin/python" -m json.tool "$PROJECT_DIR/knowledge/index/command_index.json" >/dev/null
"$VENV_DIR/bin/python" -m json.tool "$PROJECT_DIR/knowledge/context/context_pack.json" >/dev/null

echo "Compiling core Python files..."
"$VENV_DIR/bin/python" -m py_compile \
  "$PROJECT_DIR/main.py" \
  "$PROJECT_DIR/webapp.py" \
  "$PROJECT_DIR/evidence_review/engine.py" \
  "$PROJECT_DIR/evidence_review/scenario.py" \
  "$PROJECT_DIR/knowledge/tools/pdf_extract.py" \
  "$PROJECT_DIR/knowledge/tools/section_parser.py" \
  "$PROJECT_DIR/knowledge/tools/canonical_builder.py" \
  "$PROJECT_DIR/knowledge/tools/index_builder.py" \
  "$PROJECT_DIR/knowledge/tools/context_pack_builder.py"

echo "Install complete."
echo "Run terminal app: ./run.sh"
echo "Run web app:      ./run_web.sh"
