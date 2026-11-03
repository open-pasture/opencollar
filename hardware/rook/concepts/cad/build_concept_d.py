"""Rook concept D3 — look-first hybrid (design / aesthetics iteration).

Cody: structures do NOT need to be fully printable yet. Prioritize look —
slim tall soft-radius cap, visible waist seam, strap saddle + keeper + buckle,
option-1 orange (open/replace only), clean lid tops, proud pod port boss.
Hardware envelope is a rough size guide, not a hard constraint.

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
BLACK = (0.07, 0.07, 0.08, 1.0)
WORLD = (0.94, 0.93, 0.90)

# ---------------------------------------------------------------- rough envelope (guide, not hard)
CAP_W, CAP_L = 72.0, 156.0          # slimmed vs 76×160
CAP_WALL = 5.0
CAP_FLOOR = 5.0
CAP_CAVITY_H = 14.0
CAP_BASE_H = 22.0                   # slim-tall: a bit more vertical presence
CAP_LID_T = 7.0
CAP_COLS = [(sx * 28.0, y) for sx in (-1, 1) for y in (-64.0, -40.0, 40.0, 64.0)]
CAP_SERVICE = [(sx * 28.0, sy * 40.0) for sx in (-1, 1) for sy in (-1, 1)]  # orange
CAP_STRUCT = [(sx * 28.0, sy * 64.0) for sx in (-1, 1) for sy in (-1, 1)]   # charcoal

POD_L, POD_W, POD_H = 90.0, 66.0, 26.0
POD_LID_T = 8.0
POD_COLS = [(sx * 35.0, sy * 25.0) for sx in (-1, 1) for sy in (-1, 1)]

CW_L, CW_W, CW_H = 86.0, 72.0, 30.0
CW_LID_T = 9.0
CW_SCREWS = [(sx * 22.0, sy * 28.0) for sx in (-1, 1) for sy in (-1, 1)]

PLAN_R = 11.0           # soft organic plan family
REVEAL = 0.6            # visible inset seam
CLEAR = 3.4
INSERT_D = 4.0
PLUG_SEAT_D, PLUG_SEAT_H = 8.0, 1.3
PLUG_D, PLUG_H = 7.8, 1.2
PORT_D, PORT_PROUD = 8.0, 2.0
STRAP_W, STRAP_T = 44.0, 3.5

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


def soft_shell(name, size, r, h_override=None):
    """Soft plan-corner shell. Flat top (no crown bevel → no hairline)."""
    sx, sy, sz = size
    if h_override is not None:
        sz = h_override
    return oc.rounded_rect(name, (sx, sy, sz), min(r, min(sx, sy) / 2 - 0.5),
                           anchor="bottom", segments=10)


def cavity(body, w, l, floor, h, r=6.0):
    oc.cut(body, oc.rounded_rect("cav", (w, l, h + 1), r,
                                 at=(0, 0, floor), anchor="bottom"))
    return body


def seam_groove(body, w, l, z, depth=1.0):
    """Visible waist shadow line on the base (reads as the parting datum)."""
    oc.cut(body, oc.box("sx+", (depth + 0.4, l - 12, 1.0),
                        at=(w / 2 - depth / 2, 0, z), anchor="bottom"))
    oc.cut(body, oc.box("sx-", (depth + 0.4, l - 12, 1.0),
                        at=(-(w / 2 - depth / 2), 0, z), anchor="bottom"))
    oc.cut(body, oc.box("sy+", (w - 12, depth + 0.4, 1.0),
                        at=(0, l / 2 - depth / 2, z), anchor="bottom"))
    oc.cut(body, oc.box("sy-", (w - 12, depth + 0.4, 1.0),
                        at=(0, -(l / 2 - depth / 2), z), anchor="bottom"))
    return body


def groove_oring(body, w, l, r, z_top, wall=5.0):
    g, gd = 2.6, 1.5
    inset = wall / 2
    outer = oc.rounded_rect("go", (w - 2 * (inset - g / 2), l - 2 * (inset - g / 2), gd + 1),
                            max(r - inset + g / 2, 1.0), at=(0, 0, z_top - gd), anchor="bottom")
    inner = oc.rounded_rect("gi", (w - 2 * (inset + g / 2), l - 2 * (inset + g / 2), gd + 3),
                            max(r - inset - g / 2, 0.8), at=(0, 0, z_top - gd - 1), anchor="bottom")
    oc.cut(body, oc.cut(outer, inner))
    return body


def cols(body, positions, floor, top):
    bosses = [oc.cylinder(f"c{i}", 7.5, top - floor,
                          at=(x, y, floor), anchor="bottom")
              for i, (x, y) in enumerate(positions)]
    oc.union(body, *bosses)
    for i, (x, y) in enumerate(positions):
        oc.cut(body, oc.cylinder(f"ins{i}", INSERT_D, 4.5,
                                 at=(x, y, top - 4.5), anchor="bottom"))
    return body


def lid_plugs(lid, positions, lid_t):
    for i, (x, y) in enumerate(positions):
        oc.cut(lid, oc.cylinder(f"h{i}", CLEAR, lid_t + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(lid, oc.cylinder(f"ps{i}", PLUG_SEAT_D, PLUG_SEAT_H + 0.05,
                                at=(x, y, lid_t - PLUG_SEAT_H), anchor="bottom"))
    return lid


def make_plug(name):
    return prepare(oc.cylinder(name, PLUG_D, PLUG_H, anchor="bottom", segments=32))


def mono_text(name, body, size, depth, at):
    """Tiny 5×7 ROOK-001 cutter — look only."""
    font = {
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
        "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
        "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    }
    cell = size / 7.0
    cw = 5 * cell + cell * 0.2
    chars = list(body.upper())
    width = len(chars) * cw
    x0 = at[0] - width / 2
    y0 = at[1] - size / 2
    pixels = []
    for ci, ch in enumerate(chars):
        glyph = font.get(ch, font["-"])
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit != "1":
                    continue
                pixels.append(oc.box(
                    f"{name}_{ci}_{row}_{col}",
                    (cell * 0.9, cell * 0.9, depth),
                    at=(x0 + ci * cw + (col + 0.5) * cell,
                        y0 + (6 - row + 0.5) * cell, at[2]),
                    anchor="bottom"))
    if not pixels:
        return oc.box(name, (1, 1, depth), at=at, anchor="bottom")
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for p in pixels:
        p.select_set(True)
    bpy.context.view_layer.objects.active = pixels[0]
    bpy.ops.object.join()
    pixels[0].name = name
    return pixels[0]


# ---------------------------------------------------------------- parts

def d_cap_base():
    b = soft_shell("cap_base", (CAP_W, CAP_L, CAP_BASE_H), PLAN_R)
    cavity(b, CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, CAP_FLOOR, CAP_CAVITY_H + 2)
    cols(b, CAP_COLS, CAP_FLOOR, CAP_BASE_H)
    groove_oring(b, CAP_W, CAP_L, PLAN_R, CAP_BASE_H)
    seam_groove(b, CAP_W, CAP_L, CAP_BASE_H * 0.55, depth=1.1)
    return prepare(b)


def d_cap_lid():
    """Clean flat top — soft plan corners only, no crown bevel (no hairline)."""
    lw, ll = CAP_W - 2 * REVEAL, CAP_L - 2 * REVEAL
    lid = oc.rounded_rect("cap_lid", (lw, ll, CAP_LID_T), PLAN_R - 1.0,
                          anchor="bottom", segments=10)
    lid_plugs(lid, CAP_COLS, CAP_LID_T)
    # Label pad; mono text as separate look cue (simple bar marks, not glyph boolean).
    oc.cut(lid, oc.rounded_rect("pad", (28, 11, 0.5), 1.0,
                                at=(0, 0, CAP_LID_T - 0.5), anchor="bottom"))
    # Seven short bars reading as ROOK-001 placeholder at a glance.
    for i, x in enumerate((-10.5, -7.0, -3.5, 0.0, 3.5, 7.0, 10.5)):
        oc.cut(lid, oc.box(f"mark{i}", (2.2, 5.0, 0.55),
                           at=(x, 0, CAP_LID_T - 0.5 - 0.55), anchor="bottom"))
    return prepare(lid)


def d_pod_base():
    b = soft_shell("pod_base", (POD_L, POD_W, POD_H), PLAN_R)
    cavity(b, POD_L - 12, POD_W - 12, 3.0, POD_H)
    cols(b, POD_COLS, 3.0, POD_H)
    groove_oring(b, POD_L, POD_W, PLAN_R, POD_H)
    seam_groove(b, POD_L, POD_W, POD_H * 0.55, depth=1.1)
    # Proud port boss on +Y — clearly visible.
    boss = oc.cylinder("pboss", PORT_D + 5.0, PORT_PROUD + 0.5,
                       at=(16.0, POD_W / 2 + PORT_PROUD / 2, 12.0), axis="Y")
    oc.union(b, boss)
    oc.cut(b, oc.cylinder("phole", PORT_D, POD_W,
                          at=(16.0, POD_W / 2, 12.0), axis="Y"))
    oc.cut(b, oc.cylinder("pgask", PORT_D + 3.0, 0.9,
                          at=(16.0, POD_W / 2 + PORT_PROUD - 0.4, 12.0), axis="Y"))
    # Cable boss on +X
    cb = oc.cylinder("cboss", 6.0 + 4.5, PORT_PROUD + 0.5,
                     at=(POD_L / 2 + PORT_PROUD / 2, -4.0, 13.0), axis="X")
    oc.union(b, cb)
    oc.cut(b, oc.cylinder("chole", 6.0, POD_L,
                          at=(POD_L / 2, -4.0, 13.0), axis="X"))
    return prepare(b)


def d_pod_lid():
    lw, ll = POD_L - 2 * REVEAL, POD_W - 2 * REVEAL
    lid = oc.rounded_rect("pod_lid", (lw, ll, POD_LID_T), PLAN_R - 1.0,
                          anchor="bottom", segments=10)
    lid_plugs(lid, POD_COLS, POD_LID_T)
    return prepare(lid)


def d_cw_tub():
    b = soft_shell("cw_tub", (CW_L, CW_W, CW_H), PLAN_R)
    cavity(b, CW_L - 14, CW_W - 14, 3.0, CW_H)
    cols(b, CW_SCREWS, 3.0, CW_H)
    groove_oring(b, CW_L, CW_W, PLAN_R, CW_H)
    seam_groove(b, CW_L, CW_W, CW_H * 0.55, depth=1.1)
    return prepare(b)


def d_cw_lid():
    lw, ll = CW_L - 2 * REVEAL, CW_W - 2 * REVEAL
    lid = oc.rounded_rect("cw_lid", (lw, ll, CW_LID_T), PLAN_R - 1.0,
                          anchor="bottom", segments=10)
    lid_plugs(lid, CW_SCREWS, CW_LID_T)
    return prepare(lid)


def d_latch():
    """Cosmetic placeholder — final = flush recessed pull, still orange."""
    return prepare(oc.rounded_rect("latch", (7.0, 12.0, 2.5), 1.2,
                                   anchor="bottom", segments=6))


def d_strap():
    return prepare(oc.rounded_rect("strap", (STRAP_W, 220.0, STRAP_T), 2.0,
                                   anchor="bottom", segments=4))


def d_saddle():
    """Printed strap saddle under the cap — slot for the strap."""
    sw, sl, sh = CAP_W - 4, 52.0, 8.0
    s = oc.rounded_rect("saddle", (sw, sl, sh), 4.0, anchor="bottom", segments=8)
    # Strap channel through (slot).
    oc.cut(s, oc.box("slot", (sw + 2, STRAP_W + 1.5, STRAP_T + 1.2),
                     at=(0, 0, sh - STRAP_T / 2 - 0.2)))
    # Soft lead-ins on ±X.
    for sx in (-1, 1):
        oc.cut(s, oc.prism_y(f"lead{sx}", [
            (sx * (sw / 2 + 0.3), sh + 0.2),
            (sx * (sw / 2 + 0.3), sh - STRAP_T - 0.5),
            (sx * (sw / 2 - 4.0), sh + 0.2),
        ], STRAP_W + 2))
    return prepare(s)


def d_keeper():
    """Strap keeper loop — sits on the strap aft of the saddle."""
    kw, kl, kh = STRAP_W + 6, 10.0, 7.0
    k = oc.rounded_rect("keeper", (kw, kl, kh), 2.0, anchor="bottom", segments=6)
    oc.cut(k, oc.box("kslot", (STRAP_W + 1.5, kl + 2, STRAP_T + 1.0),
                     at=(0, 0, kh / 2 - 0.5)))
    return prepare(k)


def d_buckle():
    """Collar buckle — open/replace → orange per brand option 1."""
    bw, bl, bh = STRAP_W + 4, 28.0, 6.0
    b = oc.rounded_rect("buckle", (bw, bl, bh), 2.5, anchor="bottom", segments=6)
    # Frame opening.
    oc.cut(b, oc.rounded_rect("bopen", (STRAP_W - 4, bl - 10, bh + 2), 1.5,
                              at=(0, 0, -1), anchor="bottom"))
    # Crossbar.
    bar = oc.cylinder("bbar", 3.0, STRAP_W - 6, at=(0, 2.0, bh / 2), axis="X", segments=24)
    oc.union(b, bar)
    return prepare(b)


def d_test_corner():
    c = soft_shell("test_corner", (20.0, 20.0, 10.0), 8.0)
    return prepare(c)


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
    """Look study export — watertight is reported but does not block the build."""
    prepare(obj)
    dims = oc.size(obj)
    wt = check_watertight(obj)
    oc.export_stl(obj, path)
    stl = check_stl(path)
    ok = True  # D3 look-first: geometry for aesthetics, not print gate
    tag = "OK" if (wt["watertight"] and stl["watertight"]) else "LOOK"
    print(f"{tag}  {os.path.basename(path)}: {dims} mm  "
          f"bad={wt['bad_edges']} stl_bad={stl['bad_edges']}")
    return {
        "size_mm": dims,
        "watertight": wt,
        "stl": stl,
        "pass": ok,
        "stl_path": os.path.relpath(path, _CONCEPTS),
    }


def layout(parts, plugs, strap_bits, latch, strap, explode=0.0):
    gap = 30.0
    cap_x = 0.0
    pod_x = CAP_W / 2 + POD_L / 2 + gap
    cw_x = -(CAP_W / 2 + CW_L / 2 + gap)
    saddle_z = -8.0

    oc.move(parts["cap_base"], dx=cap_x)
    oc.move(parts["cap_lid"], dx=cap_x, dz=CAP_BASE_H + explode)
    oc.move(parts["pod_base"], dx=pod_x)
    oc.move(parts["pod_lid"], dx=pod_x, dz=POD_H + explode)
    oc.move(parts["cw_tub"], dx=cw_x)
    oc.move(parts["cw_lid"], dx=cw_x, dz=CW_H + explode)

    for i, (x, y) in enumerate(CAP_SERVICE):
        oc.move(plugs["service"][i], dx=cap_x + x, dy=y,
                dz=CAP_BASE_H + CAP_LID_T - PLUG_H + explode * 1.5)
    for i, (x, y) in enumerate(CAP_STRUCT):
        oc.move(plugs["struct"][i], dx=cap_x + x, dy=y,
                dz=CAP_BASE_H + CAP_LID_T - PLUG_H + explode * 1.5)
    for i, (x, y) in enumerate(POD_COLS):
        oc.move(plugs["pod"][i], dx=pod_x + x, dy=y,
                dz=POD_H + POD_LID_T - PLUG_H + explode * 1.5)
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.move(plugs["cw"][i], dx=cw_x + x, dy=y,
                dz=CW_H + CW_LID_T - PLUG_H + explode * 1.5)

    oc.move(latch, dx=cap_x, dy=CAP_L / 2 - 8, dz=CAP_BASE_H + CAP_LID_T - 1 + explode)
    oc.move(strap_bits["saddle"], dx=cap_x, dz=saddle_z)
    oc.move(strap, dx=cap_x, dz=saddle_z + 2.0)
    oc.move(strap_bits["keeper"], dx=cap_x, dy=-(CAP_L / 2 + 18), dz=saddle_z + 1.5)
    oc.move(strap_bits["buckle"], dx=cap_x, dy=-(CAP_L / 2 + 48), dz=saddle_z + 1.0)


def color_opt1(parts, plugs, strap_bits, latch, strap, lid_color):
    bodies = [
        (parts["cap_base"], CHARCOAL, "body"),
        (parts["pod_base"], CHARCOAL, "body"),
        (parts["cw_tub"], CHARCOAL, "body"),
        (parts["cap_lid"], lid_color, "lid"),
        (parts["pod_lid"], lid_color, "lid"),
        (parts["cw_lid"], lid_color, "lid"),
        (strap_bits["saddle"], CHARCOAL, "saddle"),
        (strap_bits["keeper"], CHARCOAL, "keeper"),
        (strap_bits["buckle"], ORANGE, "buckle"),   # open collar
        (latch, ORANGE, "latch"),                     # open lid
        (strap, BLACK, "strap"),
    ]
    for p in plugs["service"]:
        bodies.append((p, ORANGE, "svc"))
    for p in plugs["struct"] + plugs["pod"] + plugs["cw"]:
        bodies.append((p, CHARCOAL, "struct"))
    return bodies


def main():
    stl_dir = os.path.join(_CONCEPTS, "stl", "D_hybrid")
    rend_dir = os.path.join(_CONCEPTS, "renders", "D_hybrid")
    img_dir = os.path.join(_CONCEPTS, "images")
    for d in (stl_dir, rend_dir, img_dir):
        os.makedirs(d, exist_ok=True)

    # Clear stale D1/D2 plug names.
    for stale in ("plug.stl", "plug_opt2_dark_orange.stl", "label_coupon.stl"):
        p = os.path.join(stl_dir, stale)
        if os.path.isfile(p):
            os.remove(p)

    builders = [
        ("cap_base", d_cap_base),
        ("cap_lid", d_cap_lid),
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
    report = {"concept": "D_hybrid", "revision": "D3_look", "bodies": {}, "pass": True}
    for name, fn in builders:
        oc.reset()
        obj = fn()
        path = os.path.join(stl_dir, f"{name}.stl")
        body = export_part(obj, path)
        report["bodies"][name] = body
        report["pass"] &= body["pass"]

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
            "service": [make_plug(f"svc{i}") for i in range(4)],
            "struct": [make_plug(f"str{i}") for i in range(4)],
            "pod": [make_plug(f"pp{i}") for i in range(4)],
            "cw": [make_plug(f"cw{i}") for i in range(4)],
        }
        strap_bits = {"saddle": d_saddle(), "keeper": d_keeper(), "buckle": d_buckle()}
        latch = d_latch()
        strap = d_strap()
        return bases, plugs, strap_bits, latch, strap

    views = {
        "iso": (1.15, -1.35, 0.9),
        "front": (0.0, -1.0, 0.3),
        "side": (1.0, 0.15, 0.25),
    }

    bases, plugs, strap_bits, latch, strap = scene()
    layout(bases, plugs, strap_bits, latch, strap, explode=0.0)
    for view, direction in views.items():
        out = os.path.join(rend_dir, f"assembled_{view}.png")
        render_colored(color_opt1(bases, plugs, strap_bits, latch, strap, CHARCOAL),
                       out, direction)
        shutil.copy2(out, os.path.join(img_dir, f"D_hybrid_{view}.png"))

    bases, plugs, strap_bits, latch, strap = scene()
    layout(bases, plugs, strap_bits, latch, strap, explode=16.0)
    out = os.path.join(rend_dir, "assembled_exploded.png")
    render_colored(color_opt1(bases, plugs, strap_bits, latch, strap, CHARCOAL),
                   out, (1.2, -1.4, 0.85), pad=1.2)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_exploded.png"))

    bases, plugs, strap_bits, latch, strap = scene()
    layout(bases, plugs, strap_bits, latch, strap, explode=0.0)
    for view, direction in views.items():
        out = os.path.join(rend_dir, f"oat_{view}.png")
        render_colored(color_opt1(bases, plugs, strap_bits, latch, strap, OAT),
                       out, direction)
        shutil.copy2(out, os.path.join(img_dir, f"D_hybrid_oat_{view}.png"))

    # Port close-up
    oc.reset()
    pod = d_pod_base()
    out = os.path.join(rend_dir, "port_closeup.png")
    render_colored([(pod, CHARCOAL, "body")], out, (1.3, -0.9, 0.5), pad=0.5)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_port_closeup.png"))

    # Seam close-up
    oc.reset()
    cb, cl = d_cap_base(), d_cap_lid()
    oc.move(cl, dz=CAP_BASE_H)
    out = os.path.join(rend_dir, "seam_closeup.png")
    render_colored([(cb, CHARCOAL, "body"), (cl, OAT, "lid")],
                   out, (1.5, -0.2, 0.3), pad=0.32)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_seam_closeup.png"))

    # Strap hardware close-up
    oc.reset()
    saddle, keeper, buckle, strap = d_saddle(), d_keeper(), d_buckle(), d_strap()
    oc.move(strap, dz=2.0)
    oc.move(keeper, dy=-40, dz=1.5)
    oc.move(buckle, dy=-70, dz=1.0)
    out = os.path.join(rend_dir, "strap_closeup.png")
    render_colored([
        (saddle, CHARCOAL, "saddle"),
        (keeper, CHARCOAL, "keeper"),
        (buckle, ORANGE, "buckle"),
        (strap, BLACK, "strap"),
    ], out, (1.0, -1.2, 0.7), pad=0.7)
    shutil.copy2(out, os.path.join(img_dir, "D_hybrid_strap_closeup.png"))

    with open(os.path.join(stl_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("\nRESULT:", "PASS" if report["pass"] else "FAIL")
    if not report["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
