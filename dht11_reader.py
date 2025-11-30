#!/usr/bin/env python3
"""
DHT11 Temperature and Humidity Sensor Reader
Reads DHT11 sensor data from GPIO pin 3 on Raspberry Pi
"""

import time
import board
import adafruit_dht

# Initialize DHT11 sensor on GPIO pin 3 (board.D3)
dht_device = adafruit_dht.DHT11(board.D3)

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
    """Main loop - continuously read sensor data every 2 seconds"""
    print("DHT11 Sensor Reader")
    print("Reading from GPIO pin 3 (board.D3)")
    print("Press Ctrl+C to exit\n")

    try:
        while True:
            temperature_c, humidity = read_sensor()

            if temperature_c is not None and humidity is not None:
                temperature_f = temperature_c * (9 / 5) + 32
                print(f"Temperature: {temperature_c:.1f}°C / {temperature_f:.1f}°F  |  Humidity: {humidity}%")
            else:
                print("Failed to read sensor, retrying...")

            # DHT11 sensor requires minimum 2 second interval between reads
            time.sleep(2.0)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        dht_device.exit()


if __name__ == "__main__":
    main()
