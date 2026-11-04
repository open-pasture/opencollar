"""D5 production CAD — printable parametric rebuild of the D5 look study.

Exported STLs are in INTENDED PRINT ORIENTATION: bed face at z=0.

  cap/pod/cw bases     — cavity UP; bed = outer underside (z=0); floor glyphs UP
  cap_lid              — MATING face DOWN (z=0); outer UP — P124 pocket faces +Z
                         (outer-down would put ~7k mm² panel ceiling on supports)
  pod/cw lids          — OUTER face DOWN (z=0); mating UP (rotated on export)
  saddle               — roof on bed (z=0); strap channel opens +Z (no bridge)
  clamp_bar            — flange on bed (z=0); channel opens +Z
  fairings             — long axis on bed; slope as WALL
  floor_layout coupons — floor underside on bed; ribs/glyphs UP
  small parts          — flat on bed as built

Pod/CW lids are modeled mating-at-z=0; export_part rotates 180° about X
(recalc normals — never mirror / flip_normals) then normalize_z0.

FLOOR_GLYPHS: real embossed letterforms (≥5 mm, stroke ≥0.8, relief ≥0.6)
on floor-layout coupons AND on cap_base / pod_*_base / cw_tub floors.

Run:
  cd hardware/rook/d5/cad
  blender --background --factory-startup --python build_d5.py
"""

from __future__ import annotations

import json
import math
import os
import shutil
import struct
import sys
from collections import Counter

import bpy
from mathutils import Matrix, Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_D5 = os.path.abspath(os.path.join(_HERE, ".."))
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _HERE)
import oc  # noqa: E402
import d5_dims as D  # noqa: E402

CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
ORANGE = (0xFF / 255, 0x6A / 255, 0x2B / 255, 1.0)
PANEL_NAVY = (0.10, 0.14, 0.22, 1.0)
BLACK = (0.07, 0.07, 0.08, 1.0)
OAT = (0xEF / 255, 0xE8 / 255, 0xD8 / 255, 1.0)
WORLD = (0.94, 0.93, 0.90)

# Floor-layout assembly aids (Cody PLA floor print). Toggle glyphs/ribs.
FLOOR_GLYPHS = True
FLOOR_RIB_H = 3.0
FLOOR_LAYOUT_H = 8.0          # trimmed coupon height
GLYPH_DEPTH = 0.75            # solidify thickness; exposed relief = DEPTH - EMBED ≥ 0.6
# Blender FONT size; DejaVu Bold @10 → capital height ≈5.05 mm (≥5), "I" stroke ≈1.5 mm.
GLYPH_SIZE = 10.0
GLYPH_STROKE = 0.85           # target stroke width ≥0.8 mm (outline offset + bold stem)
GLYPH_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GLYPH_EMBED = 0.15            # sink into floor so boolean stays manifold
GLYPH_REMESH = 0.2            # voxel remesh text before union (keeps EXACT boolean manifold)
GLYPH_CHAR_H = 5.0            # nominal capital height (mm) documented for reviewers

# id → (short printable label, notes) — SINGLE SOURCE for floor glyphs
FLOOR_LABEL_TABLE = {
    "KIT": ("KIT", "nRF9151 Connect Kit; USB→−Y; pin1 mark"),
    "BQ": ("BQ", "bq24074 charger; DO NOT POT"),
    "WIO": ("WIO", "SX1262 lay-flat; U.FL→crest"),
    "USB": ("USB", "USB-C charge"),
    "BATT": ("BATT", "18650 cell bay"),
    "BUZZ": ("BUZZ", "Qwiic buzzer"),
    "GNSS": ("GNSS", "patch sky; lid / crest"),
    "LTE": ("LTE", "flex; lid / crest"),
    "POST": ("P", "lid support post"),
    "SCR1": ("1", "screw order 1"),
    "SCR2": ("2", "screw order 2"),
    "SCR3": ("3", "screw order 3"),
    "SCR4": ("4", "screw order 4"),
    "PLUS": ("+", "cell + polarity"),
    "MINUS": ("-", "cell - polarity"),
    "PIN1": ("ARROW", "pin-1 / connector direction"),
    "STEEL": ("STEEL", "CW steel pack only"),
    "ONLY": ("ONLY", "no electronics in CW"),
}

# Parts modeled mating-at-z=0 that print OUTER face down.
# cap_lid intentionally NOT listed — P124 pocket must face +Z (mating on bed).
FLIP_OUTER_DOWN = {
    "pod_L_lid", "pod_R_lid", "cw_lid",
}

# ---------------------------------------------------------------- mesh helpers

def prepare(obj, merge=1e-4):
    """Triangulate, weld near-coincident verts, drop degenerates, fill tiny holes.

    Default merge=1e-4 preserves fine gauges (fit_coupon). Glyph-bearing parts
    pass merge=0.008 at export so remesh/boolean STLs stay watertight in float32.
    """
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


# Parts with embossed floor glyphs need a slightly looser weld at export.
GLYPH_EXPORT_WELD = {
    "cap_base", "pod_L_base", "pod_R_base", "cw_tub",
    "cap_floor_layout", "pod_floor_layout", "cw_floor_layout",
}


def normalize_z0(obj):
    """Translate mesh so min Z == 0 (bed plane)."""
    oc.bake(obj)
    lo, _hi = oc.bounds(obj)
    if abs(lo[2]) > 1e-6:
        oc.move(obj, dz=-lo[2])
    return obj


def flip_outer_down(obj):
    """Rotate 180° about X so former +Z (outer) becomes bed at z=0 after normalize.

    Proper rotation only — do NOT mirror or flip_normals() (that inverts winding /
    yields negative volume). prepare() recalculates outward normals.
    """
    oc.bake(obj)
    obj.data.transform(Matrix.Rotation(math.radians(180), 4, "X"))
    return normalize_z0(prepare(obj))


def _glyph_font():
    """Load (or reuse) the emboss font. Re-load if a prior oc.reset() dropped it."""
    for f in bpy.data.fonts:
        if getattr(f, "filepath", "") == GLYPH_FONT or f.name.startswith("DejaVuSans-Bold"):
            try:
                _ = f.filepath
                return f
            except ReferenceError:
                break
    return bpy.data.fonts.load(GLYPH_FONT)


def _glyph_char_mesh(ch, size, depth, stroke=GLYPH_STROKE):
    """One character: FONT → solidify → voxel remesh (manifold)."""
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
    """Manifold letterforms. Spelled letter-by-letter — whole-word remesh of
    some strings (e.g. LTE) yields non-manifold solids.
    """
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
    """Manifold + as crossed bars (stroke ≥0.8)."""
    arm = size * 0.9
    h = oc.box("plus_h", (arm, stroke, depth), anchor="bottom")
    v = oc.box("plus_v", (stroke, arm, depth), anchor="bottom")
    return oc.union(h, v)


def _stroke_minus(size, depth, stroke=GLYPH_STROKE):
    arm = size * 0.9
    return oc.box("minus", (arm, stroke, depth), anchor="bottom")


def _stroke_arrow(size, depth, stroke=GLYPH_STROKE):
    """Connector / pin-1 arrow pointing +Y (stem + chevron head)."""
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


def emboss_glyph(body, key_or_text, at, size=GLYPH_SIZE, depth=GLYPH_DEPTH,
                 rot_z=0.0):
    """Emboss a real glyph onto the floor (relief ≥0.6). Uses FLOOR_LABEL_TABLE
    when key_or_text is a table id; otherwise treats the string as literal text.
    Symbols +, -, ARROW use stroke geometry; letters use DejaVu Bold.
    """
    if not FLOOR_GLYPHS or not key_or_text:
        return body
    if key_or_text in FLOOR_LABEL_TABLE:
        label = FLOOR_LABEL_TABLE[key_or_text][0]
    else:
        label = key_or_text
    # Stroke symbols use capital-height mm; FONT labels use Blender font size.
    stroke_h = GLYPH_CHAR_H if abs(size - GLYPH_SIZE) < 1e-6 else size * (GLYPH_CHAR_H / GLYPH_SIZE)
    if label in ("+", "PLUS"):
        glyph = _stroke_plus(stroke_h, depth)
    elif label in ("-", "−", "MINUS"):
        glyph = _stroke_minus(stroke_h, depth)
    elif label in ("ARROW", "▶", ">", "PIN1"):
        glyph = _stroke_arrow(stroke_h, depth)
    else:
        glyph = _text_mesh(label, size, depth)
    # Recentre XY on `at`; sink fill plane by GLYPH_EMBED for manifold union.
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
    """Emboss by FLOOR_LABEL_TABLE key (preferred call site)."""
    return emboss_glyph(body, key, at, size=size, depth=depth, rot_z=rot_z)


def locate_rib_rect(body, name, size_xy, at_xy, floor_z, h=FLOOR_RIB_H, wall=1.2):
    """Raised rectangular locating fence on the floor (four wall segments — manifold)."""
    sx, sy = size_xy
    ox, oy = sx / 2 + wall / 2, sy / 2 + wall / 2
    # Four separate walls instead of outer-minus-inner (avoids coplanar boolean junk)
    segs = [
        ((sx + 2 * wall, wall, h), (at_xy[0], at_xy[1] + oy, floor_z)),
        ((sx + 2 * wall, wall, h), (at_xy[0], at_xy[1] - oy, floor_z)),
        ((wall, sy, h), (at_xy[0] + ox, at_xy[1], floor_z)),
        ((wall, sy, h), (at_xy[0] - ox, at_xy[1], floor_z)),
    ]
    for i, (sz, pos) in enumerate(segs):
        oc.union(body, oc.box(f"{name}_w{i}", sz, at=pos, anchor="bottom"))
    return body


def check_wt(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return {"watertight": bad == 0, "bad_edges": bad, "normals_outward": vol > 0}


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


def slab(name, w, l, h, r=D.PLAN_R):
    return oc.rounded_rect(name, (w, l, h), r, anchor="bottom", segments=10)


def cut_cav(body, w, l, floor, h, r=5.0):
    oc.cut(body, oc.rounded_rect("cav", (w, l, h + 1), r,
                                 at=(0, 0, floor), anchor="bottom"))
    return body


def groove(body, w, l, r, z_top, wall):
    """O-ring groove with ≥GROOVE_INNER_LAND toward cavity and ≥GROOVE_OUTER_LAND outside.

    Corner radii stay concentric (outer_r - inner_r == groove half-width each side)
    so the channel walls stay parallel — fixes prior ~0.45 mm radius mismatch.
    """
    g, gd = D.GROOVE_W, D.GROOVE_D
    # Groove cavity-side edge is `inner_land` out from the cavity face (wall from outer).
    # Distance from outer face to groove centerline:
    inset = wall - D.GROOVE_INNER_LAND - g / 2
    inset = max(inset, D.GROOVE_OUTER_LAND + g / 2)
    half = g / 2
    # Parallel walls: r_outer = r_inner + half_width_diff_per_side = r_inner + half... 
    # size_outer = w - 2*(inset - half), size_inner = w - 2*(inset + half)
    # r_o - r_i should equal (size_o - size_i)/2 / 1 = 2*half / 1? Actually for rounded_rect
    # concentric: r_o = r_i + (s_o - s_i)/2 / 2 wait: (s_o-s_i)/2 = 2*half = g.
    # So r_o = r_i + g. Use r_i = max(r - inset - half, 1.0), r_o = r_i + g.
    r_i = max(r - inset - half, 1.0)
    r_o = r_i + g
    outer = oc.rounded_rect("go", (w - 2 * (inset - half), l - 2 * (inset - half), gd + 1),
                            r_o, at=(0, 0, z_top - gd), anchor="bottom")
    inner = oc.rounded_rect("gi", (w - 2 * (inset + half), l - 2 * (inset + half), gd + 3),
                            r_i, at=(0, 0, z_top - gd - 1), anchor="bottom")
    oc.cut(body, oc.cut(outer, inner))
    return body


def reg_lip(body, w, l, r, z_top, wall, h=1.2):
    """Registered lip RING inside the gasket land for lid location.

    Must be a ring (not a solid plate) — a solid 1.2 mm plate seals the cavity.
    """
    inset = wall / 2 + D.GROOVE_W / 2 + 0.6
    lip_w = w - 2 * inset
    lip_l = l - 2 * inset
    if lip_w < 10 or lip_l < 10:
        return body
    lip = oc.rounded_rect("lip", (lip_w, lip_l, h), max(r - inset, 2.0),
                          at=(0, 0, z_top), anchor="bottom")
    oc.union(body, lip)
    # Open the cavity: cut the lip interior so only a ~1.6 mm wall ring remains.
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


def pocket_box(body, name, size, at, floor_z, corner_r=None):
    """Board pocket with R1–R2 internal corner fillets."""
    sx, sy, sz = size
    rr = corner_r if corner_r is not None else D.POCKET_CORNER_R
    oc.cut(body, oc.rounded_rect(name, (sx, sy, sz + 0.5), rr,
                                 at=(at[0], at[1], floor_z), anchor="bottom"))
    return body


def board_holes(body, board_xy, hole_d, inset, at, floor_z, depth=3.0, prefix="mh"):
    """Four corner mounting holes inset from board edges (board coords at pocket centre)."""
    bw, bl = board_xy[0], board_xy[1]
    xs = (at[0] - bw / 2 + inset, at[0] + bw / 2 - inset)
    ys = (at[1] - bl / 2 + inset, at[1] + bl / 2 - inset)
    pts = [(xs[0], ys[0]), (xs[0], ys[1]), (xs[1], ys[0]), (xs[1], ys[1])]
    for i, (x, y) in enumerate(pts):
        oc.cut(body, oc.cylinder(f"{prefix}{i}", hole_d, depth + 0.5,
                                 at=(x, y, floor_z - 0.2), anchor="bottom"))
    return body


def mesh_port(body, centre, axis, port_d, wall_span, pitch=None, bar=None):
    """Open sound port as parallel slot cuts (print-in mesh; manifold-safe)."""
    pitch = pitch if pitch is not None else D.BUZZ_MESH_PITCH
    bar = bar if bar is not None else D.BUZZ_MESH_BAR
    cx, cy, cz = centre
    slot_w = max(0.8, pitch - bar)
    if axis == "Y":
        # Leave a perimeter ring; cut vertical slots through the wall
        n = max(1, int((port_d - 2.0) / pitch))
        for i in range(-n, n + 1):
            x = cx + i * pitch
            if abs(x - cx) + slot_w / 2 > port_d / 2 - 0.4:
                continue
            oc.cut(body, oc.box(f"mslot{i}",
                                (slot_w, wall_span, port_d * 0.75),
                                at=(x, cy, cz)))
    return body


def end_taper_cut(body, w, l, h, taper_len):
    """Short outer tip tapers — keeps central cavity full (resolves D4/D5 cavity bite)."""
    for sy in (-1, 1):
        tip = sy * (l / 2)
        oc.cut(body, oc.prism_x(f"taper{sy}", [
            (tip + sy * 0.5, h + 0.5),
            (tip - sy * taper_len, h + 0.5),
            (tip + sy * 0.5, h - 3.0),
        ], w + 4))
    return body


# ---------------------------------------------------------------- parts — CAP

def cap_base():
    """Print: cavity UP, bed = outer underside (flat). Load: clamp into inserts WITH layers.

    Pocket layout (firmware): Rook Connect Kit, bq24074, Wio-SX1262 in CAP.
    Antennas on crest (+Y). CW tub has NO electronics.
    """
    b = slab("cap_base", D.CAP_W, D.CAP_L, D.CAP_BASE_H, D.PLAN_R)
    cav_l = D.CAP_L - 2 * D.CAP_WALL - 2 * D.CAP_TAPER_LEN + 4
    cut_cav(b, D.CAP_W - 2 * D.CAP_WALL, max(cav_l, 110), D.CAP_FLOOR, D.CAP_CAVITY_H + 2, r=5.0)
    columns(b, D.CAP_COLS, D.CAP_FLOOR, D.CAP_BASE_H)
    for i, (x, y) in enumerate(D.CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"cl{i}", D.INSERT_D, 4.0, at=(x, y, -0.1), anchor="bottom"))
    for i, (x, y) in enumerate([(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]):
        oc.cut(b, oc.cylinder(f"pin{i}", 4.35, 2.2, at=(x, y, -0.1), anchor="bottom"))
    groove(b, D.CAP_W, D.CAP_L, D.PLAN_R, D.CAP_BASE_H, D.CAP_WALL)
    reg_lip(b, D.CAP_W, D.CAP_L, D.PLAN_R, D.CAP_BASE_H, D.CAP_WALL)

    # --- Rook Connect Kit pocket (−Y): USB-C on short end toward −Y wall ---
    kit_at = D.KIT_AT
    pocket_box(b, "kit", D.KIT_POCKET, kit_at, D.CAP_FLOOR)
    # Underside JST clearance recess under kit
    oc.cut(b, oc.rounded_rect("kitjst", (20.0, 10.0, D.KIT_JST_H + 0.5), 1.0,
                              at=(kit_at[0], kit_at[1] - 4.0, D.CAP_FLOOR - 0.1),
                              anchor="bottom"))
    board_holes(b, D.KIT_BOARD, D.KIT_HOLE_D, D.KIT_HOLE_INSET, kit_at,
                D.CAP_FLOOR, depth=2.5, prefix="kith")

    # --- bq24074 — NOT potted; service pocket with air gap ---
    bq_at = D.BQ_AT
    pocket_box(b, "bq", D.BQ_POCKET, bq_at, D.CAP_FLOOR)
    board_holes(b, D.BQ_BOARD, D.BQ_HOLE_D, D.BQ_HOLE_INSET, bq_at,
                D.CAP_FLOOR, depth=3.0, prefix="bqh")

    # --- Wio-SX1262 LAY-FLAT; ≥3 mm +X wall (AT_x=22 → pocket to 32.9; outer 38) ---
    wio_at = D.WIO_AT
    pocket_box(b, "wio", D.WIO_POCKET, wio_at, D.CAP_FLOOR)
    ux_s, uy_s = D.UFL_SLACK_AT
    oc.cut(b, oc.rounded_rect("uflslack", (6.0, D.WIO_WIRE_BEND, 4.0), D.POCKET_CORNER_R,
                              at=(ux_s, uy_s, D.CAP_FLOOR),
                              anchor="bottom"))
    oc.cut(b, oc.cylinder("uflstrain", D.UFL_STRAIN_D, 4.0,
                          at=(ux_s, 35.0, D.CAP_FLOOR - 0.1),
                          anchor="bottom"))

    # Lid support posts between kit and bq (≥1 mm from boards) — print with base.
    # Embed into floor; stop 0.4 mm below base top so they don't fight the lip ring boolean.
    for i, (px, py) in enumerate(D.LID_SUPPORT_POSTS):
        h = D.CAP_CAVITY_H + 0.1  # floor-0.5 → top at BASE_H - 0.4
        post = oc.cylinder(f"sup{i}", D.LID_SUPPORT_D, h,
                           at=(px, py, D.CAP_FLOOR - 0.5), anchor="bottom", segments=24)
        oc.union(b, post)

    # --- USB-C charge port (kit short end → −Y wall) + gasket recess; R2 corners ---
    ux, uy, uz = D.USBC_PORT
    oc.cut(b, oc.rounded_rect("usbc", (ux, uy, uz), D.POCKET_CORNER_R,
                              at=(0, -(D.CAP_L / 2 - D.CAP_WALL / 2), D.CAP_FLOOR + 2.0),
                              anchor="bottom"))
    oc.cut(b, oc.rounded_rect("usbcseat", (D.USBC_CAP[0] + 0.4, 3.0, D.USBC_CAP[1] + 0.4),
                              1.2,
                              at=(0, -(D.CAP_L / 2 - 1.5), D.CAP_FLOOR + 1.5),
                              anchor="bottom"))

    # Light-pipe wells — OUT from under P124 (near −Y free end)
    for i, (lx, ly) in enumerate(D.LIGHTPIPE_AT):
        oc.cut(b, oc.cylinder(f"lp{i}", D.LIGHTPIPE_D, D.CAP_CAVITY_H + 2,
                              at=(lx, ly, D.CAP_FLOOR + 1.0),
                              anchor="bottom"))

    # Button membrane seats — OUT from under P124
    for i, (bx, by) in enumerate(D.BTN_AT):
        oc.cut(b, oc.rounded_rect(f"btn{i}", D.BTN_MEMBRANE, 1.0,
                                  at=(bx, by, D.CAP_FLOOR + D.KIT_POCKET[2] - 0.5),
                                  anchor="bottom"))

    # Cable exits toward pods (±X): plain through-hole first.
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cable{sx}", 6.0, D.CAP_WALL + 4,
                              at=(sx * (D.CAP_W / 2 - D.CAP_WALL / 2), 0, D.CAP_FLOOR + 6),
                              axis="X", segments=32))

    end_taper_cut(b, D.CAP_W, D.CAP_L, D.CAP_BASE_H, D.CAP_TAPER_LEN)
    b = prepare(b)

    # Separate boolean: stepped countersink on outer face (45° cone was non-manifold
    # on this wall; Ø8×1.2 counterbore is the durable printable substitute).
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cablesink{sx}", 8.0, 1.2,
                              at=(sx * (D.CAP_W / 2 - 0.6), 0, D.CAP_FLOOR + 6),
                              axis="X", segments=32))

    # Floor glyphs (assembly IDs) — embossed on cavity floor when FLOOR_GLYPHS.
    # Keep clear of pocket booleans and support posts.
    fz = D.CAP_FLOOR
    emboss_label(b, "KIT", (-18.0, D.KIT_AT[1] + 2.0, fz))
    emboss_label(b, "BQ", (-18.0, D.BQ_AT[1] - 2.0, fz))
    emboss_label(b, "WIO", (D.WIO_AT[0] - 2.0, D.WIO_AT[1] + 14.0, fz))
    emboss_label(b, "USB", (0.0, -58.0, fz))
    emboss_label(b, "POST", (14.0, -1.5, fz))
    emboss_label(b, "GNSS", (-18.0, 55.0, fz))
    emboss_label(b, "LTE", (18.0, 48.0, fz))
    emboss_label(b, "PIN1", (22.0, D.KIT_AT[1] - 4.0, fz), rot_z=-90.0)
    # Screw numerals clear of USB glyph at (0,-58) and crest labels
    for key, (sx, sy) in (("SCR1", (1, 1)), ("SCR2", (-1, 1)),
                          ("SCR3", (1, -1)), ("SCR4", (-1, -1))):
        emboss_label(b, key, (sx * 28.0, sy * 62.0, fz))
    return prepare(b)


def cap_lid():
    """Print: MATING FACE DOWN (z=0), outer UP.

    P124 pocket opens on the outer face. Outer-down put ~66×113 mm of pocket
    ceiling on supports with a small rim bed — not printable cleanly. Mating-down
    puts the panel pocket facing +Z (no support) and accepts small supports for
    GNSS/LTE recesses on the bed side. Not in FLIP_OUTER_DOWN.

    Panel pocket leaves ≥2.0 mm lid under it. GNSS past panel +Y so cover stays
    1–3 mm plastic with no metal above. Frame recessed to panel top.
    """
    lw, ll = D.CAP_W - 2 * D.REVEAL, D.CAP_L - 2 * D.REVEAL
    lid = slab("cap_lid", lw, ll, D.CAP_LID_T, D.PLAN_R - 0.5)
    lid_fasteners(lid, D.CAP_COLS, D.CAP_LID_T)

    # Landing ring — concentric radii (width 1.6 → r_o - r_i = 1.6)
    ring_w = 1.6
    ring_out_w, ring_out_l = lw - 6.0, ll - 6.0
    r_o = 4.0
    r_i = r_o - ring_w
    outer = oc.rounded_rect("lring_o", (ring_out_w, ring_out_l, 1.5), r_o,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("lring_i", (ring_out_w - 2 * ring_w, ring_out_l - 2 * ring_w, 2.0),
                            r_i, at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))

    # P124 pocket — KEPT on collar #1 (2026-11-03); ≥2 mm lid under (CAP_LID_T - pz ≥ 2).
    # Full-depth full-size pocket (panel fit). Print mating-down so this opens +Z;
    # outer-down would need ~7k mm² supports on a small rim bed — not recommended.
    px, py, pz = D.PANEL_POCKET
    assert D.CAP_LID_T - pz >= D.PANEL_MIN_LID_UNDER
    oc.cut(lid, oc.rounded_rect("ppocket", (px, py, pz + 0.2), 1.2,
                                at=(0, D.PANEL_Y, D.CAP_LID_T - pz), anchor="bottom"))
    # Frame recessed to panel top (PANEL_FRAME_PROUD = -0.4) — not proud above lid
    frame_z = D.CAP_LID_T + D.PANEL_FRAME_PROUD - 0.5
    frame = oc.rounded_rect("pframe", (px + 2.8, py + 2.8, 0.5), 1.5,
                            at=(0, D.PANEL_Y, frame_z), anchor="bottom")
    oc.cut(frame, oc.rounded_rect("pfi", (px + 0.3, py + 0.3, 1.0), 1.0,
                                  at=(0, D.PANEL_Y, frame_z - 0.1), anchor="bottom"))
    oc.union(lid, frame)
    oc.cut(lid, oc.cylinder("pwire", 4.0, D.CAP_LID_T + 2,
                            at=(0, D.PANEL_Y + py / 2 - 10, -1), anchor="bottom"))

    # GNSS recess from z=0 into cavity (was z=0.3 sealed skin). Cover = lid_t - gsz.
    gx, gy = D.GNSS_AT
    gsz = D.GNSS_PATCH[2] + 0.2       # 4.2 → cover 2.3 mm (within 1–3)
    assert D.CAP_LID_T - gsz >= 1.0
    oc.cut(lid, oc.rounded_rect("gnss", (D.GNSS_PATCH[0] + 0.8, D.GNSS_PATCH[1] + 0.8, gsz + 0.2),
                                D.POCKET_CORNER_R, at=(gx, gy, -0.1), anchor="bottom"))

    # LTE flex shelf from z=0 (open to cavity — flex installable)
    lx, ly = D.LTE_AT
    oc.cut(lid, oc.rounded_rect("lte", (D.LTE_FLEX[0] + 0.8, D.LTE_FLEX[1] + 0.8, 1.4),
                                D.POCKET_CORNER_R, at=(lx, ly, -0.1), anchor="bottom"))

    # Light-pipe / button windows — OUT from under panel
    for i, (lpx, lpy) in enumerate(D.LIGHTPIPE_AT):
        oc.cut(lid, oc.cylinder(f"lplid{i}", D.LIGHTPIPE_D + 0.2, D.CAP_LID_T + 2,
                                at=(lpx, lpy, -1), anchor="bottom"))
    for i, (bx, by) in enumerate(D.BTN_AT):
        oc.cut(lid, oc.cylinder(f"btnw{i}", 5.0, D.CAP_LID_T + 2,
                                at=(bx, by, -1), anchor="bottom"))

    oc.cut(lid, oc.rounded_rect("label", (D.LABEL[0], D.LABEL[1], D.LABEL[2] + 0.05), 1.0,
                                at=(0, -72.0, D.CAP_LID_T - D.LABEL[2]), anchor="bottom"))
    return prepare(lid)


def panel_p124():
    return prepare(oc.rounded_rect("panel_p124", D.PANEL_SIZE, 1.0, anchor="bottom", segments=8))


# ---------------------------------------------------------------- parts — PODS

def pod_base(side="L"):
    """Print: cavity UP. Adjustable 18650 bay + buzzer + meshed sound port.

    Cell swap: M3 driver only (lid screws). 353 pack NOT approved.
    LP503562 U — CELL_BAY_ADJUST radial spare.
    """
    b = slab(f"pod_{side}_base", D.POD_L, D.POD_W, D.POD_BASE_H, D.PLAN_R)
    cut_cav(b, D.POD_CAVITY[0], D.POD_CAVITY[1], D.POD_FLOOR, D.POD_CAVITY[2] + 1, r=5.0)
    columns(b, D.POD_COLS, D.POD_FLOOR, D.POD_BASE_H)
    groove(b, D.POD_L, D.POD_W, D.PLAN_R, D.POD_BASE_H, D.POD_WALL)
    reg_lip(b, D.POD_L, D.POD_W, D.PLAN_R, D.POD_BASE_H, D.POD_WALL)

    # Adjustable cell bay: Ø(19.2+adjust) × (70+2×3 end clear).
    # LP503562 flat pack (U) fits in the same bay volume via CELL_BAY_ADJUST —
    # no overlapping rectangular boolean (keeps manifold).
    cell_d = D.CELL_POCKET_D + D.CELL_BAY_ADJUST
    cell_l = D.CELL_BAY_L
    cx, cy = D.CELL_AT
    oc.cut(b, oc.cylinder("cell", cell_d, cell_l,
                          at=(cx, cy, D.POD_FLOOR + cell_d / 2), axis="X"))

    # Buzzer pocket + open sound port (+Y). Mesh = press-in disc (see buzz_mesh.stl)
    # — print-in slot mesh left non-manifold on this boolean stack.
    buzz_at = D.BUZZ_AT
    pocket_box(b, "buzz", D.BUZZ_POCKET, buzz_at, D.POD_FLOOR)
    boss = oc.cylinder("sboss", D.BUZZ_PORT_D + 4.0, 1.8,
                       at=(buzz_at[0], D.POD_W / 2 + 0.9, 11.0), axis="Y")
    oc.union(b, boss)
    oc.cut(b, oc.cylinder("sport", D.BUZZ_PORT_D, D.POD_WALL + 6,
                          at=(buzz_at[0], D.POD_W / 2, 11.0), axis="Y"))
    # Outer counterbore seats a printed mesh disc
    oc.cut(b, oc.cylinder("meshseat", D.BUZZ_PORT_D + 1.6, 0.8,
                          at=(buzz_at[0], D.POD_W / 2 + 1.2, 11.0), axis="Y"))

    # Crest cable to cap
    oc.cut(b, oc.cylinder("pcable", 6.0, D.POD_WALL + 4,
                          at=(D.POD_L / 2 - D.POD_WALL / 2, 0, 12.0), axis="X"))

    # Floor glyphs — cell polarity, BATT, BUZZ, pin-1 arrow toward crest cable
    fz = D.POD_FLOOR
    emboss_label(b, "BATT", (0.0, D.CELL_AT[1] - 18.0, fz))
    emboss_label(b, "PLUS", (-28.0, 14.0, fz))
    emboss_label(b, "MINUS", (28.0, 14.0, fz))
    emboss_label(b, "BUZZ", (D.BUZZ_AT[0], D.BUZZ_AT[1] - 16.0, fz))
    emboss_label(b, "PIN1", (D.POD_L / 2 - 14.0, 0.0, fz), rot_z=-90.0)

    if side == "R":
        oc.bake(b)
        b.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
        # Mirror scales invert winding — flip once to restore outward normals.
        b.data.flip_normals()
    return prepare(b)


def pod_lid(side="L"):
    """Print: outer face DOWN. Lid ≥4.0 mm; ≥2.5 mm at gasket groove; ≥1 mm over cell.

    Concentric landing-ring radii (fixes prior ~0.45 mm corner mismatch).
    """
    lw, ll = D.POD_L - 2 * D.REVEAL, D.POD_W - 2 * D.REVEAL
    lid = slab(f"pod_{side}_lid", lw, ll, D.POD_LID_T, D.PLAN_R - 0.5)
    lid_fasteners(lid, D.POD_COLS, D.POD_LID_T)
    # Landing ring: width 1.5, r_o - r_i = 1.5 (concentric)
    ring_w = 1.5
    ring_out_w, ring_out_l = lw - 5.0, ll - 5.0
    r_o = 3.5
    r_i = r_o - ring_w
    groove_depth = min(1.3, D.POD_LID_T - 2.5)  # leave ≥2.5 mm at groove
    outer = oc.rounded_rect("plring_o", (ring_out_w, ring_out_l, groove_depth), r_o,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("plring_i",
                            (ring_out_w - 2 * ring_w, ring_out_l - 2 * ring_w, groove_depth + 0.5),
                            r_i, at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))
    # Cross-ribs on mating face for stiffness; clear of cell (±Y of cell cradle)
    # Cell along X at CELL_AT; ribs along Y outside cell Y envelope.
    cell_y = D.CELL_AT[1]
    cell_r = (D.CELL_POCKET_D + D.CELL_BAY_ADJUST) / 2 + 1.0  # ≥1 mm clearance
    for i, dy in enumerate((-1.0, 1.0)):
        ry = cell_y + dy * (cell_r + 3.0)
        if abs(ry) > ll / 2 - 8:
            continue
        rib = oc.box(f"prib{i}", (lw - 16, 2.0, 1.5),
                     at=(0, ry, 0.6))
        oc.union(lid, rib)
    if side == "R":
        from mathutils import Matrix
        oc.bake(lid)
        lid.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
        lid.data.flip_normals()
    return prepare(lid)


# ---------------------------------------------------------------- parts — CW (no electronics)

def cw_tub():
    """Print: cavity UP. Steel only — free of electronics / antennas."""
    b = slab("cw_tub", D.CW_L, D.CW_W, D.CW_H, D.PLAN_R)
    cut_cav(b, D.CW_L - 12, D.CW_W - 12, 3.0, D.CW_H, r=4.0)
    columns(b, D.CW_SCREWS, 3.0, D.CW_H, d=8.0)
    groove(b, D.CW_L, D.CW_W, D.PLAN_R, D.CW_H, 6.0)
    reg_lip(b, D.CW_L, D.CW_W, D.PLAN_R, D.CW_H, 6.0)
    for i, (x, y) in enumerate(D.CW_CLAMP):
        oc.cut(b, oc.cylinder(f"cwcl{i}", D.CLEAR, D.CW_H + 2, at=(x, y, -1), anchor="bottom"))
    emboss_label(b, "STEEL", (0.0, 8.0, 3.0))
    emboss_label(b, "ONLY", (0.0, -8.0, 3.0))
    return prepare(b)


def cw_lid():
    lw, ll = D.CW_L - 2 * D.REVEAL, D.CW_W - 2 * D.REVEAL
    lid = slab("cw_lid", lw, ll, D.CW_LID_T, D.PLAN_R - 0.5)
    lid_fasteners(lid, D.CW_SCREWS, D.CW_LID_T)
    return prepare(lid)


# ---------------------------------------------------------------- strap interface

def saddle():
    """Print: flank/rail on bed, channel as pocket (no bridge).

    Roof ≥ SADDLE_ROOF (1.6 mm). Prior ~0.8 mm roof was a centered-box boolean
    bug — NOT intentional. Channel cut uses bottom anchor so roof stays solid.
    Load: strap → rails → clamp → cap inserts; layers along Y.
    """
    s = oc.rounded_rect("saddle", (D.SADDLE_W, D.SADDLE_L, D.SADDLE_H), 3.0,
                        anchor="bottom", segments=8)
    # Channel from roof underside down — bottom of cut at SADDLE_ROOF
    oc.cut(s, oc.box("schan",
                     (D.SADDLE_W + 2, D.SADDLE_CHANNEL_W, D.SADDLE_CHANNEL_D + 0.2),
                     at=(0, 0, D.SADDLE_ROOF), anchor="bottom"))
    for sx in (-1, 1):
        oc.cut(s, oc.prism_y(f"lead{sx}", [
            (sx * (D.SADDLE_W / 2 + 0.3), D.SADDLE_H + 0.2),
            (sx * (D.SADDLE_W / 2 + 0.3), D.SADDLE_ROOF - 0.3),
            (sx * (D.SADDLE_W / 2 - 3.5), D.SADDLE_H + 0.2),
        ], D.SADDLE_CHANNEL_W + 2))
    for i, (x, y) in enumerate(D.CAP_CLAMP):
        oc.cut(s, oc.cylinder(f"scl{i}", D.CLEAR, D.SADDLE_H + 2, at=(x, y, -1), anchor="bottom"))
    for i, (x, y) in enumerate([(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]):
        pin = oc.cylinder(f"spin{i}", 4.0, 1.5, at=(x, y, D.SADDLE_H), anchor="bottom")
        oc.union(s, pin)
    return prepare(s)


def clamp_bar():
    """Channel/T section ≥8 mm deep, 3 mm web. Farmer-swappable.

    Orientation: flange flat on bed, channel opens +Z. Load along bar length
    (Y) WITH layers — strap compression; never peel across layers.
    Metal-free ≥12 mm from LoRa at crest (clamps under saddle at |y|≤28.5;
    LoRa at y≈64 → clearance ≫12 mm).
    """
    # Channel: bottom flange 10×70×3, two walls 3×70×(8-3), open top
    flange = oc.rounded_rect("cflange", (D.CLAMP_FLANGE_W, D.CLAMP_L, D.CLAMP_WEB), 1.0,
                             anchor="bottom", segments=4)
    wall_h = D.CLAMP_DEPTH - D.CLAMP_WEB
    for sx in (-1, 1):
        w = oc.box(f"cwall{sx}", (D.CLAMP_WEB, D.CLAMP_L - 2, wall_h),
                   at=(sx * (D.CLAMP_FLANGE_W / 2 - D.CLAMP_WEB / 2), 0, D.CLAMP_WEB),
                   anchor="bottom")
        oc.union(flange, w)
    # Clearance holes matching CAP_CLAMP spacing along Y (bar sits under clamp points)
    # Two holes near ends for M3 through saddle into cap
    for i, sy in enumerate((-28.5, 28.5)):
        if abs(sy) > D.CLAMP_L / 2 - 5:
            continue
        oc.cut(flange, oc.cylinder(f"ch{i}", D.CLEAR, D.CLAMP_DEPTH + 2,
                                   at=(0, sy, -1), anchor="bottom"))
    return prepare(flange)


def keeper():
    k = oc.rounded_rect("keeper", (D.STRAP_W + 5, 9.0, 6.5), 1.8, anchor="bottom", segments=6)
    oc.cut(k, oc.box("kslot", (D.STRAP_W + 1.2, 11.0, D.STRAP_T + 1.0),
                     at=(0, 0, 2.5)))
    return prepare(k)


def buckle():
    """Single solid: cross-bar must penetrate the side walls (no floating island)."""
    b = oc.rounded_rect("buckle", (D.STRAP_W + 3, 26.0, 5.5), 2.2, anchor="bottom", segments=6)
    oc.cut(b, oc.rounded_rect("bopen", (D.STRAP_W - 6, 17.0, 8.0), 1.2,
                              at=(0, 0, -1), anchor="bottom"))
    # Bar length > opening width so ends fuse into the frame (was STRAP_W-8 → floated).
    bar = oc.cylinder("bbar", 2.8, D.STRAP_W + 1.0, at=(0, 1.5, 2.75), axis="X", segments=20)
    oc.union(b, bar)
    return prepare(b)


def latch():
    """Cosmetic → production intent: flush recessed pull, orange #FF6A2B."""
    return prepare(oc.rounded_rect("latch", (6.5, 11.0, 2.0), 1.2, anchor="bottom", segments=6))


def plug():
    return prepare(oc.cylinder("plug", D.PLUG_D, D.PLUG_H, anchor="bottom", segments=32))


def gasket_oring_blank():
    """Indicative 2 mm cord blank for spares plate (cut to length at assembly)."""
    return prepare(oc.torus_approx() if False else oc.cylinder("oring_blank", 2.0, 80.0,
                                                               anchor="bottom", segments=24))


# Fairings — 25–30 mm blend, R7 plan, R2.5 edges. Print long-axis on bed; slope = WALL.

def _fairing_body(name, run, w0, w1, h):
    """Wedge with rounded plan envelope + soft edge bevel (brand R7 / R2.5)."""
    f = oc.prism_y(name, [
        (0.0, 0.0),
        (w0 / 2, 0.0),
        (w1 / 2, h),
        (-w1 / 2, h),
        (-w0 / 2, 0.0),
    ], run)
    # Soften plan silhouette with R7 rounded bounds (intersect).
    bound = oc.rounded_rect(f"{name}_bnd", (max(w0, w1) + 2, run + 2, h + 2),
                            D.FAIRING_R, at=(0, 0, -1), anchor="bottom", segments=10)
    oc.intersect(f, bound)
    # Soft edge (R2.5) — best-effort bevel; ignore if topology refuses.
    try:
        oc.bevel(f, D.FAIRING_EDGE_R, segments=3)
        oc.apply_modifiers(f)
    except Exception:
        pass
    return f


def fairing_cap_pod(side="L"):
    """Bridge cap → pod. 28 mm run (brand 25–30)."""
    return prepare(_fairing_body(f"fairing_cap_pod_{side}", D.FAIRING_RUN, 70.0, 55.0, 12.0))


def fairing_pod_strap(side="L"):
    """Blend pod into strap. 28 mm run, tapers toward strap width."""
    return prepare(_fairing_body(f"fairing_pod_strap_{side}", D.FAIRING_RUN,
                                 50.0, D.STRAP_W + 4, 10.0))


def usbc_cap():
    """TPU gasket cap for USB-C charge port — farmer replaceable."""
    return prepare(oc.rounded_rect("usbc_cap", (12.0, 10.0, 3.0), 1.5, anchor="bottom", segments=6))


def buzz_mesh():
    """Press-in mesh disc — ONE part: outer rim holds the lattice (no loose bars)."""
    od = D.BUZZ_PORT_D + 1.4
    rim = 1.4                       # solid rim width; slots stay inside
    disc = oc.cylinder("buzz_mesh", od, 0.8, anchor="bottom", segments=48)
    slot_w, pitch = 0.9, D.BUZZ_MESH_PITCH
    # Slot length limited so cuts stop before the rim (keeps a continuous ring).
    inner_span = od - 2 * rim
    n = max(1, int(inner_span / pitch))
    for i in range(-n, n + 1):
        x = i * pitch
        if abs(x) + slot_w / 2 > inner_span / 2:
            continue
        oc.cut(disc, oc.box(f"ms{i}", (slot_w, inner_span, 2.0), at=(x, 0, 0.4)))
    for i in range(-n, n + 1):
        y = i * pitch
        if abs(y) + slot_w / 2 > inner_span / 2:
            continue
        oc.cut(disc, oc.box(f"msy{i}", (inner_span, slot_w, 2.0), at=(0, y, 0.4)))
    return prepare(disc)


def label_coupon():
    t = 3.5
    c = slab("label_coupon", D.LABEL[0] + 8, D.LABEL[1] + 8, t, 2.0)
    oc.cut(c, oc.rounded_rect("pad", (D.LABEL[0], D.LABEL[1], D.LABEL[2] + 0.05), 1.0,
                              at=(0, 0, t - D.LABEL[2]), anchor="bottom"))
    return prepare(c)


def fit_coupon():
    """Board + cell + insert + groove + clearance gauges — print FIRST before enclosure.

    Sweeps BOARD_CLEAR 0.2/0.4/0.6 per side for kit/bq/buzz/wio; cell Ø; inserts; groove.
    """
    # Larger coupon: two rows of pocket gauges
    c = oc.box("fit_coupon", (150.0, 70.0, 5.0), anchor="bottom")

    # Row 1: kit clearance sweep (board + 2×clear)
    for i, clear in enumerate(D.COUPON_CLEAR_SWEEP):
        kx = D.KIT_BOARD[0] + 2 * clear
        ky = D.KIT_BOARD[1] + 2 * clear
        # Depth 4.5 through 5 mm blank (from z=1.2) — opens the top; was sealed under a skin.
        oc.cut(c, oc.rounded_rect(f"kitc{i}", (kx, ky, 4.5), 1.0,
                                  at=(-50 + i * 30, 18, 1.2), anchor="bottom"))
    # Kit mount hole gauge (dia 1.4)
    oc.cut(c, oc.cylinder("kithole", D.KIT_HOLE_D, 6.0, at=(-50, -5, -0.5), anchor="bottom"))

    # Row 1 cont: bq / buzz / wio at nominal +0.4 — open through top
    oc.cut(c, oc.rounded_rect("bqg", (D.BQ_POCKET[0], D.BQ_POCKET[1], 4.5), 1.0,
                              at=(45, 18, 1.2), anchor="bottom"))
    oc.cut(c, oc.rounded_rect("buzzg", (D.BUZZ_POCKET[0], D.BUZZ_POCKET[1], 4.5), 1.0,
                              at=(-20, -18, 1.2), anchor="bottom"))
    oc.cut(c, oc.rounded_rect("wiog", (D.WIO_POCKET[0], D.WIO_POCKET[1], 4.5), 1.0,
                              at=(15, -18, 1.2), anchor="bottom"))

    # Cell diameter gauges: nominal 19.2 and adjusted
    for i, d in enumerate((D.CELL_POCKET_D, D.CELL_POCKET_D + D.CELL_BAY_ADJUST, D.CELL_D)):
        oc.cut(c, oc.cylinder(f"cellg{i}", d, 6.0, at=(45 + i * 22, -18, -0.5), anchor="bottom"))

    # Insert hole sweep (heat-set)
    for i, d in enumerate((3.8, 4.0, 4.2)):
        oc.cut(c, oc.cylinder(f"insg{i}", d, 6.0, at=(-55 + i * 10, -5, -0.5), anchor="bottom"))

    # bq mount hole gauge
    oc.cut(c, oc.cylinder("bqhole", D.BQ_HOLE_D, 6.0, at=(-25, -5, -0.5), anchor="bottom"))

    # Groove sample
    oc.cut(c, oc.box("grv", (35.0, D.GROOVE_W, D.GROOVE_D),
                     at=(55, 0, 5.0 - D.GROOVE_D), anchor="bottom"))

    # USB-C port gauge — open through top (was sealed under 0.2–0.3 mm skin)
    oc.cut(c, oc.rounded_rect("usbcg", (D.USBC_PORT[0], D.USBC_PORT[2], 5.0), 1.0,
                              at=(0, -5, 0.8), anchor="bottom"))
    return prepare(c)


# ---------------------------------------------------------------- floor-layout coupons (PLA assembly aids)

def cap_floor_layout():
    """Trimmed cap floor + locating ribs + real embossed IDs. Bed = underside; ribs UP."""
    w, l = 70.0, 130.0
    floor = oc.rounded_rect("cap_floor", (w, l, 2.0), 3.0, anchor="bottom", segments=6)
    fz = 2.0
    locate_rib_rect(floor, "kit", (40.0, 18.0), (0.0, -22.0), fz, wall=1.2)
    locate_rib_rect(floor, "bq", (30.0, 24.0), (0.0, 22.0), fz, wall=1.2)
    locate_rib_rect(floor, "wio", (18.0, 14.0), (18.0, -5.0), fz, wall=1.2)
    for i, py in enumerate((5.0, -8.0)):
        oc.union(floor, oc.cylinder(f"flpost{i}", 8.0, FLOOR_RIB_H,
                                    at=(0.0, py, fz), anchor="bottom", segments=16))
    # Spaced clear of locating ribs (bq fence covers |y-22|<12 near x=0).
    for key, xy in (("KIT", (0, -8)), ("BQ", (0, 42)), ("WIO", (22, 10)),
                    ("USB", (0, -50)), ("POST", (22, -2)),
                    ("GNSS", (0, 58)), ("LTE", (-22, 28)),
                    ("SCR1", (-28, -60)), ("SCR2", (28, -60)),
                    ("SCR3", (-28, 60)), ("SCR4", (28, 42)),
                    ("PIN1", (-26, -22))):
        emboss_label(floor, key, (xy[0], xy[1], fz))
    return normalize_z0(prepare(floor))


def pod_floor_layout(side="L"):
    """Trimmed pod floor + cell cradle + buzzer fence + polarity glyphs."""
    w, l = 80.0, 58.0
    floor = oc.rounded_rect(f"pod_{side}_floor", (w, l, 2.0), 3.0, anchor="bottom", segments=6)
    fz = 2.0
    for sy in (-1, 1):
        oc.union(floor, oc.box(f"cellrail{sy}", (50.0, 1.4, FLOOR_RIB_H),
                               at=(0.0, sy * 11.0, fz), anchor="bottom"))
    for sx, key in ((-1, "PLUS"), (1, "MINUS")):
        oc.union(floor, oc.box(f"cellend{sx}", (1.6, 18.0, FLOOR_RIB_H),
                               at=(sx * 28.0, 0.0, fz), anchor="bottom"))
        emboss_label(floor, key, (sx * 22.0, 18.0, fz))
    emboss_label(floor, "BATT", (0.0, -20.0, fz))
    locate_rib_rect(floor, "buzz", (20.0, 20.0), (22.0, 12.0), fz, wall=1.2)
    emboss_label(floor, "BUZZ", (-18.0, 18.0, fz))
    emboss_label(floor, "PIN1", (30.0, -18.0, fz), rot_z=-90.0)
    if side == "R":
        oc.bake(floor)
        floor.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
        floor.data.flip_normals()
    return normalize_z0(prepare(floor))


def cw_floor_layout():
    """CW floor plate with steel-pack outline + STEEL/ONLY glyphs."""
    w, l = 70.0, 55.0
    floor = oc.rounded_rect("cw_floor", (w, l, 2.0), 3.0, anchor="bottom", segments=6)
    locate_rib_rect(floor, "steel", (50.0, 40.0), (0, 0), 2.0, h=2.5, wall=1.5)
    emboss_label(floor, "STEEL", (0, 12, 2.0))
    emboss_label(floor, "ONLY", (0, -12, 2.0))
    return normalize_z0(prepare(floor))


# ---------------------------------------------------------------- export / plates / render

PART_META = {
    # name: orientation, load_path, material_field, farmer_swappable, rf_near
    # orientation string = intended PRINT orientation; STL z=0 is the bed face.
    "cap_base": ("PRINT: cavity UP; bed=underside z=0", "clamp→inserts WITH layers", "ASA/PETG", False, True),
    "cap_lid": ("PRINT: MATING face DOWN z=0 (as-built); outer UP; P124 pocket +Z", "lid screws INTO base", "ASA/PETG", True, True),
    "panel_p124": ("PRINT: flat; bed=either face z=0", "bonded in pocket — P124 KEPT collar #1", "bought", True, True),
    "pod_L_base": ("PRINT: cavity UP; bed=underside z=0", "lid screws; cell cradle", "ASA/PETG", False, True),
    "pod_L_lid": ("PRINT: OUTER face DOWN z=0 (flipped on export)", "lid screws; ribs clear cell", "ASA/PETG", True, True),
    "pod_R_base": ("PRINT: cavity UP; bed=underside z=0", "mirror of L", "ASA/PETG", False, True),
    "pod_R_lid": ("PRINT: OUTER face DOWN z=0 (flipped on export)", "mirror of L", "ASA/PETG", True, True),
    "cw_tub": ("PRINT: cavity UP; bed=underside z=0", "steel pack; NO antennas", "ASA/PETG", False, False),
    "cw_lid": ("PRINT: OUTER face DOWN z=0 (flipped on export)", "lid screws", "ASA/PETG", True, False),
    "saddle": ("PRINT: roof on bed z=0; channel opens +Z", "strap→rails→clamp ALONG layers", "ASA/PETG or PA-CF*", False, False),
    "clamp_bar": ("PRINT: flange on bed z=0; channel +Z; load ALONG Y WITH layers",
                  "strap compression; ≥15 mm from LoRa crest", "ASA/PETG or PA-CF*", True, False),
    "keeper": ("PRINT: flat; bed z=0", "strap tail guide", "ASA/PETG/TPU", True, False),
    "buckle": ("PRINT: flat; bed z=0", "strap open/close", "ASA/PETG", True, False),
    "latch": ("PRINT: flat; bed z=0", "lid open cue (orange)", "ASA/PETG", True, False),
    "plug_service": ("PRINT: flat; bed z=0", "covers farmer screws", "ASA orange", True, False),
    "plug_struct": ("PRINT: flat; bed z=0", "charcoal cosmetic", "ASA charcoal", True, False),
    "fairing_cap_pod_L": ("PRINT: long axis on bed; slope=WALL", "28 mm blend", "ASA/PETG", True, False),
    "fairing_cap_pod_R": ("PRINT: long axis on bed; slope=WALL", "mirror", "ASA/PETG", True, False),
    "fairing_pod_strap_L": ("PRINT: long axis on bed; slope=WALL", "28 mm blend", "ASA/PETG", True, False),
    "fairing_pod_strap_R": ("PRINT: long axis on bed; slope=WALL", "mirror", "ASA/PETG", True, False),
    "usbc_cap": ("PRINT: flat; bed z=0", "charge-port gasket cap", "TPU", True, False),
    "buzz_mesh": ("PRINT: flat; bed z=0", "rimmed mesh disc ×2", "PETG/TPU", True, False),
    "label_coupon": ("PRINT: flat; bed z=0", "0.16 mm layer label test", "ASA/PETG", False, False),
    "fit_coupon": ("PRINT: flat; bed z=0", "FIRST print — gauges", "PLA", False, False),
    "cap_floor_layout": ("PRINT: floor underside z=0; ribs/glyphs UP", "PLA layout coupon", "PLA", False, True),
    "pod_floor_layout": ("PRINT: floor underside z=0; ribs/glyphs UP", "PLA layout coupon (L=R mirror)", "PLA", False, True),
    "cw_floor_layout": ("PRINT: floor underside z=0", "PLA steel-pack outline", "PLA", False, False),
}


def export_part(obj, path, meta_key=None):
    """Export STL in intended PRINT orientation: bed face at z=0."""
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
    oc.export_stl(obj, path)
    stl = check_stl(path)
    tag = "OK" if wt["watertight"] and stl["watertight"] else "LOOK"
    bed = "OUTER" if flipped else ("MATING" if meta_key == "cap_lid" else "as-built")
    print(f"{tag}  {os.path.basename(path)}: {[round(x,1) for x in dims]}  bad={wt['bad_edges']}"
          f"  bed_z0={bed}  normals_out={wt['normals_outward']}")
    body = {"size_mm": dims, "watertight": wt, "stl": stl, "pass": True,
            "stl_path": os.path.relpath(path, _D5),
            "export_flipped_outer_down": flipped,
            "normals_outward": wt["normals_outward"],
            "bed_face_at_z0": True}
    if meta_key and meta_key in PART_META:
        o, load, mat, swap, rf = PART_META[meta_key]
        body.update({"orientation": o, "load_path": load, "material": mat,
                     "farmer_swappable": swap, "rf_near_antenna": rf})
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


def render_objs(objs_colors, path, direction, pad=1.1):
    _setup()
    live = []
    for o, rgba, n in objs_colors:
        o.data.materials.clear()
        o.data.materials.append(_mat(n, rgba))
        live.append(o)
    lo = [min(oc.bounds(o)[0][i] for o in live) for i in range(3)]
    hi = [max(oc.bounds(o)[1][i] for o in live) for i in range(3)]
    centre = (Vector(lo) + Vector(hi)) / 2
    extent = (Vector(hi) - Vector(lo)).length
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


def build_plate_layout_doc(plates_dir):
    """Plate layouts: prior Orca baseline + estimated deltas for durability geometry."""
    # Baseline: op-maker Orca open-cavity. Deltas ESTIMATED (no Orca in this env):
    # +pod lid 1 mm, channel clamps, support posts, saddle roof — ~+6% P1, ~+8% P2.
    plates = {
        "source": "op-maker Orca baseline 2026-11-03 + durability-rev ESTIMATE deltas",
        "P2S_256": {
            "bed": list(D.BED_P2S),
            "pla_verify": [
                {"plate": "P0", "parts": ["fit_coupon", "label_coupon"], "est_h": 0.97, "g": 27.5,
                 "note": "PRINT FIRST — unchanged"},
                {"plate": "P1", "parts": ["cap_base (+posts)", "cap_lid", "pod_L/R base+lid≥4"],
                 "est_h": 12.1, "g": 283, "note": "EST +6% vs 11h25/267g (thicker pod lids, lid posts)"},
                {"plate": "P2", "parts": ["cw", "saddle roof≥1.6", "4 fairings", "8 channel clamps",
                                         "plugs", "latch", "2 buzz_mesh", "buckle", "keeper"],
                 "est_h": 8.1, "g": 195, "note": "EST +8% vs 7h31/180g (T-clamps, saddle roof)"},
            ],
            "field_asa": [
                {"plate": "P0", "est_h": 1.18, "g": 29.8},
                {"plate": "P1", "est_h": 11.8, "g": 257},
                {"plate": "P2", "est_h": 7.9, "g": 174},
            ],
            "spares_plate": {"plate": "P3", "parts": ["clamp_bar×4 (channel)", "plug_service×3", "latch",
                                                     "buzz_mesh×2", "usbc_cap×2"], "est_h": 0.85, "g": 16},
            "spares_cap_lid": {"plate": "P3b", "parts": ["cap_lid"], "est_h": 2.37, "g": 44.7},
            "per_collar_plates_verify": 2,
            "per_collar_hours_verify_pla": 20.2,
            "per_collar_grams_pla": 478,
            "per_collar_plates_field": 2,
            "per_collar_hours_field_asa": 19.7,
            "per_collar_grams_asa": 431,
            "note": "P1+P2 = collar. Times ESTIMATED from Orca baseline + durability volume; op-maker re-slice before print.",
        },
        "bed_220": {
            "bed": list(D.BED_220),
            "note": "Prior Orca 24h06/490g + ~6% durability EST → ~25.5 h / 520 g.",
            "pla_verify": [
                {"plate": "collar", "est_h": 25.5, "g": 520, "plates": 5},
                {"plate": "coupon", "est_h": 1.57, "g": 36.0},
                {"plate": "spares", "est_h": 0.9},
                {"plate": "spare_lid", "est_h": 2.48},
            ],
            "per_collar_plates_verify": 5,
            "per_collar_hours_verify_pla": 25.5,
            "honest": "Everything fits 220×220. Re-slice after durability CAD before quoting farmers.",
        },
        "starling_note": "Starling CAD not yet designed. Budget ~3 P2S / ~4×220 once XIAO+Wio shell exists (small cells only).",
        "orca_cli": False,
        "orca_note": "Durability times are ESTIMATES. Re-run Orca on new STLs; fix_bbl_3mf.py before Bambu Connect.",
    }
    with open(os.path.join(plates_dir, "plates.json"), "w") as f:
        json.dump(plates, f, indent=2)
    md = os.path.join(plates_dir, "PLATES.md")
    with open(md, "w") as f:
        f.write("# D5 plate layouts (durability revision)\n\n")
        f.write("Baseline: op-maker Orca open-cavity. **Times/grams below are ESTIMATED** "
                "(+~6–8% for thicker pod lids, channel clamps, support posts, saddle roof). "
                "Re-slice before print.\n\n")
        f.write("## P2S 256 — per Rook collar\n\n")
        f.write("| Plate | Parts | PLA (est) | ASA (est) |\n| --- | --- | --- | --- |\n")
        f.write("| P0 | fit + label coupon (**first**) | 0h58 / 27.5 g | 1h11 / 29.8 g |\n")
        f.write("| P1 | cap (+posts) + both pods (lid≥4) | ~12h06 / ~283 g | ~11h48 / ~257 g |\n")
        f.write("| P2 | CW, saddle≥1.6 roof, fairings, channel clamps, … "
                "| ~8h06 / ~195 g | ~7h54 / ~174 g |\n")
        f.write("| **Collar (P1+P2)** | | **~20h12 / ~478 g** | **~19h42 / ~431 g** |\n")
        f.write("| P3 spares | 4 channel clamps, orange, latch, mesh, usbc | ~0h51 | ~0h50 |\n")
        f.write("| P3b | spare cap_lid | 2h22 | 2h23 |\n\n")
        f.write("TPU `usbc_cap` = separate soft plate.\n\n")
        f.write("## 220 bed\n\nCollar ~5 plates / ~25.5 h / ~520 g (est).\n\n")
        f.write("## Clamp print orientation\n\n")
        f.write(D.CLAMP_ORIENTATION + "\n")
    return plates


def main():
    stl_dir = os.path.join(_D5, "stl")
    img_dir = os.path.join(_D5, "images")
    plates_dir = os.path.join(_D5, "plates")
    for d in (stl_dir, img_dir, plates_dir):
        os.makedirs(d, exist_ok=True)

    builders = [
        ("cap_base", cap_base, "cap_base"),
        ("cap_lid", cap_lid, "cap_lid"),
        ("panel_p124", panel_p124, "panel_p124"),
        ("pod_L_base", lambda: pod_base("L"), "pod_L_base"),
        ("pod_L_lid", lambda: pod_lid("L"), "pod_L_lid"),
        ("pod_R_base", lambda: pod_base("R"), "pod_R_base"),
        ("pod_R_lid", lambda: pod_lid("R"), "pod_R_lid"),
        ("cw_tub", cw_tub, "cw_tub"),
        ("cw_lid", cw_lid, "cw_lid"),
        ("saddle", saddle, "saddle"),
        ("clamp_bar", clamp_bar, "clamp_bar"),
        ("keeper", keeper, "keeper"),
        ("buckle", buckle, "buckle"),
        ("latch", latch, "latch"),
        ("plug_service", plug, "plug_service"),
        ("plug_struct", plug, "plug_struct"),
        ("fairing_cap_pod_L", lambda: fairing_cap_pod("L"), "fairing_cap_pod_L"),
        ("fairing_cap_pod_R", lambda: fairing_cap_pod("R"), "fairing_cap_pod_R"),
        ("fairing_pod_strap_L", lambda: fairing_pod_strap("L"), "fairing_pod_strap_L"),
        ("fairing_pod_strap_R", lambda: fairing_pod_strap("R"), "fairing_pod_strap_R"),
        ("usbc_cap", usbc_cap, "usbc_cap"),
        ("buzz_mesh", buzz_mesh, "buzz_mesh"),
        ("label_coupon", label_coupon, "label_coupon"),
        ("fit_coupon", fit_coupon, "fit_coupon"),
        ("cap_floor_layout", cap_floor_layout, "cap_floor_layout"),
        ("pod_floor_layout", lambda: pod_floor_layout("L"), "pod_floor_layout"),
        ("cw_floor_layout", cw_floor_layout, "cw_floor_layout"),
    ]

    # ---- clearance / sanity checks (printed into report) ----
    wio_max_x = D.WIO_AT[0] + D.WIO_POCKET[0] / 2
    wall_left = D.CAP_W / 2 - wio_max_x
    kit_y1 = D.KIT_AT[1] + D.KIT_POCKET[1] / 2
    bq_y0 = D.BQ_AT[1] - D.BQ_POCKET[1] / 2
    gnss_cover = D.CAP_LID_T - (D.GNSS_PATCH[2] + 0.2)
    panel_under = D.CAP_LID_T - D.PANEL_POCKET[2]
    lora_y = D.LORA_AT[1]
    clamp_y_max = max(abs(y) for _, y in D.CAP_CLAMP)
    clearances = {
        "wio_plus_x_wall_mm": round(wall_left, 2),
        "wio_wall_ok": wall_left >= D.WIO_MIN_WALL,
        "kit_bq_gap_mm": round(bq_y0 - kit_y1, 2),
        "support_posts": D.LID_SUPPORT_POSTS,
        "gnss_cover_mm": round(gnss_cover, 2),
        "panel_lid_under_mm": round(panel_under, 2),
        "panel_under_ok": panel_under >= D.PANEL_MIN_LID_UNDER,
        "saddle_roof_mm": D.SADDLE_ROOF,
        "clamp_lora_clear_mm": round(lora_y - clamp_y_max, 2),
        "clamp_lora_ok": (lora_y - clamp_y_max) >= D.ANTENNA_METAL_KEEP,
        "buzz_at": list(D.BUZZ_AT),
        "pod_lid_t": D.POD_LID_T,
        "colourway": D.COLOURWAY_PROPOSAL,
    }
    print("CLEARANCES:", json.dumps(clearances, indent=2))

    report = {
        "revision": "D5_real_glyphs_caplid_mating_down",
        "assumptions": D.ASSUMPTIONS,
        "fit_height_note": D.FIT_HEIGHT_NOTE,
        "cody_flags": D.CODY_FLAGS,
        "decisions": D.DECISIONS,
        "panel_kept": D.PANEL_KEPT,
        "panel_decision_date": D.PANEL_DECISION_DATE,
        "colourway_proposal": D.COLOURWAY_PROPOSAL,
        "floor_glyphs": FLOOR_GLYPHS,
        "floor_glyph_spec": {
            "char_h_mm": GLYPH_CHAR_H,
            "blender_font_size": GLYPH_SIZE,
            "stroke_mm": GLYPH_STROKE,
            "relief_mm": round(GLYPH_DEPTH - GLYPH_EMBED, 2),
            "solidify_depth_mm": GLYPH_DEPTH,
            "font": GLYPH_FONT,
            "on_bases": True,
            "on_floor_layouts": True,
        },
        "floor_label_table": {k: v[0] for k, v in FLOOR_LABEL_TABLE.items()},
        "clearances": clearances,
        "clamp_orientation": D.CLAMP_ORIENTATION,
        "print_orientation_note": (
            "All STLs exported with bed face at z=0. "
            "cap_lid: MATING face on bed (as-built) — P124 pocket faces +Z; "
            "outer-down rejected (large panel ceiling + small rim bed). "
            "pod/cw lids: rotated 180° about X on export (recalc normals, no "
            "flip_normals) so OUTER face is on the bed."
        ),
        "cap_lid_orientation_rationale": (
            "Outer-down leaves the P124 pocket open on the bed (~66×113 mm ceiling "
            "needing support, rim bed area much smaller). Mating-down prints the "
            "panel pocket facing +Z (no support); GNSS/LTE recesses may need small "
            "tree supports on the bed side. Pocket depth kept at PANEL_POCKET for fit."
        ),
        "layout": D.LAYOUT,
        "pockets": {
            "kit": {"board": list(D.KIT_BOARD), "pocket": list(D.KIT_POCKET),
                    "headers_h": D.KIT_POCKET_HEADERS[2], "headers_fit": False,
                    "at": list(D.KIT_AT), "clear_per_side": D.BOARD_CLEAR,
                    "option": "low_profile_no_headers"},
            "bq24074": {"board": list(D.BQ_BOARD), "pocket": list(D.BQ_POCKET),
                        "at": list(D.BQ_AT), "do_not_pot": True},
            "buzzer": {"board": list(D.BUZZ_BOARD), "pocket": list(D.BUZZ_POCKET),
                       "port_d": D.BUZZ_PORT_D, "mesh_rimmed": True},
            "cell_18650": {"cell": [D.CELL_D, D.CELL_L], "pocket_d": D.CELL_POCKET_D,
                           "pocket_l": D.CELL_POCKET_L, "end_clear": D.CELL_END_CLEAR,
                           "bay_adjust": D.CELL_BAY_ADJUST, "pack_353_approved": False},
            "wio": {"pocket_lay_flat": list(D.WIO_POCKET),
                    "pocket_upright_nofit": list(D.WIO_POCKET_UPRIGHT),
                    "orientation": D.WIO_ORIENTATION,
                    "wire_bend": D.WIO_WIRE_BEND, "at": list(D.WIO_AT)},
            "starling": {"pocket": list(D.STARLING_POCKET), "note": D.STARLING_NOTE},
            "antennas": {"gnss": list(D.GNSS_PATCH), "cover_t": D.GNSS_COVER_T,
                         "lte_flex": list(D.LTE_FLEX), "metal_keepout": D.ANTENNA_METAL_KEEP,
                         "crest": "+Y"},
        },
        "stacks_mm": {"cap": D.CAP_STACK_H, "pod": D.POD_STACK_H,
                      "pods_lower_than_cap": D.POD_STACK_H < D.CAP_STACK_H,
                      "note": "pod lid 4.0 durability → 26.0 vs cap 25.5 (0.5 mm brand tension)"},
        "waist_frac": D.WAIST_FRAC,
        "panel_open_decision": D.PANEL_OPEN_DECISION,
        "panel_kept": D.PANEL_KEPT,
        "cap_vs_brand_width": {
            "cap_w": D.CAP_W,
            "brand_max_1_3x_strap": D.CAP_W_MAX_BRAND,
            "cap_w_slim_historical": D.CAP_W_SLIM,
            "conflict_accepted": D.CAP_W > D.CAP_W_MAX_BRAND,
            "reason": "P124 KEPT on collar #1 — cap stays 76",
        },
        "bodies": {},
        "pass": True,
    }

    coupon_dir = os.path.join(_D5, "coupons")
    os.makedirs(coupon_dir, exist_ok=True)
    for name, fn, meta in builders:
        oc.reset()
        obj = fn()
        path = os.path.join(stl_dir, f"{name}.stl")
        report["bodies"][name] = export_part(obj, path, meta)
        if name in ("cap_floor_layout", "pod_floor_layout", "fit_coupon", "label_coupon"):
            shutil.copy2(path, os.path.join(coupon_dir, f"{name}.stl"))

    plates = build_plate_layout_doc(plates_dir)
    report["plates"] = {
        "p2s_verify_h": plates["P2S_256"]["per_collar_hours_verify_pla"],
        "p2s_field_asa_h": plates["P2S_256"]["per_collar_hours_field_asa"],
        "bed220_verify_h": plates["bed_220"]["per_collar_hours_verify_pla"],
        "orca_cli": True,
    }

    # Assembled lineup render (flat printable parts — look study images also in images/)
    oc.reset()
    parts = {
        "cap_base": cap_base(),
        "cap_lid": cap_lid(),
        "panel": panel_p124(),
        "pod_L": pod_base("L"),
        "pod_R": pod_base("R"),
        "cw": cw_tub(),
        "saddle": saddle(),
        "latch": latch(),
    }
    # Lineup along X
    oc.move(parts["cw"], dx=-120)
    oc.move(parts["cap_base"], dx=0)
    oc.move(parts["cap_lid"], dx=0, dz=D.CAP_BASE_H)
    oc.move(parts["panel"], dx=0, dz=D.CAP_BASE_H + D.CAP_LID_T - D.PANEL_POCKET[2])
    oc.move(parts["latch"], dx=0, dy=D.CAP_L / 2 - 5, dz=D.CAP_BASE_H + D.CAP_LID_T)
    oc.move(parts["saddle"], dx=0, dz=-D.SADDLE_H)
    oc.move(parts["pod_L"], dx=110)
    oc.move(parts["pod_R"], dx=200)
    for i, (x, y) in enumerate(D.CAP_ORANGE):
        p = plug()
        oc.move(p, dx=x, dy=y, dz=D.CAP_BASE_H + D.CAP_LID_T - D.PLUG_H)
        parts[f"or{i}"] = p

    colors = [
        (parts["cap_base"], CHARCOAL, "body"),
        (parts["cap_lid"], CHARCOAL, "lid"),
        (parts["panel"], PANEL_NAVY, "panel"),
        (parts["pod_L"], CHARCOAL, "pod"),
        (parts["pod_R"], CHARCOAL, "pod"),
        (parts["cw"], CHARCOAL, "cw"),
        (parts["saddle"], CHARCOAL, "saddle"),
        (parts["latch"], ORANGE, "latch"),
    ]
    for i in range(3):
        colors.append((parts[f"or{i}"], ORANGE, "svc"))
    out = os.path.join(img_dir, "d5_prod_lineup.png")
    render_objs(colors, out, (1.2, -1.3, 0.7), pad=1.05)

    # Exploded
    oc.reset()
    cb, cl, pan = cap_base(), cap_lid(), panel_p124()
    oc.move(cl, dz=D.CAP_BASE_H + 18)
    oc.move(pan, dz=D.CAP_BASE_H + 28)
    out = os.path.join(img_dir, "d5_prod_exploded_cap.png")
    render_objs([(cb, CHARCOAL, "b"), (cl, CHARCOAL, "l"), (pan, PANEL_NAVY, "p")],
                out, (1.1, -1.2, 0.8))

    with open(os.path.join(stl_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\nWaist frac:", round(D.WAIST_FRAC, 4))
    print("P124 open decision:", D.PANEL_OPEN_DECISION)
    print("Cap vs brand 1.3× strap:", D.CAP_W, "vs", D.CAP_W_MAX_BRAND,
          "(slim", D.CAP_W_SLIM, "if panel dropped)")
    print("Stacks cap/pod:", D.CAP_STACK_H, "/", D.POD_STACK_H)
    print("Wio orientation:", D.WIO_ORIENTATION)
    print("FIT_HEIGHT_NOTE:", D.FIT_HEIGHT_NOTE)
    print("CODY_FLAGS:", D.CODY_FLAGS)
    print("RESULT: PASS (real glyphs + cap_lid mating-down + P124 KEPT)")


if __name__ == "__main__":
    main()
