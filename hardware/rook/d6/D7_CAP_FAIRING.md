# D7 cap + fairing (branch `cursor/d7-cap-9a36`)

op-brand D6 aesthetics: separate flat slabs → D4 continuous tapered object.
This agent owns **cap nose** + **fairings** only. Pod outline slim is
`cursor/d7-pod-9a36` (mount interface unchanged).

## What changed

| Item | D6 | D7 |
| --- | --- | --- |
| Fairing solid | Constant-Y trapezoid prism (88→66 lived in **Z**) | Continuous wedge loft along **run** (`fairing.py`) |
| Fairing edges | `FAIRING_EDGE_R = 2.5` | **R ≥ 4** (`assembly.FAIRING_EDGE_R = 4`) |
| Fairing plan | Soft bound R=7 on a block | Stadium ends + smootherstep side ease |
| Cap Y-ends | Hard prism cut tip ~4 mm | Elliptical roof + plan R 12 + bullnose 5 |
| Params | W0/W1/run/H only | `FAIRING_POD_OUTER_*`, `FAIRING_PLAN_R*`, `FAIRING_TOP_CROWN`, … follow `POD_L` |

## Kept (do not break)

Cap W 76; crowned lid + flat panel land; pocket 66.6×113.6×2.3 + 15 mm keep-clear;
Wio 21.8×18.6×8 @ (22,−8); clamp inserts (±28.5, ±20); countersink 8×1.2; lid posts;
real glyphs; lid mating-face-down; pod mount y=±126, z=−21.9, tilt ±29.142°, 4×M3 + pad.

## Regen

```bash
cd hardware/rook/d6
blender --background --factory-startup --python cap.py
# fairings: via pod.py / cw.py mains, or fairing.py helpers
python3 assembly_check.py out
```

## Renders

`renders/d7_before/`, `renders/d7_after/` — shaded top/side/iso of nose, fairings, joint.
