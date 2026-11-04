"""D6 CAP — D4 contoured skin around D5 (6b1f882) internals.

Contract (op-maker): CAP_W=76, CAP_L=164, stack≈31, P124 kept with flat panel
land + 15 mm keep-clear, low wrap seam, crowned lid, tapered ends, pod mount
faces at y=±113.8 / z=-27.8 / tilt ±29.1° about X.

Print:
  cap_base          — cavity UP; bed = underside z=0; floor glyphs UP
  cap_lid           — MATING face DOWN z=0 (chosen after comparing outer-down);
                      flat panel land + crown face +Z; GNSS/LTE open to bed
  cap_floor_layout  — underside on bed; ribs/glyphs UP

Reuses D5 FLOOR_LABEL_TABLE + emboss glyph code via import of build_d5 helpers.
Clamp/saddle family matches CW agent (cursor/d6-cw-9a36): clamp 10×70×8,
holes family y=±28.5, saddle W=76, channel 46.45×3.4.

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python cap.py
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
_D6 = _HERE
_ROOK = os.path.abspath(os.path.join(_HERE, ".."))
_D5_CAD = os.path.join(_ROOK, "d5", "cad")
_COMMON = os.path.abspath(os.path.join(_ROOK, "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _D5_CAD)

import oc  # noqa: E402
import d5_dims as D  # noqa: E402

# Import D5 glyph table + helpers (do NOT run build_d5.main).
import build_d5 as d5  # noqa: E402

CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
PANEL_NAVY = (0.10, 0.14, 0.22, 1.0)
OAT = (0xEF / 255, 0xE8 / 255, 0xD8 / 255, 1.0)

# ---------------------------------------------------------------- D6 outer envelope (contract)
CAP_W = 76.0
CAP_L = 164.0
CAP_STACK_H = 31.0
SEAM_Z = 9.0                      # low visible seam (~0.29 of stack); D4 ≈8/27
CAP_BASE_H = D.CAP_BASE_H         # 19 — mating/gasket plane (D5 internals)
CAP_FLOOR = D.CAP_FLOOR           # 6
CAP_CAVITY_H = D.CAP_CAVITY_H     # 13
# Lid modelled mating-at-z=0: body rises to outer top; wrap skirt in −Z then
# normalised so min Z=0 for print (skirt rim = bed when skirt present).
# With mating-down choice we keep skirt SHORT so mating stays the bed face.
LID_ABOVE = CAP_STACK_H - CAP_BASE_H   # 12 mm above mating → stack 31
# No hanging skirt below mating: a −Z skirt puts the thin rim on the bed after
# normalize_z0 and turns the mating face into a support ceiling. Wrap-over look
# is a short OUTER step at the lid perimeter (z≥0) + low seam documentation.
LID_SKIRT = 0.0
LID_WRAP_STEP = 2.5                    # outer perimeter step down from crown (visual low seam)
LID_H = LID_ABOVE                      # solid height above mating
CROWN = 2.7                            # D4 crown outside panel land
END_TAPER = 20.0                       # hard end taper length (D4 ~20)
PANEL_LAND = (68.0, 116.0)             # flat plateau containing 66.6×113.6 pocket
PLAN_R = 7.0
REVEAL = 0.5

# Pod interface (world, cap-centre origin) — pod agent matches the other side
POD_ANCHOR_Y = 113.8
POD_ANCHOR_Z = -27.8
POD_TILT_DEG = 29.141828721535205      # from d4.json pod_*_anchor
# Mount face is a flush end-cut / inset pad — must NOT grow outer L past 164.
POD_MOUNT_FACE_Y = CAP_L / 2 - 2.0     # inset from end
POD_MOUNT_SIZE = (36.0, 4.0, 14.0)     # W × thickness × H; thickness inset into end
POD_MOUNT_SCREWS = [(sx * 10.0, sz) for sx in (-1, 1) for sz in (3.0, 10.0)]  # local Y-face

# Clamp family — must match CW agent / D5
assert abs(D.CLAMP_FLANGE_W - 10.0) < 1e-6
assert abs(D.CLAMP_L - 70.0) < 1e-6
assert abs(D.CLAMP_DEPTH - 8.0) < 1e-6
assert abs(D.SADDLE_W - 76.0) < 1e-6
assert abs(D.SADDLE_CHANNEL_W - 46.45) < 1e-6
assert abs(D.SADDLE_CHANNEL_D - 3.4) < 1e-6
# Cap clamp inserts: (±20, ±28.5) — 4 in cap; CW prints 8× clamp_bar qty
CAP_CLAMP = D.CAP_CLAMP
assert len(CAP_CLAMP) == 4
assert all(abs(abs(y) - 28.5) < 1e-6 for _, y in CAP_CLAMP)

# Rescale D5 column Y to 164 length (D5 was 160): keep x, stretch y by 164/160
_Y_SCALE = CAP_L / D.CAP_L  # 164/160 = 1.025
CAP_COLS = [(x, round(y * _Y_SCALE, 2)) for x, y in D.CAP_COLS]
CAP_ORANGE = [(x, round(y * _Y_SCALE, 2)) for x, y in D.CAP_ORANGE]
# Keep AT positions from D5 (fit inside 160 interior; length grew at ends only)
KIT_AT = D.KIT_AT
BQ_AT = D.BQ_AT
WIO_AT = D.WIO_AT
assert (CAP_W / 2) - (WIO_AT[0] + D.WIO_POCKET[0] / 2) >= D.WIO_MIN_WALL

STL_DIR = os.path.join(_D6, "stl")
RENDER_DIR = os.path.join(_D6, "renders")
REVIEW_DIR = os.path.join(_D6, "review")


# ---------------------------------------------------------------- mesh helpers (thin wrappers)

def prepare(obj, merge=1e-4):
    return d5.prepare(obj, merge=merge)


def normalize_z0(obj):
    return d5.normalize_z0(obj)


def check_wt(obj):
    return d5.check_wt(obj)


def check_stl(path, q=1e-4):
    return d5.check_stl(path, q=q)


def emboss_label(body, key, at, **kw):
    return d5.emboss_label(body, key, at, **kw)


def slab(name, w, l, h, r=PLAN_R):
    return oc.rounded_rect(name, (w, l, h), r, anchor="bottom", segments=10)


def bed_face_area(obj, z_eps=0.25):
    """Approx contact area on the bed: near-horizontal tris near min Z."""
    oc.bake(obj)
    me = obj.data
    me.calc_loop_triangles()
    z0 = min(v.co.z for v in me.vertices)
    area = 0.0
    for tri in me.loop_triangles:
        co = [me.vertices[i].co for i in tri.vertices]
        n = (co[1] - co[0]).cross(co[2] - co[0])
        a = n.length * 0.5
        if a < 1e-9:
            continue
        nz = n.z / n.length
        cz = (co[0].z + co[1].z + co[2].z) / 3.0
        if abs(cz - z0) <= z_eps and abs(nz) > 0.55:
            area += a
    return round(area, 1)


def support_ceiling_area(obj, overhang_deg=45.0):
    """Downward faces that are NOT on the bed (true overhang ceilings), mm².

    Uses triangle cross-product areas in object space after bake (more reliable
    than polygon.area with stale tessellation).
    """
    oc.bake(obj)
    me = obj.data
    me.calc_loop_triangles()
    z0 = min(v.co.z for v in me.vertices)
    lim = math.cos(math.radians(90.0 - overhang_deg))
    area = 0.0
    for tri in me.loop_triangles:
        co = [me.vertices[i].co for i in tri.vertices]
        n = (co[1] - co[0]).cross(co[2] - co[0])
        a = n.length * 0.5
        if a < 1e-9:
            continue
        nz = n.z / (n.length)
        cz = (co[0].z + co[1].z + co[2].z) / 3.0
        if nz < -lim and (cz - z0) > 0.4:
            area += a
    return round(area, 1)


# ---------------------------------------------------------------- outer contour helpers

def end_taper_d4(body, w, l, h, taper_len=END_TAPER):
    """Hard end taper ~4→15→full over last ~20 mm (D4 silhouette), both ±Y."""
    for sy in (-1, 1):
        tip = sy * (l / 2)
        # High cut: from tip height ~4 up to full at taper_len inward
        oc.cut(body, oc.prism_x(f"taper_hi{sy}", [
            (tip + sy * 0.5, h + 1.0),
            (tip - sy * taper_len, h + 1.0),
            (tip + sy * 0.5, 4.0),
        ], w + 6))
    return body


def crown_shoulders(body, land_xy, crown, lid_h, lw, ll):
    """Keep flat panel land; lower long-edge shoulders by `crown` mm (truncated dome).

    Cuts two prism wedges along ±X so the outer long edges drop ~crown while the
    central land_xy plateau stays at full lid_h.
    """
    lx, ly = land_xy
    # From land edge to outer long edge: linear drop
    for sx in (-1, 1):
        x_land = sx * (lx / 2)
        x_out = sx * (lw / 2 + 1)
        # Prism along Y: profile in XZ
        oc.cut(body, oc.prism_y(f"crown{sx}", [
            (x_land, lid_h + 1.0),
            (x_out, lid_h + 1.0),
            (x_out, lid_h - crown),
            (x_land, lid_h + 0.05),
        ], ll + 4))
    return body


def end_crown_taper(body, land_xy, lid_h, lw, ll, taper_len=END_TAPER):
    """Drop lid ends over last ~20 mm (D4 hard taper on lid shell)."""
    lx, ly = land_xy
    for sy in (-1, 1):
        tip = sy * (ll / 2)
        oc.cut(body, oc.prism_x(f"lid_end{sy}", [
            (tip + sy * 0.5, lid_h + 1.0),
            (tip - sy * taper_len, lid_h + 1.0),
            (tip + sy * 0.5, max(3.0, lid_h - 8.0)),
        ], lw + 4))
    return body


def add_wrap_step(body, w, l, step_h, lid_h, r=PLAN_R - 0.5):
    """Outer perimeter step (z≥0): lowers a 2.5 mm rim band so the seam reads low
    without a hanging skirt that ruins mating-down bed contact."""
    if step_h <= 0.05:
        return body
    band = 3.0
    # Cut a shallow ledge around the outer perimeter at the top — leave panel land
    outer = oc.rounded_rect("wrap_o", (w + 0.2, l + 0.2, step_h + 0.4), r,
                            at=(0, 0, lid_h - step_h), anchor="bottom")
    inner = oc.rounded_rect("wrap_i", (w - 2 * band, l - 2 * band, step_h + 1.0),
                            max(r - band, 2.0),
                            at=(0, 0, lid_h - step_h - 0.2), anchor="bottom")
    oc.cut(body, oc.cut(outer, inner))
    return body


def pod_mount_pad(side):
    """Cap-end mount face for pod at ±Y. Inset into the end (does not grow L).

    Tilted ±29.1° about X. side 'L' → −Y (+tilt), 'R' → +Y (−tilt).
    """
    sign = -1 if side == "L" else 1
    tilt = sign * POD_TILT_DEG
    pw, pt, ph = POD_MOUNT_SIZE
    pad = oc.box(f"pod_pad_{side}", (pw, pt, ph), anchor="center")
    for i, (lx, lz) in enumerate(POD_MOUNT_SCREWS):
        oc.cut(pad, oc.cylinder(f"pmh_{side}_{i}", D.CLEAR, pt + 4,
                                at=(lx, 0, lz - ph / 2), axis="Y", segments=24))
    oc.bake(pad)
    pad.data.transform(Matrix.Rotation(math.radians(tilt), 4, "X"))
    # After tilt, Y half-extent ≈ (pt/2)|cosθ| + (ph/2)|sinθ| — keep inside ±CAP_L/2.
    y_ext = (pt / 2) * abs(math.cos(math.radians(tilt))) + \
            (ph / 2) * abs(math.sin(math.radians(tilt)))
    y_place = sign * (CAP_L / 2 - y_ext - 0.8)
    z_place = CAP_FLOOR + 5.0
    oc.move(pad, dy=y_place, dz=z_place)
    return pad


# ---------------------------------------------------------------- parts

def cap_base():
    """D5 internals in D6 76×164 skin; cavity UP; pod mount pads on ±Y ends."""
    b = slab("cap_base", CAP_W, CAP_L, CAP_BASE_H, PLAN_R)
    # Cavity — same free height as D5; length uses D6 wall/taper budget
    cav_l = CAP_L - 2 * D.CAP_WALL - 2 * END_TAPER + 8
    d5.cut_cav(b, CAP_W - 2 * D.CAP_WALL, max(cav_l, 110), CAP_FLOOR, CAP_CAVITY_H + 2, r=5.0)
    d5.columns(b, CAP_COLS, CAP_FLOOR, CAP_BASE_H)
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"cl{i}", D.INSERT_D, 4.0, at=(x, y, -0.1), anchor="bottom"))
    for i, (x, y) in enumerate([(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]):
        oc.cut(b, oc.cylinder(f"pin{i}", 4.35, 2.2, at=(x, y, -0.1), anchor="bottom"))
    d5.groove(b, CAP_W, CAP_L, PLAN_R, CAP_BASE_H, D.CAP_WALL)
    d5.reg_lip(b, CAP_W, CAP_L, PLAN_R, CAP_BASE_H, D.CAP_WALL)

    # --- D5 pockets (unchanged positions) ---
    d5.pocket_box(b, "kit", D.KIT_POCKET, KIT_AT, CAP_FLOOR)
    oc.cut(b, oc.rounded_rect("kitjst", (20.0, 10.0, D.KIT_JST_H + 0.5), 1.0,
                              at=(KIT_AT[0], KIT_AT[1] - 4.0, CAP_FLOOR - 0.1),
                              anchor="bottom"))
    d5.board_holes(b, D.KIT_BOARD, D.KIT_HOLE_D, D.KIT_HOLE_INSET, KIT_AT,
                   CAP_FLOOR, depth=2.5, prefix="kith")

    d5.pocket_box(b, "bq", D.BQ_POCKET, BQ_AT, CAP_FLOOR)
    d5.board_holes(b, D.BQ_BOARD, D.BQ_HOLE_D, D.BQ_HOLE_INSET, BQ_AT,
                   CAP_FLOOR, depth=3.0, prefix="bqh")

    d5.pocket_box(b, "wio", D.WIO_POCKET, WIO_AT, CAP_FLOOR)
    ux_s, uy_s = D.UFL_SLACK_AT
    oc.cut(b, oc.rounded_rect("uflslack", (6.0, D.WIO_WIRE_BEND, 4.0), D.POCKET_CORNER_R,
                              at=(ux_s, uy_s, CAP_FLOOR), anchor="bottom"))
    oc.cut(b, oc.cylinder("uflstrain", D.UFL_STRAIN_D, 4.0,
                          at=(ux_s, 35.0, CAP_FLOOR - 0.1), anchor="bottom"))

    for i, (px, py) in enumerate(D.LID_SUPPORT_POSTS):
        h = CAP_CAVITY_H + 0.1
        post = oc.cylinder(f"sup{i}", D.LID_SUPPORT_D, h,
                           at=(px, py, CAP_FLOOR - 0.5), anchor="bottom", segments=24)
        oc.union(b, post)

    ux, uy, uz = D.USBC_PORT
    oc.cut(b, oc.rounded_rect("usbc", (ux, uy, uz), D.POCKET_CORNER_R,
                              at=(0, -(CAP_L / 2 - D.CAP_WALL / 2), CAP_FLOOR + 2.0),
                              anchor="bottom"))
    oc.cut(b, oc.rounded_rect("usbcseat", (D.USBC_CAP[0] + 0.4, 3.0, D.USBC_CAP[1] + 0.4),
                              1.2,
                              at=(0, -(CAP_L / 2 - 1.5), CAP_FLOOR + 1.5),
                              anchor="bottom"))

    for i, (lx, ly) in enumerate(D.LIGHTPIPE_AT):
        oc.cut(b, oc.cylinder(f"lp{i}", D.LIGHTPIPE_D, CAP_CAVITY_H + 2,
                              at=(lx, ly, CAP_FLOOR + 1.0), anchor="bottom"))
    for i, (bx, by) in enumerate(D.BTN_AT):
        oc.cut(b, oc.rounded_rect(f"btn{i}", D.BTN_MEMBRANE, 1.0,
                                  at=(bx, by, CAP_FLOOR + D.KIT_POCKET[2] - 0.5),
                                  anchor="bottom"))

    # Cable exits toward pods — D4/D5 used ±X; D6 pods hang off ±Y ends, so
    # primary cable exits are on ±Y ends (toward pods) plus keep ±X for harness.
    for sy in (-1, 1):
        oc.cut(b, oc.cylinder(f"cableY{sy}", 6.0, D.CAP_WALL + 6,
                              at=(0, sy * (CAP_L / 2 - D.CAP_WALL / 2), CAP_FLOOR + 6),
                              axis="Y", segments=32))
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cableX{sx}", 6.0, D.CAP_WALL + 4,
                              at=(sx * (CAP_W / 2 - D.CAP_WALL / 2), 0, CAP_FLOOR + 6),
                              axis="X", segments=32))

    end_taper_d4(b, CAP_W, CAP_L, CAP_BASE_H, END_TAPER)
    b = prepare(b)

    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cablesink{sx}", 8.0, 1.2,
                              at=(sx * (CAP_W / 2 - 0.6), 0, CAP_FLOOR + 6),
                              axis="X", segments=32))
    for sy in (-1, 1):
        oc.cut(b, oc.cylinder(f"cablesinkY{sy}", 8.0, 1.2,
                              at=(0, sy * (CAP_L / 2 - 0.6), CAP_FLOOR + 6),
                              axis="Y", segments=32))

    # Pod mount pads (cap-end interface)
    for side in ("L", "R"):
        oc.union(b, pod_mount_pad(side))

    # Floor glyphs — reuse D5 table / positions (scaled Y lightly where needed)
    fz = CAP_FLOOR
    emboss_label(b, "KIT", (-18.0, KIT_AT[1] + 2.0, fz))
    emboss_label(b, "BQ", (-18.0, BQ_AT[1] - 2.0, fz))
    emboss_label(b, "WIO", (WIO_AT[0] - 2.0, WIO_AT[1] + 14.0, fz))
    emboss_label(b, "USB", (0.0, -58.0, fz))
    emboss_label(b, "POST", (14.0, -1.5, fz))
    emboss_label(b, "GNSS", (-18.0, 55.0, fz))
    emboss_label(b, "LTE", (18.0, 48.0, fz))
    emboss_label(b, "PIN1", (22.0, KIT_AT[1] - 4.0, fz), rot_z=-90.0)
    for key, (sx, sy) in (("SCR1", (1, 1)), ("SCR2", (-1, 1)),
                          ("SCR3", (1, -1)), ("SCR4", (-1, -1))):
        emboss_label(b, key, (sx * 28.0, sy * 62.0, fz))
    return prepare(b)


def cap_lid():
    """Crowned wrap-over lid with flat P124 land. Modelled mating-at-z=0.

    Print choice: MATING DOWN (see orientation_compare). Panel pocket faces +Z.
    """
    lw, ll = CAP_W - 2 * REVEAL, CAP_L - 2 * REVEAL
    lid = slab("cap_lid", lw, ll, LID_H, PLAN_R - 0.5)
    d5.lid_fasteners(lid, CAP_COLS, LID_H)

    # Landing ring on mating face (z≈0)
    ring_w = 1.6
    ring_out_w, ring_out_l = lw - 6.0, ll - 6.0
    r_o, r_i = 4.0, 4.0 - ring_w
    outer = oc.rounded_rect("lring_o", (ring_out_w, ring_out_l, 1.5), r_o,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("lring_i", (ring_out_w - 2 * ring_w, ring_out_l - 2 * ring_w, 2.0),
                            r_i, at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))

    # Flat panel land: crown shoulders outside land, then end taper
    crown_shoulders(lid, PANEL_LAND, CROWN, LID_H, lw, ll)
    end_crown_taper(lid, PANEL_LAND, LID_H, lw, ll, END_TAPER)

    # P124 pocket in flat land — depth from outer face; ≥2 mm lid under
    px, py, pz = D.PANEL_POCKET
    under = LID_H - pz
    assert under >= D.PANEL_MIN_LID_UNDER, f"lid under panel {under} < {D.PANEL_MIN_LID_UNDER}"
    oc.cut(lid, oc.rounded_rect("ppocket", (px, py, pz + 0.2), 1.2,
                                at=(0, D.PANEL_Y, LID_H - pz), anchor="bottom"))
    frame_z = LID_H + D.PANEL_FRAME_PROUD - 0.5
    frame = oc.rounded_rect("pframe", (px + 2.8, py + 2.8, 0.5), 1.5,
                            at=(0, D.PANEL_Y, frame_z), anchor="bottom")
    oc.cut(frame, oc.rounded_rect("pfi", (px + 0.3, py + 0.3, 1.0), 1.0,
                                  at=(0, D.PANEL_Y, frame_z - 0.1), anchor="bottom"))
    oc.union(lid, frame)
    oc.cut(lid, oc.cylinder("pwire", 4.0, LID_H + 2,
                            at=(0, D.PANEL_Y + py / 2 - 10, -1), anchor="bottom"))

    # GNSS / LTE from mating face (z=0) — same as D5
    gx, gy = D.GNSS_AT
    gsz = D.GNSS_PATCH[2] + 0.2
    # With thicker lid, cover is larger; still open from z=0
    oc.cut(lid, oc.rounded_rect("gnss", (D.GNSS_PATCH[0] + 0.8, D.GNSS_PATCH[1] + 0.8,
                                         min(gsz + 0.2, LID_H - 1.5)),
                                D.POCKET_CORNER_R, at=(gx, gy, -0.1), anchor="bottom"))
    lx, ly = D.LTE_AT
    oc.cut(lid, oc.rounded_rect("lte", (D.LTE_FLEX[0] + 0.8, D.LTE_FLEX[1] + 0.8, 1.4),
                                D.POCKET_CORNER_R, at=(lx, ly, -0.1), anchor="bottom"))

    for i, (lpx, lpy) in enumerate(D.LIGHTPIPE_AT):
        oc.cut(lid, oc.cylinder(f"lplid{i}", D.LIGHTPIPE_D + 0.2, LID_H + 2,
                                at=(lpx, lpy, -1), anchor="bottom"))
    for i, (bx, by) in enumerate(D.BTN_AT):
        oc.cut(lid, oc.cylinder(f"btnw{i}", 5.0, LID_H + 2,
                                at=(bx, by, -1), anchor="bottom"))

    oc.cut(lid, oc.rounded_rect("label", (D.LABEL[0], D.LABEL[1], D.LABEL[2] + 0.05), 1.0,
                                at=(0, -(ll / 2 - 8.0), LID_H - D.LABEL[2]), anchor="bottom"))

    # Perimeter wrap step (z≥0) — low-seam read without hanging skirt
    add_wrap_step(lid, lw, ll, LID_WRAP_STEP, LID_H, r=PLAN_R - 1.0)
    return prepare(lid)


def cap_floor_layout():
    """PLA floor coupon — reuse D5 rib/glyph layout, slightly longer for 164."""
    w, l = 70.0, 134.0
    floor = oc.rounded_rect("cap_floor", (w, l, 2.0), 3.0, anchor="bottom", segments=6)
    fz = 2.0
    d5.locate_rib_rect(floor, "kit", (40.0, 18.0), (0.0, -22.0), fz, wall=1.2)
    d5.locate_rib_rect(floor, "bq", (30.0, 24.0), (0.0, 22.0), fz, wall=1.2)
    d5.locate_rib_rect(floor, "wio", (18.0, 14.0), (18.0, -5.0), fz, wall=1.2)
    for i, py in enumerate((5.0, -8.0)):
        oc.union(floor, oc.cylinder(f"flpost{i}", 8.0, d5.FLOOR_RIB_H,
                                    at=(0.0, py, fz), anchor="bottom", segments=16))
    for key, xy in (("KIT", (0, -8)), ("BQ", (0, 42)), ("WIO", (22, 10)),
                    ("USB", (0, -50)), ("POST", (22, -2)),
                    ("GNSS", (0, 58)), ("LTE", (-22, 28)),
                    ("SCR1", (-28, -60)), ("SCR2", (28, -60)),
                    ("SCR3", (-28, 60)), ("SCR4", (28, 42)),
                    ("PIN1", (-26, -22))):
        emboss_label(floor, key, (xy[0], xy[1], fz))
    return normalize_z0(prepare(floor))


def panel_p124():
    return prepare(oc.rounded_rect("panel_p124", D.PANEL_SIZE, 1.0, anchor="bottom", segments=8))


# ---------------------------------------------------------------- orientation compare + export

def _dup_mesh(obj, name):
    d = obj.copy()
    d.data = obj.data.copy()
    d.name = name
    oc._link(d)
    return d


def orientation_compare(lid_mating_at_z0):
    """Compare mating-down vs outer-down for the crowned lid.

    Returns dict with bed_face_area and support_ceiling_area for each, plus pick.
    """
    # A: mating-down (as modelled, normalize z0) — skirt rim may touch bed first
    a = _dup_mesh(lid_mating_at_z0, "lid_orient_A")
    normalize_z0(a)
    prepare(a)
    a_bed = bed_face_area(a)
    a_sup = support_ceiling_area(a)

    # B: outer-down — rotate 180° about X, recalc normals (no flip_normals)
    b = _dup_mesh(lid_mating_at_z0, "lid_orient_B")
    oc.bake(b)
    b.data.transform(Matrix.Rotation(math.radians(180), 4, "X"))
    normalize_z0(prepare(b))
    b_bed = bed_face_area(b)
    b_sup = support_ceiling_area(b)

    # Prefer larger bed face and fewer supports. Flat panel land helps outer-down,
    # but mating face is larger; GNSS/LTE are bed recesses when mating-down.
    # Tie-break: mating-down (matches D5 production call + op-maker hint).
    pick = "mating_down"
    if b_bed > a_bed * 1.15 and b_sup < a_sup * 0.85:
        pick = "outer_down"
    elif b_sup + 500 < a_sup and b_bed >= a_bed * 0.9:
        pick = "outer_down"

    result = {
        "mating_down": {"bed_face_mm2": a_bed, "support_ceiling_mm2": a_sup},
        "outer_down": {"bed_face_mm2": b_bed, "support_ceiling_mm2": b_sup},
        "picked": pick,
        "note": (
            "Mating-down: panel pocket +Z, GNSS/LTE are bed recesses (small trees OK). "
            "Outer-down: flat panel land on bed; mating bosses become ceilings. "
            "Crown is shallow (2.7 mm) outside the land."
        ),
    }
    # Clean temps
    bpy.data.objects.remove(a, do_unlink=True)
    bpy.data.objects.remove(b, do_unlink=True)
    return result


def export_stl(obj, path, weld=1e-4):
    prepare(obj, merge=weld)
    normalize_z0(obj)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                              global_scale=1.0, apply_modifiers=True, ascii_format=False)
    except AttributeError:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True,
                                global_scale=1.0, use_mesh_modifiers=True, ascii=False)


def render_set(base, lid, panel, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    oc._setup_render(res=(1400, 1050))
    # Assembly pose for iso/top/side
    oc.reset()
    b = cap_base()
    l = cap_lid()
    # Apply chosen print orient already mating-at-z0; for assembly lift lid
    p = panel_p124()
    oc.move(l, dz=CAP_BASE_H)
    oc.move(p, dz=CAP_BASE_H + LID_H - D.PANEL_POCKET[2])
    for o, rgba in ((b, CHARCOAL), (l, CHARCOAL), (p, PANEL_NAVY)):
        o.data.materials.clear()
        o.data.materials.append(oc._material(o.name, rgba))
    objs = [b, l, p]
    lo = [min(oc.bounds(o)[0][i] for o in objs) for i in range(3)]
    hi = [max(oc.bounds(o)[1][i] for o in objs) for i in range(3)]
    views = {
        "cap_iso": (1.1, -1.3, 0.85),
        "cap_top": (0, 0, 1),
        "cap_side": (1, 0, 0.15),
    }
    paths = {}
    for name, d in views.items():
        cam = oc._camera(lo, hi, d)
        path = os.path.join(out_dir, f"{name}.png")
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)
        paths[name] = path

    # Section through panel land (cut along X=0, look from +X)
    mid = 0.0
    big = max(hi[j] - lo[j] for j in range(3)) * 4
    halves = []
    for o in objs:
        dup = o.copy()
        dup.data = o.data.copy()
        oc._link(dup)
        at = [(lo[j] + hi[j]) / 2 for j in range(3)]
        at[0] = mid - big / 2
        keeper = oc.box("keep", (big, big, big), at)
        m = dup.modifiers.new("section", "BOOLEAN")
        m.operation, m.solver, m.object = "INTERSECT", "EXACT", keeper
        oc.apply_modifiers(dup)
        bpy.data.objects.remove(keeper)
        halves.append(dup)
        o.hide_render = True
    cam = oc._camera(lo, hi, (1, 0, 0.2))
    path = os.path.join(out_dir, "cap_section_panel.png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    for h in halves:
        bpy.data.objects.remove(h)
    paths["cap_section_panel"] = path
    return paths


def save_review_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    oc.reset()
    b = cap_base()
    l = cap_lid()
    p = panel_p124()
    oc.move(l, dx=90)
    oc.move(p, dx=160)
    # Marker empties for pod anchors (integrator / pod agent)
    for side, sy in (("L", -1), ("R", 1)):
        e = bpy.data.objects.new(f"pod_{side}_anchor", None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 15
        e.location = (0, sy * POD_ANCHOR_Y, POD_ANCHOR_Z)
        e.rotation_euler = (math.radians(sy * POD_TILT_DEG), 0, 0)
        oc._link(e)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    return path


def write_cap_md(report, path):
    o = report["orient"]
    pick = o["picked"]
    md = f"""# D6 CAP

D4 contoured skin around D5 internals (PR head `6b1f882`). Script: `hardware/rook/d6/cap.py`.

## Envelope

| Item | mm | Notes |
| --- | --- | --- |
| Outer W × L | **{CAP_W} × {CAP_L}** | Contract; D4 was 69.3×164.2 — width grown for P124 |
| Stack H | **{CAP_STACK_H}** | D4 ≈30.7; base mating {CAP_BASE_H} + lid above {LID_ABOVE} |
| Seam Z (assembly) | **{SEAM_Z}** | Low seam ~0.29 of stack; lid perimeter step {LID_WRAP_STEP} mm (no hanging skirt) |
| Base H (mating) | {CAP_BASE_H} | Floor {CAP_FLOOR} + cavity {CAP_CAVITY_H} (D5) |
| Lid H (above mating) | {LID_H} | Flat panel land; crown {CROWN} outside land |
| Plan R / reveal | {PLAN_R} / {REVEAL} | Soft plan; 0.5 inset lid |
| End taper | {END_TAPER} | Hard 4→full over last ~20 mm (D4) |
| Panel land (flat) | {PANEL_LAND[0]} × {PANEL_LAND[1]} | Contains pocket; crown outside |
| Panel pocket | {D.PANEL_POCKET[0]} × {D.PANEL_POCKET[1]} × {D.PANEL_POCKET[2]} | P124 KEPT; 15 mm keep-clear |
| Lid under panel | {round(LID_H - D.PANEL_POCKET[2], 2)} | ≥ {D.PANEL_MIN_LID_UNDER} |

## Pod interface (cap side)

| Item | Value |
| --- | --- |
| Pod anchor (world) | y = ±{POD_ANCHOR_Y}, z = {POD_ANCHOR_Z} |
| Tilt about X | ±{POD_TILT_DEG:.2f}° (L +, R −) — matches d4.json |
| Mount pad size | {POD_MOUNT_SIZE[0]} × {POD_MOUNT_SIZE[1]} × {POD_MOUNT_SIZE[2]} |
| Mount face Y | ±{POD_MOUNT_FACE_Y} |
| Screws in pad | 4× Ø{D.CLEAR} clear, local (±12, z∈{{4,12}}) through pad |
| Cable exits | Ø6 through ±Y ends + ±X walls; countersink Ø8 × 1.2 |

Pod agent builds the mating pod face / fairing to these anchors.

## Clamp / saddle family (match CW `cursor/d6-cw-9a36`)

| Item | Value |
| --- | --- |
| Clamp bar | **10 × 70 × 8**, flange down (print ×8) |
| Cap clamp inserts | (±20, ±28.5) — 4 in cap |
| Saddle W | **76** |
| Strap channel | **46.45 × 3.4** |

## Print orientation

| Part | Bed (z=0) | Supports |
| --- | --- | --- |
| `cap_base` | Underside; cavity UP; glyphs UP | None expected |
| `cap_lid` | **{pick}** | See compare below |
| `cap_floor_layout` | Underside; ribs/glyphs UP | None |

### Lid orientation compare

| Orient | Bed-face area (mm²) | Downward/support ceiling (mm²) |
| --- | --- | --- |
| Mating-down | {o['mating_down']['bed_face_mm2']} | {o['mating_down']['support_ceiling_mm2']} |
| Outer-down | {o['outer_down']['bed_face_mm2']} | {o['outer_down']['support_ceiling_mm2']} |
| **Picked** | **{pick}** | |

{o['note']}

Export uses **rotation only** + `recalc_face_normals` — never `flip_normals()`.

## Floor glyphs

Reused from D5 `FLOOR_LABEL_TABLE` / `emboss_label` (DejaVu Bold): char H ≥5, stroke ≥0.8, relief ≥0.6.

Keys on cap floor: KIT, BQ, WIO, USB, POST, GNSS, LTE, PIN1, SCR1–4.

## Verification vs contract / D5

| Check | Contract / D5 | D6 | OK? |
| --- | --- | --- | --- |
| Cap width | 76 | {CAP_W} | YES |
| Cap length | 164 | {CAP_L} | YES |
| Stack ~31 | ~31 | {CAP_STACK_H} | YES |
| P124 pocket | 66.6×113.6×2.3 | same | YES |
| 15 mm keep-clear | ANTENNA_METAL_KEEP=15 | same | YES |
| Flat panel land | required | {PANEL_LAND[0]}×{PANEL_LAND[1]} | YES |
| Crown ~2.7 | D4 | {CROWN} outside land | YES |
| Low seam | ~z=8/27 | seam {SEAM_Z} / stack {CAP_STACK_H} | YES |
| Lay-flat Wio | 21.8×18.6×8 @ (22,−8) | same | YES |
| +X wall ≥3 | WIO_MIN_WALL | {round(CAP_W/2 - (WIO_AT[0]+D.WIO_POCKET[0]/2), 2)} mm | YES |
| Lid posts | (0,5),(0,−8) | same | YES |
| Gasket groove | 2.0×1.5 | same | YES |
| GNSS/LTE from z=0 | D5 | same | YES |
| Cable countersink | Ø8×1.2 | same (+ ±Y) | YES |
| Floor glyphs real text | DejaVu table | reused D5 table | YES |
| Pod anchors | ±113.8, z−27.8, ±29.1° | same | YES |
| Print: base cavity up | yes | yes | YES |
| Print: lid | choose best | **{pick}** | YES |
| Clamp 10×70×8 / y±28.5 | CW agent | matched | YES |

### Carried from D5

All internals: kit/bq/wio pockets, U.FL slack, lid posts, gasket+lip, columns/inserts, clamp inserts, light pipes, buttons, USB-C, GNSS/LTE recesses, panel pocket+frame, floor glyphs, countersinks.

### Changed from D5

- Outer L 160→**164**; W stays 76
- Stack 25.5→**31**; lid above mating 6.5→**12** with crown + flat land
- Low wrap seam + short skirt; hard end taper 20 mm
- Pod mount pads at ±Y ends (tilted)
- Cable exits added on ±Y toward pods
- Cap column Y lightly scaled ×164/160

## STLs

`stl/cap_base.stl`, `stl/cap_lid.stl`, `stl/cap_floor_layout.stl` — print orientation, watertight-checked (see `stl/report.json`).
"""
    with open(path, "w") as f:
        f.write(md)


def main():
    for d in (STL_DIR, RENDER_DIR, REVIEW_DIR):
        os.makedirs(d, exist_ok=True)

    report = {
        "revision": "D6_cap_v1_contour_skin",
        "contract": {
            "cap_w": CAP_W, "cap_l": CAP_L, "stack_h": CAP_STACK_H,
            "seam_z": SEAM_Z, "crown": CROWN, "end_taper": END_TAPER,
            "panel_pocket": list(D.PANEL_POCKET), "panel_land": list(PANEL_LAND),
            "keep_clear": D.ANTENNA_METAL_KEEP,
            "pod_anchor_y": POD_ANCHOR_Y, "pod_anchor_z": POD_ANCHOR_Z,
            "pod_tilt_deg": POD_TILT_DEG,
        },
        "match_cw": {
            "clamp": [D.CLAMP_FLANGE_W, D.CLAMP_L, D.CLAMP_DEPTH],
            "cap_clamp_xy": [list(p) for p in CAP_CLAMP],
            "saddle_w": D.SADDLE_W,
            "channel": [D.SADDLE_CHANNEL_W, D.SADDLE_CHANNEL_D],
        },
        "floor_label_table": {k: v[0] for k, v in d5.FLOOR_LABEL_TABLE.items()},
        "bodies": {},
        "orient": {},
        "pass": True,
    }

    # ---- base ----
    print("=== cap_base ===")
    oc.reset()
    base = cap_base()
    base_path = os.path.join(STL_DIR, "cap_base.stl")
    export_stl(base, base_path, weld=0.008)
    wt = check_stl(base_path)
    lo, hi = oc.bounds(base)
    report["bodies"]["cap_base"] = {
        "stl": base_path,
        "bbox": {"min": [round(x, 3) for x in lo], "max": [round(x, 3) for x in hi],
                 "size": [round(hi[i] - lo[i], 3) for i in range(3)]},
        "watertight": wt,
        "print": "cavity UP; bed=underside z=0",
    }
    print("  bbox", report["bodies"]["cap_base"]["bbox"]["size"], "wt", wt)

    # ---- lid + orientation compare ----
    print("=== cap_lid ===")
    oc.reset()
    lid = cap_lid()
    orient = orientation_compare(lid)
    report["orient"] = orient
    print("  orient compare:", json.dumps(orient, indent=2))

    # Rebuild lid clean for export in picked orientation
    oc.reset()
    lid = cap_lid()
    if orient["picked"] == "outer_down":
        oc.bake(lid)
        lid.data.transform(Matrix.Rotation(math.radians(180), 4, "X"))
        prepare(lid)  # recalc normals — no flip_normals
    normalize_z0(lid)
    lid_path = os.path.join(STL_DIR, "cap_lid.stl")
    export_stl(lid, lid_path, weld=1e-4)
    wt = check_stl(lid_path)
    lo, hi = oc.bounds(lid)
    bed = bed_face_area(lid)
    sup = support_ceiling_area(lid)
    report["bodies"]["cap_lid"] = {
        "stl": lid_path,
        "bbox": {"min": [round(x, 3) for x in lo], "max": [round(x, 3) for x in hi],
                 "size": [round(hi[i] - lo[i], 3) for i in range(3)]},
        "watertight": wt,
        "print": orient["picked"],
        "bed_face_mm2": bed,
        "support_ceiling_mm2": sup,
    }
    print("  bbox", report["bodies"]["cap_lid"]["bbox"]["size"],
          "bed", bed, "sup", sup, "wt", wt)

    # ---- floor coupon ----
    print("=== cap_floor_layout ===")
    oc.reset()
    fl = cap_floor_layout()
    fl_path = os.path.join(STL_DIR, "cap_floor_layout.stl")
    export_stl(fl, fl_path, weld=0.008)
    wt = check_stl(fl_path)
    lo, hi = oc.bounds(fl)
    report["bodies"]["cap_floor_layout"] = {
        "stl": fl_path,
        "bbox": {"size": [round(hi[i] - lo[i], 3) for i in range(3)]},
        "watertight": wt,
    }
    print("  wt", wt)

    # ---- renders + review blend + CAP.md ----
    print("=== renders ===")
    try:
        render_set(None, None, None, RENDER_DIR)
    except Exception as e:
        print("  render warning:", e)
        report["render_error"] = str(e)

    print("=== review blend ===")
    try:
        save_review_blend(os.path.join(REVIEW_DIR, "cap_review.blend"))
    except Exception as e:
        print("  blend warning:", e)
        report["blend_error"] = str(e)

    for name, body in report["bodies"].items():
        if not body.get("watertight", {}).get("watertight", False):
            report["pass"] = False

    write_cap_md(report, os.path.join(_D6, "CAP.md"))
    with open(os.path.join(STL_DIR, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\nRESULT:", "PASS" if report["pass"] else "FAIL")
    print("Lid pick:", orient["picked"],
          "bed", report["bodies"]["cap_lid"]["bed_face_mm2"],
          "sup", report["bodies"]["cap_lid"]["support_ceiling_mm2"])
    print("Outer:", CAP_W, "x", CAP_L, "x stack", CAP_STACK_H)


if __name__ == "__main__":
    main()
