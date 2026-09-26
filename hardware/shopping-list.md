# Shopping list, in stages

Each stage unlocks the next. Prices are rough.

**Strategy: build one good collar first.** One board can run the nRF9151's built-in GPS and a MAX-M10S at the same time, so GPS comparisons happen side by side on a single collar. Buy multiples only when the design is proven and we need units for the pilot.

## Stage 1: unblock the bench and start playing with GPS (order today)

Goal: V0 end to end (GPS → geofence → buzzer → LTE), plus the first GNSS comparisons against the nRF9151.

| Item | Qty | Why | Approx. |
| --- | --- | --- | --- |
| Nano-SIM with LTE-M data (Hologram Hyper or Onomondo) | 1 | Telemetry, boundary download, A-GNSS | $5 + ~$2/mo |
| SparkFun Qwiic Cable, Female Jumper 4-pin (PRT-14988) | 2 | Qwiic breakouts to the nRF9151 header pins | $2 each |
| SparkFun Qwiic cable kit (assorted lengths) | 1 | Chaining GNSS, IMU and buzzer | $10 |
| MX1.25-2P battery pigtails / JST-PH → MX1.25 adapters | 2 | The board's battery socket is 1.25 mm | $8 |
| **u-blox MAX-M10S breakout** (SparkFun Qwiic) | 1 | V1 GNSS candidate, four constellations. Runs alongside the built-in GPS for side-by-side logs | $45 |
| 25 × 25 mm active L1 patch, U.FL | 1 | V1 antenna size, for the M10S | $10–15 |
| U.FL ↔ SMA pigtails | 2 | Swapping antennas between boards | $10 |
| Copper-clad board, ~70 × 70 mm | 1 | Ground planes under the patches | $10 |
| Qwiic IMU (LSM6DSO or ISM330DHCX) | 1 | Motion-gated fixes, rotation logging | $15–30 |
| USB-C data cables | 1 | Flashing and logs | $15 |

**Stage 1 total: ~$150–200**

**Later, only if the M10S isn't good enough:** a dual-band L1/L5 receiver (MAX-F10S / NEO-F10N, $60–90) with a dual-band antenna ($20–40).

## Stage 2: measure power and prove the solar + LiFePO4 power path

Goal: real numbers for the energy budget before the battery is sized.

| Item | Qty | Why | Approx. |
| --- | --- | --- | --- |
| Nordic Power Profiler Kit II (PPK2) | 1 | Current per GPS fix, per LTE report, in sleep | $100 |
| Multimeter (if you don't have a good one) | 1 | Polarity, voltages | $25–40 |
| Solar charger board with MPPT and LiFePO4 support (TI BQ25798 evaluation board or equivalent) | 1 | The V1 charger, on the bench | $50–150 |
| ETFE mini solar panels, 0.8–1 W, ~110 × 70 mm | 2 | Either side of the GNSS patch | $10 each |
| 26650 LiFePO4 cells, 3.2 V ~3.5 Ah | 3 | Two for the top unit + one spare | $6 each |
| 26650 cell holders / nickel strip + small spot-weld kit (or pre-built 2P packs) | 1 | Assembling packs | $30–60 |
| Small LiFePO4 protection boards (1S) | 2 | Safety on every pack | $3 each |

**Stage 2 total: ~$230–350**

## Stage 3: the V1-alpha collar (dev board in a printed shell)

Goal: one wearable collar. Shell printed by our fabrication partner.

| Item | Qty | Why | Approx. |
| --- | --- | --- | --- |
| **Printed parts from our fabrication partner**: top unit shells, bay cradles, ballast module shells, one camera module | 1 set (plus a spare top unit shell) | The enclosure | Filament/resin + printing time |
| Print material: ASA (UV-stable) or PA12, per the printer's capabilities | as needed | Outdoor-rated shells | $40–80 |
| Silicone O-ring cord kit + cyanoacrylate for joining, or pre-sized O-rings once dimensions are set | 1 | Sealing | $20 |
| Adhesive ePTFE vent patches (Gore-style) | 10 | Pressure equalization; acoustic vent for the buzzer | $15 |
| Stainless steel M3 screws + brass heat-set inserts kit | 1 | Assembly | $25 |
| 50 mm polyester webbing + cam/side-release buckles, stainless hardware | 1 collar | Strap | $15 |
| Ultra-flexible silicone wire, 24–26 AWG, 4 colours | 1 set | Wired strap conductors | $20 |
| IP68 4-pin circular connectors (M8 or similar), male + female pairs | 2 pairs + 1 spare | Strap ↔ top unit and strap ↔ bay | $8–15 per pair |
| Steel or zinc ballast blanks, 450–650 g | 1 | Ballast module | $10 |
| Piezo transducer, sealed, ~95 dB | 1 | Louder, waterproof cue (vs. the Qwiic buzzer) | $5 each |
| Neodymium magnet + hall sensor breakout | 1 | Magnet power-on | $5 each |

**Stage 3 total: ~$250–350** (plus printing)

## Stage 4: camera module

Goal: one camera collar for the pilot.

| Item | Qty | Why | Approx. |
| --- | --- | --- | --- |
| GoPro HERO (base model) | 1 | Camera module; open API for later collar control | $200 |
| Compact 10,000 mAh USB-C power bank | 1 | Camera power, doubles as module mass | $25 |
| GoPro two-prong mount buckles + thumbscrews | 1 set | Mount interface | $10 |
| High-endurance microSD card, 128 GB | 1 | Long recordings | $30 |
| Replaceable clear lens protectors | 1 pack | Mud and scratches | $10 |

**Stage 4 total: ~$250–280**

## Stage 5: field testing

| Item | Qty | Why | Approx. |
| --- | --- | --- | --- |
| IP67 project box | 1 | Backpack tests before shells are ready | $20 |
| Waterproof USB power bank | 1 | Long outdoor runs | $40 |
| Handheld GPS or phone with RTK/survey app access, or a known survey marker nearby | 1 | Reference points to measure real accuracy (CEP) against | Varies |

## All stages

**~$900–1,200** for one complete collar with camera, not counting printing or monthly data. More units come after the design is proven, for the pilot at the pilot farm.
