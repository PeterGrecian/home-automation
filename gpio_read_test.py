#!/usr/bin/env python3
"""
GPIO Pin Sequential Read Test
Reads each GPIO pin sequentially and displays its state
Useful for testing inputs and verifying connections
Configuration from gpio_flash_config.yaml
"""

import RPi.GPIO as GPIO
import yaml
import os
import time

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'gpio_flash_config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Get settings from config
GPIO_PINS = config['gpio_pins']
READ_INTERVAL = config.get('flash_duration', 0.5)  # Reuse flash_duration for read interval
CYCLES = config['cycles']


def read_all_pins():
    """Read each GPIO pin sequentially"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Setup all pins as inputs with pull-down resistors
    for pin in GPIO_PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    print("GPIO Sequential Read Test")
    print("=" * 40)
    print(f"Reading {len(GPIO_PINS)} GPIO pins")
    print(f"Read interval: {READ_INTERVAL}s")
    if CYCLES > 0:
        print(f"Cycles: {CYCLES}")
    print("Pull-down mode: Pins read LOW unless pulled HIGH")
    print("Press Ctrl+C to exit\n")

    try:
        cycle_count = 0
        while CYCLES == 0 or cycle_count < CYCLES:
            for pin in GPIO_PINS:
                # Read pin state
                state = GPIO.input(pin)
                state_str = "HIGH" if state else "LOW "
                print(f"GPIO {pin:2d} (Pin {gpio_to_physical(pin):2d}): {state_str}")
                time.sleep(READ_INTERVAL)

            cycle_count += 1
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
    read_all_pins()
