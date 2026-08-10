# Protocols: Wi-Fi, Zigbee, Thread, Matter — and which we actually have

Reference for the question "is this Zigbee or Matter or Thread?" and why the
answer decides whether a device gets voice, a button, or both.

## The distinction that causes all the confusion

**Wi-Fi, Zigbee and Thread are *transports*** — how bits physically move.
**Matter is an *application language*** — what the messages mean.

Matter **runs on top of** Wi-Fi or Thread. So:

- "Thread vs Matter" is a category error — Thread carries Matter.
- "Zigbee vs Matter" is a fair comparison — different languages, and Zigbee
  bundles its own transport.

## The transports

| | Wi-Fi | Zigbee | Thread |
|---|---|---|---|
| Radio | 2.4/5 GHz | 2.4 GHz, 802.15.4 | 2.4 GHz, 802.15.4 |
| Power draw | High — mains only | Very low, battery-friendly | Very low, battery-friendly |
| Mesh | No | Yes, via mains devices | Yes, via mains devices |
| IP addressable | Yes | **No** — needs a gateway | **Yes**, native IPv6 |
| Needs a hub? | No | **Yes** (our ZBDongle-E) | Border router (our Nest Hubs) |

Zigbee and Thread use the **same radio hardware**. The difference is that
Thread speaks IPv6, so devices are addressable without a protocol-translating
gateway. That single change is what makes Matter-over-Thread possible.

## Why Matter matters here: multi-admin

Matter's decisive property is **multi-admin** — one physical device joins
several controllers *simultaneously*. A Matter plug can be in Google Home
**and** Home Assistant at once: voice from Google, automation and buttons from
HA, no bridge between them.

Zigbee has no equivalent. A Zigbee device belongs to **one** coordinator (ours,
the ZBDongle-E), and anything else must go through that coordinator.

This is exactly why lab-lighting buttons should be Matter, not Zigbee — see
[integration-policy.md](integration-policy.md). Going Zigbee would pull the
lights into HA, and **HA has no voice path**, so it would trade voice away
rather than add a button to it.

## What we actually have

Counts as of 2026-08-10.

| Protocol | Count | Devices |
|---|---|---|
| **Matter** (over Wi-Fi) | 2 | Realwe plug (node 7, live); Currys Sandstrom (node 4, retired ghost) |
| **Zigbee** (ZHA) | 4 | 2 × SONOFF S60ZBTPG (washing machine, tumble dryer), SNZB-02D temp/humidity, eWeLink TH01 |
| **Wi-Fi, proprietary** | ~16 | 13 × Google Cast, eero (UPnP), iEAST AudioCast (DLNA), + 3 Wi-Fi plugs outside HA |
| **Cloud-only** | 2 | Octopus electricity + gas meters (no local radio) |

**Matter is the minority, and that's normal** — it only reached wide device
availability around 2023, so anything older speaks whatever its vendor chose.

### Wi-Fi devices that are NOT Matter

Most of them. Being Wi-Fi says nothing about the language:

- **Google Cast** (13 devices) — Cast protocol, local, not Matter
- **eero** — UPnP/SSDP, read-only stats
- **iEAST AudioCast** — DLNA/UPnP media renderer
- **The three Wi-Fi plugs** (air shower fans, 2 × lab lighting) — Smart Life
  (Tuya) or eWeLink cloud. **Not in HA at all**, by design.

### The Google speakers — voice vs Thread

Not all Google devices are equal, and the difference decides Thread coverage:

| Device | Count | Voice | Thread border router? |
|---|---|---|---|
| Google Nest Hub | 3 | Yes | **Yes** |
| Google Home Mini | 3 | Yes | **No** |
| Google Home | 1 | Yes | **No** |
| Chromecast | 3 | No | No |

So there are **7 voice-capable speakers but only 3 Thread border routers**.
Thread coverage follows the Hubs, not the speakers.

The Cast groups (Everywhere, Holiday, house, Party) are **virtual**, not
hardware.

**Asymmetry worth remembering:** HA can *talk through* these speakers (the
laundry automations push TTS to `media_player.living_room`,
`media_player.kitchen_display`, `media_player.lab_speaker`) but cannot
*listen* through them. Google does not permit third-party assistants on its
speakers, so HA's local Assist would need its own mic hardware
(ESP32-S3 Voice PE, Wyoming satellite).

## Choosing a transport for new kit

| Path | Hub needed | Reaches Google | Reaches HA |
|---|---|---|---|
| Wi-Fi + Smart Life/eWeLink | none | Yes (via vendor cloud) | No |
| Zigbee | ZBDongle-E ✓ | No | Yes |
| **Matter over Wi-Fi** | BLE to commission ✓ | **Yes** | **Yes** |
| Matter over Thread | Nest Hubs ✓ | **Yes** | Needs Thread creds |

**Default to Matter-over-Wi-Fi** for anything wanting both voice and HA.
`thread_credentials_set` is `False` on our matter-server, so Thread devices
would first need credentials shared out of Google's fabric; Wi-Fi Matter works
today with no extra setup (node 7 proves it).

Pick **Zigbee** when HA is the whole point and voice is irrelevant — battery
sensors, buttons, and the laundry power monitors.
