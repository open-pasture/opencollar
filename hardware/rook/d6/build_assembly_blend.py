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


def _add_roof_fairing_sleeves(details_col, body_rgb):
    """D7r8 review fairing: one continuous tapered band, shadow groove only.

    Same roof line across the joint (cap tip → pod roof). Print STLs keep the
    real ~4 mm gap; print fairings are hidden so the sleeve reads as the skin.
    Plan-rounded ends so L/R match (no squared block on R).
    """
    import bmesh

    for side, sy in (("L", -1.0), ("R", 1.0)):
        cap = bpy.data.objects.get("cap_lid")
        pod = bpy.data.objects.get(f"pod_{side}_lid")
        fair = bpy.data.objects.get(f"fairing_cap_pod_{side}")
        if cap is None or pod is None:
            print(f"  roof sleeve {side}: missing cap/pod, skip")
            continue
        cb = _world_bbox(cap)
        pb = _world_bbox(pod)
        y_cap = cb[2] if sy < 0 else cb[3]
        y_pod = pb[3] if sy < 0 else pb[2]
        # Deep overlap so cap+pod read as one band
        y_a = y_cap - sy * 8.0
        y_b = y_pod + sy * 12.0
        tip_zs = [
            (cap.matrix_world @ Vector(v.co)).z
            for v in cap.data.vertices
            if abs((cap.matrix_world @ Vector(v.co)).y - y_cap) < 5.0
            and abs((cap.matrix_world @ Vector(v.co)).x) < 30.0
        ]
        z_cap = max(tip_zs) if tip_zs else (cb[4] + 3.0)
        z_pod = pb[5] - 0.05
        if fair is not None:
            fair.hide_render = True
            fair.hide_viewport = True
        t = 2.4
        n_stat = 6
        bm = bmesh.new()
        rings = []
        for i in range(n_stat):
            u = i / (n_stat - 1)
            s = u * u * (3.0 - 2.0 * u)  # smoothstep
            y = y_a + (y_b - y_a) * u
            z_top = z_cap + (z_pod - z_cap) * s
            # Taper width toward pod end (nose blob adds the plan round)
            hw = 34.0 - 3.0 * s
            corners_xz = [
                (-hw, z_top),
                (hw, z_top),
                (hw, z_top - t),
                (-hw, z_top - t),
            ]
            rings.append([bm.verts.new((x, y, z)) for x, z in corners_xz])
        bm.verts.ensure_lookup_table()
        for i in range(n_stat - 1):
            a, b = rings[i], rings[i + 1]
            for j in range(4):
                j2 = (j + 1) % 4
                bm.faces.new([a[j], a[j2], b[j2], b[j]])
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))
        mesh = bpy.data.meshes.new(f"review_roof_sleeve_{side}_mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"review_roof_sleeve_{side}", mesh)
        details_col.objects.link(obj)
        obj.data.materials.append(mat(f"m_roof_sleeve_{side}", body_rgb, rough=0.6))
        # Thin shadow groove at the print-gap midline (not a lit step / flat plate)
        mid_y = 0.5 * (y_cap + y_pod)
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(0.0, mid_y, 0.5 * (z_cap + z_pod) + 0.5),
        )
        g = bpy.context.active_object
        g.name = f"_tmp_groove_{side}"
        g.scale = (70.0, 1.15, 1.1)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for cc in list(g.users_collection):
            cc.objects.unlink(g)
        details_col.objects.link(g)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new("groove", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = g
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as exc:
            print(f"  groove warn {side}: {exc}")
        bpy.data.objects.remove(g, do_unlink=True)
        # Rounded nose blob on the pod-facing end (matches L/R, kills square block)
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=1.0,
            location=(0.0, y_b, z_pod - t * 0.35),
            segments=24, ring_count=12,
        )
        nose = bpy.context.active_object
        nose.scale = (30.0, 6.0, t * 0.55)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        for cc in list(nose.users_collection):
            cc.objects.unlink(nose)
        details_col.objects.link(nose)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        umod = obj.modifiers.new("nose", "BOOLEAN")
        umod.operation = "UNION"
        umod.object = nose
        try:
            bpy.ops.object.modifier_apply(modifier=umod.name)
        except Exception as exc:
            print(f"  nose warn {side}: {exc}")
        bpy.data.objects.remove(nose, do_unlink=True)
        print(
            f"  roof sleeve {side}: Y {y_a:.1f}→{y_b:.1f} Z {z_cap:.1f}→{z_pod:.1f}"
        )


def _add_solar_review_detail(details_col, panel_c, panel_sz):
    """D7r8 review solar: D4-like thin navy edge strips + wide charcoal rib.

    Pocket 66.6×113.6 unchanged. Navy ONLY on the two edge strips. Matte.
    """
    px, py = float(panel_sz.x), float(panel_sz.y)
    bezel_w, bezel_l = px + 3.0, py + 3.0
    _add_box(
        details_col, "solar_bezel",
        (bezel_w, bezel_l, 2.2),
        (panel_c.x, panel_c.y, panel_c.z + 0.5),
        CHARCOAL_SOLAR, rough=0.75,
    )
    # D4 look: thin edge strips (~8 mm), wide charcoal centre rib
    strip_w = 8.0
    gap = 1.0  # charcoal margin between strip and rib
    rib_w = px - 2.0 * strip_w - 2.0 * gap  # ≈48.6 mm
    strip_l = py - 2.0
    for sx, tag in ((-1.0, "L"), (1.0, "R")):
        x = panel_c.x + sx * (px * 0.5 - strip_w * 0.5 - 0.5)
        _add_box(
            details_col, f"solar_navy_strip_{tag}",
            (strip_w, strip_l, 2.2),
            (x, panel_c.y, panel_c.z + 1.05),
            NAVY_SOLAR, rough=0.85,
        )
    _add_box(
        details_col, "solar_centre_rib",
        (rib_w, strip_l + 0.6, 2.4),
        (panel_c.x, panel_c.y, panel_c.z + 1.35),
        CHARCOAL_SOLAR, rough=0.7,
    )
    shade_rib = rib_w / 66.6
    shade_strips = (2.0 * strip_w) / 66.6  # navy is glass look — not shade
    return {
        "rib_w_mm": round(rib_w, 2),
        "strip_w_mm": strip_w,
        "bezel_inset_mm": 1.5,
        "panel_pocket_mm": [66.6, 113.6],
        "shade_fraction_rib": round(shade_rib, 3),
        "shade_note": (
            f"Wide charcoal rib {rib_w:.1f} mm ≈ {100 * shade_rib:.0f}% of panel "
            f"width; two navy edge strips {strip_w} mm each (not shading). Bezel "
            f"~1.5 mm ring. Review-only — pocket unchanged. If built proud over "
            f"glass, the rib+bezel would shade ~{100 * shade_rib:.0f}% of width "
            f"(strips are the active glass look)."
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
        "clamp_bar_", "strap_loop",
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
    # D7r8: hide pod clamp bars in review — they read as a thin horizontal bar
    # under the skirt in side view. Print STLs / assembly_check unchanged.
    # Cap clamps (1–2) and CW clamps (7–8) stay visible.
    if o.name in ("clamp_bar_3", "clamp_bar_4", "clamp_bar_5", "clamp_bar_6"):
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
# Solar panel glass (pocket 66.6×113.6 kept) + D7r7 navy/charcoal review look
panel_c = _wbbox_centre("cap_panel_p124") or Vector((0.0, 0.0, 32.5))
if panel_c.z < 25.0:
    panel_c = Vector((panel_c.x, panel_c.y, panel_c.z + 14.0))
# Skirt-aware lid: mating world ≈ CAP_Z0+CAP_MATING_Z = 29.4; land top ≈ 41.4
panel_c = Vector((panel_c.x, panel_c.y, max(float(panel_c.z), 38.5)))
sz = _wbbox_size("cap_panel_p124") or Vector((66.6, 113.6, 2.3))
# Force pocket footprint (review glass); keep ≥2 mm thick for hygiene
_add_box(
    details, "cap_panel_p124",
    (66.6, 113.6, max(float(sz.z), 2.0)),
    (panel_c.x, panel_c.y, panel_c.z),
    PANEL_GLASS, rough=0.12,
)
solar_meta = _add_solar_review_detail(details, panel_c, Vector((66.6, 113.6, 2.0)))

latch_path = _find_detail("latch.stl")
latch_c = _wbbox_centre("latch")
if latch_path and latch_c is not None:
    L = imp_stl(latch_path, details, name="latch")
    Lc = _bbox_centre(L)
    L.location = latch_c - Lc
    L.data.materials.clear()
    L.data.materials.append(orange_mat)
    # Ensure ≥2 mm in every dim for hygiene
    if min(L.dimensions) < 2.0 - 1e-6:
        bpy.data.objects.remove(L, do_unlink=True)
        _add_box(details, "latch", (6.0, 11.0, 2.2), latch_c, ORANGE)
elif latch_c is not None:
    _add_box(details, "latch", (6.0, 11.0, 2.2), latch_c, ORANGE)

plug_c = _wbbox_centre("cap_plug_service_orange_p68p")
if plug_c is not None:
    # ≥2 mm thick solid — no thin plate artifact
    _add_cyl(details, "collar_orange_tab", radius=3.0, depth=2.2, loc=plug_c, rgb=ORANGE)

_add_strap_loop(details)
_add_buckle_keeper(details)
_purge_curves_and_wires()

# Cap corner screw accents ON the lid surface (≥2.2 mm) — skirt-aware Z
cap_z = 33.0 + 0.6
_POD_TILT = math.radians(29.1418)
for i, (x, y) in enumerate([(29.5, 68.0), (-29.5, 68.0), (29.5, -68.0), (-29.5, -68.0)]):
    _add_cyl(details, f"screw_cap_orange_{i}", radius=2.2, depth=2.2,
             loc=(x, y, cap_z), rgb=ORANGE)

# Orange dot ON each pod lid outer — ≈9 mm across (D4 dot row height cue)
for side, sy in (("L", -1.0), ("R", 1.0)):
    _add_cyl(
        details,
        f"pod_{side}_dot_orange",
        radius=4.5,
        depth=2.2,
        loc=(0.0, sy * 110.0, 28.0),
        rgb=ORANGE,
        rot=(_POD_TILT * (-sy), 0.0, 0.0),
    )

# Review-only roof fairing sleeves (print gap kept; no mega-plate unions)
_add_roof_fairing_sleeves(details, BODY)

note = bpy.data.objects.new("NOTE_d4_ghost", None)
note.empty_display_type = "PLAIN_AXES"
note.empty_display_size = 1
note["ghost_note"] = ghost_note
note["palette"] = _palette
note["solar_shade"] = solar_meta.get("shade_note", "")
note["solar_rib_w_mm"] = float(solar_meta.get("rib_w_mm", 0))
note["cap_crown_before_mm"] = 1.0
note["cap_crown_after_mm"] = 3.5
note["cap_nose_tip_before_mm"] = 4.5
note["cap_nose_tip_after_mm"] = 3.0
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
