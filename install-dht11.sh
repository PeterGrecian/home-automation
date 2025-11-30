#!/bin/bash
#
# DHT11 Sensor Installation Script
# Installs all prerequisites for dht11_reader.py on Raspberry Pi
#

set -e  # Exit on error

echo "========================================="
echo "DHT11 Sensor Installation Script"
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
echo "Step 2: Installing system dependencies..."
sudo apt-get install -y python3-pip libgpiod3

echo ""
echo "Step 3: Installing Adafruit DHT Python library..."
pip3 install adafruit-circuitpython-dht

echo ""
echo "Step 4: Verifying installation..."
if python3 -c "import board, adafruit_dht" 2>/dev/null; then
    echo "✓ DHT library installed successfully"
else
    echo "✗ DHT library verification failed"
    exit 1
fi

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "You can now run the DHT11 sensor reader:"
echo "  python3 dht11_reader.py"
echo ""
echo "For documentation, see: dht11.md"
echo ""
