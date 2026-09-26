# Build log

## 2026-09-25

- All prototype parts delivered.
- Repo created. Next: lay out parts and photograph them for the BOM.
- Parts laid out and photographed (`hardware/photos/2026-09-25-parts-layout.jpg`). BOM recorded.
- The nRF9151 Connect Kit does MCU, cellular, and GPS on one board, so the only external module is the Qwiic buzzer (I2C). The kit also has an onboard LiPo charger.
- Gaps found: no SIM yet; no way to connect the buzzer with the jumpers on hand (needs a Qwiic-to-jumper cable or headers soldered on).
- Board powered over USB-C from the Mac. All LEDs green. Enumerates as `Makerdiary IFMCU CMSIS_DAP` with two serial ports:
  - `/dev/cu.usbmodem2101`: nRF9151 running Nordic Modem Shell (`mosh:~$`). Factory firmware.
  - `/dev/cu.usbmodem2103`: interface MCU shell (`ifsh:~$`) with charger, SIM detect, VIO, reset, and UF2 bootloader commands.
- Modem: nRF9151-LACA, modem firmware `mfw_nrf91x1_2.0.4`. System mode LTE-M + NB-IoT + GNSS.
- IFMCU firmware v2.0.0 (NCS 3.3.99, built 2026-06-19).
- VIO is 3.3V (buzzer needs 3.3V).
- SIM detect: uninserted, as expected.
- Charger (BQ25180): regulation 4200 mV, fast charge 100 mA, input limit 500 mA. Safe for the 1200 mAh LiPo (~0.08C). Battery still not connected; polarity not checked yet.
- GNSS LNA enable (`AT%XCOEX0`) already set for 1565–1586 MHz by factory firmware.
- First GNSS test, indoors on the desk, cold start, GNSS-only mode (`AT+CFUN=31`): no fix after ~170 s. Satellite 19 was tracked intermittently at C/N0 24–35 dB-Hz, so the antenna → LNA → receiver chain works. A fix needs 4+ satellites, which means a window or going outside.
- **First GPS fix.** Cold start, GNSS-only mode, no assistance data.
  - Garage with the door open: only 1–3 satellites usable. Not enough.
  - Antenna moved into open sky: fix about 3 minutes later (318 s since GNSS start). Accuracy 5.9 m at first fix, settling to **2.2 m** within about a minute. HDOP 1.6, 5–10 satellites in fix, strongest C/N0 42–44 dB-Hz.
  - Takeaway: the antenna needs a clear view of the sky, which it will have on a collar. Cold starts take minutes; A-GNSS over LTE will cut that to seconds once the SIM is in.
  - Exact coordinates deliberately not recorded here (home location, public repo).
- Firmware research done. Decision: write our own firmware on the nRF Connect SDK.
  - OpenFence (GPL-3.0, 2016): no code taken. Its geofence uses float lat/lon, clamps segments incorrectly, and has no warning zone or hysteresis. Ideas kept for later: volume rising with depth, directional cues, silence when the animal turns back, wake on motion, report-on-move.
  - Makerdiary board files (Apache-2.0) vendored into `firmware/boards/`. Build target `nrf9151_connectkit/nrf9151/ns`, flash with pyOCD over the onboard CMSIS-DAP.
  - Nordic Asset Tracker Template is the reference for the later modular structure (network, location, cloud, storage, FOTA over zbus).
  - Qwiic Buzzer register map taken from SparkFun's MIT-licensed library.
- **Battery connector:** the board's socket (J2) is **MX1.25-2P (1.25 mm pitch)**, not JST-PH 2.0. Check that the LiPo plug physically matches and that red goes to `+` on the silkscreen before connecting.
- Geofence engine (`firmware/src/geofence.c`) and cue policy (`firmware/src/cue.c`) written as plain C with host tests. All pass (`make -C firmware/tests/host`).
- nRF Connect SDK v3.4.1 installed via `nrfutil sdk-manager` (in `/opt/nordic/ncs`). Build with `nrfutil sdk-manager toolchain launch --ncs-version v3.4.1`.
- Factory nRF9151 flash backed up to `~/opencollar-backups/factory-nrf9151-flash.bin` (1 MB, via pyOCD) before flashing.
- **First flash of our firmware.** Attempt 1 crashed with a BusFault: the factory TF-M/bootloader was still at 0x0 and our image used the board's default MCUboot layout. Fixed by using Nordic's no-bootloader partition layout (same as Makerdiary's samples). Attempt 2 boots: TF-M 2.3.1 → NCS 3.4.1 → `OpenCollar V0 starting` → boundary v1 loaded → GNSS started → tracking satellites. Buzzer reports not found (not wired yet), as expected.
- Competitor GNSS research written up in `docs/research/virtual-fence-gnss.md`; V1 requirements and shopping list updated from it.
- Collar protocol drafted in `protocol/README.md`: boundaries down (one ring, 3–64 vertices, versions only go up), acks and position reports up. Fence logic stays on the collar. Transitions and exclusions are handled by the server, so V0 firmware only ever sees a single polygon. Transport (likely CoAP or MQTT over LTE-M, CBOR) not decided.
- Retrieved FCC internal photos with Firecrawl (auto proxy; fccid.io needed a click-through). **Halter P5 uses a u-blox M10 chip (UBX-M10050-KB) + SX1262 LoRa + STM32WBA65. Vence uses a u-blox ZOE-M8B with an ~18 mm patch. Nofence C2 uses a ~25 mm patch on a big ground plane + u-blox SARA-R412M cellular.** Nobody uses L5.
- Nofence field study (doi:10.1186/s40317-025-00417-1): real accuracy error 5.4 m open, 7.6 m forest. That's the bar to beat, not the ±1 m marketing claims.
- Wrote `docs/V1-DESIGN.md`: sealed top unit (MAX-M10S GNSS at the crown, solar either side, nRF9151, LiFePO4 inside), passive counterweight, no wires in the strap. Targets ≤ 2.5 m open / ≤ 4 m canopy, 60+ days without sun, ≤ 1.2 kg.
