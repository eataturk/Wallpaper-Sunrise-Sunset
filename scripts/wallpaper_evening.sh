#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-"$0"}")" && pwd)"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"
IMAGE="$(ls -t "$ASSETS_DIR"/evening* 2>/dev/null | head -n1)"
if [[ -z "$IMAGE" ]]; then
    echo "No file found in $ASSETS_DIR starting with 'evening'." >&2
    exit 1
fi

osascript <<EOF
tell application "System Events"
    set picture of every desktop to POSIX file "$IMAGE"
end tell
EOF
