# D6 Pod — D4 contour skin + D5 internals

Branch: `cursor/d6-pod-9a36`. Base: D5 `6b1f882` (`cursor/d5-productionize-9a36`).
Script: `hardware/rook/d6/pod.py`. STLs: `stl/`. Renders: `renders/`. Review: `review/pod_review.blend`.

## Intent

Cody: D4 contoured look, D5 layout/buildability. Pods hang off the cap ends on D4 mounts; two-cell cavity, gasket, glyphs, and lid rules from D5.

## Mount transform (from `d4.json` / D4_contoured_v3)

| Side | Location (mm) | Rotation about X |
| --- | --- | --- |
| L | `(0, -113.830, -27.839)` | `+29.142°` |
| R | `(0, +113.830, -27.839)` | `−29.142°` |

Frame: origin at cap centre; X across strap; Y along spine; Z up. Cap agent must put matching mount faces / fairing lands at these anchors. R is a true mirror of L (`Scale −X` + one `flip_normals` for winding) — not a print-orientation flip.

## Outer envelope

| Item | D6 | D4 ref | D5 ref |
| --- | --- | --- | --- |
| Base outer (X×Y×Z) | **92 × 97 × 22** | 67 × 89–97 × 19.4 | 92 × 68 × 22 |
| Lid outer | 91 × 96 × 4.0 | 61.5 × 97 × 6.4 | 91 × 67 × 4.0 |
| Cavity | **82 × 58 × 19.5** (kept) | (no cells) | 82 × 58 × 19.5 |
| Stack | 26.0 | ~25.8 | 26.0 |
| Plan radius | 7.0 | contoured | 7.0 |
| Tip taper | 18 mm run, 3.5 mm roof drop | hard 4→19 over ~20 mm | none |

X grown 67→92 so the 82 mm cell cavity fits; Y kept ~97 for the D4 length look; walls 5 mm.

## Internals (from D5)

| Feature | Value |
| --- | --- |
| Cell bay | Ø19.4 × 76 along X at `CELL_AT=(-2,-8)`; Adafruit 1781; 353 pack NOT approved |
| Buzzer | pocket 26.2² at `(18, 15)`; port Ø8 + mesh seat on +Y wall |
| Cable | Ø6 through +Y (cap-facing) + **D8 × 1.2** countersink |
| Gasket groove | W=2.0, D=1.5; **inner land ≥ 2.0**; outer land 1.0 |
| Reg lip | 1.2 mm ring |
| Screw bosses | `POD_COLS = (±37, ±27)`; insert Ø4 × 5 |
| Lid | 4.0 mm; landing ring; cross-ribs clear of cell; two Ø6 × 1.8 mating posts |
| Floor ribs | cell rails under cradle |

## Floor glyphs (D5 `FLOOR_LABEL_TABLE` @ 6b1f882)

DejaVu Sans Bold. Char height ≥ 5 mm, stroke ≥ 0.8 mm, relief ≥ 0.6 mm (solidify 0.75 − embed 0.15).

On `pod_*_base` and `pod_floor_layout`: `BATT`, `PLUS`, `MINUS`, `BUZZ`, `PIN1` (arrow toward +Y cable/cap), `SCR1`–`SCR4`.

## Print orientation

| Part | Bed (z=0) | Notes |
| --- | --- | --- |
| `pod_*_base` | underside; cavity UP | glyphs/ribs face +Z |
| `pod_*_lid` | **OUTER face DOWN** | modeled mating-at-z=0; export rotates **180° about X** + recalc normals — **never** `flip_normals()` for orientation |
| fairings | long axis on bed | slope = WALL |
| `pod_floor_layout` | underside; ribs UP | PLA coupon |

### Lid bed face / supports

- Bed-face area ≈ **6957 mm²** (near-full 91×96 outer).
- Soft tip taper only (not a deep crown) → **no large supports** expected for the outer shell.
- Optional tiny supports under mating-face ribs/posts if the slicer treats them as bridges.

## Fairings (agree with CW `05ef563`)

| Part | Envelope (approx) |
| --- | --- |
| `fairing_cap_pod_L/R` | **66 × 28 × 14** (W0=66, W1=50, run=28, H=14) |
| `fairing_pod_strap_L/R` | **66 × 28 × 14** (same family) |

## Assembly agree — owned by CW agent (pods do not re-export)

| Item | Match |
| --- | --- |
| Clamp bar | 10 × 70 × 8; flange down; holes at y=±28.5; **8 total** |
| Saddle | width **76**; strap channel **46.45 × 3.4** |
| CW fairings | ~66 × 28 × 14 |

## STLs (`stl/`)

`pod_L_base`, `pod_L_lid`, `pod_R_base`, `pod_R_lid`, `fairing_cap_pod_L/R`, `fairing_pod_strap_L/R`, `pod_floor_layout` — all print-oriented, watertight-checked (`stl/pod_report.json`).

## Verification vs contract / D5

| Check | Status |
| --- | --- |
| D4 mounts y=±113.8, z=−27.8, ±29.1° about X | PASS (113.830 / −27.839 / 29.142) |
| Two-cell cavity 82×58×19.5 | PASS |
| Grow envelope from D4 67×97; keep D4 length look | PASS (92×97×22) |
| Gasket inner land ≥ 2 mm | PASS (2.0) |
| Lid 4.0 + ribs | PASS |
| Buzzer (18,15) clear of cell | PASS |
| Cable countersink D8×1.2 | PASS |
| Real embossed glyphs ≥5 / 0.8 / 0.6; one table | PASS (D5 table) |
| Screw order numbers + polarity + PIN1 | PASS |
| R = true mirror, fixed normals | PASS |
| Lid outer-down via 180° X (no flip_normals) | PASS |
| Fairings ~66×28×14 (CW agree) | PASS |
| Print STLs at z=0 | PASS |
| Cap agent: mount faces at same anchors | **MUST MATCH** |
| Cap agent: fairing_cap_pod lands | **MUST MATCH** |

## Cap / CW agents — match these

1. **Mount empties** exactly as above (cap end fairings land on pod +Y local / mount face).
2. **Fairing family** 66×28×14; clamp 10×70×8 ×8; saddle 76 / channel 46.45×3.4 (CW already).
3. Pod cable exits toward cap on the mount end (+Y local before world rot).
4. Glyph + lid-flip pattern = D5 `6b1f882`.

## Build

```bash
cd hardware/rook/d6
blender --background --factory-startup --python pod.py
```
