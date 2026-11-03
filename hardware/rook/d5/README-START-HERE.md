# D5 production — start here

**Status:** draft / printable parametric CAD (audit fix). **Not** field-ready. **Not** for animal until welfare review (PR #2).

**Print first:** `coupons/fit_coupon.stl` (PLA) → confirm board + cell + insert fit → then shells.

## Rebuild

```bash
cd hardware/rook/d5/cad
blender --background --factory-startup --python build_d5.py
```

## Open decisions — Cody

1. **FIT HEIGHT (blocking for upright radio / socketed kit).** Cap free height ≈ **14.3 mm**. Upright Wio-SX1262 needs ~**23 mm** (+20 mm wire bend). Connect Kit with socketed headers needs ~**17 mm**. **Neither fits.** Production CAD uses:
   - **Lay-flat Wio** pocket 21.8 × 18.6 × **8** mm
   - **Low-profile kit** (no headers) 56.7 × 21.1 × **7.2** mm  
   Cody choose: **(A)** keep lay-flat / low-profile, **(B)** raise cap cavity ≥23 mm (hurts brand / pod-lower look), **(C)** solder headers / remote radio.
2. **P124 on cap** — OPEN. Pocket retained. Cap stays **76 mm** while panel is in play.
3. **Cap width vs brand ≤1.3× strap (~57.8 mm).** Conflict while P124 is in play. If panel dropped → `CAP_W_SLIM = 58`.
4. **Mono vs stereo buzzer; 1781 purchase** — HARDWARE-FIT.

## Brand conditions (this revision)

| Condition | Status |
| --- | --- |
| Pods visibly lower than cap | **Yes** — pod stack 25.0 mm < cap 25.5 mm |
| Cap ≤1.3× strap | **Flagged** — 76 vs 57.8 while P124 OPEN |
| Fairings 25–30 mm blend, R7 / R2.5 | **Yes** — 28 mm run, R7 plan + R2.5 edge |
| Orange latch + 3 farmer end screws | Yes |
| ROOK-001 label + coupon | Yes |
| CW free of electronics | Yes |

## Firmware pockets (board + 0.4 mm/side)

| Part | Pocket (mm) | Where |
| --- | --- | --- |
| Rook Connect Kit (low-profile) | 56.7 × 21.1 × 7.2 | Cap −Y (headers ~17 **nofit**) |
| bq24074 | 38.9 × 33.8 × 12 | Cap (not potted) |
| Wio-SX1262 **lay-flat** | 21.8 × 18.6 × 8 | Cap +X (upright 23 **nofit**) |
| Buzzer + **rimmed** mesh | 26.2 × 26.2 | Each pod |
| 18650 1781 | Ø19.2+0.2 × 70+6 | Each pod (353 **not** approved) |
| GNSS / LTE / LoRa | crest +Y | Metal keepout 12 mm |
| CW tub | — | **Steel only** |

## Corrected plate list (op-maker Orca, open-cavity STLs)

| Plate | Parts | P2S PLA | P2S ASA |
| --- | --- | --- | --- |
| **P0** | fit + label coupon (**print first**) | 0h58 / 27.5 g | 1h11 / 29.8 g |
| **P1** | cap + both pods (base+lid) | 11h25 / 267 g | 11h07 / 243 g |
| **P2** | CW, saddle, 4 fairings, clamps, plugs, latch, mesh, buckle, keeper | 7h31 / 180 g | 7h19 / 161 g |
| **Collar (P1+P2)** | | **18h56 / 447 g** | **18h26 / 404 g** |
| P3 spares | 4 clamps, 3 orange, latch, 2 mesh, 2 usbc | 0h37 | 0h36 |
| P3b | spare cap_lid | 2h22 | 2h23 |

220 bed: collar ~5 plates / ~24 h / 490 g. TPU `usbc_cap` = separate soft plate. Details: `plates/PLATES.md`.

## Audit fixes in this revision

- Base `reg_lip` is a **ring** (was a solid plate sealing cavities).
- Fit coupon gauges open through the top (no 0.2–0.3 mm skin).
- U.FL slack clear of charger; kit clear of screw columns.
- Cap lid: **landing-ring groove**, print outer-face down (was ~39% support recess).
- `buzz_mesh` has a continuous **rim** (one part). Buckle cross-bar fused to frame.
- Height conflict documented — no guessed raise; lay-flat / low-profile options + Cody flag.

## Paths

| Path | Contents |
| --- | --- |
| `cad/d5_dims.py` | Dims, pockets, `FIT_HEIGHT_NOTE`, `CODY_FLAGS` |
| `cad/build_d5.py` | Blender builder |
| `stl/` | Printable STLs + `report.json` |
| `coupons/` | Fit + label coupons |
| `D5-PRODUCTION.md` / `MATERIALS.md` / `SPARES.md` | Detail docs |
