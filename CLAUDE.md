# home-automation

Home automation for managing smart switches, temperature sensors, Google Home, and network monitoring on a Raspberry Pi.

## Structure

- `network-monitor/` — multi-threaded Python app tracking device connectivity via arp-scan + ping
- `proximity.py` — Wi-Fi/Bluetooth presence detection for automation triggers
- `evening-lights.yaml`, `on-off-test.yaml` — Google Home time-based automations

## Running

```bash
# Network monitor (don't use sudo — it's embedded in subprocess calls)
python3 network-monitor/monitor.py

# As a systemd service
sudo cp network-monitor/network-monitor.service /etc/systemd/system/
sudo systemctl enable --now network-monitor.service
journalctl -u network-monitor -f
```

## Configuration

`network-monitor/config.json` — key settings:
- `subnet`, `interface` (eth0 or wlan0)
- `discovery_interval_seconds`, `polling_interval_seconds`
- `device_overrides` — per-device config (regex on vendor name), e.g. increase ping count for flaky Espressif devices

## Deployment

Runs on Raspberry Pi (ARM Linux). System deps: `arp-scan`, `nmap`, optionally `fping`.

## TODO

### In Progress
- Configure switch #4 EIGHTREE ET36
- Monitor the switches from a Pi with Python
- Zigbee/wifi temperature and power infrastructure and HA software on Pi
- Test DHT11s with Pi GPIO

### Todo
- Python for Google Home
- Add door to network shelf
- Female dupont resistor/LED probe
- Configure Energy Dashboard in Home Assistant
- Configure DHT22 after delivery
- Design curtain automation system
- Google Cloud OAuth for Matter switches
