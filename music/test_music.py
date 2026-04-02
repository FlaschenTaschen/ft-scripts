#!/usr/bin/env python3
import socketio
import time
import sys
import os
import json
import signal
import logging
import subprocess

# Setup logging for systemd
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load configuration from ft.json
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "ft-test.json")

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        FT_HOST = config.get("host", "localhost")
        WIDTH = config.get("width", 64)
        HEIGHT = config.get("height", 64)
        X_OFFSET = config.get("x_offset", 0)
        Y_OFFSET = config.get("y_offset", 0)
        COLOR = config.get("color", "00ff00")
        FONT_NAME = config.get("font_name", "8x13B.bdf")
        LAYER = config.get("layer", 10)
        VOLUMIO_URL = config.get("volumio_url", "http://frontspeakers.local:3000")
        FT_BIN = os.path.expanduser(config.get("ft_bin", "/home/pi/flaschen-taschen/client"))
        FT_FONTS = os.path.expanduser(config.get("ft_fonts", "/home/pi/flaschen-taschen/client/fonts"))
except Exception as e:
    logger.error(f"Error loading {CONFIG_FILE}: {e}")
    sys.exit(1)

sio = socketio.Client()
last_uri = None
last_rendered = None
shutdown_requested = False

def send_text(data: str, ft_host: str = FT_HOST, width: int = WIDTH, height: int = HEIGHT) -> None:
    """Send text to FlaschenTaschen display."""
    try:
        send_text_path = os.path.join(FT_BIN, "send-text")
        geometry = f"{width}x{height}+{X_OFFSET}+{Y_OFFSET}"
        font = os.path.join(FT_FONTS, FONT_NAME)
        subprocess.run(
            [send_text_path, "-s0", "-c" + COLOR, "-l" + str(LAYER), "-g" + geometry,
             "-h" + ft_host, "-f" + font, data],
            check=False,
            timeout=30
        )
    except Exception as e:
        logger.error(f"Error sending text to display: {e}")

def update_display(artist: str, title: str) -> None:
    """Update display with current track info."""
    line = f"{artist} - {title}"
    logger.info(f"Updating display: {line}")
    send_text(line)

@sio.event
def connect():
    logger.info("Connected to Volumio")
    sio.emit("getState")

@sio.event
def disconnect():
    logger.info("Disconnected from Volumio")

@sio.on("pushState")
def on_push_state(data):
    global last_uri, last_rendered

    title = (data.get("title") or "").strip()
    artist = (data.get("artist") or "").strip()
    uri = (data.get("uri") or "").strip()
    status = (data.get("status") or "").strip()

    # Ignore empty updates
    if not title and not artist and not uri:
        return

    # Fallback text
    if not artist:
        artist = "Unknown artist"
    if not title:
        title = "Unknown title"

    # Detect a new track by URI
    if uri and uri != last_uri:
        last_uri = uri
        text = f"{artist} - {title}"

        # Prevent duplicate redraws
        if text != last_rendered:
            last_rendered = text
            update_display(artist, title)

    # Optional: also handle stream metadata changes with same URI
    elif not uri:
        text = f"{artist} - {title}"
        if text != last_rendered:
            last_rendered = text
            update_display(artist, title)

def signal_handler(signum, frame):
    """Handle SIGTERM and SIGINT for graceful shutdown."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown_requested = True
    if sio.connected:
        sio.disconnect()
    sys.exit(0)

def main():
    """Main loop: connect to Volumio and listen for track changes."""
    global shutdown_requested

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info(f"Starting Volumio WebSocket client (connecting to {VOLUMIO_URL})")
    logger.info(f"Display: {FT_HOST} ({WIDTH}x{HEIGHT})")

    while not shutdown_requested:
        try:
            sio.connect(VOLUMIO_URL)
            sio.wait()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Connection error: {e}")
            if not shutdown_requested:
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)

if __name__ == "__main__":
    main()
