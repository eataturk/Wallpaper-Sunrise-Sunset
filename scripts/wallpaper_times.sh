#!/usr/bin/env bash

# Paths to your wallpaper scripts
MORNING_SCRIPT="/Users/emirata/bin/wallpaper_morning.sh"
EVENING_SCRIPT="/Users/emirata/bin/wallpaper_evening.sh"

# Directory for temporary plists
PLIST_DIR="$HOME/Library/LaunchAgents"
SUNRISE_PLIST="$PLIST_DIR/com.emirata.wallpaper.sunrise.plist"
SUNSET_PLIST="$PLIST_DIR/com.emirata.wallpaper.sunset.plist"

# Calculate today's sunrise and sunset using Python/Astral
SUNRISE_TIME=$(~/python_venv/bin/python3 - <<END
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime
city = LocationInfo("MyCity","MyRegion","UTC+3", 41.0082, -16.0216)  # replace with your lat/lon
s = sun(city.observer, date=datetime.now())
print(s['sunrise'].strftime("%H:%M"))
END
)

SUNSET_TIME=$(~/python_venv/bin/python3 - <<END
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime
city = LocationInfo("MyCity","MyRegion","UTC+3", 41.0082, -16.0216)
s = sun(city.observer, date=datetime.now())
print(s['sunset'].strftime("%H:%M"))
END
)

# Extract hours and minutes
SUNRISE_HOUR=$(echo $SUNRISE_TIME | cut -d':' -f1)
SUNRISE_MIN=$(echo $SUNRISE_TIME | cut -d':' -f2)
SUNSET_HOUR=$(echo $SUNSET_TIME | cut -d':' -f1)
SUNSET_MIN=$(echo $SUNSET_TIME | cut -d':' -f2)

# Get current hour and minute
CURRENT_HOUR=$(date +%H)
CURRENT_MIN=$(date +%M)

# Function to create plist
create_plist() {
  local plist_path=$1
  local script_path=$2
  local hour=$3
  local min=$4

  cat > "$plist_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$(basename $plist_path .plist)</string>
    <key>ProgramArguments</key>
    <array>
        <string>$script_path</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>$hour</integer>
        <key>Minute</key><integer>$min</integer>
    </dict>
    <key>RunAtLoad</key><false/>
</dict>
</plist>
EOF
}

# Create sunrise and sunset plists
create_plist "$SUNRISE_PLIST" "$MORNING_SCRIPT" "$SUNRISE_HOUR" "$SUNRISE_MIN"
create_plist "$SUNSET_PLIST" "$EVENING_SCRIPT" "$SUNSET_HOUR" "$SUNSET_MIN"

# Run wallpaper immediately if already past the scheduled time
if [ "$CURRENT_HOUR" -gt "$SUNRISE_HOUR" ] || { [ "$CURRENT_HOUR" -eq "$SUNRISE_HOUR" ] && [ "$CURRENT_MIN" -ge "$SUNRISE_MIN" ]; }; then
    bash "$MORNING_SCRIPT"
fi

if [ "$CURRENT_HOUR" -gt "$SUNSET_HOUR" ] || { [ "$CURRENT_HOUR" -eq "$SUNSET_HOUR" ] && [ "$CURRENT_MIN" -ge "$SUNSET_MIN" ]; }; then
    bash "$EVENING_SCRIPT"
fi

# Load them into launchd
launchctl bootout gui/$(id -u) "$SUNRISE_PLIST" 2>/dev/null
launchctl bootstrap gui/$(id -u) "$SUNRISE_PLIST"

launchctl bootout gui/$(id -u) "$SUNSET_PLIST" 2>/dev/null
launchctl bootstrap gui/$(id -u) "$SUNSET_PLIST"