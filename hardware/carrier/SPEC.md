# Carrier board, rev A: spec

Draft 2026-09-26, for Cody's review. Nothing is drawn until this is agreed (`docs/DESIGN-PHASE.md`).

The carrier is a 2-layer board inside the V1-alpha top unit. The boards we already own plug into it. On the board itself: the solar charger, the strap-harness port, the connectors and the test pads. It has no radio circuits: the antennas stay on the Connect Kit and the MAX-M10S.

Sources, all kept locally in `mechanical/reference/vendor/` or `/tmp/ds` during the work:

| Ref | Document |
| --- | --- |
| [MD] | Makerdiary nRF9151 Connect Kit rev A: hardware diagram (front, back) and dimension drawing |
| [BQ] | TI BQ2407x datasheet, SLUS810N (Oct 2021) |
| [LM] | TI LM66100 datasheet |
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
 P124 panel B ──PH2──┼─ Schottky OR ─► bq24074 IN      OUT ─► kit J2 (battery input)
 strap M8 5V ──PH4──► LM66100 (fw-enabled)┘   │ BAT ◄──PH2── 6600 mAh Li-ion
                                              │ TS  ◄──PH2── 10K NTC on the pack
 strap M8 I2C ─PH4──► TCA4307 buffer ─┐       └ CHG, PGOOD, CE, ISET ─► kit GPIO/ADC
                                      │
 Connect Kit (2×20 socket) ── VIO 3.3 V + I2C2 ──┬── MAX-M10S (8 + 4-pin sockets)
                                                 ├── ISM330DHCX (9-pin socket)
                                                 ├── Qwiic Buzzer (4-pin socket)
                                                 └── spare Qwiic socket
```

| Topic | Recommendation | Why |
| --- | --- | --- |
| Board shape | **One ring-shaped board** that fills the cavity around the battery, 143 × 99 mm with a 61 × 75 mm cutout for the pack | The pack sits in the middle of the cavity and stands higher than the board plane. A ring puts the Kit and IMU on one side, the GNSS and charger on the other, and connects them without cables |
| Connect Kit | Two 1 × 20 **SMD** female sockets, 2.54 mm pitch | The Kit already has male pins fitted (parts photo). SMD sockets leave no tails under the board, where the floor is 0.7 mm away (section 8) |
| MAX-M10S | **Female sockets** (8-pin edge row and 4-pin I2C row), not Qwiic | Sockets give us EXTINT (wake from standby), RESET_N, TIMEPULSE and UART, which Qwiic doesn't carry, and hold the board rigidly with no cable |
| ISM330DHCX | **Female 9-pin socket** | Brings INT1/INT2 to the nRF for wake-on-motion. An IMU should be screwed down, not hanging on a cable |
| Buzzer | **Keep the Qwiic Buzzer**, plugged into a 4-pin female socket | Already owned, firmware driver done, and the earlier cart review found a piezo + driver no louder. The loudness test in the sealed shell (question 6) decides whether the integrated board gets a piezo driver |
| Spare Qwiic | One JST-SH 4-pin socket on the main I2C bus | For bench add-ons, or for a breakout that won't fit its socket |
| Charger | bq24074, **USB500 mode** (EN2 = 0, EN1 = 1), 1 A programmed charge, 500 mA input limit | USB500 is the only mode with input-voltage regulation (VIN-DPM 4.5 V), which stops the charger from dragging a panel down and collapsing it. The ILIM-resistor mode has no VIN-DPM ([BQ] 8.5, VIN-DPM: "EN2 = LO") |
| Kit power | bq24074 **OUT → Kit J2** (battery input) | This is how TI wires the system load ([BQ] 9.3.4, 10.1). Charge termination and the safety timers only see battery current. OUT has short-circuit protection, and the Kit boots from sun even with a flat pack. OUT is 4.3–4.5 V when there's input ([BQ] 8.5 VO(REG)), inside J2's 3.6–4.65 V range [MD] |
| 3.3 V | The Kit's VIO pin (TPS63901 buck-boost, over 400 mA at 3.3 V [TPS] p.1) powers every breakout | No regulator on the carrier. The breakouts and the nRF's GPIO bank share one rail, so nothing can back-power anything |
| Harness | 4-pin port for the M8 socket: 5 V, GND, SDA, SCL. The 5 V is **input only and off by default**; I2C runs through a hot-swap buffer, off by default | The bq24074 can't output power, so collar-to-bay 5 V waits for the BQ25798 board. Off-by-default means a camera module's power bank is never drained unless firmware asks. The buffer means a crushed cable can't hang the collar's own I2C bus |

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
| 6 | P8 | P0.08 | HBUS_PWR_EN | Gate of the NMOS that enables the harness 5 V input. 100 kΩ pull-down (off) |
| 7 | P7 | P0.07 | HBUS_I2C_EN | TCA4307 EN. 100 kΩ pull-down (bay bus isolated) |
| 8 | P6 | P0.06 | HBUS_READY | TCA4307 READY, 10 kΩ pull-up to 3V3 [TCA] pin 5 |
| 9–14 | P5…P0 | P0.05–P0.00 | EXP header | Spare, to an unpopulated 1 × 10 expansion header (stimulus board later) |
| 15 | P31 | P0.31 | I2C_SCL | Main bus, as in today's firmware (I2C2) |
| 16 | P30 | P0.30 | I2C_SDA | Main bus |
| 17 | P29 | P0.29 | IMU_INT1 | |
| 18 | P28 | P0.28 | IMU_INT2 | |
| 19 | P27 | P0.27 | GNSS_EXTINT | Wake from software standby [UBX] Table 10 pin 5 |
| 20 | P26 | P0.26 | GNSS_RESET_N | Drive open-drain; low ≥ 1 ms resets [UBX] Table 10 pin 9 |
| 21 | A0 | P0.13 / AIN0 | VBAT_SENSE | 1 MΩ / 1 MΩ divider from BAT, 100 nF at the pin. Sources this high need the SAADC's 40 µs acquisition time |
| 22 | A1 | P0.14 / AIN1 | ISET_SENSE | 100 kΩ series from ISET. V = ICHG / 400 × RISET [BQ] eq. 3: charge current for telemetry |
| 23 | A2 | P0.15 / AIN2 | VIN_SENSE | 1 MΩ / 200 kΩ divider from charger IN (8 V → 1.33 V) |
| 24 | A3 | P0.16 / AIN3 | HBUS_5V_SENSE | 1 MΩ / 1 MΩ divider from the harness 5 V pin, before the switch: detects a powered module |
| 25–26 | A4, A5 | P0.17, P0.18 | EXP header | Spare analog |
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

Firmware impact: I2C2 stays on P0.30/P0.31, so the buzzer driver is unchanged. New: UARTE1 for the GNSS, three ADC channels, the GPIOs above. UARTE0 (console) and TWIM2 (I2C) are already taken; UARTE1 is free.

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

**ISM330DHCX (Adafruit 4502), 25.40 × 17.78 mm.** 9-pin row at y = 2.54 mm, x = 2.54 → 22.86; Ø2.5 holes at (2.54, 15.24) and (22.86, 15.24) take standoffs on the opposite edge. The order below is from the LSM6DSOX board, which shares this outline. Check it against the ISM330 silkscreen when it arrives (question 3).

| Pin | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Name | VIN | 3Vo | GND | SCL | SDA | DO | CS | INT1 | INT2 |
| Net | 3V3 | NC | GND | I2C_SCL | I2C_SDA | NC (address 0x6A) | NC (board pull-up keeps I2C mode) | IMU_INT1 | IMU_INT2 |

The aux row (SCX, SDX, OCS, SDO_AUX, GND) is left unsocketed.

**Qwiic Buzzer (SparkFun BOB-24474), 25.4 × 25.4 mm.** 4-pin row J1 at y = 1.27, x = 16.51 → 8.89: SCL, SDA, 3.3V, GND. Ø3.3 corner holes for standoffs. Its RST/TRIGGER row is left unsocketed.

**Spare Qwiic:** JST-SH 4-pin, standard Qwiic order (GND, 3V3, SDA, SCL).

**I2C pull-ups:** 4.7 kΩ to 3V3 on the carrier. The M10S and the buzzer each add their own (SparkFun boards fit pull-ups by default), and the three in parallel are about 1.2 kΩ. That's more than the nRF's standard-drive pins should sink, so cut the pull-up jumpers on those two boards (question 4). The IMU's 10 kΩ pull-ups can stay.

Addresses on the main bus: M10S 0x42, buzzer 0x34, ISM330 0x6A. No clashes.

## 4. Charger: bq24074 (from [BQ])

| Pin | Connection | Value | Reason and datasheet section |
| --- | --- | --- | --- |
| IN (13) | Charger input node; 10 µF 25 V to GND at the pin | | 1–10 µF bypass [BQ] Table 7-1. Rated for the ~8 V panel open-circuit voltage when cold, not 5 V |
| OUT (10, 11) | CHG_OUT → Kit J2 feed; 10 µF to GND at the pins | | 4.7–47 µF [BQ] Table 7-1; system load on OUT [BQ] 10.1 |
| BAT (2, 3) | Pack + (PH socket); 10 µF to GND | | 4.7–47 µF [BQ] Table 7-1 |
| EN2 (5) | GND | | USB500 mode [BQ] Table 7-2 |
| EN1 (6) | 10 kΩ to OUT | | Logic high ≥ 1.4 V [BQ] 8.5; pin rated to 7 V [BQ] 8.1. Tied to OUT, not the Kit's 3.3 V, so the charger runs without the Kit |
| ILIM (12) | 3.24 kΩ 1 % to GND | ≈ 470 mA if ever switched to resistor mode | Must be fitted: "Leaving ILIM unconnected disables all charging" [BQ] Table 7-1; range 1.1–8 kΩ [BQ] 8.3 |
| ISET (16) | 887 Ω 1 % to GND | ICHG = 890 / 887 = 1.0 A | [BQ] eq. 2. Input-limited to 500 mA, so the real charge current is ≤ ~480 mA, and the timers slow down to match [BQ] 9.3.5. Pre-charge 88 / 887 = 99 mA [BQ] 8.5 |
| ITERM (15) | Open | Terminates at 10 % × ICHG = 100 mA | Default [BQ] 9.3.5.2 |
| TMR (14) | 72 kΩ to GND | Fast-charge timer 10 × 48 × 72 = 9.6 h at full rate; pre-charge 58 min | [BQ] eq. 6–7. Maximum allowed value: a 6600 mAh pack takes ~14 h at 480 mA, and the timer counts at ~half speed when input-limited ([BQ] 9.3.5.6), so ~20 h in practice. A timer fault clears when the input drops at night or firmware toggles CE [BQ] 9.3.5.6 |
| TS (1) | 10K NTC to GND via a PH socket; 10 kΩ DNP footprint in parallel for bench use without an NTC | Charges between ~3 °C and ~47 °C with a B3950 NTC | ITS = 75 µA; cold trip 2.1 V (28 kΩ), hot trip 0.3 V (4 kΩ) [BQ] 8.5, 9.3.6. The Adafruit 372 is B3950 (to confirm on the bag). With no NTC fitted, TS floats above the cold trip and charging stops: fail-safe |
| CE (4) | CHG_CE, 100 kΩ to GND | Charging enabled by default | [BQ] Table 7-1 (internal 285 kΩ pull-down, "do not leave unconnected") |
| CHG (9), PGOOD (7) | 100 kΩ to 3V3, to GPIO | | [BQ] 10.2.2.4. No LEDs: an LED to OUT would pull these nRF inputs above 3.3 V, and nobody sees LEDs inside a sealed shell |
| VSS (8) + thermal pad | GND, 3 × 3 array of vias in the pad | | [BQ] 12.1 |

**Inputs.** Every source reaches IN through its own diode, so the panels can be paralleled on the board and none can feed another:

| Source | Path | Reason |
| --- | --- | --- |
| Panel A, panel B | PH 2-pin each → B5819W Schottky → IN | P124: Vmp 6.0 V, Voc 7.07–7.28 V, Isc 0.21–0.23 A [P124]. Diode drop ~0.3 V at 0.2 A is fine against a 6 V panel. A diode per panel stops a sunlit panel pushing current back into a shaded one |
| Harness 5 V | M8 pin 1 → LM66100 → B5819W → IN | The LM66100 gives reverse-polarity protection and an off switch. Its CE is pulled up to its own input by 100 kΩ (off), and a 2N7002 driven by HBUS_PWR_EN pulls it low (on). CE only switches relative to VIN ([LM] Comparator Chip Enable), so a 3.3 V GPIO can't drive it directly. The Schottky after it keeps the ~8 V panel node off the LM66100, which is rated to 6 V [LM] abs. max |

**Thermal.** Worst realistic case is both panels at ~6 V and 400 mA into a pack at 3.4 V. That's P = (6 − 4.4) × 0.4 + (4.4 − 3.4) × 0.4 ≈ 1.0 W ([BQ] eq. 11), +45 °C at 44.5 °C/W ([BQ] 8.4). In a 60 °C shell that's ~105 °C, under the 125 °C thermal regulation. Pour copper on both layers under and around the IC.

**Not MPPT.** The bq24074 holds the panels at ~4.5 V at best, where the P124 is on the flat part of its curve: it gives almost its full current, at about 75 % of the power at Vmp. Current in ≈ current into the pack, so the harvest is counted in mAh (section 9). The BQ25798 board gets real MPPT.

## 5. Harness port (strap bus)

A 4-pin PH socket for the pigtail from the top unit's M8 panel socket. Pin order follows the M8 4-pin sensor convention (1 brown L+, 2 white, 3 blue L−, 4 black C/Q). This fixes the bus standard for every module:

| M8 pin | Wire | Signal |
| --- | --- | --- |
| 1 | brown | +5 V bus |
| 2 | white | SCL |
| 3 | blue | GND |
| 4 | black | SDA |

- **5 V:** into the charger through the LM66100, off by default (section 4). Sensed on HBUS_5V_SENSE before the switch.
- **I2C:** TCA4307 between the main bus (SDAIN/SCLIN) and the harness (SDAOUT/SCLOUT), VCC = 3V3, 0.1 µF at pin 8, 10 kΩ pull-ups on both sides ([TCA] pin functions). EN is low by default (sides isolated, 10 µA [TCA] 5.5). If a module holds the bus low for about 40 ms, the TCA4307 disconnects it and clocks it free [TCA] p.1. Its bus pins take 7 V absolute maximum [TCA] 5.1, so a crushed cable shorting 5 V onto SDA doesn't reach the nRF.
- **ESD:** a 3-line TVS array on 5 V, SDA and SCL at the connector (part chosen in the schematic).
- Bus logic is 3.3 V with pull-ups in the top unit; modules must not pull up to 5 V.

## 6. Wire connectors

| Ref | Connector | Mates with | Pins |
| --- | --- | --- | --- |
| J_BAT | JST-PH 2-pin, SMD right-angle | Adafruit 353 pack's PH plug | Polarity to match Adafruit's convention; Cody checks with a meter before first plug-in (question 2) |
| J_SOLA, J_SOLB | JST-PH 2-pin each | Pre-crimped PH pigtails soldered to each P124's pads | 1 = +, 2 = − |
| J_NTC | JST-PH 2-pin | Pre-crimped PH pigtail soldered to the Adafruit 372 leads | Non-polar |
| J_HBUS | JST-PH 4-pin | Pigtail from the M8 panel socket | Section 5 |
| J_KIT | 2 plated holes + strain-relief slot | 1.25 mm pigtail (on order) into Kit J2 | CHG_OUT, GND |
| J_QWIIC | JST-SH 4-pin | Qwiic cable | GND, 3V3, SDA, SCL |
| J_EXP | 1 × 10, 2.54 mm, unpopulated | Stimulus board / experiments | 3V3, GND, P0.00–P0.05, A4, A5 |

There's no crimp tool in `hardware/tools.md`, so every mating half is a pre-crimped pigtail spliced with solder and heat shrink (both on hand).

## 7. Test pads

1.0 mm round pads on the **bottom** side, labelled in silkscreen, all on a 2.54 mm grid where the layout allows, so a pogo fixture can reach them. The bottom is otherwise empty (section 8).

| Group | Pads |
| --- | --- |
| Rails | BAT, CHG_OUT, CHG_IN, SOLAR_A (before the diode), SOLAR_B, HBUS_5V, 3V3, Kit VBUS, Kit VSYS, and GND × 4 spread across the board |
| Programming | SWDIO, SWCLK, RESET, UART0 TX (P0.11), UART0 RX (P0.12), Kit ENABLE |
| Buses | I2C_SDA, I2C_SCL, HBUS_SDA, HBUS_SCL |
| Charger | TS, ISET, CHG, PGOOD, CE |
| GNSS | GNSS_SAFEBOOT (!SAFE), GNSS_RESET_N, GNSS_PPS |

## 8. Board outline, stack and mounting (from [SHELL])

The shell draft gives the cavity, the pack position, the floor and the lid. The board fits inside them:

| Item | Value | From [SHELL] |
| --- | --- | --- |
| Cavity | 144 × 100 mm, 4 mm corner radius | Footprint 170 × 126 minus 13 mm rim each side |
| **Board outline** | **143 × 99 mm, 3.5 mm corners** (0.5 mm clear of the walls) | |
| Pack keep-out | Pack 54 × 69 centred at (0, 0), z 19.0–37.0, plus 2 mm corner locators: 60 × 74 | `_layout()` battery, `_add_internals()` locators |
| **Cutout** | **61 × 75 mm centred** (0.5 mm clear of the locators) | |
| Result | Side zones x = ±30.5 → ±71.5 (41 mm wide, 99 long); end bridges y = ±37.5 → ±49.5 (12 mm wide) | |
| Board plane | Underside at z = 18.0, 1.6 mm thick | `BOARD_Z` |
| Floor below | Highest at the inner edge over the strap channel: 17.3 mm at x = 30, \|y\| < 25. **0.7 mm clearance, so the bottom side carries test pads only, no parts or through-hole tails** | `floor_z()` |
| Vent notch | 8 × 2 mm notch in the −Y edge at x = 30: the M6 vent bore (Ø5.2 at z 17.5) opens into the cavity there | `top_base()` vent |

Headroom under the lid (inner roof, z, from `_roof_profile(WALL)`): 52.0 at |x| ≤ 17, 47.4 at 30, 44.1 at 40, 40.7 at 50, 37.3 at 60, 33.9 at 70. Every plugged board sits ~11 mm above the carrier (8.5 mm socket + the pins' 2.5 mm plastic spacer), so the tallest part on it has to stay below that line:

| Board | Top of tallest part (est) | Where it fits |
| --- | --- | --- |
| Connect Kit, USB-C 3.26 mm | ~34.9 | Right zone anywhere; as in the shell draft, USB end to −Y, antenna end to +Y (LTE flex is on the +Y wall) |
| MAX-M10S, SMA and Qwiic ~3.3 mm | ~35.2 | Left zone, **inboard of x = −62** (ceiling 36.6 there) |
| ISM330DHCX | ~33 | Right zone beside the Kit |
| Qwiic Buzzer, 2.5 mm buzzer | ~34.7 | Inboard of x = ±65, near whichever wall gets the sound port |

Panel leads enter through the lid slots at about (±51, +46), so J_SOLA and J_SOLB go at the +Y end of each side zone. The charger and J_HBUS go in the left zone; J_BAT on the bridge nearest the pack's lead.

**Mounting holes (proposed, M3, Ø3.2 plain):** four at (±66, ±43.5), where the floor top is ~8 mm and a printed post (10 mm tall) can hold an M3 × 4 heat-set insert. Two more at (0, ±43.5) on the bridges, to stop them flexing. There's only 5.7 mm of shell below the board plane there, not enough for an insert, so these take thread-forming screws. The shell has no carrier posts yet; these positions go into `collar.py` when the carrier is accepted (section 12).

Board: 2 layers, 1.6 mm FR-4, 1 oz, lead-free HASL, green. Ground pour both sides.

## 9. Power budget

Per day, 3.7 V pack side. The Kit's buck-boost is taken as 90 % efficient at these loads (est; [TPS] Fig. 7-2 to 7-4). "Measure" means the multimeter on its µA range in series with the pack. A PPK2 would do it better but is deferred.

| Load | Condition | Current | mAh/day | Source |
| --- | --- | --- | --- | --- |
| MAX-M10S | Continuous tracking, 1 Hz, default GPS+GAL+BDS | 9.5 mA VCC + 2.3 mA V_IO at 3.0 V → ~11.7 mA from the pack | 281 | [UBX] Table 15 |
| | Power-save mode instead | 5 + 2 mA → ~6.9 mA | 166 | [UBX] Table 15 |
| nRF9151 | LTE-M in PSM between reports | µA level | < 1 | Nordic; measure |
| LTE-M reports | Every 15 min | est. 10–30 | 10–30 | Size with Nordic's Online Power Profiler once the interval is set |
| ISM330DHCX board | Accel on, gyro off, plus the Adafruit regulator and power LED | unknown | ? | Measure (question 5) |
| Qwiic Buzzer idle | ATtiny84 + power LED | unknown | ? | Measure (question 5) |
| Connect Kit overhead | Interface MCU, BQ25180, TPS63901, LEDs | unknown | ? | Measure (question 5) |
| bq24074 | No input (night) | 4.3 µA typ | 0.1 | [BQ] 8.5 IBAT(PDWN) |
| TCA4307 | Disabled | 10 µA typ | 0.2 | [TCA] 5.5 |
| Dividers | VBAT 2 MΩ | 2.1 µA | 0.05 | |
| **Known total** | GNSS continuous | | **~300** + unknowns | |

Every unknown mA running all the time adds 24 mAh/day.

**Storage:** 6600 mAh, about 5,600 usable from 4.2 V down to a 3.4 V firmware cutoff (est): **~19 days without sun** at 300 mAh/day. V1's 60-day target needs the GNSS averaging ≤ ~3 mA, meaning power-save mode, or GNSS duty-cycled when the animal is far from the fence. That's firmware work, not a board change.

**Harvest:** two P124 in parallel give up to ~0.42–0.46 A in full sun [P124 Isc]. The panels face ±18.7° to either side of the spine [SHELL], so assume ~70 % of flat. Allow another 90 % for dirt and heat: ~0.28 A × peak-sun-hours. Middle Tennessee is roughly 2.5 (Dec) to 5 (Jun) peak sun hours: **~700 mAh/day in winter, ~1,400 mAh/day in summer.** That's 2–4 × the known load, before shade, hair and animals lying down. Firmware logs the real harvest from ISET_SENSE and VIN_SENSE.

## 10. Parts (preliminary, JLCPCB/LCSC)

Checked at LCSC 2026-09-26: **BQ24074RGTR C54313**, **LM66100DCKR C2869734**, **TCA4307DGKR C880333** (all extended parts, ~$3 setup fee each at JLCPCB). Schottky B5819W (SOD-123) and 2N7002 are JLCPCB basic parts. Passives from the basic 0402/0603 range, with the IN capacitor rated 25 V. PH/SH sockets, the SMD female sockets and the TVS array get picked and their LCSC numbers recorded when the schematic is written.

The Adafruit 4755 charger board we bought is no longer needed in the collar. It stays a bench reference and a fallback.

## 11. Open questions for Cody

Decisions (these change the design):

1. **Ring board, one piece, 143 × 99 mm.** Over 100 × 100 mm, so it loses JLCPCB's cheapest price tier (a few dollars more for 5). The alternative is two boards joined by a cable across a bridge. Recommend the ring. OK?
2. **Harness 5 V is input-only on this board, off unless firmware turns it on.** The collar can't charge a bay module until the BQ25798 board. OK for V1-alpha?

Bench checks when parts arrive:

3. **Pinouts against silkscreen:** the ISM330's 9-pin order (VIN, 3Vo, GND, SCL, SDA, DO, CS, INT1, INT2); the battery pack's JST-PH polarity; the 1.25 mm pigtail's red wire against the `+` on the Kit's J2.
4. **Cut the I2C pull-up jumpers** on the MAX-M10S and the Qwiic Buzzer. While you're there, the power-LED jumpers on the M10S, the buzzer and the ISM330.
5. **Idle currents**, multimeter in series with the pack: the Kit alone with USB unplugged, then plus the buzzer, then plus the IMU. Those three numbers fill the gaps in section 9.
6. **Buzzer loudness through the shell:** dB at 1 m with a phone app, lid on. It decides piezo or not for the integrated board. The shell also needs a sound port with a membrane (section 12).
7. **Heights with calipers:** the MAX-M10S from PCB to the top of the SMA, the Kit's male pins below its PCB (spacer and pin length), and a female socket's height. Section 8 uses typical values (8.5 mm socket + 2.5 mm spacer) until measured. If the PLA quick-look print exists, check the cavity is really 144 × 100 mm.
8. **Pack lead:** which end of the pack the lead leaves, and how long it is. That decides which bridge J_BAT goes on.

Not needed now:

9. The Kit's USB VBUS could feed the charger for bench charging. Left out: a diode on VBUS leaks back at high temperature and can wake the Kit's own charger. Bench-charge through J_SOLA with the bench supply at 6 V, 0.5 A limit instead.

## 12. Shell changes this implies (for `mechanical/`, after sign-off)

- Replace the per-board standoffs with carrier posts at the section 8 hole positions, top at z = 18.0.
- Keep the floor under the carrier's inner edge at or below 17.3 mm (it is now).
- A sound port for the buzzer, with an ePTFE membrane like the vent's.
- The M8 panel socket's position on the −X end wall, below the seal, near J_HBUS.
- Clearance for the plugged boards against the lid (section 8 table), re-checked once question 7 is measured.
