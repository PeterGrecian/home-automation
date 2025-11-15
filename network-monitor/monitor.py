#!/usr/bin/env python3
"""
Network Device Monitor
Tracks device online/offline status with auto-discovery
"""

import sqlite3
import threading
import time
import subprocess
import json
import csv
import requests
from datetime import datetime
from typing import Dict, Set, Optional
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
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
            '1C6499': 'Unknown-IoT',
            '0050B6': 'Unknown-Device',
            'AC6784': 'Unknown-Device',
            'E4F042': 'Unknown-Device',
        }
        
        vendor = common_vendors.get(oui, 'Unknown')
        self.cache[mac] = vendor
        return vendor
    
    def generate_hostname(self, mac: str, ip: str, dns_hostname: str = None) -> str:
        """Generate a friendly hostname from MAC vendor"""
        if dns_hostname and dns_hostname != ip:
            return dns_hostname
        
        vendor = self.get_vendor(mac)
        last4 = mac.replace(':', '')[-4:].upper()
        
        # Clean up vendor name
        vendor_clean = vendor.replace(',', '').replace(' ', '-')
        base_hostname = f"{vendor_clean}-{last4}"
        
        # Handle duplicates
        if base_hostname in self.hostname_counts:
            self.hostname_counts[base_hostname] += 1
            return f"{base_hostname}-{self.hostname_counts[base_hostname]}"
        else:
            self.hostname_counts[base_hostname] = 1
            return base_hostname


class DeviceDatabase:
    """SQLite database manager for device tracking"""
    
    def __init__(self, db_path='devices.db'):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY,
                ip TEXT,
                hostname TEXT,
                first_seen TEXT,
                last_seen TEXT,
                status TEXT DEFAULT 'unknown'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                mac TEXT,
                ip TEXT,
                hostname TEXT,
                event_type TEXT,
                FOREIGN KEY (mac) REFERENCES devices (mac)
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_or_update_device(self, mac: str, ip: str, hostname: str = None):
        """Add new device or update existing one"""
        max_retries = 3
        should_log_discovery = False
        
        for attempt in range(max_retries):
            try:
                with self.lock:
                    with sqlite3.connect(self.db_path, timeout=30.0, isolation_level='IMMEDIATE') as conn:
                        now = datetime.now().isoformat()
                        cursor = conn.cursor()
                        
                        cursor.execute('SELECT mac, status FROM devices WHERE mac = ?', (mac,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            cursor.execute('''
                                UPDATE devices 
                                SET ip = ?, hostname = ?, last_seen = ?
                                WHERE mac = ?
                            ''', (ip, hostname or existing[0], now, mac))
                        else:
                            cursor.execute('''
                                INSERT INTO devices (mac, ip, hostname, first_seen, last_seen, status)
                                VALUES (?, ?, ?, ?, ?, 'online')
                            ''', (mac, ip, hostname, now, now))
                            should_log_discovery = True
                            logger.info(f"New device discovered: {hostname or ip} ({mac})")
                        
                        conn.commit()
                
                # Log event AFTER connection is closed
                if should_log_discovery:
                    self.log_event(mac, ip, hostname, 'discovered')
                break
            except sqlite3.OperationalError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(0.5)
                else:
                    logger.error(f"Failed to add/update device after {max_retries} attempts: {e}")
    
    def update_device_status(self, mac: str, status: str):
        """Update device online/offline status"""
        max_retries = 3
        should_log_event = False
        event_data = None
        
        for attempt in range(max_retries):
            try:
                with self.lock:
                    with sqlite3.connect(self.db_path, timeout=30.0, isolation_level='IMMEDIATE') as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT status, ip, hostname FROM devices WHERE mac = ?', (mac,))
                        result = cursor.fetchone()
                        
                        if result and result[0] != status:
                            old_status = result[0]
                            ip, hostname = result[1], result[2]
                            
                            cursor.execute('''
                                UPDATE devices SET status = ?, last_seen = ?
                                WHERE mac = ?
                            ''', (status, datetime.now().isoformat(), mac))
                            
                            event_type = 'online' if status == 'online' else 'offline'
                            should_log_event = True
                            event_data = (mac, ip, hostname, event_type)
                            
                            logger.info(f"Device {hostname or ip} ({mac}): {old_status} -> {status}")
                            conn.commit()
                
                # Log event AFTER connection is closed
                if should_log_event and event_data:
                    self.log_event(*event_data)
                break
            except sqlite3.OperationalError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(0.5)
                else:
                    logger.error(f"Failed to update device status after {max_retries} attempts: {e}")
    
    def log_event(self, mac: str, ip: str, hostname: str, event_type: str):
        """Log device event - must be called OUTSIDE of other database transactions"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with self.lock:
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    conn.execute('PRAGMA busy_timeout=30000')
                    conn.execute('''
                        INSERT INTO events (timestamp, mac, ip, hostname, event_type)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (datetime.now().isoformat(), mac, ip, hostname, event_type))
                    conn.commit()
                    conn.close()
                break
            except sqlite3.OperationalError as e:
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                else:
                    logger.error(f"Failed to log event after {max_retries} attempts: {e}")
    
    def get_all_devices(self) -> list:
        """Get all known devices"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.lock:
                    with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT mac, ip, hostname, status FROM devices')
                        return cursor.fetchall()
            except sqlite3.OperationalError as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    logger.error(f"Failed to get devices after {max_retries} attempts: {e}")
                    return []
    
    def export_events_to_csv(self, filename='events_export.csv'):
        """Export all events to CSV for analysis"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, mac, ip, hostname, event_type 
                    FROM events 
                    ORDER BY timestamp
                ''')
                
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Timestamp', 'MAC', 'IP', 'Hostname', 'Event'])
                    writer.writerows(cursor.fetchall())
                
                logger.info(f"Events exported to {filename}")


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
    
    @staticmethod
    def is_online(ip: str) -> bool:
        """Quick ping check"""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1', ip],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False


class NetworkMonitor:
    """Main monitor coordinating discovery and polling threads"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.db = DeviceDatabase()
        self.scanner = NetworkScanner(self.config['subnet'])
        self.pinger = DevicePinger()
        self.running = False
    
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
                    self.db.add_or_update_device(mac, ip, hostname)
                    self.db.update_device_status(mac, 'online')
                
                time.sleep(self.config['discovery_interval_seconds'])
            
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                time.sleep(60)
    
    def polling_thread(self):
        """Thread for fast polling of known devices"""
        logger.info(f"Polling thread started (interval: {self.config['polling_interval_seconds']}s)")
        
        while self.running:
            try:
                devices = self.db.get_all_devices()
                
                for mac, ip, hostname, current_status in devices:
                    is_online = self.pinger.is_online(ip)
                    new_status = 'online' if is_online else 'offline'
                    
                    if new_status != current_status:
                        self.db.update_device_status(mac, new_status)
                
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
    monitor = NetworkMonitor()
    monitor.start()
    

