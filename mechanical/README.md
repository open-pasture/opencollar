# Mechanical

Printed parts for the collar. Every part is a Python script run by Blender, so a dimension change is a one-line edit and a rebuild. See `../docs/DESIGN-TOOLING.md` for why.

## Layout

| Path | What |
| --- | --- |
| `parts/*.py` | One script per part. Builds the geometry, then calls `oc.finish()` |
| `lib/oc.py` | Shared helpers: primitives, booleans, export, renders, checks |
| `lib/collar.py` | V1-alpha geometry (top unit, clamp bars, bay), shared by part scripts and the assembly |
| `assembly/collar.py` | The whole collar on a strap with the bought parts inside; saves `collar_v1_alpha.blend` and presentation renders to `renders/collar/` |
| `PRINT-LIST.md` | What to print, how, and the hardware list, for the fabrication partner |
| `lib/dims.py` | Every bought-part and tolerance dimension, with its source. Parts import from here |
| `exports/<part>/*.stl` | Print files for the fabrication partner (mm) |
| `reference/vendor/` | Vendor drawings and CAD (nRF9151 STEP, Eagle boards, vent and panel drawings). Local only, not committed; sources in `lib/dims.py` |
| `renders/<part>/` | Review images (front, side, top, bottom, iso, section) and `report.json` |

## Build

```sh
./build.sh            # every part
./build.sh seal_box   # one part
./package.sh          # rebuild everything, render the assembly, zip a share package into ../../output/
```

Needs Blender 5.x at `/Applications/Blender.app` (override with `BLENDER=/path/to/blender`). Takes a few seconds per part.

## What every build checks

A part fails the build (non-zero exit) unless:

1. **Manifold** (watertight) with outward normals.
2. **Walls** no thinner than the part's minimum (ray cast inward from every face, like Blender's 3D Print Toolbox).
3. **Size** matches the spec in the script.
4. **Clearance**: no overlap with reference bodies (the bought parts it has to hold).

It also reports volume, solid mass in the chosen material and downward-facing overhang area, and renders six views, including a section cut with cut faces in red.

## Parts

| Part | Files | Print |
| --- | --- | --- |
| `fit_test` | `fit_test.stl` | Flat, engraved face up |
| `seal_box` | `seal_box_box.stl`, `seal_box_lid.stl` | Box open side up; lid groove side up |
| `top_unit` | `top_unit_base.stl`, `top_unit_lid.stl`, `top_unit_clamp_bar.stl` (×2) | Base underside down, lid rim down, both with tree supports; bars flat |
| `bay` | `bay_cradle.stl`, `bay_ballast_module.stl` | Cradle on its side; module top face down |

The collar parts are draft 1: print the fit test and seal box first, put the winning sizes into `lib/dims.py`, rebuild, then print the collar.

## First print run (for the fabrication partner)

Material for everything: **ASA**, light grey or white, 0.2 mm layers, 6 perimeters (walls ≥ 2.4 mm), 40 % infill.

1. **`fit_test`**: one plate that sets our tolerances for your printer. Engraved numbers are the designed size in mm.
   - Row A: M3 × 4 brass heat-set inserts (Adafruit 4255). Press one into each hole with the iron; which holds best without bulging the plastic?
   - Row B: M3 screw clearance. Which lets an M3 screw drop through without rattling?
   - Row C: 2 mm silicone O-ring cord. Which grips the cord and leaves it standing about 0.5 mm proud?
   - Row D: M6 × 0.75 tap drill. Tap each and screw in the vent; which threads cleanly and seals on its O-ring?
2. **`seal_box`**: the seal the top unit will use. Fit 4 inserts, press about 213 mm of O-ring cord into the lid groove (superglue the butt joint), tap the lid's centre hole M6 × 0.75 for the vent, close it with 4 × M3 × 8 socket-head screws and a dry paper towel inside. Hold it 1 m under water for 30 minutes, then check the towel.

Send back: the winning size for each row, whether the box stayed dry, printer and material used, and any print problems (warping, stringing in holes, layer splits).

## Still to measure

Not published anywhere; needed before the top unit and strap mount are drawn. Calipers on the real parts:

- Strap thickness (Heritage 1-3/4" double-thick nylon)
- MAX-M10S breakout height (SMA is tallest), bq24074 board height
- GPS patch total height (ceramic + LNA board + shield) and cable length
- LTE flex antenna size and cable length
- Li-ion pack lead length

## Live sessions

For looking around and quick edits, Blender runs with the MCP for Blender add-on (auto-starts its server on port 9876 when Blender opens) and Claude Code has the `blender` MCP server registered. Anything worth keeping goes back into a script here.
