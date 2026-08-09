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

## Voice control: decided 2026-08-09 — no HA↔Google bridge

**Where Google Home ends and HA starts** (the `TODO.md` question):

- **Google Home owns voice.** The three Wi-Fi plugs (air shower fans, ×2 lab
  lighting) publish straight to Google via Smart Life/eWeLink. HA is not in
  that chain and doesn't need to be — **lab lighting already has working voice
  control today.**
- **HA owns logic and history.** Zigbee plugs, the Matter plug, sensors,
  power-drop alerts. These have **no voice at all**, and that is accepted.

Verified 2026-08-09: no `google_assistant` and no `cloud` integration is
configured, and `homeassistant.exposed_entities` has `"assistants": {}` —
**zero HA entities are exposed to any assistant.** That is the current design,
not a broken setup.

Bridging HA to Google would cost either a Nabu Casa subscription (~£6.50/mo)
or hours of GCP/OAuth setup plus public HTTPS (the `CLAUDE.md` "Google Cloud
OAuth for Matter switches" TODO). **Decision: not worth it at current usage —
staying as-is.** Revisit only if an HA-owned device genuinely needs voice.

Note: HA's local **Assist** cannot run on Google Home speakers — Google
doesn't permit third-party assistants on them. Local voice would need its own
mic hardware (ESP32-S3 Voice PE, Wyoming satellite). The existing
`mcp_server | Assist` entry is for LLM/agent access, not speaker voice.

### Buttons for lab lighting — use Matter, not Zigbee (2026-08-09)

Wanted: a **physical button** for the lab late at night (no wake word, no
phone, doesn't wake the house) **and** keep voice. Button matters more.

**Zigbee is the wrong choice here.** Moving lab lighting to Zigbee pulls it
into HA, and HA has no voice path (see above) — so it would *trade away* the
Google voice control those plugs have today rather than add to it.

**Matter gives both, with no subscription.** A Matter plug joins Google Home
**and** HA simultaneously (multi-admin, the point of Matter):

- **Voice** — pairs natively to Google Home, local, no Smart Life cloud
- **Button** — also visible in HA, so a Zigbee button in ZHA can switch it
- **No bridge needed** — sidesteps the Nabu Casa / GCP-OAuth decision entirely

Infrastructure already present, nothing to buy beyond the plugs:

- Matter commissioning works headlessly (proven twice, nodes 4 and 7)
- `hci0` BLE on homepi for commissioning
- **Three Google Nest Hubs = Thread border routers** already in the house

**Buy Matter-over-Wi-Fi plugs**, not Thread. `thread_credentials_set` is
`False` on the matter-server, so Wi-Fi Matter works today with zero extra
setup (node 7 is exactly this), whereas Thread would first need credentials
shared out of the Google fabric.

Then add a Zigbee button (ZHA, coordinator already present) bound to the
plug's HA entity. Status: **decided, not yet bought or built.**

### Why the fans are reliable and everything else barfs

Chain length. The air-shower fans are **plug → Smart Life → Google Home**:
three components, one vendor path, no HA. Every layer is a failure point, and
the fans have the fewest.

What "barfs" has more links, or a broken one:

- **Tumble dryer** (Zigbee, ought to be reliable) — `light.lights_east` is a
  `switch_as_x` helper pointing at `switch.tumble_dryer`, so a second entity
  switches the dryer behind your back. Suspected cause of its flakiness; see
  the hardware inventory's Gaps section. **Not yet fixed.**
- **The astro plug** — the Sandstrom was replaced 2026-08-09 for genuine
  unreliability; `eos-power cycle` now verifies via USB re-enumeration rather
  than trusting the plug's ACK.
- **Anything HA-owned** — HA adds container, radio, integration and helper
  layers that the fans simply don't have.

The lesson matches the policy above: **don't add layers to a device that
already works.** Migrate only for a capability you actually need.

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
