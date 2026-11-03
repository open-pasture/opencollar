# D5 production — start here

**Status:** draft / printable parametric CAD (durability revision). **Not** field-ready. **Not** for animal until welfare review (PR #2).

**Print first:** `coupons/fit_coupon.stl` (PLA) → confirm board + cell + insert fit → then shells.

## Rebuild

```bash
cd hardware/rook/d5/cad
blender --background --factory-startup --python build_d5.py
```

## Open decisions — Cody

1. **FIT HEIGHT (blocking for upright radio / socketed kit).** Cap free height ≈ **14.3 mm**. Upright Wio ~**23 mm** (+20 mm wire bend) and kit+headers ~**17 mm** **do not fit**. CAD uses lay-flat Wio (8 mm) + low-profile kit (7.2 mm). Choose **(A)** keep, **(B)** raise cavity ≥23 mm, **(C)** solder headers / remote radio.
2. **P124 solar panel KEEP-OR-DROP — OPEN.** Pocket retained. Cap stays **76 mm** while panel is in play; if dropped → `CAP_W_SLIM = 58` (brand ≤1.3× strap).
3. **Cap width vs brand ≤1.3× strap (~57.8 mm).** Conflict while P124 is in play.
4. **Mono vs stereo buzzer; 1781 purchase** — HARDWARE-FIT.
5. **Light-gray colourway** — proposed; **PENDING op-brand review** (charcoal + orange remain locked accents).

## Brand / durability (this revision)

| Condition | Status |
| --- | --- |
| Pods vs cap height | Pod stack **26.0** vs cap **25.5** (pod lid ≥4.0 durability; 0.5 mm brand tension) |
| Cap ≤1.3× strap | **Flagged** — 76 vs 57.8 while P124 OPEN |
| Fairings 25–30 mm, R7 / R2.5 | Yes |
| CW free of electronics | Yes |

## Firmware pockets

| Part | Pocket (mm) | Where |
| --- | --- | --- |
| Kit low-profile | 56.7 × 21.1 × 7.2 | Cap −Y |
| bq24074 | 38.9 × 33.8 × 12 | Cap (not potted) |
| Wio lay-flat | 21.8 × 18.6 × 8 | Cap +X (**≥3 mm** wall) |
| Buzzer + rimmed mesh | 26.2 × 26.2 | Pod (+3 Y clear of cell) |
| 18650 1781 | Ø19.2+0.2 × 70+6 | Each pod |
| GNSS / LTE / LoRa | crest; GNSS/LTE open to cavity from z=0 | Metal keepout 12 mm |
| CW tub | — | **Steel only** |

## Plate list (durability est. from Orca baseline)

| Plate | Parts | P2S PLA (est) | P2S ASA (est) |
| --- | --- | --- | --- |
| **P0** | fit + label coupon (**first**) | 0h58 / 27.5 g | 1h11 / 29.8 g |
| **P1** | cap (+posts) + pods (lid≥4) | ~12h06 / ~283 g | ~11h48 / ~257 g |
| **P2** | CW, saddle≥1.6, fairings, **channel clamps**, … | ~8h06 / ~195 g | ~7h54 / ~174 g |
| **Collar (P1+P2)** | | **~20h12 / ~478 g** | **~19h42 / ~431 g** |
| P3 spares | 4 channel clamps, orange, latch, mesh, usbc | ~0h51 | ~0h50 |
| P3b | spare cap_lid | 2h22 | 2h23 |

220 bed: ~5 plates / ~25.5 h / ~520 g (est). **Re-slice before print** — times are estimates. TPU `usbc_cap` separate.

### Clamp orientation

Print flange flat on bed, channel opens +Z. Load along bar length **WITH layers** (never peel across). ≥12 mm from LoRa crest.

## Durability fixes (this push)

1. GNSS/LTE recesses open into cavity from z=0; panel keeps ≥2 mm lid under; GNSS past panel +Y.
2. Wio +X wall ≥3 mm (`WIO_AT` x=22).
3. Channel clamp bars ≥8 mm deep / 3 mm web.
4. Pod lid ≥4.0 mm (+ ribs); concentric groove radii; `BUZZ_AT` +3 Y.
5. Ø8 lid-support posts between kit and bq.
6. Gasket groove inner land ≥2 mm.
7. Panel frame recessed (−0.4); light pipes/buttons out from under panel.
8. R1–R2 pocket/port fillets; saddle roof ≥1.6 mm (prior 0.8 was a bug).
9. Columns at (±32, −48) clear kit bracket.
10. Light-gray colourway note — pending op-brand.

## Paths

| Path | Contents |
| --- | --- |
| `cad/d5_dims.py` | Dims, pockets, flags, colourway |
| `cad/build_d5.py` | Blender builder + clearance report |
| `stl/report.json` | Watertight + clearances |
| `MATERIALS.md` / `plates/` | Materials + plate estimates |
