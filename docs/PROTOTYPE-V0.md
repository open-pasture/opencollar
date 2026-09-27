# Prototype V0

Goal: draw a boundary in openpasture, send it to a collar built from off-the-shelf parts, walk across it, hear the collar respond, and see the event recorded.

## Bring-up checklist

- [x] Parts laid out, photographed, BOM recorded
- [x] Voltages and logic levels checked (VIO 3.3V, charger 4.2V/100mA; battery polarity still pending)
- [ ] SIM activated
- [x] MCU: our firmware boots and logs over serial
- [x] GPS: first fix, time-to-fix and accuracy recorded (cold start ~3 min in open sky, 2.2 m)
- [ ] Buzzer: warning tone from code
- [ ] Cellular: registered on network, JSON POST to test endpoint
- [ ] Battery: runs on battery, voltage read over ADC
- [ ] Geofence: boundary from the console or a bench boundary, inside/near/outside, cue on near
- [ ] Telemetry: periodic POST to openpasture
- [ ] Boundary download: fetch by version over LTE (store in flash and ack are done in 0.2, waiting on the SIM)
- [ ] Walk test: cue position vs. true boundary logged

## Firmware

`firmware/`, built on the nRF Connect SDK (Zephyr) for `nrf9151_connectkit/nrf9151/ns`. Version 0.2 speaks protocol v1 (`protocol/README.md`).

| File | Role |
| --- | --- |
| `src/main.c` | Starts the modem in GNSS-only mode, 1 Hz fixes, feeds each fix and each console line to `app.c`, plays cues, logs every decision over serial |
| `src/app.c` | The collar without Zephyr: boot from flash, GNSS time as the only clock for activation, ticks slots on fixes, console commands |
| `src/geofence.c` | Outer ring plus up to 16 holes (384 vertices) in local metres; signed distance to the nearest edge and its ring; inside / warning / outside with hysteresis; ignores fixes worse than 10 m |
| `src/cue.c` | Only cues a crossing (holes included): unarmed at boot and after each new boundary until an inside fix. Warning-zone beeps get louder toward the edge; outside tone for 10 s after a crossing; 20 s max continuous cue then 30 s rest. Cue kinds, track mode, episodes |
| `src/shape.c` | The twelve shape rules, in openpasture's order and math |
| `src/command.c` | Signed commands: top-level span scanner, canonical bytes into SHA-512, Ed25519 (Monocypher), exact decimal to e7 |
| `src/config.c` | Signed config: herd, cadence, fast mode until a GNSS time, endpoint switch with 24 h fallback |
| `src/slots.c` | Active and staged boundaries (16 slots, 24 KB), records with CRC in flash |
| `src/acks.c` | Acks waiting to go up, kept over reboots |
| `src/provision.c` | The card payload typed on the serial console |
| `src/store.h`, `src/store_nvs.c` | Persistence by id on Zephyr NVS (64 KB `storage` partition) |
| `src/console.c` | One line at a time from the USB serial port |
| `src/buzzer.c` | Qwiic Buzzer I2C driver |
| `src/boundary.h` | Bench boundary from `boundary_local.h` (gitignored), only with `CONFIG_OPENCOLLAR_BENCH_BOUNDARY=y` |
| `third_party/monocypher/` | Monocypher 4.0.2 (CC0 or BSD-2-Clause) |
| `tests/host/` | Tests per module that run on a laptop, including the shared protocol vectors: `make -C firmware/tests/host` |

Build: `nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- firmware/build.sh` (prints the partition map and checks the image size). Flash: `firmware/build.sh flash`.

Defaults: warning zone 5 m, hysteresis 1 m, 1 Hz fixes, report and poll every 60 s.

Set up a collar: open the USB serial port (115 200 baud) and paste or scan the card: `provision {"v":1,...}`. `status` shows the collar, herd, firmware, config version and the slots it holds. Until the SIM is in, a signed boundary command can be pasted too: `boundary {...}`.

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
