"""Render a bed-of-nails test fixture around the real carrier board, for TEST-FIXTURE.md.

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python docs/images/test-fixture/render_fixture.py -- <board.glb> <tp.json> <out_dir>

Inputs come from the carrier build: `kicad-cli pcb export glb` of the board, and the
test-pad and hole positions read from the .kicad_pcb (see TEST-FIXTURE.md). Renders:
  fixture-exploded.png  lid, board and probe plate pulled apart
  fixture-closed.png    close-up, board pressed down onto the pins
Illustration only: pin and plate sizes are typical 100-mil fixture values.
"""
import json
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, TPJ, OUT = argv
tp = json.load(open(TPJ))
BW, BH = tp["board"]

# ---------------------------------------------------------------- scene

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, metal=0.0, rough=0.4, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
    if transmission:
        for key in ("Transmission Weight", "Transmission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = transmission
                break
    return m


GOLD = mat("gold", (1.0, 0.72, 0.32), metal=1.0, rough=0.25)
NICKEL = mat("nickel", (0.78, 0.78, 0.76), metal=1.0, rough=0.3)
STEEL = mat("steel", (0.6, 0.62, 0.64), metal=1.0, rough=0.35)
PLATE = mat("g10", (0.9, 0.89, 0.85), rough=0.55)          # fixture plates are often G10 or delrin
OUTLINE = mat("outline", (0.08, 0.35, 0.22), rough=0.5)
BASE = mat("base", (0.12, 0.13, 0.14), rough=0.6)
DELRIN = mat("delrin", (0.93, 0.92, 0.88), rough=0.5)
LID = mat("lid", (0.9, 0.95, 1.0), rough=0.05, transmission=0.9)
FLOOR = mat("floor", (0.93, 0.92, 0.9), rough=0.9)
WIRE = [mat(f"wire{i}", c, rough=0.5) for i, c in enumerate(
    [(0.75, 0.1, 0.1), (0.1, 0.1, 0.1), (0.9, 0.7, 0.1), (0.1, 0.35, 0.8)])]


def cyl(name, r, h, at, m, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts,
                                        location=(at[0], at[1], at[2] + h / 2))
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def cone(name, r, h, at, m):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0.0, depth=h, vertices=24,
                                    location=(at[0], at[1], at[2] + h / 2))
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def box(name, size, at, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(at[0], at[1], at[2] + size[2] / 2))
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    return o


def board_xy(x, y):
    """Board-local mm (origin top-left, y down) to world mm (y up)."""
    return x, -y


# ---------------------------------------------------------------- the board

def import_board(z_bottom):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=GLB)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new("board", None)
    scene.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    # KiCad's GLB is in metres with the board at (100, -100) mm on the page.
    root.scale = (1000, 1000, 1000)
    bpy.context.view_layer.update()
    # The board's underside (bottom pads and mask) is the lowest point of the model.
    lo = min((o.matrix_world @ Vector(c)).z for o in new if o.type == "MESH" for c in o.bound_box)
    root.location = (-100.0, 100.0, z_bottom - lo)
    return root


# ---------------------------------------------------------------- the fixture

PLATE_T = 6.0          # probe plate thickness
PIN_ABOVE = 4.0        # how far each pin sticks up above the plate
M = 12.0               # plate margin around the board


def board_outline(z):
    """Where the board lands: a thin frame at the board's outline."""
    w = 0.6
    for size, at in [((BW, w, w), (BW / 2, 0, z)), ((BW, w, w), (BW / 2, -BH, z)),
                     ((w, BH, w), (0, -BH / 2, z)), ((w, BH, w), (BW, -BH / 2, z))]:
        box("outline", size, at, OUTLINE)


def fixture(board_gap, lid_gap, with_lid=True):
    """Build base, probe plate, pins and (optionally) the lid. The plate's top face is z = 0."""
    cx, cy = BW / 2, -BH / 2
    box("base", (BW + 2 * M + 8, BH + 2 * M + 8, 42), (cx, cy, -PLATE_T - 42), BASE, bevel=2.0)
    box("probe_plate", (BW + 2 * M, BH + 2 * M, PLATE_T), (cx, cy, -PLATE_T), PLATE, bevel=0.6)
    for t in tp["tps"]:
        x, y = board_xy(t["x"], t["y"])
        cyl(f"receptacle_{t['ref']}", 0.84, PLATE_T + 1.0, (x, y, -PLATE_T - 0.5), NICKEL)
        cyl(f"barrel_{t['ref']}", 0.51, 2.2, (x, y, 0.5), NICKEL)
        cyl(f"plunger_{t['ref']}", 0.34, PIN_ABOVE - 2.7 - 0.5, (x, y, 2.7), GOLD)
        cone(f"tip_{t['ref']}", 0.34, 0.5, (x, y, PIN_ABOVE - 0.5), GOLD)
    # alignment pins through two of the carrier's mounting holes (tooling holes on the integrated board)
    for ref in ("H1", "H4"):
        h = next(h for h in tp["holes"] if h["ref"] == ref)
        x, y = board_xy(h["x"], h["y"])
        cyl(f"align_{ref}", h["d"] / 2 - 0.1, PIN_ABOVE + 7.0, (x, y, 0), STEEL)
        cone(f"align_tip_{ref}", h["d"] / 2 - 0.1, 1.5, (x, y, PIN_ABOVE + 7.0), STEEL)
    if with_lid:
        z = board_gap + lid_gap
        box("lid", (BW + 2 * M, BH + 2 * M, 5.0), (cx, cy, z), LID, bevel=0.6)
        # push fingers land on bare board, away from parts
        for (fx, fy) in [(1.5, 57.0), (63.5, 57.0), (24.0, 1.0), (63.5, 1.0)]:
            x, y = board_xy(fx, fy)
            cyl("finger", 1.8, lid_gap - 8.0, (x, y, z - (lid_gap - 8.0)), DELRIN)
        # hinge along the back edge
        bpy.ops.mesh.primitive_cylinder_add(radius=3, depth=BW + 2 * M, vertices=32,
                                            location=(cx, cy + BH / 2 + M, z + 2.5),
                                            rotation=(0, math.pi / 2, 0))
        bpy.context.object.data.materials.append(STEEL)


def floor():
    box("floor", (900, 900, 1), (BW / 2, -BH / 2, -PLATE_T - 43), FLOOR)


def lights(target):
    for name, loc, energy, size in [("key", (-120, -160, 220), 180000, 160),
                                    ("fill", (220, -60, 120), 60000, 200),
                                    ("rim", (40, 220, 160), 90000, 120)]:
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        d = Vector(target) - Vector(loc)
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.95, 0.94, 0.92, 1)
    bg.inputs["Strength"].default_value = 0.6
    scene.world = w


def camera(loc, target, lens=60):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_end = 5000
    c = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scene.camera = c


def render(path, res=(1800, 1250), samples=96):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = path
    scene.view_settings.view_transform = "AgX"
    bpy.ops.render.render(write_still=True)


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


# ---------------------------------------------------------------- views

# 1. Exploded: board lifted above the pins, lid higher still.
floor()
fixture(board_gap=PIN_ABOVE + 30, lid_gap=42)
import_board(PIN_ABOVE + 30)
lights((BW / 2, -BH / 2, 20))
camera((-150, -250, 205), (BW / 2 + 2, -BH / 2, 16), lens=50)
render(f"{OUT}/fixture-exploded.png", samples=64)

# 2. The bed of nails on its own: one pin under every test pad, board outline in green.
clear()
floor()
fixture(board_gap=0, lid_gap=0, with_lid=False)
board_outline(PIN_ABOVE + 0.3)
lights((BW / 2, -BH / 2, 0))
camera((-30, -120, 85), (BW / 2 - 4, -BH / 2 + 12, 0), lens=55)
render(f"{OUT}/fixture-pins.png", res=(1800, 1150), samples=64)
