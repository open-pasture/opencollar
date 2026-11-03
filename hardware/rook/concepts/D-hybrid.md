# D — Hybrid technical-soft

**Intent:** One family after op-brand’s review of A/B/C. Led by **B** (flat
planes, even fastener grid, one waist datum), softened with **A**’s plan-corner
radii, and held to **C**’s low cap. B’s 45° crown chamfer is gone — replaced by
a continuous top-edge radius so nothing shelves dust.

## Form

| Cue | Spec |
| --- | --- |
| Plan corners | **R7** on cap, pod, tub (and lids) — one R6–R8 family |
| Top edge | **R2.5** radius on lids (no 45° dust ledge) |
| Waist | Real lid parting line; O-ring groove in the base rim; lid inset **0.5 mm** reveal |
| Waist datum | Shared height fraction **0.75** = base / (base + lid) on all three |
| Cap | Base **18 mm** (floor 5 + cavity ≥13); lid 6 mm |
| Pod | Base 24.5 mm (cavity 82×58×21.5); lid ≈8.17 mm |
| Tub | Base **30 mm** (needed steel pack); lid 10 mm |
| Fasteners | Recessed seats + separate blaze-orange flush plugs (chamfered lead-in) |
| Pod ports | Raised annular boss + shallow gasket recess (not bare holes) |
| Label | Flat **30×12** pad on cap lid; debossed 0.5 mm mono `ROOK-001` |
| Latch | Concept orange one-hand latch on the cap lid (+Y) |

## Hardware envelope (locked)

Unchanged fit points vs Node V1 / concepts A–C:

- Cap 76×160; columns `(±29.5, ±68/±42)`; clamp `(±20, ±28.5)`; cavity ≥13 mm
- Pod cavity 82×58×21.5; columns `(±37, ±27)`; outer ~92×68
- Tub ~88×74×30; screws `(±22, ±31.5)`; clamp `(±36, ±29.5)`

Lid screws enter from above into heat-set inserts in the base columns so the
thin lid can carry the Instrument plug grid without a blind-insert pack.

## Colour (op-brand)

| Role | Hex | Use |
| --- | --- | --- |
| Charcoal | `#26282B` | Bodies (and Instrument lids) |
| Oat | `#EFE8D8` | Two-tone lid variant |
| Blaze orange | `#FF6A2B` | Plugs, latch |
| Black | near `#141416` | Strap (render only) |

Renders in [`images/`](images/): assembled iso / front / side, exploded, plus
oat-lid iso / front / side.

## Print

Concept study only — **do not print without Cody’s OK.**

- Bed face flat, cavity / lid mating face up; flanks and R2.5 crown are
  self-supporting (no supports on visible faces).
- O-ring groove floor is horizontal (same as production) — acceptable on
  0.16–0.20 mm; ASA may want the groove facing up or a co-extruded fill later.
- [`stl/D_hybrid/test_corner.stl`](stl/D_hybrid/test_corner.stl) is a 22 mm
  coupon of the plan R7 + top R2.5 for a later **0.12 / 0.16 mm** layer test.

```sh
cd hardware/rook/concepts/cad
blender --background --factory-startup --python build_concept_d.py
```

Watertight + footprint checks run in the builder (`stl/D_hybrid/report.json`).

## Trade-offs

- Cap stack is base 18 + lid 6 = 24 mm overall — silhouette is still low vs the
  gable production stack, but taller than C’s single 18 mm shell.
- Orange plugs are separate printed bodies (or painted caps); seating depth is
  capped so the lid CLEAR→CBORE shelf stays manifold.
- Production `stl/node_v1_*` is untouched; port this silhouette into
  `cad/lib/node_v1.py` only after Cody picks the direction.
