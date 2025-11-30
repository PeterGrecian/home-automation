# home-automation

Home automation project for Raspberry Pi including network device monitoring, sensor data collection, and Google Home integrations.

## Components

- **Network Monitor** (`network-monitor/`) - Multi-threaded Python application for tracking device connectivity on local network
- **DHT11 Sensor Reader** (`dht11_reader.py`) - Temperature and humidity monitoring via GPIO pin 3
- **Proximity Detection** (`proximity.py`) - Wi-Fi and Bluetooth-based presence detection
- **Google Home Automations** (YAML files) - Time-based automation scripts

## Documentation

- [Network Monitor Setup](CLAUDE.md#network-monitor-configuration-network-monitorconfigjson)
- [DHT11 Sensor Guide](dht11.md)

## Links

- Project Board: https://github.com/users/PeterGrecian/projects/12/views/1
- Google Home Automations: https://home.google.com/home/1-56d22f65d9f3fcfe14bb11676c8914b07cb922bc77a9d3450e7c1937eb8eb8da/automations/create
