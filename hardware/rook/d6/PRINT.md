# D8 printable candidate — Rook collar (ASA, P2S 256)

Material: **ASA** for collar shells. Bed: **Bambu P2S 256×256×256**. **Brim 8 mm**
on every ASA shell. Enclosure closed; dry filament. PLA coupons = fit-check only.
**Nothing is printed without the owner's explicit say-so.**

Times/grams are **estimates**. Re-slice before any real plate.

## D8 delta vs D6 @ debb5de

- Pod plan: R3 corners; mount tip ~66; mid swell 68; **strap-end flare ~76**
- Pod lids: **3 mm inset** + lip; prism **`001`** (6×0.6 mm, letter-up −X); 4× Ø2 recesses
- Cap↔pod fairings: **1.5 mm top groove** (fastening intact); pod↔strap fairings kiss flare
- Cap plan R3; heights / arc / panel keep-clear unchanged (cap roof 48.2 / pod 25 review; print stacks lay-flat as today)
- **P0 first:** `d8_fit_coupon.stl` (gauges + footprints + joint) before any ASA plate
- **+2 neck saddles +2 bay covers**; height **0 mm above strap** (module depth extra toward neck only)

## Parts list (1 collar)

| STL | Print bbox (mm) | Vol (cm³) | Qty | Bed / notes |
| --- | --- | ---: | ---: | --- |
| `d8_fit_coupon` | ~238 × 207 × 14 | ~138 | 1 | **PLA P0** — R208/218/221/350 gauges + footprints + joint; re-slice |
| `cap_base` | 76.0 × 186.9 × 34.2 | ~130 | 1 | cavity UP + strap skirts; **Y+brim ≤256** |
| `cap_lid` | 75.0 × 163.0 × 12.0 | ~110 | 1 | mating DOWN; lower crown/nose |
| `pod_L_base` / `pod_R_base` | **76.0 × 98.8 × 37.7** | ~59 each | 1+1 | cavity UP; flare 76 + D4 strap notches |
| `pod_L_lid` / `pod_R_lid` | 70.0 × 91.0 × 6.0 | ~24 each | 1+1 | outer DOWN; prism `001` + screw recesses |
| `pod_L/R_saddle` | **52 × 97 × ~12** | — | 1+1 | ASA; flat on bed, R220 concave UP + bowl supports |
| `pod_L/R_bay_cover` | ~30 × 45 × 2 | — | 1+1 | blank sealed cover for empty shock bay |
| `cw_tub` | 89.1 × 116.0 × 19.2 | 59.9 | 1 | cavity UP; 2×2 steel |
| `cw_lid` | 88.4 × 114.8 × 6.35 | 46.3 | 1 | mating DOWN |
| `saddle` | 76.0 × 96.0 × 6.5 | 20.9 | 1 | channel along Y |
| `clamp_bar` | 10.0 × 70.0 × 8.0 | 4.1 | **8** | flange on bed |
| `fairing_cap_pod_L/R` | 68.0 × 16.0 × 16.0 | 16.8 each | 1+1 | short rounded nose |
| `fairing_pod_strap_L/R` | 68.2 × 28.0 × 18.0 | 29.0 each | 1+1 | long face on bed |
| `fairing_cw_L/R` | 89.5 × 32.0 × 14.0 | 30.4 each | 1+1 | long face on bed |
| `*_floor_layout` | coupons | — | 3 | **PLA** |

Non-print: **4× steel bar** → **771.8 g**; P124; strap; inserts; O-ring; M3.

## P2S 256 — plate fit with 8 mm brims

Usable ≈ **240 mm** after dual-side brim.

| Plate | Parts | Fit note | Est. ASA |
| --- | --- | --- | --- |
| **P0** | `d8_fit_coupon` (+ floor coupons) | PLA; no brim; **print first**; re-slice (~12 h heuristic) | PLA |
| **P1** | `cap_base` | Y+brim 203 ≤ 256; alone on long axis | ~4.5 h / ~130 g |
| **P1b** | `cap_lid` | 75×163 + brim | ~3.5 h / ~90 g |
| **P2** | both pod bases | two 68×99 + brims side-by-side ≈ 2×84 ≤ 240 | ~5.5 h / ~100 g |
| **P3** | both pod lids + 4× clamp | lids 67×96; clamps in gaps | ~2.5 h / ~60 g |
| **P4** | `cw_tub` + `cw_lid` | tub 89×116 + brim | ~4.5 h / ~110 g |
| **P5** | saddle + 6 fairings + 4× clamp | nest fairings | ~4.0 h / ~100 g |

**Collar ASA (P1–P5):** ~5–6 plates / **~20–25 h** / **~450–550 g** (est.).

## Intact contract

- Mount: y=±126, z=−21.9, ±29.142°, 36×4×14 recess, 4× M3
- Panel 66.6×113.6×2.3 + 15 mm keep-clear; Wio 21.8×18.6×8; cavity **82×58×19.5**
- Steel **771.8 g**
