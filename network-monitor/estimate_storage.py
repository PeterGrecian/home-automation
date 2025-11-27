#!/usr/bin/env python3
"""
Estimate how long it will take to accumulate a given amount of data
"""

import os
from datetime import datetime, timedelta

def get_directory_size(path):
    """Calculate total size of all files in directory"""
    total = 0
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        if os.path.isfile(filepath):
            total += os.path.getsize(filepath)
    return total

def get_time_range(devices_dir):
    """Get earliest and latest timestamps from all device files"""
    earliest = None
    latest = None

    for filename in os.listdir(devices_dir):
        filepath = os.path.join(devices_dir, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r') as f:
                    lines = [line.strip() for line in f if line.strip()]

                    if lines:
                        # First line
                        first_timestamp = lines[0].split(',')[0]
                        first_dt = datetime.fromisoformat(first_timestamp)

                        # Last line
                        last_timestamp = lines[-1].split(',')[0]
                        last_dt = datetime.fromisoformat(last_timestamp)

                        if earliest is None or first_dt < earliest:
                            earliest = first_dt
                        if latest is None or last_dt > latest:
                            latest = last_dt
            except:
                continue

    return earliest, latest

def format_time(hours):
    """Format hours into human-readable time"""
    if hours < 24:
        return f"{hours:.1f} hours"

    days = hours / 24
    if days < 30:
        return f"{days:.1f} days ({hours:.0f} hours)"

    months = days / 30
    if months < 12:
        return f"{months:.1f} months ({days:.0f} days)"

    years = days / 365
    return f"{years:.1f} years ({days:.0f} days)"

def main():
    devices_dir = 'devices'

    if not os.path.exists(devices_dir):
        print(f"Error: {devices_dir} directory not found")
        return

    # Get current size
    current_bytes = get_directory_size(devices_dir)
    current_kb = current_bytes / 1024
    current_mb = current_kb / 1024

    # Get time range
    earliest, latest = get_time_range(devices_dir)

    if not earliest or not latest:
        print("Error: Could not determine time range")
        return

    duration = latest - earliest
    hours = duration.total_seconds() / 3600

    # Calculate rate
    bytes_per_hour = current_bytes / hours if hours > 0 else 0
    kb_per_hour = bytes_per_hour / 1024
    mb_per_hour = kb_per_hour / 1024

    print("Current Data Statistics:")
    print(f"  Directory size: {current_bytes:,} bytes ({current_kb:.1f} KB, {current_mb:.2f} MB)")
    print(f"  Monitoring started: {earliest}")
    print(f"  Latest data: {latest}")
    print(f"  Duration: {format_time(hours)}")
    print(f"  Data rate: {kb_per_hour:.2f} KB/hour ({mb_per_hour:.4f} MB/hour)")
    print()

    # Estimate for various targets
    targets_mb = [1, 5, 10, 50, 100, 1000]

    print("Time to reach various storage sizes:")
    print(f"{'Target':<15} {'Hours':<12} {'Days':<12} {'Time from now'}")
    print("=" * 70)

    for target_mb in targets_mb:
        target_bytes = target_mb * 1024 * 1024

        if target_bytes <= current_bytes:
            print(f"{target_mb} MB{'':<10} Already reached!")
        else:
            remaining_bytes = target_bytes - current_bytes
            hours_remaining = remaining_bytes / bytes_per_hour if bytes_per_hour > 0 else float('inf')
            days_remaining = hours_remaining / 24

            eta = latest + timedelta(hours=hours_remaining)

            print(f"{target_mb} MB{'':<10} {hours_remaining:<12.1f} {days_remaining:<12.1f} {eta.strftime('%Y-%m-%d %H:%M')}")

    print()

    # Line count info
    total_lines = 0
    for filename in os.listdir(devices_dir):
        filepath = os.path.join(devices_dir, filename)
        if os.path.isfile(filepath):
            with open(filepath, 'r') as f:
                total_lines += sum(1 for line in f if line.strip())

    avg_bytes_per_line = current_bytes / total_lines if total_lines > 0 else 0
    lines_per_hour = total_lines / hours if hours > 0 else 0

    print("Line Statistics:")
    print(f"  Total lines: {total_lines:,}")
    print(f"  Average bytes per line: {avg_bytes_per_line:.1f}")
    print(f"  Lines written per hour: {lines_per_hour:.1f}")
    print(f"  Lines for 10MB: {(10 * 1024 * 1024 / avg_bytes_per_line):,.0f} lines")

if __name__ == '__main__':
    main()
