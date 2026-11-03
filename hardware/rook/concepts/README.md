# Rook enclosure concepts

Three **visual languages** for the Rook collar housings. Same internal hardware
envelope as Node V1 so the current electronics, cells, and strap clamps still
fit. These are design studies — not drop-in replacements for `stl/node_v1_*`.

| Concept | Mood | STLs | Hero |
| --- | --- | --- | --- |
| **A — Soft organic** | Large radii, tapered crown, continuous soft silhouette | [`stl/A_organic/`](stl/A_organic/) | ![A](renders/A_organic.png) |
| **B — Clean technical** | Chamfered top, single accent seam at the waist | [`stl/B_technical/`](stl/B_technical/) | ![B](renders/B_technical.png) |
| **C — Minimal low-profile** | Flush faces, hidden fastener seats, no decoration | [`stl/C_minimal/`](stl/C_minimal/) | ![C](renders/C_minimal.png) |

Short notes: [`A-organic.md`](A-organic.md) · [`B-technical.md`](B-technical.md) · [`C-minimal.md`](C-minimal.md).

## Envelope (locked)

| Module | Constraint |
| --- | --- |
| Cap | Footprint **76×160**; columns `(±29.5, ±68/±42)`; clamp `(±20, ±28.5)`; cavity height ≥13 mm |
| Pod | Cavity **82×58×21.5** (one 18650 + Qwiic buzzer); columns `(±37, ±27)`; outer ~92×68 |
| Counterweight | Outer ~**88×74×30**; lid screws `(±22, ±31.5)`; clamp `(±36, ±29.5)` |

## Print

Bambu P2S. Each shell prints **outside / bed face down**, cavity up — no
supports (chamfers ≤45°, organic radii self-supporting). Watertight check runs
in the concept builder (triangulated bad-edge count + post-export STL scan).

```sh
cd hardware/rook/concepts/cad
blender --background --factory-startup --python build_concepts.py
```

## Vs production CAD

Production parts stay under `hardware/rook/stl/node_v1_*` and `cad/lib/node_v1.py`.
Pick a concept direction, then port the outer silhouette into that CAD without
moving screw columns or shrinking the cavity.
