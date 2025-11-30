#!/usr/bin/env python3
"""
DHT11 Temperature and Humidity Sensor Reader (using pigpio)
Reads DHT11 sensor data from GPIO pin 3 on Raspberry Pi
Uses pigpio library - more reliable on older/32-bit Raspberry Pi systems
"""

import time
import pigpio

# GPIO pin for DHT11 data line
DHT11_PIN = 3

class DHT11Reader:
    """
    DHT11 sensor reader using pigpio library.
    More compatible with 32-bit ARM systems than Adafruit library.
    """

    def __init__(self, pi, gpio):
        self.pi = pi
        self.gpio = gpio
        self.high_tick = 0
        self.bit = 40
        self.either_edge_cb = None

    def _decode_dht11(self, gpio, level, tick):
        """Decode DHT11 data bits"""
        if level == 0:  # Falling edge
            self.bit += 1
            if self.bit >= 40:
                self.bit = -2
                self.pi.set_watchdog(self.gpio, 0)

        elif level == 1:  # Rising edge
            diff = pigpio.tickDiff(self.high_tick, tick)
            self.high_tick = tick

            if diff >= 50:
                self.bit = -1
                self.hum = 0
                self.temp = 0
                self.checksum = 0

            elif self.bit >= 0:
                self.hum = (self.hum << 1) + (0 if diff < 28 else 1)

                if self.bit >= 8:
                    self.temp = (self.temp << 1) + (0 if diff < 28 else 1)

                    if self.bit >= 16:
                        self.checksum = (self.checksum << 1) + (0 if diff < 28 else 1)

    def read(self):
        """
        Read temperature and humidity from DHT11.

        Returns:
            tuple: (temperature_c, humidity_percent) or (None, None) on error
        """
        self.bit = 40
        self.hum = 0
        self.temp = 0
        self.checksum = 0

        # Send start signal
        self.pi.write(self.gpio, 0)
        time.sleep(0.018)  # 18ms low

        self.pi.set_mode(self.gpio, pigpio.INPUT)
        self.pi.set_watchdog(self.gpio, 200)

        if self.either_edge_cb is None:
            self.either_edge_cb = self.pi.callback(self.gpio, pigpio.EITHER_EDGE, self._decode_dht11)

        time.sleep(0.2)

        self.pi.set_watchdog(self.gpio, 0)

        # Extract data
        humidity = self.hum >> 8
        temp = self.temp >> 8
        checksum = (self.hum + self.temp) & 0xFF

        # Verify checksum
        if checksum == self.checksum and humidity <= 100 and temp <= 50:
            return temp, humidity
        else:
            return None, None

    def cancel(self):
        """Clean up callbacks"""
        if self.either_edge_cb is not None:
            self.either_edge_cb.cancel()
            self.either_edge_cb = None


def main():
    """Main loop - continuously read sensor data"""
    print("DHT11 Sensor Reader (pigpio version)")
    print("Reading from GPIO pin 3")
    print("Press Ctrl+C to exit\n")

    # Connect to pigpio daemon
    pi = pigpio.pi()

    if not pi.connected:
        print("ERROR: Could not connect to pigpio daemon")
        print("Please start it with: sudo pigpiod")
        return

    sensor = DHT11Reader(pi, DHT11_PIN)

    try:
        while True:
            temperature_c, humidity = sensor.read()

            if temperature_c is not None and humidity is not None:
                temperature_f = temperature_c * (9 / 5) + 32
                print(f"Temperature: {temperature_c:.1f}°C / {temperature_f:.1f}°F  |  Humidity: {humidity}%")
            else:
                print("Failed to read sensor, retrying...")

            # DHT11 requires minimum 2 second interval
            time.sleep(2.0)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sensor.cancel()
        pi.stop()


if __name__ == "__main__":
    main()
