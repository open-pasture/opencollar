# D6 integration decisions

Integrator branch `cursor/d6-integrate-9a36` (from D5 `6b1f882` + cap/pod/cw agents).

## Strap path (along Y)

D4 / the D6 contract put the strap along **Y** (spine), width across **X**.
D5 `CAP_CLAMP = (±20, ±28.5)` and the CW `saddle.stl` channel (width along Y)
were a cross-strap leftover: with strap-along-Y those inserts sit inside the
44.45 mm strap (|x|=20 < 22.225) and would pierce it.

**Decision:** D6 uses `CAP_CLAMP = (±28.5, ±20)` (see `assembly.py`).

- Inserts clear the strap (|x|=28.5 > 22.225).
- Saddle channel is **46.45 wide in X**, run along Y, body still **76 wide**.
- Clamp bars stay **10×70×8**, holes at **±28.5** along the bar; under the
  cap/saddle they rotate 90° about Z so holes land on x=±28.5 at y=±20.
- CW tub clamp pitch Y moved **29.5 → 28.5** to match the bars (X stays ±36).

## Pod envelope vs D4

D4 pods are ~67×97×19.4. D5 cavity **82×58×19.5** was first placed with 82
across X → outer **92** wide. **D7r2** rotates the cavity so **82 runs along Y**
and **58 across X** → outer **~68 × 97** (wall 5.0 ≥ 3.5), narrower than cap 76,
matching D4's plan ratio. Mount face local Y stays **+46** (locked); the
strap-end grows to make length ~97. Anchors remain **y=±126, z=−21.9**, tilt
L **+29.142°** / R **−29.142°**, 36×4×14 M3 joint. R pods mirror X then Y so
the mount face points at the cap.

## Fairings (D7r3 continuous wedge)

Wide end = slim pod outer **68** (cap↔pod / pod↔strap) or CW outer **89.4**.
Cap↔pod: short rounded nose — run **16**, **W1=W0** (no sail taper),
**TOP_CROWN=0** (no crease), flush with tilted pod tip outline. Pod↔strap
still tapers to **52** along run **28**. CW run **32**, H **18** / CW **14**,
edge fillet **R ≥ 4**. Loft in `fairing.py`; `FAIRING_*` in `assembly.py`.
`FAIRING_BEVEL_OVERSIZE` keeps seam ≤ 0.5 mm. World poses from `FAIRING_CENTRES`.

## Review palette + orange (D7r4)

DEFAULT review palette = **charcoal** (~`#3A3C3E`, roughness 0.6) matching
D4_contoured_v3 body; `--palette light` (`#C9CBCC`) is secondary. Brand orange
**#FF6A2B** only on: one small dot per pod lid, one collar tab, tiny screw
heads, latch. No orange saddles / clamp endcaps. Strap = slim flat YZ band
through the saddle channel and under the CW clamp; D4 buckle + keeper in dark
gray.

## CW lid print orientation

Compared outer-face-down (~787 mm² bed / ~5544 mm² support-ish) vs
mating-face-down (large bed face, far less support — same rule as `cap_lid`).
**Picked mating-face-down**; rotation only + recalc normals, never
`flip_normals()`.

## Kept from D5 (unchanged)

Panel pocket 66.6×113.6×2.3 + 15 mm keep-clear; Wio 21.8×18.6×8 at (22,−8);
countersink 8×1.2; lid posts; `FLOOR_LABEL_TABLE` in `build_d5.py`; cap width 76.
