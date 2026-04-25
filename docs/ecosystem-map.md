# Ecosystem map: phone apps, clouds, and Home Assistant

How the various smart-home apps, clouds, and protocols fit together — and where Home Assistant slots in.

## Phone apps in use

| App | Cloud / protocol | Devices in this house | HA path |
|---|---|---|---|
| **Smart Life** (Tuya) | Tuya cloud + local LAN | Eightree ET36, mystery thermometer, possibly the lab WiFi Sonoffs | Tuya cloud integration *or* LocalTuya (HACS) |
| **eWeLink** (Sonoff/iTead) | Sonoff/iTead cloud | Stock-firmware Sonoff WiFi devices | Sonoff LAN (HACS) or eWeLink cloud integration |
| **Google Home** | Google cloud + Matter/local | Anything linked via the integrations above; Cast speakers/displays | HA → Google Assistant integration (exposes HA entities to Google) |
| **Home Assistant Companion** | Direct to HA | Mobile notifications, location, phone sensors | Native — this *is* the HA mobile app |
| **ESPHome** (desktop tool, no phone app) | Local only | Custom-flashed ESP8266/ESP32 boards | Native ESPHome integration in HA, fully local |

Other ecosystems worth knowing about (not currently in use here):

- **Tasmota** — alternative custom firmware for ESP-based devices. Talks MQTT to HA.
- **Matter / Thread** — newer cross-vendor standard. Google Home, HA, and Apple Home all support it.
- **Apple Home** — only matters with iOS users.

## Composition: one device, one primary path

For each physical device pick **one** "primary" integration. Everything else inherits.

- **Zigbee Sonoff plugs** (washing machine, tumble dryer) → ZHA in HA → exposed to Google Home via HA. No Sonoff cloud or eWeLink app needed.
- **WiFi Sonoff plugs** (lab lights) → Smart Life or eWeLink → Google Home directly. Bypasses HA. Matches the policy of leaving simple plugs in their native ecosystem.
- **Tuya plugs that need HA logic** (Eightree ET36 — auto-power-cycling zeropi/springpi) → LocalTuya → HA → optionally re-exposed to Google Home for voice. Smart Life app keeps working in parallel because it speaks the same LAN protocol.
- **ESPHome custom boards** (future) → direct ESPHome → HA. No cloud.

## Why "HA is the hub" rather than each app separately

If Google Home talks to **HA** rather than to each ecosystem (Smart Life, eWeLink, …) directly, voice control inherits everything HA knows about, automations can mix any ecosystem's devices, and there is one source of truth. But this is a *recommendation*, not a requirement: plugs that work fine in Google Home directly can stay there (see [integration-policy.md](integration-policy.md)).

## Cloud vs LocalTuya for Tuya devices

Two ways to get Tuya/Smart Life devices into HA:

- **Official Tuya cloud integration** — easier (free Tuya IoT developer signup, link Smart Life account). Pulls state via Tuya's cloud API.
- **LocalTuya** (HACS) — talks directly on the LAN, no internet dependency. Needs each device's local key extracted once from the Tuya developer portal. Survives Tuya outages and has lower latency.

**Pick LocalTuya for reliability-critical automations** (e.g. auto-recovery for hung Pis — the recovery shouldn't depend on Tuya's cloud being up). **Pick the cloud integration for sensors** where a brief outage just means stale readings.

## Specific exception: Eightree ET36 ("8tree")

Powers **zeropi** and **springpi** — both run cameras (the old `camerapi` name is obsolete; cameras moved to these two). Reason for going into HA: auto-power-cycle when the Pis hang.

**Path: Matter, not LocalTuya.** Discovered during setup that the 8tree was paired to Google Home as a native Matter device (no Smart Life / eWeLink in the chain — "Linked Matter apps and services" was empty). Matter is a local protocol with no cloud dependency, which suits the reliability requirement.

Setup so far:
- `python-matter-server` Docker container running on homepi (see [home-assistant.md](home-assistant.md))
- Matter integration added in HA, talking to it at `ws://localhost:5580/ws`
- 8tree commissioning into HA pending — multi-fabric share from Google Home was failing with "Can't set up device". To be retried by hand.

Both Pis share the plug, so cycling reboots both — acceptable for now; revisit if it becomes a problem.
