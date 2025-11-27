#!/usr/bin/env python3
"""
Basic tests for network monitor
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

# Import the module to test
import monitor


def test_imports():
    """Test that all required modules can be imported"""
    assert hasattr(monitor, 'NetworkMonitor')
    assert hasattr(monitor, 'DeviceTracker')
    assert hasattr(monitor, 'DevicePinger')
    assert hasattr(monitor, 'NetworkScanner')
    assert hasattr(monitor, 'MacVendorLookup')


def test_config_loading():
    """Test that config file can be loaded"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "subnet": "192.168.1.0/24",
            "interface": "eth0",
            "discovery_interval_seconds": 30,
            "polling_interval_seconds": 3,
            "ping_timeout_seconds": 2,
            "ping_count": 3,
            "parallel_ping_workers": 10,
            "scanner": "arp-scan",
            "prepopulate_arp": True,
            "devices_dir": "test_devices",
            "log_file": "test.log",
            "log_level": "INFO",
            "common_vendors": {}
        }
        json.dump(config, f)
        config_path = f.name

    try:
        # Test NetworkMonitor initialization with custom config
        nm = monitor.NetworkMonitor(config_path=config_path)
        assert nm.config['subnet'] == "192.168.1.0/24"
        assert nm.config['parallel_ping_workers'] == 10
        assert nm.config['ping_count'] == 3
    finally:
        os.unlink(config_path)
        # Clean up test devices directory if created
        if os.path.exists("test_devices"):
            import shutil
            shutil.rmtree("test_devices")


def test_device_pinger_initialization():
    """Test DevicePinger with different configurations"""
    # Default values
    pinger1 = monitor.DevicePinger()
    assert pinger1.timeout_seconds == 2
    assert pinger1.ping_count == 1

    # Custom values
    pinger2 = monitor.DevicePinger(timeout_seconds=5, ping_count=3)
    assert pinger2.timeout_seconds == 5
    assert pinger2.ping_count == 3


def test_device_tracker_directory_creation():
    """Test that DeviceTracker creates directory if missing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        devices_dir = os.path.join(tmpdir, 'test_devices')

        # Directory shouldn't exist yet
        assert not os.path.exists(devices_dir)

        # Create tracker - should create directory
        tracker = monitor.DeviceTracker(devices_dir=devices_dir)

        # Directory should now exist
        assert os.path.exists(devices_dir)
        assert os.path.isdir(devices_dir)


def test_device_tracker_safe_filename():
    """Test that _get_filename creates safe filenames"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = monitor.DeviceTracker(devices_dir=tmpdir)

        # Test normal name
        assert tracker._get_filename("Device-1") == "Device-1"

        # Test name with unsafe characters
        assert tracker._get_filename("Device/Name*Test") == "DeviceNameTest"

        # Test name with leading hyphens (should be stripped)
        assert tracker._get_filename("--Device") == "Device"

        # Test empty after sanitization
        assert tracker._get_filename("---") == "unknown-device"


def test_mac_vendor_lookup():
    """Test MAC vendor lookup cache"""
    lookup = monitor.MacVendorLookup()

    # Test that cache is initialized
    assert isinstance(lookup.cache, dict)
    assert isinstance(lookup.hostname_counts, dict)


def test_network_monitor_initialization():
    """Test NetworkMonitor initializes all components"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "subnet": "192.168.1.0/24",
            "interface": "eth0",
            "discovery_interval_seconds": 30,
            "polling_interval_seconds": 3,
            "ping_timeout_seconds": 2,
            "ping_count": 3,
            "parallel_ping_workers": 5,
            "scanner": "arp-scan",
            "prepopulate_arp": True,
            "devices_dir": "test_devices_nm",
            "log_file": "test.log",
            "log_level": "INFO",
            "common_vendors": {}
        }
        json.dump(config, f)
        config_path = f.name

    try:
        nm = monitor.NetworkMonitor(config_path=config_path)

        # Check all components initialized
        assert nm.tracker is not None
        assert nm.scanner is not None
        assert nm.pinger is not None
        assert nm.running == False

        # Check pinger got config values
        assert nm.pinger.timeout_seconds == 2
        assert nm.pinger.ping_count == 3

    finally:
        os.unlink(config_path)
        if os.path.exists("test_devices_nm"):
            import shutil
            shutil.rmtree("test_devices_nm")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
