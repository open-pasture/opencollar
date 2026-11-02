# Node V1 hardware fit audit (2026-11-02, updated)

## Bottom line

**Solar:** resize the cap for **one owned Voltaic P124** (done on this branch). Do not buy P122s.

**Battery:** do **not** buy Adafruit 1781 cells. Unit #1 uses the **one owned Adafruit 353 6600 mAh pack** in a dedicated **battery pod** (left). The pack feeds the cap’s bq24074 / kit battery socket over the potted cable. The **cue pod** (right) has no battery bay.

**Buzzer:** only **one** SparkFun Qwiic Buzzer (BOB-24474) is owned. **Unit #1 recommendation: one buzzer is enough** (mono fence cues). Put it in the **cue pod**. The longer-term left/right spatial-cue design wants two (addresses **0x34** and **0x5B** via the board jumper); firmware today only talks to `0x34`. Buy a second BOB-24474 later if stereo cues are required — not blocking for unit #1.

## Where the pack lives

| Module | Role |
| --- | --- |
| Cap | MCU, LTE, GNSS, IMU, bq24074, P124, cables to both pods |
| Battery pod (left) | Adafruit 353 pack + electrodes (unwired) + ePTFE vent; power cable to cap |
| Cue pod (right) | One Qwiic Buzzer + electrodes (unwired); Qwiic/cue cable to cap |
| Counterweight | Steel only (no battery) |

Both pods still have electrode studs for later pulse work. They do **not** each need a local cell: the charger and load live in the cap, so one pack is the correct power split for the owned hardware. Mass is asymmetric (~155 g on the left) — accept for the prototype; bias the counterweight later if needed.

## Assumed — verify with calipers

| Item | CAD value | Status |
| --- | --- | --- |
| Strap thickness (`dims.STRAP.design_thickness`) | **4.0 mm** | **Assumed, verify with calipers** (not published) |
| bq24074 tallest part (`BQ_H`) | **11.0 mm** | **Assumed, verify with calipers** |
| GPS patch total height (`PATCH_H`) | **6.0 mm** | **Assumed, verify with calipers** |
| P124 outline / thickness | **113 × 66 × 3.1** from `dims.P124_PANEL` | Assumed from drawing (2.8±0.3); confirm labels are P124 |
| Adafruit 353 pack | **69 × 54 × 18 mm, 155 g** | From Adafruit / `dims.LIION_6600` |

## CAD status (this branch)

- **Cap:** 76 × 160 × 41.4 mm; one P124 pocket 66.6 × 113.6 × 1.2 (VHB — full 3.1 mm depth would hit lid inserts); `PANEL_Y = +11` deliberate for GPS; channel gable + spine V ≥45°.
- **Battery pod:** **100 × 90 × 26 mm**; pack locator 71 × 56 × 1.2; columns (±42, ±32); vent on −Y; crest cable +X.
- **Cue pod:** **92 × 68 × 26 mm**; buzzer at (0, 10); sound port +Y; no battery bay.
- **Clamp / strap:** shared 70 mm bars, clamp Y ±29.5, channel follows strap (fits P2S 256×256 easily).
- Clearances PASS vs pack / buzzer / electrodes in the part builds.

## Parts list (battery)

| Item | Qty | Notes |
| --- | --- | --- |
| Adafruit 353 3.7 V 6600 mAh | **1 (owned)** | Battery pod |
| Adafruit 1781 protected 18650 | **0 — do not buy** | Superseded by the 353 |

## Buzzer (plain)

- **What each buzzer is for:** left/right audio fence cues on the neck (~30° cattle MAA; BUILD-LOG / carrier SPEC).
- **I2C:** default **0x34**; a second board remaps to **0x5B** with the address jumper. Firmware (`buzzer.c`) hardcodes `0x34` only.
- **Owned:** 1. **Unit #1: one buzzer in the cue pod is enough.** Optional later: second BOB-24474 for stereo.

## Ask Cody

1. Confirm panels are P124s (photo of backs/labels).
2. Calipers: strap thickness, bq24074 height, GPS patch height.
3. Accept left-side ~155 g pack asymmetry for unit #1, or say if the pack should move.
