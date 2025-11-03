#!/usr/bin/env bash
VERSION= "0.2.7"
IMAGE="/opt/homebrew/Cellar/riset/$VERSION/share/riset/assets/morning.jpg"
osascript <<EOF
tell application "System Events"
    set picture of every desktop to POSIX file "$IMAGE"
end tell
EOF
