#!/bin/bash
#
# DHT11 Sensor Installation Script (pigpio version)
# Installs pigpio for dht11_reader_pigpio.py on Raspberry Pi
# Compatible with 32-bit and 64-bit Raspberry Pi systems
#

set -e  # Exit on error

echo "========================================="
echo "DHT11 Sensor Installation (pigpio)"
echo "========================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null && ! grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
fi

echo "Step 1: Updating package lists..."
sudo apt-get update

echo ""
echo "Step 2: Installing pigpio and dependencies..."
sudo apt-get install -y pigpio python3-pigpio python3-yaml

echo ""
echo "Step 3: Enabling and starting pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

echo ""
echo "Step 4: Verifying installation..."
if python3 -c "import pigpio" 2>/dev/null; then
    echo "✓ pigpio library installed successfully"
else
    echo "✗ pigpio library verification failed"
    exit 1
fi

if systemctl is-active --quiet pigpiod; then
    echo "✓ pigpio daemon is running"
else
    echo "✗ pigpio daemon is not running"
    echo "Try starting it manually: sudo systemctl start pigpiod"
    exit 1
fi

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "You can now run the DHT11 sensor reader:"
echo "  python3 dht11_reader_pigpio.py"
echo ""
echo "Note: The pigpio daemon (pigpiod) must be running."
echo "It will auto-start on boot."
echo ""
