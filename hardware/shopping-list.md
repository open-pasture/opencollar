# Shopping list

## 1. Unblock V0 (order now)

| Item | Why | Approx. |
| --- | --- | --- |
| Nano-SIM with LTE-M data (Hologram Hyper or Onomondo) | Telemetry, boundary download, A-GNSS. Check LTE-M coverage at the pilot farm when choosing. | $5 + ~$1–5/mo |
| SparkFun Qwiic Cable, Female Jumper 4-pin (PRT-14988), x2 | Connects the buzzer to the board's header pins | $2 each |
| MX1.25-2P battery pigtails, or a JST-PH-2.0 → MX1.25 adapter | Board's battery socket is 1.25 mm; confirm the PKCELL plug first | $5–8 |
| USB-C data cable (if needed) | Flashing and logs | $8 |

## 2. Measure what matters

| Item | Why | Approx. |
| --- | --- | --- |
| Nordic Power Profiler Kit II (PPK2) | Measures real current draw per GPS fix, LTE report, and sleep. Battery life estimates are guesses without it. | $100 |
| Multimeter (if you don't have one) | Battery polarity, voltages | $25 |
| 2 more nRF9151 Connect Kits | Side-by-side antenna and placement tests with identical radios; also the first 3-unit field batch | $60–80 each |

## 3. GPS experiments (priority #1 for V1)

Specific receiver and antenna models are pending the competitor research. Categories:

| Item | Why |
| --- | --- |
| Multi-constellation GNSS receiver breakout (GPS + Galileo + BeiDou + GLONASS) | The nRF9151's built-in GNSS only tracks GPS + QZSS. A multi-constellation receiver sees roughly 3x the satellites, which matters most under trees and on hillsides. |
| Dual-band (L1 + L5) receiver breakout and matching antenna | L5 rejects multipath (signals bouncing off the animal, trees, terrain). The main route to sub-2 m without RTK. |
| Larger active patch antennas (25 mm and 35 mm) | A bigger patch with a bigger ground plane gives more signal. Test against the current antenna. |
| IMU breakout (Qwiic accelerometer/gyro) | Motion-triggered fixes (save power when the animal is lying down), dead reckoning through short GPS dropouts, and detecting when the collar has rotated. |

## 4. Field test gear

| Item | Why |
| --- | --- |
| IP67 project boxes | Weatherproof housing for backpack and first cattle tests before the printed enclosure |
| Cattle neck strap with buckle, plus a counterweight | How commercial collars keep the antenna on top of the neck |
| USB power bank | Multi-hour outdoor runs before the battery is sorted out |
