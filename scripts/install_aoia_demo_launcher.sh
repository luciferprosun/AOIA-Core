#!/usr/bin/env bash
# Optional: install a user-local .desktop launcher for AOIA Control Chat.
# This script does nothing unless the human explicitly runs it. It never
# runs automatically as part of building or launching the demo, and it
# never requires root — everything is installed under the user's own
# local application directory.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHER_SCRIPT="$REPO_ROOT/run_aoia_demo.sh"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$APPS_DIR/aoia-control-chat-demo.desktop"

if [ ! -x "$LAUNCHER_SCRIPT" ]; then
    echo "ERROR: expected launcher not found or not executable: $LAUNCHER_SCRIPT" >&2
    exit 1
fi

mkdir -p "$APPS_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=AOIA Control Chat — Competition Demo
Comment=Human-controlled epistemic-control desktop chat demo (AOIA-Core)
Exec=$LAUNCHER_SCRIPT
Terminal=false
Categories=Development;Utility;
EOF

chmod +x "$DESKTOP_FILE"
echo "Installed: $DESKTOP_FILE"
echo "This only affects your user-local application menu; no system-wide files were changed."
