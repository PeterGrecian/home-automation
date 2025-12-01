#!/usr/bin/env python3
"""
GPIO Pin Sequential Flash Test
Flashes each GPIO pin sequentially for LED testing
Prints pin number as each pin is activated
"""

import RPi.GPIO as GPIO
import time

# All usable GPIO pins on Raspberry Pi (BCM numbering)
# Excluding special pins like I2C, SPI, UART by default
GPIO_PINS = [
    4, 5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27
]

# Flash duration in seconds
FLASH_DURATION = 0.5

def flash_all_pins():
    """Flash each GPIO pin sequentially"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Setup all pins as outputs
    for pin in GPIO_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    print("GPIO Sequential Flash Test")
    print("=" * 40)
    print(f"Testing {len(GPIO_PINS)} GPIO pins")
    print("Connect LED + resistor to GND and each pin")
    print("Press Ctrl+C to exit\n")

    try:
        while True:
            for pin in GPIO_PINS:
                # Turn on current pin
                GPIO.output(pin, GPIO.HIGH)
                print(f"GPIO {pin:2d} (Pin {gpio_to_physical(pin):2d}): ON")
                time.sleep(FLASH_DURATION)

                # Turn off current pin
                GPIO.output(pin, GPIO.LOW)
                time.sleep(0.1)  # Brief pause between pins

            print()  # Blank line after full cycle

    except KeyboardInterrupt:
        print("\n\nExiting...")
    finally:
        GPIO.cleanup()


def gpio_to_physical(gpio_pin):
    """Convert BCM GPIO number to physical pin number"""
    # Mapping of BCM to physical pin numbers
    bcm_to_physical = {
        2: 3, 3: 5, 4: 7, 5: 29, 6: 31,
        12: 32, 13: 33, 16: 36, 17: 11, 18: 12,
        19: 35, 20: 38, 21: 40, 22: 15, 23: 16,
        24: 18, 25: 22, 26: 37, 27: 13
    }
    return bcm_to_physical.get(gpio_pin, 0)


if __name__ == "__main__":
    flash_all_pins()
