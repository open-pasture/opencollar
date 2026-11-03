# D5 production — start here

**Status:** draft / printable parametric CAD. **Not** field-ready. **Not** for animal until welfare review (PR #2).

**Print first:** `coupons/fit_coupon.stl` (PLA) → confirm board + cell + insert fit → then shells.

## What this is

D5 is the production rebuild of the D5 look-study (B-led + A radii + C height, remeshed visuals in `look_study/`). Printable parts are flat parametric solids in `stl/` — strap curve comes from the **saddle + fairings**, not a voxel warp.

| Path | Contents |
| --- | --- |
| `cad/d5_dims.py` | Locked dims, firmware pockets, assumptions |
| `cad/build_d5.py` | Blender builder |
| `stl/` | Printable STLs + `report.json` |
| `coupons/` | Fit + label coupons (print first) |
| `plates/plates.json` | P2S 256 + 220-bed plate nests (no Orca CLI here) |
| `images/` | Production lineup/exploded + look-study stills |
| `look_study/` | Remeshed brand visuals (not for print) |
| `D5-PRODUCTION.md` | Envelope, RF, materials, farmer repair |
| `MATERIALS.md` | ASA / PETG / TPU / PA-CF keepout |
| `SPARES.md` | Farmer-swappable set / &lt;2 h plate |

## Rebuild

```bash
cd hardware/rook/d5/cad
blender --background --factory-startup --python build_d5.py
```

## Open decisions (do not bury)

1. **P124 on cap** — OPEN (Cody/strategy). Pocket retained.
2. **Cap width 76 mm vs brand ≤1.3× strap (~57.8 mm)** — conflict while P124 is in play.
3. **Mono vs stereo buzzer** — Cody (HARDWARE-FIT).
4. **1781 purchase** — pending Cody.

## Firmware pocket summary

| Part | Pocket (mm) | Where |
| --- | --- | --- |
| Rook Connect Kit | 56.7 × 21.1 × 7.2 (~17 w/ headers) | Cap −Y |
| bq24074 | 38.9 × 33.8 × 12 | Cap (not potted) |
| Wio-SX1262 | 21.8 × 18.6 × 23 | Cap +X |
| Buzzer | 26.2 × 26.2 + mesh disc | Each pod |
| 18650 1781 | Ø19.2+2 × 70+6 | Each pod (adjustable) |
| GNSS / LTE / LoRa | crest +Y lid | Cap lid; metal keepout 12 mm |
| CW tub | — | **Steel only — no electronics** |

Clearance policy: **board + 0.4 mm per side** (coupon sweeps 0.2 / 0.4 / 0.6).

## Scope

- **Rook** — this CAD (kit + dual 1781 pods + CW).
- **Starling** — same Wio XY pocket; **small cells only**; separate shell CAD TBD (~3 P2S plates once designed).
- Pilot kit = Rook unit #1 first; Starling follows.

## Before “field-ready”

Calipers on strap / bq / patch; fit coupon pass; ASA enclosure dry-run; drop + IP splash on seals; RF range check with keepouts; welfare sign-off.
