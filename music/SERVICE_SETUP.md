# Volumio Display Service Setup

This guide explains how to set up the Volumio Display service on a Raspberry Pi.

## Prerequisites

- Raspberry Pi running Raspberry Pi OS
- Python 3.7+
- FlaschenTaschen client installed (configure path in `ft.json`)
- Volumio running with API enabled
- systemd service already configured (volumio-display.service)

## Installation Steps

### 1. Install Dependencies

Run the setup script to install and configure Python dependencies:

```bash
cd /home/pi/FT/music
bash setup-pi.sh
```

This script will:
- Update system packages
- Install Python 3 and pip
- Install correct Socket.IO versions (Volumio 3 compatible: python-socketio==4.6.0, python-engineio==3.14.2)

### 2. Configure ft.json

Edit `/home/pi/FT/music/ft.json` to customize settings:

```json
{
    "name": "Polaris",
    "host": "localhost",
    "width": 64,
    "height": 64,
    "x_offset": 0,
    "y_offset": 0,
    "color": "00ff00",
    "font_name": "8x13B.bdf",
    "layer": 10,
    "volumio_url": "http://frontspeakers.local:3000",
    "ft_bin": "/home/pi/bin",
    "ft_fonts": "/home/pi/fonts"
}
```

**Configuration options:**
- `host`: FlaschenTaschen display hostname or IP
- `width` / `height`: Display resolution
- `x_offset` / `y_offset`: Text position offset in pixels
- `color`: Text color as hex (e.g., "00ff00" for green, "ff00ff" for magenta)
- `font_name`: BDF font filename (e.g., "8x13B.bdf", "9x15B.bdf")
- `layer`: Display layer 0-15 (default 10)
- `volumio_url`: Volumio API endpoint
- `ft_bin`: Path to FlaschenTaschen send-text binary
- `ft_fonts`: Path to BDF font files

### 3. Start the Service

If the service is already configured, start it:

```bash
sudo systemctl start volumio-display
sudo systemctl enable volumio-display
```

---

## Manual Dependency Installation

If you prefer to install dependencies manually:

```bash
sudo apt-get update
sudo apt-get install python3-pip
pip3 install -r /home/pi/FT/music/requirements.txt
```

The `requirements.txt` file locks the correct Socket.IO versions for Volumio 3 compatibility.

## Managing the Service

### View Status
```bash
systemctl status volumio-display
```

### View Logs
```bash
journalctl -u volumio-display -f           # Follow logs
journalctl -u volumio-display --since 1h   # Last hour
```

### Stop/Restart
```bash
sudo systemctl stop volumio-display
sudo systemctl restart volumio-display
```

### Disable at Startup
```bash
sudo systemctl disable volumio-display
```

## Troubleshooting

### Service fails to start
- Check logs: `journalctl -u volumio-display -n 50`
- Verify Python path: `which python3`
- Test manually: `python3 /home/pi/FT/music/volumio_websocket.py`

### No display updates
- Check Volumio is running: `curl http://frontspeakers.local:3000`
- Verify ft.json settings: `cat /home/pi/FT/music/ft.json`
- Test send-text directly: `/home/pi/flaschen-taschen/client/send-text -h localhost -g 64x64 "test"`

### Connection drops frequently
- Check network stability: `ping frontspeakers.local`
- Review socket.io settings in code (reconnection delays)
- Check Volumio logs

## Technical Details

- **Logging**: Output goes to systemd journal (accessible via `journalctl`)
- **Graceful Shutdown**: Responds to SIGTERM/SIGINT for clean disconnection
- **Auto-restart**: Restarts automatically on failure after 5 seconds
- **Config**: Loaded from `ft.json` relative to script location
- **Display Format**: `Artist - Title` (green text, 20pt font, left-aligned)

## Notes

- The service runs as user `pi` for file access
- Uncomment security options in the .service file to increase isolation if desired
- The display font is hardcoded to `8x13B.bdf`; edit `send_text()` function to change
