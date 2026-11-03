# Node V1 hardware fit audit (2026-11-02, updated)

## Bottom line

**Solar:** resize the cap for **one owned Voltaic P124** (done). Do not buy P122s.

**Battery (plan of record):** unit #1 uses **2 × Adafruit 1781** protected 18650 cells with the original dual-cell pods (pending Cody’s purchase approval). The battery-pod / cue-pod redesign (100×90×26 with the Adafruit 353 + 92×68×26 cue) is a **PROPOSED ALTERNATIVE, NOT APPROVED**, awaiting Cody’s decision; the as-drawn dual-cell pods remain the plan of record. Those unapproved STLs (formerly `exports/node_v1_pod_battery` and `exports/node_v1_pod_cue`) live under `stl/alt_pods_unapproved/`.

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
| Adafruit 1781 cell | **Ø18.4 × 69 mm, ~46 g** | Protected 18650; 2× pending Cody’s purchase approval |

## CAD status (this branch)

- **Cap styles** (`CAP_STYLE` / `OC_CAP_STYLE` in `cad/lib/node_v1.py`):
  - **`gable` (v3, fit-test):** 76 × 160 × **41.4** mm; channel gable + spine V ≥45°; export `stl/node_v1_cap/` (**do not overwrite** when building saddle). Lid screws **M3×40**; clamp **M3×8**.
  - **`saddle` (slim, plan moving forward):** flat underside (bed face; blind pin sockets Ø4.35×2), floor **6.0** + cavity **13** → base **19.0** mm; saddle **76 × 80 × 5.9** with roof pins (bbox 7.4); export `stl/node_v1_cap_saddle/`. Lid **M3×16**; clamp **M3×14**. Stack strap→lid top **~32.5 mm**. Assembly aids REV AID1: `cad/ASSEMBLY-AIDS.md`. Design note: `cad/SADDLE.md`.
- **Both styles:** one P124 pocket 66.6 × 113.6 × 1.2 (VHB); `PANEL_Y = +11` deliberate for GPS; 8 lid + 4 clamp insert columns; O-ring groove; potted Ø6 cable entries. Footprint **76×160** kept (P124 + patch). `CAP_WALL` stays **5.0** (4.0 deferred).
- **Pod (plan of record):** **92 × 68 × 24.5 mm** base / lid 6 mm; cell at (−2, −13); buzzer at (19.5, 15); columns (±37, ±27); sound port +Y; crest cable +X. Export: `stl/node_v1_pod/`.
- **PROPOSED ALTERNATIVE, NOT APPROVED:** battery pod 100×90×26 (Adafruit 353) + cue pod 92×68×26 under `stl/alt_pods_unapproved/` (was `node_v1_pod_battery` / `node_v1_pod_cue`); dual-cell `stl/node_v1_pod/` remains the plan of record.
- **Clamp / strap:** shared 70 mm bars, clamp at (±20, ±28.5) on the cap (pod/CW still ±29.5), channel 46.45 × 3.4 follows strap (fits P2S 256×256 easily). Saddle style: same bars/positions; screws pass through the saddle into underside inserts (blind to the cavity).
- Clearances PASS vs kit / bq24074 / IMU / patch / P124 in the saddle build (`renders/node_v1_cap_saddle/report.json`).

## Parts list (battery)

| Item | Qty | Notes |
| --- | --- | --- |
| Adafruit 1781 protected 18650 | **2 (pending Cody’s purchase approval)** | One per dual-cell pod — plan of record |
| Adafruit 353 3.7 V 6600 mAh | **1 (owned)** | Spare; only for the PROPOSED ALTERNATIVE (not approved) alt-pod layout |

## Fasteners (cap / pods / CW)

| Item | Qty | Notes |
| --- | --- | --- |
| M3×40 button head (ISO 7380, A2/304) + M3 bonded sealing washer | **8** | **Gable v3 only** — lid through-screws through the 41.4 mm base |
| M3×16 button head (ISO 7380, A2/304) + M3 bonded sealing washer | **8** | **Saddle / slim** — lid through-screws (seat z=4; through 15; ~3 mm grip / 2 mm pocket spare; M3×18 can bottom) |
| M3×8 button head | **4** | **Gable v3** cap clamp bars |
| M3×14 button head | **4** | **Saddle / slim** clamp (to mouth 10.5; tip 3.5 in blind pocket — round down; M3×16 risks seal) |
| M3×4 brass heat-set inserts (Adafruit 4255) | **36 of 50 owned** | Cap 12 (8 lid + 4 clamp), pods 16 (8 each ×2), CW 8 |

**Insert install:** iron ~220 °C for PLA, ~245 °C for ASA; press until flush with the pocket mouth. Slim-cap clamp pockets are shallower (keep-out to cavity); do not drive inserts past flush.

## Buzzer (plain)

- **What each buzzer is for:** left/right audio fence cues on the neck (~30° cattle MAA; BUILD-LOG / carrier SPEC).
- **I2C:** default **0x34**; second board → **0x5B** via `setAddress()` in software (not a board jumper). **JP1 is volume only.**
- **Owned:** 1. CAD draws one per pod. **Mono vs stereo: Cody’s open call.**

## Ask Cody

1. Confirm panels are P124s (photo of backs/labels).
2. Calipers: strap thickness, bq24074 height, GPS patch height.
3. Mono vs stereo buzzer for unit #1 (one owned vs buy a second BOB-24474).
4. Confirm 1781 purchase / delivery so pods can be fitted.
