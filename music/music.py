#!/usr/bin/python3
import requests
import subprocess
import sys
import json
import os

# Load configuration from ft.json
config_path = os.path.join(os.path.dirname(__file__), "../muni/ft.json")
with open(config_path) as f:
    config = json.load(f)

FT_HOST = config["host"]
WIDTH = config["width"]
HEIGHT = config["height"]
VOLUMIO_IP = "frontspeakers.local"

def send_text(data, ft_host=FT_HOST, width=WIDTH, height=HEIGHT):
    color = "00ff00"
    # Note: On macOS, ensure 'send-text' is in your PATH or provide the full path here.
    send_text_path = "/home/pi/flaschen-taschen/client/send-text"
    geometry = f"{width}x{height}"
    font = "/home/pi/flaschen-taschen/client/fonts/9x15.bdf"
    subprocess.run(["timeout", "20",send_text_path,"-s20","-c"+color,"-l4","-g"+geometry,"-h"+ft_host,"-f"+font,'-O',data])

def get_playing_song():
    """Fetch status from the shared Volumio instance."""
    response = requests.get(f"http://{VOLUMIO_IP}/api/v1/getState")
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "play":
            if len(data["title"]) > 0:
                return data["artist"]+" "+data["title"]
    return None

def main():
    song = get_playing_song()
    if song:
        print(f"Fetching song from {VOLUMIO_IP}...")
        print(f"Sending to {FT_HOST} ({WIDTH}x{HEIGHT}): {song}")
        send_text(song)
    else:
        print(f"No song is currently playing on {VOLUMIO_IP}.")

if __name__ == "__main__":
    main()
