# Rook enclosure concepts

Design studies for the Rook collar housings. Same internal hardware envelope as
Node V1 so the current electronics, cells, and strap clamps still fit. **Not**
drop-in replacements for `stl/node_v1_*`.

## D — Hybrid (D3 cow-look, current)

Cody’s AI-cow target: tall slim charcoal cap slab, soft radii, strap
slot/keeper/buckle, small low CW, orange = latch + 2–3 screws. **Cap keeps
locked 76×160 envelope** (see fit/break table in [`D-hybrid.md`](D-hybrid.md)).
Not print-ready.

| | |
| --- | --- |
| Notes | [`D-hybrid.md`](D-hybrid.md) |
| STLs | [`stl/D_hybrid/`](stl/D_hybrid/) |
| Builder | [`cad/build_concept_d.py`](cad/build_concept_d.py) |

![D iso](images/D_hybrid_iso.png)

| Assembled | Detail |
| --- | --- |
| ![front](images/D_hybrid_front.png) | ![port](images/D_hybrid_port_closeup.png) |
| ![side](images/D_hybrid_side.png) | ![seam](images/D_hybrid_seam_closeup.png) |
| ![exploded](images/D_hybrid_exploded.png) | ![oat](images/D_hybrid_oat_iso.png) |

## Prior studies (A / B / C)

Organic / technical / minimal shells live on PR
[#17](https://github.com/open-pasture/opencollar/pull/17)
(`cursor/rook-enclosure-concepts-9a36`). D supersedes them as the working
direction.

## Envelope (locked)

| Module | Constraint |
| --- | --- |
| Cap | Footprint **76×160**; columns `(±29.5, ±68/±42)`; clamp `(±20, ±28.5)`; cavity height ≥13 mm |
| Pod | Cavity **82×58×21.5**; columns `(±37, ±27)`; outer ~92×68 |
| Counterweight | Outer ~**88×74×30**; lid screws `(±22, ±31.5)`; clamp `(±36, ±29.5)` |

## Print

Bambu P2S concept plate later — **Cody approves any print.** Each shell prints
outside / bed face down, cavity up; no supports on visible faces. Watertight +
footprint checks run in the concept builder.

```sh
cd hardware/rook/concepts/cad
blender --background --factory-startup --python build_concept_d.py
# Colour heroes land in images/ (tracked). Working views under renders/ (gitignored).
```
