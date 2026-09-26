# OpenCollar V1 design

The best-value virtual fence collar: nothing extra, every part engineered properly.

## Principles

1. **Delete parts.** No base station, no wires running through the strap, no charging by the farmer, no app needed to set up. Every part we remove is a part that can't fail in a pasture.
2. **Position is the product.** A fence is only as good as the fix. We spend our engineering there first.
3. **The fence works with no signal.** Boundary logic runs on the collar. The network is for reporting and updates, never for containment.
4. **Serviceable, not disposable.** Sealed with gaskets, not potting. The strap, bottom module, battery and electronics can each be replaced on their own.
5. **Open.** Off-the-shelf parts, published design files, open device API. Anyone can build software for it or repair it.

## What it has to beat

From FCC teardowns and a published field study (`research/virtual-fence-gnss.md`):
- Commercial collars use u-blox single-band L1 receivers (Halter P5: M10; Vence: M8) with 18–25 mm patch antennas.
- Nofence measured **5.4 m accuracy error in the open and 7.6 m under forest**.
- Weight: Monil 1.0 kg, Nofence 1.3 kg, Halter ~1.4 kg.

## Targets

| | Target | Market today |
| --- | --- | --- |
| Accuracy error, open pasture | **≤ 2.5 m** (CEP50) | ~5.5 m |
| Accuracy error, under canopy | **≤ 4 m** | ~7.6 m |
| Fix availability when requested | **≥ 99 %** | Not published |
| Fix after sleep (hot start) | **≤ 2 s** | Not published |
| Runs with no sun | **≥ 60 days** | Varies |
| Maintenance | **None for a season**; no charging | Solar models similar |
| Total weight | **≤ 1.2 kg** | 1.0–1.4 kg |
| Setup per collar | **< 2 minutes**: scan, strap on, done | |
| Design life | 5 years, battery 2,000+ cycles | |

## Layout

```
            ┌──────────── solar ────────────┐
            │  panel  │ GNSS │  panel       │   top unit, sits on the neck
            │ (left)  │patch │  (right)     │   (everything electronic is here)
            └─────────┴──────┴──────────────┘
           /                                  \
   strap  |           50 mm polyester          |  strap, no wires inside
           \                                  /
                  ┌──────────────────┐
                  │   bottom bay     │   swappable module: ballast, camera,
                  └──────────────────┘   later battery (see BOTTOM-BAY.md)
```

**One sealed top unit, one swappable bottom module, nothing electrical in the strap.** The bottom needs mass to keep the GNSS antenna facing up, so instead of a dead counterweight the bottom is a **bay** that takes interchangeable modules within a fixed mass window: plain ballast by default, a camera on a few collars, an extra battery later. Modules are self-contained and talk to the top unit over Bluetooth LE if they need to, so no cable ever runs through the strap. Commercial collars that wire a bottom battery to the top add a cable that flexes thousands of times a day on a moving animal; we don't. Details in `BOTTOM-BAY.md`.

The GNSS patch sits at the crown of the top unit with nothing over it. The solar panels sit on the two sloped faces either side, like Nofence, so the panels never shade the antenna.

## Components

| Function | Part | Why |
| --- | --- | --- |
| **GNSS** | u-blox **MAX-M10S** | Same u-blox M10 generation Halter ships, but as a pre-tested module with a built-in LNA and SAW filter. Tracks GPS + Galileo + BeiDou + GLONASS with SBAS. < 25 mW tracking, low-power (LEAP) mode. |
| GNSS upgrade path | u-blox **MAX-F10S** (L1 + L5) | Same MAX form factor. If the dual-band tests win, it drops onto the same pads (confirm pin compatibility before layout) with a dual-band antenna. |
| **GNSS antenna** | 25 × 25 mm ceramic patch on a ≥ 60 mm ground plane, at the crown | Matches Nofence's patch but with a cleaner sky view and more ground plane. Kept away from the LTE antenna and the battery. |
| **Processor + cellular** | Nordic **nRF9151** SiP | Runs the firmware, LTE-M with NB-IoT fallback, and satellite NB-IoT (NTN) as a future option. Monil uses its predecessor. We already have firmware running on it. Its built-in GNSS stays available as a backup receiver. |
| **SIM** | Soldered eSIM (MFF2), multi-carrier | No SIM tray to corrode or shake loose. Roams to whichever carrier is strongest at the farm. |
| **Cellular antenna** | Flexible LTE antenna along the far edge of the top unit | Away from the GNSS patch |
| **Motion** | 6-axis IMU (ST LSM6DSV16X or Bosch BMI270) | Wakes GNSS on movement, slows fixes when the animal is lying down, fills short GPS gaps, logs collar rotation |
| **Storage** | 16 MB SPI NOR flash | Weeks of offline telemetry, firmware update images, event logs |
| **Audio cue** | Sealed piezo transducer, ~95 dB, behind an acoustic vent membrane | Loud, waterproof, no moving parts |
| **Battery** | 2 × 26650 **LiFePO4** in parallel (~22 Wh, ~170 g) | LiFePO4 over Li-ion: much safer in summer sun on an animal, 2,000+ cycles, flat voltage. |
| **Solar** | 2 × ~0.8 W ETFE-laminated monocrystalline panels (≈ 1.5 W total) | ETFE survives UV and scratching; glass doesn't belong on a cow |
| **Charger** | TI **BQ25798** | MPPT solar charging, supports LiFePO4, stops charging below 0 °C (LiFePO4 must not charge when frozen) |
| **Fuel gauge** | Coulomb counter (e.g. MAX17260) | Real state of charge. LiFePO4's flat voltage makes voltage-based estimates useless. |
| **Power on** | Hall-effect sensor | Ships asleep. A magnet wakes it: no switch, no hole in the case. |
| **Status** | One LED behind a light pipe | Confirms power-on, network and GNSS fix at setup |
| **Service** | Pogo-pin pads under a screw cap | Debug and recovery flashing. Normal updates go over the air. |
| **Extension connector** | Sealed 4-pin connector on the top unit (blanking plug on base collars), plus power-path circuitry for an external LiFePO4 pack | Makes the Battery Extension a field upgrade instead of a new collar (see `BOTTOM-BAY.md`) |
| **Bluetooth LE** (V1-beta) | Small BLE chip, e.g. Nordic nRF54L15 | Controls a camera module (Open GoPro API), identifies the fitted bay module, shelter beacons, phone setup |

### Electric pulse

Every commercial collar escalates from audio to a mild electric pulse, and containment depends on it. V1 ships **audio-first** while we validate position and behaviour at the pilot farm with his existing fence as the backstop. The top unit reserves space, electrode openings on its underside (resting on top of the neck) and a connector for a stimulus board, so adding it is fitting a board, not a redesign. It lives in the top unit, not the bottom bay, so every collar can enforce whichever module is fitted. It goes in once we have the welfare logic and field data to do it responsibly.

## Energy budget

| Load | Average |
| --- | --- |
| GNSS (adaptive: 1 Hz near the fence, every few minutes deep inside, off when lying down) | 5–10 mW |
| Cellular (LTE-M in power-saving mode, report every 5–15 min) | 2–4 mW |
| Processor, IMU, flash, sleep | ~0.5 mW |
| **Total** | **~10–15 mW ≈ 0.25–0.35 Wh/day** |

- **With no sun at all:** 22 Wh ÷ 0.35 Wh/day ≈ **60+ days**.
- **Solar:** 1.5 W × ~2.5 winter sun-hours in Tennessee × 50 % losses (angle, dirt, the animal shading itself) ≈ 1.9 Wh/day. That's about 5× what the collar uses in the worst month.
- To verify with the Power Profiler Kit before committing the battery size.

## Weight

| | |
| --- | --- |
| Top unit (electronics, battery, panels, shell) | ~450–550 g |
| Bottom module (ballast or camera) | ~450–650 g |
| Strap and buckle | ~100 g |
| **Total** | **~1.05–1.25 kg** |

## Enclosure

- **Pilot build:** printed by the fabrication partner in a tough, UV-stable material (ASA, or MJF PA12 dyed and UV-coated). Silicone O-ring seal, stainless screws, and a Gore-style vent to stop pressure changes pumping water past the seals.
- **Production:** injection-moulded PC/ASA. The pilot shell is designed with draft angles and wall thicknesses that carry over to moulding.
- **Tests before cattle:**
  - Submersion (IP67: 1 m for 30 min).
  - Drop onto concrete from 1.5 m.
  - 60 °C in direct sun.
  - −20 °C cold soak.
  - Rubbing against a post.
  - Pressure washing.
- **Strap:** standard 50 mm cattle neck belting with a buckle, replaceable without tools.

## Cost (rough, 20-unit pilot)

| | |
| --- | --- |
| nRF9151 SiP | $25–30 |
| MAX-M10S | $15 |
| Antennas (GNSS + LTE) | $10 |
| IMU, flash, fuel gauge, charger, power, piezo, eSIM | $20 |
| Battery (2 × LiFePO4 26650) | $12 |
| Solar panels (2) | $15–20 |
| PCB + assembly | $30–40 |
| Printed shell, gaskets, vent, hardware | $40–70 |
| Strap, buckle, bay cradle, ballast module | $20–30 |
| **Total** | **~$190–260** per collar at 20 units |

Target at volume: under $120. Plus data: LTE-M at a few KB per report is about $1–2/month.

## How we get there

1. **V1-alpha: dev boards in a real shell** (now).
   - nRF9151 Connect Kit + SparkFun MAX-M10S + IMU + solar charger + battery, in a printed top unit with a bottom bay (ballast module, plus one GoPro camera module) on a real strap.
   - Validates the layout, GNSS performance against V0, the energy budget and the firmware.
   - 3 units. Walk tests, then worn by a person, then on a cow alongside the pilot farm's fence.
2. **V1-beta: one custom board.**
   - The same parts on a single 4-layer board shaped to the shell, factory-assembled (e.g. JLCPCB).
   - 10–20 units.
   - Firmware is the same as alpha.
3. **Pilot at the pilot farm.**
   - Passive tracking first, then audio cues, with his current system as the backstop.
   - Measure fix availability, accuracy, battery and durability against the targets above.
4. **Freeze V1.**
   - Publish the BOM, board files, shell, firmware and API.
   - Then add the stimulus module.

## What makes it better than the others

- **Position:** four constellations, a clean antenna placement and more ground plane, IMU-aided filtering and strict accuracy gating before any cue. Target is half the real-world error of today's collars, with a dual-band upgrade ready if the tests justify it.
- **Reliability:** no base station, no cable in the strap, no SIM tray, no charging. LiFePO4 for safety and life. Fence logic keeps working without signal.
- **Openness:** the only collar with published hardware, firmware and an open device API. Farmers can repair it, and any software can drive it.
