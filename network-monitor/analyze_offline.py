#!/usr/bin/env python3
"""
Analyze device offline time from network monitor data
Reads device files and calculates total time each device was offline
"""

import os
from datetime import timedelta
from typing import Dict, List, Tuple

def parse_device_file(filepath: str) -> Tuple[str, str, str, float]:
    """
    Parse a device file and calculate total offline time
    Returns: (hostname, ip, mac, total_offline_seconds)
    """
    total_offline = 0.0
    last_ip = ""
    last_mac = ""

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(',')
                if len(parts) >= 5:
                    # timestamp, ip, mac, status, interval_seconds
                    ip = parts[1]
                    mac = parts[2]
                    status = parts[3]
                    interval = float(parts[4])

                    last_ip = ip
                    last_mac = mac

                    # Sum up offline intervals
                    # When status is 'online', the interval shows how long it was offline before
                    if status == 'online':
                        total_offline += interval

    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return (os.path.basename(filepath), "", "", 0.0)

    hostname = os.path.basename(filepath)
    return (hostname, last_ip, last_mac, total_offline)

def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration"""
    td = timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)

def main():
    devices_dir = 'devices'

    if not os.path.exists(devices_dir):
        print(f"Error: {devices_dir} directory not found")
        return

    # Collect device data
    devices: List[Tuple[str, str, str, float]] = []

    for filename in os.listdir(devices_dir):
        filepath = os.path.join(devices_dir, filename)
        if os.path.isfile(filepath):
            device_data = parse_device_file(filepath)
            devices.append(device_data)

    # Sort by offline time (descending)
    devices.sort(key=lambda x: x[3], reverse=True)

    # Print results
    print("Devices ordered by total offline time:\n")
    print(f"{'Hostname':<30} {'IP Address':<15} {'MAC Address':<17} {'Offline Time':<20} {'Raw Seconds':<12}")
    print("=" * 110)

    for hostname, ip, mac, offline_seconds in devices:
        duration_str = format_duration(offline_seconds)
        print(f"{hostname:<30} {ip:<15} {mac:<17} {duration_str:<20} {offline_seconds:<12.1f}")

    # Print summary
    print("\n" + "=" * 110)
    total_devices = len(devices)
    devices_with_downtime = sum(1 for d in devices if d[3] > 0)
    total_offline = sum(d[3] for d in devices)

    print(f"\nSummary:")
    print(f"  Total devices: {total_devices}")
    print(f"  Devices with downtime: {devices_with_downtime}")
    print(f"  Total offline time across all devices: {format_duration(total_offline)}")

if __name__ == '__main__':
    main()
