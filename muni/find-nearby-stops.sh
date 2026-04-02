#!/bin/zsh

# Find all MUNI bus stops within a radius of a named location
# Usage: ./find-nearby-stops.sh <location_name> [radius_miles]
# Example: ./find-nearby-stops.sh "Sequoia Fabrica" 0.5
# Default radius: 0.25 miles if not specified
#
# Requirements:
#   - SF_TRANSIT_API_KEY environment variable set
#   - coordinates.json in same directory with location data
#   - get-nearby-stops.sh functions available (source it)

if [[ -z "$1" ]]; then
    echo "Usage: $0 <location_name> [radius_miles]"
    echo "Example: $0 \"Sequoia Fabrica\" 0.5"
    echo "Default radius: 0.25 miles"
    exit 1
fi

LOCATION_NAME="$1"
RADIUS_MILES="${2:-0.25}"

AGENCY="${MUNI_AGENCY:-SF}"

if [[ -z "$SF_TRANSIT_API_KEY" ]]; then
    echo "Error: SF_TRANSIT_API_KEY environment variable not set"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COORDS_FILE="$SCRIPT_DIR/coordinates.json"

if [[ ! -f "$COORDS_FILE" ]]; then
    echo "Error: coordinates.json not found in $SCRIPT_DIR"
    exit 1
fi

# Look up location by name in coordinates.json
LOCATION=$(python3 -c "
import json
import sys

location_name = '$LOCATION_NAME'
coords_file = '$COORDS_FILE'

try:
    with open(coords_file, 'r') as f:
        locations = json.load(f)

    for loc in locations:
        if loc.get('name', '').lower() == location_name.lower():
            print(f\"{loc.get('latitude')} {loc.get('longitude')}\")
            sys.exit(0)

    print(f\"Location '{location_name}' not found in coordinates.json\", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f\"Error reading coordinates.json: {e}\", file=sys.stderr)
    sys.exit(1)
")

if [[ -z "$LOCATION" ]]; then
    exit 1
fi

LAT=$(echo "$LOCATION" | awk '{print $1}')
LON=$(echo "$LOCATION" | awk '{print $2}')

# Convert miles to kilometers (1 mile = 1.60934 km)
RADIUS_KM=$(python3 -c "print(round($RADIUS_MILES * 1.60934, 3))")

# Source the functions from get-nearby-stops.sh (suppress test output)
source "$SCRIPT_DIR/get-nearby-stops.sh" 2>/dev/null || true

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "Finding stops within $RADIUS_MILES miles of \"$LOCATION_NAME\""
echo "Coordinates: $LAT, $LON | Radius: $RADIUS_KM km"
echo ""

download_gtfs "$TMPDIR" || exit 1

# Use the awk-based function to find stops within radius
NEARBY_STOPS=$(awk -F, -v lat="$LAT" -v lon="$LON" -v radius="$RADIUS_KM" '
BEGIN { OFS="|" }
NR==1 {
  for (i=1; i<=NF; i++) {
    if ($i=="stop_id") id=i;
    if ($i=="stop_name") name=i;
    if ($i=="stop_lat") slat=i;
    if ($i=="stop_lon") slon=i;
  }
  next
}
{
  if ($(slat)==""  || $(slon)=="") next
  dlat = ($(slat)-lat) * 111.32
  dlon = ($(slon)-lon) * 111.32 * cos(lat * 3.1415926535 / 180)
  dist = sqrt(dlat*dlat + dlon*dlon)

  if (dist <= radius) {
    print dist, $(id), $(name), $(slat), $(slon)
  }
}
' "$TMPDIR/stops.txt" | sort -t' ' -k1,1n)

if [[ -z "$NEARBY_STOPS" ]]; then
    echo "No stops found within $RADIUS_MILES miles"
    exit 0
fi

echo "Stop Code | Stop Name | Distance"
echo "-----------|-----------|----------"

while IFS='|' read -r dist stop_code stop_name lat lon; do
    printf "%-10s | %-40s | %.3f km\n" "$stop_code" "$stop_name" "$dist"
done <<< "$NEARBY_STOPS"

echo ""
echo "Stop codes for use in scripts:"
echo "$NEARBY_STOPS" | awk -F'|' '{printf "%s ", $2}'
echo ""
