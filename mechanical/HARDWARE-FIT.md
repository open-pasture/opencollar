# Node V1 hardware fit audit (2026-11-02, updated)

## Bottom line

**Solar:** resize the cap for **one owned Voltaic P124** (done). Do not buy P122s.

**Battery (plan of record):** unit #1 uses **2 × Adafruit 1781** protected 18650 cells (one per dual-cell pod). Cody is placing the purchase. The owned Adafruit 353 pack is **not** the plan of record; an unapproved battery-pod / cue-pod redesign lives under `exports/alt_pods_unapproved/`.

**Buzzer:** one SparkFun Qwiic Buzzer (BOB-24474) is owned; the dual-cell CAD draws one buzzer per pod. **Mono vs stereo is still Cody’s open call** — do not assert that one buzzer is enough. I2C default **0x34**; a second board’s address is set in software with the SparkFun library’s `setAddress()` (see Example_10_Buzz_Multiple.ino). The board’s only documented jumper, **JP1, is for volume**, not address. Firmware (`buzzer.c`) hardcodes `0x34` today.

## Where the cells live

| Module | Role |
| --- | --- |
| Cap | MCU, LTE, GNSS, IMU, bq24074, P124, cables to both pods |
| Left pod | 1 × Adafruit 1781 + 1 × Qwiic Buzzer + electrodes (unwired) |
| Right pod | 1 × Adafruit 1781 + 1 × Qwiic Buzzer + electrodes (unwired) |
| Counterweight | Steel only (no battery) |

Both pods are identical mirrors (92 × 68 × 24.5). Electrode studs stay for later pulse work.

## Assumed — verify with calipers

| Item | CAD value | Status |
| --- | --- | --- |
| Strap thickness (`dims.STRAP.design_thickness`) | **4.0 mm** | **Assumed, verify with calipers** (not published) |
| bq24074 tallest part (`BQ_H`) | **11.0 mm** | **Assumed, verify with calipers** |
| GPS patch total height (`PATCH_H`) | **6.0 mm** | **Assumed, verify with calipers** |
| P124 outline / thickness | **113 × 66 × 3.1** from `dims.P124_PANEL` | Assumed from drawing (2.8±0.3); confirm labels are P124 |
| Adafruit 1781 cell | **Ø18.4 × 69 mm, ~46 g** | Protected 18650; Cody ordering 2× |

## CAD status (this branch)

- **Cap:** 76 × 160 × 41.4 mm; one P124 pocket 66.6 × 113.6 × 1.2 (VHB — full 3.1 mm depth would hit lid inserts); `PANEL_Y = +11` deliberate for GPS; channel gable + spine V ≥45°. Cap CAD unchanged in this follow-up.
- **Pod (plan of record):** **92 × 68 × 24.5 mm** base / lid 6 mm; cell at (−2, −13); buzzer at (20, 15); columns (±37, ±27); sound port +Y; crest cable +X. Export: `exports/node_v1_pod/`.
- **Unapproved alternative:** battery pod 100×90×26 (Adafruit 353) + cue pod 92×68×26 under `exports/alt_pods_unapproved/` — not the plan of record.
- **Clamp / strap:** shared 70 mm bars, clamp Y ±29.5, channel follows strap (fits P2S 256×256 easily).
- Clearances PASS vs cell / buzzer / electrodes in the part builds (rebuild and report bounding boxes on this branch).

## Parts list (battery)

| Item | Qty | Notes |
| --- | --- | --- |
| Adafruit 1781 protected 18650 | **2 (Cody ordering)** | One per dual-cell pod — plan of record |
| Adafruit 353 3.7 V 6600 mAh | **1 (owned)** | Spare / unapproved alt-pod layout only |

## Buzzer (plain)

- **What each buzzer is for:** left/right audio fence cues on the neck (~30° cattle MAA; BUILD-LOG / carrier SPEC).
- **I2C:** default **0x34**; second board → **0x5B** via `setAddress()` in software (not a board jumper). **JP1 is volume only.**
- **Owned:** 1. CAD draws one per pod. **Mono vs stereo: Cody’s open call.**

## Ask Cody

1. Confirm panels are P124s (photo of backs/labels).
2. Calipers: strap thickness, bq24074 height, GPS patch height.
3. Mono vs stereo buzzer for unit #1 (one owned vs buy a second BOB-24474).
4. Confirm 1781 purchase / delivery so pods can be fitted.
