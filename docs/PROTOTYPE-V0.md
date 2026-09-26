# Prototype V0

Goal: draw a boundary in OpenPasture, send it to a collar built from off-the-shelf parts, walk across it, hear the collar respond, and see the event recorded.

## Bring-up checklist

- [x] Parts laid out, photographed, BOM recorded
- [x] Voltages and logic levels checked (VIO 3.3V, charger 4.2V/100mA; battery polarity still pending)
- [ ] SIM activated
- [ ] MCU: blink + serial logging
- [x] GPS: first fix, time-to-fix and accuracy recorded (cold start ~3 min in open sky, 2.2 m)
- [ ] Buzzer: warning tone from code
- [ ] Cellular: registered on network, JSON POST to test endpoint
- [ ] Battery: runs on battery, voltage read over ADC
- [ ] Geofence: hardcoded polygon, inside/near/outside, cue on near
- [ ] Telemetry: periodic POST to OpenPasture
- [ ] Boundary download: fetch by version, store in flash, ack
- [ ] Walk test: cue position vs. true boundary logged

## Firmware

`firmware/`, built on the nRF Connect SDK (Zephyr) for `nrf9151_connectkit/nrf9151/ns`.

| File | Role |
| --- | --- |
| `src/main.c` | Starts the modem in GNSS-only mode, 1 Hz fixes, feeds each fix to the geofence and cue policy, logs every decision over serial |
| `src/geofence.c` | Projects the polygon to local metres; signed distance to the edge; inside / warning / outside with hysteresis; ignores fixes worse than 10 m |
| `src/cue.c` | Warning-zone beeps get louder toward the edge; outside tone for 10 s then stops; 20 s max continuous cue then 30 s rest |
| `src/buzzer.c` | Qwiic Buzzer I2C driver |
| `src/boundary.h` | Compiled-in boundary. Real coordinates go in `boundary_local.h` (gitignored) |
| `tests/host/` | Geofence and cue tests that run on a laptop: `make -C firmware/tests/host` |

Build and flash: `firmware/build.sh flash`

Defaults: warning zone 5 m, hysteresis 1 m, 1 Hz fixes.

## Wiring

| Buzzer (Qwiic) | Wire colour on Qwiic cable | nRF9151 Connect Kit header |
| --- | --- | --- |
| GND | black | GND |
| 3.3V | red | 3V3 (VIO set to 3.3V) |
| SDA | blue | P0.30 |
| SCL | yellow | P0.31 |

GPS antenna → `GPS` U.FL. LTE antenna → `LTE` U.FL. Battery → J2 (MX1.25-2P), polarity to be confirmed.

## Known issues

None yet.
