#!/usr/bin/python3
import subprocess
import sys
import os
import json
import transit
import time

# Load configuration from ft.json
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "ft.json")

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        FT_HOST = config.get("host", "localhost")
        WIDTH = config.get("width", 64)
        HEIGHT = config.get("height", 64)
        X_OFFSET = config.get("x_offset", 0)
        Y_OFFSET = config.get("y_offset", 0)
        COLOR = config.get("color", "00ffff")
        FONT_NAME = config.get("font_name", "8x13B.bdf")
        LAYER = config.get("layer", 10)
        SCROLL = config.get("scroll", 0)
        DISPLAY_DELAY = config.get("display_delay", 3)
        FT_BIN = os.path.expanduser(config.get("ft_bin", "/home/pi/bin"))
        FT_FONTS = os.path.expanduser(config.get("ft_fonts", "/home/pi/fonts"))
except Exception as e:
    print(f"Error loading {CONFIG_FILE}: {e}")
    sys.exit(1)

def send_text(data, ft_host=FT_HOST, width=WIDTH, height=HEIGHT):
    send_text_path = os.path.join(FT_BIN, "send-text")
    geometry = f"{width}x{height}+{X_OFFSET}+{Y_OFFSET}"
    font = os.path.join(FT_FONTS, FONT_NAME)
    cmd = [send_text_path, "-s" + str(SCROLL), "-c" + COLOR, "-l" + str(LAYER), "-g" + geometry, "-h" + ft_host, "-f" + font]
    if SCROLL > 0:
        cmd.append("-O")
    cmd.append(data)
    subprocess.run(cmd, check=False, timeout=30)

def main():
    try:
        # Find 3 nearest stops to Sequoia Fabrica
        print("Finding 3 nearest stops to Sequoia Fabrica...")
        stops = transit.find_stops_within_radius("Sequoia Fabrica", radius_miles=0.25)

        if not stops:
            print("No stops found")
            return

        # Use first 3 nearest stops
        stops = stops[:3]

        # Collect all arrivals grouped by line
        lines_arrivals = {}

        for i, stop in enumerate(stops):
            stop_code = stop['code']
            stop_name = stop['name']

            print(f"Getting arrivals for {stop_name} ({stop_code})...")
            arrivals = transit.get_arrivals_for_stop(stop_code, max_arrivals=1)

            if arrivals:
                first_arrival = arrivals[0]
                line = first_arrival['line']
                minutes = first_arrival['minutes_until']

                # Group by line number
                if line not in lines_arrivals:
                    lines_arrivals[line] = []
                lines_arrivals[line].append((minutes, stop_name))
            else:
                print(f"No arrivals for {stop_code}")

            # Rate limiting: wait between requests
            if i < len(stops) - 1:
                time.sleep(0.5)

        # Display all lines with sorted arrival times
        for line in sorted(lines_arrivals.keys()):
            arrivals = sorted(lines_arrivals[line])
            times_str = ", ".join([f"{m}" for m, stop in arrivals])
            stop_names = ", ".join(sorted(set([stop for m, stop in arrivals])))
            msg = f"{line}: {times_str}: {stop_names}"
            print(f"Sending to {FT_HOST} ({WIDTH}x{HEIGHT}): {msg}")
            send_text(msg)
            time.sleep(DISPLAY_DELAY)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
