#!/usr/bin/env python3
"""
Network Device Monitor
Tracks device online/offline status with auto-discovery
Uses simple text files instead of database
"""

import threading
import time
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, Optional
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Logger will be configured after loading config
logger = logging.getLogger(__name__)


class MacVendorLookup:
    """Look up device manufacturer from MAC address"""
    
    def __init__(self):
        self.cache = {}
        self.hostname_counts = {}
    
    def get_vendor(self, mac: str) -> str:
        """Get vendor name from MAC address OUI"""
        if mac in self.cache:
            return self.cache[mac]
        
        # Extract OUI (first 3 octets)
        oui = mac.replace(':', '').replace('-', '').upper()[:6]
        
        # Try online lookup first
        try:
            import requests
            response = requests.get(
                f'https://api.maclookup.app/v2/macs/{oui}',
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                vendor = data.get('company', 'Unknown')
                self.cache[mac] = vendor
                return vendor
        except:
            pass
        
        # Fallback to common vendors
        common_vendors = {
            '74B6B6': 'Eero',
            '1C6499': 'UnknownIoT',
            '0050B6': 'UnknownDevice',
            'AC6784': 'UnknownDevice',
            'E4F042': 'UnknownDevice',
        }
        
        vendor = common_vendors.get(oui, 'Unknown')
        self.cache[mac] = vendor
        return vendor
    
    def generate_hostname(self, mac: str, ip: str, dns_hostname: str = None) -> str:
        """Generate a friendly hostname from MAC vendor"""
        if dns_hostname and dns_hostname != ip:
            # Clean up DNS hostname
            clean_dns = dns_hostname.replace('.', '-').replace(' ', '-')
            return clean_dns
        
        vendor = self.get_vendor(mac)
        last4 = mac.replace(':', '')[-4:].upper()
        
        # Clean up vendor name for filename
        vendor_clean = vendor.replace(',', '').replace(' ', '').replace('.', '')
        base_hostname = f"{vendor_clean}-{last4}"
        
        # Handle duplicates
        if base_hostname in self.hostname_counts:
            self.hostname_counts[base_hostname] += 1
            return f"{base_hostname}-{self.hostname_counts[base_hostname]}"
        else:
            self.hostname_counts[base_hostname] = 1
            return base_hostname


class DeviceTracker:
    """File-based device tracking"""
    
    def __init__(self, devices_dir='devices'):
        self.devices_dir = devices_dir
        self.lock = threading.Lock()
        self.device_states = {}  # {mac: {'hostname': str, 'ip': str, 'status': str, 'last_change': datetime}}
        
        # Create devices directory if it doesn't exist
        os.makedirs(self.devices_dir, exist_ok=True)
        
        # Load existing device states
        self._load_device_states()
    
    def _load_device_states(self):
        """Load device states from existing files"""
        if not os.path.exists(self.devices_dir):
            return
        
        for filename in os.listdir(self.devices_dir):
            filepath = os.path.join(self.devices_dir, filename)
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            # Parse last line to get current state
                            last_line = lines[-1].strip()
                            if last_line:
                                parts = last_line.split(',')
                                if len(parts) >= 4:
                                    timestamp_str = parts[0]
                                    ip = parts[1]
                                    mac = parts[2]
                                    status = parts[3]
                                    
                                    self.device_states[mac] = {
                                        'hostname': filename,
                                        'ip': ip,
                                        'status': status,
                                        'last_change': datetime.fromisoformat(timestamp_str)
                                    }
                except Exception as e:
                    logger.error(f"Error loading device state from {filename}: {e}")
    
    def _get_filename(self, hostname: str) -> str:
        """Get safe filename for device"""
        # Remove any unsafe characters
        safe_name = ''.join(c for c in hostname if c.isalnum() or c in '-_')
        # Strip leading hyphens/underscores to avoid bash command issues
        safe_name = safe_name.lstrip('-_')
        # Fallback if name is empty after sanitization
        if not safe_name:
            safe_name = 'unknown-device'
        return safe_name
    
    def add_or_update_device(self, mac: str, ip: str, hostname: str):
        """Add new device or update existing one"""
        with self.lock:
            now = datetime.now()
            
            # Check if device exists
            if mac in self.device_states:
                # Update IP if changed
                self.device_states[mac]['ip'] = ip
            else:
                # New device
                self.device_states[mac] = {
                    'hostname': hostname,
                    'ip': ip,
                    'status': 'online',
                    'last_change': now
                }
                
                # Create new file with initial entry
                filename = self._get_filename(hostname)
                filepath = os.path.join(self.devices_dir, filename)
                
                with open(filepath, 'a') as f:
                    f.write(f"{now.isoformat()},{ip},{mac},online,0\n")
                
                logger.info(f"New device discovered: {hostname} ({mac}) at {ip}")
    
    def update_device_status(self, mac: str, new_status: str):
        """Update device online/offline status"""
        with self.lock:
            if mac not in self.device_states:
                return
            
            device = self.device_states[mac]
            old_status = device['status']
            
            # Only log if status actually changed
            if old_status != new_status:
                now = datetime.now()
                last_change = device['last_change']
                interval_seconds = (now - last_change).total_seconds()
                
                # Update state
                device['status'] = new_status
                device['last_change'] = now
                
                # Append to file
                filename = self._get_filename(device['hostname'])
                filepath = os.path.join(self.devices_dir, filename)
                
                with open(filepath, 'a') as f:
                    f.write(f"{now.isoformat()},{device['ip']},{mac},{new_status},{interval_seconds:.1f}\n")
                
                logger.info(f"Device {device['hostname']} ({mac}): {old_status} -> {new_status} (after {interval_seconds:.1f}s)")
    
    def get_all_devices(self) -> list:
        """Get all known devices"""
        with self.lock:
            return [(mac, data['ip'], data['hostname'], data['status']) 
                    for mac, data in self.device_states.items()]


class NetworkScanner:
    """Network discovery using ARP scan"""
    
    def __init__(self, subnet: str):
        self.subnet = subnet
        self.mac_lookup = MacVendorLookup()
    
    def scan(self) -> Dict[str, tuple]:
        """
        Scan network and return dict of {mac: (ip, hostname)}
        Uses arp-scan for fast discovery
        """
        devices = {}
        
        try:
            result = subprocess.run(
                ['sudo', 'arp-scan', '--interface=eth0', self.subnet],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            for line in result.stdout.split('\n'):
                parts = line.split()
                if len(parts) >= 2 and ':' in parts[1]:
                    ip = parts[0]
                    mac = parts[1].lower()
                    
                    dns_hostname = self._get_hostname(ip)
                    hostname = self.mac_lookup.generate_hostname(mac, ip, dns_hostname)
                    devices[mac] = (ip, hostname)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("arp-scan failed, falling back to nmap")
            devices = self._nmap_scan()
        
        return devices
    
    def _nmap_scan(self) -> Dict[str, tuple]:
        """Fallback scan using nmap"""
        devices = {}
        
        try:
            result = subprocess.run(
                ['nmap', '-sn', '-oG', '-', self.subnet],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            for line in result.stdout.split('\n'):
                if 'Host:' in line:
                    parts = line.split()
                    ip = parts[1]
                    
                    mac = self._get_mac(ip)
                    if mac:
                        dns_hostname = self._get_hostname(ip)
                        hostname = self.mac_lookup.generate_hostname(mac, ip, dns_hostname)
                        devices[mac] = (ip, hostname)
        
        except subprocess.TimeoutExpired:
            logger.error("Nmap scan timeout")
        
        return devices
    
    def _get_mac(self, ip: str) -> Optional[str]:
        """Get MAC address from IP using ARP cache"""
        try:
            result = subprocess.run(
                ['arp', '-n', ip],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if ip in line:
                    parts = line.split()
                    if len(parts) >= 3 and ':' in parts[2]:
                        return parts[2].lower()
        except:
            pass
        return None
    
    def _get_hostname(self, ip: str) -> Optional[str]:
        """Try to resolve hostname from IP"""
        try:
            result = subprocess.run(
                ['host', ip],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            for line in result.stdout.split('\n'):
                if 'domain name pointer' in line:
                    hostname = line.split()[-1].rstrip('.')
                    return hostname
        except:
            pass
        return None


class DevicePinger:
    """Fast ping checking for known devices"""

    def __init__(self, timeout_seconds: int = 2, ping_count: int = 1):
        self.timeout_seconds = timeout_seconds
        self.ping_count = ping_count

    def is_online(self, ip: str) -> bool:
        """Quick ping check"""
        try:
            result = subprocess.run(
                ['ping', '-c', str(self.ping_count), '-W', str(self.timeout_seconds), ip],
                capture_output=True,
                timeout=self.timeout_seconds + 1
            )
            return result.returncode == 0
        except:
            return False


class NetworkMonitor:
    """Main monitor coordinating discovery and polling threads"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Setup logging with optional file output
        self._setup_logging()

        self.tracker = DeviceTracker(devices_dir=self.config.get('devices_dir', 'devices'))
        self.scanner = NetworkScanner(self.config['subnet'])
        self.pinger = DevicePinger(
            timeout_seconds=self.config.get('ping_timeout_seconds', 2),
            ping_count=self.config.get('ping_count', 1)
        )
        self.running = False

    def _setup_logging(self):
        """Configure logging based on config (file logging is optional)"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        log_format = '%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'

        handlers = [logging.StreamHandler(sys.stdout)]

        # Only add file handler if log_file is specified
        log_file = self.config.get('log_file')
        if log_file:
            handlers.append(logging.FileHandler(log_file))

        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers,
            force=True  # Override any existing config
        )
    
    def discovery_thread(self):
        """Thread for periodic network discovery"""
        logger.info(f"Discovery thread started (interval: {self.config['discovery_interval_seconds']}s)")
        
        while self.running:
            try:
                # Pre-populate ARP cache to ensure all devices are visible
                logger.info("Pre-populating ARP cache with ping sweep...")
                try:
                    subprocess.run(
                        ['fping', '-g', '-q', '-r', '0', self.config['subnet']],
                        timeout=60,
                        capture_output=True
                    )
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    logger.warning("fping not available, skipping ARP cache pre-population")
                
                logger.info(f"Starting network scan of {self.config['subnet']}")
                devices = self.scanner.scan()
                logger.info(f"Scan complete: found {len(devices)} devices")
                
                for mac, (ip, hostname) in devices.items():
                    self.tracker.add_or_update_device(mac, ip, hostname)
                    self.tracker.update_device_status(mac, 'online')
                
                time.sleep(self.config['discovery_interval_seconds'])
            
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                time.sleep(60)
    
    def _check_device(self, device_info, stagger_delay=0.0):
        """Check a single device (for parallel execution)"""
        # Stagger start time to spread network/CPU load
        if stagger_delay > 0:
            time.sleep(stagger_delay)

        mac, ip, hostname, current_status = device_info
        is_online = self.pinger.is_online(ip)
        new_status = 'online' if is_online else 'offline'
        return (mac, new_status, current_status)

    def polling_thread(self):
        """Thread for fast polling of known devices (parallel with staggered start)"""
        max_workers = self.config.get('parallel_ping_workers', 10)

        logger.info(f"Polling thread started (interval: {self.config['polling_interval_seconds']}s, "
                   f"workers: {max_workers})")

        while self.running:
            try:
                devices = self.tracker.get_all_devices()

                if not devices:
                    time.sleep(self.config['polling_interval_seconds'])
                    continue

                # Calculate stagger delay to spread pings across polling interval
                # stagger = interval / num_devices (in seconds)
                num_devices = len(devices)
                polling_interval = self.config['polling_interval_seconds']
                stagger_delay = polling_interval / num_devices if num_devices > 0 else 0

                stagger_ms = stagger_delay * 1000.0
                logger.debug(f"Polling {num_devices} devices with {stagger_ms:.1f}ms stagger")

                # Ping all devices in parallel with staggered start
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all ping tasks with incremental stagger delays
                    future_to_device = {}
                    for i, device in enumerate(devices):
                        delay = i * stagger_delay
                        future = executor.submit(self._check_device, device, delay)
                        future_to_device[future] = device

                    # Process results as they complete
                    for future in as_completed(future_to_device):
                        try:
                            mac, new_status, current_status = future.result()
                            if new_status != current_status:
                                self.tracker.update_device_status(mac, new_status)
                        except Exception as e:
                            device = future_to_device[future]
                            logger.error(f"Error checking device {device[2]}: {e}")

                time.sleep(self.config['polling_interval_seconds'])

            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(30)
    
    def start(self):
        """Start monitoring"""
        self.running = True
        
        discovery = threading.Thread(
            target=self.discovery_thread,
            name="Discovery",
            daemon=True
        )
        
        polling = threading.Thread(
            target=self.polling_thread,
            name="Polling",
            daemon=True
        )
        
        discovery.start()
        polling.start()
        
        logger.info("Network monitor started")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.running = False
            time.sleep(2)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Network Device Monitor')
    parser.add_argument('--config', default='config.json',
                       help='Path to configuration file (default: config.json)')
    args = parser.parse_args()

    monitor = NetworkMonitor(config_path=args.config)
    monitor.start()
