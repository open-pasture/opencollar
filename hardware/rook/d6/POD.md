# D7 Pod — tapered D4 silhouette + D5 internals

Branch: `cursor/d7-pod-9a36` (from d6-integrate `96f3b30`).
Script: `hardware/rook/d6/pod.py`. STLs: `stl/`. Renders: `renders/`. Review: `review/pod_review.blend`.

## Intent

op-brand on D6: pods read as flat 92 mm slabs bolted in a row. D7 restores D4_contoured_v3’s one continuous tapered object: **92 mm only over the cell bay**, tips narrow toward D4’s **~67 mm**, generous plan radii, chamfered shoulder, stronger tip roof drop. Mount face / cavity / lid / glyphs stay locked so the parallel cap/fairing agent (`cursor/d7-cap-9a36`) still meets.

## Mount transform (LOCKED — do not move)

| Side | Location (mm) | Rotation about X |
| --- | --- | --- |
| L | `(0, -126.0, -21.9)` | `+29.142°` |
| R | `(0, +126.0, -21.9)` | `−29.142°` |

Frame: origin at cap centre; X across strap; Y along spine; Z up. Cap agent must keep matching mount faces / fairing lands at these anchors. Joint: **36×4×14** pad recess + **4× M3 clear** on the +Y local face (same hole pattern / face plane as d6-integrate). R is a true mirror of L (`Scale −X` + one `flip_normals` for winding).

## Outer envelope

| Item | D7 | D6 | D4 ref |
| --- | --- | --- | --- |
| Swell X (cells) | **92** | 92 flat | 67 |
| Tip X | **~70 → ~66** at nose (R8) | 92 | 67 |
| Length Y | **92** (mount face locked) | 92 | 97 |
| Base H (mating) | **22.2** + tip roof drop 5.5 | 22.2 / soft 3.5 drop | 19.4 |
| Lid | **4.0** contoured | 4.0–4.2 flat | 6.4 |
| Cavity | **82 × 58 × 19.5** | same | (no cells) |
| Plan R | **8** tip / **10** swell | 7 | contoured |
| Shoulder | chamfer 92→70 over 7 mm Y | none | smooth |
| Wall at cells | **5.0** (3.5–5 allowed) | 5.0 | — |
| Wall outside cells | tip skin ~2.6 equiv (taper) | 5 all around | — |

X stays 92 only where the 82 mm cavity needs wall; Y kept at 92 so `±POD_W/2` mount faces still meet the cap pads. Cannot reach D4’s 19.4 base height with a 19.5 cavity + 1.5 floor — tip roof drop carries the thinner read.

## Internals (unchanged from D5 / D6)

| Feature | Value |
| --- | --- |
| Cell bay | Ø19.4 × 76 along X at `CELL_AT=(-2,-8)`; Adafruit 1781 |
| Buzzer | pocket 26.2² at `(18, 15)`; port Ø8 + mesh seat on +Y wall |
| Cable | Ø6 through +Y (cap-facing) + **D8 × 1.2** countersink |
| Gasket groove | W=2.0, D=1.5; on **cavity+wall** rect 92×68 (inside swell); inner land ≥ 2.0 |
| Reg lip | 1.2 mm ring on same envelope |
| Screw bosses | `POD_COLS = (±37, ±27)`; insert Ø4 × 5 |
| Lid | 4.0 mm; landing ring; cross-ribs clear of cell; two Ø6 × 1.8 mating posts |
| Floor ribs | cell rails under cradle |

## Floor glyphs (D5 `FLOOR_LABEL_TABLE`)

DejaVu Sans Bold. Char height ≥ 5 mm, stroke ≥ 0.8 mm, relief ≥ 0.6 mm.

On `pod_*_base` and `pod_floor_layout`: `BATT`, `PLUS`, `MINUS`, `BUZZ`, `PIN1` (arrow toward +Y cable/cap), `SCR1`–`SCR4`.

## Print orientation

| Part | Bed (z=0) | Notes |
| --- | --- | --- |
| `pod_*_base` | underside; cavity UP | glyphs/ribs face +Z |
| `pod_*_lid` | **OUTER face DOWN** | modeled mating-at-z=0; export rotates **180° about X** + recalc normals — **never** `flip_normals()` for orientation |
| fairings | long axis on bed | slope = WALL (unchanged this branch; cap agent rebuilds) |
| `pod_floor_layout` | underside; ribs UP | PLA coupon |

## Fairings (stand-ins; cap agent owns redesign)

| Part | Envelope (approx) |
| --- | --- |
| `fairing_cap_pod_L/R` | **88 → 66 × 18 × 14** |
| `fairing_pod_strap_L/R` | **88 → 66 × 28 × 14** |

Pod end interface (mount face Y, recess, holes) unchanged so redesigned fairings/cap ends can meet.

## What moved (D6 → D7)

| Item | Change |
| --- | --- |
| Plan outline | Flat 92×92 → swell 92 over cells + taper to ~70 tip |
| Plan radius | 7 → 8 (tips) / 10 (swell) |
| Shoulder | added chamfered 92→70 over 7 mm Y |
| Tip roof drop | 3.5 / 18 mm → 5.5 / 22 mm |
| Groove/lip envelope | full 92×92 → cavity+wall 92×68 (inside swell) |
| Lid plan | matching contoured outline + reveal |
| Volume (L base) | ~85k → ~69k mm³ |
| Mount / cavity / buzzer / glyphs / lid T | **unchanged** |

## Verification

| Check | Status |
| --- | --- |
| Mounts y=±126, z=−21.9, ±29.142°; face plane / hole pattern | PASS (locked) |
| Two-cell cavity 82×58×19.5; wall ≥4 at swell | PASS |
| Tip width toward D4 67; swell ~92 | PASS (`assembly_check`) |
| Plan R ≥ 8; contoured_slab | PASS |
| Gasket inner land ≥ 2 mm; lid 4.0 + ribs | PASS |
| Buzzer (18,15); cable D8×1.2 | PASS |
| Real glyphs; R = true mirror; lid outer-down | PASS |
| Print STLs z=0, watertight, ≤256³ | PASS |
| Assembly `assembly_check.py` | **109+ / 109+** |

## Honest rough edges

1. **Length still 92, not D4’s 97** — lengthening would move the mount face; locked for the parallel cap agent.
2. **Stack still ~26 mm, not D4’s ~19.4** — 19.5 cavity + floor forbids a 19.4 shell; tip roof drop is the visual lever.
3. **Base glyph boolean still needs voxel remesh** (~0.32–0.40) for watertight export; softens micro-edges slightly.
4. **Fairings still 88-wide D6 stand-ins** — narrower tips mean less blend volume; cap/fairing agent should retaper them to the new nose.
5. **CW “visually lower/smaller than pods”** is owned by the CW/cap pass; pods are less slabby but still the larger of the two until CW shrinks.

## Build

```bash
cd hardware/rook/d6
blender --background --factory-startup --python pod.py
python3 assembly_check.py
```
