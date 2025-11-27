#!/usr/bin/env python3
"""
Analyze state change rate over time for network monitor devices
Detects periods of instability (frequent state changes) and trend changes
"""

import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple
import statistics

def parse_device_files(devices_dir: str) -> List[Tuple[datetime, str, str]]:
    """
    Parse all device files and extract state changes
    Returns: [(timestamp, mac, status), ...]
    """
    state_changes = []

    for filename in os.listdir(devices_dir):
        filepath = os.path.join(devices_dir, filename)
        if not os.path.isfile(filepath):
            continue

        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split(',')
                    if len(parts) >= 4:
                        timestamp = datetime.fromisoformat(parts[0])
                        mac = parts[2]
                        status = parts[3]
                        state_changes.append((timestamp, mac, status))
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    # Sort by timestamp
    state_changes.sort(key=lambda x: x[0])
    return state_changes

def calculate_rate_by_window(state_changes: List[Tuple[datetime, str, str]],
                             window_minutes: int = 60) -> List[Tuple[datetime, float, int]]:
    """
    Calculate state change rate in sliding time windows
    Returns: [(window_start, changes_per_hour, change_count), ...]
    """
    if not state_changes:
        return []

    window_delta = timedelta(minutes=window_minutes)
    rates = []

    # Start from first state change
    start_time = state_changes[0][0]
    end_time = state_changes[-1][0]

    # Slide window by 1/4 of window size for overlap
    step_delta = timedelta(minutes=window_minutes // 4)

    current = start_time
    while current <= end_time:
        window_end = current + window_delta

        # Count changes in this window
        changes_in_window = sum(1 for ts, _, _ in state_changes
                               if current <= ts < window_end)

        # Calculate rate as changes per hour
        actual_hours = window_minutes / 60.0
        rate = changes_in_window / actual_hours if actual_hours > 0 else 0

        rates.append((current, rate, changes_in_window))
        current += step_delta

    return rates

def detect_anomalies(rates: List[Tuple[datetime, float, int]],
                     threshold_stdev: float = 2.0) -> List[Tuple[datetime, float, str]]:
    """
    Detect periods where state change rate is anomalous
    Returns: [(timestamp, rate, reason), ...]
    """
    if len(rates) < 3:
        return []

    rate_values = [r[1] for r in rates]
    mean_rate = statistics.mean(rate_values)
    stdev_rate = statistics.stdev(rate_values) if len(rate_values) > 1 else 0

    anomalies = []
    for timestamp, rate, count in rates:
        if stdev_rate > 0:
            z_score = (rate - mean_rate) / stdev_rate

            if abs(z_score) > threshold_stdev:
                reason = f"High instability" if z_score > 0 else f"Unusually stable"
                anomalies.append((timestamp, rate, reason))

    return anomalies

def detect_trends(rates: List[Tuple[datetime, float, int]],
                 min_samples: int = 5) -> Dict[str, any]:
    """
    Detect if state change rate is trending up or down
    Returns: trend information
    """
    if len(rates) < min_samples:
        return {"trend": "insufficient_data"}

    # Split into first half and second half
    midpoint = len(rates) // 2
    first_half = [r[1] for r in rates[:midpoint]]
    second_half = [r[1] for r in rates[midpoint:]]

    mean_first = statistics.mean(first_half)
    mean_second = statistics.mean(second_half)

    percent_change = ((mean_second - mean_first) / mean_first * 100) if mean_first > 0 else 0

    trend = {
        "mean_rate_first_half": mean_first,
        "mean_rate_second_half": mean_second,
        "percent_change": percent_change,
        "trend": "increasing" if percent_change > 10 else "decreasing" if percent_change < -10 else "stable"
    }

    return trend

def analyze_per_device(state_changes: List[Tuple[datetime, str, str]]) -> Dict[str, Dict]:
    """
    Analyze state change patterns per device
    Returns: {mac: {stats}, ...}
    """
    device_changes = defaultdict(list)

    for timestamp, mac, status in state_changes:
        device_changes[mac].append((timestamp, status))

    device_stats = {}
    for mac, changes in device_changes.items():
        if len(changes) < 2:
            continue

        # Calculate time between state changes
        intervals = []
        for i in range(1, len(changes)):
            interval = (changes[i][0] - changes[i-1][0]).total_seconds()
            intervals.append(interval)

        mean_interval = statistics.mean(intervals) if intervals else 0

        device_stats[mac] = {
            "total_changes": len(changes),
            "mean_interval_seconds": mean_interval,
            "mean_interval_hours": mean_interval / 3600,
            "flapping": mean_interval < 300  # Changes more often than 5 minutes
        }

    return device_stats

def main():
    devices_dir = "devices"

    if not os.path.exists(devices_dir):
        print(f"Error: {devices_dir} directory not found")
        return

    print("=== Network Monitor State Change Rate Analysis ===\n")

    # Parse all state changes
    print("Reading device files...")
    state_changes = parse_device_files(devices_dir)

    if not state_changes:
        print("No state changes found")
        return

    print(f"Found {len(state_changes)} total state changes")
    print(f"Time range: {state_changes[0][0]} to {state_changes[-1][0]}")
    total_duration = (state_changes[-1][0] - state_changes[0][0]).total_seconds() / 3600
    print(f"Duration: {total_duration:.1f} hours\n")

    # Calculate overall rate
    overall_rate = len(state_changes) / total_duration if total_duration > 0 else 0
    print(f"Overall state change rate: {overall_rate:.2f} changes/hour\n")

    # Calculate rate by time window
    print("Calculating state change rate over time (60-minute windows)...")
    rates = calculate_rate_by_window(state_changes, window_minutes=60)

    if rates:
        print(f"\nRate statistics:")
        rate_values = [r[1] for r in rates]
        print(f"  Min rate:  {min(rate_values):.2f} changes/hour")
        print(f"  Max rate:  {max(rate_values):.2f} changes/hour")
        print(f"  Mean rate: {statistics.mean(rate_values):.2f} changes/hour")
        if len(rate_values) > 1:
            print(f"  Std dev:   {statistics.stdev(rate_values):.2f} changes/hour")

    # Detect trend
    print("\n=== Trend Analysis ===")
    trend = detect_trends(rates)
    if trend["trend"] != "insufficient_data":
        print(f"First half average: {trend['mean_rate_first_half']:.2f} changes/hour")
        print(f"Second half average: {trend['mean_rate_second_half']:.2f} changes/hour")
        print(f"Change: {trend['percent_change']:+.1f}%")
        print(f"Trend: {trend['trend'].upper()}")
    else:
        print("Insufficient data for trend analysis")

    # Detect anomalies
    print("\n=== Anomaly Detection ===")
    anomalies = detect_anomalies(rates, threshold_stdev=2.0)
    if anomalies:
        print(f"Found {len(anomalies)} anomalous periods (>2 std dev from mean):\n")
        for timestamp, rate, reason in anomalies[:10]:  # Show top 10
            print(f"  {timestamp.strftime('%Y-%m-%d %H:%M')}: {rate:.2f} changes/hour - {reason}")
        if len(anomalies) > 10:
            print(f"  ... and {len(anomalies) - 10} more")
    else:
        print("No significant anomalies detected")

    # Per-device analysis
    print("\n=== Per-Device Analysis ===")
    device_stats = analyze_per_device(state_changes)

    # Sort by total changes
    sorted_devices = sorted(device_stats.items(),
                          key=lambda x: x[1]['total_changes'],
                          reverse=True)

    print(f"\nTop 10 most unstable devices:\n")
    for mac, stats in sorted_devices[:10]:
        flap_indicator = " [FLAPPING]" if stats['flapping'] else ""
        print(f"  {mac}: {stats['total_changes']} changes, "
              f"avg interval {stats['mean_interval_hours']:.1f}h{flap_indicator}")

    # Show flapping devices
    flapping = [(mac, stats) for mac, stats in device_stats.items() if stats['flapping']]
    if flapping:
        print(f"\n⚠ {len(flapping)} device(s) showing frequent state changes (<5 min intervals)")

    # Show recent rate
    if len(rates) > 0:
        recent_rate = rates[-1][1]
        print(f"\nMost recent rate: {recent_rate:.2f} changes/hour")

if __name__ == "__main__":
    main()
