# Integration policy: what goes in Home Assistant, what doesn't

A guideline for deciding whether a smart device should be brought into Home Assistant or left in its native ecosystem (Smart Life, Google Home, etc.).

## Principle

**All sensors in HA. Plugs stay where they work.**

Each layer added to a device's control chain is another thing that can break. WiFi plug + Smart Life + Google Home is already a 3-component chain that gives reliable voice control. Pulling it into HA adds a fourth component and splits the source of truth between Smart Life and HA.

## Sensors → always HA

Temperature, humidity, power, motion, presence — sensors have no voice-control angle to lose by being in HA, and centralising them gives:

- One dashboard with everything
- Long-term history (Google Home discards this)
- Cross-device automation triggers

Examples in scope: Sonoff SNZB-02D Zigbee temp/humidity, future DHT11/DHT22 readings (via MQTT), Tuya/Smart Life thermometers.

## Plugs → stay in native ecosystem by default

WiFi plugs (Sonoff WiFi, Tuya/Smart Life) work well with Google Home for voice + simple schedules. Don't migrate to HA just for the sake of it.

**Migrate a plug to HA only when you need an HA-only capability for that specific plug:**

- Power monitoring + multi-month history
- Conditional automation Google Home can't express (presence, sensor-driven, delays, multi-step)
- Local fallback when the vendor cloud is down
- Cross-device logic (sensor X → plug Y)

The two utility-room Zigbee Sonoffs (washing machine, tumble dryer) are HA-managed precisely because they need power-drop-based finished alerts — not something Google Home can do.

The two lab WiFi Sonoffs stay outside HA: voice + schedule via Google Home is enough.

## Practical rules

| Device type | Default home | Migrate to HA when |
|---|---|---|
| Temperature / humidity sensor | HA | (always) |
| Motion / presence sensor | HA | (always) |
| Energy / power sensor | HA | (always) |
| WiFi smart plug | Smart Life + Google Home | A specific automation needs power monitoring or HA logic |
| Zigbee smart plug | HA (no choice — it needs the ZHA bridge) | (always) |
| Light bulb | Google Home | Same rule as plugs |

## Implication for the Tuya/Smart Life integration

Add the Tuya cloud integration to HA so its **sensors** (e.g. the mystery thermometer) appear, but leave the Tuya plugs controlled via Smart Life + Google Home as before. They will also appear in HA after the integration is added — that's fine, just don't build automations on them unless one of the migration triggers above applies.
