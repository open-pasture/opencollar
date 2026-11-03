# Bill of materials

![Parts layout](photos/2026-09-25-parts-layout.jpg)

| Part | Model | Qty | Role | Notes |
| --- | --- | --- | --- | --- |
| Main board | Makerdiary nRF9151 Connect Kit | 1 | MCU + LTE-M/NB-IoT modem + GNSS | nRF9151 SiP (Cortex-M33). nRF52820 interface MCU gives CMSIS-DAP flashing and USB-UART over USB-C. BQ25180 LiPo charger, TPS63901 buck-boost. Nano-SIM slot. U.FL for LTE and GPS. Onboard GNSS LNA, enabled by nRF9151 `COEX0`. Firmware: nRF Connect SDK / Zephyr. |
| LTE antenna | Flexible adhesive antenna, U.FL | 1 | Cellular | 3M 300LSE adhesive backing. Connects to the `LTE` U.FL. |
| GPS antenna | Ceramic patch, 1575R-A, U.FL | 1 | GNSS | Connects to the `GPS` U.FL. Ceramic face points at the sky. |
| Buzzer | SparkFun Qwiic Buzzer (BOB-24474) | 1 (owned) | Audio cue | I2C default 0x34; a second board’s address is set in software with `setAddress()` (JP1 is volume only). CAD draws one per pod; mono vs stereo is Cody’s open call. |
| Battery | Adafruit 1781 protected 18650 | 2 (pending Cody’s purchase approval) | Collar power | One cell per dual-cell pod — plan of record. |
| Battery | Adafruit 353 3.7 V 6600 mAh | 1 (owned) | Spare | PROPOSED ALTERNATIVE, NOT APPROVED (battery/cue pods under `hardware/rook/stl/alt_pods_unapproved/`); dual-cell pods remain the plan of record. |
| Battery | PKCELL LP503562, 3.7V 1200mAh LiPo | 1 | Power | 2-wire lead with connector. Polarity must be checked against the board before connecting. |
| Jumper wires | Dupont female-female, ribbon | 1 set | Bench wiring | |
| Cap lid screws (gable v3) | M3×40 button head ISO 7380 A2/304 + M3 bonded sealing washer | 8 | Through the 41.4 mm gabled base into lid inserts |
| Cap lid screws (slim / saddle) | M3×18 button head ISO 7380 A2/304 + M3 bonded sealing washer | 8 | Through the 19 mm slim base into lid inserts (seat z=4; M3×20 bottoms) |
| Cap clamp screws (gable v3) | M3×8 button head | 4 | Cap clamp bars flush on underside |
| Cap clamp screws (slim / saddle) | M3×14 button head | 4 | Bar+saddle+0.6 gap → mouth 10.5; tip 3.5 into blind pocket (M3×16 risks seal) |
| Heat-set inserts | Adafruit 4255 M3×4 brass | 36 of 50 owned | Cap 12 (8 lid + 4 clamp), pods 16, CW 8. Iron ~220 °C PLA / ~245 °C ASA; press flush. |

Cap styles and stack math: `hardware/rook/cad/SADDLE.md`. Gable STLs: `hardware/rook/stl/node_v1_cap/`. Slim + saddle: `hardware/rook/stl/node_v1_cap_saddle/`.

## Still needed

| Part | Why |
| --- | --- |
| Nano-SIM with LTE-M data | Board can't reach the network without one. Hologram, Onomondo, Soracom, or 1NCE. |
| Qwiic to female-jumper cable (SparkFun PRT-14988) or 4-pin 0.1" header + soldering iron | Dupont jumpers can't plug into the buzzer as-is. |
| USB-C data cable | Flashing, serial logs, charging. |
| 8 × M3×40 button head (ISO 7380) + M3 bonded sealing washers | Gable v3 lid screws; needed for the tall 41.4 mm base fit-test set. |
| 8 × M3×18 button head (ISO 7380) + M3 bonded sealing washers | Slim / saddle lid screws (19 mm base; see SADDLE.md). |
| 4 × M3×14 button head | Slim / saddle clamp screws (round down for blind pocket). |
