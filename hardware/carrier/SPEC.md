# Carrier board, rev A2: spec

Rev A 2026-09-26; **rev A2 the same day**, after the first-principles collar decisions (`docs/COLLAR-FIRST-PRINCIPLES.md`). Rev A2 changes:
- The board is a plain 95 × 75 mm rectangle, no longer shaped to a shell.
- The battery lives in the bottom module and reaches the board over the harness.
- The harness is now M8 8-pin.
- Two cue ports (left and right ear pods) replace the on-board buzzer socket.
- Everything that leaves the box sits behind one switched, protected external bus.

The carrier is a 2-layer board inside the V1-alpha test box (draft 1 of the shell). The boards we already own plug into it. On the board itself: the solar charger, the strap-harness port, the connectors and the test pads. It has no radio circuits: the antennas stay on the Connect Kit and the MAX-M10S.

Sources, all kept locally in `mechanical/reference/vendor/` or `/tmp/ds` during the work:

| Ref | Document |
| --- | --- |
| [MD] | Makerdiary nRF9151 Connect Kit rev A: hardware diagram (front, back) and dimension drawing |
| [BQ] | TI BQ2407x datasheet, SLUS810N (Oct 2021) |
| [TPS25] | TI TPS2553 datasheet (current-limited load switch) |
| [TCA] | TI TCA4307 datasheet, SCPS270B (Nov 2023) |
| [TPS] | TI TPS63901 datasheet (the Connect Kit's 3.3 V regulator) |
| [BQ18] | TI BQ25180 datasheet (the Connect Kit's own charger) |
| [UBX] | u-blox MAX-M10S data sheet, UBX-20035208 R08 |
| [P124] | Voltaic P124 datasheet, Aug 2026 |
| [SF] | SparkFun MAX-M10S and Qwiic Buzzer Eagle board files, Adafruit LSM6DSOX/ISM330 board file |
| [SHELL] | `mechanical/lib/collar.py` and `dims.py` (V1-alpha draft 1) |

**Licence rule:** [SF] boards are CC BY-SA. We read them only for the **mating interface**: where their header pins are and what each pin is called. No circuit on this board comes from them. Every circuit comes from the chip maker's datasheet. The board is CERN-OHL-P.

## 1. What plugs in, and the recommendations

```
 P124 panel A ──PH2──┐
 P124 panel B ──PH2──┴─ Schottky OR ─► bq24074 IN      OUT ─► Kit J2 (battery input)
                                        │ BAT ◄── harness BAT+ ×2 ◄── 6600 mAh Li-ion (bottom module)
                                        │ TS  ◄── harness NTC     ◄── 10K NTC on the pack
                                        └ CHG, PGOOD, CE, ISET ─► Kit GPIO/ADC

 Connect Kit (2×20 socket) ── VIO 3.3 V + I2C2 ──┬── MAX-M10S (8 + 4-pin sockets)
                                                 ├── ISM330DHCX (9-pin socket)
                                                 ├── spare Qwiic socket (inside the box)
                                                 └── TCA4307 ── EXT bus ──┬── CUE_L Qwiic ── left ear pod buzzer
          3V3 ── TPS2553 (current limit) ── EXT_3V3 ──────────────────────┼── CUE_R Qwiic ── right ear pod buzzer
                        EXT_EN switches both                              └── harness SDA/SCL ── pack fuel gauge (later)
```

| Topic | Recommendation | Why |
| --- | --- | --- |
| Board shape | **Rectangle, 95 × 75 mm**, four M3 corner holes | Under 100 × 100 mm, JLCPCB's cheapest tier. The battery has left the top box, so the board no longer has to wrap around it (decided 2026-09-26) |
| Connect Kit | Two 1 × 20 **SMD** female sockets, 2.54 mm pitch | The Kit already has male pins fitted (parts photo). SMD sockets leave no tails under the board, which keeps the bottom flat for test pads and the fixture (section 7) |
| MAX-M10S | **Female sockets** (8-pin edge row and 4-pin I2C row), not Qwiic | Sockets give us EXTINT (wake from standby), RESET_N, TIMEPULSE and UART, which Qwiic doesn't carry, and hold the board rigidly with no cable |
| ISM330DHCX | **Female 9-pin socket** | Brings INT1/INT2 to the nRF for wake-on-motion. An IMU should be screwed down, not hanging on a cable |
| Cues | **Two Qwiic Buzzers, one in each ear pod** on the strap, on Qwiic cables to CUE_L and CUE_R | Left/right cues need one sound source on each side of the neck (`docs/COLLAR-FIRST-PRINCIPLES.md` section 1). Qwiic Buzzers because one is owned and its driver is written; the second buzzer's address moves from 0x34 to 0x5B in software (SparkFun's two-buzzer example) |
| Spare Qwiic | One JST-SH 4-pin socket on the main I2C bus | For bench add-ons, or for a breakout that won't fit its socket |
| Charger | bq24074, **USB500 mode** (EN2 = 0, EN1 = 1), 1 A programmed charge, 500 mA input limit | USB500 is the only mode with input-voltage regulation (VIN-DPM 4.5 V), which stops the charger from dragging a panel down and collapsing it. The ILIM-resistor mode has no VIN-DPM ([BQ] 8.5, VIN-DPM: "EN2 = LO") |
| Kit power | bq24074 **OUT → Kit J2** (battery input) | This is how TI wires the system load ([BQ] 9.3.4, 10.1). Charge termination and the safety timers only see battery current. OUT has short-circuit protection, and the Kit boots from sun even with a flat pack. OUT is 4.3–4.5 V when there's input ([BQ] 8.5 VO(REG)), inside J2's 3.6–4.65 V range [MD] |
| 3.3 V | The Kit's VIO pin (TPS63901 buck-boost, over 400 mA at 3.3 V [TPS] p.1) powers every breakout | No regulator on the carrier. The breakouts and the nRF's GPIO bank share one rail, so nothing can back-power anything |
| Harness | **M8 8-pin**: BAT+ ×2, GND ×2, SDA, SCL, NTC, INT. The pack itself, not a 5 V bus | The battery is the counterweight (layout B). The charger's thermistor has to sit on the pack, which the 4-pin harness had no wire for. The power conductors are doubled so one broken wire doesn't drop the pack |
| External bus | Everything that leaves the box (both cue ports, the harness I2C) sits behind a **TCA4307 buffer plus a TPS2553 current-limited switch**, both switched by one GPIO, off by default | A chewed Qwiic cable or crushed harness can't hang the GNSS/IMU bus or short the Kit's 3.3 V. The buzzers are unpowered between cues, which removes their idle current |

## 2. Connect Kit sockets

Geometry [MD dimension drawing]: two rows of 20 pins at 2.54 mm pitch, **17.78 mm between rows** (the Ø1.4 corner holes are 1.27 mm in from each edge and in line with the rows). Pin 1 (VBUS) and pin 40 (VIO) are 3.81 mm from the USB end, and pins 20/21 are 3.81 mm from the antenna end (1.27 mm hole inset + 22.86 mm from the top hole to pin 32, and the 48.26 mm span from pin 1 to pin 20). Viewed from the top with USB up: pins 1–20 run down the left row, pins 21–40 run up the right row.

Pinout [MD front diagram] and what the carrier connects:

| Pin | Kit signal | nRF9151 | Carrier net | Notes |
| --- | --- | --- | --- | --- |
| 1 | VBUS | | TP only | USB 5 V from the Kit's USB-C. Not used for charging (see question 9) |
| 2 | VSYS | | TP only | Kit's system rail, an output (3.8–5.0 V) |
| 3 | GND | | GND | |
| 4 | ENABLE | | TP only | Kit power enable, left at its default |
| 5 | P9 | P0.09 | CHG_CE | bq24074 CE, 100 kΩ pull-down: charging on unless firmware drives it high |
| 6 | P8 | P0.08 | EXT_INT | Harness pin 6 (module interrupt, e.g. a fuel-gauge alert), 1 kΩ series + ESD, 100 kΩ pull-up to 3V3 |
| 7 | P7 | P0.07 | EXT_EN | TCA4307 EN and TPS2553 EN together. 100 kΩ pull-down: external bus off and unpowered |
| 8 | P6 | P0.06 | EXT_READY | TCA4307 READY, 10 kΩ pull-up to 3V3 [TCA] pin 5 |
| 9 | P5 | P0.05 | EXT_FAULT | TPS2553 FAULT (open-drain, over-current), 100 kΩ pull-up to 3V3 [TPS25] |
| 10–14 | P4…P0 | P0.04–P0.00 | EXP header | Spare, to an unpopulated expansion header (stimulus board later) |
| 15 | P31 | P0.31 | I2C_SCL | Main bus, as in today's firmware (I2C2) |
| 16 | P30 | P0.30 | I2C_SDA | Main bus |
| 17 | P29 | P0.29 | IMU_INT1 | |
| 18 | P28 | P0.28 | IMU_INT2 | |
| 19 | P27 | P0.27 | GNSS_EXTINT | Wake from software standby [UBX] Table 10 pin 5 |
| 20 | P26 | P0.26 | GNSS_RESET_N | Drive open-drain; low ≥ 1 ms resets [UBX] Table 10 pin 9 |
| 21 | A0 | P0.13 / AIN0 | VBAT_SENSE | 1 MΩ / 1 MΩ divider from BAT, 100 nF at the pin. Sources this high need the SAADC's 40 µs acquisition time |
| 22 | A1 | P0.14 / AIN1 | ISET_SENSE | 100 kΩ series from ISET. V = ICHG / 400 × RISET [BQ] eq. 3: charge current for telemetry |
| 23 | A2 | P0.15 / AIN2 | VIN_SENSE | 1 MΩ / 200 kΩ divider from charger IN (8 V → 1.33 V) |
| 24–26 | A3, A4, A5 | P0.16–P0.18 | EXP header | Spare analog |
| 27–28 | A6, A7 | P0.19, P0.20 | NC | |
| 29 | P21 | P0.21 | CHG_STAT | bq24074 CHG, 100 kΩ pull-up to 3V3 [BQ] 10.2.2.4 |
| 30 | P22 | P0.22 | GNSS_RXD | nRF TX → M10S RX (UARTE1) |
| 31 | P23 | P0.23 | GNSS_TXD | M10S TX → nRF RX |
| 32 | P24 | P0.24 | GNSS_PPS | TIMEPULSE. Input only: the M10S pin is shared with SAFEBOOT_N, so nothing may pull it low at boot [UBX] Table 10 note 15 |
| 33 | P10 | P0.10 | CHG_PGOOD | bq24074 PGOOD, 100 kΩ pull-up to 3V3 |
| 34 | P11 | P0.11 | TP only | UART0 TX to the Kit's interface MCU (console) |
| 35 | P12 | P0.12 | TP only | UART0 RX |
| 36 | SWDIO | | TP only | |
| 37 | SWCLK | | TP only | |
| 38 | RESET | | TP only | |
| 39 | GND | | GND | |
| 40 | VDD_GPIO (VIO) | | 3V3 | Must be set to 3.3 V (the factory setting, `viosel` on the Kit's interface MCU) |

Firmware impact: I2C2 stays on P0.30/P0.31, so the buzzer driver is unchanged, but the buzzers now sit behind the buffer. Firmware raises EXT_EN, waits for EXT_READY, then cues. New: UARTE1 for the GNSS, three ADC channels, the GPIOs above. UARTE0 (console) and TWIM2 (I2C) are already taken; UARTE1 is free.

**Kit battery feed.** The header has no battery pin; the battery reaches the Kit only through J2 (MX1.25-2P, underside) or test pad TP3 [MD back]. The carrier brings CHG_OUT and GND to two plated holes (2.54 mm pitch, strain-relief slot beside them). One of the 1.25 mm pigtails on order plugs into J2 and its wires are soldered into these holes.

## 3. Breakout sockets

Pin names and positions come from the [SF] board files (mating interface only).

**MAX-M10S (SparkFun GPS-18037), 38.10 × 30.48 mm.** Two female rows plus the four Ø3.3 corner holes for standoffs.

| Row | Pin | Name | Carrier net |
| --- | --- | --- | --- |
| J5 (8-pin, x = 1.27 mm, y = 24.13 → 6.35) | 1 | GND | GND |
| | 2 | 3.3V | 3V3 |
| | 3 | !SAFE | TP only (recovery) |
| | 4 | TXO | GNSS_TXD |
| | 5 | RXI | GNSS_RXD |
| | 6 | PPS | GNSS_PPS |
| | 7 | INT | GNSS_EXTINT |
| | 8 | !RESET | GNSS_RESET_N |
| J3 (4-pin, y = 29.21, x = 22.86 → 15.24) | 1 | GND | GND |
| | 2 | 3.3V | 3V3 |
| | 3 | SDA | I2C_SDA |
| | 4 | SCL | I2C_SCL |

**ISM330DHCX (Adafruit 4502), 25.40 × 17.78 mm.** 9-pin row at y = 2.54 mm, x = 2.54 → 22.86; Ø2.5 holes at (2.54, 15.24) and (22.86, 15.24) take standoffs on the opposite edge. The order below is from the LSM6DSOX board, which shares this outline. Check it against the ISM330 silkscreen when it arrives (question 4).

| Pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Name | VIN | 3Vo | GND | SCL | SDA | DO | CS | INT1 | INT2 |
| Net | 3V3 | NC | GND | I2C_SCL | I2C_SDA | NC (address 0x6A) | NC (board pull-up keeps I2C mode) | IMU_INT1 | IMU_INT2 |

The aux row (SCX, SDX, OCS, SDO_AUX, GND) is left unsocketed.

**Cue ports CUE_L, CUE_R:** JST-SH 4-pin, Qwiic order (GND, EXT_3V3, EXT_SDA, EXT_SCL). A Qwiic cable runs from each to a Qwiic Buzzer in its ear pod. Buzzer addresses 0x34 (left) and 0x5B (right).

**Spare Qwiic:** JST-SH 4-pin on the main bus, inside the box: GND, 3V3, SDA, SCL.

**I2C pull-ups:**
- **Main bus:** 4.7 kΩ to 3V3. The M10S fits its own pull-ups by default; cut that jumper (question 5). The IMU's 10 kΩ can stay, giving ~3.2 kΩ.
- **EXT bus:** 4.7 kΩ to EXT_3V3, so nothing on it is back-powered while it's off. Cut the buzzers' pull-up jumpers too.

Addresses: main bus M10S 0x42, ISM330 0x6A. EXT bus buzzers 0x34 and 0x5B, and the pack's fuel gauge later (MAX17260 is 0x36). No clashes.

**EXT_3V3:** TPS2553 from 3V3, current limit set to ~250 mA by its ILIM resistor (value from [TPS25] in the schematic), EN tied to EXT_EN, FAULT to EXT_FAULT. A short in a cue cable trips the limit instead of pulling down the Kit's VIO.

## 4. Charger: bq24074 (from [BQ])

| Pin | Connection | Value | Reason and datasheet section |
| --- | --- | --- | --- |
| IN (13) | Charger input node; 10 µF 25 V to GND at the pin | | 1–10 µF bypass [BQ] Table 7-1. Rated for the ~8 V panel open-circuit voltage when cold, not 5 V |
| OUT (10, 11) | CHG_OUT → Kit J2 feed; 10 µF to GND at the pins | | 4.7–47 µF [BQ] Table 7-1; system load on OUT [BQ] 10.1 |
| BAT (2, 3) | Pack + over the harness (two conductors), or J_BAT on the bench; 10 µF to GND | | 4.7–47 µF [BQ] Table 7-1. BAT is also the charger's voltage-sense input, so ~0.6 m of cable adds ~50 mV at 0.5 A: charging slows slightly near full, and the pack still finishes at 4.2 V as the current tapers |
| EN2 (5) | GND | | USB500 mode [BQ] Table 7-2 |
| EN1 (6) | 10 kΩ to OUT | | Logic high ≥ 1.4 V [BQ] 8.5; pin rated to 7 V [BQ] 8.1. Tied to OUT, not the Kit's 3.3 V, so the charger runs without the Kit |
| ILIM (12) | 3.24 kΩ 1 % to GND | ≈ 470 mA if ever switched to resistor mode | Must be fitted: "Leaving ILIM unconnected disables all charging" [BQ] Table 7-1; range 1.1–8 kΩ [BQ] 8.3 |
| ISET (16) | 887 Ω 1 % to GND | ICHG = 890 / 887 = 1.0 A | [BQ] eq. 2. Input-limited to 500 mA, so the real charge current is ≤ ~480 mA, and the timers slow down to match [BQ] 9.3.5. Pre-charge 88 / 887 = 99 mA [BQ] 8.5 |
| ITERM (15) | Open | Terminates at 10 % × ICHG = 100 mA | Default [BQ] 9.3.5.2 |
| TMR (14) | 72 kΩ to GND | Fast-charge timer 10 × 48 × 72 = 9.6 h at full rate; pre-charge 58 min | [BQ] eq. 6–7. Maximum allowed value: a 6600 mAh pack takes ~14 h at 480 mA, and the timer counts at ~half speed when input-limited ([BQ] 9.3.5.6), so ~20 h in practice. A timer fault clears when the input drops at night or firmware toggles CE [BQ] 9.3.5.6 |
| TS (1) | 10K NTC at the pack, over the harness NTC pin (or J_NTC on the bench); 10 nF to GND against pickup on the cable; 10 kΩ DNP footprint for bench use without an NTC | Charges between ~3 °C and ~47 °C with a B3950 NTC | ITS = 75 µA; cold trip 2.1 V (28 kΩ), hot trip 0.3 V (4 kΩ) [BQ] 8.5, 9.3.6. The Adafruit 372 is B3950 (to confirm on the bag). With no NTC fitted, TS floats above the cold trip and charging stops: fail-safe |
| CE (4) | CHG_CE, 100 kΩ to GND | Charging enabled by default | [BQ] Table 7-1 (internal 285 kΩ pull-down, "do not leave unconnected") |
| CHG (9), PGOOD (7) | 100 kΩ to 3V3, to GPIO | | [BQ] 10.2.2.4. No LEDs: an LED to OUT would pull these nRF inputs above 3.3 V, and nobody sees LEDs inside a sealed shell |
| VSS (8) + thermal pad | GND, 3 × 3 array of vias in the pad | | [BQ] 12.1 |

**Inputs.** Each panel reaches IN through its own diode, so they can be paralleled on the board and neither can feed the other:

| Source | Path | Reason |
| --- | --- | --- |
| Panel A, panel B | PH 2-pin each → B5819W Schottky → IN | P124: Vmp 6.0 V, Voc 7.07–7.28 V, Isc 0.21–0.23 A [P124]. Diode drop ~0.3 V at 0.2 A is fine against a 6 V panel. A diode per panel stops a sunlit panel pushing current back into a shaded one |

**Thermal.** Worst realistic case is both panels at ~6 V and 400 mA into a pack at 3.4 V. That's P = (6 − 4.4) × 0.4 + (4.4 − 3.4) × 0.4 ≈ 1.0 W ([BQ] eq. 11), +45 °C at 44.5 °C/W ([BQ] 8.4). In a 60 °C shell that's ~105 °C, under the 125 °C thermal regulation. Pour copper on both layers under and around the IC.

**Not MPPT.** The bq24074 holds the panels at ~4.5 V at best, where the P124 is on the flat part of its curve: it gives almost its full current, at about 75 % of the power at Vmp. Current in ≈ current into the pack, so the harvest is counted in mAh (section 9). The BQ25798 board gets real MPPT.

## 5. Harness port (strap bus)

An 8-pin PH socket for the pigtail from the box's panel-mount M8 8-pin socket. The pack in the bottom module is on the other end. Pin order and wire colours follow the M8 8-pin cordset standard (IEC 61076-2-104, DIN 47100 colours). This is the V1 bus standard as well (`docs/COLLAR-FIRST-PRINCIPLES.md` section 4):

| M8 pin | Wire | Signal |
| --- | --- | --- |
| 1 | white | SDA |
| 2 | brown | BAT+ |
| 3 | green | GND |
| 4 | yellow | SCL |
| 5 | grey | NTC (pack thermistor to GND) |
| 6 | pink | INT (module interrupt, open-drain) |
| 7 | blue | GND |
| 8 | red | BAT+ |

- **BAT+ and GND** go straight to the charger's BAT node and ground, each on two conductors. The pack's own protection circuit is the only thing that can stop a short in the cable itself (upstream of this board), so the bottom module also gets a fuse at the cells (section 12).
- **I2C:** on the EXT bus behind the TCA4307 (section 3). The buffer's pins take 7 V absolute maximum [TCA] 5.1, and it clocks a stuck module free after ~40 ms [TCA] p.1.
- **ESD:** TVS protection on every line that leaves the box: harness BAT+, SDA, SCL, NTC, INT, and both cue ports' EXT_3V3, SDA, SCL (parts chosen in the schematic).
- Logic is 3.3 V with pull-ups in the top unit; modules must not pull up to anything higher.
- **Bench vs field:** J_BAT and J_NTC stay for bench use without a harness. Silkscreen warning: never connect J_BAT and a harness pack at the same time.

## 6. Wire connectors

| Ref | Connector | Mates with | Pins |
| --- | --- | --- | --- |
| J_BAT | JST-PH 2-pin, SMD right-angle | Adafruit 353 pack's PH plug, **bench only** | Polarity to match Adafruit's convention; Cody checks with a meter before first plug-in (question 4) |
| J_SOLA, J_SOLB | JST-PH 2-pin each | Pre-crimped PH pigtails soldered to each P124's pads | 1 = +, 2 = − |
| J_NTC | JST-PH 2-pin | Pre-crimped PH pigtail on the Adafruit 372, **bench only** | Non-polar |
| J_HBUS | JST-PH 8-pin | Pigtail from the M8 8-pin panel socket | Section 5 |
| J_CUE_L, J_CUE_R | JST-SH 4-pin | Qwiic cables to the ear-pod buzzers | GND, EXT_3V3, EXT_SDA, EXT_SCL |
| J_KIT | 2 plated holes + strain-relief slot | 1.25 mm pigtail (on order) into Kit J2 | CHG_OUT, GND |
| J_QWIIC | JST-SH 4-pin | Qwiic cable, inside the box | GND, 3V3, SDA, SCL |
| J_EXP | 1 × 10, 2.54 mm, unpopulated | Stimulus board / experiments | 3V3, GND, P0.00–P0.04, A3, A4, A5 |

There's no crimp tool in `hardware/tools.md`, so every mating half is a pre-crimped pigtail spliced with solder and heat shrink (both on hand).

## 7. Test pads

1.0 mm round pads on the **bottom** side, labelled in silkscreen, all on a 2.54 mm grid where the layout allows, so a pogo fixture can reach them. The bottom is otherwise empty.

| Group | Pads |
| --- | --- |
| Rails | BAT, CHG_OUT, CHG_IN, SOLAR_A (before the diode), SOLAR_B, 3V3, EXT_3V3, Kit VBUS, Kit VSYS, and GND × 4 spread across the board |
| Programming | SWDIO, SWCLK, RESET, UART0 TX (P0.11), UART0 RX (P0.12), Kit ENABLE |
| Buses | I2C_SDA, I2C_SCL, EXT_SDA, EXT_SCL, EXT_EN, EXT_INT |
| Charger | TS, ISET, CHG, PGOOD, CE |
| GNSS | GNSS_SAFEBOOT (!SAFE), GNSS_RESET_N, GNSS_PPS |

## 8. Board outline, placement and mounting

**95 × 75 mm, 2 mm corner radius, four M3 holes (Ø3.2) at 3.5 mm from each edge.** The board isn't shaped to a shell: the V1-alpha test box gets posts to match (section 12).

Placement (top view, origin at the bottom-left corner):

| Block | Where | Why |
| --- | --- | --- |
| Connect Kit sockets | Along the left edge, rows vertical; USB end at the bottom edge, antenna end at the top | USB reachable at the edge for flashing; U.FL cables head up to the lid antennas |
| MAX-M10S | Top right; SMA toward the right edge | Its antenna cable goes to the patch under the crown, away from the Kit's LTE U.FL |
| ISM330DHCX | Middle, between the Kit and the M10S | Screwed down near the board's centre |
| Charger, panel and NTC connectors | Bottom right | Short high-current loop IN → bq24074 → BAT; J_SOLA/J_SOLB on the bottom edge |
| J_HBUS, J_CUE_L, J_CUE_R, TCA4307, TPS2553, ESD | Right edge | Every line that leaves the box enters on one edge, through its ESD part first |
| J_EXP, J_QWIIC, J_KIT | Top edge | |

Height above the board: each plugged board sits ~11 mm up (8.5 mm socket + the pins' 2.5 mm plastic spacer), and the tallest part on any of them is ~3.3 mm (the USB-C or SMA). So **~17 mm from the board's top face** (question 7 refines this).

Board: 2 layers, 1.6 mm FR-4, 1 oz, lead-free HASL, green. Ground pour both sides.

## 9. Power budget

Per day, 3.7 V pack side. The Kit's buck-boost is taken as 90 % efficient at these loads (est; [TPS] Fig. 7-2 to 7-4). "Measure" means the multimeter on its µA range in series with the pack. A PPK2 would do it better but is deferred.

| Load | Condition | Current | mAh/day | Source |
| --- | --- | --- | --- | --- |
| MAX-M10S | Continuous tracking, 1 Hz, default GPS+GAL+BDS | 9.5 mA VCC + 2.3 mA V_IO at 3.0 V → ~11.7 mA from the pack | 281 | [UBX] Table 15 |
| | Power-save mode instead | 5 + 2 mA → ~6.9 mA | 166 | [UBX] Table 15 |
| nRF9151 | LTE-M in PSM between reports | µA level | < 1 | Nordic; measure |
| LTE-M reports | Every 15 min | est. 10–30 | 10–30 | Size with Nordic's Online Power Profiler once the interval is set |
| ISM330DHCX board | Accel on, gyro off, plus the Adafruit regulator and power LED | unknown | ? | Measure (question 6) |
| Qwiic Buzzers ×2 | Unpowered between cues (EXT_3V3 off) | 0 idle | ~0 | Cue current only while sounding |
| Connect Kit overhead | Interface MCU, BQ25180, TPS63901, LEDs | unknown | ? | Measure (question 6) |
| bq24074 | No input (night) | 4.3 µA typ | 0.1 | [BQ] 8.5 IBAT(PDWN) |
| TCA4307 | Disabled between uses | 10 µA typ | 0.2 | [TCA] 5.5; ~2.5 mA while enabled, so firmware enables it only to cue or read the pack |
| Dividers | VBAT 2 MΩ | 2.1 µA | 0.05 | |
| **Known total** | GNSS continuous | | **~300** + unknowns | |

Every unknown mA running all the time adds 24 mAh/day.

**Storage:** 6600 mAh, about 5,600 usable from 4.2 V down to a 3.4 V firmware cutoff (est): **~19 days without sun** at 300 mAh/day. V1's 60-day target needs the GNSS averaging ≤ ~3 mA, meaning power-save mode, or GNSS duty-cycled when the animal is far from the fence. That's firmware work, not a board change.

**Harvest:** two P124 in parallel give up to ~0.42–0.46 A in full sun [P124 Isc]. In the draft-1 test box the panels face ±18.7° to either side of the spine [SHELL], so assume ~70 % of flat. Allow another 90 % for dirt and heat: ~0.28 A × peak-sun-hours. Middle Tennessee is roughly 2.5 (Dec) to 5 (Jun) peak sun hours: **~700 mAh/day in winter, ~1,400 mAh/day in summer.** That's 2–4 × the known load, before shade, hair and animals lying down. Firmware logs the real harvest from ISET_SENSE and VIN_SENSE.

## 10. Parts (preliminary, JLCPCB/LCSC)

Checked at LCSC 2026-09-26: **BQ24074RGTR C54313**, **TCA4307DGKR C880333**, **TPS2553DBVR C55266** (extended parts, ~$3 setup fee each at JLCPCB). Schottky B5819W (SOD-123) is a JLCPCB basic part. The LM66100 from rev A is gone with the 5 V harness input. Passives from the basic 0402/0603 range, with the IN capacitor rated 25 V. PH/SH sockets, the SMD female sockets and the TVS array get picked and their LCSC numbers recorded when the schematic is written.

The Adafruit 4755 charger board we bought is no longer needed in the collar. It stays a bench reference and a fallback.

## 11. Open questions for Cody

Decided 2026-09-26: rectangle board (was question 1); the harness carries the battery, not 5 V (replaces question 2).

To buy when you're ready (not ordered):
1. **A second SparkFun Qwiic Buzzer** (BOB-24474) and **two Qwiic cables, 200–500 mm**, for the ear pods.
2. **M8 8-pin harness:** a high-flex PUR female-to-male cordset and two panel-mount sockets with leads (one on the box, one on the bottom module). Length once the bottom module is drawn (section 12).
3. Pre-crimped JST-PH pigtails (2-pin ×4, 8-pin ×1) for the panels, NTC, bench battery and harness.

Bench checks when parts arrive:
4. **Pinouts against silkscreen:** the ISM330's 9-pin order (VIN, 3Vo, GND, SCL, SDA, DO, CS, INT1, INT2); the battery pack's JST-PH polarity; the 1.25 mm pigtail's red wire against the `+` on the Kit's J2.
5. **Cut the I2C pull-up jumpers** on the MAX-M10S and both buzzers, and the power-LED jumpers on the M10S and the ISM330.
6. **Idle current**, multimeter in series with the pack: the Kit alone with USB unplugged, then plus the IMU. Those numbers fill the gaps in section 9.
7. **Heights with calipers:** the MAX-M10S from PCB to the top of the SMA, the Kit's male pins below its PCB (spacer and pin length), a female socket's height.
8. **Buzzer loudness from an ear pod:** dB at 1 m with a phone app. It decides piezo or not for the integrated board.

Not needed now:
9. The Kit's USB VBUS could feed the charger for bench charging. Left out: a diode on VBUS leaks back at high temperature and can wake the Kit's own charger. Bench-charge through J_SOLA with the bench supply at 6 V, 0.5 A limit instead.

## 12. Test-box changes this implies (for `mechanical/`)

The V1-alpha test box is draft 1 of the shell, adapted:
- Remove the battery locators and the per-board standoffs; add four posts for the carrier's M3 holes. Raise the board plane from z = 18 to **z = 20**, because a centred board sits over the strap channel, where the floor is at 18.8.
- Panel-mount M8 8-pin socket in the box wall, below the seal.
- **Two ear pods** on the strap, one per side, each holding a Qwiic Buzzer behind an ePTFE acoustic membrane, with the Qwiic cable through a sealed gland.
- **Bottom module** holding the 6600 mAh pack, its NTC, an inline fuse at the pack and the other M8 socket, plus steel to make **bottom ≥ 1.87 × top**. The box and boards without the pack are ~345 g *est*, so the bottom needs ~645 g: pack 155 g + shell ~100 g + ~390 g of steel.
- **Adjustment on both sides at the bottom module**, as Halter does it (both buckles within one hole of each other), so the bottom stays under the throat and the top on the crest across the 75–130 cm range. The harness's extra length is stored in a slack pocket in the bottom module.
