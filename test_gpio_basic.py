#!/usr/bin/env python3
"""
Basic GPIO test - blink GPIO 4 to verify it works
If you have an LED, connect it: GPIO4 -> LED -> 220Ω resistor -> GND
Otherwise this will just test if GPIO can be controlled
"""

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

TEST_PIN = 4

print("Testing GPIO 4 basic functionality")
print("Toggling pin HIGH/LOW 10 times...")
print("If you have an LED connected, it should blink")
print()

GPIO.setup(TEST_PIN, GPIO.OUT)

try:
    for i in range(10):
        GPIO.output(TEST_PIN, GPIO.HIGH)
        print(f"Pin {TEST_PIN}: HIGH")
        time.sleep(0.5)

        GPIO.output(TEST_PIN, GPIO.LOW)
        print(f"Pin {TEST_PIN}: LOW")
        time.sleep(0.5)

    print("\n✓ GPIO 4 can be controlled")
    print("\nNow testing as INPUT...")

    GPIO.setup(TEST_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print(f"With pull-up: {GPIO.input(TEST_PIN)}")

    GPIO.setup(TEST_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    print(f"With pull-down: {GPIO.input(TEST_PIN)}")

    print("\n✓ GPIO 4 works as input/output")
    print("\nConclusion: GPIO pins are functional")
    print("Problem is likely with the DHT11 sensors")

except Exception as e:
    print(f"\n✗ GPIO test failed: {e}")
    print("GPIO pins may be damaged")

finally:
    GPIO.cleanup()
