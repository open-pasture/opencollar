"""D6 counterweight + clamp set — D4 contoured skin around D5 internals.

Scope (CW agent): cw_tub, cw_lid (domed), saddle, fairing_cw_L/R, clamp_bar,
cw_floor_layout. Cap/pods are other agents.

CHOICE (mass): keep D5 envelope 88×74×30 mm tub. D4's ~59×85×24 cannot hold the
required steel pack (4× 76.2×50.8×6.35 mm flat bar ≈ 772 g). Lid takes D4's
domed ~12.7 mm look. Print orientation: mating-face-down (less support than
outer-down; same rule as cap_lid). Rotation only — never flip_normals().

Print orientation (bed at z=0):
  cw_tub           — cavity UP
  cw_lid           — MATING face DOWN z=0 (chosen vs outer-down)
  saddle           — roof on bed; channel opens +Z (strap along Y)
  clamp_bar        — flange on bed; channel +Z; load along Y WITH layers
  fairing_cw_*     — long axis on bed; slope as WALL
  cw_floor_layout  — underside on bed; ribs/glyphs UP

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python cw.py
"""

from __future__ import annotations

import json
import math
import os
import struct
import sys
from collections import Counter

import bpy
from mathutils import Matrix, Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOK = os.path.abspath(os.path.join(_HERE, ".."))
_COMMON = os.path.abspath(os.path.join(_ROOK, "..", "common", "cad", "lib"))
_D5_CAD = os.path.abspath(os.path.join(_ROOK, "d5", "cad"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _D5_CAD)
sys.path.insert(0, _HERE)
import oc  # noqa: E402
import d5_dims as D  # noqa: E402
import assembly as A  # noqa: E402

CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
ORANGE = (0xFF / 255, 0x6A / 255, 0x2B / 255, 1.0)
STEEL_GREY = (0.55, 0.55, 0.57, 1.0)
WORLD = (0.94, 0.93, 0.90)

# ---------------------------------------------------------------- dimensions / CHOICE
# D5 mass envelope kept; D4 look on the lid only.
CW_L, CW_W, CW_H = D.CW_L, D.CW_W, D.CW_H          # 88 × 74 × 30
CW_FLOOR = 3.0
CW_WALL = 6.0
CW_LID_T = 12.7                                     # D4 domed lid height
CW_LID_FLAT = 4.0                                   # mating slab thickness
CW_CROWN_RISE = CW_LID_T - CW_LID_FLAT              # ~8.7 mm dome above flat
CW_CROWN_LAND = (42.0, 36.0)                        # flat land on dome apex (X,Y)
CW_SCREWS = list(D.CW_SCREWS)                       # (±22, ±31.5)
# D6: unify Y with clamp_bar holes (±28.5); X stays ±36 (see assembly.py)
CW_CLAMP = list(A.CW_CLAMP)                         # (±36, ±28.5)
PLAN_R = D.PLAN_R
CAP_CLAMP = list(A.CAP_CLAMP)                       # (±28.5, ±20) strap-along-Y

# Steel pack (node_v1 / D5 required mass)
STEEL_PIECE = (76.2, 50.8, 6.35)                    # 3 in of 2×1/4 in flat bar
STEEL_N = 4
STEEL_DENSITY = 7.85                                # g/cm³ mild steel
STEEL_CLEAR = 1.2                                   # pocket oversize per side of pack XY
FOAM_PAD_T = 1.5                                    # foam above steel under lid

# Strap interface (bottom of loop) — channel width across X, run along Y
CHANNEL_W = A.SADDLE_CHANNEL_W                      # STRAP_W + 2 = 46.45
CHANNEL_D = A.SADDLE_CHANNEL_D                      # 3.4
SADDLE_W = A.SADDLE_W
SADDLE_L = A.SADDLE_L
SADDLE_ROOF = A.SADDLE_ROOF
SADDLE_H = A.SADDLE_H

# Fairings — widen to span 88 mm CW (assembly.py)
FAIRING_RUN = A.FAIRING_RUN
FAIRING_W0 = A.FAIRING_W0
FAIRING_W1 = A.FAIRING_W1
FAIRING_H = A.FAIRING_H

# Glyphs — same spec as D5 build_d5.py @ 6b1f882
FLOOR_GLYPHS = True
FLOOR_RIB_H = 3.0
GLYPH_DEPTH = 0.75
GLYPH_SIZE = 10.0
GLYPH_STROKE = 0.85
GLYPH_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GLYPH_EMBED = 0.15
GLYPH_REMESH = 0.2
GLYPH_CHAR_H = 5.0

# SINGLE SOURCE text table for CW floor (contract: one table)
FLOOR_LABEL_TABLE = {
    "STEEL": ("STEEL", "CW steel pack only — no electronics"),
    "ONLY": ("ONLY", "no antennas / boards in CW"),
    "FILL": ("FILL", "fill line — steel top + foam"),
    "SCR1": ("1", "screw order 1"),
    "SCR2": ("2", "screw order 2"),
    "SCR3": ("3", "screw order 3"),
    "SCR4": ("4", "screw order 4"),
    "PIN1": ("ARROW", "lid / assembly direction toward +Y strap"),
    "UP": ("UP", "cavity orientation cue"),
}

# Mating-face-down chosen over outer-down (larger bed face / far less support;
# same rule as cap_lid). Rotation only + recalc normals — never flip_normals().
FLIP_OUTER_DOWN = set()
GLYPH_EXPORT_WELD = {"cw_tub", "cw_floor_layout"}

STL_DIR = os.path.join(_HERE, "stl")
RENDER_DIR = os.path.join(_HERE, "renders")
REVIEW_DIR = os.path.join(_HERE, "review")


def steel_volume_mm3():
    sx, sy, sz = STEEL_PIECE
    return sx * sy * sz * STEEL_N


def steel_mass_g():
    return steel_volume_mm3() / 1000.0 * STEEL_DENSITY


def cavity_xy():
    """Steel pack pocket XY (piece + clearance)."""
    sx, sy, _ = STEEL_PIECE
    return (sx + STEEL_CLEAR, sy + STEEL_CLEAR)


def cavity_h():
    """Clear height above floor for steel stack + foam."""
    return STEEL_N * STEEL_PIECE[2] + FOAM_PAD_T + 0.5  # ~27.4


# ---------------------------------------------------------------- mesh helpers (from D5)

def prepare(obj, merge=1e-4):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge)
    bmesh.ops.dissolve_degenerate(bm, dist=merge, edges=list(bm.edges))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    boundary = [e for e in bm.edges if len(e.link_faces) < 2]
    if boundary:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=8)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def normalize_z0(obj):
    oc.bake(obj)
    lo, _hi = oc.bounds(obj)
    if abs(lo[2]) > 1e-6:
        oc.move(obj, dz=-lo[2])
    return obj


def flip_outer_down(obj):
    """Rotate 180° about X. Never flip_normals() — that inverts volume."""
    oc.bake(obj)
    obj.data.transform(Matrix.Rotation(math.radians(180), 4, "X"))
    return normalize_z0(prepare(obj))


def check_wt(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return {"watertight": bad == 0, "bad_edges": bad, "normals_outward": vol > 0,
            "volume_mm3": abs(vol)}


def check_stl(path, q=1e-4):
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0]
    edges = Counter()
    off = 84
    for _ in range(n):
        vals = struct.unpack_from("<12fH", data, off)
        off += 50
        vs = [vals[3:6], vals[6:9], vals[9:12]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka = tuple(round(vs[a][i] / q) * q for i in range(3))
            kb = tuple(round(vs[b][i] / q) * q for i in range(3))
            key = (ka, kb) if ka < kb else (kb, ka)
            edges[key] += 1
    bad = sum(1 for c in edges.values() if c != 2)
    return {"watertight": bad == 0, "bad_edges": bad, "faces": n}


def bed_face_area_mm2(obj, z_tol=0.05):
    """Approximate area of faces whose centroid is within z_tol of min Z."""
    import bmesh
    oc.bake(obj)
    lo, _ = oc.bounds(obj)
    z0 = lo[2]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    area = 0.0
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(c.z - z0) <= z_tol and f.normal.z < -0.3:
            area += f.calc_area()
    bm.free()
    return round(area, 1)


def slab(name, w, l, h, r=PLAN_R):
    return oc.rounded_rect(name, (w, l, h), r, anchor="bottom", segments=10)


def cut_cav(body, w, l, floor, h, r=4.0):
    oc.cut(body, oc.rounded_rect("cav", (w, l, h + 1), r,
                                 at=(0, 0, floor), anchor="bottom"))
    return body


def groove(body, w, l, r, z_top, wall):
    g, gd = D.GROOVE_W, D.GROOVE_D
    inset = wall - D.GROOVE_INNER_LAND - g / 2
    inset = max(inset, D.GROOVE_OUTER_LAND + g / 2)
    half = g / 2
    r_i = max(r - inset - half, 1.0)
    r_o = r_i + g
    outer = oc.rounded_rect("go", (w - 2 * (inset - half), l - 2 * (inset - half), gd + 1),
                            r_o, at=(0, 0, z_top - gd), anchor="bottom")
    inner = oc.rounded_rect("gi", (w - 2 * (inset + half), l - 2 * (inset + half), gd + 3),
                            r_i, at=(0, 0, z_top - gd - 1), anchor="bottom")
    oc.cut(body, oc.cut(outer, inner))
    return body


def reg_lip(body, w, l, r, z_top, wall, h=1.2):
    inset = wall / 2 + D.GROOVE_W / 2 + 0.6
    lip_w = w - 2 * inset
    lip_l = l - 2 * inset
    if lip_w < 10 or lip_l < 10:
        return body
    lip = oc.rounded_rect("lip", (lip_w, lip_l, h), max(r - inset, 2.0),
                          at=(0, 0, z_top), anchor="bottom")
    oc.union(body, lip)
    oc.cut(body, oc.rounded_rect("lipin", (lip_w - 3.2, lip_l - 3.2, h + 1.0),
                                 max(r - inset - 1.6, 1.5),
                                 at=(0, 0, z_top - 0.5), anchor="bottom"))
    return body


def columns(body, cols, floor, top, d=8.0):
    bosses = [oc.cylinder(f"c{i}", d, top - floor,
                          at=(x, y, floor), anchor="bottom")
              for i, (x, y) in enumerate(cols)]
    oc.union(body, *bosses)
    for i, (x, y) in enumerate(cols):
        oc.cut(body, oc.cylinder(f"ins{i}", D.INSERT_D, 5.0,
                                 at=(x, y, top - 5.0), anchor="bottom"))
    return body


def lid_fasteners(lid, cols, lid_t):
    for i, (x, y) in enumerate(cols):
        oc.cut(lid, oc.cylinder(f"h{i}", D.CLEAR, lid_t + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(lid, oc.cylinder(f"cb{i}", D.CBORE_D, 2.2 + D.PLUG_SEAT_H,
                                at=(x, y, lid_t - (2.2 + D.PLUG_SEAT_H)), anchor="bottom"))
        oc.cut(lid, oc.cylinder(f"ps{i}", D.PLUG_SEAT_D, D.PLUG_SEAT_H + 0.05,
                                at=(x, y, lid_t - D.PLUG_SEAT_H), anchor="bottom"))
    return lid


def locate_rib_rect(body, name, size_xy, at_xy, floor_z, h=FLOOR_RIB_H, wall=1.2):
    sx, sy = size_xy
    ox, oy = sx / 2 + wall / 2, sy / 2 + wall / 2
    segs = [
        ((sx + 2 * wall, wall, h), (at_xy[0], at_xy[1] + oy, floor_z)),
        ((sx + 2 * wall, wall, h), (at_xy[0], at_xy[1] - oy, floor_z)),
        ((wall, sy, h), (at_xy[0] + ox, at_xy[1], floor_z)),
        ((wall, sy, h), (at_xy[0] - ox, at_xy[1], floor_z)),
    ]
    for i, (sz, pos) in enumerate(segs):
        oc.union(body, oc.box(f"{name}_w{i}", sz, at=pos, anchor="bottom"))
    return body


# ---------------------------------------------------------------- glyphs (D5 DejaVu Bold)

def _glyph_font():
    for f in bpy.data.fonts:
        if getattr(f, "filepath", "") == GLYPH_FONT or f.name.startswith("DejaVuSans-Bold"):
            try:
                _ = f.filepath
                return f
            except ReferenceError:
                break
    return bpy.data.fonts.load(GLYPH_FONT)


def _glyph_char_mesh(ch, size, depth, stroke=GLYPH_STROKE):
    outline = max(0.05, (stroke - 0.55) / 2)
    safe = ch if ch.isalnum() else "x"
    cu = bpy.data.curves.new(f"cu_{safe}", "FONT")
    cu.body = ch
    cu.size = size
    cu.extrude = 0.0
    cu.fill_mode = "FRONT"
    cu.offset = outline
    cu.font = _glyph_font()
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    obj = oc._link(bpy.data.objects.new(f"ch_{safe}", cu))
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    bm.to_mesh(obj.data)
    bm.free()
    sol = obj.modifiers.new("sol", "SOLIDIFY")
    sol.thickness = depth
    sol.offset = 1.0
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    vox = obj.modifiers.new("vox", "REMESH")
    vox.mode = "VOXEL"
    vox.voxel_size = GLYPH_REMESH
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    prepare(obj, merge=1e-4)
    return obj


def _text_mesh(label, size, depth, stroke=GLYPH_STROKE):
    chars = [c for c in label if not c.isspace()]
    if not chars:
        return oc.box("empty_glyph", (1, 1, depth), anchor="bottom")
    parts = []
    cursor_x = 0.0
    gap = 0.8
    for ch in chars:
        g = _glyph_char_mesh(ch, size, depth, stroke=stroke)
        lo, hi = oc.bounds(g)
        w = hi[0] - lo[0]
        oc.move(g,
                dx=cursor_x - (lo[0] + hi[0]) / 2,
                dy=-(lo[1] + hi[1]) / 2,
                dz=-lo[2])
        parts.append(g)
        cursor_x += w + gap
    body = parts[0]
    for p in parts[1:]:
        oc.union(body, p)
    return prepare(body)


def _stroke_plus(size, depth, stroke=GLYPH_STROKE):
    arm = size * 0.9
    h = oc.box("plus_h", (arm, stroke, depth), anchor="bottom")
    v = oc.box("plus_v", (stroke, arm, depth), anchor="bottom")
    return oc.union(h, v)


def _stroke_minus(size, depth, stroke=GLYPH_STROKE):
    return oc.box("minus", (size * 0.9, stroke, depth), anchor="bottom")


def _stroke_arrow(size, depth, stroke=GLYPH_STROKE):
    stem = oc.box("arr_stem", (stroke, size * 0.7, depth),
                  at=(0.0, -size * 0.1, 0.0), anchor="bottom")

    def chevron_bar(name, angle_deg):
        bar = oc.box(name, (size * 0.55, stroke, depth), anchor="bottom")
        oc.bake(bar)
        bar.data.transform(Matrix.Rotation(math.radians(angle_deg), 4, "Z"))
        lo, hi = oc.bounds(bar)
        oc.move(bar,
                dx=-(lo[0] + hi[0]) / 2,
                dy=size * 0.32 - (lo[1] + hi[1]) / 2,
                dz=-lo[2])
        return bar

    return oc.union(oc.union(stem, chevron_bar("arr_l", 40)), chevron_bar("arr_r", -40))


def emboss_glyph(body, key_or_text, at, size=GLYPH_SIZE, depth=GLYPH_DEPTH, rot_z=0.0):
    if not FLOOR_GLYPHS or not key_or_text:
        return body
    if key_or_text in FLOOR_LABEL_TABLE:
        label = FLOOR_LABEL_TABLE[key_or_text][0]
    else:
        label = key_or_text
    stroke_h = GLYPH_CHAR_H if abs(size - GLYPH_SIZE) < 1e-6 else size * (GLYPH_CHAR_H / GLYPH_SIZE)
    if label in ("+", "PLUS"):
        glyph = _stroke_plus(stroke_h, depth)
    elif label in ("-", "−", "MINUS"):
        glyph = _stroke_minus(stroke_h, depth)
    elif label in ("ARROW", "▶", ">", "PIN1"):
        glyph = _stroke_arrow(stroke_h, depth)
    else:
        glyph = _text_mesh(label, size, depth)
    lo, hi = oc.bounds(glyph)
    oc.move(glyph,
            dx=at[0] - (lo[0] + hi[0]) / 2,
            dy=at[1] - (lo[1] + hi[1]) / 2,
            dz=(at[2] - GLYPH_EMBED) - lo[2])
    if abs(rot_z) > 1e-6:
        oc.bake(glyph)
        cx, cy = at[0], at[1]
        T = (Matrix.Translation((cx, cy, 0)) @
             Matrix.Rotation(math.radians(rot_z), 4, "Z") @
             Matrix.Translation((-cx, -cy, 0)))
        glyph.data.transform(T)
    oc.union(body, glyph)
    return body


def emboss_label(body, key, at, size=GLYPH_SIZE, depth=GLYPH_DEPTH, rot_z=0.0):
    return emboss_glyph(body, key, at, size=size, depth=depth, rot_z=rot_z)


# ---------------------------------------------------------------- dome helper

def _uv_sphere(name, radius, segments=32, rings=16):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return oc._from_bmesh(name, bm)


def _domed_lid_solid(name, w, l, flat_h, total_h, plan_r, land_xy):
    """Mating slab + truncated ellipsoid dome with flat crown land (bed face).

    Modeled mating at z=0, outer +Z. Export flips 180° about X.
    """
    body = slab(name, w, l, flat_h, plan_r)
    # Ellipsoid sized so it peaks near total_h and covers the plan
    rx, ry = w * 0.62, l * 0.62
    rz = CW_CROWN_RISE * 1.35
    sph = _uv_sphere(f"{name}_sph", 1.0, segments=28, rings=14)
    oc.bake(sph)
    # scale to ellipsoid
    for v in sph.data.vertices:
        v.co.x *= rx
        v.co.y *= ry
        v.co.z *= rz
    sph.data.update()
    # Centre so equator sits near flat_h; upper hemisphere forms the dome
    oc.move(sph, dz=flat_h)
    # Keep only the part above flat_h - 0.5 and inside plan
    keep = oc.box(f"{name}_keep", (w + 2, l + 2, total_h + 4),
                  at=(0, 0, flat_h - 0.5), anchor="bottom")
    oc.intersect(sph, keep)
    bound = oc.rounded_rect(f"{name}_bnd", (w, l, total_h + 2), plan_r,
                            at=(0, 0, -0.5), anchor="bottom", segments=10)
    oc.intersect(sph, bound)
    oc.union(body, sph)
    # Flat crown land (printable bed face after flip)
    lw, ll = land_xy
    land = oc.rounded_rect(f"{name}_land", (lw, ll, 1.2), 3.0,
                           at=(0, 0, total_h - 1.0), anchor="bottom", segments=8)
    oc.union(body, land)
    # Trim anything above total_h
    oc.cut(body, oc.box(f"{name}_cap", (w + 4, l + 4, 6),
                        at=(0, 0, total_h), anchor="bottom"))
    return body


# ---------------------------------------------------------------- parts

def cw_tub():
    """Print: cavity UP. Steel only. Floor ribs + embossed glyphs."""
    b = slab("cw_tub", CW_L, CW_W, CW_H, PLAN_R)
    cx, cy = cavity_xy()
    ch = max(cavity_h(), CW_H - CW_FLOOR)
    # Cavity must fit steel; also leave wall for groove (use max of steel pocket, CW-12)
    cav_w = max(cx, CW_L - 2 * CW_WALL)
    cav_l = max(cy, CW_W - 2 * CW_WALL)
    # Prefer steel-sized pocket so pack seats; walls stay ≥ (outer-steel)/2
    cav_w, cav_l = cx, cy
    cut_cav(b, cav_w, cav_l, CW_FLOOR, ch + 1, r=3.0)
    columns(b, CW_SCREWS, CW_FLOOR, CW_H, d=8.0)
    groove(b, CW_L, CW_W, PLAN_R, CW_H, CW_WALL)
    reg_lip(b, CW_L, CW_W, PLAN_R, CW_H, CW_WALL)
    # Clamp through-holes (bars under saddle at CW bottom)
    for i, (x, y) in enumerate(CW_CLAMP):
        oc.cut(b, oc.cylinder(f"cwcl{i}", D.CLEAR, CW_H + 2, at=(x, y, -1), anchor="bottom"))

    # Floor ribs — steel pack fence
    locate_rib_rect(b, "steel", (STEEL_PIECE[0], STEEL_PIECE[1]), (0, 0),
                    CW_FLOOR, h=2.5, wall=1.4)
    # Cross ribs under pack for stiffness
    for i, dy in enumerate((-18.0, 0.0, 18.0)):
        oc.union(b, oc.box(f"rib_y{i}", (cav_w - 8, 1.6, 2.0),
                           at=(0, dy, CW_FLOOR), anchor="bottom"))
    for i, dx in enumerate((-22.0, 22.0)):
        oc.union(b, oc.box(f"rib_x{i}", (1.6, cav_l - 8, 2.0),
                           at=(dx, 0, CW_FLOOR), anchor="bottom"))

    # Embossed glyphs (DejaVu Bold / stroke) — fill line, screw order, arrows
    fz = CW_FLOOR
    emboss_label(b, "STEEL", (0.0, 14.0, fz))
    emboss_label(b, "ONLY", (0.0, -14.0, fz))
    emboss_label(b, "FILL", (0.0, 0.0, fz))
    emboss_label(b, "PIN1", (28.0, 0.0, fz), rot_z=-90.0)
    for key, (sx, sy) in (("SCR1", (1, 1)), ("SCR2", (-1, 1)),
                          ("SCR3", (1, -1)), ("SCR4", (-1, -1))):
        emboss_label(b, key, (sx * 30.0, sy * 24.0, fz))
    return prepare(b)


def cw_lid():
    """Domed D4-look lid. Mating@z=0; PRINT mating-face-down (no outer flip).

    Compared outer-down (~787 mm² bed / ~5544 mm² support) vs mating-down
    (large bed face / far less support) — picked mating-down like cap_lid.
    Seal: lid mates to tub O-ring land; 4× M3 button into tub inserts;
    foam pad compresses steel. Strap channel on OUTER (+Z) face, width across X.
    """
    lw, ll = CW_L - 2 * D.REVEAL, CW_W - 2 * D.REVEAL
    lid = _domed_lid_solid("cw_lid", lw, ll, CW_LID_FLAT, CW_LID_T,
                           PLAN_R - 0.5, CW_CROWN_LAND)
    lid_fasteners(lid, CW_SCREWS, CW_LID_T)
    # Landing ring on mating face
    ring_w = 1.6
    ring_out_w, ring_out_l = lw - 6.0, ll - 6.0
    r_o = 4.0
    r_i = r_o - ring_w
    outer = oc.rounded_rect("lring_o", (ring_out_w, ring_out_l, 1.5), r_o,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("lring_i", (ring_out_w - 2 * ring_w, ring_out_l - 2 * ring_w, 2.0),
                            r_i, at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))
    # Strap channel on OUTER face — width along X, run along Y (strap-along-Y)
    oc.cut(lid, oc.box("cwchan",
                       (CHANNEL_W, ll + 2, CHANNEL_D + 0.3),
                       at=(0, 0, CW_LID_T - CHANNEL_D), anchor="bottom"))
    # Clamp insert seats on outer (toward strap) — bars clamp through saddle
    for i, (x, y) in enumerate(CW_CLAMP):
        if abs(x) > lw / 2 - 4 or abs(y) > ll / 2 - 4:
            continue
        oc.cut(lid, oc.cylinder(f"cwci{i}", D.INSERT_D, 4.8 + 0.5,
                                at=(x, y, CW_LID_T - 4.8), anchor="bottom"))
    return prepare(lid)


def saddle():
    """Strap saddle. Roof on bed; channel +Z. Strap along Y: width across X.

    Channel 46.45 × 3.4; body 76 wide; holes at CAP_CLAMP (±28.5, ±20).
    """
    s = oc.rounded_rect("saddle", (SADDLE_W, SADDLE_L, SADDLE_H), 3.0,
                        anchor="bottom", segments=8)
    # Channel: width = CHANNEL_W along X, run along Y (was D5 cross-strap)
    oc.cut(s, oc.box("schan",
                     (CHANNEL_W, SADDLE_L + 2, CHANNEL_D + 0.2),
                     at=(0, 0, SADDLE_ROOF), anchor="bottom"))
    # Lead-ins at ±Y ends (strap entry/exit) — chamfer the channel mouths
    for sy in (-1, 1):
        oc.cut(s, oc.box(
            f"lead{sy}", (CHANNEL_W + 2, 5.0, SADDLE_H),
            at=(0, sy * (SADDLE_L / 2 - 1.0), SADDLE_ROOF - 0.2), anchor="bottom"))
    # Clamp holes — D6 CAP_CLAMP (±28.5, ±20)
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(s, oc.cylinder(f"scl{i}", D.CLEAR, SADDLE_H + 2, at=(x, y, -1), anchor="bottom"))
    for i, (x, y) in enumerate([(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]):
        pin = oc.cylinder(f"spin{i}", 4.0, 1.5, at=(x, y, SADDLE_H), anchor="bottom")
        oc.union(s, pin)
    return prepare(s)


def clamp_bar():
    """10×70×8 channel bar, flange-down. Print 8× per collar.

    LoRa clearance: clamps under saddle at |y|≤28.5; LoRa at y≈64 → 35.5 mm
    (≥15 mm keep). Load along Y WITH layers.
    """
    flange = oc.rounded_rect("cflange", (D.CLAMP_FLANGE_W, D.CLAMP_L, D.CLAMP_WEB), 1.0,
                             anchor="bottom", segments=4)
    wall_h = D.CLAMP_DEPTH - D.CLAMP_WEB
    for sx in (-1, 1):
        w = oc.box(f"cwall{sx}", (D.CLAMP_WEB, D.CLAMP_L - 2, wall_h),
                   at=(sx * (D.CLAMP_FLANGE_W / 2 - D.CLAMP_WEB / 2), 0, D.CLAMP_WEB),
                   anchor="bottom")
        oc.union(flange, w)
    for i, sy in enumerate((-28.5, 28.5)):
        if abs(sy) > D.CLAMP_L / 2 - 5:
            continue
        oc.cut(flange, oc.cylinder(f"ch{i}", D.CLEAR, D.CLAMP_DEPTH + 2,
                                   at=(0, sy, -1), anchor="bottom"))
    return prepare(flange)


def _fairing_body(name, run, w0, w1, h):
    f = oc.prism_y(name, [
        (0.0, 0.0),
        (w0 / 2, 0.0),
        (w1 / 2, h),
        (-w1 / 2, h),
        (-w0 / 2, 0.0),
    ], run)
    bound = oc.rounded_rect(f"{name}_bnd", (max(w0, w1) + 2, run + 2, h + 2),
                            D.FAIRING_R, at=(0, 0, -1), anchor="bottom", segments=10)
    oc.intersect(f, bound)
    try:
        oc.bevel(f, D.FAIRING_EDGE_R, segments=3)
        oc.apply_modifiers(f)
    except Exception:
        pass
    return f


def fairing_cw(side="L"):
    """CW↔strap fairing at bottom of loop. W0=88→W1=66 × run 28 × H 14."""
    f = prepare(_fairing_body(f"fairing_cw_{side}", FAIRING_RUN, FAIRING_W0, FAIRING_W1, FAIRING_H))
    if side == "R":
        # Mirror of L across X (matches pod fairings)
        oc.bake(f)
        f.data.transform(Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0)))
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(f.data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(f.data)
        bm.free()
        f.data.update()
    return f


def cw_floor_layout():
    """PLA coupon: steel outline + glyphs from FLOOR_LABEL_TABLE."""
    w, l = 78.0, 58.0
    floor = oc.rounded_rect("cw_floor", (w, l, 2.0), 3.0, anchor="bottom", segments=6)
    locate_rib_rect(floor, "steel", (STEEL_PIECE[0], STEEL_PIECE[1]), (0, 0), 2.0,
                    h=2.5, wall=1.5)
    emboss_label(floor, "STEEL", (0, 16, 2.0))
    emboss_label(floor, "ONLY", (0, -16, 2.0))
    emboss_label(floor, "FILL", (0, 0, 2.0))
    emboss_label(floor, "PIN1", (30, 0, 2.0), rot_z=-90.0)
    for key, (sx, sy) in (("SCR1", (1, 1)), ("SCR2", (-1, 1)),
                          ("SCR3", (1, -1)), ("SCR4", (-1, -1))):
        emboss_label(floor, key, (sx * 28.0, sy * 20.0, 2.0))
    return normalize_z0(prepare(floor))


# ---------------------------------------------------------------- export / render

PART_META = {
    "cw_tub": ("PRINT: cavity UP; bed=underside z=0; glyphs UP",
               "steel pack; NO antennas; M3 farmer path", "ASA/PETG", False),
    "cw_lid": ("PRINT: MATING face DOWN z=0 (no outer flip; less support)",
               "lid screws; dome up; strap channel on outer", "ASA/PETG", True),
    "saddle": ("PRINT: roof on bed z=0; channel +Z; strap along Y",
               "strap→rails→clamp ALONG layers", "ASA/PETG or PA-CF*", False),
    "clamp_bar": ("PRINT: flange on bed z=0; channel +Z; load ALONG Y WITH layers",
                  "strap compression; holes y=±28.5", "ASA/PETG or PA-CF*", True),
    "fairing_cw_L": ("PRINT: long axis on bed; slope=WALL", "88→66×28×14 CW↔strap", "ASA/PETG", True),
    "fairing_cw_R": ("PRINT: long axis on bed; slope=WALL", "mirror of L", "ASA/PETG", True),
    "cw_floor_layout": ("PRINT: floor underside z=0; ribs/glyphs UP",
                        "PLA steel-pack + fill/screw glyphs", "PLA", False),
}


def export_part(obj, path, meta_key=None):
    weld = 0.008 if meta_key in GLYPH_EXPORT_WELD else 1e-4
    prepare(obj, merge=weld)
    flipped = False
    if meta_key in FLIP_OUTER_DOWN:
        flip_outer_down(obj)
        flipped = True
    else:
        normalize_z0(obj)
    dims = list(oc.size(obj))
    wt = check_wt(obj)
    bed_area = bed_face_area_mm2(obj) if meta_key == "cw_lid" else None
    oc.export_stl(obj, path)
    stl = check_stl(path)
    tag = "OK" if wt["watertight"] and stl["watertight"] else "LOOK"
    bed = "OUTER" if flipped else "as-built"
    print(f"{tag}  {os.path.basename(path)}: {[round(x, 1) for x in dims]}  "
          f"bad={wt['bad_edges']}  bed_z0={bed}  normals_out={wt['normals_outward']}"
          + (f"  bed_area≈{bed_area} mm²" if bed_area is not None else ""))
    body = {
        "size_mm": dims,
        "watertight": wt,
        "stl": stl,
        "pass": wt["watertight"] and stl["watertight"] and wt["normals_outward"],
        "stl_path": os.path.relpath(path, _HERE),
        "export_flipped_outer_down": flipped,
        "normals_outward": wt["normals_outward"],
        "bed_face_at_z0": True,
    }
    if bed_area is not None:
        body["bed_face_area_mm2"] = bed_area
        body["support_note"] = (
            "Flat crown land on bed (~42×36 mm). Strap channel is a pocket on the "
            "bed (no bridge). Internal cbore/landing after flip face UP — no large "
            "tree supports expected; optional tiny supports only if land bridges fail."
        )
    if meta_key and meta_key in PART_META:
        o, load, mat, swap = PART_META[meta_key]
        body.update({"orientation": o, "load_path": load, "material": mat,
                     "farmer_swappable": swap})
    return body


def _mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


def _setup(res=(1400, 1050)):
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.render.resolution_x, s.render.resolution_y = res
    sh = s.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_object_outline = True
    w = bpy.data.worlds.new("w")
    w.color = WORLD
    s.world = w
    s.view_settings.view_transform = "Standard"


def render_objs(objs_colors, path, direction, pad=1.15):
    _setup()
    live = []
    for o, rgba, n in objs_colors:
        o.data.materials.clear()
        o.data.materials.append(_mat(n, rgba))
        live.append(o)
    lo = [min(oc.bounds(o)[0][i] for o in live) for i in range(3)]
    hi = [max(oc.bounds(o)[1][i] for o in live) for i in range(3)]
    centre = (Vector(lo) + Vector(hi)) / 2
    extent = max((Vector(hi) - Vector(lo)).length, 1.0)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(extent * pad, 1)
    cam = oc._link(bpy.data.objects.new("cam", cam_data))
    d = Vector(direction).normalized()
    cam.location = centre + d * extent * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def render_section(objs_colors, path, axis="X"):
    """Section cut for review PNG."""
    live = []
    for o, rgba, n in objs_colors:
        o.data.materials.clear()
        o.data.materials.append(_mat(n, rgba))
        live.append(o)
    lo = [min(oc.bounds(o)[0][i] for o in live) for i in range(3)]
    hi = [max(oc.bounds(o)[1][i] for o in live) for i in range(3)]
    # Cut half away
    mid = [(lo[i] + hi[i]) / 2 for i in range(3)]
    if axis == "X":
        cutter = oc.box("sec", (hi[0] - lo[0] + 4, hi[1] - lo[1] + 4, hi[2] - lo[2] + 4),
                        at=(mid[0] + (hi[0] - lo[0]) / 2 + 1, mid[1], mid[2]))
        direction = (0.2, -1.2, 0.5)
    else:
        cutter = oc.box("sec", (hi[0] - lo[0] + 4, hi[1] - lo[1] + 4, hi[2] - lo[2] + 4),
                        at=(mid[0], mid[1] + (hi[1] - lo[1]) / 2 + 1, mid[2]))
        direction = (1.2, -0.2, 0.5)
    for o, _, _ in objs_colors:
        try:
            oc.cut(o, cutter)
        except Exception:
            pass
    render_objs(objs_colors, path, direction, pad=1.2)


def main():
    for d in (STL_DIR, RENDER_DIR, REVIEW_DIR):
        os.makedirs(d, exist_ok=True)

    builders = [
        ("cw_tub", cw_tub, "cw_tub"),
        ("cw_lid", cw_lid, "cw_lid"),
        ("saddle", saddle, "saddle"),
        ("clamp_bar", clamp_bar, "clamp_bar"),
        ("fairing_cw_L", lambda: fairing_cw("L"), "fairing_cw_L"),
        ("fairing_cw_R", lambda: fairing_cw("R"), "fairing_cw_R"),
        ("cw_floor_layout", cw_floor_layout, "cw_floor_layout"),
    ]

    lora_clear = D.LORA_AT[1] - max(abs(y) for _, y in CAP_CLAMP)
    mass_g = steel_mass_g()
    vol_mm3 = steel_volume_mm3()

    report = {
        "revision": "D6_cw_d4_skin_d5_mass",
        "choice": {
            "envelope": f"{CW_L}×{CW_W}×{CW_H} tub (D5 mass envelope)",
            "lid": f"D4-style dome {CW_LID_T} mm with flat crown land {CW_CROWN_LAND}",
            "why_not_d4_tub": (
                f"D4 tub ~59×85×24 cannot fit steel pack {STEEL_PIECE}×{STEEL_N} "
                f"(stack H={STEEL_N * STEEL_PIECE[2]} mm, XY {STEEL_PIECE[0]}×{STEEL_PIECE[1]})"
            ),
            "fill_material": (
                f"{STEEL_N}× mild steel flat bar {STEEL_PIECE[0]}×{STEEL_PIECE[1]}×"
                f"{STEEL_PIECE[2]} mm (3 in of 2×1/4 in) + {FOAM_PAD_T} mm foam pad"
            ),
            "steel_mass_g": round(mass_g, 1),
            "steel_volume_mm3": round(vol_mm3, 1),
            "steel_volume_cm3": round(vol_mm3 / 1000.0, 2),
            "lid_seal": (
                "2.0 mm O-ring groove in tub rim + registered lip; "
                "4× M3 button-head screws through lid into heat-set inserts; "
                "foam pad compresses steel pack under lid"
            ),
        },
        "clamp_lora_clear_mm": round(lora_clear, 2),
        "clamp_note": "Print clamp_bar ×1 STL; print 8 physical bars per collar",
        "floor_label_table": {k: list(v) for k, v in FLOOR_LABEL_TABLE.items()},
        "floor_glyph_spec": {
            "char_h_mm": GLYPH_CHAR_H,
            "blender_font_size": GLYPH_SIZE,
            "stroke_mm": GLYPH_STROKE,
            "relief_mm": round(GLYPH_DEPTH - GLYPH_EMBED, 2),
            "font": GLYPH_FONT,
        },
        "print_orientation_note": (
            "All STLs bed face at z=0. cw_lid: mating-face-down (no outer flip; "
            "chosen vs outer-down for less support). Never flip_normals()."
        ),
        "cw_clamp": [list(p) for p in CW_CLAMP],
        "cap_clamp": [list(p) for p in CAP_CLAMP],
        "bodies": {},
        "pass": True,
    }

    for name, fn, meta in builders:
        oc.reset()
        obj = fn()
        path = os.path.join(STL_DIR, f"{name}.stl")
        report["bodies"][name] = export_part(obj, path, meta)
        if not report["bodies"][name].get("pass", True):
            report["pass"] = False

    # ---- renders: iso / top / side / section ----
    oc.reset()
    tub = cw_tub()
    lid = cw_lid()
    # Stack for iso (assembly preview — lid not flipped here)
    oc.move(lid, dz=CW_H + 2)
    sad = saddle()
    oc.move(sad, dz=-SADDLE_H - 1)
    bar = clamp_bar()
    oc.move(bar, dx=CW_L / 2 + 20, dz=0)
    fL = fairing_cw("L")
    oc.move(fL, dy=CW_W / 2 + FAIRING_RUN / 2 + 5)
    fR = fairing_cw("R")
    oc.move(fR, dy=-(CW_W / 2 + FAIRING_RUN / 2 + 5))
    colors = [
        (tub, CHARCOAL, "tub"),
        (lid, CHARCOAL, "lid"),
        (sad, CHARCOAL, "saddle"),
        (bar, STEEL_GREY, "bar"),
        (fL, CHARCOAL, "fL"),
        (fR, CHARCOAL, "fR"),
    ]
    render_objs(colors, os.path.join(RENDER_DIR, "cw_iso.png"), (1.3, -1.4, 0.9))
    render_objs(colors, os.path.join(RENDER_DIR, "cw_top.png"), (0.01, 0.01, 1.0), pad=1.25)
    render_objs(colors, os.path.join(RENDER_DIR, "cw_side.png"), (1.0, 0.01, 0.15), pad=1.2)

    # Section through tub+lid
    oc.reset()
    tub2 = cw_tub()
    lid2 = cw_lid()
    oc.move(lid2, dz=CW_H)
    render_section([(tub2, CHARCOAL, "t"), (lid2, ORANGE, "l")],
                   os.path.join(RENDER_DIR, "cw_section.png"), axis="X")

    # ---- review .blend (assembly in print-ish layout) ----
    oc.reset()
    parts = {
        "cw_tub": cw_tub(),
        "cw_lid": cw_lid(),
        "saddle": saddle(),
        "clamp_bar": clamp_bar(),
        "fairing_cw_L": fairing_cw("L"),
        "fairing_cw_R": fairing_cw("R"),
        "cw_floor_layout": cw_floor_layout(),
    }
    # Lineup for review (cw_lid shown mating-down = print orientation)
    oc.move(parts["cw_lid"], dx=110)
    oc.move(parts["saddle"], dx=220)
    oc.move(parts["clamp_bar"], dx=300)
    oc.move(parts["fairing_cw_L"], dx=360)
    oc.move(parts["fairing_cw_R"], dx=420)
    oc.move(parts["cw_floor_layout"], dx=-120)
    blend_path = os.path.join(REVIEW_DIR, "cw_review.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    report["review_blend"] = os.path.relpath(blend_path, _HERE)

    with open(os.path.join(STL_DIR, "cw_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    # NOTE file for clamp qty
    with open(os.path.join(STL_DIR, "CLAMP_QTY.txt"), "w") as f:
        f.write("clamp_bar.stl — print 8× per collar "
                "(2 under cap saddle, 2 under each pod, 2 under CW saddle).\n"
                "Orientation: flange flat on bed, channel opens +Z.\n"
                f"LoRa clearance from clamp |y|≤28.5 to LoRa y≈64 = {lora_clear:.1f} mm.\n")

    print("\nCHOICE: D5 envelope", CW_L, CW_W, CW_H, "+ D4 dome lid", CW_LID_T)
    print(f"STEEL MASS: {mass_g:.1f} g  volume {vol_mm3:.0f} mm³ ({vol_mm3/1000:.1f} cm³)")
    print(f"LoRa clamp clearance: {lora_clear:.1f} mm (need ≥15, contract cites 35.5)")
    print("RESULT:", "PASS" if report["pass"] else "LOOK — check watertight")
    return report


if __name__ == "__main__":
    main()
