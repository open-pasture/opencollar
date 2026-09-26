# Designing the collar with Claude and Blender

How an agent designs collar parts in Blender and checks its own work.

## Two ways to drive Blender

### 1. Blender MCP (live session)

[blender-mcp](https://github.com/ahujasid/blender-mcp) is a Blender add-on plus an MCP server. Blender stays open on screen; the agent runs Python inside it, inspects the scene, and takes viewport screenshots to look at what it built.

Setup:
1. Install Blender (4.x) from blender.org.
2. Download `addon.py` from the blender-mcp repo. In Blender: *Edit → Preferences → Add-ons → Install from disk*, enable "Blender MCP".
3. In Blender's sidebar (N) → BlenderMCP tab → *Connect to Claude*.
4. Register the server with Claude Code: `claude mcp add blender uvx blender-mcp` (`uv` is already installed on this Mac).

Good for: interactive sessions where you watch the model take shape and steer it.

Cautions: it runs arbitrary Python inside Blender, so only point it at our own files. One Blender instance per server.

### 2. Headless Blender scripts (no MCP)

Blender runs from the command line with a Python script: `blender --background --python make_top_unit.py`. The script builds the part, exports STL/3MF, and renders review images.

Good for: repeatable, version-controlled parts. Every part is a script in the repo, so a dimension change is a one-line edit and a re-run. Works from any agent, no GUI needed.

### Recommendation

Use **both**: headless scripts are the source of truth (committed in `mechanical/`), and the MCP session is for looking around and quick iteration. Final parts must come out of a script so they're reproducible and open.

## How the agent checks its own work

A part isn't done until it passes all of these:

1. **Look at it.** Render fixed views (front, side, top, isometric, section cut through the middle) to PNG and view them. Blender MCP's viewport screenshot does the same live.
2. **Measure it.** The script prints overall dimensions, wall thicknesses at key points, and hole positions, and compares them with the spec (board outlines, cell sizes, connector cut-outs).
3. **Check it's printable.** Blender's bundled *3D Print Toolbox*: manifold (watertight), no inverted normals, minimum wall thickness, overhangs. Optionally a second check in Python with `trimesh`.
4. **Check the fit.** Import the real parts as reference bodies (the nRF9151 Connect Kit outline, MAX-M10S breakout, 26650 cells, M8 connectors, O-ring groove dimensions) and check clearances with boolean intersection: anything overlapping is a failure.
5. **Check mass and balance.** Compute volume × material density per part, plus component masses, and confirm the bottom module lands in the 450–650 g window.
6. **Export.** STL for the fabrication partner, with the print orientation and material noted in the file name or a README.

## Caveat: Blender is a mesh tool

Blender is great for shape, ergonomics and renders, but it isn't a parametric CAD program. Tolerances, O-ring grooves and screw bosses are harder to keep exact, and it doesn't export STEP files (the format injection moulders want).

For V1-alpha prints, Blender scripts are fine. Before production tooling, consider moving the enclosure to a code-based CAD library (**build123d** or **CadQuery**, both Python), which produces exact STEP files and fits the same agent workflow. The Blender scripts can stay for renders.

## Setup (done 2026-09-26)

- Blender 5.2.2 LTS in `/Applications` (checksum verified).
- MCP for Blender add-on (formerly blender-mcp) installed with `uvx mcp-for-blender install-addon` and enabled. Its server auto-starts on port 9876 when Blender opens. Telemetry is off in the add-on and in the server (`DISABLE_TELEMETRY=true`); the Poly Haven / Hyper3D / Sketchfab asset integrations stay off.
- Registered with Claude Code at user scope: `claude mcp add blender --scope user -e DISABLE_TELEMETRY=true -- uvx mcp-for-blender`. New Claude sessions pick it up.
- 3D Print Toolbox installed from extensions.blender.org (in Blender 4.2+ it's an extension, not bundled).
- `mechanical/` pipeline: part scripts, shared helpers, headless build with checks 1–3 and 6 above automated, plus the fit (clearance) check against reference bodies. See `mechanical/README.md`.
- Reference dimensions gathered into `mechanical/lib/dims.py`, each marked published, estimated, to measure, or to tune.

## Still open

- [ ] Measure the unpublished dimensions (list in `mechanical/README.md`)
- [ ] Ask the fabrication partner which printers and materials he has
- [ ] First print run: `fit_test` and `seal_box`, then put the winning sizes into `lib/dims.py`
- [ ] Mass and balance check (step 5) once the top unit and bay exist
