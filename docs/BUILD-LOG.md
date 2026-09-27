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

### Firmware 0.2: protocol v1 (branch `fr/ef`)
- **Scope:** the collar side of protocol v1 as rewritten in `protocol/README.md`: holes (up to 16, 384 vertices), shape rules, signed boundary and config commands, staged boundaries in flash, provisioning from the collar's card over the USB serial port. Boundary download over LTE waits for the SIM; the same code path takes a signed command pasted on the console.
- **Baseline first:** the unchanged firmware builds at 68 800 B flash, 20 640 B RAM. Run as `nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh`, west can't find the SDK outside its workspace ("unknown command build"), so `build.sh` now sets `ZEPHYR_BASE=/opt/nordic/ncs/v3.4.1/zephyr` when it is unset and that directory exists.
- **Modules** (`firmware/src/`), all plain C except `main.c`, `console.c` and `store_nvs.c`, so they run in host tests:
  - `shape.c`: the twelve rejection codes in openpasture's order. Crossings and containment exact on e7 integers (int64 products compared, never subtracted); areas and gaps in single precision about the outer ring's first vertex, in the same order of operations as `op_geo::shape`. Built with `-ffp-contract=off`; the ARM build has no fused multiply-add instructions in the app (checked with objdump).
  - `geofence.c`: outer ring plus holes, distance to the nearest edge of any ring and which ring, box shortcut for far holes. The V0 API and tests are unchanged.
  - `cue.c`: cue kinds (`warn`, `outside`), track mode (fence runs, nothing sounds), episodes (`turned_back`, `crossed`, `rest`, `boundary_changed`).
  - `command.c`: records up to 16 top-level spans, sorts them, streams the canonical bytes into SHA-512 and checks Ed25519 with Monocypher 4.0.2 (`third_party/monocypher/`, CC0 or BSD-2-Clause, SHA-512 of the release tarball matches the published one). Coordinates go to e7 integers exactly from the decimal text.
  - `config.c`: signed config (herd, cadence, fast mode until a GNSS time, endpoint trial with a 24 h fallback), NVS id 3.
  - `slots.c` + `store.h`/`store_nvs.c`: 16 slots and 24 576 slot bytes on NVS (ids 0x100 + i), 192-byte header + 8 B per vertex with a CRC-32. A new record is always written before the ones it replaces are deleted, and boot tidies up after a cut. `acks.c`: acks waiting to go up, NVS id 2.
  - `provision.c`: `provision <card payload>` checks each field and stores the payload in NVS id 1; slots, config and pending acks are wiped first.
  - `app.c`: everything wired together. GNSS UTC from fixes is the only clock for activation, carried forward on the uptime counter between fixes. No boundary means no fence and no cues; the compiled-in example boundary is gone. A bench boundary loads as version 0 only with `CONFIG_OPENCOLLAR_BENCH_BOUNDARY=y` (default n) and `src/boundary_local.h`.
  - `main.c`: boot from flash, fixes and console lines on the main thread (`k_poll`), so Ed25519 runs on the 8 KB main stack.
- **Console commands** (115 200 baud): `provision <payload>`, `status`, `boundary <command>`, `config <command>`. No echo, so a pasted 12 KB command isn't slowed down.
- **Logging is now deferred** (was immediate): immediate mode holds interrupts off while each line prints, which would drop bytes of a long command arriving on the same port.

### Vectors and host tests
- The five vector files are copied byte-identical from openpasture tag `fr-w0` (`crates/op-protocol/tests/vectors/`, read from the integration worktree) into `firmware/tests/host/vectors/`. SHA-256 prefixes: commands `70aae176bce665a7`, config `51a6789c9a74e28d`, geofence `3bd4cb46e1bc260d`, shapes `6f0fbadbe45a7e29`, slots `4d2018eb54d91794`.
- `make -C firmware/tests/host` builds one binary per module (`-Wall -Wextra -Werror`) and all pass:
  - geofence: the V0 tests unchanged; margins around and inside holes, concave hole, nearest ring; `geofence.json` 20 cases within 1 mm; 384 vertices in 9 rings: ~500 ns per fix on the Mac.
  - shape: `shapes.json` 46 cases, every code covered; exact decimal to e7 (`1e-7`, halves away from zero, 180.00000001 out of range).
  - command: `commands.json` 36 cases, canonical bytes identical for every valid case; UTF-8, escapes, surrogates.
  - config: `config.json` 17 cases; fast mode ends at `fast_until` by GNSS time; endpoint kept after a successful report, back to the previous one after 24 h of failures, the trial surviving a reboot.
  - slots: `slots.json` 12 cases through the real flash path (every step followed by a reload from the store that must give the same state; `boot` steps reload for real); record round trip; every flipped byte of a 3 264-byte record is caught.
  - store: a power cut after every byte of an immediate insert (3 279 bytes written), a staged insert (298) and a tick applying a staged boundary (266) always leaves the old state or the new one; bad CRC, unknown format and wrong size are ignored; an empty store gives no fence and no cues.
  - cue: the V0 tests unchanged; kinds, each episode outcome, track mode silent, walking into a hole is a crossing, a hole drawn on an animal stays silent until it is clear.
  - provision: a valid payload is stored and wipes the slots; each bad field gives its `error <code>`.
  - app: end to end, including a staged boundary applied by the first fix after a reboot and a collar-scoped track-mode boundary with holes.
- Changing one expected result in each vector file (a scratch copy) makes the matching test fail, so the tests do compare against the files.

### Build
- `nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh`, clean build, no compiler warnings.
- **Application image 115 300 B (112.6 KB)**, limit 440 KB. **RAM 73 776 B (72.0 KB) of 211 608 B**, 134.6 KB free. The new RAM: both fences 13.6 KB, e7 scratch 3 KB, slot headers 3.7 KB, receive/line buffer 12.3 KB, record buffer 3.3 KB, pending acks 2.7 KB, config and provisioning 2.8 KB, main stack 4 → 8 KB, deferred log buffer and thread 6 KB.
- Worst stack on the main thread (GCC `-fstack-usage`, `-Os`): about 2.5 KB for a signature check (`crypto_eddsa_check_equation` 1 088 B), about 1.5 KB for shape checks and applying a boundary.
- Partition map, printed by `scripts/check_image.py` after every build, every edge on a 32 KB SPU boundary:
  - `0x00000-0x08000` TF-M (32 KB)
  - `0x08000-0xF0000` application (928 KB)
  - `0xF0000-0x100000` storage (64 KB, was 32 KB at 0xF8000)
- `CONFIG_NVS_INIT_BAD_MEMORY_REGION=y`: the new storage area was part of the application area, so NVS formats it if it finds old bytes there.
- Not flashed in this step (the board may be in use). On the next flash: paste a card payload, check `status`, and check the boot log says "No boundary: no cues".
- Open: LTE wiring (report, ack and boundary download over HTTP) once the SIM is in; the position report serializer; the console keeps the UART receiver on, which costs power on battery (the production board should enable it only with USB present).

### Herd change drops the old herd's staged boundaries (branch `fr/fx-fw`)
- **Problem (field-ready review):** a signed config naming another herd only changed the herd that new boundaries were checked against. Staged boundaries already accepted for the old herd stayed in the slots and on flash, and `slots_tick` applied them when due, with no herd check, as did boot. A collar moved from herd A to herd B, holding herd A's 07:00 strip and out of coverage before herd B's boundary arrived, applied herd A's strip at 07:00. The kept slots also kept `have` above herd B's boundary, so herd B's active version below it came back `stale`.
- **Reproduced first:** `test_herd.c` (new) signs boundary and config commands with the vectors' key and drives the app. Before the fix, herd A's v13 applied at 12:00 after the config naming herd B, the reboot re-enforced it, and herd B's v12 was rejected `stale`. `local/slots.json` (new, the vectors' format) failed at the `set_herd` step with `have` 13 instead of 10.
- **Fix** (`slots.c`): `slots_set_herd` drops every staged slot whose `herd_id` isn't the new herd, from RAM and flash, with no ack. The active boundary stays in force until one of the new herd applies. `slots_load` does the same after picking the active record, which covers a power cut after the config is stored and before the deletes (`app_config` stores the config first, then sets the herd). Slots without a `herd_id` stay, as insert accepts them in any herd.
- **Spec** (`protocol/README.md`): herd change bullet under Slots; `herd_id` in the config points to it. `wrong_herd` is now permanent only until the collar's config version goes up. A boundary of the new herd fetched before the config arrives is refused `wrong_herd`, and the server has to offer it again after the config. The server side is being changed in openpasture in parallel.
- **Tests**, `make -C firmware/tests/host`, 10 binaries, all pass:
  - slots: `vectors/slots.json` 12 cases unchanged. `local/slots.json` has 2 cases: the herd change drops staged, and the collar's own herd's staged slots are kept, including a move there and back. The vector runner takes a `set_herd` step and reloads each step's state with the herd set first, as `app_boot` does. Two more tests: a staged slot without `herd_id` survives a herd change, and a boot in the new herd drops the old herd's staged record from flash and still enforces the old active one.
  - herd: the story above now passes. Herd B's v14, refused `wrong_herd` before the config, is applied when offered again; herd B's v12 is applied; herd A's v13 is `wrong_herd`. With the power cut after every byte of the change (636 bytes written), the result is always the old state (herd A, slots 10 13) or the new one (herd B, slots 10), with v10 enforced: 631 old, 6 new.
  - Taking the prune out of `slots_load` makes the slot boot test fail, so that test depends on it.
- **Build:** clean, no compiler warnings. Application image 115 396 B (112.7 KB, +96 B) of 440 KB; RAM 73 776 B, unchanged. Not flashed.
