# Home Assistant

Home Assistant runs on **homepi** (Raspberry Pi 4, 192.168.0.53). It is the central hub for all smart-plug automations, Zigbee devices (ZHA), and Google Home / media-player TTS alerts.

## Access

| | |
|---|---|
| URL | http://192.168.0.53:8123 |
| API token | `super/bin/secrets get /home-automation/ha-claude` |
| Auth | `Authorization: Bearer <token>` |
| WebSocket | `ws://192.168.0.53:8123/api/websocket` (needed for entity registry edits) |

`homepi.local` mDNS is unreliable from `pip` — use the IP, or check pi-fleet.

## Smart plug fleet

**Two** Zigbee plugs are in HA. The lab Wi-Fi plugs are **not** — they bypass HA entirely (see below).

| Plug | Type | Location | Purpose | Switch entity |
|---|---|---|---|---|
| Sonoff S60ZBTPG | Zigbee (ZHA) | Utility room | Washing machine | `switch.washing_machine` |
| Sonoff S60ZBTPG | Zigbee (ZHA) | Utility room | Tumble dryer | `switch.tumble_dryer` |

Both expose power/voltage/current/summation sensors, which is the entire reason they are in HA.

**These plugs are MEASURE-ONLY.** They watch for the end-of-cycle power drop and must never switch the appliance — switching one mid-cycle kills a load. Their switch entities are therefore not exposed on the dashboard as toggles, and nothing in HA calls `turn_off` on them. See [integration-policy.md](integration-policy.md) for the three unwanted power-control paths found and closed on 2026-08-10.

### The lab Wi-Fi plugs are outside HA

Three Wi-Fi plugs exist — air shower fans, and two for lab lighting — reached via Smart Life/eWeLink → Google Home, bypassing HA by design ([ecosystem-map.md](ecosystem-map.md)). **They have no HA entity**, so they cannot be scripted, automated, or driven by an HA button.

An earlier version of this table listed two of them as HA plugs, with `switch.sonoff_s60zbtpg` as the "Lights East" entity. No such switch entity exists — the tumble dryer's switch is `switch.tumble_dryer`; only its *sensors* kept the generic `sonoff_s60zbtpg` name. What did exist was `light.lights_east`, a `switch_as_x` helper wrapping `switch.tumble_dryer`, so "Lights East" switched the **dryer**, not any lab light. The helper was deleted 2026-08-10.

## Appliance-finished automations

Both washing machine and tumble dryer share the same pattern:

- **Trigger** — power sensor below 5 W for 3 minutes
- **Condition** — **none** (`conditions: []`). Previously gated on the plug's switch entity being `on`, used as a manual enable flag. Dropped 2026-08-10: making the switch an arming control meant routinely toggling a plug that must never be switched. The power drop alone means the cycle finished.
- **Actions** —
  - TTS "The X has finished." to `media_player.living_room`, `media_player.kitchen_display`, `media_player.lab_speaker` (via `tts.google_translate_en_com`)
  - `notify.mobile_app_homepi` push notification
  - `rest_command.alerting_fire` with `data: {title, detail, severity, slack}` — laundry alerts use `severity: info` (Slack only, no xMatters page — laundry doesn't warrant paging) and `slack: laundry` (routes to the #laundry channel rather than the default `alerts`)

| Appliance | Power sensor | Automation |
|---|---|---|
| Washing machine | `sensor.washing_machine_power` | `automation.washing_machine_finished` |
| Tumble dryer | `sensor.tumble_dryer_power` | `automation.tumble_dryer_finished` |

The dryer's entities were renamed `sonoff_s60zbtpg_*` → `tumble_dryer_*` on 2026-08-12, so all three S60ZBTPG plugs now carry appliance names rather than the model name. Previously the dryer kept the generic model id (it was never renamed at the entity level), which was **a live footgun, not just a readability problem**: a third S60ZBTPG (`canon_eos_power`, the EOS plug) joined the same coordinator, and anything matching that model *by name* rather than by entity id would have switched **the dryer**. Same shape as the `light.lights_east` fault and the node-4 Sandstrom ghost. **Match on entity id, never on model name.**

Renaming entity ids does **not** update references — `automations.yaml` (dryer-finished trigger, coordinator watchdog) and the status dashboard were updated by hand at the same time, and automations reloaded. Anything renamed here must have its references swept the same way.

The 3-minute delay avoids false triggers from mid-cycle pauses (rinse, spin-up). The 5 W threshold may need tuning for appliances with higher standby draw.

### Coordinator watchdog

`automation.zigbee_coordinator_offline_watchdog` fires `alerting_fire` (**severity `warn`** — pages via xMatters, plus `slack: laundry`) if either laundry power sensor stays `unavailable` for 15 min. This catches ZHA/USB-coordinator dropouts the same day instead of only noticing when a wash finishes and no alert arrives (which cost us 10 days in the 2026-06-25 incident — see Troubleshooting). The appliance-finished automations rely on live power sensors, so if the coordinator drops, they silently never fire.

### `rest_command.alerting_fire`

Defined in `homepi:/home/pi/homeassistant/configuration.yaml` (not in git — back up before editing). Templated payload posts to the alerting API Gateway:

```yaml
rest_command:
  alerting_fire:
    url: "https://b5wgk4mp4g.execute-api.eu-west-1.amazonaws.com/alert"
    method: POST
    content_type: "application/json"
    payload: >-
      {{ {
        'source': 'home-assistant',
        'severity': severity | default('info'),
        'title': title,
        'detail': detail | default(''),
      } | combine(
        {'slack':    slack}    if slack    is defined else {},
        {'xmatters': xmatters} if xmatters is defined else {},
        {'appraise': appraise} if appraise is defined else {}
      ) | to_json }}
```

Callers pass `data: {title, detail, severity?, slack?, xmatters?, appraise?}`. **Severity defaults to `info` (Slack-only, no xMatters page)** — anything that should page must set `severity: warn` or `critical` explicitly. This way, forgetting a field in a notification automation never pages.

> **The key is `payload`, not `payload_template`.** HA renamed this option; `payload_template` fails config validation (`'payload_template' is an invalid option for 'rest_command'`) and the whole `rest_command` domain silently fails to load — so `alerting_fire` won't exist and every alert POST is a no-op. This bit us 2026-06-07 → 2026-07-04 (see Troubleshooting).

## Adding a new appliance alert

1. Confirm the plug exposes a `*_power` sensor and a `switch.*` entity (rename the switch via the entity registry if its friendly name is misleading).
2. POST to `/api/config/automation/config/<id>` with the same shape as `automation.washing_machine_finished`, swapping entity IDs, the spoken message, and the `rest_command.alerting_fire` `title`/`detail` payload.
3. POST to `/api/services/automation/reload` to pick up the new automation without restarting HA.
4. Turn the switch on so the enable-condition is satisfied.

## HA container

HA runs as a manually-managed Docker container on homepi (not Ansible-deployed; only `configuration.yaml` is templated via the `apps/homeassistant` role). Recreate with:

```
sudo docker run -d \
  --name homeassistant \
  --restart unless-stopped \
  --privileged \
  --network host \
  -e TZ=Europe/London \
  --dns 194.168.4.100 --dns 194.168.8.100 --dns 1.1.1.1 \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  -v /home/pi/homeassistant:/config \
  ghcr.io/home-assistant/home-assistant:stable
```

`--dns` is required. Without it the container inherits `/etc/resolv.conf` from the host at run time, which can capture Tailscale nameservers (`100.100.100.100`) that become unreachable if Tailscale later goes down — symptom: TTS silently fails (`Failed to connect. Probable cause: Unknown` in HA error log), metno/Octopus integrations time out, SSDP errors. Explicit `--dns` pins resolvers regardless of host state.

## Matter Server

Matter support is provided by a separate `python-matter-server` Docker container running alongside the HA container on homepi (HA Container install — no add-ons available).

```
sudo docker run -d \
  --name matter-server \
  --restart unless-stopped \
  --network host \
  -v /opt/matter-server/data:/data \
  ghcr.io/home-assistant-libs/python-matter-server:stable
```

`--network host` is required: Matter discovery uses mDNS / IPv6 multicast.

The Matter integration in HA is configured to talk to it at `ws://localhost:5580/ws`.

### Adding a Matter device

1. Put the device into commissioning mode (or, if already paired to another fabric e.g. Google Home, use that platform's "Link to another Matter platform" / "share to" flow to generate an 11-digit pairing code).
2. In HA: Settings → Devices → Add → Matter → enter the pairing code.
3. Phone must be on the same WiFi as the device, with Bluetooth on, within a few metres.

Multi-fabric sharing from Google Home can be flaky ("Can't set up device" with no detail). Common fixes: force-close Google Home, toggle Bluetooth, retry, or long-press the device button to force commissioning mode. If it persistently fails, factory-reset the device and pair to HA first using the QR code printed on the device, then share back to Google Home — but only if you still have access to that QR.

## Renaming an entity

Entity-id renames need the WebSocket API (REST does not expose this):

```
{"type":"config/entity_registry/update",
 "entity_id":"<old_entity_id>",
 "new_entity_id":"<new_entity_id>",
 "name":"<friendly name>",
 "icon":"mdi:..."}
```

Send after the `auth_ok` handshake.

## Troubleshooting

### Laundry alerts stopped firing (2026-06-25 → 2026-07-04)

Two independent faults, either of which alone silences laundry alerts:

1. **Zigbee coordinator dropped off USB.** At 2026-06-25 09:30 UTC the HA log showed
   `bellows … Fatal write error on serial transport … write failed: [Errno 19] No such device`
   and every ZHA entity went `unavailable`. Root cause: **Pi undervoltage** — `vcgencmd
   get_throttled` read `0x50005` (bit 0 = under-voltage now, bit 16 = has occurred) with
   thousands of `Undervoltage detected!` lines in dmesg. The CP210x dongle browned out and
   left the USB bus; `lsusb` and `/dev/ttyUSB0` showed nothing. Re-plugging did not help
   while power was still sagging. **A reboot re-enumerated it** (same path `/dev/ttyUSB0`,
   stable id `usb-Itead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_V2_...`) — but the real fix is a
   **new PSU + good USB-C cable**. Until `get_throttled` clears bit 0, expect repeat dropouts.
   Consider a powered USB hub so the dongle isn't on the Pi's rail.
2. **`rest_command` broke on 2026-06-07** — config used the deprecated `payload_template`
   key (now `payload`), so the `rest_command` domain failed validation and `alerting_fire`
   never registered. Even after Zigbee recovered, alert POSTs were no-ops until this was
   fixed. See `rest_command.alerting_fire` above.

**Fast diagnosis checklist when laundry (or any ZHA) alerts go quiet:**
- `curl .../api/states/sensor.washing_machine_power` → `unavailable`? Coordinator is down.
- On homepi: `vcgencmd get_throttled` (want bit 0 clear), `lsusb | grep 10c4`, `ls /dev/ttyUSB*`.
- `docker logs homeassistant 2>&1 | grep -iE "rest_command|Invalid config"` → catches the payload-key regression.
- `automation.zigbee_coordinator_offline_watchdog` now pages if the sensors stay `unavailable` 15 min.
