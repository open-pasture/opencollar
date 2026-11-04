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

D4 pods are ~67×97×19.4. D5 cavity **82×58×19.5** forces outer X ≥ **92**
(5 mm walls) — cannot recover D4's 67 mm width without relocating the cells.
D6 keeps cavity and tilt; uses outer **92×92×21** (floor 1.5) and shifts
anchors outboard to **y=±124** (from D4 ±113.8) so cap/pod bodies clear with
a ~2–3 mm fairing-bridged gap. Cap pad tilt matches pod/D4: L **+29.142°**,
R **−29.142°**. Cap pads and pod ends share a 36×4×14 M3 joint (4× clear).

## Fairings

Wide end **88** (spans 92 mm pods / 88 mm CW), taper to **66**, run **28**,
H **14**. World poses from D4 fairing bbox centres in `assembly.py`.

## CW lid print orientation

Compared outer-face-down (~787 mm² bed / ~5544 mm² support-ish) vs
mating-face-down (large bed face, far less support — same rule as `cap_lid`).
**Picked mating-face-down**; rotation only + recalc normals, never
`flip_normals()`.

## Kept from D5 (unchanged)

Panel pocket 66.6×113.6×2.3 + 15 mm keep-clear; Wio 21.8×18.6×8 at (22,−8);
countersink 8×1.2; lid posts; `FLOOR_LABEL_TABLE` in `build_d5.py`; cap width 76.
