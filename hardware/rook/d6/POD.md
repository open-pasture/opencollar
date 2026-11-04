# D7r2 POD — cavity rotated for D4-narrow outline

Script: `hardware/rook/d6/pod.py`. Mount locked from `assembly.py`.

## Envelope

| Item | mm | Notes |
| --- | --- | --- |
| Outer swell W × L | **~68 × 97** | D4 ≈67×97; narrower than cap 76 |
| Tip width | **66** | soft plan taper; R≥8 |
| Stack H | **~26.2** | base 22.2 + lid 4.0 |
| Cavity (locked) | **82 × 58 × 19.5** | size unchanged |
| Cavity orientation | **58 across X / 82 along Y** | D7r2 rotation (was 82 across X) |
| Wall at cells | **5.0** (≥3.5) | outer X = 58+10 = 68 |
| Mount face local Y | **+46** | LOCKED (was POD_W/2 when W=92) |
| Mount recess | **36 × 4 × 14** | side land (68−36)/2 = 16 ≥ 3 |
| Lid crown | **sagitta 1.4** | single-curvature barrel along Y (G1) |

## Mount (unchanged world)

| Side | loc | rot_x |
| --- | --- | --- |
| L | (0, −126.0, −21.9) | +29.142° |
| R | (0, +126.0, −21.9) | −29.142° |

4× M3 clear through recess; pattern from `POD_MOUNT_SCREWS`.

## Internals (re-placed for orientation)

- Cell bay axis **along Y**; `CELL_AT = (0, −2)`
- Buzzer `BUZZ_AT = (0, 28)` toward mount; port through +Y wall
- Cable + Ø8×1.2 countersink on mount face
- Columns at (±22, ±36); groove/lip on 68×92 envelope
- Floor glyphs from `FLOOR_LABEL_TABLE` (readable along Y)

## Fairings

Wide end = pod outer **68** (via `FAIRING_W0`); H **20** so top meets lid roof at seam (≤0.3 mm). Continuous loft in `fairing.py`.

## Print

| Part | Bed | Notes |
| --- | --- | --- |
| base | underside; cavity UP | glyphs UP |
| lid | OUTER DOWN (180° X) | smooth crown; no flip_normals |
| floor_layout | underside | PLA coupon |
