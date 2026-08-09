# Hardware inventory

Every piece of physical kit in the Home Assistant estate: the host, its radios,
and the devices they drive. Complements [home-assistant.md](home-assistant.md)
(how HA is run) and [ecosystem-map.md](ecosystem-map.md) (which cloud/app owns
what).

Snapshot taken **2026-08-09** from the live HA device registry
(`core.device_registry`, 34 devices), the matter-server WS API, and `lsusb` on
homepi. Cloud-only "devices" that aren't hardware (Sun, Backup, HACS, Forecast,
Octopus tariff entries) are omitted.

## The hub

| | |
|---|---|
| Host | **homepi** — Raspberry Pi 4 Model B Rev 1.4 |
| LAN | `192.168.0.53` (Tailscale `100.127.158.37`) |
| HA | `homeassistant:stable` container, `/home/pi/homeassistant` → `/config` |
| Matter | `python-matter-server:stable`, `/opt/matter-server/data` → `/data` |

`homepi.local` mDNS is **unreliable from pip** — it failed mid-commissioning on
2026-08-09 with `gaierror -2`. Use the IP for anything scripted.

## Radios

| Radio | Hardware | Bus | Serves |
|---|---|---|---|
| **Zigbee** | Sonoff ZBDongle-E (Zigbee 3.0 USB Dongle Plus V2) | `10c4:ea60` CP210x → `ttyUSB0` | ZHA — 4 devices |
| **Bluetooth** | Pi 4 built-in, `hci0` (`E4:5F:01:46:92:35`) | onboard | Matter BLE commissioning |
| **Wi-Fi/Thread** | — | — | Matter over Wi-Fi; **no Thread border router** |

By-id path (stable across reboots, prefer over `ttyUSB0`):
`/dev/serial/by-id/usb-Itead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_V2_fe489cf068c2ef118098c8138148b910-if00-port0`

`hci0` must be **UP** and the matter-server container needs
`--bluetooth-adapter 0`, `--security-opt apparmor=unconfined`,
`-v /run/dbus:/run/dbus:ro` and `--network=host` or BLE commissioning fails.
See the home-automation strand STATE — **this container is a hand-run
`docker run`, not captured in IaC.**

## Matter devices

Fabric `2608715694913625144`. Commission via the WS API on `ws://<ip>:5580/ws`
(`set_wifi_credentials` → `commission_with_code`), no phone app.

| Node | Device | Vendor/Product ID | SW | State |
|---|---|---|---|---|
| **7** | Realwe Innovation Smart Plug | 5242 / 851 | 1.2.6 | **live** — On/Off on endpoint 1 |
| 4 | Currys Sandstrom Wi-Fi Smart Plug | 5470 / 9217 | V1.0.0.5 | **retired ghost**, `available: False` |

**Node 7 powers the astro EOS dummy-battery feed.** `astro/bin/eos-power`
drives it; it resolves the plug by **vendor** (`MATTER_VENDOR = "Realwe"`,
attribute `0/40/1`) with node id only as fallback, so a future swap needs no
code edit.

Match on vendor, **not** product: the node-4 ghost is also named
`…Smart Plug`, so a product-name match hits both. Node 4 was discarded as
unreliable on 2026-08-09; its fabric entry is deliberately left in place and is
harmless.

## Zigbee devices (ZHA)

| Device | Model | Purpose |
|---|---|---|
| Washing Machine | SONOFF S60ZBTPG | Smart plug, power monitoring (utility room) |
| Tumble Dryer | SONOFF S60ZBTPG | Smart plug, power monitoring (utility room) |
| Lab Temperature | SONOFF SNZB-02D | Temp/humidity sensor |
| eWeLink TH01 | eWeLink TH01 | Temp/humidity sensor |

> **Correction to [home-assistant.md](home-assistant.md):** that doc lists
> "four Sonoff plugs", two of them Wi-Fi in the Lab. As of 2026-08-09 the
> registry holds **only these two Zigbee plugs** — there are no Wi-Fi Sonoff
> plug devices or entities. `light.lights_east` is a `switch_as_x` helper
> wrapping the **Matter** plug, not a Sonoff. The only switch entities that
> exist are `switch.washing_machine`, `switch.tumble_dryer`,
> `switch.smart_plug` (node 7) and `switch.sandstrom_wi_fi_smart_plug`
> (node 4, dead).

## Google Cast

Media endpoints, used for TTS alerts. Not controllable hardware.

| Device | Model |
|---|---|
| Music room speaker, Lab speaker, Minsk speaker | Google Home Mini |
| Living Room | Google Home |
| Kitchen display, Beside display, Zoes fancy Google | Google Nest Hub |
| Hifi, Downstairs, Bedroom TV | Chromecast |
| BBC Radio 3u | iEAST AudioCast (DLNA) |

Cast **groups** (Everywhere, Holiday, house, Party) are virtual, not hardware.

## Other

| Device | What |
|---|---|
| eero | Router/mesh, via UPnP integration |
| Electricity + Gas Meter | Secure Meters UK C0A10101 / C4A10501, via Octopus Energy (cloud, read-only) |
| Pixel 6a | Phone running the HA Companion app |

## Gaps

- **No Thread border router.** Matter devices must be Wi-Fi; Thread-only kit
  cannot be commissioned as things stand.
- **matter-server is not in IaC** — a homepi reprovision loses the BLE flags and
  breaks the EOS reset path. Owned by the astro-canon strand.
- **Node 4 ghost** still on the fabric. Deliberate, removable via `remove_node`.
