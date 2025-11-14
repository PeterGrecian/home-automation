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


class DeviceDatabase:
    """SQLite database manager for device tracking"""
    
    def __init__(self, db_path='devices.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
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
    
    def add_or_update_device(self, mac: str, ip: str, hostname: str = None):
        """Add new device or update existing one"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                cursor = conn.cursor()
                
                # Check if device exists
                cursor.execute('SELECT mac, status FROM devices WHERE mac = ?', (mac,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing device
                    cursor.execute('''
                        UPDATE devices 
                        SET ip = ?, hostname = ?, last_seen = ?
                        WHERE mac = ?
                    ''', (ip, hostname or existing[0], now, mac))
                else:
                    # Insert new device
                    cursor.execute('''
                        INSERT INTO devices (mac, ip, hostname, first_seen, last_seen, status)
                        VALUES (?, ?, ?, ?, ?, 'online')
                    ''', (mac, ip, hostname, now, now))
                    self.log_event(mac, ip, hostname, 'discovered')
                    logger.info(f"New device discovered: {hostname or ip} ({mac})")
                
                conn.commit()
    
    def update_device_status(self, mac: str, status: str):
        """Update device online/offline status"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
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
                    self.log_event(mac, ip, hostname, event_type)
                    
                    logger.info(f"Device {hostname or ip} ({mac}): {old_status} -> {status}")
                    conn.commit()
    
    def log_event(self, mac: str, ip: str, hostname: str, event_type: str):
        """Log device event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO events (timestamp, mac, ip, hostname, event_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), mac, ip, hostname, event_type))
            conn.commit()
    
    def get_all_devices(self) -> list:
        """Get all known devices"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT mac, ip, hostname, status FROM devices')
                return cursor.fetchall()
    
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
    
    def scan(self) -> Dict[str, tuple]:
        """
        Scan network and return dict of {mac: (ip, hostname)}
        Uses arp-scan for fast discovery
        """
        devices = {}
        
        try:
            # Try arp-scan first (fastest, requires sudo)
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
                    
                    # Try to get hostname
                    hostname = self._get_hostname(ip)
                    devices[mac] = (ip, hostname)
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to nmap if arp-scan not available
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
                    
                    # Get MAC from arp cache
                    mac = self._get_mac(ip)
                    if mac:
                        hostname = self._get_hostname(ip)
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