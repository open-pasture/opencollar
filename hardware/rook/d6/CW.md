# D6 counterweight + clamps

D4 contoured look (domed lid) around D5 mass / strap / clamp internals.
Script: `hardware/rook/d6/cw.py`. Base: D5 @ `6b1f882` (real floor glyphs + lid 180° X flip).

## Choice (mass)

| Item | Value |
| --- | --- |
| **Envelope chosen** | **D5 tub 88 × 74 × 30 mm** (+ D4-style **12.7 mm** domed lid) |
| Why not D4 tub | D4 ~59 × 85 × 24 cannot fit steel pack 76.2 × 50.8 × (4×6.35=25.4) mm |
| **Fill** | **4× mild steel flat bar** 76.2 × 50.8 × 6.35 mm (3 in of 2×¼ in) + **1.5 mm foam** pad |
| **Steel volume** | **98 322 mm³** (98.3 cm³) |
| **Steel mass** | **771.8 g** @ 7.85 g/cm³ |
| **Lid seal** | 2.0 mm O-ring groove in tub rim + registered lip; **4× M3** button-head into heat-set inserts; foam compresses pack under lid |

Electronics stay out of the CW (D5 / contract).

## Dimensions

| Part | Size (mm) | Notes |
| --- | --- | --- |
| `cw_tub` | 88 × 74 × 30 (+1.2 lip → bbox ~31.2) | Cavity UP; floor 3; wall 6; steel pocket 77.4 × 52.0 |
| `cw_lid` | 87 × 73 × 12.7 | Domed; flat crown land 42 × 36; reveal 0.5 |
| `saddle` | 76 × 96 × 5.0 (+pins → ~6.5) | Roof ≥1.6; channel W=46.45 D=3.4 |
| `clamp_bar` | **10 × 70 × 8** | Flange 10×70×3; walls to depth 8; **print 8×** |
| `fairing_cw_L/R` | **88 → 66 × 28 × 14**, R≥4 | D7 continuous loft (`fairing.py`) |
| `cw_floor_layout` | ~78 × 58 × 2 (+ribs/glyphs) | PLA coupon |

### Screws / clamps

| Feature | XY (mm) |
| --- | --- |
| Lid / tub M3 (`CW_SCREWS`) | (±22, ±31.5) |
| CW clamp holes (`CW_CLAMP`) | (±36, ±29.5) |
| Cap/saddle clamp family | (±28.5, ±20) strap-along-Y |
| CW clamp holes | (±36, ±28.5) — Y matched to bars |
| LoRa crest ref | (0, 64) |
| **Clamp→LoRa clearance** | **35.5 mm** (≥15 keep; matches D5) |

Farmer repair: one M3 driver; orange = service elsewhere; CW lid charcoal plugs OK.

## Print orientation

| Part | Bed (z=0) | Supports |
| --- | --- | --- |
| `cw_tub` | Underside; cavity UP; glyphs UP | None |
| `cw_lid` | **OUTER** (export: 180° about X, normals recalc — **never** `flip_normals`) | **No large supports.** Flat crown land ≈ **787 mm²** bed face; strap channel is a bed pocket |
| `saddle` | Roof; channel +Z | None |
| `clamp_bar` | Flange; channel +Z; load along Y WITH layers | None |
| Fairings | Widest face on bed z=0; walls = slope | None (R≥4 continuous wedge) |
| Floor layout | Underside; ribs/glyphs UP | None |

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

Floor ribs: rectangular steel-pack fence + cross ribs.

## STLs (`stl/`)

- `cw_tub.stl`, `cw_lid.stl`, `saddle.stl`, `fairing_cw_L.stl`, `fairing_cw_R.stl`
- `clamp_bar.stl` — **print 8** (see `CLAMP_QTY.txt`)
- `cw_floor_layout.stl`
- `cw_report.json` — watertight / dims / mass

All exported in print orientation; watertight-checked (PASS on first build).

## Renders / review

- `renders/cw_iso.png`, `cw_top.png`, `cw_side.png`, `cw_section.png`
- `review/cw_review.blend` — lineup with lid in print orientation

## Verification vs contract / D5

| Requirement | Status |
| --- | --- |
| D4 look (domed lid) + D5 mass envelope | **PASS** — dome 12.7; tub 88×74×30 |
| Steel mass stated (volume, fill, seal) | **PASS** — 771.8 g / 98.3 cm³ / foam + O-ring + M3 |
| Channel clamps 10×70×8 flange-down | **PASS** |
| Load along layers; farmer M3 | **PASS** |
| LoRa clearance | **PASS** (64 − 20 = 44 mm with D6 CAP_CLAMP y) |
| Floor ribs + real embossed glyphs (table) | **PASS** — DejaVu Bold / stroke symbols |
| Lid outer-down via 180° X (no `flip_normals`) | **PASS** |
| STLs print-oriented z=0, watertight | **PASS** |
| Saddle + CW fairings at bottom of loop | **PASS** (parametric; D4 world poses are assembly) |
| Cap / pod skin | **Out of scope** — cap & pod agents |

## Match notes for other agents

- Cap agent: clamp XY (±28.5, ±20); saddle width 76; strap 44.45; channel along Y.
- Pod agent: same clamp_bar STL ×2 per pod; fairing run 28 mm brand.
- CW world pose (assembly): D4 `cw_anchor` at z≈−465.75, rot 180° about X — not baked into these print STLs.
