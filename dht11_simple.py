#!/usr/bin/env python3
"""
Simple DHT11/DHT22 reader
Supports both DHT11 and DHT22 (AM2302) sensors
Sensor type configured in dht11_config.yaml
"""

import time
import yaml
import os
import RPi.GPIO as GPIO

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'dht11_config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

DHT11_PIN = config['gpio_pin']

def read_dht_sensor():
    """
    Read DHT11 or DHT22 sensor using bit-banging.
    Sensor type determined by config.
    Returns (temperature, humidity) or (None, None) on error.
    """
    sensor_type = config.get('sensor_type', 'DHT11').upper()
    # Setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    data = []

    # Send start signal
    GPIO.setup(DHT11_PIN, GPIO.OUT)
    GPIO.output(DHT11_PIN, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(DHT11_PIN, GPIO.LOW)
    time.sleep(0.02)  # 20ms low
    GPIO.setup(DHT11_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Wait for response
    timeout = 0
    while GPIO.input(DHT11_PIN) == GPIO.HIGH:
        timeout += 1
        if timeout > 100:
            return None, None

    # Read 40 bits
    for i in range(40):
        # Wait for high
        timeout = 0
        while GPIO.input(DHT11_PIN) == GPIO.LOW:
            timeout += 1
            if timeout > 100:
                return None, None

        # Measure high pulse length
        start = time.time()
        timeout = 0
        while GPIO.input(DHT11_PIN) == GPIO.HIGH:
            timeout += 1
            if timeout > 100:
                return None, None
        duration = time.time() - start

        # 0 = ~26-28us, 1 = ~70us
        data.append(1 if duration > 0.00005 else 0)

    # Convert bits to bytes
    humidity_int = 0
    humidity_dec = 0
    temp_int = 0
    temp_dec = 0
    checksum = 0

    for i in range(8):
        humidity_int = (humidity_int << 1) | data[i]
        humidity_dec = (humidity_dec << 1) | data[i + 8]
        temp_int = (temp_int << 1) | data[i + 16]
        temp_dec = (temp_dec << 1) | data[i + 24]
        checksum = (checksum << 1) | data[i + 32]

    # Verify checksum
    if checksum == ((humidity_int + humidity_dec + temp_int + temp_dec) & 0xFF):
        if sensor_type == 'DHT22':
            # DHT22 returns 16-bit values with decimal
            humidity = ((humidity_int << 8) | humidity_dec) / 10.0
            temp = ((temp_int << 8) | temp_dec) / 10.0
            # Handle negative temperatures for DHT22
            if temp_int & 0x80:
                temp = -temp
        else:
            # DHT11 returns integer values
            temp = temp_int
            humidity = humidity_int

        return temp, humidity
    else:
        return None, None


def main():
    sensor_type = config.get('sensor_type', 'DHT11')
    print(f"{sensor_type} Sensor Reader")
    print(f"Reading from GPIO {DHT11_PIN}")
    print("Press Ctrl+C to exit\n")

    try:
        while True:
            temp, humidity = read_dht_sensor()

            if temp is not None and humidity is not None:
                temp_f = temp * 9/5 + 32
                if config.get('show_both_units', True):
                    print(f"Temperature: {temp}°C / {temp_f:.1f}°F  |  Humidity: {humidity}%")
                elif config.get('temperature_unit', 'C') == 'F':
                    print(f"Temperature: {temp_f:.1f}°F  |  Humidity: {humidity}%")
                else:
                    print(f"Temperature: {temp}°C  |  Humidity: {humidity}%")
            else:
                print("Failed to read sensor, retrying...")

            time.sleep(config.get('read_interval', 2))

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
