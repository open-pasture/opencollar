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
- Replaced the fixed counterweight with a **bottom bay** of swappable modules in a fixed mass window: ballast (default), camera (GoPro mount + power bank as the mass), battery later. No electrical connection through the strap; modules talk over BLE if needed. Pulse module goes inside the top unit so every collar can enforce. See `docs/BOTTOM-BAY.md`.
- Product lineup set: base collar = top unit + plain strap + ballast module. Add-ons: **Battery Extension** (LiFePO4 pack ~45 Wh + powered strap, extends no-sun autonomy from ~60 to ~190 days) and **Camera**. V1 top unit gets the sealed extension connector and power path now so the battery is a field upgrade.
- Changed to a **wired strap on every collar** (one strap, plug-in modules, collar power for the camera). Conditions: collar never depends on it, short-circuit protected port, wires only in the fixed-length strap section, flex-rated wire + IP68 connectors, and V1-alpha straps wired from day one to prove durability.
- Shopping list rewritten in five stages (bench + GPS, power, V1-alpha shells, camera, field). ~$1,800–2,400 total.
- Blender tooling plan in `docs/DESIGN-TOOLING.md`: blender-mcp for live sessions, headless scripts in `mechanical/` as the source of truth, and a six-step self-review checklist. Blender not yet installed.
- Cut to **one collar first**: the built-in GPS and a MAX-M10S log side by side on the same board, so extra kits aren't needed yet. Shopping list down to ~$900–1,200 including the camera.
- Volume cost estimate with pulse module added to `docs/V1-DESIGN.md`: BOM ~$85–115, all-in ~$110–160 per collar at 5,000 units (~$170–270 at 1,000).
- Materials and strap approach in `docs/MATERIALS-AND-STRAP.md`: buy a commercial cattle strap, print only the top unit, bay and modules. ASA (desktop FDM) or PA12 (MJF/SLS) for rigid parts, TPU 95A for clamps and bumpers, bought silicone O-rings. No PLA/PETG. Light colours.
- Wiring on a bought strap: a separate harness, an off-the-shelf high-flex M8 4-pin cordset (robot/drag-chain cable, IP67/68) between panel sockets on the top unit and bay, clipped along the fixed side. 5 V bus either end can supply (BQ25798 dual input + OTG), I2C for module ID/fuel gauge/camera control. Camera module is now Battery + Camera (pack with GoPro mount) so it never drains the fence battery; prototype uses a pass-through power bank.
- Two versions agreed: **DIY** (bought strap + printed parts, unwired; ballast or standalone GoPro+power bank; optional M8 harness) and **sold OpenCollar** (wired strap; supports Battery Extension and Battery + Camera). Same top unit, firmware and bay standard.
- Prototype cart verified and saved to `hardware/prototype-cart.md` (~$916 incl. camera and PPK2).
- Filled guest carts in the T3 browser: Amazon, SparkFun, Adafruit, Pololu, Voltaic, United Lithium, K&J, Heritage (strap; Coburn is dealer-only). DigiKey and TI block automated adds; GoPro and Hologram left to do by hand. Status and DigiKey paste list in `hardware/prototype-cart.md`.
- Parts revenue options in `docs/PARTS-REVENUE.md`: affiliate links earn ~$10–20 per build (SparkFun 10% on Originals, Amazon ~3%, GoPro 3%, Adafruit none); kits ~$100–200 margin each. Recommend both: disclosed affiliate list now, kits after the prototype works.
- Strategy set (`docs/STRATEGY.md`): assembled OpenCollars first; proprietary collar later; open device API always; paid OpenPasture subscription. Permissive licences (Apache-2.0 / CERN-OHL-P / CC BY) so the proprietary collar can reuse open work.
- DIY power path changed to need no software: Adafruit bq24074 solar charger (4.2 V fixed) + protected 6600 mAh Li-ion pack + thermistor. Shipped collars keep LiFePO4 + BQ25798 with charging held off in hardware until configured. Shop build page updated (DIY parts ~$305 without PPK2).
- **Simplified the first build** to what it must prove (GPS, fence/cue, telemetry, physical collar): 6 checkouts instead of 11, ~$260. Switched our prototype to the no-config Li-ion power path (bq24074 + 6600 mAh pack + thermistor); IMU now Adafruit ISM330DHCX; Adafruit 960 reference antenna. Deferred: TI board + LiFePO4, PPK2, camera module, harness, piezo, hall sensor, SPI flash, fuel gauge. Removed cut items from the Amazon cart; DigiKey rows pre-selected for deletion (click Delete). Shop DIY page updated to match.

## 2026-09-26

- **Collar rule: only cue a crossing.** The collar now cues "outside" only when the animal goes from inside (or the warning zone) to outside under the boundary it holds. At boot and after every new boundary the fence is unarmed; the first fix inside the polygon arms it. Unarmed and outside means silent, state `outside`. After a crossing (10 s of outside tone) it disarms, so an animal walking back in isn't cued in the warning zone on the way. 10 s outside limit and 20 s active / 30 s rest unchanged.
  - Why: an audio cue only teaches when the animal can escape it by moving away from the edge. A fence drawn on top of an animal gives no direction, only noise, and cueing an animal that is already out punishes it for coming back.
  - Enables moves as sweeps: openpasture sets a target and sends a series of boundaries whose back edge sits just behind the rearmost animal, so only those animals hear the warning cue and walk forward. The collar needs nothing new for it; each step is a newer boundary.
  - `cue_rearm()` added to `cue.c`; `main.c` applies every boundary through `apply_boundary()`, which calls it. Boundary download over LTE should use the same function.
  - Host tests added: a new boundary that leaves the animal outside gives no cue, walking in arms it, crossing out cues; a new boundary with the animal in its warning zone cues at once. All pass (`make -C firmware/tests/host`). Firmware still builds (NCS v3.4.1, 68.8 KB flash).
  - `protocol/README.md` updated with the rule, `herd_id` in the boundary command (signed by the server; a collar rejects another herd's boundary), and a note on moves. The same rule is ported to openpasture's `op-geo` and its collar simulator.

## 2026-09-26

- **3D design setup.** Blender 5.2.2 installed. MCP for Blender add-on installed and enabled, telemetry off, and registered with Claude Code as the `blender` MCP server (user scope). Live socket test from Python works. 3D Print Toolbox extension installed.
- `mechanical/` pipeline built: `./build.sh` runs each `parts/*.py` in headless Blender and exports STL. It renders front/side/top/bottom/iso views plus a section with cut faces in red, and checks manifold, normals, minimum wall (inward ray cast), size against spec and clearance against reference bodies. Volume and solid mass are reported. Any failure gives a non-zero exit.
- The wall check caught knife-edge slivers inside engraved digits (6, 9, 3 in Blender's font). Labels get an explicit, commented allowance; structure is still checked at 1.2 mm.
- Reference dimensions researched into `mechanical/lib/dims.py` from vendor drawings and board files: nRF9151 kit 55.88 × 20.32, MAX-M10S 38.1 × 30.48, bq24074 38.1 × 33.02, 6600 mAh pack 69 × 54 × 18 / 155 g, P124 panel 113 × 66 × ~3, vent M6 × 0.75 (wall ≥ 4, chamfer to Ø8.6), 2 mm cord groove 2.9 × 1.5 (ERIKS). The strap is **44.45 mm (1-3/4")**, not the 50 mm in the V1 docs. Thickness, several board heights and antenna sizes aren't published; to measure.
- First printable parts for the fabrication partner: `fit_test` (sweeps insert, M3 clearance, O-ring groove and vent tap-drill sizes) and `seal_box` (76 mm box and lid with the top unit's seal: O-ring face groove, 4 M3 inserts, M6 vent; for a 1 m / 30 min submersion test). Both pass all checks.
- Note for the top unit: two P124 panels (113 × 66 each) either side of the GNSS patch make the top unit much wider than the 130 × 90 mm in `MATERIALS-AND-STRAP.md`. Panel choice vs. footprint to decide when the top unit is drawn.
- **Collar V1-alpha, draft 1, designed in Blender** (`mechanical/lib/collar.py`, all checks pass):
  - Top unit 170 × 126 × 55 mm. Base with 13 mm solid walls carrying the O-ring face groove; roof lid with the GNSS patch under a flat crown and a P124 panel recessed into each 18.7° face. The underside is an R300 arch with flat feet at the ends and a strap channel across it; two clamp bars with M3 button-heads grip the strap on the feet.
  - The lid is held by 10 × M3 × 16 screws **from underneath**, so the panels never cover a screw.
  - Inside: the 6600 mAh pack low and central (mass low, on the centreline); Connect Kit, IMU and buzzer on the right; charger and MAX-M10S on the left, all on printed standoffs; 70 × 70 ground plane under the patch; LTE flex on the far end wall; M6 vent in the end wall below the seal.
  - Bay: 104 × 66 cradle with a strap tunnel, plus a ballast module (70 × 46 × 16 steel, ~404 g) on 2 × M3 thumbscrews.
  - Estimated collar ~1.1–1.2 kg: top ~500 g, bay ~540 g, strap ~100 g.
- Assembly (`mechanical/assembly/collar.py`) puts it on a strap around a 25 × 42 cm neck section, saves `collar_v1_alpha.blend` and renders front, side, top unit, exploded, inside, underside and bay views. Loaded into the live Blender session over the MCP add-on's socket.
- `mechanical/package.sh` zips STLs, renders, the .blend and `PRINT-LIST.md` for the fabrication partner: `output/opencollar-v1-alpha-2026-09-26.zip` (20 MB).
- Design issues the checks caught and fixed on the way: the arch feathering to a knife edge at the ends (now steps onto flat feet), clamp bar counterbores breaking out of the bar ends, the insert holes under the panel recesses leaving 0.2 mm, board posts poking into the strap channel, the battery sitting in the thicker floor over the strap, and overlapping battery locators making the mesh non-manifold.
- **Scale and dimension check** of the collar design:
  - Units: the Blender scene is metric, mm, scale 0.001, so 1 unit = 1 mm. Every exported STL was measured from its triangles and matches its design size to 0.01 mm: base 170 × 126 × 24, lid 170 × 126 × 31, bar 12 × 70 × 5, cradle 104 × 66 × 16, module 104 × 66 × 22.
  - Bought parts against vendor sources: the MAX-M10S, bq24074, ISM330 and Qwiic Buzzer outlines and mounting holes match their Eagle board files exactly. The nRF9151 kit (55.88 × 20.32, Ø1.4 holes 1.27 in, 17.80 c-c) matches Makerdiary's dimension drawing. The P124 panel (113 × 66 × 2.8 ± 0.3) and the vent (M6 × 0.75, 7.0 thread, 10 AF / 10.6 AC hex, 12.3 long) match their drawings.
  - Fixed: the panel wire hole was a single Ø5 hole but the P124 has **two 4 × 4 pads at 6 mm pitch**. Now a 14 × 9 slot 17 mm from the +Y edge, centred across the panel so it reaches the pads with either long edge up.
  - Fixed: the clamp-bar screws were M3 × 10 and would have bottomed out in the 6 mm insert hole; now **M3 × 8** (5 mm engaged).
  - Fixed: the thumbscrews only reached 2 mm into the 4 mm insert. The head recess is now 6 deep (4 mm engaged with M3 × 20); screws moved to x ±40 and the steel slab shortened to **64 × 46 × 16 (~370 g)** to clear it. Bay ~505 g, still inside the 450–650 g window.
  - Checked OK: lid screws M3 × 16 (11 mm clamp + 5 into a 6 mm hole); seal box M3 × 8 (2.8 + 5.2 into 6); O-ring groove 2.9 × 1.5 for 2 mm cord (25 % squeeze, 72 % fill).
  - Flagged: the strap loop around the modelled 107 cm neck is 1,156 mm of the 1,219 mm strap, so little is left for the buckle. Measure the pilot animals' necks.
- **PLA quick-look print on the Ender-3 V3 SE** (checks size, fit and layout, not strength). OrcaSlicer 2.4.2 installed. `mechanical/print/` has `orient.py` (writes print-oriented STLs), `flatten_profiles.py` (turns OrcaSlicer's bundled V3 SE / Generic PLA presets into standalone CLI presets with our overrides) and `slice.sh`.
  - Quick-look profile: 0.28 mm layers, 2 walls, 0 % infill, grid supports. Tree supports doubled the time: the underside arch and the inside of the roof both need support.
  - Plates: `OC1_top_base` (base + 2 clamp bars) 4 h 45 m, 114 g; `OC2_top_lid` 3 h 49 m, 108 g; `OC3_bay` (cradle on its side + module) 2 h 10 m, 61 g. About 10.7 h and 283 g PLA in total. All toolpaths sit inside the 220 × 220 bed.
  - With the production-like 0.24 mm / 10 % infill / tree supports settings it was about 24 h and 350 g.

### Carts reset to the prototype list (2026-09-26)
- DigiKey: started a new cart with only the MAX-M10S breakout and the M6 vent ($49.26). The old cart had parts deferred to build two.
- Amazon: only the 5 collar items are selected for checkout ($61.35). Other items in the cart are unticked, not deleted.
- Voltaic: re-added 2 × P124 panels ($28.00). Heritage: strap ($23.10).
- Emptied SparkFun, Pololu, United Lithium and K&J.
- Adafruit: automated adds were silently dropped until Cody created an account and signed in; then all 9 items went in ($98.60).

### Prototype parts ordered (2026-09-26)
Cody placed all six orders: DigiKey, Amazon, Adafruit, Voltaic, Heritage, Hologram. Total $260.31 plus shipping and tax (list in `hardware/prototype-cart.md`).
When the boxes arrive: photograph the parts, check every item against the list, then bench-test power (panels → bq24074 → pack → nRF9151) before anything goes in a shell.

### Board design toolchain installed (2026-09-26)
- KiCad 10.0.6 in `/Applications/KiCad`; `kicad-cli` and a `kicad-python` wrapper (KiCad's bundled Python with `pcbnew`) in `~/.local/bin`.
- Chose **SKiDL** (MIT) for schematic-as-code. Tried atopile first: its command-line tool is in maintenance mode and moving to a hosted app that needs an account, so it was uninstalled.
- `hardware/carrier/` project: a smoke test goes SKiDL → netlist → `.kicad_pcb` → DRC → render, all headless. Works.
- Method written up in `docs/DESIGN-PHASE.md`. Next: the carrier board spec.

### Carrier board spec drafted (2026-09-26)
- `hardware/carrier/SPEC.md` written; waiting on Cody's sign-off before the schematic.
- **Connect Kit pinout** taken from Makerdiary's rev A hardware diagrams and dimension drawing: 2 × 20 pins, 2.54 mm pitch, rows 17.78 mm apart, pin 1 (VBUS) and pin 40 (VIO) 3.81 mm from the USB end. The header has **no battery pin**. The battery reaches the Kit only through J2 (MX1.25) or test pad TP3, so the carrier feeds J2 through a 1.25 mm pigtail. VSYS (pin 2) is an output. The parts photo shows the Kit came with male pins fitted.
- **Charger from TI's BQ2407x datasheet (SLUS810N).** Key finding: VIN-DPM, which stops the charger from collapsing a solar panel, only works in the USB modes (EN2 low). The charger runs in USB500 mode: 500 mA input limit, ISET 887 Ω (1 A programmed, so it's input-limited and the safety timers slow down), TMR 72 kΩ, ILIM 3.24 kΩ fitted (charging is disabled without it), TS straight to the 10K NTC (about 3–47 °C with B3950; no NTC means no charging, fail-safe), CE pulled low, EN1 tied to OUT so it works without the Kit.
- The Kit is powered from bq24074 OUT (4.3–4.5 V, inside J2's 3.6–4.65 V). 3.3 V for every breakout comes from the Kit's VIO (TPS63901, over 400 mA).
- Panels: Voc 7.28 V (P124 datasheet), so the charger input can reach ~8 V when cold. That rules out the 5.5 V ideal-diode chips there. Each panel gets a Schottky; the harness 5 V goes through an LM66100 (off unless firmware enables it) and then a Schottky.
- **Harness port:** 5 V, GND, SDA, SCL in M8 sensor order (1 brown +5 V, 2 white SCL, 3 blue GND, 4 black SDA). 5 V is input-only on this board. I2C goes through a TCA4307 hot-swap buffer (7 V-tolerant pins, stuck-bus recovery, off by default).
- **Buzzer:** keep the Qwiic Buzzer on a 4-pin socket. The MAX-M10S and ISM330 plug into female sockets, not Qwiic, so EXTINT, RESET, PPS, UART and the IMU interrupts reach the nRF. Pin maps read from the SparkFun/Adafruit board files, mating interface only. The ISM330's order comes from its sister LSM6DSOX board: check the silkscreen.
- **Board shape from the shell model:** a 143 × 99 mm ring around a 61 × 75 mm cutout for the pack, board underside at z = 18. The floor is only 0.7 mm below the inner edge, so the bottom side carries only test pads. Lid headroom falls from 52 mm at the crown to 33.9 mm at x = 70, which keeps the MAX-M10S inboard of x = −62. The vent bore needs a notch in the board edge.
- MAX-M10S draws 9.5 + 2.3 mA in continuous tracking (u-blox Table 15). Its TIMEPULSE shares a pin with SAFEBOOT_N, so it must never be pulled low at boot.
- Power budget: ~300 mAh/day known (GNSS dominates) plus unmeasured idle currents (Kit overhead, buzzer, IMU board): ~19 days without sun. Estimated harvest ~700 mAh/day in winter, ~1,400 in summer. The 60-day target needs GNSS power-save or duty-cycling in firmware.
- LCSC checked: BQ24074RGTR C54313, LM66100DCKR C2869734, TCA4307DGKR C880333 (extended parts).
- Open: ring vs. two boards; harness 5 V input-only for alpha; bench checks when parts arrive (pinouts, pull-up and LED jumpers, idle currents, buzzer dB through the shell, heights, pack lead). List in SPEC.md section 11.

### Collar redesign from first principles (2026-09-26)
- Cody wants the collar slim and sleek, as close to Halter's as we can get, designed from first principles rather than around the dev boards. Written up in `docs/COLLAR-FIRST-PRINCIPLES.md`; competitor findings with sources in `docs/research/collar-form-factors.md`.
- Halter, from a 2026 peer-reviewed trial: 488 g on the neck plus a 912 g counterweight, 1.40 kg. The top unit is two side pods joined by a flexible bridge (US design patent USD1089882S), and the counterweight is almost certainly dead mass that also sets the collar size. Nofence C2.5 is a 15.3 × 14.5 × 5.4 cm box at ~1.5 kg with a 72 Wh battery. Monil is a top puck plus a weighted lock, ~1 kg. The P5 FCC exhibits couldn't be reached.
- **Draft 1 fails the stability rule.** Bottom : top is ~1 : 1 (500 g over 505 g) against Halter's 1.87 : 1. Its 170 × 126 × 55 mm size comes from dev boards on standoffs and the 18 mm pack, not from anything the collar needs.
- Derived: only the GNSS patch, panels, LTE antenna, main board (as the patch's ground plane) and piezo need to be on top: ~195–225 g *est*. Every top gram needs ~1.8 g underneath.
- Two layouts compared at the 60-day / ~20 Wh target. **A (Halter's):** battery on top, ~26 mm thick, ~1.18 kg collar. **B:** the battery is the counterweight, with a small buffer cell on top, ~16–18 mm thick, ~0.78 kg collar. Recommended B, gated on the V1-alpha harness durability test. With a cut strap wire, B keeps the fence running on the top's own panels and buffer, and loses only the no-sun reserve.
- Shape: one low puck on the neck crest, ≤ 120 × 80 × 18 mm, ≤ 250 g; the panel bonded in as the lid; the patch beside the panel, not under it; sizing at the bottom module like Halter. Our own look: Halter's shape is design-patented.
- Knock-on: draft 1 becomes the alpha test box; the carrier board becomes a plain rectangle under 100 × 100 mm (spec marked on hold for its outline); the integrated board gets shaped to the puck.
- Open for Cody: layout A or B, keep the 60-day target, carrier as a rectangle, puck vs side pods. Measurements needed: neck circumference and crest curvature on the pilot animals. Next: a cheap rotation test with 225 g on top and 420 g below, on a person first, then a steer.

### Repo published, collar contract moved in (2026-09-26)
- Published at https://github.com/open-pasture/opencollar. This backs up the local history and fixes the 404 behind the "The opencollar repo" button on openpasture.dev/collar/build.
- Checked before pushing: gitleaks 8.30.1 over all 43 commits found nothing, and a manual search for keys, tokens, SIM and Wi-Fi credentials and `.env` files found nothing either. The largest file is the 3.4 MB parts photo (its GPS tags are empty), well under GitHub's limits.
- The partner names already taken out of the docs were also taken out of the older commits, plus one leftover in `docs/BOTTOM-BAY.md`. Messages and dates are unchanged, but commit hashes differ from the old local history. The pre-publish history is kept as a bundle in `output/backups/`.
- The collar server contract, `docs/contracts.md` from the retired agent kit (commit c306c5c), is now `protocol/contracts.md`. `protocol/README.md` points at it and at the Rust app's `crates/op-protocol` and the Device endpoints section of its `docs/API.md`.
- Still missing: licence files. `docs/STRATEGY.md` plans Apache-2.0 for firmware, CERN-OHL-P for hardware and CAD, and CC BY 4.0 for docs. Until those files are added, the repo is all rights reserved by default.

### First-principles decisions and carrier rev A2 (2026-09-26)
- **Cody decided:** the battery is the counterweight (layout B); keep the 60-day no-sun target; the carrier is a plain rectangle; left and right sound cues, as Halter does; design to average neck sizes with adjustment instead of measuring the pilot animals.
- **Why two cues need two places:** cattle's minimum audible angle is ~30° (Heffner & Heffner 1992), so two speakers close together on top of the neck sound the same to the animal. One per side of the neck works. The top becomes a **crest unit** (GNSS, board, panel, buffer cell; ~60 × 130 × 18 mm) plus **two small ear pods** on the strap (a piezo each, pulse electrodes later), ~270 g *est*. Bottom ~505 g, collar ~0.9 kg *est*.
- **Neck:** fit range 75–130 cm (Monil's published range; indigenous Ethiopian cattle average ~70 cm). Design centre ~107 cm on an ellipse ~25 × 42 cm: crest radius ~74 mm, sides ~350 mm. The crest is tight and the sides nearly flat, which is why rigid parts go on the sides and only a narrow unit across the top. Estimates, not measurements.
- **Caught:** adjusting one side only puts the bottom off-centre, and the weight then rotates the top off the crest. Adjust both ends at the bottom module (Halter: "within one hole of each other") and store the harness slack there.
- **Caught:** with the pack under the throat, the charger's thermistor has to come up the harness. The bus changes from M8 4-pin 5 V to **M8 8-pin**: BAT+ ×2, GND ×2, SDA, SCL, NTC, INT (DIN 47100 colours). `BOTTOM-BAY.md` marked superseded.
- **Carrier rev A2** (`hardware/carrier/SPEC.md`): 95 × 75 mm with four M3 holes. The battery and NTC arrive over the harness (J_BAT and J_NTC kept for the bench). The LM66100 5 V input is gone. Two Qwiic cue ports feed the ear-pod buzzers (addresses 0x34 and 0x5B, set in software). Everything leaving the box sits behind a TCA4307 buffer plus a TPS2553 current-limited switch (LCSC C55266) on one EXT_EN line, so a chewed cable can't hang the GNSS/IMU bus and the buzzers draw nothing between cues.
- Alpha test box: board plane raised to z = 20 (a centred board sits over the strap channel), M8 socket, two ear pods, and a bottom module with the pack, a fuse, NTC and ~390 g of steel for ≥ 1.87 : 1.
- To buy when Cody's ready (not ordered): a second Qwiic Buzzer, two long Qwiic cables, an M8 8-pin cordset plus two panel sockets, JST-PH pigtails.

### Carrier schematic and first placement (2026-09-26)
- `hardware/carrier/schematic.py` (SKiDL): one function per block, each citing its datasheet section. Blocks: Connect Kit sockets, Kit battery feed, bq24074 charger, solar inputs, bench battery, ADC sensing, main I2C, GNSS sockets, IMU socket, external bus (TCA4307 + TPS2553), cue ports, harness, ESD, expansion, test pads, holes. The TCA4307 and TPS2553 have no KiCad symbols, so they're defined in the script from their datasheet pin tables.
- **ERC clean.** Netlist checked by hand: 96 parts, 53 nets, no single-pin or duplicated nets. Kit pins land on the right sockets (e.g. PPS on Kit pin 32 = P0.24, both Kit grounds).
- **Parts from JLCPCB's parts search.** Everything is stocked except a 1 × 20 SMD socket (3 pieces of one Samtec part), so each Kit row is two 1 × 10 hanxia 8.5 mm SMD sockets end to end. The bq24074 has only 816 in stock. 887 Ω, 3.24 kΩ and 71.5 kΩ have no Basic part. Full table in SPEC.md section 10.
- Changes on the way:
  - Both panels share one 3-pin PH (the right edge couldn't fit three 2-pin connectors).
  - The MAX-M10S's two holes beside its 8-pin row sit under the SMD socket, so it gets standoffs only on the far corners.
  - The IMU gets M2 standoffs to clear the GNSS socket.
  - The bq24074's thermal-via footprint uses 0.2 mm drills, so it gets four 0.3 mm vias instead (JLCPCB's standard minimum).
- `hardware/carrier/layout.py` (KiCad Python): places the fixed parts at computed positions (Kit rows 17.78 mm apart; breakout sockets at their board-file positions) and packs passives near their block without overlaps. Test pads go on the bottom with ≤ 5-character labels; GND pours on both layers; design rules set for JLCPCB (0.15 mm clearance and track, 0.3/0.6 mm vias).
- **DRC:** the only violations left are the intended end-to-end Kit sockets (2 courtyard overlaps and their silkscreen), plus 142 unconnected items because nothing is routed yet.
- **Caught in my own render review:** the LCSC/MPN fields were printing on the silkscreen over every part (now hidden). The Kit-battery "+ −" label sat over the wrong holes, so the polarity marks are now placed from the real pad positions. The board title covered U5's reference.
- Open before ordering: route (Freerouting still to install, it needs Java). Check the hanxia sockets' pad stagger against KiCad's Pin1Left and that the body is 25.4 mm long. Confirm the bq24074 RGT0016B land pattern.

## 2026-09-27

### Carrier board shrunk to 65 × 62 mm
- Cody saw a lot of wasted space on the 95 × 75 mm layout. The cause: the carrier's own parts sat beside the plugged boards. The Kit, MAX-M10S and ISM330 ride ~11 mm up on their sockets, so the board under them was empty.
- Now the three plugged boards are tiled edge to edge, and every carrier part sits underneath them:
  - Kit down the left edge.
  - MAX-M10S top right.
  - ISM330 below it, turned 180° so its standoffs sit clear of the bottom-edge ports.
  - Under the Kit, between its socket rows: the buffer and switch, pull-ups, dividers, the Kit feed and two board mounts.
  - Under the M10S: the charger. Under the IMU: the ESD parts.
- **65 × 62 mm, 43 % less area.** The limit is the three boards' footprints: the M10S's 8-pin socket can't sit closer to the Kit's right-hand socket, which sets the width.
- Removed to make room:
  - The bench-only battery and NTC sockets. On the bench, a PH8 pigtail into the harness socket does the same job, and two packs can no longer be connected at once.
  - The unpopulated expansion header. The stimulus board belongs to the integrated board, and the spare GPIOs are left unconnected.
- The harness socket is now the right-angle S8B-PH-SM4-TB (LCSC C265121), so the cable enters from the edge.
- The M10S's two far-corner standoffs double as board mounts (M3 male-female standoffs into the box posts). The carrier goes into the box before the plugged boards.
- Silkscreen: the panel socket, turned sideways at the edge, gets its A+ / GND / B+ marks beside each pad, placed from the real pad positions.
- ERC clean; 91 parts, 45 nets. DRC shows only the intended butted Kit sockets, plus 131 unrouted connections. Renders reviewed top and bottom.

### Carrier board to 65 × 58.5 mm; assembled preview
- Cody still saw white space. Most of it was under the plugged boards, which the renders don't draw. `layout.py` now also writes `build/carrier_assembled.kicad_pcb`, a copy with the Kit, MAX-M10S and ISM330 outlined on the silkscreen, to render how it looks fitted. It's not for manufacture.
- The real leftover space was the connector band along the bottom edge (10.3 mm, for the PH harness socket) and the column right of the IMU. The harness socket now sits in that column, on the right edge. The panels moved to a JST-SH 3-pin (SM03B-SRSS-TB, C160403; 1 A per contact, both panels ≤ 0.46 A), so the bottom band only needs an SH socket's 6.6 mm.
- **65 × 58.5 mm**, 47 % less area than the 95 × 75 layout. This is within ~1 mm of the floor for these boards: the Kit's 55.9 mm length sets the height; the Kit, the 4 mm gap its right-hand socket needs from the M10S's socket, and the M10S's 38.1 mm set the width.
- ERC clean. DRC shows only the intended butted Kit sockets, plus the unrouted connections. Renders reviewed: bare top, assembled top, bottom.
