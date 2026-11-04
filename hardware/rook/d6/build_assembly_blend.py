"""Build review/d6_assembly.blend + 4 assembly renders from world STLs.

D7 palette: calm light-gray ASA body; orange (#FF6A2B) only on small functional
accents (latch, screw heads, cue/service dots, tiny clamp-bar end caps).
Clamp bars + fairings use the body colour.

Review-only details (not print STLs): solar panel, strap loop + buckle/keeper,
orange screw heads, latch + service dot, rib lines, recessed glyph panel.

D4 ghost: repo has no real D4_contoured_v3 mesh/blend — keep wbbox placeholders
from out/d4_ghost/. Do NOT mirror a duplicate D4_pod_R.

Cameras match d6-integrate (iso/front/side/top) for before/after compare.

Usage:
  blender --background --factory-startup --python build_assembly_blend.py -- \\
      out/world out/d4_ghost out/assembly_review
  # or: python3 build_assembly_blend.py <world> <d4> <out>   (needs bpy)
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

import bpy
from mathutils import Vector

# Args: last three non-.py tokens
_args = [x for x in sys.argv if not x.endswith(".py") and x != "--"]
if len(_args) < 3:
    raise SystemExit("usage: build_assembly_blend.py <world_dir> <d4_stl_dir> <out_dir>")
WORLD, D4, OUT = _args[-3:]
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOK = os.path.abspath(os.path.join(_HERE, ".."))
_D5_STL = os.path.join(_ROOK, "d5", "stl")
_HYBRID_STL = os.path.join(_ROOK, "concepts", "stl", "D_hybrid")

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = "MILLIMETERS"

# ---- palette (D7r2) -------------------------------------------------------
# Mid light-gray ASA (~0.58 linear, #C9CBCC) — was washing out at 0.78
BODY = (0xC9 / 255, 0xCB / 255, 0xCC / 255)
ORANGE = (1.0, 0x6A / 255, 0x2B / 255)  # #FF6A2B accents only
PANEL_GLASS = (0.05, 0.08, 0.14)   # dark blue-black solar glass
STRAP = (0.18, 0.18, 0.17)
GHOST = (0.10, 0.45, 0.95)
RIB = (0.62, 0.63, 0.64)
GLYPH_PANEL = (0.64, 0.65, 0.66)

# Body colour for all structural families (incl. clamp + fairing)
BODY_KEYS = ("cap", "pod", "cw", "fairing", "saddle", "clamp")


def col(n):
    c = bpy.data.collections.new(n)
    sc.collection.children.link(c)
    return c


def mat(n, rgb, alpha=1.0):
    m = bpy.data.materials.new(n)
    m.diffuse_color = (*rgb[:3], alpha)
    return m


def imp_stl(path, collection, name=None):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    for cc in o.users_collection:
        cc.objects.unlink(o)
    collection.objects.link(o)
    if name:
        o.name = name
    return o


def _bbox_centre(obj):
    lo = Vector(obj.bound_box[0])
    hi = Vector(obj.bound_box[6])
    return (lo + hi) / 2


def _add_box(collection, name, size, loc, rgb, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    collection.objects.link(o)
    o.data.materials.append(mat("m_" + name, rgb))
    return o


def _add_cyl(collection, name, radius, depth, loc, rgb, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    collection.objects.link(o)
    o.data.materials.append(mat("m_" + name, rgb))
    return o


def _find_detail(name):
    for root in (_D5_STL, _HYBRID_STL):
        p = os.path.join(root, name)
        if os.path.exists(p):
            return p
    return None


def _d4_obj(name):
    path = os.path.join(_HERE, "d4.json")
    if not os.path.exists(path):
        return None
    data = json.load(open(path))
    for o in data.get("objs", []):
        if o.get("name") == name:
            return o
    return None


def _wbbox_centre(name):
    o = _d4_obj(name)
    if not o or not o.get("wbbox"):
        return None
    lo, hi = o["wbbox"]
    return Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))


def _wbbox_size(name):
    o = _d4_obj(name)
    if not o or not o.get("wbbox"):
        return None
    lo, hi = o["wbbox"]
    return Vector((hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))


# ---- collections ----------------------------------------------------------
d6 = col("D6_assembly")
ghost = col("D4_contoured_v3_ghost")
details = col("D7_review_details")
body_mat = mat("body_asa", BODY)
orange_mat = mat("accent_orange", ORANGE)

# World STLs
for f in sorted(glob.glob(os.path.join(WORLD, "*.stl"))):
    o = imp_stl(f, d6)
    # All structural parts → body colour (clamps + fairings included)
    o.data.materials.clear()
    o.data.materials.append(body_mat)
    # Tiny orange end caps on clamp bars (not the whole bar)
    if o.name.startswith("clamp_bar"):
        # ~12×10 mm orange end caps so the accent reads in iso
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        ys = sorted(v.y for v in bb)
        xs = sorted(v.x for v in bb)
        zs = sorted(v.z for v in bb)
        mid_x = 0.5 * (xs[0] + xs[-1])
        mid_z = 0.5 * (zs[0] + zs[-1])
        for i, y in enumerate((ys[0], ys[-1])):
            _add_box(
                details,
                f"{o.name}_endcap_{i}",
                (10.0, 3.0, 12.0),
                (mid_x, y, mid_z),
                ORANGE,
            )

# D4 ghost — bounding boxes only (no real D4 mesh in repo). Skip mirror.
gm = mat("d4_ghost", GHOST, 0.25)
ghost_note = "D4 ghost = wbbox placeholders from d4.json; no D4_contoured_v3 mesh/blend in repo."
for f in sorted(glob.glob(os.path.join(D4, "*.stl"))):
    if os.path.basename(f).startswith("._"):
        continue
    o = imp_stl(f, ghost)
    o.name = "D4_" + o.name
    o.data.materials.append(gm)
    o.display_type = "WIRE"
    o.show_in_front = True
    # Intentionally NO D4_pod_R_mirror duplicate

# Pod anchor empties (same as d6-integrate)
for n in ("pod_L", "pod_R"):
    e = bpy.data.objects.new(n + "_anchor", None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 15
    s = -1 if n == "pod_L" else 1
    e.location = (0, s * 126.0, -21.9)
    e.rotation_euler = (math.radians(-s * 29.1418), 0, 0)
    d6.objects.link(e)

# ---- review-only details --------------------------------------------------
# Solar panel (cap_panel_p124) — dark blue-black glass in pocket pose
panel_path = _find_detail("panel_p124.stl")
panel_c = _wbbox_centre("cap_panel_p124")
if panel_path and panel_c is not None:
    p = imp_stl(panel_path, details, name="cap_panel_p124")
    # Centre the print STL on the D4 world pocket centre
    pc = _bbox_centre(p)
    p.location = panel_c - pc
    p.data.materials.clear()
    p.data.materials.append(mat("solar_glass", PANEL_GLASS))
elif panel_c is not None:
    sz = _wbbox_size("cap_panel_p124") or Vector((66.6, 113.6, 2.3))
    _add_box(details, "cap_panel_p124", (sz.x, sz.y, sz.z), panel_c, PANEL_GLASS)

# Latch (orange) + service cue dots (orange)
latch_path = _find_detail("latch.stl")
latch_c = _wbbox_centre("latch")
if latch_path and latch_c is not None:
    L = imp_stl(latch_path, details, name="latch")
    Lc = _bbox_centre(L)
    L.location = latch_c - Lc
    L.data.materials.clear()
    L.data.materials.append(orange_mat)
elif latch_c is not None:
    _add_box(details, "latch", (6.0, 11.0, 8.0), latch_c, ORANGE)

for nm in (
    "cap_plug_service_orange_n68p",
    "cap_plug_service_orange_p68n",
    "cap_plug_service_orange_p68p",
):
    c = _wbbox_centre(nm)
    if c is None:
        continue
    plug_path = _find_detail("plug_service.stl") or _find_detail("plug_service_orange.stl")
    if plug_path:
        pl = imp_stl(plug_path, details, name=nm)
        plc = _bbox_centre(pl)
        pl.location = c - plc
        pl.data.materials.clear()
        pl.data.materials.append(orange_mat)
    else:
        _add_cyl(details, nm, radius=3.5, depth=1.3, loc=c, rgb=ORANGE)

# Strap loop (torus-ish from d4 wbbox) + buckle + keeper
strap_c = _wbbox_centre("strap_loop")
strap_sz = _wbbox_size("strap_loop")
if strap_c is not None and strap_sz is not None:
    # Approximate the D4 strap loop as a thin torus in the YZ plane of the collar
    bpy.ops.mesh.primitive_torus_add(
        major_radius=max(strap_sz.y, strap_sz.z) / 2 - strap_sz.x / 2,
        minor_radius=max(strap_sz.x / 2, 1.5),
        major_segments=64,
        minor_segments=12,
        location=strap_c,
    )
    loop = bpy.context.active_object
    loop.name = "strap_loop"
    # D4 strap_loop is rotated 90° about Y (see d4.json)
    loop.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    for cc in list(loop.users_collection):
        cc.objects.unlink(loop)
    details.objects.link(loop)
    loop.data.materials.append(mat("strap", STRAP))

# Buckle / keeper: D4 wbbox places them floating well below the body in side
# view. Hide until a strap-path pose is authored (do not import).
# (Intentionally skipped — see INTEGRATION.md rough edges.)

# Orange screw heads on cap orange columns + CW lid screws (approx world)
# Cap orange screws from d5_dims-style positions at lid top
cap_z = 19.0  # approx lid top in world (CAP_Z0 + CAP_BASE_H)
for i, (x, y) in enumerate([(29.5, 68.0), (-29.5, 68.0), (29.5, -68.0)]):
    _add_cyl(details, f"screw_cap_orange_{i}", radius=2.8, depth=1.6,
             loc=(x, y, cap_z + 0.5), rgb=ORANGE)
# CW screw heads (world: CW flipped 180° X at z≈-465.75)
# Assembled lid outer faces -Z; screws near (±22, ±54) in print → mirrored in world Y
cw_lid_z = -465.75 - 3.2 - 18.0 - 7.5 + 1.0  # rough outer
for i, (x, y) in enumerate([(22, 54), (-22, 54), (22, -54), (-22, -54)]):
    _add_cyl(details, f"screw_cw_{i}", radius=2.4, depth=1.4,
             loc=(x, y, cw_lid_z), rgb=ORANGE)

# Rib lines (review) — shallow strips on cap lid top
for i, y in enumerate((-50.0, -25.0, 25.0, 50.0)):
    _add_box(details, f"rib_cap_{i}", (60.0, 0.6, 0.35), (0.0, y, 20.5), RIB)
# Recessed glyph panel on cap lid (review placeholder)
_add_box(details, "glyph_panel_recess", (28.0, 18.0, 0.5), (0.0, -40.0, 20.2), GLYPH_PANEL)

# Text note as empty
note = bpy.data.objects.new("NOTE_d4_ghost", None)
note.empty_display_type = "PLAIN_AXES"
note.empty_display_size = 1
note["ghost_note"] = ghost_note
details.objects.link(note)

blend_path = os.path.join(OUT, "d6_assembly.blend")
# Also copy/symlink path expected by INTEGRATION.md
review_blend = os.path.join(_HERE, "review", "d6_assembly.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

# ---- renders: same cameras as d6-integrate --------------------------------
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_xray = False
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.render.film_transparent = False
w = bpy.data.worlds.new("w")
sc.world = w
w.color = (0.94, 0.92, 0.86)

# Ghost wire for render
for o in ghost.objects:
    if o.type != "MESH":
        continue
    m = o.modifiers.new("wf", "WIREFRAME")
    m.thickness = 0.35
    o.display_type = "TEXTURED"
    o.data.materials.clear()
    o.data.materials.append(mat("ghostR", GHOST, 1.0))

objs = [o for o in list(d6.objects) + list(details.objects) if o.type == "MESH"]
lo = Vector([min((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
hi = Vector([max((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
ctr = (lo + hi) / 2
ext = (hi - lo).length
cam_d = bpy.data.cameras.new("cam")
cam_d.type = "ORTHO"
cam_d.ortho_scale = ext * 1.05
cam_d.clip_end = 1e5
cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam

# Identical view directions / naming as d6-integrate
for name, d in {
    "iso": (1, -1, 0.8),
    "front": (0, -1, 0.0001),
    "side": (1, 0, 0.0001),
    "top": (0.0001, 0, 1),
}.items():
    d = Vector(d).normalized()
    cam.location = ctr + d * ext * 2
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, f"d6_assembly_{name}.png")
    bpy.ops.render.render(write_still=True)

# Mirror renders into hardware/rook/d6/renders for the review pack
render_dir = os.path.join(_HERE, "renders")
os.makedirs(render_dir, exist_ok=True)
import shutil
for name in ("iso", "front", "side", "top"):
    src = os.path.join(OUT, f"d6_assembly_{name}.png")
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(render_dir, f"d6_assembly_{name}.png"))
# Joint close-up: reuse iso framing but tighter ortho on cap–pod L joint
joint_objs = [o for o in d6.objects if o.type == "MESH" and (
    o.name.startswith("cap_") or o.name.startswith("pod_L") or "fairing_cap_pod_L" in o.name)]
if joint_objs:
    jlo = Vector([min((o.matrix_world @ Vector(c))[i] for o in joint_objs for c in o.bound_box) for i in range(3)])
    jhi = Vector([max((o.matrix_world @ Vector(c))[i] for o in joint_objs for c in o.bound_box) for i in range(3)])
    jctr = (jlo + jhi) / 2
    jext = (jhi - jlo).length
    cam_d.ortho_scale = jext * 1.2
    d = Vector((1, -1, 0.6)).normalized()
    cam.location = jctr + d * jext * 2
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, "d6_assembly_joint.png")
    bpy.ops.render.render(write_still=True)
    shutil.copy2(sc.render.filepath, os.path.join(render_dir, "d6_assembly_joint.png"))

# Save blend into review/ as well
os.makedirs(os.path.dirname(review_blend), exist_ok=True)
shutil.copy2(blend_path, review_blend)

print("OK", ghost_note)
print("blend", blend_path)
print("renders", OUT)
