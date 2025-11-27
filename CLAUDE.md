# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a home automation project for managing Google Home devices and network monitoring on a Raspberry Pi. The repository contains:

1. **Network Device Monitor** (`network-monitor/`) - Multi-threaded Python application for tracking device connectivity
2. **Proximity Detection** (`proximity.py`) - Wi-Fi and Bluetooth-based presence detection for automation triggers
3. **Google Home Automations** (YAML files) - Time-based automation scripts for controlling smart home devices

## Running the Applications

### Network Monitor

Run **without sudo** (sudo is already embedded in the code for arp-scan calls):

```bash
# Run manually
python3 network-monitor/monitor.py

# View logs in real-time
tail -f monitor.log

# Run as systemd service (auto-start on boot)
sudo cp network-monitor/network-monitor.service /etc/systemd/system/
sudo systemctl enable network-monitor.service
sudo systemctl start network-monitor.service
sudo systemctl status network-monitor.service
```

**Important:** Do not run with sudo or device files will be owned by root.

### Proximity Detection

```bash
python3 proximity.py
```

Requires configuration of MAC addresses and API endpoints in the file before running.

## Configuration

### Network Monitor Configuration (`network-monitor/config.json`)

Key settings:
- `subnet`: Network range to scan (default: 192.168.4.0/24)
- `interface`: Network interface (eth0 or wlan0)
- `discovery_interval_seconds`: How often to scan entire network (default: 30s)
- `polling_interval_seconds`: How often to ping known devices (default: 3s)
- `ping_count`: Number of ping packets to send per check (default: 3)
- `ping_timeout_seconds`: Maximum time to wait for ping response (default: 3s)

**Ping behavior:** A device is marked **online** if ANY ping packet succeeds, and **offline** only if ALL packets fail. Using `ping_count: 3` reduces false positives from transient packet loss compared to single-ping checks.

### Google Home Automations (YAML files)

YAML files define time-based automations using Google Home's format:
- `evening-lights.yaml`: Sunset/time-based lighting control
- `on-off-test.yaml`: Hourly on/off routines for testing

These are meant to be imported into Google Home at: https://home.google.com/home/1-56d22f65d9f3fcfe14bb11676c8914b07cb922bc77a9d3450e7c1937eb8eb8da/automations/create

## Architecture

### Network Monitor (`network-monitor/monitor.py`)

**Threading Model:**
- Main process coordinates two daemon threads
- **Discovery Thread**: Runs every `discovery_interval_seconds` (default 30s)
  - Pre-populates ARP cache with fping
  - Scans entire subnet using arp-scan (primary) or nmap (fallback)
  - Discovers new devices and updates device registry
- **Polling Thread**: Runs every `polling_interval_seconds` (default 3s)
  - Fast ping check on all known devices
  - Detects and logs state transitions (online ↔ offline)

**File-Based Storage:**
- Uses text files instead of database (changed from earlier SQLite design)
- One file per device in `devices/` directory
- Format: `timestamp,ip,mac,status,interval_seconds`
- Thread-safe with lock-based synchronization
- **Automatic creation**: Both the `devices/` directory and individual device files are created automatically if missing
- **Easy archiving**: Can move/delete entire `devices/` directory to archive old data - will be recreated on next run
- **Human-readable**: CSV format allows direct inspection with `cat`, `grep`, or any text tools
- **Resilient**: If one device file is corrupted, others are unaffected

**Key Classes:**
- `NetworkMonitor`: Main coordinator, manages threads
- `NetworkScanner`: Handles device discovery via arp-scan/nmap
- `DeviceTracker`: Thread-safe file-based device state management
  - `_get_filename()` strips leading hyphens/underscores to prevent bash command issues
- `DevicePinger`: Configurable ping-based connectivity checks (timeout and count from config.json)
- `MacVendorLookup`: MAC OUI → manufacturer mapping with API fallback

**Network Interface:**
Currently hardcoded to `eth0` in monitor.py:225. Change to `wlan0` if using Wi-Fi.

### Proximity Detection (`proximity.py`)

Uses scapy for Wi-Fi ARP scanning and PyBluez for Bluetooth discovery to detect phone presence and trigger automation API calls.

## System Dependencies

```bash
# Required for network monitor
sudo apt-get install -y arp-scan nmap python3 python3-pip

# Optional for faster ARP cache population
sudo apt-get install -y fping

# Required for proximity detection
sudo apt-get install -y python3-scapy python3-bluez
```

## Python Dependencies

The network monitor uses only standard library modules (no pip requirements).

Proximity detection requires:
```bash
pip install scapy pybluez requests
```

## Development Notes

- All Python scripts use Python 3
- Network monitor runs as regular user (sudo is embedded in subprocess calls for arp-scan)
- Logging is configured to both file and stdout
- The project is designed to run on Raspberry Pi (ARM Linux)
- Git repo tracked at: https://github.com/users/PeterGrecian/projects/12/views/1

## Data Analysis

Network monitor device files can be analyzed directly (CSV format) or queried programmatically:

```python
# Example: Read device history
import os
for filename in os.listdir('network-monitor/devices'):
    with open(f'network-monitor/devices/{filename}', 'r') as f:
        print(f"=== {filename} ===")
        for line in f:
            print(line.strip())
```

Each line shows: timestamp, IP, MAC, status (online/offline), and seconds since last state change.
