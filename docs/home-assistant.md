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
  - `rest_command.alerting_fire`

| Appliance | Power sensor | Switch (enable) | Automation |
|---|---|---|---|
| Washing machine | `sensor.washing_machine_power` | `switch.washing_machine` | `automation.washing_machine_finished` |
| Tumble dryer | `sensor.sonoff_s60zbtpg_power` | `switch.tumble_dryer` | `automation.tumble_dryer_finished` |

The 3-minute delay avoids false triggers from mid-cycle pauses (rinse, spin-up). The 5 W threshold may need tuning for appliances with higher standby draw.

## Adding a new appliance alert

1. Confirm the plug exposes a `*_power` sensor and a `switch.*` entity (rename the switch via the entity registry if its friendly name is misleading).
2. POST to `/api/config/automation/config/<id>` with the same shape as `automation.washing_machine_finished`, swapping entity IDs and the spoken message.
3. POST to `/api/services/automation/reload` to pick up the new automation without restarting HA.
4. Turn the switch on so the enable-condition is satisfied.

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
