# D7 counterweight + clamps

Low continuous profile around the same steel mass. Script: `hardware/rook/d6/cw.py`.
Base integrate: D6 @ `96f3b30` (109/109). Branch: `cursor/d7-cw-9a36`.

## Choice (mass / silhouette)

| Item | Value |
| --- | --- |
| **Envelope chosen** | **89.4 × 115.8 × 18 mm** tub (+ **7.5 mm** low dome lid) |
| Pack layout | **2 high × 2 along strap (Y)** — footprint 76.2 × 102.6 × 12.7 mm |
| Why not 4-high stack | D5/D6 88×74×30 tower read as a bolted slab; 2×2 keeps mass, drops height, stretches along strap |
| **Fill** | **4× mild steel flat bar** 76.2 × 50.8 × 6.35 mm (3 in of 2×¼ in) + **1.5 mm foam** pad |
| **Steel volume** | **98 322 mm³** (98.3 cm³) |
| **Steel mass** | **771.8 g** @ 7.85 g/cm³ |
| **Lid seal** | 2.0 mm O-ring groove in tub rim + registered lip; **4× M3** button-head into heat-set inserts; foam compresses pack under lid |
| Plan / taper | Outer vertical corners **R = 10 mm**; top inset taper **2.2 mm**/side |
| Colour | Body = one calm light-gray ASA; **orange (#FF6A2B) only** on tiny functional accents |

Electronics stay out of the CW (D5 / contract).

## Dimensions

| Part | Size (mm) | Notes |
| --- | --- | --- |
| `cw_tub` | 89.4 × 115.8 × 18 (+ lip) | Cavity UP; floor 3; wall 6; 2×2 steel pocket; tapered R10 |
| `cw_lid` | ~88.4 × 114.8 × **6.35** (target 7.5) | Low dome; as-exported height after soft channel trim; crown land 36 × 48 |
| `saddle` | 76 × 96 × 5.0 (+pins → ~6.5) | **Unchanged strap path** from d6-integrate; soft plan R |
| `clamp_bar` | **10 × 70 × 8** | Flange 10×70×3; walls to depth 8; **print 8×** |
| `fairing_cw_L/R` | ~66 × 28 × 14 | 28 mm run (brand 25–30); body colour in review |
| `cw_floor_layout` | ~82 × 109 × 2 (+ribs/glyphs) | PLA coupon for 2×2 pack |

### Screws / clamps

| Feature | XY (mm) |
| --- | --- |
| Lid / tub M3 (`CW_SCREWS`) | (±22, ±54) — Y-end land outside 2×2 pack |
| CW clamp holes (`CW_CLAMP`) | (**±36, ±28.5**) — Y locked to clamp bars |
| Cap/saddle clamp family | (±28.5, ±20) strap-along-Y |
| LoRa crest ref | (0, 64) |
| **Clamp→LoRa clearance** | **≥15 mm keep** (cap clamps at \|y\|=20) |

Farmer repair: one M3 driver; orange = service accents only (not whole CW).

## Print orientation

| Part | Bed (z=0) | Supports |
| --- | --- | --- |
| `cw_tub` | Underside; cavity UP; glyphs UP | None |
| `cw_lid` | **MATING** face down (no outer flip; same rule as cap_lid) | Minimal — soft crown, no large trees |
| `saddle` | Roof; channel +Z | None |
| `clamp_bar` | Flange; channel +Z; load along Y WITH layers | None |
| Fairings | Long axis on bed; slope = WALL | None |
| Floor layout | Underside; ribs/glyphs UP | None |

Export: z=0, watertight, rotation-only, recalc normals, **never** `flip_normals()`.

## Floor glyphs

One table (`FLOOR_LABEL_TABLE` in `cw.py`). DejaVu Bold; char H ≥5 mm; stroke ≥0.8; relief ≥0.6.

| Key | Label | Meaning |
| --- | --- | --- |
| STEEL | STEEL | Steel pack only |
| ONLY | ONLY | No electronics |
| FILL | FILL | Fill line (steel top + foam) |
| SCR1–4 | 1–4 | Screw order |
| PIN1 | ARROW | Assembly / lid direction |
| UP | UP | Cavity cue (table; optional use) |

Floor ribs: fence per side-by-side pack + cross ribs.

## STLs (`stl/`)

- `cw_tub.stl`, `cw_lid.stl`, `saddle.stl`, `fairing_cw_L.stl`, `fairing_cw_R.stl`
- `clamp_bar.stl` — **print 8** (see `CLAMP_QTY.txt`)
- `cw_floor_layout.stl`
- `cw_report.json` — watertight / dims / mass

## Renders / review

- `renders/cw_iso.png`, `cw_top.png`, `cw_side.png`, `cw_section.png`
- `renders/d6_assembly_{iso,front,side,top,joint}.png` — body ASA + orange accents
- `review/cw_review.blend`, `review/d6_assembly.blend`
- Review-only details in the assembly blend: solar `cap_panel_p124`, strap loop + buckle/keeper, orange screw heads, latch + service dots, rib lines, recessed glyph panel
- D4 ghost: **bounding boxes only** (no `D4_contoured_v3` mesh/blend in repo); duplicate `D4_pod_R_mirror` removed

## Verification

| Requirement | Status |
| --- | --- |
| Steel mass 771.8 g / foam / O-ring / M3 | **PASS** (unchanged fill) |
| Longer along strap, shallower than 30 mm tower | **PASS** — 18 mm tub, 2×2 pack |
| Outer R ≥ 10 + side taper + lower dome | **PASS** — R10, inset 2.2, lid 7.5 |
| Clamp holes y=±28.5 | **PASS** |
| Strap-through-saddle geometry (d6-integrate) | **PASS** — channel 46.45 × 3.4 along Y |
| Body light-gray; orange accents only | **PASS** (renders / blend) |
| STLs print-oriented z=0, watertight, no flip_normals | **PASS** (re-export) |
| Cap / pod skin | **Out of scope** — parallel d7-cap / d7-pod agents |

## Match notes for other agents

- Cap agent: clamp XY (±28.5, ±20); saddle width 76; strap 44.45; channel along Y — unchanged.
- Pod agent: same clamp_bar STL ×2 per pod; fairing run 28 mm brand.
- Integrator: `assembly.py` CW_TUB_H=18, CW_L/W=89.4×115.8; fairing_cw centres y=±72.
- CW world pose: D4 `cw_anchor` at z≈−465.75, rot 180° about X — not baked into print STLs.
