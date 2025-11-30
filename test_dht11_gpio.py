#!/usr/bin/env python3
"""
Test DHT11 GPIO connection
Checks if pigpio can communicate with the DHT11 sensor
"""

import time
import pigpio

DHT11_PIN = 3

print("DHT11 GPIO Connection Test")
print("=" * 40)
print(f"Testing GPIO pin: {DHT11_PIN}")
print()

# Connect to pigpio daemon
pi = pigpio.pi()

if not pi.connected:
    print("ERROR: Could not connect to pigpio daemon")
    print("Start it with: sudo pigpiod")
    exit(1)

print("✓ Connected to pigpio daemon")
print()

# Test basic GPIO operations
print("Testing GPIO pin read/write...")

# Set as output and toggle
pi.set_mode(DHT11_PIN, pigpio.OUTPUT)
pi.write(DHT11_PIN, 1)
time.sleep(0.1)
print(f"  Set pin HIGH, reading: {pi.read(DHT11_PIN)}")

pi.write(DHT11_PIN, 0)
time.sleep(0.1)
print(f"  Set pin LOW, reading: {pi.read(DHT11_PIN)}")

# Set as input with pull-up
pi.set_mode(DHT11_PIN, pigpio.INPUT)
pi.set_pull_up_down(DHT11_PIN, pigpio.PUD_UP)
time.sleep(0.1)
print(f"  Set as INPUT with pull-up, reading: {pi.read(DHT11_PIN)}")

print()
print("If the sensor is connected properly:")
print("  - With pull-up, pin should read HIGH (1)")
print("  - Check your wiring:")
print("    DHT11 VCC  -> Pi Pin 1 (3.3V) or Pin 2 (5V)")
print("    DHT11 DATA -> Pi Pin 5 (GPIO 3)")
print("    DHT11 GND  -> Pi Pin 6 (Ground)")
print()
print("Current pin state:", "HIGH" if pi.read(DHT11_PIN) else "LOW")

pi.stop()
