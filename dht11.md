# DHT11 Temperature and Humidity Sensor

Documentation for reading DHT11 sensor data on Raspberry Pi via GPIO.

## Overview

The `dht11_reader.py` program continuously reads temperature and humidity data from a DHT11 sensor connected to GPIO pin 3 on a Raspberry Pi. The DHT11 is an inexpensive digital temperature and humidity sensor commonly used in home automation projects.

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- DHT11 temperature/humidity sensor module
- Jumper wires (3 required: power, ground, data)
- Optional: 10kΩ pull-up resistor (most DHT11 modules have this built-in)

## DHT11 Specifications

- **Temperature Range:** 0-50°C (±2°C accuracy)
- **Humidity Range:** 20-90% RH (±5% accuracy)
- **Sampling Rate:** Maximum once every 2 seconds
- **Operating Voltage:** 3.3V - 5V
- **Output:** Digital signal via single-wire protocol

## Wiring Diagram

Connect the DHT11 sensor to your Raspberry Pi:

```
DHT11 Sensor    Raspberry Pi
------------    ------------
VCC (+)      -> Pin 1 (3.3V) or Pin 2 (5V)
DATA (OUT)   -> Pin 5 (GPIO 3 / SCL)
GND (-)      -> Pin 6 (Ground) or any GND pin
```

**GPIO Pin Reference:**
- Physical Pin 5 = GPIO 3 = BCM 3 = `board.D3` in code
- Some DHT11 modules have 4 pins; leave NC (not connected) unconnected

## Installation

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-pip libgpiod3
```

### 2. Install Python Library

```bash
pip3 install adafruit-circuitpython-dht
```

### 3. Verify Installation

```bash
python3 -c "import board, adafruit_dht; print('DHT library installed successfully')"
```

## Usage

### Basic Usage

Run the sensor reader:

```bash
python3 dht11_reader.py
```

**Expected Output:**
```
DHT11 Sensor Reader
Reading from GPIO pin 3 (board.D3)
Press Ctrl+C to exit

Temperature: 23.0°C / 73.4°F  |  Humidity: 45%
Temperature: 23.0°C / 73.4°F  |  Humidity: 46%
Temperature: 23.5°C / 74.3°F  |  Humidity: 46%
...
```

### Run as Background Service

To run continuously on boot, create a systemd service:

```bash
# Create service file
sudo nano /etc/systemd/system/dht11-monitor.service
```

Add the following content:

```ini
[Unit]
Description=DHT11 Temperature and Humidity Monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/home-automation
ExecStart=/usr/bin/python3 /home/pi/home-automation/dht11_reader.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable dht11-monitor.service
sudo systemctl start dht11-monitor.service
sudo systemctl status dht11-monitor.service
```

View logs:

```bash
journalctl -u dht11-monitor -f
```

## Troubleshooting

### Common Issues

**1. "Failed to read sensor, retrying..."**
- **Cause:** DHT11 sensors are timing-sensitive and occasionally fail to read
- **Solution:** This is normal behavior; the program will automatically retry
- **Action:** If failures persist, check wiring connections

**2. "RuntimeError: Timed out waiting for PulseIn message"**
- **Cause:** Loose connections or incorrect GPIO pin
- **Solution:**
  - Verify wiring connections are secure
  - Confirm using GPIO 3 (physical pin 5)
  - Try using a different GPIO pin and update code if needed

**3. "ModuleNotFoundError: No module named 'adafruit_dht'"**
- **Cause:** Python library not installed
- **Solution:** Run `pip3 install adafruit-circuitpython-dht`

**4. "PermissionError: [Errno 13] Permission denied"**
- **Cause:** Insufficient permissions to access GPIO
- **Solution:** Add user to `gpio` group: `sudo usermod -a -G gpio $USER` then logout/login

**5. Readings seem incorrect or stuck**
- **Cause:** Sensor malfunction or poor power supply
- **Solution:**
  - Power cycle the Raspberry Pi
  - Try using 5V instead of 3.3V (or vice versa)
  - Replace the sensor (DHT11 sensors are inexpensive)

## Technical Details

### Reading Interval

The DHT11 sensor has a minimum 2-second interval between readings. The program enforces this with `time.sleep(2.0)` to prevent sensor errors.

### Error Handling

- **RuntimeError:** Caught and logged when sensor timing fails (common with DHT11)
- **KeyboardInterrupt:** Clean shutdown on Ctrl+C
- **Finally block:** Ensures proper cleanup of GPIO resources via `dht_device.exit()`

### Code Modification

To change the GPIO pin, edit line 11 in `dht11_reader.py`:

```python
# Current (GPIO 3):
dht_device = adafruit_dht.DHT11(board.D3)

# Change to GPIO 4:
dht_device = adafruit_dht.DHT11(board.D4)

# Change to GPIO 17:
dht_device = adafruit_dht.DHT11(board.D17)
```

**GPIO Pin Reference:**
- `board.D3` = GPIO 3 = Physical Pin 5
- `board.D4` = GPIO 4 = Physical Pin 7
- `board.D17` = GPIO 17 = Physical Pin 11
- See full pinout: https://pinout.xyz

## Integration with Home Automation

### Save to File

Modify the main loop to log data:

```python
with open('temperature_log.csv', 'a') as f:
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    f.write(f"{timestamp},{temperature_c},{humidity}\n")
```

### HTTP API Endpoint

Send data to a home automation server:

```python
import requests

if temperature_c is not None and humidity is not None:
    requests.post('http://homeassistant.local/api/sensor', json={
        'temperature': temperature_c,
        'humidity': humidity
    })
```

### Trigger Actions

Example: Turn on fan if temperature exceeds threshold:

```python
if temperature_c is not None and temperature_c > 28:
    print("Temperature high! Triggering cooling system...")
    # Add your automation logic here
```

## DHT22 Upgrade

For better accuracy, consider upgrading to DHT22 (AM2302):
- Temperature: -40 to 80°C (±0.5°C accuracy)
- Humidity: 0-100% RH (±2% accuracy)
- Drop-in replacement: change one line in code:

```python
# Replace this:
dht_device = adafruit_dht.DHT11(board.D3)

# With this:
dht_device = adafruit_dht.DHT22(board.D3)
```

## References

- Adafruit DHT Library: https://github.com/adafruit/Adafruit_CircuitPython_DHT
- DHT11 Datasheet: https://www.mouser.com/datasheet/2/758/DHT11-Technical-Data-Sheet-Translated-Version-1143054.pdf
- Raspberry Pi GPIO Pinout: https://pinout.xyz
- CircuitPython Board Module: https://docs.circuitpython.org/en/latest/shared-bindings/board/

## License

Part of the home-automation project.
Repository: https://github.com/PeterGrecian/home-automation
