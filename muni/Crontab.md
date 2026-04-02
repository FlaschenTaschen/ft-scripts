# Cron Setup for Transit Scripts

Cron jobs run in a minimal environment without shell configuration. To make environment variables available to both your shell and cron jobs, use a centralized `~/.transit` file.

## Setup

### 1. Create ~/.transit

Create a file in your home directory with all transit-related environment variables:

```bash
cat > ~/.transit << 'EOF'
export SF_TRANSIT_API_KEY="your_actual_api_key_here"
export MUNI_AGENCY="SF"
EOF
```

### 2. Load in ~/.profile

Add this to your `~/.profile` so variables load on shell login:

```bash
if [ -f ~/.transit ]; then
    . ~/.transit
fi
```

Test it works:
```bash
source ~/.profile
echo $SF_TRANSIT_API_KEY
```

### 3. Create a wrapper script (recommended)

Create `~/run-muni.sh` to handle environment setup:

```bash
#!/bin/bash
. ~/.transit
python3 /home/pi/path/to/muni.py
```

Make it executable:
```bash
chmod +x ~/run-muni.sh
```

### 4. Add cron jobs

Edit your crontab:
```bash
crontab -e
```

**Option A: Using wrapper script (cleaner)**
```bash
# Display bus arrivals every 5 minutes
*/5 * * * * /home/pi/run-muni.sh
```

**Option B: Inline sourcing**
```bash
# Display bus arrivals every 5 minutes
*/5 * * * * bash -c '. ~/.transit && python3 /home/pi/muni.py'
```

## Example Crontabs

Display transit info at specific times:

```bash
# Every 5 minutes
*/5 * * * * /home/pi/run-muni.sh

# Every hour on the hour
0 * * * * /home/pi/run-muni.sh

# Weekdays at 8am
0 8 * * 1-5 /home/pi/run-muni.sh

# Every 10 minutes during business hours (9am-5pm)
*/10 9-17 * * * /home/pi/run-muni.sh
```

## Troubleshooting

**Variables not available:**
- Verify `~/.transit` exists and is readable: `cat ~/.transit`
- Check `~/.profile` was sourced: `echo $SF_TRANSIT_API_KEY`

**Script fails in cron but works in shell:**
- Use absolute paths (e.g., `/home/pi/path/to/script.sh`, not `./script.sh`)
- Test the wrapper: `/home/pi/run-muni.sh` from shell
- Check cron logs: `grep CRON /var/log/syslog`

**Permission denied:**
- Make wrapper script executable: `chmod +x ~/run-muni.sh`
- Check cron job output: `crontab -l`

## Viewing Cron Output

Add email notifications to crontab to receive job output:

```bash
MAILTO=your_email@example.com

*/5 * * * * /home/pi/run-muni.sh
```

Or redirect to a log file:

```bash
*/5 * * * * /home/pi/run-muni.sh >> /tmp/muni.log 2>&1
```

View log:
```bash
tail -f /tmp/muni.log
```