# D5 production — start here

**Status:** draft / printable parametric CAD. **Not** field-ready. **Not** for animal until welfare review (PR #2).

**Print first:** `coupons/fit_coupon.stl` (PLA) → then optional `stl/cap_floor_layout.stl` + `stl/pod_floor_layout.stl` for floor assembly layout → then shells.

## Rebuild

```bash
cd hardware/rook/d5/cad
blender --background --factory-startup --python build_d5.py
```

All exported STLs are in **intended print orientation** (bed face at `z=0`). Lids are flipped on export so the **outer face is on the bed**.

## Decisions (closed)

| ID | Status | Date | Note |
| --- | --- | --- | --- |
| **P124 solar panel** | **KEPT** on collar #1 | **2026-11-03** (Cody) | Pocket + **15 mm** keep-clear retained; cap stays **76×160** |
| Fit height | **Option A** | 2026-11-03 | Lay-flat Wio + low-profile kit (no headers) |

## Still open — Cody

1. Fit height B/C only if Option A is revisited (upright Wio / raise cavity).
2. Mono vs stereo buzzer; 1781 purchase — HARDWARE-FIT.
3. **Light-gray colourway** — proposed; **PENDING op-brand** (charcoal + orange remain locked accents).

## Brand / durability

| Condition | Status |
| --- | --- |
| Cap width vs 1.3× strap | **Accepted conflict** — 76 vs 57.8 because P124 KEPT |
| Pods vs cap height | Pod stack 26.0 vs cap 25.5 (lid ≥4.0 durability) |
| Fairings 25–30 mm, R7 / R2.5 | Yes |
| CW free of electronics | Yes |

## Print orientation (exported STL z=0 = bed)

| Part | Face at z=0 (bed) | Notes |
| --- | --- | --- |
| `cap_base`, `pod_*_base`, `cw_tub` | Outer underside | Cavity opens +Z |
| `cap_lid`, `pod_*_lid`, `cw_lid` | **Outer face** (flipped on export) | GNSS/LTE openings face +Z |
| `saddle` | Roof | Channel opens +Z |
| `clamp_bar` | Flange | Channel opens +Z; load along Y WITH layers |
| `cap_floor_layout`, `pod_floor_layout`, `cw_floor_layout` | Floor underside | Ribs/glyphs UP |
| Small parts / coupons | Flat as built | — |

## Plate list (est. from Orca baseline + durability)

| Plate | Parts | P2S PLA (est) | P2S ASA (est) |
| --- | --- | --- | --- |
| **P0** | fit + label (+ optional floor layouts) | ~1h10 | ~1h25 |
| **P1** | cap (+posts) + pods (lid≥4) | ~12h06 / ~283 g | ~11h48 / ~257 g |
| **P2** | CW, saddle, fairings, channel clamps, … | ~8h06 / ~195 g | ~7h54 / ~174 g |
| **Collar (P1+P2)** | | **~20h12 / ~478 g** | **~19h42 / ~431 g** |

Re-slice before print. TPU `usbc_cap` separate.

## Paths

| Path | Contents |
| --- | --- |
| `cad/d5_dims.py` | Dims, `DECISIONS`, panel KEPT, 15 mm keep-clear |
| `cad/build_d5.py` | Builder; `FLOOR_GLYPHS`; print-orient export |
| `stl/` | All parts + `*_floor_layout.stl` + `report.json` |
| `MATERIALS.md` | Materials + colourway pending + panel KEPT note |
