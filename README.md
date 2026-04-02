# FlaschenTaschen Display Scripts

Scripts to display real-time music and transit information on a FlaschenTaschen LED display.

## Overview

This repository contains two main features:

- **Music Display**: Shows current playing track from Volumio on the LED display
- **Transit Display**: Shows upcoming MUNI bus arrivals for nearby stops

Both scripts send formatted text to a FlaschenTaschen display using the `send-text` command-line utility.

## Project Structure

```
ft-scripts/
├── music/              # Music display scripts
│   ├── music.py        # One-shot script to display current song
│   ├── volumio_websocket.py  # Continuous listener for Volumio
│   ├── mock_volumio.py # Mock server for testing
│   ├── test_music.py   # Tests
│   ├── requirements.txt # Python dependencies
│   └── setup-pi.sh     # Raspberry Pi setup script
├── muni/               # Transit display scripts
│   ├── muni.py         # Display nearby transit arrivals
│   ├── transit.py      # Transit library (stops, arrivals)
│   ├── coordinates.json # Named locations (lat/lon)
│   ├── ft.json         # Display configuration
│   └── *.sh            # Helper scripts for finding stops
```

## Requirements

- Python 3.6+
- FlaschenTaschen display and client tools (`send-text`)
- Volumio instance (for music display)
- API keys (for transit display)

## Setup

### 1. Install Python Dependencies

```bash
# For music display
pip install -r music/requirements.txt

# For transit display
pip install requests
```

### 2. Configure Display Settings

Create `ft.json` files in each directory to configure the display:

```json
{
  "host": "192.168.1.100",
  "width": 64,
  "height": 64,
  "x_offset": 0,
  "y_offset": 0,
  "color": "00ff00",
  "font_name": "8x13B.bdf",
  "layer": 10,
  "ft_bin": "/home/pi/bin",
  "ft_fonts": "/home/pi/fonts"
}
```

**Configuration Options:**
- `host`: IP address or hostname of FlaschenTaschen server
- `width`, `height`: Display dimensions in pixels
- `x_offset`, `y_offset`: Display position offset
- `color`: Text color in hex (RGB format, no #)
- `font_name`: Font file name (from `ft_fonts` directory)
- `layer`: Display layer priority
- `ft_bin`: Path to FlaschenTaschen client binaries
- `ft_fonts`: Path to font files

## Music Display

### Quick Display

Display the currently playing track from Volumio:

```bash
cd music
python3 music.py
```

### Continuous Display

Listen for track changes and update the display in real-time:

```bash
cd music
python3 volumio_websocket.py
```

This script connects to Volumio via WebSocket and updates the display whenever the track changes.

**Configuration (in `ft.json`):**
```json
{
  "volumio_url": "http://frontspeakers.local:3000"
}
```

### Requirements

The music display requires:
- Volumio instance running with API enabled
- Network access to Volumio (`frontspeakers.local` by default)
- FlaschenTaschen client tools installed and configured

### Testing

```bash
# Test with mock Volumio server
python3 test_music.py
```

## Transit Display

### Display Nearby Arrivals

Show upcoming arrivals for MUNI buses near "Sequoia Fabrica":

```bash
cd muni
python3 muni.py
```

This script:
1. Finds the 3 nearest transit stops to your configured location
2. Gets arrival times for each stop
3. Groups arrivals by line number
4. Displays them on the LED display

### Configuration

**Environment Variables:**
```bash
export SF_TRANSIT_API_KEY="your-api-key-here"
export MUNI_AGENCY="SF"  # Optional, defaults to "SF"
```

**Or create `~/.transit` file for cron jobs:**
```bash
export SF_TRANSIT_API_KEY="your-api-key-here"
```

Then source it in scripts:
```bash
. ~/.transit
```

**Locations (`coordinates.json`):**

Add named locations for easy reference:

```json
[
  {
    "name": "Sequoia Fabrica",
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  {
    "name": "Home",
    "latitude": 37.7751,
    "longitude": -122.4192
  }
]
```

Then use them in scripts:
```python
stops = transit.find_stops_within_radius("Sequoia Fabrica", radius_miles=0.25)
```

**Display Configuration (in `ft.json`):**
```json
{
  "display_delay": 3,
  "scroll": 0
}
```

### API Key

Get a transit API key from [511.org](https://511.org/):

1. Visit [511.org/open-data/api](https://511.org/open-data/api)
2. Register for an API key
3. Set `SF_TRANSIT_API_KEY` environment variable
4. API has a 60 requests/hour limit (caching helps)

### Caching

Transit data is cached locally in `~/.cache/muni/`:
- `arrivals.json`: Arrival times (2-minute TTL)
- `stops.txt`: Stop information (24-hour TTL)

This helps avoid hitting API rate limits.

### Scheduled Display with Cron

Display transit arrivals on a recurring schedule using crontab. The included `muni.sh` script sources your API key from `~/.transit` and runs the display:

```bash
#!/bin/bash
. ~/.transit && /usr/bin/python3 ./muni/muni.py
```

**Setup:**

1. Create `~/.transit` with your API key:
```bash
export SF_TRANSIT_API_KEY="your-api-key-here"
```

2. Make the script executable:
```bash
chmod +x muni.sh
```

3. Add to crontab to run every 5 minutes between 10 AM and 9 PM:
```bash
crontab -e

# Add this line:
*/5 10-21 * * * /home/pi/muni.sh
```

This displays transit arrivals every 5 minutes during waking hours, updating your LED display with the latest information.

### Helper Scripts

Find nearby stops manually:

```bash
cd muni

# List nearby stops (requires coordinates.json with location)
./get-nearby-stops.sh "Sequoia Fabrica"

# Display stop information
./display-nearby-stops.py
```

## Example Systemd Service

Run scripts as services on a Raspberry Pi:

### Music Display Service

Create `/etc/systemd/system/music-display.service`:

```ini
[Unit]
Description=Volumio Music Display
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ft-scripts/music
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 /home/pi/ft-scripts/music/volumio_websocket.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Transit Display Service

Create `/etc/systemd/system/transit-display.service`:

```ini
[Unit]
Description=MUNI Transit Display
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ft-scripts/muni
Environment="PYTHONUNBUFFERED=1"
Environment="SF_TRANSIT_API_KEY=your-api-key"
ExecStart=/usr/bin/python3 /home/pi/ft-scripts/muni/muni.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable music-display.service
sudo systemctl start music-display.service
```

## Troubleshooting

### Music display not updating
- Check Volumio is running and accessible: `curl http://frontspeakers.local/api/v1/getState`
- Verify network connectivity
- Check `ft.json` configuration

### Transit display not showing arrivals
- Verify `SF_TRANSIT_API_KEY` environment variable is set
- Check internet connectivity
- Verify location name exists in `coordinates.json`
- Check API rate limit (60 requests/hour)
- Review cache in `~/.cache/muni/`

### Text not appearing on display
- Verify `ft.json` host address is correct
- Check FlaschenTaschen server is running
- Verify network connectivity to display server
- Test manually: `/home/pi/bin/send-text -h192.168.1.100 "test"`

### Cron job not running
- Verify script is executable: `chmod +x muni.sh`
- Check crontab syntax: `crontab -l` to list jobs
- Verify `~/.transit` file exists and contains API key
- Check cron logs: `grep CRON /var/log/syslog` (on some systems)
- Test script manually from cron context: `env -i HOME=$HOME /bin/bash -c 'muni.sh'`

## License

MIT License - see [LICENSE](LICENSE) file for details.
