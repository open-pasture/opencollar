"""D8 straight-prism '001' cutters (shared by printable pod lids + fit coupon).

Local frame (pod lid, before side mirror):
  −X = letter-up (world −X after assembly tilt about X → D4 ref screen-up)
  +Y = baseline along strap; increasing +Y = 0, 0, 1
  +Z = depth into lid (cutter extruded in Z, then placed)
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector


def _extrude_profile_prism(profile_xy, depth, name="prism"):
    import bmesh as _bm

    bm = _bm.new()
    half = float(depth) * 0.5
    bot = [bm.verts.new((p[0], p[1], -half)) for p in profile_xy]
    top = [bm.verts.new((p[0], p[1], +half)) for p in profile_xy]
    bm.verts.ensure_lookup_table()
    n = len(profile_xy)
    bm.faces.new(bot)
    bm.faces.new(list(reversed(top)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    _bm.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _rounded_rect_ring_profile(width, height, stroke, corner_r, n_arc=5):
    def rr(w, h, r):
        r = min(float(r), w * 0.45, h * 0.45)
        hw, hh = w * 0.5, h * 0.5
        arcs = [
            (hw - r, -hh + r, -0.5 * math.pi, 0.0),
            (hw - r, hh - r, 0.0, 0.5 * math.pi),
            (-hw + r, hh - r, 0.5 * math.pi, math.pi),
            (-hw + r, -hh + r, math.pi, 1.5 * math.pi),
        ]
        pts = []
        for cx, cy, a0, a1 in arcs:
            for k in range(n_arc + 1):
                ang = a0 + (a1 - a0) * k / n_arc
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        out = [pts[0]]
        for p in pts[1:]:
            if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-6:
                out.append(p)
        if math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 1e-6:
            out.pop()
        return out

    outer = rr(width, height, corner_r)
    hole = rr(
        max(0.8, width - 2.0 * stroke),
        max(0.8, height - 2.0 * stroke),
        max(0.2, corner_r - stroke * 0.5),
    )
    return outer, hole


def _poly_digit_0(height=6.0, width=3.7, depth=1.2, stroke=1.0):
    outer, hole = _rounded_rect_ring_profile(
        width=width, height=height, stroke=stroke,
        corner_r=min(0.9, width * 0.28, height * 0.18),
    )
    # (px, py) width×height → local (X=−py, Y=px) so +py (top) → −X
    remap = lambda pts: [(-py, px) for px, py in pts]
    o = _extrude_profile_prism(remap(outer), depth, name="d8_digit0_outer")
    h = _extrude_profile_prism(remap(hole), depth * 1.3, name="d8_digit0_hole")
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    mod = o.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = h
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(h, do_unlink=True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    return o


def _poly_digit_1(height=6.0, depth=1.2, stroke=1.0):
    h = float(height)
    d = float(depth)
    sw = float(stroke)
    stem = [
        (-0.5 * h, -0.5 * sw),
        (0.5 * h, -0.5 * sw),
        (0.5 * h, 0.5 * sw),
        (-0.5 * h, 0.5 * sw),
    ]
    fw, fh = sw * 1.5, sw * 0.9
    flag = [
        (-0.5 * h, -0.5 * sw - fw),
        (-0.5 * h + fh, -0.5 * sw - fw),
        (-0.5 * h + fh, -0.5 * sw + 0.15),
        (-0.5 * h, -0.5 * sw + 0.15),
    ]
    s = _extrude_profile_prism(stem, d, name="d8_digit1_stem")
    f = _extrude_profile_prism(flag, d, name="d8_digit1_flag")
    bpy.ops.object.select_all(action="DESELECT")
    s.select_set(True)
    bpy.context.view_layer.objects.active = s
    mod = s.modifiers.new("flag_u", "BOOLEAN")
    mod.operation = "UNION"
    mod.object = f
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(f, do_unlink=True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    return s


def make_001_cutters(size=6.0, depth=1.2, stroke=1.0, width=3.7, gap=1.2):
    """Three prisms along +Y = 0,0,1; letter-up −X. Returns list of objects."""
    half = float(depth) * 0.5
    parts = []
    for i, kind in enumerate(("0", "0", "1")):
        if kind == "0":
            c = _poly_digit_0(height=size, width=width, depth=depth, stroke=stroke)
        else:
            c = _poly_digit_1(height=size, depth=depth, stroke=stroke)
        c.name = f"d8_cutter_001_{kind}_{i}"
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
        ys = [v.co.y for v in c.data.vertices]
        parts.append((c, max(ys) - min(ys)))
    spans = [w for _, w in parts]
    total = sum(spans) + gap * (len(spans) - 1)
    y = -0.5 * total
    cutters = []
    for c, w in parts:
        c.location = Vector((0.0, y + 0.5 * w, 0.0))
        cutters.append(c)
        y += w + gap
    return cutters, total
