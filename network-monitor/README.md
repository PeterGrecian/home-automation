# Network Device Monitor

Automated network device monitoring with auto-discovery and reliability tracking.

## Features

- **Auto-discovery**: Scans your network (192.168.4.0/22) to find all devices
- **Multi-threaded**: Separate threads for discovery (slow/comprehensive) and polling (fast/targeted)
- **Event logging**: Tracks every device connection/disconnection with timestamps
- **SQLite database**: Stores device info and historical events
- **CSV export**: Export data for analysis in Excel/Google Sheets
- **Smart plug testing**: Perfect for tracking reliability of IoT devices

## Architecture

```
Main Process
├── Discovery Thread (every 10 minutes)
│   └── Scans entire subnet, finds new devices
└── Polling Thread (every 60 seconds)
    └── Pings known devices, logs status changes
```

## Installation

### 1. Install system dependencies

```bash
# On Raspberry Pi / Debian / Ubuntu
sudo apt-get update
sudo apt-get install -y arp-scan nmap python3 python3-pip
```

### 2. Extract and setup

```bash
# Extract the zip
unzip network-monitor.zip
cd network-monitor

# Make executable
chmod +x monitor.py
```

### 3. Configure (optional)

Edit `config.json` to adjust:
- `discovery_interval_seconds`: How often to scan network (default: 600 = 10 min)
- `polling_interval_seconds`: How often to ping known devices (default: 60 = 1 min)

## Usage

### Run manually

```bash
sudo python3 monitor.py
```

Note: Requires `sudo` for arp-scan to work properly.

### Run as a service (auto-start on boot)

```bash
# Copy service file
sudo cp network-monitor.service /etc/systemd/system/

# Edit the service file to set correct paths
sudo nano /etc/systemd/system/network-monitor.service
# Change WorkingDirectory and ExecStart paths to match your installation

# Enable and start
sudo systemctl enable network-monitor.service
sudo systemctl start network-monitor.service

# Check status
sudo systemctl status network-monitor.service

# View logs
sudo journalctl -u network-monitor.service -f
```

## Monitoring and Analysis

### View real-time logs

```bash
tail -f monitor.log
```

### Export data for analysis

```python
# In Python shell
from monitor import DeviceDatabase

db = DeviceDatabase()
db.export_events_to_csv('my_analysis.csv')
```

Then open `my_analysis.csv` in Excel/Google Sheets to analyze:
- Which devices go offline most frequently
- Dropout patterns by time of day
- Compare reliability between brands
- Calculate uptime percentages

### Query database directly

```bash
sqlite3 devices.db

# See all devices
SELECT * FROM devices;

# See recent events
SELECT * FROM events ORDER BY timestamp DESC LIMIT 20;

# Count events per device
SELECT hostname, event_type, COUNT(*) 
FROM events 
GROUP BY hostname, event_type;

# Calculate offline events per device
SELECT hostname, COUNT(*) as dropout_count
FROM events 
WHERE event_type = 'offline'
GROUP BY hostname
ORDER BY dropout_count DESC;
```

## Files Generated

- `devices.db`: SQLite database with device info and events
- `monitor.log`: Text log file with timestamped events
- `events_export.csv`: Exported event data (when you run export)

## Troubleshooting

### "arp-scan: command not found"

```bash
sudo apt-get install arp-scan
```

### "Permission denied" errors

Run with `sudo` - required for network scanning.

### Devices not being detected

- Check your subnet is correct in `config.json`
- Ensure Pi is connected to the network (eth0 or wlan0)
- Some devices may not respond to ARP or ping when sleeping

### Too many devices being scanned

Your network is large (192.168.4.0/22 = ~1024 IPs). Discovery takes longer but polling is fast. Consider increasing `discovery_interval_seconds` to 900 (15 min) or 1200 (20 min).

### "Database is locked" errors

The updated version includes:
- WAL mode for concurrent access
- Automatic retry logic with exponential backoff
- 30-second timeout for all operations
- Thread-safe locking mechanisms

If you still see this, make sure only one instance is running.

## Customization

### Change network interface

Edit `monitor.py`, find the arp-scan line:
```python
['sudo', 'arp-scan', '--interface=wlan0', self.subnet],  # Change eth0 to wlan0
```

### Ignore certain devices

You can filter them post-export or modify the code to skip certain MAC ranges.

### Add notifications

Extend the `log_event` method to send emails, webhook calls, etc.

## Performance

- **Discovery**: Takes 30-120 seconds depending on network size
- **Polling**: Takes 1-5 seconds for typical home networks
- **Resource usage**: Minimal - ~20MB RAM, negligible CPU between scans
- **Database size**: Very small - months of data < 10MB

## Privacy Note

This tool tracks all devices on your local network. The data stays on your Pi and is not sent anywhere. Be mindful of others' privacy if monitoring a shared network.

## License

MIT License - Free to use and modify

## Support

This is a standalone tool. For issues:
1. Check the logs: `tail -f monitor.log`
2. Verify dependencies are installed
3. Ensure correct permissions (sudo)
4. Check your subnet configuration

Created for monitoring smart home device reliability.