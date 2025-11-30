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
echo "Step 2a: Creating libgpiod compatibility symlink..."
# Adafruit library expects libgpiod.so.2, but newer systems have libgpiod.so.3
# Create symlink for backward compatibility
SYMLINK_CREATED=false
if [ -f /usr/lib/aarch64-linux-gnu/libgpiod.so.3 ] && [ ! -f /usr/lib/aarch64-linux-gnu/libgpiod.so.2 ]; then
    sudo ln -s /usr/lib/aarch64-linux-gnu/libgpiod.so.3 /usr/lib/aarch64-linux-gnu/libgpiod.so.2
    echo "✓ Created libgpiod.so.2 -> libgpiod.so.3 symlink"
    SYMLINK_CREATED=true
elif [ -f /usr/lib/arm-linux-gnueabihf/libgpiod.so.3 ] && [ ! -f /usr/lib/arm-linux-gnueabihf/libgpiod.so.2 ]; then
    sudo ln -s /usr/lib/arm-linux-gnueabihf/libgpiod.so.3 /usr/lib/arm-linux-gnueabihf/libgpiod.so.2
    echo "✓ Created libgpiod.so.2 -> libgpiod.so.3 symlink"
    SYMLINK_CREATED=true
elif [ -f /usr/lib/aarch64-linux-gnu/libgpiod.so.2 ] || [ -f /usr/lib/arm-linux-gnueabihf/libgpiod.so.2 ]; then
    echo "✓ libgpiod.so.2 already exists"
else
    echo "⚠ Could not find libgpiod library - may cause issues"
fi

# Update dynamic linker cache so libraries are found
echo "Updating library cache..."
sudo ldconfig
echo "✓ Library cache updated"

echo ""
echo "Step 3: Installing Adafruit DHT Python library..."

# Try system package first
if sudo apt-get install -y python3-adafruit-circuitpython-dht 2>/dev/null; then
    echo "✓ Installed from system package"
else
    echo "System package not available, using pip..."
    # Use --break-system-packages for Raspberry Pi (dedicated device)
    # This is safe on a dedicated automation device
    if pip3 install --break-system-packages adafruit-circuitpython-dht 2>/dev/null; then
        echo "✓ Installed via pip with --break-system-packages"
    else
        echo "✗ Failed to install DHT library"
        echo ""
        echo "Manual installation required:"
        echo "  pip3 install --break-system-packages adafruit-circuitpython-dht"
        echo "or create a virtual environment"
        exit 1
    fi
fi

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
