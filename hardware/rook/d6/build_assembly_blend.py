"""Build review/d6_assembly.blend + assembly renders from world STLs.

D7r4 review pack (op-brand):
  - Palette DEFAULT = charcoal (D4_contoured_v3 body ~#3A3C3E, roughness 0.6).
    Secondary = light (#C9CBCC). Switch: --palette charcoal|light  (or env
    D6_PALETTE). Orange accents unchanged (#FF6A2B).
  - Strap: slim flat band (≈44.45 × 3.0) on a YZ ring through the saddle
    channel and under the CW clamp; D4-style buckle + keeper.
  - Orange only: one small dot per pod lid (no collar tab; latch charcoal).
    No orange saddles / clamp endcaps / screw dashes.

Usage:
  blender --background --factory-startup --python build_assembly_blend.py -- \\
      out/world out/d4_ghost out/assembly_review [--palette charcoal|light]
"""
from __future__ import annotations

import glob
import json
import math
import os
import shutil
import sys

import bpy
from mathutils import Vector

# ---- args -----------------------------------------------------------------
_raw = [x for x in sys.argv if x != "--"]
_args = [x for x in _raw if not x.endswith(".py")]
_palette = os.environ.get("D6_PALETTE", "charcoal").strip().lower()
if "--palette" in _args:
    i = _args.index("--palette")
    if i + 1 < len(_args):
        _palette = _args[i + 1].strip().lower()
        del _args[i : i + 2]
_args = [x for x in _args if not x.startswith("--")]
if len(_args) < 3:
    raise SystemExit(
        "usage: build_assembly_blend.py <world_dir> <d4_stl_dir> <out_dir> "
        "[--palette charcoal|light]"
    )
WORLD, D4, OUT = _args[-3:]
if _palette not in ("charcoal", "light"):
    raise SystemExit(f"unknown palette {_palette!r}; use charcoal|light")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOK = os.path.abspath(os.path.join(_HERE, ".."))
_D5_STL = os.path.join(_ROOK, "d5", "stl")
_HYBRID_STL = os.path.join(_ROOK, "concepts", "stl", "D_hybrid")

os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = "MILLIMETERS"

# ---- palette --------------------------------------------------------------
ORANGE = (1.0, 0x6A / 255, 0x2B / 255)  # #FF6A2B
PANEL_GLASS = (0.05, 0.08, 0.14)
# D7r7 review solar look — navy strips + charcoal rib/bezel (matte)
NAVY_SOLAR = (0x1B / 255, 0x2A / 255, 0x4A / 255)  # #1B2A4A
CHARCOAL_SOLAR = (0x2A / 255, 0x2C / 255, 0x2E / 255)
GHOST = (0.10, 0.45, 0.95)
STRAP = (0.14, 0.14, 0.13)
HARDWARE = (0.22, 0.22, 0.21)  # buckle / keeper — dark gray


def _read_d4_body_rgb():
    """Try D4_contoured_v3.blend body material; else #3A3C3E."""
    candidates = [
        os.path.join(_HERE, "review", "D4_contoured_v3.blend"),
        os.path.join(_ROOK, "D4_contoured_v3.blend"),
        "/Downloads/opencollar-review/D4_contoured_v3.blend",
        os.path.expanduser("~/Downloads/opencollar-review/D4_contoured_v3.blend"),
        "/home/ubuntu/Downloads/opencollar-review/D4_contoured_v3.blend",
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with bpy.data.libraries.load(path, link=False) as (src, dst):
                dst.materials = [m for m in src.materials if m][:12]
            for m in dst.materials:
                if m is None:
                    continue
                # Prefer a body-ish name; else first opaque diffuse
                n = (m.name or "").lower()
                col = None
                if m.use_nodes and m.node_tree:
                    for node in m.node_tree.nodes:
                        if node.type == "BSDF_PRINCIPLED":
                            c = node.inputs.get("Base Color")
                            if c is not None:
                                col = tuple(c.default_value[:3])
                                break
                if col is None:
                    col = tuple(m.diffuse_color[:3])
                if col and ("body" in n or "asa" in n or "charcoal" in n or "plastic" in n):
                    return col, path
                if col and max(col) < 0.55:
                    return col, path
        except Exception:
            continue
    return (0x3A / 255, 0x3C / 255, 0x3E / 255), None


_CHARCOAL, _D4_MAT_SRC = _read_d4_body_rgb()
_LIGHT = (0xC9 / 255, 0xCB / 255, 0xCC / 255)

if _palette == "charcoal":
    BODY = _CHARCOAL
    RIB = tuple(min(1.0, c + 0.08) for c in BODY)
    GLYPH_PANEL = tuple(min(1.0, c + 0.06) for c in BODY)
    WORLD_BG = (0.55, 0.55, 0.52)
else:
    BODY = _LIGHT
    RIB = (0.62, 0.63, 0.64)
    GLYPH_PANEL = (0.64, 0.65, 0.66)
    WORLD_BG = (0.94, 0.92, 0.86)

# Strap / channel (must match assembly.py)
STRAP_W = 44.45
STRAP_T = 3.0
CHANNEL_W = 46.45


def col(n):
    c = bpy.data.collections.new(n)
    sc.collection.children.link(c)
    return c


def mat(n, rgb, alpha=1.0, rough=0.6):
    m = bpy.data.materials.new(n)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*rgb[:3], 1.0)
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = float(rough)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
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


def _add_box(collection, name, size, loc, rgb, rot=(0, 0, 0), rough=0.6):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (float(size[0]), float(size[1]), float(size[2]))
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    collection.objects.link(o)
    o.data.materials.append(mat("m_" + name, rgb, rough=rough))
    return o


def _add_cyl(collection, name, radius, depth, loc, rgb, rot=(0, 0, 0), rough=0.55):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    collection.objects.link(o)
    o.data.materials.append(mat("m_" + name, rgb, rough=rough))
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


def _add_strap_loop(collection):
    """Slim flat strap band in the YZ plane through saddle + under CW clamp.

    D4 strap_loop: rot 90° about Y, wbbox X=44, YZ circle ~471, centre z=-232.
    Fitted here so the band midplane kisses the saddle channel (~z=-6.85) and
    sits in the CW tub↔clamp gap (~z=-460.85). Cross-section ≈44.45 × 3.0.
    """
    # Fitted ring (see D7r4 notes): top at saddle channel, bottom in CW gap
    zc = -233.85
    major_r = 227.0
    # Bezier circle defaults to XY; rotate 90° about Y → YZ plane (D4).
    bpy.ops.curve.primitive_bezier_circle_add(
        radius=major_r, location=(0.0, 0.0, zc), enter_editmode=False
    )
    curve = bpy.context.active_object
    curve.name = "strap_loop_curve"
    curve.rotation_euler = (0.0, math.radians(90.0), 0.0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # Rectangular bevel profile: width along X (strap), thickness radial
    bpy.ops.curve.primitive_bezier_circle_add(radius=1.0, location=(0, 0, 0))
    bevel = bpy.context.active_object
    bevel.name = "strap_bevel_profile"
    # Turn the circle into a flat rectangle via scale (approx) — use a poly curve
    bpy.data.objects.remove(bevel, do_unlink=True)

    # Build a 2-point rectangular curve profile (width × thickness)
    bevel_data = bpy.data.curves.new("strap_bevel_data", type="CURVE")
    bevel_data.dimensions = "2D"
    bevel_data.fill_mode = "NONE"
    sp = bevel_data.splines.new("POLY")
    hw, ht = STRAP_W / 2.0, STRAP_T / 2.0
    sp.points.add(3)  # 4 points total
    for i, (x, y) in enumerate(((-hw, -ht), (hw, -ht), (hw, ht), (-hw, ht))):
        sp.points[i].co = (x, y, 0.0, 1.0)
    sp.use_cyclic_u = True
    bevel_obj = bpy.data.objects.new("strap_bevel_profile", bevel_data)
    sc.collection.objects.link(bevel_obj)

    cd = curve.data
    cd.dimensions = "3D"
    cd.fill_mode = "FULL"
    cd.bevel_mode = "OBJECT"
    cd.bevel_object = bevel_obj
    cd.use_fill_caps = True
    cd.resolution_u = 64

    # Convert to mesh
    bpy.ops.object.select_all(action="DESELECT")
    curve.select_set(True)
    bpy.context.view_layer.objects.active = curve
    bpy.ops.object.convert(target="MESH")
    loop = bpy.context.active_object
    loop.name = "strap_loop"
    bpy.data.objects.remove(bevel_obj, do_unlink=True)
    try:
        bpy.data.curves.remove(bevel_data, do_unlink=True)
    except Exception:
        pass
    for cc in list(loop.users_collection):
        cc.objects.unlink(loop)
    collection.objects.link(loop)
    loop.data.materials.append(mat("strap", STRAP, rough=0.7))
    return loop


def _strap_point(angle_deg, major_r=227.0, zc=-233.85):
    """Point on the strap midplane (YZ ring) + outward normal (for flat-on-strap)."""
    a = math.radians(angle_deg)
    # Circle in YZ centred at (0,0,zc); angle 0 = +Y, 90 = +Z top, -90/+270 = bottom
    y = major_r * math.sin(a)
    z = zc + major_r * math.cos(a)
    # Tangent about X: rotate so local +Z of a flat part points outward (radial)
    # At angle a from +Z toward +Y, outward normal in YZ is (0, sin a, cos a)
    # Euler X rot that maps local +Z to that normal: ...
    # Simpler: rotate about X by -a so a plate in XY lies tangent to the ring.
    return Vector((0.0, y, z)), (-a, 0.0, 0.0)


def _add_buckle_keeper(collection):
    """D7r8 buckle + flat rectangular keeper — square to the strap, not a hoop.

    Buckle: open rect frame ≈24×30×3 flat on strap (no diagonal tongue bar).
    Keeper: flat rectangular frame ~24×6×2, ≤3 mm proud, square to strap.
    Placed toward the buckle (not under the pod skirt) so side view stays clean.
    """
    # Buckle + keeper past the pod free-end (pod tip ≈ |y| 187) so side view
    # does not show a thin bar under the skirt. Angles → |y| ≳ 200.
    b_pos, b_eul = _strap_point(-68.0)
    k_pos, k_eul = _strap_point(-62.0)

    major_r = 227.0
    zc = -233.85

    def _on_surface(pos, proud=1.6):
        v = Vector((pos.x, pos.y, pos.z - zc))
        if v.length < 1e-6:
            return pos
        return Vector((0.0, 0.0, zc)) + v.normalized() * (major_r + proud)

    b_pos = _on_surface(b_pos, proud=1.7)
    # Keeper ≤3 mm proud; ~1.8 mm typical
    k_pos = _on_surface(k_pos, proud=1.8)

    outer = _add_box(
        collection, "buckle_frame", (24.0, 30.0, 3.0), b_pos, HARDWARE,
        rot=b_eul, rough=0.55,
    )
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=b_pos)
    hole = bpy.context.active_object
    hole.name = "buckle_opening"
    hole.scale = (18.0, 22.0, 4.0)
    hole.rotation_euler = b_eul
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for cc in list(hole.users_collection):
        cc.objects.unlink(hole)
    collection.objects.link(hole)
    bpy.ops.object.select_all(action="DESELECT")
    outer.select_set(True)
    bpy.context.view_layer.objects.active = outer
    mod = outer.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = hole
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(hole, do_unlink=True)
    # D7r7: no buckle_tongue — was reading as a diagonal bar left of the buckle

    # Flat rectangular keeper frame (not a torus hoop). Local: X across strap,
    # Y along strap (~6 mm), Z proud (~2 mm). Opening lets the strap through.
    keeper_outer = _add_box(
        collection, "keeper", (STRAP_W + 6.0, 6.0, 2.0), k_pos, HARDWARE,
        rot=k_eul, rough=0.55,
    )
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=k_pos)
    khole = bpy.context.active_object
    khole.name = "keeper_opening"
    khole.scale = (STRAP_W + 1.0, 3.2, 3.0)
    khole.rotation_euler = k_eul
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for cc in list(khole.users_collection):
        cc.objects.unlink(khole)
    collection.objects.link(khole)
    bpy.ops.object.select_all(action="DESELECT")
    keeper_outer.select_set(True)
    bpy.context.view_layer.objects.active = keeper_outer
    kmod = keeper_outer.modifiers.new("khole", "BOOLEAN")
    kmod.operation = "DIFFERENCE"
    kmod.object = khole
    bpy.ops.object.modifier_apply(modifier=kmod.name)
    bpy.data.objects.remove(khole, do_unlink=True)


def _purge_curves_and_wires():
    """Delete leftover curves and force mesh display — no wireframe artifacts."""
    for o in list(bpy.data.objects):
        if o.type == "CURVE":
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.curves):
        if c.users == 0:
            bpy.data.curves.remove(c)
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.display_type = "TEXTURED"
            o.show_in_front = False


def _delete_ghost_wires(ghost_col):
    """D4 ghost wbbox wires cause thin frames in the review blend — remove them."""
    for o in list(ghost_col.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def _world_bbox(obj):
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _load_d4_profile():
    """D4 housing profile (stations / roofline / end_shoulder), mm, Z-up."""
    candidates = [
        os.path.join(_HERE, "review", "d4_profile.json"),
        os.path.join(_HERE, "d4_profile.json"),
        "/home/ubuntu/.cursor/projects/agent-repos-opencollar/uploads/d4_profile_209f.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            return json.load(open(path)), path
    raise FileNotFoundError("d4_profile.json not found")


def _lerp_table(rows, key_x, key_y, x):
    """Linear interpolate key_y vs key_x from sorted rows."""
    xs = [float(r[key_x]) for r in rows]
    ys = [float(r[key_y]) for r in rows]
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / max(xs[i + 1] - xs[i], 1e-9)
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def _flared_section_xz(hw_lid, hw_skirt, z_bot, z_top, chamfer=1.8):
    """Hard-surface CCW section: flat lid + sharp 1.8 mm chamfer + vertical walls.

    Profile is a clean polyline (few segments) so the loft silhouette stays a
    clean tiered block — no soft sleeve, no noisy side facets.
    """
    ch = 1.8  # fixed visible chamfer
    # Vertical wall for most of the height; flare only in the bottom band
    z_wall_bot = z_bot + max(3.0, 0.22 * (z_top - z_bot))
    pts = [
        (-hw_lid + ch, z_top),          # flat lid L
        (hw_lid - ch, z_top),           # flat lid R
        (hw_lid, z_top - ch),           # R chamfer
        (hw_lid, z_wall_bot),           # R vertical wall
        (hw_skirt, z_bot + 0.4),        # R flare to skirt
        (hw_skirt - ch * 0.4, z_bot),   # underside R
        (-hw_skirt + ch * 0.4, z_bot),  # underside L
        (-hw_skirt, z_bot + 0.4),       # L flare
        (-hw_lid, z_wall_bot),          # L vertical wall
        (-hw_lid, z_top - ch),          # L chamfer
    ]
    return pts, ch


def _poly_digit_0(height=9.5, depth=1.4, stroke=1.55):
    """Rounded-rectangle ring '0' — simple manifold prism, no font."""
    import bmesh as _bm
    w = float(height) * 0.58
    h = float(height)
    d = float(depth)
    sw = float(stroke)
    # Outer rounded-rect via bevelled cube, then inner hole
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    outer = bpy.context.active_object
    outer.scale = (w, h, d)
    bpy.ops.object.transform_apply(scale=True)
    bev = outer.modifiers.new("round", "BEVEL")
    bev.width = min(1.6, w * 0.28)
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(40.0)
    bpy.ops.object.modifier_apply(modifier=bev.name)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    hole = bpy.context.active_object
    hole.scale = (max(0.9, w - 2.0 * sw), max(0.9, h - 2.0 * sw), d * 1.4)
    bpy.ops.object.transform_apply(scale=True)
    bev = hole.modifiers.new("round", "BEVEL")
    bev.width = min(1.1, (w - 2.0 * sw) * 0.25)
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(40.0)
    bpy.ops.object.modifier_apply(modifier=bev.name)

    bpy.ops.object.select_all(action="DESELECT")
    outer.select_set(True)
    bpy.context.view_layer.objects.active = outer
    mod = outer.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = hole
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(hole, do_unlink=True)
    # Manifold cleanup
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.01)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    return outer


def _poly_digit_1(height=9.5, depth=1.4, stroke=1.55):
    """Vertical bar + short top flag — manifold stem ∪ flag cubes."""
    h = float(height)
    d = float(depth)
    sw = max(float(stroke), 1.85)  # thicker stem so '1' reads clearly
    fw, fh = sw * 1.45, sw * 0.85

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    stem = bpy.context.active_object
    stem.scale = (sw, h, d)
    bpy.ops.object.transform_apply(scale=True)

    # Flag at top-left (−X, +Y); overlaps stem so UNION is solid
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(-0.5 * sw - 0.30 * fw, 0.5 * h - 0.55 * fh, 0.0),
    )
    flag = bpy.context.active_object
    flag.scale = (fw, fh, d)
    bpy.ops.object.transform_apply(scale=True)

    bpy.ops.object.select_all(action="DESELECT")
    stem.select_set(True)
    bpy.context.view_layer.objects.active = stem
    mod = stem.modifiers.new("flag_u", "BOOLEAN")
    mod.operation = "UNION"
    mod.object = flag
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(flag, do_unlink=True)

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.01)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    return stem


def _make_001_cutters(size=9.5, depth=1.4, font_path=None):
    """Three polygon glyphs spaced along WORLD +X (same on both lids).

    Local frame: baseline +X (L→R in TOP), letter-up +Y, depth +Z.
    ≥1.2 mm gap between glyph AABBs. No font / no trough.
    """
    gap = 1.25
    half = float(depth) * 0.5
    parts = []
    for i, kind in enumerate(("0", "0", "1")):
        if kind == "0":
            c = _poly_digit_0(height=size, depth=depth)
        else:
            c = _poly_digit_1(height=size, depth=depth)
        c.name = f"cutter_001_{kind}_{i}"
        # Force exact Z prism depth (closed manifold slab)
        zs = [v.co.z for v in c.data.vertices]
        z0, z1 = min(zs), max(zs)
        span = max(z1 - z0, 1e-6)
        for v in c.data.vertices:
            t = (v.co.z - z0) / span
            v.co.z = -half + t * float(depth)
        bpy.ops.object.select_all(action="DESELECT")
        c.select_set(True)
        bpy.context.view_layer.objects.active = c
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        xs = [v.co.x for v in c.data.vertices]
        parts.append((c, max(xs) - min(xs)))
        print(
            f"  poly '{kind}': widthX={parts[-1][1]:.2f} height≈{size:.1f} "
            f"verts={len(c.data.vertices)}"
        )
    spans = [w for _, w in parts]
    total = sum(spans) + gap * (len(spans) - 1)
    x = -0.5 * total
    cutters = []
    for c, w in parts:
        c.location = (x + 0.5 * w, 0.0, 0.0)
        cutters.append(c)
        x += w + gap
    return cutters


def _verify_001_pit(obj, a_deg, r_out, zc, h_expect, depth=0.6):
    """Return (ok, measured_depth_mm) by sampling radial heights near a_deg."""
    roof, pit = [], []
    h_ref = float(h_expect)
    for v in obj.data.vertices:
        co = v.co
        yy, zz = co.y, co.z - zc
        ang = math.degrees(math.atan2(yy, zz))
        if abs(ang - a_deg) > 4.0:
            continue
        if abs(co.x) > 14.0:
            continue
        rad = math.hypot(yy, zz) - r_out
        if abs(rad - h_ref) < 0.35:
            roof.append(rad)
        elif (h_ref - 0.95) <= rad <= (h_ref - 0.35):
            pit.append(rad)
    if len(roof) < 8 or len(pit) < 8:
        return False, 0.0
    top = sorted(roof)[len(roof) // 2]
    measured = top - min(pit)
    ok = 0.45 <= measured <= 0.85
    return ok, round(measured, 3)


def _arc_solid(a0_deg, a1_deg, h_fn, h_bot, half_w, zc, r_out, n_seg=64, name="arc_solid", angles=None):
    """D7r15: clean annular slab — constant/variable roof, extruded across X.

    2D profile in the circumferential (YZ) plane, extruded ±half_w in X.
    Straight side walls. No subdiv. h_fn(a_deg) → roof height above strap outer.
    Pass `angles` to force exact tier breakpoints (avoids chord notches).
    """
    import bmesh
    bm = bmesh.new()
    if angles is not None:
        angle_list = [float(a) for a in angles]
    else:
        a0, a1 = float(a0_deg), float(a1_deg)
        if a1 < a0:
            a0, a1 = a1, a0
        n = max(4, int(n_seg))
        angle_list = [a0 + (a1 - a0) * i / n for i in range(n + 1)]
    rings = []
    for a_deg in angle_list:
        a = math.radians(a_deg)
        h_top = float(h_fn(a_deg))
        sa, ca = math.sin(a), math.cos(a)
        # 4 corners: (±X, roof/bot) in radial frame
        pts = [
            (-half_w, r_out + h_top),
            ( half_w, r_out + h_top),
            ( half_w, r_out + h_bot),
            (-half_w, r_out + h_bot),
        ]
        ring = []
        for lx, rr in pts:
            ring.append(bm.verts.new((lx, rr * sa, zc + rr * ca)))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    n = len(rings) - 1
    for i in range(n):
        a_ring, b_ring = rings[i], rings[i + 1]
        for j in range(4):
            j2 = (j + 1) % 4
            try:
                bm.faces.new([a_ring[j], a_ring[j2], b_ring[j2], b_ring[j]])
            except ValueError:
                pass
    try:
        bm.faces.new(rings[0])
    except ValueError:
        pass
    try:
        bm.faces.new(list(reversed(rings[-1])))
    except ValueError:
        pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    return obj


def _bool_union(target, other, tag="union"):
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new(tag, "BOOLEAN")
    mod.operation = "UNION"
    mod.object = other
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as exc:
        print(f"  union {tag} warn: {exc}")
        if tag in [m.name for m in target.modifiers]:
            try:
                target.modifiers.remove(target.modifiers[tag])
            except Exception:
                pass
    try:
        bpy.data.objects.remove(other, do_unlink=True)
    except Exception:
        pass
    return target


def _add_d4_loft_shell(details_col, body_rgb):
    """D7r16: extruded tier solids + 45° ramps + 1.8 mm tier/rail chamfers.

    Cap / mid / pod are arc-concentric slabs extruded across the strap; ramps
    are straight 45° wedges. Bevel ONLY side rails + tier-break lips (never
    every dense across-strap roof edge — that caused ripples/creases).
    Closed charcoal roof; polygon 001 cut AFTER bevel on WORLD +X.
    """
    profile, profile_path = _load_d4_profile()
    stations = profile["stations"]
    end_sh = profile.get("end_shoulder", {})
    d4_r_out = float(profile["strap"]["r_outer"])
    d4_ang0 = float(profile["housing_angle_range_deg"][0])
    d4_ang1 = float(profile["housing_angle_range_deg"][1])
    D4_CAP_MAX = float(profile.get("max_top_above_strap_outer_mm", 27.6))
    d4_arc_mm = float(profile.get("housing_arc_length_mm_at_r_outer", 363.5))

    major_r = 227.0
    zc = -233.85
    r_out = major_r + STRAP_T / 2.0
    strap_outer_z0 = zc + r_out

    PANEL_LAND_Z = 41.4
    CAP_H = PANEL_LAND_Z - strap_outer_z0 + 1.5
    CAP_H_DRIVER = (
        "cap_lid panel land z=41.4 (+1.5 skin); cannot reach ~39 mm (1.4×D4) "
        "without lowering the land / lid stack — see review/height_options.md"
    )
    POD_H = 25.0
    POD_H_DRIVER = "review target ≈1.4× D4 pod (print lids hidden; STL stack still 26.4)"
    DROP = CAP_H - POD_H
    STAGE = min(12.0, DROP * 0.5)
    MID_H = CAP_H - STAGE
    BOTTOM = -4.9

    POD_W = 68.0
    CAP_W = 76.0
    MID_W = 72.0

    d6_ang0, d6_ang1 = -43.5, 45.0
    d6_body0, d6_body1 = -41.5, 42.5
    drop_tail = abs(d6_ang0) - abs(d6_body0)
    ARC_DRIVER = (
        "review shell matches D4 −43.5…+45.0° (≈363 mm outer arc at D4 r). "
        "Print pod_L/R_base tips |Y|≈183 (~±53.7°) are hidden under shell; "
        "that tip would set the min arc if the shell had to cover exposed pods."
    )

    PANEL_LAND_L = 116.0
    CAP_WALL_EXTRA = 4.0
    cap_half_y = PANEL_LAND_L * 0.5 + CAP_WALL_EXTRA
    A_CAP = math.degrees(math.asin(min(0.999, cap_half_y / major_r)))
    DEG_PER_MM = 180.0 / (math.pi * r_out)
    # Exact 45° ramp: run_mm = rise_mm
    ramp_deg = STAGE * DEG_PER_MM
    land_deg = 5.5
    A_R1_0 = A_CAP
    A_R1_1 = A_CAP + ramp_deg
    A_LAND_0 = A_R1_1
    A_LAND_1 = A_LAND_0 + land_deg
    A_R2_0 = A_LAND_1
    A_R2_1 = A_R2_0 + ramp_deg

    cap_block_arc_mm = 2.0 * A_CAP * math.pi / 180.0 * r_out
    d4_cap_half_deg = 17.0
    d4_cap_block_arc_mm = 2.0 * d4_cap_half_deg * math.pi / 180.0 * d4_r_out

    def d4_angle_to_d6(a_d4):
        t = (a_d4 - d4_ang0) / max(d4_ang1 - d4_ang0, 1e-9)
        return d6_ang0 + t * (d6_ang1 - d6_ang0)

    def roof_at_d6_angle(a_d6):
        aa = abs(a_d6)
        if aa <= A_R1_0:
            return CAP_H, CAP_H_DRIVER
        if aa < A_R1_1:
            t = (aa - A_R1_0) / max(A_R1_1 - A_R1_0, 1e-9)
            return CAP_H + (MID_H - CAP_H) * t, f"stage1 45° ramp ≤{STAGE:.1f}mm"
        if aa < A_LAND_1:
            return MID_H, f"mid landing {MID_H:.1f}mm"
        if aa < A_R2_1:
            t = (aa - A_R2_0) / max(A_R2_1 - A_R2_0, 1e-9)
            return MID_H + (POD_H - MID_H) * t, f"stage2 45° ramp ≤{STAGE:.1f}mm"
        return POD_H, POD_H_DRIVER

    def _const(h):
        return lambda a: h

    def _ramp(a0, a1, h0, h1):
        def fn(a):
            t = (abs(a) - a0) / max(a1 - a0, 1e-9)
            t = max(0.0, min(1.0, t))
            return h0 + (h1 - h0) * t
        return fn

    def _pod_h(a_deg):
        """Pod roof with soft end drop past body limit."""
        aa = abs(a_deg)
        h = POD_H
        body_lim = abs(d6_body0) if a_deg < 0 else d6_body1
        if aa > body_lim:
            t_end = min(1.0, max(0.0, (aa - body_lim) / max(drop_tail + 0.8, 1e-9)))
            s = t_end * t_end * (3.0 - 2.0 * t_end)
            h = h * (1.0 - s * s) + 1.2 * s * s
        return h

    # ONE continuous arc solid — height from the clean polyline (tiers +
    # straight 45° ramps). No per-tier unions → no notches/spurs at joints.
    def _h_full(a_deg):
        h, _ = roof_at_d6_angle(a_deg)
        # end drop
        aa = abs(a_deg)
        body_lim = abs(d6_body0) if a_deg < 0 else d6_body1
        if aa > body_lim:
            t_end = min(1.0, max(0.0, (aa - body_lim) / max(drop_tail + 0.8, 1e-9)))
            s = t_end * t_end * (3.0 - 2.0 * t_end)
            h = h * (1.0 - s * s) + 1.2 * s * s
        return h

    def _w_full(a_deg):
        aa = abs(a_deg)
        if aa <= A_CAP:
            return CAP_W * 0.5
        if aa < A_R2_1:
            t = (aa - A_CAP) / max(A_R2_1 - A_CAP, 1e-9)
            return 0.5 * (CAP_W + (POD_W - CAP_W) * t)
        return POD_W * 0.5

    # Dense enough for a smooth arc silhouette; exact breakpoints included.
    # Use variable half-width by building with a mid width then... actually
    # keep constant half-width = CAP_W/2 for clean side walls (D4-like),
    # pod/cap width difference is secondary to notch-free roof.
    # Exact breakpoints + dense fill → smooth arc per tier, sharp ramp corners
    _breaks = sorted({
        round(x, 4) for x in (
            d6_ang0, d6_body0,
            -A_R2_1, -A_LAND_1, -A_R1_1, -A_CAP,
            0.0,
            A_CAP, A_R1_1, A_LAND_1, A_R2_1,
            d6_body1, d6_ang1,
        )
    })
    angle_list = []
    for i in range(len(_breaks) - 1):
        a0, a1 = _breaks[i], _breaks[i + 1]
        span = abs(a1 - a0)
        # Dense on flats for smooth arc walls; ramps keep only endpoints (straight 45°)
        if span < 0.05:
            continue
        # Ramp spans are ~3° — keep just the two endpoints (n=1 adds start only)
        is_ramp = span < 4.0 and any(
            abs(abs(a0) - abs(b)) < 0.05 or abs(abs(a1) - abs(b)) < 0.05
            for b in (A_R1_0, A_R1_1, A_R2_0, A_R2_1)
        ) and abs(
            _h_full(a0) - _h_full(a1)
        ) > 2.0
        step = 0.15 if not is_ramp else span  # denser flats → fewer shade ripples
        n = max(1, int(math.ceil(span / step)))
        for k in range(n):
            angle_list.append(a0 + (a1 - a0) * k / n)
    angle_list.append(_breaks[-1])
    obj = _arc_solid(
        d6_ang0, d6_ang1, _h_full, BOTTOM, CAP_W * 0.5, zc, r_out,
        name="review_shell", angles=angle_list,
    )
    details_col.objects.link(obj)
    obj.data.materials.append(mat("m_review_shell", body_rgb, rough=0.55))

    # Bevel ONLY: (1) ±X side rails along the arc, (2) vertical corners,
    # (3) across-strap lips exactly at tier breakpoints. Never weight every
    # dense roof across-edge — that rippled the planar/arc roofs.
    _tier_breaks = (A_CAP, A_R1_1, A_LAND_1, A_R2_1)
    _half_w = CAP_W * 0.5
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        import bmesh as _bm
        bm = _bm.new()
        bm.from_mesh(obj.data)
        bw = bm.edges.layers.float.get("bevel_weight_edge")
        if bw is None:
            bw = bm.edges.layers.float.new("bevel_weight_edge")
        bm.edges.ensure_lookup_table()
        n_rail = n_tier = n_corner = 0
        for e in bm.edges:
            v0, v1 = e.verts
            dx = abs(v0.co.x - v1.co.x)
            dyz = math.hypot(v0.co.y - v1.co.y, v0.co.z - v1.co.z)
            h0 = math.hypot(v0.co.y, v0.co.z - zc) - r_out
            h1 = math.hypot(v1.co.y, v1.co.z - zc) - r_out
            h_mid = 0.5 * (h0 + h1)
            a0 = math.degrees(math.atan2(v0.co.y, v0.co.z - zc))
            a1 = math.degrees(math.atan2(v1.co.y, v1.co.z - zc))
            a_mid = 0.5 * (a0 + a1)
            near_break = any(abs(abs(a_mid) - b) < 0.40 for b in _tier_breaks)
            on_side = (
                abs(abs(v0.co.x) - _half_w) < 0.6
                and abs(abs(v1.co.x) - _half_w) < 0.6
            )
            # Along-arc rail at ±X roof/wall lip (dense stations → short edges)
            rail = (
                on_side and dx < 0.8 and dyz > 0.25
                and h_mid > (POD_H - 2.5)
                and abs(h0 - h1) < 3.5
            )
            # Across-strap tier lip only at breakpoints (visible 1.8 mm chamfer)
            tier_lip = (
                dx > 1.0 and dyz < 2.5 and near_break
                and h_mid > (POD_H - 2.5)
            )
            corner = (
                dx < 0.5 and abs(h0 - h1) > 1.0 and min(h0, h1) > 10.0
            )
            if rail or tier_lip or corner:
                e[bw] = 1.0
                if rail:
                    n_rail += 1
                elif tier_lip:
                    n_tier += 1
                else:
                    n_corner += 1
            else:
                e[bw] = 0.0
        bm.to_mesh(obj.data)
        bm.free()
        print(f"  bevel weights: rail={n_rail} tier_lip={n_tier} corner={n_corner}")
        bev = obj.modifiers.new("chamfer_1v8", "BEVEL")
        bev.width = 1.8
        bev.segments = 2
        bev.limit_method = "WEIGHT"
        try:
            bev.affect = "EDGES"
        except Exception:
            pass
        try:
            bev.profile = 0.5  # straight chamfer look
        except Exception:
            pass
        bpy.ops.object.modifier_apply(modifier=bev.name)
    except Exception as exc:
        print(f"  chamfer bevel warn: {exc}")
    # Flat roofs: clear custom normals; smooth only with 30° angle limit
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass
    try:
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(30.0)
    except Exception:
        pass
    bpy.ops.object.shade_smooth()

    def _bool_cut(cutter, tag, solver="EXACT"):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        n0 = len(obj.data.vertices)
        if n0 < 8:
            print(f"  bool {tag}: SKIP — shell already empty ({n0} verts)")
            try:
                bpy.data.objects.remove(cutter, do_unlink=True)
            except Exception:
                pass
            return False
        # Snapshot mesh so a catastrophic boolean can be rolled back
        backup = obj.data.copy()
        cutter.hide_render = True
        mod = obj.modifiers.new(tag, "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        try:
            mod.solver = solver
        except Exception:
            pass
        applied = False
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
            applied = True
        except Exception as exc:
            print(f"  bool {tag} {solver} warn: {exc}")
            if tag in [m.name for m in obj.modifiers]:
                try:
                    obj.modifiers.remove(obj.modifiers[tag])
                except Exception:
                    pass
            if solver == "EXACT":
                bpy.data.meshes.remove(backup)
                return _bool_cut(cutter, tag, solver="FAST")
        n1 = len(obj.data.vertices)
        # Rollback if the cut destroyed the shell
        if n1 < max(32, int(0.5 * n0)):
            print(
                f"  bool {tag}: CATASTROPHIC {n0}→{n1} ({solver}) — restore + "
                + ("retry FAST" if solver == "EXACT" else "skip")
            )
            obj.data = backup
            if solver == "EXACT":
                return _bool_cut(cutter, tag, solver="FAST")
            try:
                bpy.data.objects.remove(cutter, do_unlink=True)
            except Exception:
                pass
            return False
        try:
            bpy.data.meshes.remove(backup)
        except Exception:
            pass
        try:
            bpy.data.objects.remove(cutter, do_unlink=True)
        except Exception:
            pass
        print(f"  bool {tag}: verts {n0}→{n1} solver={solver} applied={applied}")
        return n1 != n0

    # NO solar cut — closed charcoal roof (navy strips inlaid flush)

    # Flat pod roof patch 31–40°; ≥3 mm from ramp (A_R2_1) and from orange.
    # If orange at 29° is too close to the ramp, move the DOT — not the digits.
    DOT_A = 29.0
    _clear_deg = 3.0 * 180.0 / (math.pi * r_out)
    if DOT_A < (A_R2_1 + _clear_deg):
        DOT_A = round(A_R2_1 + _clear_deg + 0.15, 2)
        print(f"  moved DOT_A → {DOT_A:.2f}° (≥3 mm clear of ramp {A_R2_1:.2f}°)")
    ID_001_A = 35.5  # centre of 31–40° flat pod patch
    # Keep ≥3 mm from DOT and from ramp
    if ID_001_A < (DOT_A + _clear_deg + 1.5):
        ID_001_A = round(DOT_A + _clear_deg + 1.5, 2)
    if ID_001_A > 39.5:
        ID_001_A = 39.5
    id_001_info = {}
    for side, sy in (("L", -1.0), ("R", 1.0)):
        a_id = sy * ID_001_A
        a = math.radians(a_id)
        h_p = POD_H  # flat pod roof plane at 25.0 mm
        cy = r_out * math.sin(a)
        cz = zc + r_out * math.cos(a)
        ny, nz = math.sin(a), math.cos(a)

        # Mesh roof sample on flat pod patch (filter near h=25)
        _roof_samples = []
        for v in obj.data.vertices:
            aa = math.degrees(math.atan2(v.co.y, v.co.z - zc))
            if abs(aa - a_id) > 2.5:
                continue
            if abs(v.co.x) > 6.0:
                continue
            hh = math.hypot(v.co.y, v.co.z - zc) - r_out
            if abs(hh - POD_H) < 1.5:
                _roof_samples.append(hh)
        mesh_roof = (
            sorted(_roof_samples)[int(0.9 * (len(_roof_samples) - 1))]
            if len(_roof_samples) >= 8 else h_p
        )
        # Cutter depth 1.5 → centre at roof+0.15 → pit floor at roof-0.6
        cut_h = mesh_roof + 0.15
        cutters = _make_001_cutters(size=9.5, depth=1.5)
        for ci, cutter in enumerate(cutters):
            cutter.name = f"cutter_001_{side}_{ci}"
            # WORLD +X baseline — same L→R on BOTH lids (no mirror / no "100")
            along_x = float(cutter.location.x)
            cutter.location = (0.0, 0.0, 0.0)
            # Tip depth into lid normal; letter-up → strap tangent (upright in top)
            cutter.rotation_euler = (-a, 0.0, 0.0)
            bpy.ops.object.select_all(action="DESELECT")
            cutter.select_set(True)
            bpy.context.view_layer.objects.active = cutter
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            lid = Vector((0.0, cy + ny * cut_h, cz + nz * cut_h))
            cutter.location = lid + Vector((along_x, 0.0, 0.0))
            for cc in list(cutter.users_collection):
                cc.objects.unlink(cutter)
            details_col.objects.link(cutter)
            _bool_cut(cutter, f"id_001_{side}_{ci}")
        ok, measured = _verify_001_pit(obj, a_id, r_out, zc, mesh_roof, depth=0.5)
        clear_mm = abs(ID_001_A - DOT_A) * math.pi / 180.0 * r_out
        clear_ramp_mm = abs(ID_001_A - A_R2_1) * math.pi / 180.0 * r_out
        id_001_info[side] = {
            "angle_deg": a_id,
            "dot_angle_deg": sy * DOT_A,
            "clearance_to_dot_mm": round(clear_mm, 1),
            "clearance_to_ramp_mm": round(clear_ramp_mm, 1),
            "modifier_applied": (
                f"id_001_{side}_0/1/2 (3× BOOLEAN DIFFERENCE, WORLD +X baseline)"
            ),
            "object": "review_shell",
            "verified_in_mesh": ok,
            "measured_depth_mm": measured,
            "target_depth_mm": 0.6,
            "height_mm": 9.5,
            "material": "same charcoal as lid",
            "reads_in": "TOP view L→R increasing world X on BOTH lids (no mirror)",
            "glyph_gap_mm": 1.2,
            "glyphs": "polygon 0=rounded-rect ring, 1=bar+flag; cut AFTER bevel",
        }
        print(
            f"  001 {side}: verified={ok} depth≈{measured} mm at a={a_id:.1f}° "
            f"(dot at {sy * DOT_A:.1f}°, clear_dot≈{clear_mm:.1f} mm, "
            f"clear_ramp≈{clear_ramp_mm:.1f} mm, WORLD +X)"
        )

    # Post-boolean cleanup — kill stray tabs / non-manifold from cuts
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(threshold=0.02)
        bpy.ops.mesh.dissolve_degenerate(threshold=0.02)
        bpy.ops.mesh.delete_loose()
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception as exc:
        print(f"  mesh cleanup warn: {exc}")
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            pass
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass
    try:
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(30.0)
    except Exception:
        pass
    bpy.ops.object.shade_smooth()
    # Explicit flat shade on near-planar roof faces (dihedral-stable lids)
    try:
        import bmesh as _bm2
        bm = _bm2.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        flat_n = 0
        for f in bm.faces:
            # Roof face: centroid high above strap, normal ~ radial
            c = f.calc_center_median()
            h = math.hypot(c.y, c.z - zc) - r_out
            if h < (POD_H - 1.5):
                continue
            n = f.normal
            radial = Vector((0.0, c.y, c.z - zc))
            if radial.length < 1e-6:
                continue
            radial.normalize()
            if n.dot(radial) > 0.92:
                f.smooth = False
                flat_n += 1
        bm.to_mesh(obj.data)
        bm.free()
        print(f"  flat-shaded roof faces: {flat_n}")
    except Exception as exc:
        print(f"  flat roof shade warn: {exc}")

    _sil = []
    for a_s in [-40, -36, -30, -27, -24, -21, -18, -15, -10, 0,
                10, 15, 18, 21, 24, 27, 30, 36, 40]:
        h_s, drv = roof_at_d6_angle(float(a_s))
        _sil.append({"a": a_s, "h": round(h_s, 2), "drv": drv.split("(")[0].strip()})
    print("  silhouette polyline:", _sil)

    hide_names = []
    for o in list(bpy.data.objects):
        n = o.name
        if (
            n.startswith("fairing_")
            or n.startswith("review_roof_sleeve")
            or n in (
                "cap_base", "cap_lid", "pod_L_base", "pod_R_base",
                "pod_L_lid", "pod_R_lid", "saddle",
            )
            or n.startswith("screw_cap_orange")
            or n == "cap_panel_p124"  # closed roof — hide panel glass
        ):
            o.hide_render = True
            o.hide_viewport = True
            hide_names.append(n)

    compare = []
    for st in stations:
        a_d4 = float(st["angle_deg"])
        a_d6 = d4_angle_to_d6(a_d4)
        h_d6, driver = roof_at_d6_angle(a_d6)
        aa = abs(a_d6)
        body_lim = abs(d6_body0) if a_d6 < 0 else d6_body1
        hw = CAP_W if aa <= A_CAP else (MID_W if aa < A_R2_1 else POD_W)
        if aa > body_lim:
            t_end = min(1.0, max(0.0, (aa - body_lim) / max(drop_tail + 0.8, 1e-9)))
            s = t_end * t_end * (3.0 - 2.0 * t_end)
            h_d6 = h_d6 * (1.0 - s * s) + 1.2 * s * s
            hw = hw * (1.0 - s) + 16.0 * s
            driver = "end_drop"
        compare.append({
            "angle_d4_deg": round(a_d4, 2),
            "angle_d6_deg": round(a_d6, 2),
            "d4_width_mm": round(float(st["width_mm"]), 2),
            "d6_lid_width_mm": round(hw, 2),
            "d6_skirt_width_mm": round(hw + 4.0, 2),
            "d4_roof_mm": round(float(st["top_above_strap_outer_mm"]), 2),
            "d6_roof_mm": round(h_d6, 2),
            "d4_bottom_rel_mm": round(float(st["bottom_rel_strap_outer_mm"]), 2),
            "d6_bottom_rel_mm": BOTTOM,
            "roof_delta_mm": round(h_d6 - float(st["top_above_strap_outer_mm"]), 2),
            "height_driver": driver,
        })

    outer_arc_mm = (d6_ang1 - d6_ang0) * math.pi / 180.0 * r_out
    meta = {
        "round": "D7r16",
        "profile_path": profile_path,
        "d4_r_outer": d4_r_out,
        "d6_r_outer": r_out,
        "d6_angle_span_deg": [round(d6_ang0, 2), round(d6_ang1, 2)],
        "d6_outer_arc_mm": round(outer_arc_mm, 1),
        "d4_angle_span_deg": [round(d4_ang0, 2), round(d4_ang1, 2)],
        "d4_outer_arc_mm": d4_arc_mm,
        "arc_driver": ARC_DRIVER,
        "cap_roof_need_mm": round(CAP_H, 2),
        "cap_height_driver": CAP_H_DRIVER,
        "pod_roof_mm": POD_H,
        "pod_height_driver": POD_H_DRIVER,
        "mid_landing_mm": round(MID_H, 2),
        "stage_drop_mm": round(STAGE, 2),
        "cap_block": {
            "half_angle_deg": round(A_CAP, 2),
            "arc_mm": round(cap_block_arc_mm, 1),
            "set_by": f"panel land {PANEL_LAND_L} mm + {CAP_WALL_EXTRA} mm wall",
            "d4_half_angle_deg": d4_cap_half_deg,
            "d4_arc_mm": round(d4_cap_block_arc_mm, 1),
        },
        "step_angles_deg": {
            "cap_end": round(A_R1_0, 2),
            "ramp1_end": round(A_R1_1, 2),
            "landing_end": round(A_LAND_1, 2),
            "ramp2_end": round(A_R2_1, 2),
        },
        "silhouette_polyline": _sil,
        "d4_cap_max_mm": D4_CAP_MAX,
        "bottom_rel_mm": BOTTOM,
        "chamfer_mm": 1.8,
        "build": (
            "extruded arc slabs + 45° ramps; Bevel 1.8 mm on rails+tier lips only; "
            "polygon 001 WORLD +X after bevel; flat roofs auto_smooth 30°; NO subdiv"
        ),
        "id_001": id_001_info,
        "dot_angle_deg": DOT_A,
        "id_001_angle_deg": ID_001_A,
        "cap_roof_note": (
            f"D7r16 extruded tiers. Cap {CAP_H:.1f} / mid {MID_H:.1f} "
            f"/ pod {POD_H:.0f}; chamfer 1.8 mm on every tier lip + rails; "
            f"closed charcoal roof; polygon 001 WORLD +X at ±{ID_001_A}°; "
            f"dots at ±{DOT_A}°; navy strips inlaid ≤0.2 mm below roof."
        ),
        "n_stations_loft": "n/a (extruded solids)",
        "hidden": hide_names,
        "stations_vs_d4": compare,
        "end_shoulder_d4": end_sh,
        "solar_cut": False,
    }
    print(
        f"  review_shell r16: angles {d6_ang0:.1f}→{d6_ang1:.1f} "
        f"cap={CAP_H:.1f} mid={MID_H:.1f} pod={POD_H:.0f} "
        f"tier-chamfer 1.8 + polygon 001 WORLD +X (no subdiv, no solar cut)"
    )
    print(f"  hidden under shell: {hide_names}")
    return obj, meta


def _add_solar_review_detail(
    details_col, panel_c, panel_sz, roof_z=None,
    shell_obj=None, zc=None, r_out=None, cap_h=None,
):
    """D7r16: navy strips INLAID into the ARC charcoal roof (no panel glass).

    Strips follow the cylindrical roof (not a flat world-Z plane — that made
    blue tabs float above the arc). Pocket is boolean-cut from the shell;
    strip top sits 0.0–0.2 mm below the local roof.
    """
    px, py = float(panel_sz.x), float(panel_sz.y)
    strip_depth = 2.2
    inset = 0.1
    strip_y = max(6.0, min(9.0, py / 8.0))
    # Keep inside lid rails (CAP_W=76 → ±38); leave ≥3 mm margin each side
    strip_x = min(px - 2.0, 68.0)
    zc = -233.85 if zc is None else float(zc)
    r_out = (227.0 + STRAP_T / 2.0) if r_out is None else float(r_out)
    cap_h = 48.25 if cap_h is None else float(cap_h)

    def _bool_pocket(target, cutter, tag):
        bpy.ops.object.select_all(action="DESELECT")
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        mod = target.modifiers.new(tag, "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = cutter
        try:
            mod.solver = "EXACT"
        except Exception:
            pass
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as exc:
            print(f"  navy pocket {tag} warn: {exc}")
            if tag in [m.name for m in target.modifiers]:
                try:
                    target.modifiers.remove(target.modifiers[tag])
                except Exception:
                    pass
        try:
            bpy.data.objects.remove(cutter, do_unlink=True)
        except Exception:
            pass

    for sy, tag in ((-1.0, "N"), (1.0, "S")):
        # Target Y on the panel; map to arc angle at strap outer
        y_target = float(panel_c.y) + sy * (py * 0.5 - strip_y * 0.5 - 0.5)
        a = math.asin(max(-0.999, min(0.999, y_target / r_out)))
        ny, nz = math.sin(a), math.cos(a)
        # Local roof height (cap flat)
        h_roof = cap_h
        # Pocket cutter: slightly taller/wider, centred so it opens the roof
        cut_depth = strip_depth + 0.6
        cut_h_mid = h_roof - inset - cut_depth * 0.5 + 0.15
        cut_loc = Vector((
            0.0,
            (r_out + cut_h_mid) * ny,
            zc + (r_out + cut_h_mid) * nz,
        ))
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=cut_loc)
        cutter = bpy.context.active_object
        cutter.name = f"navy_pocket_cutter_{tag}"
        cutter.scale = (strip_x + 0.6, strip_y + 0.4, cut_depth)
        cutter.rotation_euler = (-a, 0.0, 0.0)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        cutter.location = cut_loc
        if shell_obj is not None:
            _bool_pocket(shell_obj, cutter, f"navy_pocket_{tag}")
        else:
            bpy.data.objects.remove(cutter, do_unlink=True)

        # Navy strip solid — top at roof − inset
        h_mid = h_roof - inset - strip_depth * 0.5
        loc = (
            0.0,
            (r_out + h_mid) * ny,
            zc + (r_out + h_mid) * nz,
        )
        box = _add_box(
            details_col, f"solar_navy_strip_{tag}",
            (strip_x, strip_y, strip_depth),
            loc,
            NAVY_SOLAR, rough=0.85,
            rot=(-a, 0.0, 0.0),
        )
        bpy.ops.object.select_all(action="DESELECT")
        box.select_set(True)
        bpy.context.view_layer.objects.active = box
        bpy.ops.object.shade_flat()
        print(
            f"  navy strip {tag}: a={math.degrees(a):.2f}° "
            f"top at roof−{inset:.1f} mm (arc-inlaid)"
        )

    return {
        "rib_y_mm": 0.0,
        "strip_y_mm": round(strip_y, 2),
        "strip_x_mm": round(strip_x, 2),
        "placement": "arc-inlaid in closed charcoal roof at ±Y ends; top ≤0.2 mm below roof",
        "bezel": "none — closed roof, no panel cut, no centre rib, no lit outline",
        "panel_pocket_mm": [66.6, 113.6],
        "shade_fraction_rib": 0.0,
        "rib_w_mm": 0.0,
        "roof_z": round(float(roof_z) if roof_z is not None else (zc + r_out + cap_h), 2),
        "strip_top_below_roof_mm": inset,
        "shade_note": (
            f"D7r16 closed roof: navy strips {strip_y:.1f} mm at each Y-end "
            f"arc-inlaid {inset:.1f} mm below roof; charcoal centre is the shell."
        ),
    }


def _meshes_touching(a, b, tol=0.5):
    """True if world AABBs overlap or come within tol mm (proxy for contact)."""
    ab = _world_bbox(a)
    bb = _world_bbox(b)

    def gap1(a0, a1, b0, b1):
        if a1 < b0:
            return b0 - a1
        if b1 < a0:
            return a0 - b1
        return 0.0

    gx = gap1(ab[0], ab[1], bb[0], bb[1])
    gy = gap1(ab[2], ab[3], bb[2], bb[3])
    gz = gap1(ab[4], ab[5], bb[4], bb[5])
    # Separating-axis style: if any axis gap > tol and others don't compensate —
    # floating if the Euclidean AABB gap > tol
    if gx <= tol and gy <= tol and gz <= tol:
        return True
    return (gx * gx + gy * gy + gz * gz) ** 0.5 <= tol


def _geometry_hygiene_report(path):
    """Flag non-mesh / floating / thin (<2 mm) detail not part of a named body.

    Named bodies (print STLs + strap) may be thin in one AABB axis after tilt;
    review details under 2 mm thick are flagged.
    """
    allow_empty = {"NOTE_d4_ghost", "pod_L_anchor", "pod_R_anchor"}
    named_body_prefixes = (
        "cap_", "pod_L_", "pod_R_", "cw_", "fairing_", "saddle",
        "clamp_bar_", "strap_loop", "review_shell",
    )
    thin = []
    floating = []
    non_mesh = []
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render]
    for o in bpy.data.objects:
        if o.type != "MESH":
            if o.name not in allow_empty:
                non_mesh.append({"name": o.name, "type": o.type})
            continue
        if o.hide_render:
            continue
        dims = [float(d) for d in o.dimensions]
        is_named = any(o.name.startswith(p) or o.name == p.rstrip("_")
                       for p in named_body_prefixes)
        # D7r8: flag review/detail solids with any dim < 2 mm
        if (not is_named) and any(d < 2.0 - 1e-6 for d in dims):
            thin.append({"name": o.name, "dims": [round(d, 3) for d in dims]})
        # Also flag ANY visible object (incl. named) with thickness < 2 if it
        # looks like a stray plate under a skirt (world Z extent < 2)
        bb = _world_bbox(o)
        z_th = bb[5] - bb[4]
        if (not is_named) and z_th < 2.0 - 1e-6:
            entry = {"name": o.name, "dims": [round(d, 3) for d in dims], "z_th": round(z_th, 3)}
            if entry not in thin and not any(t["name"] == o.name for t in thin):
                thin.append(entry)
    for o in meshes:
        others = [p for p in meshes if p.name != o.name]
        if not others:
            continue
        if not any(_meshes_touching(o, p, tol=0.8) for p in others):
            floating.append({"name": o.name, "dims": [round(float(d), 3) for d in o.dimensions]})
    report = {
        "thin_lt_2mm": thin,
        "thin_lt_1mm": thin,  # back-compat key for assembly_check
        "floating": floating,
        "non_mesh": non_mesh,
        "ok": not thin and not non_mesh and not floating,
        "n_mesh": len(meshes),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(report, open(path, "w"), indent=1)
    print("geometry hygiene:", "PASS" if report["ok"] else "FAIL", report)
    return report


# ---- collections ----------------------------------------------------------
d6 = col("D6_assembly")
ghost = col("D4_contoured_v3_ghost")
details = col("D7_review_details")
body_mat = mat("body_asa", BODY, rough=0.6)
orange_mat = mat("accent_orange", ORANGE, rough=0.45)

# World STLs — body colour only (clamps + fairings + saddle); NO orange endcaps
for f in sorted(glob.glob(os.path.join(WORLD, "*.stl"))):
    o = imp_stl(f, d6)
    o.data.materials.clear()
    o.data.materials.append(body_mat)
    # D7r10: hide all clamp bars + CW in review — visible set is shell + lids
    # + accents + strap/buckle/keeper. Print STLs / assembly_check unchanged.
    if o.name.startswith("clamp_bar_") or o.name in ("cw_tub", "cw_lid"):
        o.hide_render = True
        o.hide_viewport = True

# D4 ghost STLs are imported only for optional wbbox notes, then DELETED —
# WIRE display leftovers were reading as thin frames around lids/cap ends.
ghost_note = (
    f"palette={_palette}; D4 ghost deleted from review blend (D7r6); "
    f"body={tuple(round(c, 3) for c in BODY)}"
    + (f"; d4_mat={_D4_MAT_SRC}" if _D4_MAT_SRC else "; d4_mat=fallback#3A3C3E")
)
for f in sorted(glob.glob(os.path.join(D4, "*.stl"))):
    if os.path.basename(f).startswith("._"):
        continue
    o = imp_stl(f, ghost)
    o.name = "D4_" + o.name
_delete_ghost_wires(ghost)

for n in ("pod_L", "pod_R"):
    e = bpy.data.objects.new(n + "_anchor", None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 15
    s = -1 if n == "pod_L" else 1
    e.location = (0, s * 126.0, -21.9)
    e.rotation_euler = (math.radians(-s * 29.1418), 0, 0)
    d6.objects.link(e)

# ---- review-only details --------------------------------------------------
# D7r16: closed charcoal roof — no panel glass. Navy strips arc-inlaid after shell.
panel_c = _wbbox_centre("cap_panel_p124") or Vector((0.0, 0.0, 32.5))
if panel_c.z < 25.0:
    panel_c = Vector((panel_c.x, panel_c.y, panel_c.z + 14.0))
panel_c = Vector((panel_c.x, panel_c.y, max(float(panel_c.z), 38.5)))
_cap_roof_z = -5.35 + 48.25

# D7r13: orange ONLY on the two lid dots — latch in body charcoal (no tab)
latch_path = _find_detail("latch.stl")
latch_c = _wbbox_centre("latch")
if latch_path and latch_c is not None:
    L = imp_stl(latch_path, details, name="latch")
    Lc = _bbox_centre(L)
    L.location = latch_c - Lc
    L.data.materials.clear()
    L.data.materials.append(body_mat)
    if min(L.dimensions) < 2.0 - 1e-6:
        bpy.data.objects.remove(L, do_unlink=True)
        _add_box(details, "latch", (6.0, 11.0, 2.2), latch_c, BODY)
elif latch_c is not None:
    _add_box(details, "latch", (6.0, 11.0, 2.2), latch_c, BODY)

# Tab dropped — buckle/keeper only
_add_strap_loop(details)
_add_buckle_keeper(details)
_purge_curves_and_wires()

_shell_obj, _shell_meta = _add_d4_loft_shell(details, BODY)
# Navy strips AFTER shell so pockets cut into the finished roof
solar_meta = _add_solar_review_detail(
    details, panel_c, Vector((66.6, 113.6, 2.0)),
    roof_z=_cap_roof_z,
    shell_obj=_shell_obj,
    zc=-233.85,
    r_out=227.0 + STRAP_T / 2.0,
    cap_h=float(_shell_meta.get("cap_roof_need_mm", 48.25)),
)
# Re-shade shell after pocket cuts
bpy.ops.object.select_all(action="DESELECT")
_shell_obj.select_set(True)
bpy.context.view_layer.objects.active = _shell_obj
try:
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
except Exception:
    pass
try:
    _shell_obj.data.use_auto_smooth = True
    _shell_obj.data.auto_smooth_angle = math.radians(30.0)
except Exception:
    pass
bpy.ops.object.shade_smooth()

_shell_report_path = os.path.join(OUT, "d7r16_stations_vs_d4.json")
json.dump(_shell_meta, open(_shell_report_path, "w"), indent=2)
os.makedirs(os.path.join(_HERE, "review"), exist_ok=True)
shutil.copy2(
    _shell_report_path,
    os.path.join(_HERE, "review", "d7r16_stations_vs_d4.json"),
)

# Ø5 mm flat orange dots — 0.3 mm proud on the lid, NO recess / no dark rim
_zc, _r_out = -233.85, 227.0 + STRAP_T / 2.0
_dot_a = float(_shell_meta.get("dot_angle_deg", 29.0))
for side, sy in (("L", -1.0), ("R", 1.0)):
    a = math.radians(sy * _dot_a)
    h_pod = float(_shell_meta.get("pod_roof_mm", 25.0))
    cy = _r_out * math.sin(a)
    cz = _zc + _r_out * math.cos(a)
    ny, nz = math.sin(a), math.cos(a)
    # Thin flat disc, 0.3 mm proud — no recess, minimal side-wall rim
    proud = 0.3
    depth = 0.35
    h_c = h_pod + proud - depth * 0.5  # top at h_pod+0.3
    loc = (0.0, cy + ny * h_c, cz + nz * h_c)
    dot = _add_cyl(
        details,
        f"pod_{side}_dot_orange",
        radius=2.5,   # Ø5 mm
        depth=depth,
        loc=loc,
        rgb=ORANGE,
        rot=(-a, 0.0, 0.0),
        rough=0.35,
    )
    bpy.ops.object.select_all(action="DESELECT")
    dot.select_set(True)
    bpy.context.view_layer.objects.active = dot
    bpy.ops.object.shade_flat()

bpy.ops.object.select_all(action="DESELECT")
_shell_obj.select_set(True)
bpy.context.view_layer.objects.active = _shell_obj
try:
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
except Exception:
    pass
try:
    _shell_obj.data.use_auto_smooth = True
    _shell_obj.data.auto_smooth_angle = math.radians(30.0)
except Exception:
    pass
bpy.ops.object.shade_smooth()

note = bpy.data.objects.new("NOTE_d4_ghost", None)
note.empty_display_type = "PLAIN_AXES"
note.empty_display_size = 1
note["ghost_note"] = ghost_note
note["palette"] = _palette
note["solar_shade"] = solar_meta.get("shade_note", "")
note["solar_rib_w_mm"] = float(solar_meta.get("rib_w_mm", 0))
note["review_shell"] = "d4_extruded_r16"
note["cap_roof_note"] = _shell_meta.get("cap_roof_note", "")
note["cap_height_driver"] = _shell_meta.get("cap_height_driver", "")
note["id_001"] = (
    "deboss 0.6mm charcoal; polygon glyphs; WORLD +X L→R BOTH lids; "
    "flat pod roof 31–40°; clear of orange"
)
details.objects.link(note)

hygiene_path = os.path.join(OUT, "geometry_hygiene.json")
hygiene = _geometry_hygiene_report(hygiene_path)
# Also copy into review/ for the assembly_check reader
review_hygiene = os.path.join(_HERE, "review", "geometry_hygiene.json")
shutil.copy2(hygiene_path, review_hygiene)
if not hygiene["ok"]:
    raise SystemExit(f"geometry hygiene FAIL: {hygiene}")

blend_path = os.path.join(OUT, "d6_assembly.blend")
review_blend = os.path.join(_HERE, "review", "d6_assembly.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)

# ---- renders --------------------------------------------------------------
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_xray = False
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.render.film_transparent = False
w = bpy.data.worlds.new("w")
sc.world = w
w.color = WORLD_BG

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

suffix = "" if _palette == "charcoal" else f"_{_palette}"
for name, d in {
    "iso": (1, -1, 0.8),
    # Hero: low-angle underside like D4 compare shots
    "hero": (1.0, -1.1, 0.35),
    "front": (0, -1, 0.0001),
    "side": (1, 0, 0.0001),
    "top": (0.0001, 0, 1),
}.items():
    d = Vector(d).normalized()
    cam.location = ctr + d * ext * 2
    if name == "top":
        # Standard top-down: +X = LEFT→RIGHT so WORLD-X 001 reads 0,0,1 L→R
        # on both lids. Strap (Y) runs vertical on screen.
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    else:
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, f"d6_assembly_{name}{suffix}.png")
    bpy.ops.render.render(write_still=True)

render_dir = os.path.join(_HERE, "renders")
os.makedirs(render_dir, exist_ok=True)
for name in ("iso", "hero", "front", "side", "top"):
    src = os.path.join(OUT, f"d6_assembly_{name}{suffix}.png")
    if os.path.exists(src):
        # Charcoal = canonical committed names; light gets _light suffix
        dst_name = f"d6_assembly_{name}.png" if not suffix else f"d6_assembly_{name}{suffix}.png"
        shutil.copy2(src, os.path.join(render_dir, dst_name))

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
    sc.render.filepath = os.path.join(OUT, f"d6_assembly_joint{suffix}.png")
    bpy.ops.render.render(write_still=True)
    dst = f"d6_assembly_joint.png" if not suffix else f"d6_assembly_joint{suffix}.png"
    shutil.copy2(sc.render.filepath, os.path.join(render_dir, dst))

# ---- 001 top-down orthographic lid crops (charcoal only) ------------------
if _palette == "charcoal":
    from mathutils import Matrix as _Mtx
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    _id_a = float(_shell_meta.get("id_001_angle_deg", 35.5))
    _dot_a_cu = float(_shell_meta.get("dot_angle_deg", 29.0))
    _h_pod = float(_shell_meta.get("pod_roof_mm", 25.0))
    for side, sy in (("L", -1.0), ("R", 1.0)):
        # True top-down on the 001 patch: look along −radial, +X = L→R.
        a_id = math.radians(sy * _id_a)
        cy = _r_out * math.sin(a_id)
        cz = _zc + _r_out * math.cos(a_id)
        ny, nz = math.sin(a_id), math.cos(a_id)
        lid = Vector((0.0, cy + ny * _h_pod, cz + nz * _h_pod))
        out = Vector((0.0, ny, nz)).normalized()
        right = Vector((1.0, 0.0, 0.0))
        up = out.cross(right).normalized()  # along-strap for upright glyphs
        # Re-orthogonalise right in case of drift
        right = up.cross(out).normalized()
        # Columns = local X,Y,Z; camera looks down −Z → toward −out = into lid
        basis = _Mtx((
            (right.x, up.x, out.x),
            (right.y, up.y, out.y),
            (right.z, up.z, out.z),
        ))
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = 48.0
        cam.location = lid + out * 100.0
        cam.rotation_euler = basis.to_euler()
        for out_name in (
            f"d6_001_closeup_{side}{suffix}.png",
            f"lid001_{side}{suffix}.png",
        ):
            sc.render.filepath = os.path.join(OUT, out_name)
            bpy.ops.render.render(write_still=True)
            shutil.copy2(sc.render.filepath, os.path.join(render_dir, out_name))
            shutil.copy2(sc.render.filepath, os.path.join(_HERE, "review", out_name))
            art = "/opt/cursor/artifacts"
            if os.path.isdir(art):
                shutil.copy2(sc.render.filepath, os.path.join(art, out_name))
            print(f"  001 top-down {side}: {out_name}")

os.makedirs(os.path.dirname(review_blend), exist_ok=True)
if _palette == "charcoal":
    shutil.copy2(blend_path, review_blend)
else:
    shutil.copy2(blend_path, os.path.join(_HERE, "review", f"d6_assembly_{_palette}.blend"))

# Fail the build if 001 did not land in the mesh
_id = _shell_meta.get("id_001") or {}
for side, info in _id.items():
    if isinstance(info, dict) and not info.get("verified_in_mesh", False):
        raise SystemExit(
            f"001 deboss NOT verified in review_shell mesh ({side}): {info}"
        )

print("OK", ghost_note)
print("palette", _palette)
print("blend", blend_path)
print("renders", OUT)
print("001", json.dumps(_id, indent=2))
