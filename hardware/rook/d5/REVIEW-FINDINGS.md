# PR #21 D5 production: op-maker review (box, 2026-11-03 ~01:40 CT)
Nothing printed. Printer not touched. Nothing merged. No PR opened.

## Blocking (found in PR STLs, fixed locally in fixtree/ only, not committed)
1. reg_lip() unions a SOLID 1.2 mm plate on top of every base, so cap_base, pod_L/R_base and cw_tub are SEALED BOXES with no cavity access. Fix: cut the lip to a ring (lip minus 1.6 mm wall). Effect: shells plate support fell from 35% to 12%, time from 17.1 h to 11.4 h.
2. fit_coupon: kit, bq, buzzer and Wio gauge pockets plus the USB-C gauge were sealed under a 0.2-0.3 mm skin (internal voids), so the coupon could not gauge anything. Fix: pocket depth 3.5 to 4.5 and USB-C 4.0 to 5.0, so they open through the top.
   Patch: fixtree/hardware/rook/d5/cad/build_d5.py (render_objs is stubbed out with `return` there, so drop that line before upstreaming).

## Fit conflicts vs locked cavities (not fixed, needs design)
- Cap internal height is about 14.3 mm (13 mm cavity + 1.3 mm lid recess). The Wio-SX1262 pocket is spec'd 23 mm (+20 mm wire bend) and the Connect Kit with socketed headers is about 17 mm. NEITHER FITS. Options: solder headers or cut the kit low, lay the Wio flat, or raise the cap (hurts brand proportions).
- The U.FL slack channel (x 13-21, y 2-22) overlaps the bq24074 pocket corner (x to 19.5, y from 5.1).
- The cap screw column at (±29.5, -42) d8 clips the kit pocket corner by about 0.5 mm.
- Pods are taller than the cap (30.5 vs 25.5 mm total), against brand's "pods smaller and lower".
- Cap width is 76 mm against the brand limit of ≤57.8 mm (1.3× strap). P124 panel **KEPT** on collar #1 (Cody 2026-11-03) — conflict accepted.
- Strap thickness 4.0 mm and the bq/GNSS/Wio heights are unverified (calipers / parts Nov 4-6).

## Geometry checks (fixed set)
All 24 STLs are watertight, with consistent winding and no degenerate faces. The largest part is cap 76×160×20 (fits P2S and 220 beds).
Remaining flags: buzz_mesh is 28 disconnected 0.7 mm islands (it falls apart, so it needs a rim). buckle has a separate floating inner body (pin in slot?). Fairings are 16-triangle plain wedges, with no R7/R2.5 and none of brand's 25-30 mm blend. cap_lid needs about 39% tree support (underside recess); flip it or add a ring land.

## Slices (Orca CLI, 0.2 mm, 3 walls, 35% gyroid, tree supports auto)
| Plate | P2S PLA | P2S ASA | 
|---|---|---|
| P0 fit+label coupon (print first) | 0h58, 27.5 g | 1h11, 29.8 g |
| P1 shells (cap+pods base/lid, single merged object) | 11h25, 266.9 g | 11h07, 242.8 g |
| P2 CW, saddle, 4 fairings, 8 clamps, 8 plugs, latch, 2 mesh, buckle, keeper | 7h31, 180.1 g | 7h19, 161.4 g |
| **Collar (P1+P2)** | **2 plates, 18h56, 447 g** | **2 plates, 18h26, 404 g** |
| P3 spares (4 clamps, 3 orange screws, latch, 2 mesh, 2 usbc caps) | 0h37, 11.0 g | 0h36, 10.2 g |
| P3b spare cap_lid | 2h22, 44.7 g | 2h23, 41.9 g |
220 bed (Ender 3 V3 SE PETG profile, auto-arranged): collar 5 plates, about 24h06, 490.5 g. Coupon 1h34 (36 g), spares 0h38, spare lid 2h29. Everything fits 220×220.
PETG on P2S: not sliced separately; estimate about 1.05-1.1× PLA time (about 20-21 h), ~1.05x PLA grams by density (about 470 g) [ESTIMATE].
TPU usbc_cap (1 per collar) is not in P1/P2. For the field, print it in TPU separately. The spares-plate copies are in the plate's main material.

## Caveats
- P1/P2 are one merged object per plate, packed by hand (the Orca CLI refused --arrange 0 multi-object with -101). Individual objects can't be cancelled mid-print. Auto-arrange splits the collar to 4 P2S plates (~26 h).
- Before sending any .gcode.3mf to Bambu Connect, run print/fix_bbl_3mf.py on it (CLI-sliced 3mf patch). Not applied yet.
- Renders are mine (renders/). The PR's d5_prod_lineup.png is blank.
