"""Rook enclosure concept D — hybrid (B technical + A radii + C height).

Led by B's clean technical language: flat functional planes, one waist datum,
even fastener grid. Softened with A's plan-corner family (R6–R8) and C's low
cap (~18 mm, cavity ≥13). B's 45° crown chamfer becomes a 2.5 mm top-edge
radius (no dust ledge). The waist is a real lid parting line with O-ring seat
and ~0.5 mm reveal, same height fraction on cap / pod / tub.

Does NOT touch production `stl/node_v1_*`. Concept study only — Cody approves
any print.

Run:
  cd hardware/rook/concepts/cad
  blender --background --factory-startup --python build_concept_d.py
"""

from __future__ import annotations

import json
import math
import os
import shutil
import struct
import sys
from collections import Counter

import bmesh
import bpy
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONCEPTS = os.path.abspath(os.path.join(_HERE, ".."))
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
import oc  # noqa: E402

# ---------------------------------------------------------------- palette (op-brand)
CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)   # #26282B body
OAT = (0xEF / 255, 0xE8 / 255, 0xD8 / 255, 1.0)         # #EFE8D8 lid variant
ORANGE = (0xFF / 255, 0x6A / 255, 0x2B / 255, 1.0)      # #FF6A2B fasteners/latch
BLACK = (0.08, 0.08, 0.09, 1.0)                          # strap
WORLD = (0.94, 0.93, 0.90)

# ---------------------------------------------------------------- envelope (locked)
CAP_W, CAP_L = 76.0, 160.0
CAP_WALL = 5.0
CAP_FLOOR = 5.0
CAP_CAVITY_H = 13.0
CAP_BASE_H = CAP_FLOOR + CAP_CAVITY_H  # 18
# Lid thin enough for Instrument plugs; screws from above into base inserts.
CAP_LID_T = 6.0
CAP_COLS = [(sx * 29.5, y) for sx in (-1, 1) for y in (-68.0, -42.0, 42.0, 68.0)]
CAP_CLAMP = [(sx * 20.0, sy * 28.5) for sx in (-1, 1) for sy in (-1, 1)]

POD_L, POD_W = 92.0, 68.0
POD_WALL = 5.0
POD_FLOOR = 3.0
POD_CAVITY = (82.0, 58.0, 21.5)
POD_BASE_H = POD_FLOOR + POD_CAVITY[2]  # 24.5
POD_COLS = [(sx * 37.0, sy * 27.0) for sx in (-1, 1) for sy in (-1, 1)]

CW_L, CW_W = 88.0, 74.0
CW_WALL = 5.0
CW_FLOOR = 3.0
CW_TUB_H = 30.0
CW_SCREWS = [(sx * 22.0, sy * 31.5) for sx in (-1, 1) for sy in (-1, 1)]
CW_CLAMP = [(sx * 36.0, sy * 29.5) for sx in (-1, 1) for sy in (-1, 1)]

# Shared waist fraction base/(base+lid) on all three — lids scale with bases.
WAIST_FRAC = CAP_BASE_H / (CAP_BASE_H + CAP_LID_T)  # 0.75
POD_LID_T = round(POD_BASE_H * (1.0 / WAIST_FRAC - 1.0), 2)  # ≈8.17
CW_LID_T = round(CW_TUB_H * (1.0 / WAIST_FRAC - 1.0), 2)      # 10.0

PLAN_R = 7.0          # one radius family (R6–R8)
TOP_R = 2.5           # top-edge radius (replaces B's 45° chamfer)
REVEAL = 0.5          # lid inset → ~0.5 mm flush-joint reveal
CLEAR = 3.4
INSERT_D = 4.0
GROOVE_W, GROOVE_D = 2.9, 1.5
CBORE_D, CBORE_H = 7.6, 2.6
PLUG_SEAT_D, PLUG_SEAT_H = 8.4, 1.4
PLUG_D, PLUG_H = 8.0, 1.3
PLUG_CHAMFER = 0.35
PORT_D, CABLE_D = 8.0, 6.0
PORT_BOSS_T, PORT_BOSS_H = 2.2, 1.6
LABEL_W, LABEL_L, LABEL_D = 30.0, 12.0, 0.35
ENGRAVE_D = 0.5
ENGRAVE_SIZE = 5.0

# ---------------------------------------------------------------- 5×7 mono (manifold)
_FONT_5X7 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


# ---------------------------------------------------------------- mesh helpers

def prepare(obj, merge=1e-4):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=merge, edges=list(bm.edges))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge)
    tiny = [f for f in bm.faces if f.calc_area() < 1e-8]
    if tiny:
        bmesh.ops.delete(bm, geom=tiny, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def check_watertight(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    loose = sum(1 for v in bm.verts if not v.link_edges)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return {
        "watertight": bad == 0 and zero == 0 and loose == 0,
        "bad_edges": bad,
        "zero_area_faces": zero,
        "normals_outward": vol > 0,
    }


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


def top_edge_radius(obj, r=TOP_R, segments=5, z_tol=0.15):
    """Bevel only the top outer perimeter edges (no dust ledge / no full-body bevel)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    zmax = max(v.co.z for v in bm.verts)
    # Outer edges near the crown: both verts near zmax, not vertical.
    chosen = []
    for e in bm.edges:
        a, b = e.verts
        if abs(a.co.z - zmax) > z_tol or abs(b.co.z - zmax) > z_tol:
            continue
        direction = (a.co - b.co).normalized()
        if abs(direction.z) > 0.3:
            continue
        # Prefer boundary / silhouette: edge lies on the outer wall or top face pair.
        if len(e.link_faces) != 2:
            continue
        n0 = e.link_faces[0].normal
        n1 = e.link_faces[1].normal
        # Top-face + side-face meeting → one normal ~+Z, other ~horizontal.
        if (n0.z > 0.7 and abs(n1.z) < 0.35) or (n1.z > 0.7 and abs(n0.z) < 0.35):
            chosen.append(e)
    if chosen:
        bmesh.ops.bevel(bm, geom=chosen, offset=r, segments=segments,
                        affect="EDGES", profile=0.5)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def groove_loop(name, w, l, r, z_top, inset):
    """O-ring groove cut down from z_top; centreline `inset` from outer edge."""
    g, gd = GROOVE_W, GROOVE_D
    outer = oc.rounded_rect(
        name + "_o",
        (w - 2 * (inset - g / 2), l - 2 * (inset - g / 2), gd + 1),
        max(r - inset + g / 2, 0.6),
        at=(0, 0, z_top - gd),
        anchor="bottom",
    )
    inner = oc.rounded_rect(
        name + "_i",
        (w - 2 * (inset + g / 2), l - 2 * (inset + g / 2), gd + 3),
        max(r - inset - g / 2, 0.4),
        at=(0, 0, z_top - gd - 1),
        anchor="bottom",
    )
    return oc.cut(outer, inner)


def manifold_text(name, body, size, depth, at, align="CENTER"):
    cell = size / 7.0
    gap = cell * 0.2
    cw = 5 * cell + gap
    body = body.upper()
    chars = list(body)
    width = max(len(chars) * cw - gap, cell)
    if align == "CENTER":
        x0 = at[0] - width / 2
    elif align == "LEFT":
        x0 = at[0]
    else:
        x0 = at[0] - width
    y0 = at[1] - size / 2
    z0 = at[2]
    pixels = []
    for ci, ch in enumerate(chars):
        glyph = _FONT_5X7.get(ch, _FONT_5X7[" "])
        for row, bits in enumerate(glyph):
            col = 0
            while col < 5:
                if bits[col] != "1":
                    col += 1
                    continue
                start = col
                while col < 5 and bits[col] == "1":
                    col += 1
                run = col - start
                px = x0 + ci * cw + (start + run / 2) * cell
                py = y0 + (6 - row + 0.5) * cell
                pixels.append(oc.box(
                    f"{name}_{ci}_{row}_{start}",
                    (run * cell * 0.92, cell * 0.92, depth),
                    at=(px, py, z0), anchor="bottom"))
    if not pixels:
        return oc.box(name, (cell, cell, depth), at=(at[0], at[1], z0), anchor="bottom")
    if len(pixels) == 1:
        pixels[0].name = name
        return pixels[0]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for p in pixels:
        p.select_set(True)
    bpy.context.view_layer.objects.active = pixels[0]
    bpy.ops.object.join()
    pixels[0].name = name
    return pixels[0]


def add_columns(body, cols, floor_z, top_z, through_clear=False):
    # Flush with the waist rim (no proud boss that inflates bbox height).
    bosses = [
        oc.cylinder(f"col{i}", 8.0, top_z - floor_z,
                    at=(x, y, floor_z), anchor="bottom")
        for i, (x, y) in enumerate(cols)
    ]
    oc.union(body, *bosses)
    if through_clear:
        for i, (x, y) in enumerate(cols):
            oc.cut(body, oc.cylinder(f"h{i}", CLEAR, top_z + 2,
                                     at=(x, y, -1), anchor="bottom"))
    return body


def cut_cavity(body, size_xy_h, floor_z, r=4.0):
    sx, sy, h = size_xy_h
    oc.cut(body, oc.rounded_rect("cav", (sx, sy, h + 1), r,
                                 at=(0, 0, floor_z), anchor="bottom"))
    return body


def lid_fastener_seats(lid, cols, lid_t):
    """Through clearance + head cbore + flush plug seat with chamfered lead-in.

    Screws enter from above into heat-set inserts in the base columns, so the
    lid stays a thin through-plate (no blind insert pack under the plug).
    Keep ≥1.5 mm solid under the cbore so the CLEAR→CBORE step stays manifold.
    """
    # Plug + button-head stack. On a 6 mm lid, >3.0 mm leaves a non-manifold
    # CLEAR→CBORE shelf (exact boolean); keep ≥3 mm solid under the cbore.
    head_stack = min(PLUG_SEAT_H + 1.6, lid_t - 3.0, 3.0)
    for i, (x, y) in enumerate(cols):
        oc.cut(lid, oc.cylinder(f"lh{i}", CLEAR, lid_t + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(lid, oc.cylinder(f"lcb{i}", CBORE_D, head_stack + 0.05,
                                at=(x, y, lid_t - head_stack),
                                anchor="bottom"))
        oc.cut(lid, oc.cylinder(f"lps{i}", PLUG_SEAT_D, PLUG_SEAT_H + 0.05,
                                at=(x, y, lid_t - PLUG_SEAT_H),
                                anchor="bottom"))
        oc.cut(lid, oc.cone(f"lpc{i}", PLUG_SEAT_D + 2 * PLUG_CHAMFER, PLUG_SEAT_D,
                            PLUG_CHAMFER + 0.05,
                            at=(x, y, lid_t - PLUG_CHAMFER)))
    return lid


def make_plug(name, at=(0, 0, 0)):
    """Separate blaze-orange flush plug body (exportable / colourable)."""
    p = oc.cylinder(name, PLUG_D, PLUG_H, at=at, anchor="bottom")
    # Small top chamfer so the plug seats without a proud lip.
    oc.cut(p, oc.cone(name + "_ch", PLUG_D + 0.1, PLUG_D - 2 * PLUG_CHAMFER,
                      PLUG_CHAMFER + 0.05,
                      at=(at[0], at[1], at[2] + PLUG_H - PLUG_CHAMFER)))
    return prepare(p)


def port_boss(axis, at, hole_d, boss_od=None, height=PORT_BOSS_H):
    """Raised annular boss around a round port (not a bare hole)."""
    boss_od = boss_od or (hole_d + 2 * PORT_BOSS_T)
    ring = oc.cylinder("boss", boss_od, height, at=at, axis=axis, anchor="center")
    oc.cut(ring, oc.cylinder("bossh", hole_d, height + 2, at=at, axis=axis, anchor="center"))
    return ring


def port_gasket_recess(body, axis, at, hole_d, recess_d=None, depth=1.0):
    """Optional shallow gasket counterbore on the outer face around a port."""
    recess_d = recess_d or (hole_d + 3.0)
    oc.cut(body, oc.cylinder("prec", recess_d, depth + 0.2, at=at, axis=axis, anchor="center"))
    return body


# ---------------------------------------------------------------- shells

def base_column_inserts(body, cols, top_z, depth=5.0):
    """Heat-set insert pockets opening at the waist (lid screws from above)."""
    for i, (x, y) in enumerate(cols):
        oc.cut(body, oc.cylinder(f"bins{i}", INSERT_D, depth + 0.2,
                                 at=(x, y, top_z - depth), anchor="bottom"))
    return body


def d_cap_base():
    b = oc.rounded_rect("d_cap_base", (CAP_W, CAP_L, CAP_BASE_H), PLAN_R,
                        anchor="bottom", segments=10)
    cut_cavity(b, (CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, CAP_CAVITY_H + 2),
               CAP_FLOOR, r=5.0)
    add_columns(b, CAP_COLS, CAP_FLOOR, CAP_BASE_H)
    # Replace through-clear with insert pockets at the waist rim.
    base_column_inserts(b, CAP_COLS, CAP_BASE_H, depth=5.0)
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ci{i}", INSERT_D, 4.5, at=(x, y, -0.2), anchor="bottom"))
    oc.cut(b, groove_loop("cg", CAP_W, CAP_L, PLAN_R, CAP_BASE_H, CAP_WALL / 2))
    return prepare(b)


def d_cap_lid():
    lw, ll = CAP_W - 2 * REVEAL, CAP_L - 2 * REVEAL
    lr = max(PLAN_R - REVEAL, 4.0)
    lid = oc.rounded_rect("d_cap_lid", (lw, ll, CAP_LID_T), lr, anchor="bottom", segments=10)
    lid_fastener_seats(lid, CAP_COLS, CAP_LID_T)
    # Flat label pad 30×12, debossed mono Rook-001.
    oc.cut(lid, oc.rounded_rect("label_pad", (LABEL_W, LABEL_L, LABEL_D + 0.1), 1.0,
                                at=(0, 0, CAP_LID_T - LABEL_D), anchor="bottom"))
    text = manifold_text("rook_id", "ROOK-001", ENGRAVE_SIZE, ENGRAVE_D + 0.15,
                         at=(0, 0, CAP_LID_T - LABEL_D - ENGRAVE_D))
    oc.cut(lid, text)
    top_edge_radius(lid, r=TOP_R, segments=5)
    return prepare(lid)


def d_pod_base():
    b = oc.rounded_rect("d_pod_base", (POD_L, POD_W, POD_BASE_H), PLAN_R,
                        anchor="bottom", segments=10)
    cut_cavity(b, POD_CAVITY, POD_FLOOR, r=5.0)
    add_columns(b, POD_COLS, POD_FLOOR, POD_BASE_H)
    base_column_inserts(b, POD_COLS, POD_BASE_H, depth=5.0)
    oc.cut(b, groove_loop("pg", POD_L, POD_W, PLAN_R, POD_BASE_H, POD_WALL / 2))
    # Sound port (+Y) + cable: raised boss + gasket recess, not bare holes.
    port_at = (20.0, POD_W / 2 - POD_WALL / 2, 11.0)
    cable_at = (POD_L / 2 - POD_WALL / 2, -2.0, 12.0)
    oc.union(b, port_boss("Y", port_at, PORT_D))
    oc.union(b, port_boss("X", cable_at, CABLE_D, boss_od=CABLE_D + 2 * PORT_BOSS_T))
    oc.cut(b, oc.cylinder("port", PORT_D, POD_WALL + PORT_BOSS_H + 4,
                          at=port_at, axis="Y"))
    oc.cut(b, oc.cylinder("cable", CABLE_D, POD_WALL + PORT_BOSS_H + 4,
                          at=cable_at, axis="X"))
    port_gasket_recess(b, "Y", (20.0, POD_W / 2 + PORT_BOSS_H / 2, 11.0), PORT_D, depth=0.8)
    port_gasket_recess(b, "X", (POD_L / 2 + PORT_BOSS_H / 2, -2.0, 12.0), CABLE_D, depth=0.8)
    return prepare(b)


def d_pod_lid():
    lw, ll = POD_L - 2 * REVEAL, POD_W - 2 * REVEAL
    lr = max(PLAN_R - REVEAL, 4.0)
    lid = oc.rounded_rect("d_pod_lid", (lw, ll, POD_LID_T), lr, anchor="bottom", segments=10)
    lid_fastener_seats(lid, POD_COLS, POD_LID_T)
    top_edge_radius(lid, r=TOP_R, segments=5)
    return prepare(lid)


def d_cw_tub():
    b = oc.rounded_rect("d_cw_tub", (CW_L, CW_W, CW_TUB_H), PLAN_R,
                        anchor="bottom", segments=10)
    cut_cavity(b, (CW_L - 2 * CW_WALL - 2, CW_W - 2 * CW_WALL - 2, CW_TUB_H),
               CW_FLOOR, r=4.0)
    oc.cut(b, groove_loop("wg", CW_L, CW_W, PLAN_R, CW_TUB_H, CW_WALL / 2))
    # Inserts open at the waist for lid screws from above.
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.cut(b, oc.cylinder(f"cwi{i}", INSERT_D, 5.2,
                              at=(x, y, CW_TUB_H - 5.0), anchor="bottom"))
    for i, (x, y) in enumerate(CW_CLAMP):
        oc.cut(b, oc.cylinder(f"cwcl{i}", CLEAR, CW_TUB_H + 2,
                              at=(x, y, -1), anchor="bottom"))
    return prepare(b)


def d_cw_lid():
    lw, ll = CW_L - 2 * REVEAL, CW_W - 2 * REVEAL
    lr = max(PLAN_R - REVEAL, 4.0)
    lid = oc.rounded_rect("d_cw_lid", (lw, ll, CW_LID_T), lr, anchor="bottom", segments=10)
    lid_fastener_seats(lid, CW_SCREWS, CW_LID_T)
    top_edge_radius(lid, r=TOP_R, segments=5)
    return prepare(lid)


def d_latch(length=14.0, width=8.0, thick=3.0):
    """One-handed Instrument latch cue (blaze orange) — concept solid only."""
    latch = oc.rounded_rect("d_latch", (width, length, thick), 1.5, anchor="bottom", segments=6)
    # Finger scoop on the outer face.
    oc.cut(latch, oc.cylinder("scoop", 5.0, thick,
                              at=(0, length * 0.15, thick * 0.55), axis="X"))
    return prepare(latch)


def d_test_corner():
    """Small coupon: plan R7 + top-edge R2.5 for 0.12 / 0.16 mm layer print tests."""
    s = 22.0
    h = 10.0
    # One rounded corner family on a square coupon.
    c = oc.rounded_rect("d_test_corner", (s, s, h), PLAN_R, anchor="bottom", segments=12)
    top_edge_radius(c, r=TOP_R, segments=6)
    # Engrave layer hints on the top face (away from the radiused rim).
    t1 = manifold_text("t012", "0.12", 3.5, 0.4, at=(0, 3.5, h - 0.4))
    t2 = manifold_text("t016", "0.16", 3.5, 0.4, at=(0, -3.5, h - 0.4))
    oc.cut(c, t1, t2)
    return prepare(c)


def d_strap(length=180.0, width=44.0, thick=4.0):
    return prepare(oc.rounded_rect("d_strap", (width, length, thick), 2.0,
                                   anchor="bottom", segments=4))


# ---------------------------------------------------------------- colour render

def _mat(name, rgba):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def _setup_color_render(res=(1600, 1200)):
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.render.resolution_x, s.render.resolution_y = res
    s.render.film_transparent = False
    sh = s.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = True
    sh.show_specular_highlight = False
    world = bpy.data.worlds.new("wd")
    world.color = WORLD
    s.world = world
    s.view_settings.view_transform = "Standard"


def _paint(obj, rgba, name):
    obj.data.materials.clear()
    obj.data.materials.append(_mat(name, rgba))


def _camera(lo, hi, direction, pad=1.15):
    centre = (Vector(lo) + Vector(hi)) / 2
    extent = (Vector(hi) - Vector(lo)).length
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(extent * pad, 1.0)
    cam_data.clip_end = extent * 20
    cam = oc._link(bpy.data.objects.new("cam", cam_data))
    d = Vector(direction).normalized()
    cam.location = centre + d * extent * 3
    if abs(d.z) > 0.99:
        cam.rotation_euler = (0, 0, 0) if d.z > 0 else (math.pi, 0, 0)
    else:
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def render_colored(objs_colors, out_path, direction, pad=1.12):
    _setup_color_render()
    live = []
    for obj, rgba, mname in objs_colors:
        _paint(obj, rgba, mname)
        obj.hide_render = False
        live.append(obj)
    lo = [min(oc.bounds(o)[0][i] for o in live) for i in range(3)]
    hi = [max(oc.bounds(o)[1][i] for o in live) for i in range(3)]
    cam = _camera(lo, hi, direction, pad=pad)
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    return out_path


# ---------------------------------------------------------------- build / export

def export_part(obj, path, expect_xy=None, z_min=5.0):
    prepare(obj)
    dims = oc.size(obj)
    vol = oc.volume_mm3(obj)
    wt = check_watertight(obj)
    oc.export_stl(obj, path)
    stl = check_stl(path)
    size_ok = True
    if expect_xy is not None:
        size_ok = (abs(dims[0] - expect_xy[0]) <= 1.5
                   and abs(dims[1] - expect_xy[1]) <= 1.5
                   and dims[2] >= z_min)
    ok = wt["watertight"] and stl["watertight"] and wt["normals_outward"] and size_ok
    body = {
        "size_mm": dims,
        "volume_cm3": round(vol / 1000, 2),
        "watertight": wt,
        "stl": stl,
        "size_ok": size_ok,
        "pass": ok,
        "stl_path": os.path.relpath(path, _CONCEPTS),
    }
    print(f"{'PASS' if ok else 'FAIL'}  {os.path.basename(path)}: {dims} mm  "
          f"bad={wt['bad_edges']} stl_bad={stl['bad_edges']} size_ok={size_ok}")
    return body


def place_assembled(parts, plugs, latch, strap, explode=0.0):
    """Family lineup: CW | Cap | Pod. Lids sit on bases; explode lifts lids/plugs."""
    gap = 28.0
    cap_x = 0.0
    pod_x = CAP_W / 2 + POD_L / 2 + gap
    cw_x = -(CAP_W / 2 + CW_L / 2 + gap)

    oc.move(parts["cap_base"], dx=cap_x)
    oc.move(parts["cap_lid"], dx=cap_x, dz=CAP_BASE_H + explode)
    oc.move(parts["pod_base"], dx=pod_x)
    oc.move(parts["pod_lid"], dx=pod_x, dz=POD_BASE_H + explode)
    oc.move(parts["cw_tub"], dx=cw_x)
    oc.move(parts["cw_lid"], dx=cw_x, dz=CW_TUB_H + explode)

    # Cap plugs on lid top.
    for i, (x, y) in enumerate(CAP_COLS):
        oc.move(plugs["cap"][i],
                dx=cap_x + x, dy=y,
                dz=CAP_BASE_H + CAP_LID_T - PLUG_H + 0.05 + explode * 1.6)
    for i, (x, y) in enumerate(POD_COLS):
        oc.move(plugs["pod"][i],
                dx=pod_x + x, dy=y,
                dz=POD_BASE_H + POD_LID_T - PLUG_H + 0.05 + explode * 1.6)
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.move(plugs["cw"][i],
                dx=cw_x + x, dy=y,
                dz=CW_TUB_H + CW_LID_T - PLUG_H + 0.05 + explode * 1.6)

    # Latch on +Y end of cap lid.
    oc.move(latch, dx=cap_x, dy=CAP_L / 2 - REVEAL - 6.0,
            dz=CAP_BASE_H + CAP_LID_T - 1.0 + explode)
    # Strap under the cap (black).
    oc.move(strap, dx=cap_x, dz=-4.5)
    return cw_x, cap_x, pod_x


def colored_set(parts, plugs, latch, strap, lid_color):
    bodies = [
        (parts["cap_base"], CHARCOAL, "body"),
        (parts["pod_base"], CHARCOAL, "body"),
        (parts["cw_tub"], CHARCOAL, "body"),
        (parts["cap_lid"], lid_color, "lid"),
        (parts["pod_lid"], lid_color, "lid"),
        (parts["cw_lid"], lid_color, "lid"),
        (latch, ORANGE, "latch"),
        (strap, BLACK, "strap"),
    ]
    for p in plugs["cap"] + plugs["pod"] + plugs["cw"]:
        bodies.append((p, ORANGE, "plug"))
    return bodies


def main():
    stl_dir = os.path.join(_CONCEPTS, "stl", "D_hybrid")
    rend_dir = os.path.join(_CONCEPTS, "renders", "D_hybrid")
    img_dir = os.path.join(_CONCEPTS, "images")
    os.makedirs(stl_dir, exist_ok=True)
    os.makedirs(rend_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    oc.reset()
    parts = {
        "cap_base": d_cap_base(),
        "cap_lid": d_cap_lid(),
        "pod_base": d_pod_base(),
        "pod_lid": d_pod_lid(),
        "cw_tub": d_cw_tub(),
        "cw_lid": d_cw_lid(),
        "test_corner": d_test_corner(),
        "latch": d_latch(),
        "plug": make_plug("d_plug"),
    }

    report = {
        "concept": "D_hybrid",
        "title": "D — Hybrid technical-soft",
        "waist_frac": WAIST_FRAC,
        "plan_r_mm": PLAN_R,
        "top_r_mm": TOP_R,
        "reveal_mm": REVEAL,
        "palette": {
            "charcoal": "#26282B",
            "oat": "#EFE8D8",
            "orange": "#FF6A2B",
            "strap": "#141416",
        },
        "bodies": {},
        "pass": True,
    }

    expect = {
        "cap_base": (CAP_W, CAP_L),
        "cap_lid": (CAP_W - 2 * REVEAL, CAP_L - 2 * REVEAL),
        "pod_base": (POD_L, POD_W),
        "pod_lid": (POD_L - 2 * REVEAL, POD_W - 2 * REVEAL),
        "cw_tub": (CW_L, CW_W),
        "cw_lid": (CW_L - 2 * REVEAL, CW_W - 2 * REVEAL),
        "test_corner": (22.0, 22.0),
        "latch": None,
        "plug": None,
    }
    zmin = {
        "cap_base": CAP_BASE_H - 1.0,
        "cap_lid": CAP_LID_T - 1.5,
        "pod_base": POD_BASE_H - 1.0,
        "pod_lid": POD_LID_T - 1.5,
        "cw_tub": CW_TUB_H - 1.0,
        "cw_lid": CW_LID_T - 1.5,
        "test_corner": 8.0,
        "latch": 2.0,
        "plug": 1.0,
    }

    for name, obj in parts.items():
        path = os.path.join(stl_dir, f"{name}.stl")
        body = export_part(obj, path, expect_xy=expect[name], z_min=zmin[name])
        report["bodies"][name] = body
        report["pass"] &= body["pass"]

    # ---- assembled colour renders (rebuild scene so transforms are clean)
    oc.reset()
    bases = {
        "cap_base": d_cap_base(),
        "cap_lid": d_cap_lid(),
        "pod_base": d_pod_base(),
        "pod_lid": d_pod_lid(),
        "cw_tub": d_cw_tub(),
        "cw_lid": d_cw_lid(),
    }
    plugs = {
        "cap": [make_plug(f"pcap{i}") for i in range(len(CAP_COLS))],
        "pod": [make_plug(f"ppod{i}") for i in range(len(POD_COLS))],
        "cw": [make_plug(f"pcw{i}") for i in range(len(CW_SCREWS))],
    }
    latch = d_latch()
    strap = d_strap()
    place_assembled(bases, plugs, latch, strap, explode=0.0)

    views = {
        "iso": (1.1, -1.3, 0.95),
        "front": (0.0, -1.0, 0.25),
        "side": (1.0, 0.0, 0.2),
    }
    for view, direction in views.items():
        out = os.path.join(rend_dir, f"assembled_{view}.png")
        render_colored(colored_set(bases, plugs, latch, strap, CHARCOAL),
                       out, direction)
        shutil.copy2(out, os.path.join(img_dir, f"D_hybrid_{view}.png"))

    # Exploded
    oc.reset()
    bases = {
        "cap_base": d_cap_base(),
        "cap_lid": d_cap_lid(),
        "pod_base": d_pod_base(),
        "pod_lid": d_pod_lid(),
        "cw_tub": d_cw_tub(),
        "cw_lid": d_cw_lid(),
    }
    plugs = {
        "cap": [make_plug(f"epcap{i}") for i in range(len(CAP_COLS))],
        "pod": [make_plug(f"eppod{i}") for i in range(len(POD_COLS))],
        "cw": [make_plug(f"epcw{i}") for i in range(len(CW_SCREWS))],
    }
    latch = d_latch()
    strap = d_strap()
    place_assembled(bases, plugs, latch, strap, explode=18.0)
    out = os.path.join(rend_dir, "assembled_exploded.png")
    render_colored(colored_set(bases, plugs, latch, strap, CHARCOAL),
                   out, (1.15, -1.35, 0.85), pad=1.2)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_exploded.png"))

    # Oat lid variant (3 angles)
    oc.reset()
    bases = {
        "cap_base": d_cap_base(),
        "cap_lid": d_cap_lid(),
        "pod_base": d_pod_base(),
        "pod_lid": d_pod_lid(),
        "cw_tub": d_cw_tub(),
        "cw_lid": d_cw_lid(),
    }
    plugs = {
        "cap": [make_plug(f"opcap{i}") for i in range(len(CAP_COLS))],
        "pod": [make_plug(f"oppod{i}") for i in range(len(POD_COLS))],
        "cw": [make_plug(f"opcw{i}") for i in range(len(CW_SCREWS))],
    }
    latch = d_latch()
    strap = d_strap()
    place_assembled(bases, plugs, latch, strap, explode=0.0)
    for view, direction in views.items():
        out = os.path.join(rend_dir, f"oat_{view}.png")
        render_colored(colored_set(bases, plugs, latch, strap, OAT),
                       out, direction)
        shutil.copy2(out, os.path.join(img_dir, f"D_hybrid_oat_{view}.png"))

    with open(os.path.join(rend_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    with open(os.path.join(stl_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\nWaist fractions:")
    print(f"  cap  {CAP_BASE_H / (CAP_BASE_H + CAP_LID_T):.4f}  "
          f"(base {CAP_BASE_H} + lid {CAP_LID_T})")
    print(f"  pod  {POD_BASE_H / (POD_BASE_H + POD_LID_T):.4f}  "
          f"(base {POD_BASE_H} + lid {POD_LID_T})")
    print(f"  cw   {CW_TUB_H / (CW_TUB_H + CW_LID_T):.4f}  "
          f"(tub  {CW_TUB_H} + lid {CW_LID_T})")
    print("\nRESULT:", "PASS" if report["pass"] else "FAIL")
    if not report["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
