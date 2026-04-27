# Home Assistant

Home Assistant runs on **homepi** (Raspberry Pi 4, 192.168.4.71). It is the central hub for all smart-plug automations, Zigbee devices (ZHA), and Google Home / media-player TTS alerts.

## Access

| | |
|---|---|
| URL | http://192.168.4.71:8123 |
| API token | `super/bin/secrets get /home-automation/ha-claude` |
| Auth | `Authorization: Bearer <token>` |
| WebSocket | `ws://192.168.4.71:8123/api/websocket` (needed for entity registry edits) |

`homepi.local` mDNS is unreliable from `pip` — use the IP, or check pi-fleet.

## Smart plug fleet

Four Sonoff plugs:

| Plug | Type | Location | Purpose | Switch entity |
|---|---|---|---|---|
| Sonoff (WiFi) | WiFi | Lab | Lights East | `switch.sonoff_s60zbtpg` |
| Sonoff (WiFi) | WiFi | Lab | Lights (other) | TBD |
| Sonoff S60ZBTPG | Zigbee (ZHA) | Utility room | Washing machine | `switch.washing_machine` |
| Sonoff S60ZBTPG | Zigbee (ZHA) | Utility room | Tumble dryer | `switch.tumble_dryer` |

The Zigbee plugs expose power/voltage/current/summation sensors used by the appliance-finished automations.

## Appliance-finished automations

Both washing machine and tumble dryer share the same pattern:

- **Trigger** — power sensor below 5 W for 3 minutes
- **Condition** — the plug's switch entity is `on` (used as a manual enable/disable flag — turn it on when you start a load)
- **Actions** —
  - TTS "The X has finished." to `media_player.living_room`, `media_player.kitchen_display`, `media_player.lab_speaker` (via `tts.google_translate_en_com`)
  - `notify.mobile_app_homepi` push notification
  - `rest_command.alerting_fire` with `data: {title, detail, severity?}` (severity defaults to `warn`, so Slack + xMatters both fire)

| Appliance | Power sensor | Switch (enable) | Automation |
|---|---|---|---|
| Washing machine | `sensor.washing_machine_power` | `switch.washing_machine` | `automation.washing_machine_finished` |
| Tumble dryer | `sensor.sonoff_s60zbtpg_power` | `switch.tumble_dryer` | `automation.tumble_dryer_finished` |

The 3-minute delay avoids false triggers from mid-cycle pauses (rinse, spin-up). The 5 W threshold may need tuning for appliances with higher standby draw.

### `rest_command.alerting_fire`

Defined in `homepi:/home/pi/homeassistant/configuration.yaml` (not in git — back up before editing). Templated payload posts to the alerting API Gateway:

```yaml
rest_command:
  alerting_fire:
    url: "https://b5wgk4mp4g.execute-api.eu-west-1.amazonaws.com/alert"
    method: POST
    content_type: "application/json"
    payload: '{"source": "home-assistant", "severity": "{{ severity | default(''warn'') }}", "title": "{{ title }}", "detail": "{{ detail | default('''') }}"}'
```

Callers pass `data: {title, detail, severity?}`. Severity defaults to `warn` (Slack + xMatters); use `info` for non-paging notifications (Slack only).

## Adding a new appliance alert

1. Confirm the plug exposes a `*_power` sensor and a `switch.*` entity (rename the switch via the entity registry if its friendly name is misleading).
2. POST to `/api/config/automation/config/<id>` with the same shape as `automation.washing_machine_finished`, swapping entity IDs, the spoken message, and the `rest_command.alerting_fire` `title`/`detail` payload.
3. POST to `/api/services/automation/reload` to pick up the new automation without restarting HA.
4. Turn the switch on so the enable-condition is satisfied.

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
