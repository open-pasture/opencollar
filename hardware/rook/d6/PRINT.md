# D7 print plan — Rook collar (ASA, P2S 256)

Branch carries D7 integrate on `cursor/d6-integrate-9a36`. Material: **ASA**
(outdoor shells). Bed: **Bambu P2S 256×256×256**. **Brim 8 mm** on every ASA
shell (bases, lids, CW, fairings, saddle). Enclosure closed; dry filament.

PLA floor coupons (`*_floor_layout`) stay PLA fit-check only — no brim required.

Times/grams below are **estimates** from D5 plates scaled to D7 envelopes.
Re-slice before any real plate.

## Parts list (1 collar)

| STL | Print bbox (mm) | Vol (cm³) | Qty | Bed / notes |
| --- | --- | --- | ---: | --- |
| `cap_base` | 76.0 × 186.9 × 20.2 | 123.1 | 1 | cavity UP; floor glyphs UP |
| `cap_lid` | 75.0 × 163.0 × 12.0 | 112.6 | 1 | **mating DOWN** |
| `pod_L_base` / `pod_R_base` | 92.0 × 93.8 × 23.4 | 68.9 each | 1+1 | cavity UP; R = mirror |
| `pod_L_lid` / `pod_R_lid` | 91.0 × 91.0 × 4.15 | 28.6 each | 1+1 | outer DOWN (180° X) |
| `cw_tub` | 89.1 × 116.0 × 19.2 | 59.9 | 1 | cavity UP; 2×2 steel pack |
| `cw_lid` | 88.4 × 114.8 × 6.35 | 46.3 | 1 | **mating DOWN** |
| `saddle` | 76.0 × 96.0 × 6.5 | 20.9 | 1 | channel along Y |
| `clamp_bar` | 10.0 × 70.0 × 8.0 | 4.1 | **8** | flange on bed |
| `fairing_cap_pod_L/R` | 70.4 × 18.0 × 14.0 | 15.0 each | 1+1 | long face on bed |
| `fairing_pod_strap_L/R` | 70.2 × 28.0 × 14.0 | 23.4 each | 1+1 | long face on bed |
| `fairing_cw_L/R` | 89.5 × 32.0 × 12.0 | 26.8 each | 1+1 | long face on bed |
| `cap_floor_layout` | 70 × 134 × 5 | 20.3 | 1 | **PLA coupon** |
| `pod_floor_layout` | 80 × 58 × 5 | 10.3 | 1 | **PLA coupon** |
| `cw_floor_layout` | 82.2 × 108.6 × 4.5 | 19.7 | 1 | **PLA coupon** |

Non-print: **4× steel bar** 76.2×50.8×6.35 → **771.8 g** pack + 1.5 mm foam;
P124 panel; strap; heat-set inserts; O-ring; M3 hardware.

Plastic solid ≈ **705 cm³** (excl. coupons). At ASA ~1.07 g/cm³ + ~40% infill
expect roughly **~380–450 g** filament for shells (re-slice).

## P2S 256 — plate fit with 8 mm brims

Usable footprint after dual-side brim ≈ **256 − 2×8 = 240 mm** per axis.
Leave ≥4 mm between brim islands.

| Plate | Parts | Footprint check (ASA + 8 mm brim) | Est. ASA |
| --- | --- | --- | --- |
| **P0** | `cap_floor_layout` + `pod_floor_layout` + `cw_floor_layout` | PLA coupons; no brim | ~1.2 h / ~50 g PLA |
| **P1** | `cap_base` + `cap_lid` | Cap base Y=187 + brim → ~203; lid beside or second layer — **cap_base alone needs nearly full Y**; put lid on P1b if Orca complains | ~6.5 h / ~160 g |
| **P1b** | `cap_lid` (if not on P1) | 75×163 + brim fits alone | ~3.5 h / ~90 g |
| **P2** | `pod_L_base` + `pod_R_base` | Two 92×94 + brims ≈ 2×(108×110); side-by-side in X: 108+108=216 ≤ 240 | ~7.5 h / ~150 g |
| **P3** | `pod_L_lid` + `pod_R_lid` + 4× `clamp_bar` | Lids 91×91; clamps in gaps | ~3.0 h / ~70 g |
| **P4** | `cw_tub` + `cw_lid` | Tub 89×116 + brim; lid beside or stacked plate | ~4.5 h / ~110 g |
| **P5** | `saddle` + 6 fairings + 4× `clamp_bar` | Fairings nest; saddle 76×96; remaining clamps | ~4.0 h / ~90 g |

**Collar ASA (P1–P5):** ~5–6 plates / **~25–29 h** / **~480–570 g** (est.).
Tightest part: **cap_base** length 187 mm + 8 mm brim ≈ 203 mm — fits 256 with
~26 mm margin each end; do not pair another long part on the same Y span.

## Settings (ASA field)

| Setting | Value |
| --- | --- |
| Nozzle / layer | 0.4 mm / 0.20 mm (0.6 / 0.28 OK for CW tub only) |
| Walls / infill | 6 walls / 40 % gyroid (100 % around bosses) |
| Brim | **8 mm** outer; ears OK on cap_base corners |
| Bed / chamber | ~100 °C bed; enclosure on |
| Supports | Cap/pod bases: cavity features as needed; lids mating-down = minimal; fairing slopes as WALL |

## Intact contract (do not “optimize” away)

- Cap–pod mount pad/recess **36×4×14**, tilt ±29.14°, anchors from `assembly.py`
- Panel pocket **66.6×113.6×2.3** + **15 mm** keep-clear
- Wio pocket **21.8×18.6×8** @ (22, −8)
- Pod cavity **82×58×19.5**
- Steel pack **771.8 g** (4× 76.2×50.8×6.35)

## Rebuild

```bash
cd hardware/rook/d6
blender --background --factory-startup --python cap.py
blender --background --factory-startup --python pod.py
blender --background --factory-startup --python cw.py
python3 assembly_check.py out   # expect 136/136 PASS
blender --background --factory-startup --python build_assembly_blend.py -- \
  out/world out/d4_ghost out/assembly_review
```
