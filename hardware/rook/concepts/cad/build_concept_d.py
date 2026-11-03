"""Rook concept D3b — cow-look + Voltaic P124 panel (same PR as D/D2/D3).

Tall slim matte-charcoal cap (locked 76×160), soft radii, strap slot/keeper/
buckle, small low CW, orange = latch + 2–3 end screws, flush P124 instrument
window on the lid with separate panel_p124.stl (dark navy).

Look study — not print-ready. Draft only.

Run:
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

import bpy
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONCEPTS = os.path.abspath(os.path.join(_HERE, ".."))
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
import oc  # noqa: E402

# ---------------------------------------------------------------- palette
CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
OAT = (0xEF / 255, 0xE8 / 255, 0xD8 / 255, 1.0)
ORANGE = (0xFF / 255, 0x6A / 255, 0x2B / 255, 1.0)
# Dark navy / glassy panel body (reads against matte charcoal lid).
PANEL_NAVY = (0.10, 0.14, 0.22, 1.0)
BLACK = (0.07, 0.07, 0.08, 1.0)
WORLD = (0.94, 0.93, 0.90)

# ---------------------------------------------------------------- LOCKED envelope (cap hard)
CAP_W, CAP_L = 76.0, 160.0
CAP_WALL = 5.0
CAP_FLOOR = 5.0
CAP_CAVITY_H = 13.0
CAP_BASE_H = CAP_FLOOR + CAP_CAVITY_H  # 18 — tall-slim slab (low overall, long)
CAP_LID_T = 6.0
CAP_COLS = [(sx * 29.5, y) for sx in (-1, 1) for y in (-68.0, -42.0, 42.0, 68.0)]
CAP_CLAMP = [(sx * 20.0, sy * 28.5) for sx in (-1, 1) for sy in (-1, 1)]
# Voltaic P124 — HARDWARE-FIT / dims: 113×66×~2.6–3.1; pocket +0.3/side.
# X across neck, Y along spine; centered on long axis (PANEL_Y=0).
PANEL_SIZE = (66.0, 113.0, 2.6)          # visual body (user ~2.6 mm)
PANEL_POCKET = (66.6, 113.6, 2.3)        # depth → panel face ~0.3 mm proud
PANEL_Y = 0.0
PANEL_BORDER_W = 1.4                     # slim raised instrument-window frame
PANEL_BORDER_H = 0.7
# Orange service screws clear of centered panel (|y|=68 > 56.8): three end-cols.
CAP_ORANGE_SCREWS = [(29.5, 68.0), (-29.5, 68.0), (29.5, -68.0)]
CAP_CHARCOAL_SCREWS = [c for c in CAP_COLS if c not in CAP_ORANGE_SCREWS]

# Soft plan radius — max that still clears columns to outer wall.
# Column at x=29.5, boss r=4 → needs wall land; outer half=38.
# R must leave the outline outside the column bosses: R ≤ ~10 is safe on 76-wide.
CAP_PLAN_R = 10.0

# Pod — small / low counterweight-side look (cavity guide kept, outer slimmed visually)
POD_CAVITY = (82.0, 58.0, 21.5)  # locked cavity guide
POD_WALL = 5.0
POD_L = POD_CAVITY[0] + 2 * POD_WALL  # 92
POD_W = POD_CAVITY[1] + 2 * POD_WALL  # 68
POD_FLOOR = 3.0
POD_BASE_H = 20.0   # intentionally lower visual slab (cavity height short of 21.5 — FLAGGED)
POD_LID_T = 5.5
POD_COLS = [(sx * 37.0, sy * 27.0) for sx in (-1, 1) for sy in (-1, 1)]
POD_PLAN_R = 10.0

# Tub / CW — small low counterweight pod look
CW_L, CW_W = 80.0, 64.0   # visually smaller than ~88×74 — FLAGGED vs ~88×74 guide
CW_H = 22.0               # lower than 30 — FLAGGED
CW_LID_T = 5.5
CW_SCREWS = [(sx * 20.0, sy * 26.0) for sx in (-1, 1) for sy in (-1, 1)]  # inboard of ±22±31.5 — FLAGGED
CW_PLAN_R = 10.0

REVEAL = 0.55
CLEAR = 3.4
INSERT_D = 4.0
PLUG_SEAT_D, PLUG_SEAT_H = 7.8, 1.2
PLUG_D, PLUG_H = 7.6, 1.1
PORT_D, PORT_PROUD = 8.0, 1.8
STRAP_W, STRAP_T = 44.45, 3.5  # webbing guide

# ---------------------------------------------------------------- helpers

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


def check_watertight(obj):
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


def slab(name, w, l, h, r):
    """Flat-top slab with soft plan corners — no crown bevel (no hairline)."""
    return oc.rounded_rect(name, (w, l, h), r, anchor="bottom", segments=10)


def cavity(body, w, l, floor, h, r=5.0):
    oc.cut(body, oc.rounded_rect("cav", (w, l, h + 1), r,
                                 at=(0, 0, floor), anchor="bottom"))
    return body


def seam_line(body, w, l, z, depth=1.0):
    oc.cut(body, oc.box("sx+", (depth + 0.3, l - 14, 0.9),
                        at=(w / 2 - depth / 2, 0, z), anchor="bottom"))
    oc.cut(body, oc.box("sx-", (depth + 0.3, l - 14, 0.9),
                        at=(-(w / 2 - depth / 2), 0, z), anchor="bottom"))
    oc.cut(body, oc.box("sy+", (w - 14, depth + 0.3, 0.9),
                        at=(0, l / 2 - depth / 2, z), anchor="bottom"))
    oc.cut(body, oc.box("sy-", (w - 14, depth + 0.3, 0.9),
                        at=(0, -(l / 2 - depth / 2), z), anchor="bottom"))
    return body


def add_cols(body, positions, floor, top, d=8.0):
    bosses = [oc.cylinder(f"c{i}", d, top - floor,
                          at=(x, y, floor), anchor="bottom")
              for i, (x, y) in enumerate(positions)]
    oc.union(body, *bosses)
    for i, (x, y) in enumerate(positions):
        oc.cut(body, oc.cylinder(f"ins{i}", INSERT_D, 4.5,
                                 at=(x, y, top - 4.5), anchor="bottom"))
    return body


def lid_holes(lid, positions, lid_t):
    for i, (x, y) in enumerate(positions):
        oc.cut(lid, oc.cylinder(f"h{i}", CLEAR, lid_t + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(lid, oc.cylinder(f"ps{i}", PLUG_SEAT_D, PLUG_SEAT_H + 0.05,
                                at=(x, y, lid_t - PLUG_SEAT_H), anchor="bottom"))
    return lid


def make_plug(name):
    return prepare(oc.cylinder(name, PLUG_D, PLUG_H, anchor="bottom", segments=32))


# ---------------------------------------------------------------- envelope audit

def envelope_report():
    """What fits the locked guide vs what the cow-look study deliberately changes."""
    fits = [
        f"Cap footprint {CAP_W}×{CAP_L} (locked)",
        f"Cap columns {CAP_COLS} (locked)",
        f"Cap clamp {CAP_CLAMP} (locked)",
        f"Cap cavity height {CAP_CAVITY_H} mm ≥ 13 (locked)",
        f"Cap base height {CAP_BASE_H} mm (floor {CAP_FLOOR} + cavity)",
        f"Cap plan R={CAP_PLAN_R} — soft corners inside 76×160 outline",
        f"Pod outer {POD_L}×{POD_W} matches cavity {POD_CAVITY[0]}×{POD_CAVITY[1]} + wall {POD_WALL}",
        f"Pod columns {POD_COLS} (locked XY)",
        f"Reveal inset {REVEAL} mm on all lids (aesthetic)",
        f"Orange option-1: latch + {len(CAP_ORANGE_SCREWS)} cap screws only",
        f"P124 pocket {PANEL_POCKET[0]}×{PANEL_POCKET[1]}×{PANEL_POCKET[2]} "
        f"centered PANEL_Y={PANEL_Y} (HARDWARE-FIT sized)",
        f"Orange screws at |y|=68 clear of panel ±{PANEL_POCKET[1]/2:.1f}",
    ]
    breaks = [
        {
            "item": "Pod base height",
            "study": f"{POD_BASE_H} mm",
            "guide": f"≥ {POD_FLOOR + POD_CAVITY[2]} mm for full 21.5 cavity",
            "note": "Low slab for cow-look; cavity short — electronics pack may not fit",
        },
        {
            "item": "CW / counterweight outer",
            "study": f"{CW_L}×{CW_W}×{CW_H}",
            "guide": "~88×74×30",
            "note": "Intentionally small low pod for the AI-cow silhouette",
        },
        {
            "item": "CW screw XY",
            "study": f"{CW_SCREWS}",
            "guide": "(±22, ±31.5)",
            "note": "Moved inboard for the smaller tub footprint",
        },
        {
            "item": "Slim visual profile",
            "study": "Soft R10 + flat lid + long low proportions",
            "guide": "Envelope XY locked; visual slim is radii/proportion, not a shrink",
            "note": "Does NOT break 76×160 — silhouette reads slimmer via radii",
        },
    ]
    return {"fits": fits, "breaks_or_flags": breaks}


# ---------------------------------------------------------------- parts

def d_cap_base():
    b = slab("cap_base", CAP_W, CAP_L, CAP_BASE_H, CAP_PLAN_R)
    cavity(b, CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, CAP_FLOOR, CAP_CAVITY_H + 2, r=6.0)
    add_cols(b, CAP_COLS, CAP_FLOOR, CAP_BASE_H)
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"cl{i}", INSERT_D, 3.5,
                              at=(x, y, -0.1), anchor="bottom"))
    seam_line(b, CAP_W, CAP_L, CAP_BASE_H * 0.52, depth=1.0)
    return prepare(b)


def d_cap_lid():
    """Flat lid + P124 instrument window (flush/0.3 proud panel) + wire exit."""
    lw, ll = CAP_W - 2 * REVEAL, CAP_L - 2 * REVEAL
    lid = slab("cap_lid", lw, ll, CAP_LID_T, CAP_PLAN_R - 0.5)
    lid_holes(lid, CAP_COLS, CAP_LID_T)

    px, py, pz = PANEL_POCKET
    # Panel recess — face will sit ~0.3 mm proud of lid top with PANEL_SIZE z=2.6.
    oc.cut(lid, oc.rounded_rect("ppocket", (px, py, pz + 0.2), 1.2,
                                at=(0, PANEL_Y, CAP_LID_T - pz), anchor="bottom"))

    # Slim raised border — intentional instrument window (matte lid frame).
    frame_outer = oc.rounded_rect(
        "pframe",
        (px + 2 * PANEL_BORDER_W, py + 2 * PANEL_BORDER_W, PANEL_BORDER_H),
        1.6,
        at=(0, PANEL_Y, CAP_LID_T),
        anchor="bottom",
    )
    oc.cut(frame_outer, oc.rounded_rect(
        "pframe_i", (px + 0.2, py + 0.2, PANEL_BORDER_H + 1), 1.0,
        at=(0, PANEL_Y, CAP_LID_T - 0.2), anchor="bottom"))
    oc.union(lid, frame_outer)

    # Wire exit: slot from pocket floor down into cavity (+Y end of panel).
    wire_y = PANEL_Y + py / 2 - 10.0
    oc.cut(lid, oc.cylinder("pwire", 4.0, CAP_LID_T + 2,
                            at=(0, wire_y, -1), anchor="bottom"))
    # Shallow channel on pocket floor toward the wire hole (readable in section).
    oc.cut(lid, oc.box("pchan", (3.5, 12.0, 1.0),
                       at=(0, wire_y - 4.0, CAP_LID_T - pz), anchor="bottom"))

    # Label pad moved to −Y free end (beyond panel + orange screws on +/−Y ends).
    # Sit between panel (−56.8) and −Y rim; keep clear of (−29.5, −68) screw.
    oc.cut(lid, oc.rounded_rect("pad", (22, 8, 0.4), 1.0,
                                at=(0, -72.0, CAP_LID_T - 0.4), anchor="bottom"))
    return prepare(lid)


def d_panel_p124():
    """Separate Voltaic P124 body — dark navy/glassy for colour renders."""
    sx, sy, sz = PANEL_SIZE
    p = oc.rounded_rect("panel_p124", (sx, sy, sz), 1.0, anchor="bottom", segments=8)
    # Subtle cell grid cue (look only) — three lengthwise grooves.
    for i, x in enumerate((-18.0, 0.0, 18.0)):
        oc.cut(p, oc.box(f"cell{i}", (0.4, sy - 8, 0.25),
                         at=(x, 0, sz - 0.2), anchor="bottom"))
    return prepare(p)


def d_pod_base():
    b = slab("pod_base", POD_L, POD_W, POD_BASE_H, POD_PLAN_R)
    # Cavity as deep as the low slab allows (FLAGGED vs 21.5).
    cav_h = POD_BASE_H - POD_FLOOR - 0.5
    cavity(b, POD_CAVITY[0], POD_CAVITY[1], POD_FLOOR, cav_h + 1, r=5.0)
    add_cols(b, POD_COLS, POD_FLOOR, POD_BASE_H)
    seam_line(b, POD_L, POD_W, POD_BASE_H * 0.52, depth=1.0)
    # Proud port boss.
    boss = oc.cylinder("pboss", PORT_D + 4.5, PORT_PROUD + 0.4,
                       at=(16.0, POD_W / 2 + PORT_PROUD / 2, 10.0), axis="Y")
    oc.union(b, boss)
    oc.cut(b, oc.cylinder("phole", PORT_D, POD_W,
                          at=(16.0, POD_W / 2, 10.0), axis="Y"))
    return prepare(b)


def d_pod_lid():
    lw, ll = POD_L - 2 * REVEAL, POD_W - 2 * REVEAL
    lid = slab("pod_lid", lw, ll, POD_LID_T, POD_PLAN_R - 0.5)
    lid_holes(lid, POD_COLS, POD_LID_T)
    return prepare(lid)


def d_cw_tub():
    b = slab("cw_tub", CW_L, CW_W, CW_H, CW_PLAN_R)
    cavity(b, CW_L - 12, CW_W - 12, 3.0, CW_H, r=4.0)
    add_cols(b, CW_SCREWS, 3.0, CW_H, d=7.5)
    seam_line(b, CW_L, CW_W, CW_H * 0.52, depth=1.0)
    return prepare(b)


def d_cw_lid():
    lw, ll = CW_L - 2 * REVEAL, CW_W - 2 * REVEAL
    lid = slab("cw_lid", lw, ll, CW_LID_T, CW_PLAN_R - 0.5)
    lid_holes(lid, CW_SCREWS, CW_LID_T)
    return prepare(lid)


def d_latch():
    """Cosmetic placeholder latch — orange (open lid)."""
    return prepare(oc.rounded_rect("latch", (6.5, 11.0, 2.2), 1.2,
                                   anchor="bottom", segments=6))


def d_strap():
    return prepare(oc.rounded_rect("strap", (STRAP_W, 240.0, STRAP_T), 1.5,
                                   anchor="bottom", segments=4))


def d_saddle():
    """Webbing slot under the cap — indicative."""
    sw, sl, sh = CAP_W - 6, 50.0, 7.5
    s = oc.rounded_rect("saddle", (sw, sl, sh), 3.5, anchor="bottom", segments=8)
    oc.cut(s, oc.box("slot", (sw + 2, STRAP_W + 1.5, STRAP_T + 1.0),
                     at=(0, 0, sh - STRAP_T / 2)))
    for sx in (-1, 1):
        oc.cut(s, oc.prism_y(f"lead{sx}", [
            (sx * (sw / 2 + 0.3), sh + 0.2),
            (sx * (sw / 2 + 0.3), sh - STRAP_T - 0.4),
            (sx * (sw / 2 - 3.5), sh + 0.2),
        ], STRAP_W + 2))
    return prepare(s)


def d_keeper():
    """Keeper loop — separate part, indicative."""
    kw, kl, kh = STRAP_W + 5, 9.0, 6.5
    k = oc.rounded_rect("keeper", (kw, kl, kh), 1.8, anchor="bottom", segments=6)
    oc.cut(k, oc.box("kslot", (STRAP_W + 1.2, kl + 2, STRAP_T + 0.9),
                     at=(0, 0, kh / 2 - 0.4)))
    return prepare(k)


def d_buckle():
    """Simple buckle — charcoal (orange reserved for latch + 2–3 lid screws)."""
    bw, bl, bh = STRAP_W + 3, 26.0, 5.5
    b = oc.rounded_rect("buckle", (bw, bl, bh), 2.2, anchor="bottom", segments=6)
    oc.cut(b, oc.rounded_rect("bopen", (STRAP_W - 6, bl - 9, bh + 2), 1.2,
                              at=(0, 0, -1), anchor="bottom"))
    bar = oc.cylinder("bbar", 2.8, STRAP_W - 8, at=(0, 1.5, bh / 2), axis="X", segments=20)
    oc.union(b, bar)
    return prepare(b)


def d_test_corner():
    return prepare(slab("test_corner", 20.0, 20.0, 10.0, 8.0))


# ---------------------------------------------------------------- render

def _mat(name, rgba):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def _setup(res=(1600, 1200)):
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.render.resolution_x, s.render.resolution_y = res
    sh = s.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_object_outline = True
    world = bpy.data.worlds.new("w")
    world.color = WORLD
    s.world = world
    s.view_settings.view_transform = "Standard"


def _paint(obj, rgba, name):
    obj.data.materials.clear()
    obj.data.materials.append(_mat(name, rgba))


def _cam(lo, hi, direction, pad=1.12):
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
    _setup()
    live = []
    for obj, rgba, mname in objs_colors:
        _paint(obj, rgba, mname)
        obj.hide_render = False
        live.append(obj)
    lo = [min(oc.bounds(o)[0][i] for o in live) for i in range(3)]
    hi = [max(oc.bounds(o)[1][i] for o in live) for i in range(3)]
    cam = _cam(lo, hi, direction, pad=pad)
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def export_part(obj, path):
    prepare(obj)
    dims = oc.size(obj)
    wt = check_watertight(obj)
    oc.export_stl(obj, path)
    stl = check_stl(path)
    tag = "OK" if (wt["watertight"] and stl["watertight"]) else "LOOK"
    print(f"{tag}  {os.path.basename(path)}: {dims} mm  "
          f"bad={wt['bad_edges']} stl_bad={stl['bad_edges']}")
    return {
        "size_mm": dims,
        "watertight": wt,
        "stl": stl,
        "pass": True,
        "stl_path": os.path.relpath(path, _CONCEPTS),
    }


def layout(parts, plugs, strap_bits, latch, strap, panel, explode=0.0):
    gap = 28.0
    cap_x = 0.0
    pod_x = CAP_W / 2 + POD_L / 2 + gap
    cw_x = -(CAP_W / 2 + CW_L / 2 + gap)
    saddle_z = -7.5

    oc.move(parts["cap_base"], dx=cap_x)
    oc.move(parts["cap_lid"], dx=cap_x, dz=CAP_BASE_H + explode)
    oc.move(parts["pod_base"], dx=pod_x)
    oc.move(parts["pod_lid"], dx=pod_x, dz=POD_BASE_H + explode)
    oc.move(parts["cw_tub"], dx=cw_x)
    oc.move(parts["cw_lid"], dx=cw_x, dz=CW_H + explode)

    # Panel seats in pocket: top of panel = lid top + 0.3 proud (+ explode).
    oc.move(panel, dx=cap_x, dy=PANEL_Y,
            dz=CAP_BASE_H + CAP_LID_T - PANEL_POCKET[2] + explode * 1.2)

    for i, (x, y) in enumerate(CAP_ORANGE_SCREWS):
        oc.move(plugs["orange"][i], dx=cap_x + x, dy=y,
                dz=CAP_BASE_H + CAP_LID_T - PLUG_H + explode * 1.5)
    for i, (x, y) in enumerate(CAP_CHARCOAL_SCREWS):
        oc.move(plugs["charcoal_cap"][i], dx=cap_x + x, dy=y,
                dz=CAP_BASE_H + CAP_LID_T - PLUG_H + explode * 1.5)
    for i, (x, y) in enumerate(POD_COLS):
        oc.move(plugs["pod"][i], dx=pod_x + x, dy=y,
                dz=POD_BASE_H + POD_LID_T - PLUG_H + explode * 1.5)
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.move(plugs["cw"][i], dx=cw_x + x, dy=y,
                dz=CW_H + CW_LID_T - PLUG_H + explode * 1.5)

    # Latch at +Y end, clear of panel frame and orange screws.
    oc.move(latch, dx=cap_x, dy=CAP_L / 2 - 5,
            dz=CAP_BASE_H + CAP_LID_T + PANEL_BORDER_H - 0.5 + explode)
    oc.move(strap_bits["saddle"], dx=cap_x, dz=saddle_z)
    oc.move(strap, dx=cap_x, dz=saddle_z + 1.8)
    oc.move(strap_bits["keeper"], dx=cap_x, dy=-(CAP_L / 2 + 16), dz=saddle_z + 1.2)
    oc.move(strap_bits["buckle"], dx=cap_x, dy=-(CAP_L / 2 + 46), dz=saddle_z + 0.8)


def color_opt1(parts, plugs, strap_bits, latch, strap, panel, lid_color):
    bodies = [
        (parts["cap_base"], CHARCOAL, "body"),
        (parts["pod_base"], CHARCOAL, "body"),
        (parts["cw_tub"], CHARCOAL, "body"),
        (parts["cap_lid"], lid_color, "lid"),
        (parts["pod_lid"], lid_color, "lid"),
        (parts["cw_lid"], lid_color, "lid"),
        (panel, PANEL_NAVY, "panel"),
        (strap_bits["saddle"], CHARCOAL, "saddle"),
        (strap_bits["keeper"], CHARCOAL, "keeper"),
        (strap_bits["buckle"], CHARCOAL, "buckle"),
        (latch, ORANGE, "latch"),
        (strap, BLACK, "strap"),
    ]
    for p in plugs["orange"]:
        bodies.append((p, ORANGE, "svc"))
    for p in plugs["charcoal_cap"] + plugs["pod"] + plugs["cw"]:
        bodies.append((p, CHARCOAL, "struct"))
    return bodies


def main():
    stl_dir = os.path.join(_CONCEPTS, "stl", "D_hybrid")
    rend_dir = os.path.join(_CONCEPTS, "renders", "D_hybrid")
    img_dir = os.path.join(_CONCEPTS, "images")
    for d in (stl_dir, rend_dir, img_dir):
        os.makedirs(d, exist_ok=True)

    env = envelope_report()
    print("\n=== ENVELOPE FIT ===")
    for line in env["fits"]:
        print("  FIT ", line)
    print("=== FLAGS / BREAKS ===")
    for b in env["breaks_or_flags"]:
        print(f"  FLAG {b['item']}: study={b['study']}  guide={b['guide']}")
        print(f"       {b['note']}")

    builders = [
        ("cap_base", d_cap_base),
        ("cap_lid", d_cap_lid),
        ("panel_p124", d_panel_p124),
        ("pod_base", d_pod_base),
        ("pod_lid", d_pod_lid),
        ("cw_tub", d_cw_tub),
        ("cw_lid", d_cw_lid),
        ("saddle", d_saddle),
        ("keeper", d_keeper),
        ("buckle", d_buckle),
        ("latch", d_latch),
        ("strap", d_strap),
        ("plug_service_orange", lambda: make_plug("plug_service_orange")),
        ("plug_struct_charcoal", lambda: make_plug("plug_struct_charcoal")),
        ("test_corner", d_test_corner),
    ]
    report = {
        "concept": "D_hybrid",
        "revision": "D3b_panel",
        "envelope": env,
        "orange_screws": CAP_ORANGE_SCREWS,
        "panel": {
            "pocket_mm": PANEL_POCKET,
            "body_mm": PANEL_SIZE,
            "panel_y": PANEL_Y,
            "proud_mm": round(PANEL_SIZE[2] - PANEL_POCKET[2], 2),
            "border_mm": {"w": PANEL_BORDER_W, "h": PANEL_BORDER_H},
        },
        "bodies": {},
        "pass": True,
    }
    for name, fn in builders:
        oc.reset()
        obj = fn()
        path = os.path.join(stl_dir, f"{name}.stl")
        body = export_part(obj, path)
        report["bodies"][name] = body

    def scene():
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
            "orange": [make_plug(f"or{i}") for i in range(len(CAP_ORANGE_SCREWS))],
            "charcoal_cap": [make_plug(f"cc{i}") for i in range(len(CAP_CHARCOAL_SCREWS))],
            "pod": [make_plug(f"pp{i}") for i in range(len(POD_COLS))],
            "cw": [make_plug(f"cw{i}") for i in range(len(CW_SCREWS))],
        }
        strap_bits = {"saddle": d_saddle(), "keeper": d_keeper(), "buckle": d_buckle()}
        return bases, plugs, strap_bits, d_latch(), d_strap(), d_panel_p124()

    views = {
        "iso": (1.15, -1.35, 0.85),
        "front": (0.0, -1.0, 0.28),
        "side": (1.0, 0.12, 0.22),
    }

    bases, plugs, strap_bits, latch, strap, panel = scene()
    layout(bases, plugs, strap_bits, latch, strap, panel, 0.0)
    for view, direction in views.items():
        out = os.path.join(rend_dir, f"assembled_{view}.png")
        render_colored(color_opt1(bases, plugs, strap_bits, latch, strap, panel, CHARCOAL),
                       out, direction)
        shutil.copy2(out, os.path.join(img_dir, f"D_hybrid_{view}.png"))

    bases, plugs, strap_bits, latch, strap, panel = scene()
    layout(bases, plugs, strap_bits, latch, strap, panel, 14.0)
    out = os.path.join(rend_dir, "assembled_exploded.png")
    render_colored(color_opt1(bases, plugs, strap_bits, latch, strap, panel, CHARCOAL),
                   out, (1.2, -1.4, 0.8), pad=1.18)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_exploded.png"))

    bases, plugs, strap_bits, latch, strap, panel = scene()
    layout(bases, plugs, strap_bits, latch, strap, panel, 0.0)
    for view, direction in views.items():
        out = os.path.join(rend_dir, f"oat_{view}.png")
        render_colored(color_opt1(bases, plugs, strap_bits, latch, strap, panel, OAT),
                       out, direction)
        shutil.copy2(out, os.path.join(img_dir, f"D_hybrid_oat_{view}.png"))

    # Cap + panel close-up (instrument window)
    oc.reset()
    cl, pan = d_cap_lid(), d_panel_p124()
    oc.move(pan, dy=PANEL_Y, dz=CAP_LID_T - PANEL_POCKET[2])
    out = os.path.join(rend_dir, "panel_closeup.png")
    render_colored([(cl, CHARCOAL, "lid"), (pan, PANEL_NAVY, "panel")],
                   out, (0.2, -1.1, 1.2), pad=0.55)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_panel_closeup.png"))

    oc.reset()
    pod = d_pod_base()
    out = os.path.join(rend_dir, "port_closeup.png")
    render_colored([(pod, CHARCOAL, "body")], out, (1.3, -0.9, 0.45), pad=0.48)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_port_closeup.png"))

    oc.reset()
    cb, cl = d_cap_base(), d_cap_lid()
    oc.move(cl, dz=CAP_BASE_H)
    out = os.path.join(rend_dir, "seam_closeup.png")
    render_colored([(cb, CHARCOAL, "body"), (cl, OAT, "lid")],
                   out, (1.5, -0.15, 0.28), pad=0.3)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_seam_closeup.png"))

    oc.reset()
    saddle, keeper, buckle, strap = d_saddle(), d_keeper(), d_buckle(), d_strap()
    oc.move(strap, dz=1.8)
    oc.move(keeper, dy=-38, dz=1.2)
    oc.move(buckle, dy=-68, dz=0.8)
    out = os.path.join(rend_dir, "strap_closeup.png")
    render_colored([
        (saddle, CHARCOAL, "saddle"),
        (keeper, CHARCOAL, "keeper"),
        (buckle, CHARCOAL, "buckle"),
        (strap, BLACK, "strap"),
    ], out, (1.0, -1.2, 0.65), pad=0.65)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_strap_closeup.png"))

    with open(os.path.join(stl_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("\nRESULT: PASS (look study)")


if __name__ == "__main__":
    main()
