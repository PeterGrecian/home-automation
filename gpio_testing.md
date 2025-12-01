# GPIO Testing Tools

Documentation for GPIO pin testing utilities on Raspberry Pi.

## Overview

This repository includes tools for testing and diagnosing GPIO pins on Raspberry Pi, useful for:
- Verifying GPIO pins work correctly
- Testing LED probes and circuits
- Debugging hardware connections
- Learning GPIO pin layouts

## GPIO Sequential Flash Test (Output)

**Script:** `gpio_flash_test.py`
**Config:** `gpio_flash_config.yaml`

### What It Does

Flashes each GPIO pin sequentially in order, printing both the BCM GPIO number and physical pin number as each pin activates. Connect an LED probe to watch each pin light up in sequence.

## GPIO Sequential Read Test (Input)

**Script:** `gpio_read_test.py`
**Config:** `gpio_flash_config.yaml` (reuses same config)

### What It Does

Reads each GPIO pin sequentially and displays whether it's HIGH or LOW. Useful for testing input connections, buttons, switches, or verifying signals from other devices. Pins are configured with pull-down resistors (read LOW by default).

### Usage (Flash Test)

```bash
python3 gpio_flash_test.py
```

### Usage (Read Test)

```bash
python3 gpio_read_test.py
```

**Flash Test** will:
1. Configure all specified GPIO pins as outputs
2. Flash each pin HIGH for the configured duration
3. Display the GPIO number and physical pin number
4. Move to the next pin after a brief pause
5. Repeat the cycle (infinite loop or configured number of cycles)

**Read Test** will:
1. Configure all specified GPIO pins as inputs (pull-down)
2. Read each pin state sequentially
3. Display the GPIO number, physical pin number, and state (HIGH/LOW)
4. Pause between reads according to configuration
5. Repeat the cycle (infinite loop or configured number of cycles)

### Configuration

Edit `gpio_flash_config.yaml` to customize:

```yaml
# Flash duration (how long each pin stays HIGH) in seconds
flash_duration: 0.5

# Pause between pins in seconds
pause_between_pins: 0.1

# GPIO pins to test (BCM numbering)
gpio_pins:
  - 4   # Physical pin 7
  - 17  # Physical pin 11
  - 27  # Physical pin 13
  # ... add or remove pins as needed

# Number of cycles (0 = infinite loop)
cycles: 0
```

**Configuration Options:**
- `flash_duration`: How long each pin stays HIGH (seconds)
- `pause_between_pins`: Delay between activating pins (seconds)
- `gpio_pins`: List of GPIO pins to test (BCM numbering)
- `cycles`: Number of complete cycles to run (0 = infinite)

### Building an LED Test Probe

To test GPIO pins, build a simple LED probe:

**Materials:**
- 1x LED (any color)
- 1x 220Ω resistor (or 330Ω)
- 2x Dupont female connectors
- Wire

**Assembly:**
1. Solder LED cathode (-) to one end of resistor
2. Connect resistor other end to black wire with female dupont
3. Connect LED anode (+) to red wire with female dupont
4. Optionally add heat shrink tubing for durability

**Usage:**
- Black probe → Raspberry Pi GND (pin 6, 9, 14, 20, 25, 30, 34, or 39)
- Red probe → GPIO pin being tested
- LED lights when pin goes HIGH

### GPIO Pin Reference

Physical pin layout with BCM GPIO numbers.

| Pin | Function       | Pin | Function       |
|-----|----------------|-----|----------------|
| 1   | *3V3*          | 2   | **5V**         |
| 3   | GPIO 2         | 4   | **5V**         |
| 5   | GPIO 3         | 6   | **GND**        |
| 7   | GPIO 4         | 8   | GPIO 14        |
| 9   | **GND**        | 10  | GPIO 15        |
| 11  | GPIO 17        | 12  | GPIO 18        |
| 13  | GPIO 27        | 14  | **GND**        |
| 15  | GPIO 22        | 16  | GPIO 23        |
| 17  | *3V3*          | 18  | GPIO 24        |
| 19  | GPIO 10        | 20  | **GND**        |
| 21  | GPIO 9         | 22  | GPIO 25        |
| 23  | GPIO 11        | 24  | GPIO 8         |
| 25  | **GND**        | 26  | GPIO 7         |
| 27  | GPIO 0         | 28  | GPIO 1         |
| 29  | GPIO 5         | 30  | **GND**        |
| 31  | GPIO 6         | 32  | GPIO 12        |
| 33  | GPIO 13        | 34  | **GND**        |
| 35  | GPIO 19        | 36  | GPIO 16        |
| 37  | GPIO 26        | 38  | GPIO 20        |
| 39  | **GND**        | 40  | GPIO 21        |

**Legend:**
- *3V3* = 3.3V Power (italic)
- **5V** = 5V Power (bold)
- **GND** = Ground/0V (bold)

Full interactive pinout: https://pinout.xyz

### Example Output (Flash Test)

```
GPIO Sequential Flash Test
========================================
Testing 17 GPIO pins
Flash duration: 0.5s
Pause between pins: 0.1s
Connect LED + resistor to GND and each pin
Press Ctrl+C to exit

GPIO  4 (Pin  7): ON
GPIO  5 (Pin 29): ON
GPIO  6 (Pin 31): ON
GPIO 12 (Pin 32): ON
...
```

### Example Output (Read Test)

```
GPIO Sequential Read Test
========================================
Reading 17 GPIO pins
Read interval: 0.5s
Pull-down mode: Pins read LOW unless pulled HIGH
Press Ctrl+C to exit

GPIO  4 (Pin  7): LOW
GPIO  5 (Pin 29): LOW
GPIO  6 (Pin 31): HIGH
GPIO 12 (Pin 32): LOW
...
```

In this example, GPIO 6 (pin 31) is reading HIGH because something is pulling it up (connected to 3.3V or another output pin).

## Basic GPIO Test

**Script:** `test_gpio_basic.py`

Simple script to verify GPIO 4 can toggle HIGH/LOW and read input states. Useful for diagnosing faulty GPIO pins.

```bash
python3 test_gpio_basic.py
```

## DHT11/DHT22 GPIO Test

**Script:** `test_dht11_gpio.py`

Tests GPIO pin connection for DHT11/DHT22 sensors using pigpio. Verifies basic read/write operations and pull-up resistor functionality.

```bash
python3 test_dht11_gpio.py
```

## Troubleshooting

**LED doesn't light up:**
- Check LED polarity (long leg = anode/+, short leg = cathode/-)
- Verify resistor value (220Ω-330Ω recommended)
- Ensure GND probe is connected to a ground pin
- Try a different GPIO pin

**Script errors:**
- Install dependencies: `sudo apt-get install python3-yaml`
- Run without sudo (GPIO permissions should be configured via gpio group)
- Check config file exists: `ls -l gpio_flash_config.yaml`

**Permission errors:**
- Add user to gpio group: `sudo usermod -a -G gpio $USER`
- Logout and login for group changes to take effect

## Safety Notes

- Never connect GPIO pins directly to 5V or 3.3V power rails
- Always use current-limiting resistors with LEDs
- Maximum GPIO current: 16mA per pin, 50mA total
- GPIO pins are **not** 5V tolerant (3.3V max input)

## Related Documentation

- [DHT11/DHT22 Sensor Guide](dht11.md)
- [Network Monitor Setup](CLAUDE.md)
- [Project README](README.md)
