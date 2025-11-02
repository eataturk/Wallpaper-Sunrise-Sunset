#!/usr/bin/env bash
IMAGE="/Users/emirata/Documents/everything_else/wallpaper/Backgrounds/Crosscode_Background_2.jpg"
osascript <<EOF
tell application "System Events"
    set picture of every desktop to POSIX file "$IMAGE"
end tell
EOF
