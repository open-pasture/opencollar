# OpenCollar V1-alpha: print list

Draft 1, 2026-09-26. Two test prints first, then the collar itself. All parts in **ASA**, light grey or white, 0.2 mm layers, 6 perimeters, 40 % infill (100 % is fine for the small parts). Files are STL in millimetres.

Pictures of the design are in `renders/`; `collar_v1_alpha.blend` opens in Blender 5.x.

## 1. Test prints (please do these first)

| File | Qty | Orientation | What it tells us |
| --- | --- | --- | --- |
| `fit_test.stl` | 1 | Flat, engraved face up | Best hole sizes on your printer: row A M3 heat-set inserts, row B M3 screw clearance, row C 2 mm O-ring cord groove, row D M6 × 0.75 tap drill. Engraved numbers are the designed size |
| `seal_box_box.stl` | 1 | Open side up | Submersion test of the seal the collar uses |
| `seal_box_lid.stl` | 1 | Groove side up | (with the box) |

Seal box: fit 4 inserts, press ~213 mm of 2 mm silicone O-ring cord into the lid groove (superglue the butt joint), tap the centre hole M6 × 0.75 and screw in the vent, close with 4 × M3 × 8 socket-head screws around a dry paper towel. Hold 1 m under water for 30 minutes, then check the towel.

Please send back: the winning size in each fit-test row, whether the box stayed dry, printer and material, and anything that printed badly. The collar files get updated to your sizes before you print them.

## 2. The collar

| File | Qty | Orientation | Notes |
| --- | --- | --- | --- |
| `top_unit_base.stl` | 1 | Underside down, tree supports under the arch | Rim with the O-ring groove faces up |
| `top_unit_lid.stl` | 1 | Rim down, tree supports inside the roof | Solar panels bond into the two recesses |
| `top_unit_clamp_bar.stl` | 2 | Flat | Clamp the strap under each end of the top unit |
| `bay_cradle.stl` | 1 | On its side (a long edge down) | Strap threads through its tunnel; keeps the tunnel roof a short bridge |
| `bay_ballast_module.stl` | 1 | Top face down | Holds the steel ballast slab |

MJF/SLS PA12 is also fine and needs no supports.

### Hardware

| Item | Qty |
| --- | --- |
| M3 × 4 brass heat-set inserts | 16 (10 lid, 4 clamp bars, 2 bay) |
| M3 × 16 socket-head screws, stainless | 10 (lid, from underneath) |
| M3 × 8 button-head screws, stainless | 4 (clamp bars) |
| M3 × 20 knurled thumbscrews, head ≤ 8 mm | 2 (ballast module to cradle) |
| 2 mm silicone O-ring cord | ~500 mm (top unit groove) |
| M6 × 0.75 ePTFE vent (Amphenol VENT-PS2NGY-O8001) | 1, tapped into the base end wall |
| Mild steel flat bar, 64 × 46 × 16 mm | 1 (~370 g ballast) |

### Estimated weight

| | Approx. |
| --- | --- |
| Top unit: printed parts ~220 g + battery, boards, panels, antennas ~280 g | ~500 g |
| Bay: cradle + module ~135 g + steel 370 g | ~505 g |
| Strap | ~100 g |
| **Collar** | **~1.1–1.2 kg** |

### Still open

- Strap length: around the 107 cm neck section we modelled, the loop takes ~1,156 mm of the 48" (1,219 mm) strap, which leaves little for the buckle. Measure the pilot animals' necks; bigger necks need a longer strap.
- Strap thickness is designed at 4 mm until measured; the strap channel, clamp squeeze and bay tunnel follow it.
- A few board heights and antenna sizes aren't published; they're modelled with margin and get checked against the real parts.
