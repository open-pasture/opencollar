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
- Adafruit still rejects automated adds; the 9 product tabs are open to add by hand ($99.20).
