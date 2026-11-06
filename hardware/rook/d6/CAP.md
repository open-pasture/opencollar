# D6 CAP

D4 contoured skin around D5 internals (PR head `6b1f882`). Script: `hardware/rook/d6/cap.py`.

## Envelope

| Item | mm | Notes |
| --- | --- | --- |
| Outer W × L | **76.0 × 164.0** | Contract; D4 was 69.3×164.2 — width grown for P124 |
| Stack H | **31.0** | D4 ≈30.7; base mating 19.0 + lid above 12.0 |
| Seam Z (assembly) | **9.0** | Low seam ~0.29 of stack; lid perimeter step 3.2 mm (no hanging skirt) |
| Base H (mating) | 19.0 | Floor 6.0 + cavity 13.0 (D5) |
| Lid H (above mating) | 12.0 | Flat panel land; crown 3.5 outside land |
| Plan R / reveal | 3.0 / 0.5 | Soft plan; 0.5 inset lid |
| End nose | 32.0 taper / tip 3.0 / plan R 14.0 | D7 rounded ellipse + bullnose (was hard ~4 mm cut) |
| Panel land (flat) | 71.0 × 120.0 | Contains pocket; crown outside |
| Panel pocket | 67.2 × 114.2 × 3.1 | P124 vendor 66×113×2.6 ±0.5; +0.6/side |
| Lid under panel | 8.9 | ≥ 2.0 |
| Kit pocket | 57.6 × 21.4 × 7.5 | nRF9151 locating; J2 relief 2.6 deep |
| SMA bulkhead | Ø6.6 ±X + 10.0 AF nut seat | Adafruit 960 external; no internal GNSS recess |
| End margin math | 25.5 mm/end | 15+25 patch needs 40 → external GPS required |

## Pod interface (cap side)

| Item | Value |
| --- | --- |
| Pod anchor (world) | y = ±126.0, z = -21.9 |
| Tilt about X | ±29.14° (L +, R −) — matches d4.json |
| Mount pad size | 36.0 × 4.0 × 14.0 |
| Mount face Y | inset pads; outer envelope stays 164.0 (tilt-compensated) |
| Screws in pad | 4× Ø3.4 clear through pad (local ±10 X, two Z rows) |
| Cable / SMA | Ø6 ±Y pods; Ø6.6 SMA bulkhead ±X + nut seat |

Pod agent builds the mating pod face / fairing to these anchors.

## Clamp / saddle family (match CW `cursor/d6-cw-9a36`)

| Item | Value |
| --- | --- |
| Clamp bar | **10 × 70 × 8**, flange down (print ×8) |
| Cap clamp inserts | (±28.5, ±20) — 4 in cap (strap-along-Y) |
| Saddle W | **76** |
| Strap channel | **46.45 × 3.4** |

## Print orientation

| Part | Bed (z=0) | Supports |
| --- | --- | --- |
| `cap_base` | Underside; cavity UP; glyphs UP | None expected |
| `cap_lid` | **mating_down** | See compare below |
| `cap_floor_layout` | Underside; ribs/glyphs UP | None |

### Lid orientation compare

| Orient | Bed-face area (mm²) | Downward/support ceiling (mm²) |
| --- | --- | --- |
| Mating-down | 10808.8 | 1189.9 |
| Outer-down | 194.8 | 11907.2 |
| **Picked** | **mating_down** | |

Mating-down: panel pocket +Z, GNSS/LTE are bed recesses (small trees OK). Outer-down: flat panel land on bed; mating bosses become ceilings. Crown is shallow (2.7 mm) outside the land.

Export uses **rotation only** + `recalc_face_normals` — never `flip_normals()`.

## Floor glyphs

Reused from D5 `FLOOR_LABEL_TABLE` / `emboss_label` (DejaVu Bold): char H ≥5, stroke ≥0.8, relief ≥0.6.

Keys on cap floor: KIT, BQ, WIO, USB, POST, GNSS, LTE, PIN1, SCR1–4.

## Verification vs contract / D5

| Check | Contract / D5 | D6 | OK? |
| --- | --- | --- | --- |
| Cap width | 76 | 76.0 | YES |
| Cap length | 164 | 164.0 | YES |
| Stack ~31 | ~31 | 31.0 | YES |
| P124 pocket | 66.6×113.6×2.3 X2a | **67.2×114.2×3.1** | YES |
| P124 vendor T | 2.6 ±0.5 | PANEL_SIZE z=2.6 | YES |
| Kit pocket | 56.7×21.1 X2a | **57.6×21.4×7.5** | YES |
| J2 relief | none on X2a | 2.6 mm deep | YES |
| SMA bulkhead | Ø6.0 X2a (blocked 6.35) | **Ø6.6** | YES |
| Internal GNSS | 25.8³ recess (keep-clear FAIL) | **removed** (960 external) | YES |
| Flat panel land | required | 71.0×120.0 | YES |
| Crown ~2.7 | D4 | 3.5 outside land | YES |
| Low seam | ~z=8/27 | seam 9.0 / stack 31.0 | YES |
| Lay-flat Wio | 21.8×18.6×8 @ (22,−8) | same | YES |
| +X wall ≥3 | WIO_MIN_WALL | 5.1 mm | YES |
| Lid posts | (0,5),(0,−8) | same | YES |
| Gasket groove | 2.0×1.5 | same | YES |
| LTE shelf | D5 | kept (no GNSS recess) | YES |
| Floor glyphs real text | DejaVu table | reused D5 table | YES |
| Pod anchors | ±113.8, z−27.8, ±29.1° | same | YES |
| Print: base cavity up | yes | yes | YES |
| Print: lid | choose best | **mating_down** | YES |
| Clamp 10×70×8 / y±28.5 | CW agent | matched | YES |

### Carried from D5

All internals: kit/bq/wio pockets, U.FL slack, lid posts, gasket+lip, columns/inserts, clamp inserts, light pipes, buttons, USB-C, GNSS/LTE recesses, panel pocket+frame, floor glyphs, countersinks.

### Changed from D5

- Outer L 160→**164**; W stays 76
- Stack 25.5→**31**; lid above mating 6.5→**12** with crown + flat land
- Low wrap seam + short skirt; D7 rounded nose (ellipse + plan R + bullnose)
- Pod mount pads at ±Y ends (tilted)
- Cable exits added on ±Y toward pods
- Cap column Y lightly scaled ×164/160

## STLs

`stl/cap_base.stl`, `stl/cap_lid.stl`, `stl/cap_floor_layout.stl` — print orientation, watertight-checked (see `stl/report.json`).
