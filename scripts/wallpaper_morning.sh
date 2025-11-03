#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-"$0"}")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"
IMAGE="${RISET_DAY_IMAGE:-$ASSETS_DIR/morning.jpg}"

osascript <<EOF
tell application "System Events"
    set picture of every desktop to POSIX file "$IMAGE"
end tell
EOF
