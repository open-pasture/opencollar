"""Build review/d6_assembly.blend + assembly renders from world STLs.

D7r4 review pack (op-brand):
  - Palette DEFAULT = charcoal (D4_contoured_v3 body ~#3A3C3E, roughness 0.6).
    Secondary = light (#C9CBCC). Switch: --palette charcoal|light  (or env
    D6_PALETTE). Orange accents unchanged (#FF6A2B).
  - Strap: slim flat band (≈44.45 × 3.0) on a YZ ring through the saddle
    channel and under the CW clamp; D4-style buckle + keeper.
  - Orange only: one small dot per pod lid, one small collar tab, tiny
    screw heads + latch. No orange saddles / clamp endcaps.

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
    """D4 buckle: open rect frame flat ON the strap + solid keeper loop.

    Frame ≈24×30×3 mm, central opening, tongue across (≥2 mm solid).
    Keeper = torus with ≥2 mm tube — never a thin wire/curve.
    """
    b_pos, b_eul = _strap_point(-48.0)
    k_pos, k_eul = _strap_point(-38.0)

    major_r = 227.0
    zc = -233.85

    def _on_surface(pos, proud=1.6):
        v = Vector((pos.x, pos.y, pos.z - zc))
        if v.length < 1e-6:
            return pos
        return Vector((0.0, 0.0, zc)) + v.normalized() * (major_r + proud)

    b_pos = _on_surface(b_pos, proud=1.7)
    k_pos = _on_surface(k_pos, proud=2.2)

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

    # Solid tongue (≥2 mm) — not a diagonal wire
    _add_box(
        collection, "buckle_tongue", (20.0, 3.0, 2.5), b_pos, HARDWARE,
        rot=b_eul, rough=0.55,
    )

    # Solid keeper loop — minor radius ≥2 mm so it never reads as a wire
    bpy.ops.mesh.primitive_torus_add(
        major_radius=STRAP_W / 2.0 + 2.5,
        minor_radius=2.2,
        major_segments=40,
        minor_segments=12,
        location=k_pos,
    )
    keeper = bpy.context.active_object
    keeper.name = "keeper"
    keeper.rotation_euler = (k_eul[0] + math.radians(90), 0.0, math.radians(90))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    for cc in list(keeper.users_collection):
        cc.objects.unlink(keeper)
    collection.objects.link(keeper)
    keeper.data.materials.append(mat("m_keeper", HARDWARE, rough=0.55))


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


def _add_continuous_roof_skins(d6_col, details_col, body_rgb):
    """Review-only: one continuous band per side (cap nose + fairing + pod lid).

    Boolean-unions duplicates so the hero silhouette is a single surface; printable
    STLs stay separate. Original fairing_cap_pod_* are hidden.
    """
    for side in ("L", "R"):
        names = [f"fairing_cap_pod_{side}", f"pod_{side}_lid", "cap_lid"]
        srcs = [bpy.data.objects.get(n) for n in names]
        if any(s is None for s in srcs):
            print(f"  roof skin {side}: missing source, skip")
            continue
        copies = []
        for s in srcs:
            c = s.copy()
            c.data = s.data.copy()
            c.name = f"review_roof_{side}__{s.name}"
            details_col.objects.link(c)
            copies.append(c)
        base = copies[0]
        bpy.ops.object.select_all(action="DESELECT")
        for c in copies:
            c.select_set(True)
        bpy.context.view_layer.objects.active = base
        for other in copies[1:]:
            mod = base.modifiers.new(f"u_{other.name[-8:]}", "BOOLEAN")
            mod.operation = "UNION"
            mod.object = other
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except Exception as exc:
                print(f"  roof union warn {side}: {exc}")
        for other in copies[1:]:
            bpy.data.objects.remove(other, do_unlink=True)
        base.name = f"review_roof_band_{side}"
        base.data.materials.clear()
        base.data.materials.append(mat(f"m_roof_{side}", body_rgb, rough=0.6))
        # Hide the bridging fairing so only the continuous band shows the join
        fair = bpy.data.objects.get(f"fairing_cap_pod_{side}")
        if fair is not None:
            fair.hide_render = True
            fair.hide_viewport = True
        print(f"  roof skin {side}: OK")


def _geometry_hygiene_report(path):
    """List non-mesh / sub-1 mm objects (excluding known empties). Write JSON."""
    allow_empty = {"NOTE_d4_ghost", "pod_L_anchor", "pod_R_anchor"}
    thin = []
    non_mesh = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            if o.name not in allow_empty:
                non_mesh.append({"name": o.name, "type": o.type})
            continue
        dims = [float(d) for d in o.dimensions]
        if any(d < 1.0 - 1e-6 for d in dims):
            thin.append({"name": o.name, "dims": [round(d, 3) for d in dims]})
    report = {
        "thin_lt_1mm": thin,
        "non_mesh": non_mesh,
        "ok": not thin and not non_mesh,
        "n_mesh": sum(1 for o in bpy.data.objects if o.type == "MESH"),
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
# Solar panel — clean flat dark rectangle with a crisp edge (no mottling)
# Z raised with CAP_MATING_Z (skirt-aware lid)
panel_c = _wbbox_centre("cap_panel_p124") or Vector((0.0, 0.0, 32.5))
if panel_c.z < 25.0:
    panel_c = Vector((panel_c.x, panel_c.y, panel_c.z + 14.0))
sz = _wbbox_size("cap_panel_p124") or Vector((66.6, 113.6, 2.3))
_add_box(
    details, "cap_panel_p124",
    (sz.x, sz.y, max(float(sz.z), 2.0)),
    (panel_c.x, panel_c.y, panel_c.z),
    PANEL_GLASS, rough=0.12,
)

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

plug_c = _wbbox_centre("cap_plug_service_orange_p68p")
if plug_c is not None:
    # ≥2 mm thick solid — no thin plate artifact
    _add_cyl(details, "collar_orange_tab", radius=3.0, depth=2.2, loc=plug_c, rgb=ORANGE)

_add_strap_loop(details)
_add_buckle_keeper(details)
_purge_curves_and_wires()

# Cap corner screw accents ON the lid surface (≥2 mm) — skirt-aware Z
cap_z = 33.0 + 0.6
_POD_TILT = math.radians(29.1418)
for i, (x, y) in enumerate([(29.5, 68.0), (-29.5, 68.0), (29.5, -68.0), (-29.5, -68.0)]):
    _add_cyl(details, f"screw_cap_orange_{i}", radius=2.2, depth=2.0,
             loc=(x, y, cap_z), rgb=ORANGE)

# Orange dot ON each pod lid outer (not inside the cavity)
for side, sy in (("L", -1.0), ("R", 1.0)):
    _add_cyl(
        details,
        f"pod_{side}_dot_orange",
        radius=3.0,
        depth=2.0,
        loc=(0.0, sy * 110.0, 28.0),
        rgb=ORANGE,
        rot=(_POD_TILT * (-sy), 0.0, 0.0),
    )

# Review-only continuous cap↔fairing↔pod roof bands
_add_continuous_roof_skins(d6, details, BODY)

note = bpy.data.objects.new("NOTE_d4_ghost", None)
note.empty_display_type = "PLAIN_AXES"
note.empty_display_size = 1
note["ghost_note"] = ghost_note
note["palette"] = _palette
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
bpy.ops.wm.save_as_mainfile(filepath=blend_path)

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
    "front": (0, -1, 0.0001),
    "side": (1, 0, 0.0001),
    "top": (0.0001, 0, 1),
}.items():
    d = Vector(d).normalized()
    cam.location = ctr + d * ext * 2
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, f"d6_assembly_{name}{suffix}.png")
    bpy.ops.render.render(write_still=True)

render_dir = os.path.join(_HERE, "renders")
os.makedirs(render_dir, exist_ok=True)
for name in ("iso", "front", "side", "top"):
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

os.makedirs(os.path.dirname(review_blend), exist_ok=True)
if _palette == "charcoal":
    shutil.copy2(blend_path, review_blend)
else:
    shutil.copy2(blend_path, os.path.join(_HERE, "review", f"d6_assembly_{_palette}.blend"))

print("OK", ghost_note)
print("palette", _palette)
print("blend", blend_path)
print("renders", OUT)
