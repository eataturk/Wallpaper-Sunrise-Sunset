#!/usr/bin/env bash
VERSION= "0.2.5"
IMAGE="/opt/homebrew/Cellar/riset/$VERSION/share/riset/assets/evening.jpg"
osascript <<EOF
tell application "System Events"
    set picture of every desktop to POSIX file "$IMAGE"
end tell
EOF
