#!/usr/bin/env python3
"""
DHT11/DHT22 Temperature and Humidity Sensor Reader (Adafruit library)
Supports both DHT11 and DHT22 sensors
Configuration from dht11_config.yaml
"""

import time
import yaml
import os
import board
import adafruit_dht

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'dht11_config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Get GPIO pin dynamically
gpio_pin = config['gpio_pin']
pin = getattr(board, f'D{gpio_pin}')

# Initialize sensor based on type
sensor_type = config.get('sensor_type', 'DHT11').upper()
if sensor_type == 'DHT22':
    dht_device = adafruit_dht.DHT22(pin, use_pulseio=False)
else:
    dht_device = adafruit_dht.DHT11(pin, use_pulseio=False)

def read_sensor():
    """
    Read temperature and humidity from DHT11 sensor.

    Returns:
        tuple: (temperature_c, humidity_percent) or (None, None) on error
    """
    try:
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity
        return temperature_c, humidity
    except RuntimeError as error:
        # DHT11 sensors can be finicky, errors are common
        print(f"Reading error: {error.args[0]}")
        return None, None
    except Exception as error:
        print(f"Unexpected error: {error}")
        dht_device.exit()
        raise


def main():
    """Main loop - continuously read sensor data"""
    print(f"{sensor_type} Sensor Reader (Adafruit library)")
    print(f"Reading from GPIO {gpio_pin}")
    print("Press Ctrl+C to exit\n")

    try:
        while True:
            temperature_c, humidity = read_sensor()

            if temperature_c is not None and humidity is not None:
                temperature_f = temperature_c * (9 / 5) + 32
                if config.get('show_both_units', True):
                    print(f"Temperature: {temperature_c:.1f}°C / {temperature_f:.1f}°F  |  Humidity: {humidity:.1f}%")
                elif config.get('temperature_unit', 'C') == 'F':
                    print(f"Temperature: {temperature_f:.1f}°F  |  Humidity: {humidity:.1f}%")
                else:
                    print(f"Temperature: {temperature_c:.1f}°C  |  Humidity: {humidity:.1f}%")
            else:
                print("Failed to read sensor, retrying...")

            # Sensor requires minimum 2 second interval between reads
            time.sleep(config.get('read_interval', 2))

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        dht_device.exit()


if __name__ == "__main__":
    main()
