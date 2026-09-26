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

Goal: A/B test against the nRF9151's built-in GNSS on the same walk. Prefer Qwiic/I2C breakouts so they plug into the same board.

| Item | Why | Approx. |
| --- | --- | --- |
| u-blox **MAX-M10S** breakout (SparkFun Qwiic version) | Likely V1 default: L1, GPS + Galileo + BeiDou + GLONASS, < 25 mW. About 3x the satellites of the nRF9151. | $45 |
| u-blox **MAX-F10S** (or NEO-F10N) L1/L5 breakout | Dual-band accuracy candidate, 1.0 m CEP with SBAS. Tells us whether L5 is worth the extra power. | $60–90 |
| Dual-band L1/L5 active antenna (stacked patch or small quadrifilar helix), U.FL/SMA | Required for the F10; the helix also tests rotation tolerance | $20–40 |
| 25×25 mm active L1 patch antenna, U.FL | Bigger than the current patch; test on the nRF9151 and the M10S | $10–15 |
| 35×35 mm active L1 patch antenna, U.FL | Upper bound on how much a bigger patch helps | $15–20 |
| Copper-clad board or aluminium plate, ~70×70 mm | Ground plane under the patch, to measure its effect | $5 |
| Qwiic IMU breakout (e.g. LSM6DSO or ISM330DHCX) | Motion-gated fixes, dead reckoning, rotation logging | $15–30 |

## 4. Field test gear

| Item | Why |
| --- | --- |
| IP67 project boxes | Weatherproof housing for backpack and first cattle tests before the printed enclosure |
| Cattle neck strap with buckle, plus a counterweight | How commercial collars keep the antenna on top of the neck |
| USB power bank | Multi-hour outdoor runs before the battery is sorted out |
