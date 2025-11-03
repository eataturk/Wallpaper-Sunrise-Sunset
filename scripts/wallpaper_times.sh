#!/usr/bin/env bash
set -euo pipefail

# Resolve location of companion scripts relative to this file unless overridden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-"$0"}")" && pwd)"
MORNING_SCRIPT="${MORNING_SCRIPT:-"$SCRIPT_DIR/wallpaper_morning.sh"}"
EVENING_SCRIPT="${EVENING_SCRIPT:-"$SCRIPT_DIR/wallpaper_evening.sh"}"

# Allow overriding python interpreter and location metadata via env vars
PYTHON_BIN="${RISET_PYTHON_BIN:-python3}"
LAT="${RISET_LAT:-41.0082}"
LON="${RISET_LON:--16.0216}"
TZ_LABEL="${RISET_TZ:-UTC+3}"
CITY_NAME="${RISET_CITY:-MyCity}"
REGION_NAME="${RISET_REGION:-MyRegion}"

export RISET_LAT="$LAT" \
       RISET_LON="$LON" \
       RISET_TZ="$TZ_LABEL" \
       RISET_CITY="$CITY_NAME" \
       RISET_REGION="$REGION_NAME"

# Directory for temporary plists
PLIST_DIR="$HOME/Library/LaunchAgents"
SUNRISE_PLIST="$PLIST_DIR/com.riset.sunrise.plist"
SUNSET_PLIST="$PLIST_DIR/com.riset.sunset.plist"

mkdir -p "$PLIST_DIR"

# Sanity check companions exist before proceeding
if [ ! -f "$MORNING_SCRIPT" ] || [ ! -f "$EVENING_SCRIPT" ]; then
  echo "Expected wallpaper scripts next to wallpaper_times.sh." >&2
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python interpreter not found: $PYTHON_BIN" >&2
    exit 1
  fi
fi

# Calculate today's sunrise and sunset using Python/Astral
SUNRISE_TIME=$("$PYTHON_BIN" - <<'END'
import os
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime

lat = float(os.environ["RISET_LAT"])
lon = float(os.environ["RISET_LON"])
tz = os.environ["RISET_TZ"]
city = os.environ["RISET_CITY"]
region = os.environ["RISET_REGION"]

location = LocationInfo(city, region, tz, lat, lon)
sun_times = sun(location.observer, date=datetime.now())
print(sun_times["sunrise"].strftime("%H:%M"))
END
)

SUNSET_TIME=$("$PYTHON_BIN" - <<'END'
import os
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime

lat = float(os.environ["RISET_LAT"])
lon = float(os.environ["RISET_LON"])
tz = os.environ["RISET_TZ"]
city = os.environ["RISET_CITY"]
region = os.environ["RISET_REGION"]

location = LocationInfo(city, region, tz, lat, lon)
sun_times = sun(location.observer, date=datetime.now())
print(sun_times["sunset"].strftime("%H:%M"))
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
