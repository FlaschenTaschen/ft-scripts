#!/bin/zsh

# Get MUNI bus stops and arrival estimates using 511.org API
# Organized into functions for easy reuse
#
# Requirements:
#   - SF_TRANSIT_API_KEY environment variable set
#   - MUNI_AGENCY (optional, defaults to "SF")

set -e

AGENCY="${MUNI_AGENCY:-SF}"

# ============================================================================
# Utility function to check environment
# ============================================================================
check_api_key() {
    if [[ -z "$SF_TRANSIT_API_KEY" ]]; then
        echo "Error: SF_TRANSIT_API_KEY environment variable not set"
        return 1
    fi
}

# ============================================================================
# Download and extract regional GTFS data
# ============================================================================
download_gtfs() {
    local tmpdir="$1"
    echo "Downloading regional GTFS data..."

    curl -s -L -o "$tmpdir/regional_gtfs.zip" \
        "http://api.511.org/transit/datafeeds?api_key=${SF_TRANSIT_API_KEY}&operator_id=RG"

    if [[ ! -f "$tmpdir/regional_gtfs.zip" ]]; then
        echo "Error: Failed to download GTFS data"
        return 1
    fi

    unzip -q -o "$tmpdir/regional_gtfs.zip" stops.txt -d "$tmpdir"

    if [[ ! -f "$tmpdir/stops.txt" ]]; then
        echo "Error: Failed to extract stops.txt"
        return 1
    fi
}

# ============================================================================
# Find nearby stops given coordinates
# ============================================================================
find_nearby_stops() {
    local lat="$1"
    local lon="$2"
    local stops_file="$3"
    local count="${4:-3}"

    awk -F, -v lat="$lat" -v lon="$lon" '
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
  print dist, $(id), $(name), $(slat), $(slon)
}
' "$stops_file" | sort -t' ' -k1,1n | head -$count
}

# ============================================================================
# Get arrival estimates for a single stop
# ============================================================================
get_arrivals_for_stop() {
    local stop_code="$1"
    local max_arrivals="${2:-3}"

    curl -s --compressed \
        "http://api.511.org/transit/StopMonitoring?api_key=${SF_TRANSIT_API_KEY}&agency=${AGENCY}&stopCode=${stop_code}&format=json" \
        | python3 -c "import sys, json; text = sys.stdin.read().lstrip('\ufeff'); print(json.dumps(json.loads(text)))" \
        | jq -r '.ServiceDelivery.StopMonitoringDelivery.MonitoredStopVisit[] | {
            line: .MonitoredVehicleJourney.LineRef,
            destination: .MonitoredVehicleJourney.DestinationName,
            expectedArrival: .MonitoredVehicleJourney.MonitoredCall.ExpectedArrivalTime
          } | "\(.line) to \(.destination): \(.expectedArrival)"' 2>/dev/null | head -$max_arrivals
}

# ============================================================================
# Display stop info with arrivals
# ============================================================================
display_stop_with_arrivals() {
    local dist="$1"
    local stop_code="$2"
    local stop_name="$3"

    echo "Stop Code: $stop_code"
    echo "Stop Name: $stop_name"
    echo "Distance: $(printf "%.3f" $dist) km"
    echo ""

    local arrivals=$(get_arrivals_for_stop "$stop_code")

    if [[ -n "$arrivals" ]]; then
        echo "Next arrivals:"
        echo "$arrivals" | sed 's/^/  /'
    else
        echo "No arrival data available"
    fi
    echo ""
}

show_arrivals_for_stop() {
    local stop_code="$1"
    local arrivals=$(get_arrivals_for_stop "$stop_code")

    if [[ -n "$arrivals" ]]; then
        echo "Next arrivals:"
        echo "$arrivals" | sed 's/^/  /'
    else
        echo "No arrival data available"
    fi
    echo ""
}

# ============================================================================
# Main: Find nearby stops and show arrivals
# ============================================================================
main() {
    if [[ -z "$1" || -z "$2" ]]; then
        echo "Usage: $0 <latitude> <longitude> [num_stops]"
        echo "Example: $0 37.7749 -122.4194 3"
        exit 1
    fi

    local lat="$1"
    local lon="$2"
    local count="${3:-3}"

    check_api_key || exit 1

    local tmpdir=$(mktemp -d)
    trap "rm -rf $tmpdir" EXIT

    download_gtfs "$tmpdir" || exit 1

    echo "Finding $count nearest stops for coordinates: $lat, $lon"
    echo ""

    local nearby_stops=$(find_nearby_stops "$lat" "$lon" "$tmpdir/stops.txt" "$count")

    while IFS='|' read -r dist stop_code stop_name lat lon; do
        display_stop_with_arrivals "$dist" "$stop_code" "$stop_name"
        echo "---"
        echo ""
    done <<< "$nearby_stops"
}

# main "$@"

show_arrivals_for_stop 14352
show_arrivals_for_stop 14125
show_arrivals_for_stop 14126
