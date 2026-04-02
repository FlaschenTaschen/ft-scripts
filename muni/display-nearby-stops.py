#!/usr/bin/python3
"""
Display nearby MUNI stops for a location with next arrivals.
Uses transit.py library and coordinates.json.

Usage:
    ./display-nearby-stops.py [location_name] [radius_miles] [max_stops]

Examples:
    ./display-nearby-stops.py                    # Sequoia Fabrica, 0.25 miles
    ./display-nearby-stops.py "Sequoia Fabrica" 0.5
    ./display-nearby-stops.py "Home" 0.75 5
"""

import sys
import time
import transit

def main():
    # Parse arguments
    location = sys.argv[1] if len(sys.argv) > 1 else "Sequoia Fabrica"
    radius = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
    max_stops = int(sys.argv[3]) if len(sys.argv) > 3 else None

    try:
        # Find nearby stops
        print(f"Finding stops near '{location}' within {radius} miles...\n")
        stops = transit.find_stops_within_radius(location, radius_miles=radius)

        if not stops:
            print(f"No stops found within {radius} miles of '{location}'")
            return

        # Limit number of stops to display (default 5 to avoid API rate limiting)
        if max_stops is None:
            max_stops = 5
        stops = stops[:max_stops]

        print(f"Found {len(stops)} stops (showing first {len(stops)}):\n")
        print("-" * 80)

        for i, stop in enumerate(stops, 1):
            print(f"\n{i}. {stop['name']}")
            print(f"   Code: {stop['code']} | Distance: {stop['distance_km']} km")

            # Get arrivals for this stop
            try:
                arrivals = transit.get_arrivals_for_stop(stop['code'], max_arrivals=3)

                if arrivals:
                    print(f"   Next arrivals:")
                    for arr in arrivals:
                        print(f"     • Line {arr['line']} to {arr['destination']}: {arr['minutes_until']} min")
                else:
                    print(f"   No arrivals available")
            except Exception as e:
                print(f"   No arrivals available")

            # Rate limiting: wait 0.5 seconds between API calls to avoid 429 errors
            if i < len(stops):
                time.sleep(0.5)

        print(f"\n{'-' * 80}\n")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
