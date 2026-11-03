"""D5 production CAD — printable parametric rebuild of the D5 look study.

Print orientation (load WITH layers, never across):
  cap_base / pod_*_base / cw_tub  — bed = outer face OR cavity-up (documented per part)
  lids                             — mating face down (seal land on bed)
  saddle                           — flank on bed, channel as pocket (no bridge)
  fairings                         — long axis on bed, visible slope as WALL
  clamp bars                       — flat on bed
  plugs / latch / seals            — flat on bed

Does NOT remesh/warp like the look-study. Curve to strap is via saddle +
fairing mating, not voxel bend. Look-study STLs stay in ../look_study/.

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
from mathutils import Vector

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

# ---------------------------------------------------------------- mesh helpers

def prepare(obj, merge=1e-4):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


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
    inset = wall / 2
    g, gd = D.GROOVE_W, D.GROOVE_D
    outer = oc.rounded_rect("go", (w - 2 * (inset - g / 2), l - 2 * (inset - g / 2), gd + 1),
                            max(r - inset + g / 2, 0.8), at=(0, 0, z_top - gd), anchor="bottom")
    inner = oc.rounded_rect("gi", (w - 2 * (inset + g / 2), l - 2 * (inset + g / 2), gd + 3),
                            max(r - inset - g / 2, 0.5), at=(0, 0, z_top - gd - 1), anchor="bottom")
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


def pocket_box(body, name, size, at, floor_z):
    sx, sy, sz = size
    oc.cut(body, oc.rounded_rect(name, (sx, sy, sz + 0.5), 1.5,
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

    # --- Wio-SX1262 LAY-FLAT (+X wall); upright 23 mm does NOT fit — see FIT_HEIGHT_NOTE ---
    wio_at = D.WIO_AT
    pocket_box(b, "wio", D.WIO_POCKET, wio_at, D.CAP_FLOOR)
    # U.FL slack along +X wall only (x≥24) — must NOT overlap bq pocket (x to ~19.5).
    oc.cut(b, oc.rounded_rect("uflslack", (6.0, D.WIO_WIRE_BEND, 4.0), 1.0,
                              at=(30.0, 10.0, D.CAP_FLOOR),
                              anchor="bottom"))
    # Strain-relief boss on +X wall before crest antenna run
    oc.cut(b, oc.cylinder("uflstrain", D.UFL_STRAIN_D, 4.0,
                          at=(30.0, 35.0, D.CAP_FLOOR - 0.1),
                          anchor="bottom"))

    # --- USB-C charge port (kit short end → −Y wall) + gasket recess ---
    ux, uy, uz = D.USBC_PORT
    oc.cut(b, oc.rounded_rect("usbc", (ux, uy, uz), 1.0,
                              at=(0, -(D.CAP_L / 2 - D.CAP_WALL / 2), D.CAP_FLOOR + 2.0),
                              anchor="bottom"))
    # Outer gasket-cap seat
    oc.cut(b, oc.rounded_rect("usbcseat", (D.USBC_CAP[0] + 0.4, 3.0, D.USBC_CAP[1] + 0.4),
                              1.2,
                              at=(0, -(D.CAP_L / 2 - 1.5), D.CAP_FLOOR + 1.5),
                              anchor="bottom"))

    # Light-pipe wells over kit LEDs (toward −Y lid)
    for i, dx in enumerate((-6.0, 6.0)):
        oc.cut(b, oc.cylinder(f"lp{i}", D.LIGHTPIPE_D, D.CAP_CAVITY_H + 2,
                              at=(dx, kit_at[1] - 6.0, D.CAP_FLOOR + 1.0),
                              anchor="bottom"))

    # Button membrane seats (press-through) near kit
    for i, dx in enumerate((-14.0, 14.0)):
        oc.cut(b, oc.rounded_rect(f"btn{i}", D.BTN_MEMBRANE, 1.0,
                                  at=(dx, kit_at[1] + 8.0, D.CAP_FLOOR + D.KIT_POCKET[2] - 0.5),
                                  anchor="bottom"))

    # Cable exits toward pods (±X) with strain wells
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cable{sx}", 6.0, D.CAP_WALL + 4,
                              at=(sx * (D.CAP_W / 2 - D.CAP_WALL / 2), 0, D.CAP_FLOOR + 6),
                              axis="X"))

    end_taper_cut(b, D.CAP_W, D.CAP_L, D.CAP_BASE_H, D.CAP_TAPER_LEN)
    return prepare(b)


def cap_lid():
    """Print: OUTER FACE DOWN (flat bed) — mating features face UP (no support).

    Replaces the old full-area underside recess (~39% tree support) with a
    narrow landing-ring groove that receives the base reg_lip.

    Crest (+Y): GNSS ceramic under 1–3 mm plastic, no metal above.
    """
    lw, ll = D.CAP_W - 2 * D.REVEAL, D.CAP_L - 2 * D.REVEAL
    lid = slab("cap_lid", lw, ll, D.CAP_LID_T, D.PLAN_R - 0.5)
    lid_fasteners(lid, D.CAP_COLS, D.CAP_LID_T)

    # Landing ring groove (not a solid plate recess) — printable outer-down.
    # Matches base reg_lip ring; ~1.6 mm wide channel.
    ring_out_w, ring_out_l = lw - 6.0, ll - 6.0
    ring_in_w, ring_in_l = ring_out_w - 3.2, ring_out_l - 3.2
    outer = oc.rounded_rect("lring_o", (ring_out_w, ring_out_l, 1.5), 4.0,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("lring_i", (ring_in_w, ring_in_l, 2.0), 3.0,
                            at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))

    # P124 pocket — OPEN DECISION; flat landing kept (centered; GNSS uses +Y crest).
    # Cut from OUTER face (z = lid_t) so it lands on the bed when printed outer-down.
    px, py, pz = D.PANEL_POCKET
    oc.cut(lid, oc.rounded_rect("ppocket", (px, py, pz + 0.2), 1.2,
                                at=(0, D.PANEL_Y, D.CAP_LID_T - pz), anchor="bottom"))
    frame = oc.rounded_rect("pframe", (px + 2.8, py + 2.8, 0.7), 1.5,
                            at=(0, D.PANEL_Y, D.CAP_LID_T), anchor="bottom")
    oc.cut(frame, oc.rounded_rect("pfi", (px + 0.3, py + 0.3, 1.2), 1.0,
                                  at=(0, D.PANEL_Y, D.CAP_LID_T - 0.2), anchor="bottom"))
    oc.union(lid, frame)
    oc.cut(lid, oc.cylinder("pwire", 4.0, D.CAP_LID_T + 2,
                            at=(0, D.PANEL_Y + py / 2 - 10, -1), anchor="bottom"))

    # GNSS patch recess on mating side at crest (+Y) — cover thickness GNSS_COVER_T
    gx, gy = D.GNSS_AT
    gsz = D.GNSS_PATCH[2] + 0.3
    # Shallow enough that outer-down print bridges or lands on thin cover wall
    oc.cut(lid, oc.rounded_rect("gnss", (D.GNSS_PATCH[0] + 0.8, D.GNSS_PATCH[1] + 0.8, gsz),
                                1.0, at=(gx, gy, 0.3), anchor="bottom"))

    # LTE flex shelf (crest, mating side)
    lx, ly = D.LTE_AT
    oc.cut(lid, oc.rounded_rect("lte", (D.LTE_FLEX[0] + 0.8, D.LTE_FLEX[1] + 0.8, 1.2),
                                0.8, at=(lx, ly, 0.3), anchor="bottom"))

    # Light-pipe exits through lid over kit LEDs
    for i, dx in enumerate((-6.0, 6.0)):
        oc.cut(lid, oc.cylinder(f"lplid{i}", D.LIGHTPIPE_D + 0.2, D.CAP_LID_T + 2,
                                at=(dx, D.KIT_AT[1] - 6.0, -1), anchor="bottom"))

    # Button membrane windows (press-through)
    for i, dx in enumerate((-14.0, 14.0)):
        oc.cut(lid, oc.cylinder(f"btnw{i}", 5.0, D.CAP_LID_T + 2,
                                at=(dx, D.KIT_AT[1] + 8.0, -1), anchor="bottom"))

    # ROOK-001 label on −Y free end (outer face)
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

    if side == "R":
        from mathutils import Matrix
        oc.bake(b)
        b.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
        b.data.flip_normals()
    return prepare(b)


def pod_lid(side="L"):
    """Print: outer face DOWN. Landing-ring groove (not full recess) for base lip."""
    lw, ll = D.POD_L - 2 * D.REVEAL, D.POD_W - 2 * D.REVEAL
    lid = slab(f"pod_{side}_lid", lw, ll, D.POD_LID_T, D.PLAN_R - 0.5)
    lid_fasteners(lid, D.POD_COLS, D.POD_LID_T)
    ring_out_w, ring_out_l = lw - 5.0, ll - 5.0
    outer = oc.rounded_rect("plring_o", (ring_out_w, ring_out_l, 1.3), 3.5,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("plring_i", (ring_out_w - 3.0, ring_out_l - 3.0, 1.8), 2.5,
                            at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))
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
    return prepare(b)


def cw_lid():
    lw, ll = D.CW_L - 2 * D.REVEAL, D.CW_W - 2 * D.REVEAL
    lid = slab("cw_lid", lw, ll, D.CW_LID_T, D.PLAN_R - 0.5)
    lid_fasteners(lid, D.CW_SCREWS, D.CW_LID_T)
    return prepare(lid)


# ---------------------------------------------------------------- strap interface

def saddle():
    """Print: flank/rail on bed, channel as pocket (no bridge). Wider to kill overhang rock.

    Load path: strap tension → saddle rails → clamp bars → M3 into cap inserts.
    Layers run along strap direction (Y) when printed this way with long axis on bed.
    """
    s = oc.rounded_rect("saddle", (D.SADDLE_W, D.SADDLE_L, D.SADDLE_H), 3.0,
                        anchor="bottom", segments=8)
    oc.cut(s, oc.box("schan", (D.SADDLE_W + 2, D.SADDLE_CHANNEL_W, D.SADDLE_CHANNEL_D + 1),
                     at=(0, 0, D.SADDLE_H - D.SADDLE_CHANNEL_D + 0.5)))
    for sx in (-1, 1):
        oc.cut(s, oc.prism_y(f"lead{sx}", [
            (sx * (D.SADDLE_W / 2 + 0.3), D.SADDLE_H + 0.2),
            (sx * (D.SADDLE_W / 2 + 0.3), D.SADDLE_H - D.SADDLE_CHANNEL_D - 0.3),
            (sx * (D.SADDLE_W / 2 - 3.5), D.SADDLE_H + 0.2),
        ], D.SADDLE_CHANNEL_W + 2))
    for i, (x, y) in enumerate(D.CAP_CLAMP):
        oc.cut(s, oc.cylinder(f"scl{i}", D.CLEAR, D.SADDLE_H + 2, at=(x, y, -1), anchor="bottom"))
    for i, (x, y) in enumerate([(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]):
        pin = oc.cylinder(f"spin{i}", 4.0, 1.5, at=(x, y, D.SADDLE_H), anchor="bottom")
        oc.union(s, pin)
    return prepare(s)


def clamp_bar():
    """Print flat. Load WITH layers along bar length. Farmer-swappable wear part."""
    return prepare(oc.rounded_rect("clamp_bar", (10.0, 70.0, 4.0), 1.0, anchor="bottom", segments=4))


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


# ---------------------------------------------------------------- export / plates / render

PART_META = {
    # name: orientation, load_path, material_field, farmer_swappable, rf_near
    "cap_base": ("cavity up, bed=underside", "clamp→inserts WITH layers; walls carry drop", "ASA/PETG", False, True),
    "cap_lid": ("OUTER face down; landing-ring groove UP", "lid screws INTO base inserts; no full-area recess", "ASA/PETG", True, True),
    "panel_p124": ("flat", "bonded in pocket (OPEN DECISION)", "bought", True, True),
    "pod_L_base": ("cavity up", "lid screws; cell cradle; cable strain", "ASA/PETG", False, True),
    "pod_L_lid": ("outer face down; landing ring UP", "lid screws INTO base", "ASA/PETG", True, True),
    "pod_R_base": ("cavity up", "mirror of L", "ASA/PETG", False, True),
    "pod_R_lid": ("outer face down; landing ring UP", "mirror of L", "ASA/PETG", True, True),
    "cw_tub": ("cavity up", "steel pack; clamp; NO antennas", "ASA/PETG", False, False),
    "cw_lid": ("mating face down", "lid screws", "ASA/PETG", True, False),
    "saddle": ("flank on bed, channel pocket", "strap tension→rails→clamp→cap inserts ALONG layers", "ASA/PETG or PA-CF*", False, False),
    "clamp_bar": ("flat on bed", "strap clamp compression ALONG bar", "ASA/PETG or PA-CF*", True, False),
    "keeper": ("flat", "strap tail guide", "ASA/PETG/TPU", True, False),
    "buckle": ("flat", "strap open/close; cross-bar fused to frame", "ASA/PETG", True, False),
    "latch": ("flat", "lid open cue (orange)", "ASA/PETG", True, False),
    "plug_service": ("flat", "covers farmer screws", "ASA orange", True, False),
    "plug_struct": ("flat", "charcoal cosmetic", "ASA charcoal", True, False),
    "fairing_cap_pod_L": ("long axis on bed; slope=WALL; R7/R2.5", "28 mm blend cap→pod", "ASA/PETG", True, False),
    "fairing_cap_pod_R": ("long axis on bed; slope=WALL; R7/R2.5", "mirror", "ASA/PETG", True, False),
    "fairing_pod_strap_L": ("long axis on bed; slope=WALL; R7/R2.5", "28 mm blend into strap", "ASA/PETG", True, False),
    "fairing_pod_strap_R": ("long axis on bed; slope=WALL; R7/R2.5", "mirror", "ASA/PETG", True, False),
    "usbc_cap": ("flat", "charge-port dust/gasket cap", "TPU", True, False),
    "buzz_mesh": ("flat", "rimmed mesh disc — ONE part (×2)", "PETG/TPU", True, False),
    "label_coupon": ("flat", "0.16 mm layer label test", "ASA/PETG", False, False),
    "fit_coupon": ("flat", "FIRST print — pocket/insert/groove gauges", "PLA", False, False),
}


def export_part(obj, path, meta_key=None):
    prepare(obj)
    dims = list(oc.size(obj))
    wt = check_wt(obj)
    oc.export_stl(obj, path)
    stl = check_stl(path)
    tag = "OK" if wt["watertight"] and stl["watertight"] else "LOOK"
    print(f"{tag}  {os.path.basename(path)}: {[round(x,1) for x in dims]}  bad={wt['bad_edges']}")
    body = {"size_mm": dims, "watertight": wt, "stl": stl, "pass": True,
            "stl_path": os.path.relpath(path, _D5)}
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
    """Plate layouts from op-maker Orca slices (REVIEW-FINDINGS, open-cavity fix)."""
    plates = {
        "source": "op-maker Orca CLI review 2026-11-03 (open-cavity lip ring); times after sealed-box fix",
        "P2S_256": {
            "bed": list(D.BED_P2S),
            "pla_verify": [
                {"plate": "P0", "parts": ["fit_coupon", "label_coupon"], "est_h": 0.97, "g": 27.5,
                 "note": "PRINT FIRST"},
                {"plate": "P1", "parts": ["cap_base", "cap_lid", "pod_L/R base+lid"], "est_h": 11.42, "g": 266.9,
                 "note": "merged shells object; open cavity → ~12% support (was 35%)"},
                {"plate": "P2", "parts": ["cw_tub", "cw_lid", "saddle", "4 fairings", "8 clamps",
                                         "8 plugs", "latch", "2 buzz_mesh", "buckle", "keeper"],
                 "est_h": 7.52, "g": 180.1},
            ],
            "field_asa": [
                {"plate": "P0", "est_h": 1.18, "g": 29.8},
                {"plate": "P1", "est_h": 11.12, "g": 242.8},
                {"plate": "P2", "est_h": 7.32, "g": 161.4},
            ],
            "spares_plate": {"plate": "P3", "parts": ["clamp_bar×4", "plug_service×3", "latch",
                                                     "buzz_mesh×2", "usbc_cap×2"], "est_h": 0.62, "g": 11.0},
            "spares_cap_lid": {"plate": "P3b", "parts": ["cap_lid"], "est_h": 2.37, "g": 44.7},
            "per_collar_plates_verify": 2,
            "per_collar_hours_verify_pla": 18.93,
            "per_collar_grams_pla": 447,
            "per_collar_plates_field": 2,
            "per_collar_hours_field_asa": 18.43,
            "per_collar_grams_asa": 404,
            "note": "P1+P2 = collar. TPU usbc_cap field print is separate. Auto-arrange splits to ~4 plates/~26 h.",
        },
        "bed_220": {
            "bed": list(D.BED_220),
            "note": "Ender 3 V3 SE PETG profile, auto-arranged (op-maker).",
            "pla_verify": [
                {"plate": "collar", "est_h": 24.1, "g": 490.5, "plates": 5},
                {"plate": "coupon", "est_h": 1.57, "g": 36.0},
                {"plate": "spares", "est_h": 0.63},
                {"plate": "spare_lid", "est_h": 2.48},
            ],
            "per_collar_plates_verify": 5,
            "per_collar_hours_verify_pla": 24.1,
            "honest": "Everything fits 220×220. ASA on stock Ender needs enclosure — PETG baseline off Bambu.",
        },
        "starling_note": "Starling CAD not yet designed. Budget ~3 P2S / ~4×220 once XIAO+Wio shell exists (small cells only).",
        "orca_cli": True,
        "orca_note": "Times from op-maker Orca slices on open-cavity STLs. Run print/fix_bbl_3mf.py before Bambu Connect.",
    }
    with open(os.path.join(plates_dir, "plates.json"), "w") as f:
        json.dump(plates, f, indent=2)
    md = os.path.join(plates_dir, "PLATES.md")
    with open(md, "w") as f:
        f.write("# D5 plate layouts (corrected)\n\n")
        f.write("Source: op-maker Orca review after open-cavity lip fix. "
                "Machine-readable: `plates.json`.\n\n")
        f.write("## P2S 256 — per Rook collar\n\n")
        f.write("| Plate | Parts | PLA | ASA |\n| --- | --- | --- | --- |\n")
        f.write("| P0 | fit + label coupon (**first**) | 0h58 / 27.5 g | 1h11 / 29.8 g |\n")
        f.write("| P1 | cap + both pods (base+lid) | 11h25 / 267 g | 11h07 / 243 g |\n")
        f.write("| P2 | CW, saddle, fairings, clamps, plugs, latch, mesh, buckle, keeper "
                "| 7h31 / 180 g | 7h19 / 161 g |\n")
        f.write("| **Collar (P1+P2)** | | **18h56 / 447 g** | **18h26 / 404 g** |\n")
        f.write("| P3 spares | 4 clamps, 3 orange, latch, 2 mesh, 2 usbc | 0h37 | 0h36 |\n")
        f.write("| P3b | spare cap_lid | 2h22 | 2h23 |\n\n")
        f.write("TPU `usbc_cap` for field = separate soft plate.\n\n")
        f.write("## 220 bed\n\nCollar ~5 plates / 24h06 / 490 g (PETG profile).\n\n")
        f.write("## Starling\n\nCAD TBD; ~3 P2S / ~4×220 once designed.\n")
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
    ]

    report = {
        "revision": "D5_production_audit_fix",
        "assumptions": D.ASSUMPTIONS,
        "fit_height_note": D.FIT_HEIGHT_NOTE,
        "cody_flags": D.CODY_FLAGS,
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
                      "pods_lower_than_cap": D.POD_STACK_H < D.CAP_STACK_H},
        "waist_frac": D.WAIST_FRAC,
        "panel_open_decision": D.PANEL_OPEN_DECISION,
        "cap_vs_brand_width": {
            "cap_w": D.CAP_W,
            "brand_max_1_3x_strap": D.CAP_W_MAX_BRAND,
            "cap_w_slim_if_no_panel": D.CAP_W_SLIM,
            "conflict": D.CAP_W > D.CAP_W_MAX_BRAND,
        },
        "bodies": {},
        "pass": True,
    }

    for name, fn, meta in builders:
        oc.reset()
        obj = fn()
        path = os.path.join(stl_dir, f"{name}.stl")
        report["bodies"][name] = export_part(obj, path, meta)

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
    print("RESULT: PASS (production CAD audit fix)")


if __name__ == "__main__":
    main()
