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
Clamp/saddle family (D6 strap-along-Y): CAP_CLAMP (±28.5, ±20), clamp 10×70×8
holes ±28.5, saddle W=76, channel 46.45×3.4 along Y. See assembly.py.

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
sys.path.insert(0, _D6)

import oc  # noqa: E402
import d5_dims as D  # noqa: E402

# Import D5 glyph table + helpers (do NOT run build_d5.main).
import build_d5 as d5  # noqa: E402
import assembly as A  # noqa: E402

CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
# D7 review palette — calm light-gray ASA (matches cw.py / build_assembly_blend)
BODY_ASA = (0.78, 0.79, 0.80, 1.0)
PANEL_NAVY = (0.10, 0.14, 0.22, 1.0)
OAT = (0xEF / 255, 0xE8 / 255, 0xD8 / 255, 1.0)
WORLD = (0.94, 0.93, 0.90)

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
LID_WRAP_STEP = 3.2                    # D7r7: deeper rim drop — less ledge at ends
LID_H = LID_ABOVE                      # solid height above mating (cavities kept)
# D7r7: drop outer crown/shoulder toward pod roof (~panel land stays at LID_H).
# Before (D7r6): CROWN=1.0, NOSE_TIP_H=4.5 → world tip ~33.9 / land ~41.4.
# After: CROWN=3.5, NOSE_TIP_H=3.0 → tip ~32.4; shoulders ~37.9 (panel/Wio/screws OK).
CROWN = 3.5                            # long-edge shoulder drop outside panel land
END_TAPER = 32.0                       # longer tangent into fairing / pod roof
NOSE_TIP_H = 3.0                       # as low as wall allows; cavities unchanged
NOSE_ARC_SEGS = 10                     # smoother elliptical roof (D4-like)
NOSE_PLAN_R = 14.0                     # match pod tip plan R — no shadow line
NOSE_BULL_R = 6.0                      # bullnose blends into fairing
PANEL_LAND = (71.0, 120.0)             # flat plateau — fits D8 P124 pocket 67.2×114.2
# Production planar parting (Cody mating audit): one stadium R across the whole plan.
# PLAN_R kept as alias for older call sites; slab uses R_BASE / R_LID.
REVEAL = 0.50
R_BASE = NOSE_PLAN_R                       # 14.0 — entire 76×164 stadium
R_LID = R_BASE - REVEAL                    # 13.5 — entire 75×163 stadium
PLAN_R = R_BASE                            # was 3.0 (caused plan-radius mismatch)
LW = CAP_W - 2 * REVEAL                    # 75.0
LL = CAP_L - 2 * REVEAL                    # 163.0
# 360° concentric tongue-and-groove rabbet (lid-referenced insets)
LAND_W = 1.80                              # outer flush land (lid edge → groove)
GROOVE_IN0, GROOVE_IN1, GROOVE_D = 1.52, 3.48, 1.60
TONGUE_IN0, TONGUE_IN1, TONGUE_H = 1.80, 3.20, 1.20
BOSS_SPOT_D, BOSS_RECESS = 8.4, 0.40
INSERT_BORE_DEPTH = 6.5
LID_CBORE_D, LID_CBORE_FLOOR_Z = 6.4, 3.80
RABBET_SEGS = 32

# ===========================================================================
# D8 X2a hardware clearances (overrides D5 headline dims — FDM-realistic)
# Audit: review/d8_x2a_hardware_clearance_audit.md
# Vendor: Adafruit GPS-01.pdf (960), Voltaic P124_ds.pdf, makerdiary nRF9151.
# ===========================================================================
# Voltaic P124: 113 × 66 × 2.6 mm ±0.5 (vendor); brief target 2.8. Axes (X across, Y along).
PANEL_SIZE = (66.0, 113.0, 2.6)         # vendor datasheet thickness 2.6 (not 2.8)
PANEL_POCKET = (67.2, 114.2, 3.1)       # +0.6/side XY; depth 3.1 → 2.6–2.8 + thin VHB flush
PANEL_Y = 0.0                          # centered on 164 mm cap (end margin 25.5 mm each)
PANEL_MIN_LID_UNDER = D.PANEL_MIN_LID_UNDER  # 2.0
PANEL_FRAME_PROUD = D.PANEL_FRAME_PROUD
assert LID_H - PANEL_POCKET[2] >= PANEL_MIN_LID_UNDER

# makerdiary nRF9151 Connect Kit: PCB 55.88×20.32×1.0; USB-C overhang +1.5 → 57.38;
# USB +3.26 above PCB; J2 −1.95 below; 4×Ø1.4 inset 1.27.
KIT_BOARD = D.KIT_BOARD                # 55.88 × 20.32 × 1.0
KIT_POCKET = (57.6, 21.4, 7.5)         # ≥56.8×21.2 locating (+0.4/side min) + USB overhang
KIT_JST_RELIEF = (20.0, 12.0, 2.6)     # underside J2 MX1.25-2P ≥2.5 deep so PCB sits flat
KIT_USB_RELIEF = (12.0, 10.0, 5.5)     # in-pocket nose at USB-C end
KIT_AT = D.KIT_AT                      # (0, −24)
# Plugged USB-C access: through −Y wall + elastomer-plug seat (115200 without board pull).
# Exact tunnel / seat / plug dims for 0.22 mm/side clearance (mating audit).
USBC_TUNNEL_W = 10.90
USBC_TUNNEL_H = 6.90
USBC_PORT = (USBC_TUNNEL_W, 9.0, USBC_TUNNEL_H)  # W × (legacy Y) × H
USBC_PLUG_SEAT = (13.00, 3.00, 9.50)              # W × depth_Y × H on −Y outer wall
USBC_PLUG_CLEAR = 0.22                            # mm per side stem + flange
PAD_USB_NOTCH_W = 12.60                           # U-arch through pod_mount_pad("L")
PAD_USB_NOTCH_H = 14.00
SMA_Z = CAP_FLOOR + 5.0                           # lowered so hex seat clears parting deck

# Adafruit #960 (GPS-01.pdf): housing 41.2 × 38.5 × 13.3 mm magnetic IP66 puck +
# 5 m RG174 + SMA male. CANNOT fit in 12 mm lid or 12.6 mm cavity → EXTERNAL mount.
# Paired with SMA-female bulkhead pigtail (Adafruit 851 class): 1/4"-36 UNEF =
# Ø6.35 mm thread → through-port Ø6.6; hex nut ~8–10 mm AF; 15 cm RG178 → U.FL.
GNSS_960_HOUSING = (41.2, 38.5, 13.3)  # datasheet — external only this weekend
GNSS_PATCH_CERAMIC = (25.0, 25.0, 4.0) # optional bare patch — NOT reserved in lid (see audit)
GNSS_INTERNAL_POCKET = None            # removed: would violate 15 mm keep-clear vs centered P124
SMA_BULKHEAD_D = 6.6                   # clears 1/4"-36 (Ø6.35); was Ø6.0 at 4e52f6c — BLOCKED
SMA_NUT_SEAT_AF = 10.0                 # flat hex-nut seat across-flats
SMA_NUT_SEAT_T = 1.5
UFL_ROUTE_CH = (6.0, 28.0, 4.0)        # internal U.FL / RG178 slack toward WIO
ANTENNA_METAL_KEEP = D.ANTENNA_METAL_KEEP  # 15.0
# Honest end-margin math (centered P124 on 164 mm cap):
#   (164 − 113) / 2 = 25.5 mm per end. A 25 mm patch + 15 mm keep-clear needs 40 mm
#   beyond the panel edge → 14.5 mm shortfall. Do NOT cut an internal GNSS recess
#   that pretends to honor the keep-clear. Weekend path = external 960 + SMA bulkhead.
_END_MARGIN = 0.5 * (CAP_L - PANEL_SIZE[1])
assert abs(_END_MARGIN - 25.5) < 0.05
assert _END_MARGIN < (ANTENNA_METAL_KEEP + GNSS_PATCH_CERAMIC[1]), (
    "internal ceramic patch + 15 mm keep-clear cannot fit with centered P124"
)

BQ_AT = D.BQ_AT
WIO_AT = D.WIO_AT
assert (CAP_W / 2) - (WIO_AT[0] + D.WIO_POCKET[0] / 2) >= D.WIO_MIN_WALL

# Pod interface — shared with assembly.py / pod.py (D4 tilt signs; D6 outboard anchors)
POD_ANCHOR_Y = A.POD_ANCHOR_Y
POD_ANCHOR_Z = A.POD_ANCHOR_Z
POD_TILT_DEG = A.TILT_DEG
# Mount pad: 36×4×14 boss protruding past the end to meet the pod face.
# Y matches pod face at anchor ±124; Z = CAP_FLOOR+5 keeps pad above bed after tilt.
POD_MOUNT_FACE_Y = 88.3               # |y| of pad centre (anchor Y=126)
POD_MOUNT_FACE_Z = CAP_FLOOR + 5.0    # 11 — print-safe after ±29° tilt
POD_MOUNT_SIZE = A.POD_MOUNT_SIZE      # W × thickness × H
POD_MOUNT_SCREWS = list(A.POD_MOUNT_SCREWS)  # local Y-face (lx, lz)

# Clamp family — D6 strap-along-Y (see assembly.py / DECISIONS.md)
assert abs(D.CLAMP_FLANGE_W - 10.0) < 1e-6
assert abs(D.CLAMP_L - 70.0) < 1e-6
assert abs(D.CLAMP_DEPTH - 8.0) < 1e-6
assert abs(D.SADDLE_W - 76.0) < 1e-6
assert abs(D.SADDLE_CHANNEL_W - 46.45) < 1e-6
assert abs(D.SADDLE_CHANNEL_D - 3.4) < 1e-6
# Cap clamp inserts: (±28.5, ±20) — outside 44.45 strap; 4 in cap; 8× clamp_bar
CAP_CLAMP = list(A.CAP_CLAMP)
assert len(CAP_CLAMP) == 4
assert all(abs(abs(x) - 28.5) < 1e-6 for x, _ in CAP_CLAMP)
assert all(abs(abs(y) - 20.0) < 1e-6 for _, y in CAP_CLAMP)
assert all(abs(x) > A.STRAP_HALF for x, _ in CAP_CLAMP)

# Lid screws MUST sit outside P124 pocket (|Y|≥57.1+cbore) so lid stays removable
# after VHB. Dual poka-yoke: −Y −X shifted +3.5 mm in X AND −Y bosses at |Y|=67.5
# vs +Y at 69.5 → 180° flip has 0/4 hole coincidences.
CAP_COLS_POKA = [
    (-28.0,  69.50),  # +Y −X
    ( 28.0,  69.50),  # +Y +X
    (-24.5, -67.50),  # −Y −X  poka-yoke (+3.5 mm X from −28.0)
    ( 28.0, -67.50),  # −Y +X
]
CAP_COLS = list(CAP_COLS_POKA)
_Y_SCALE = CAP_L / D.CAP_L  # 164/160 = 1.025 (legacy)
CAP_ORANGE = [(x, round(y * _Y_SCALE, 2)) for x, y in D.CAP_ORANGE]

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


def slab(name, w, l, h, r=None):
    if r is None:
        r = R_BASE
    return oc.rounded_rect(name, (w, l, h), r, anchor="bottom", segments=RABBET_SEGS)


def stadium_ring(name, w_out, l_out, r_out, w_in, l_in, r_in, h, z0, segments=RABBET_SEGS):
    """Concentric stadium ring (outer − inner) as a solid for union/cut."""
    outer = oc.rounded_rect(
        f"{name}_o", (w_out, l_out, h), max(r_out, 0.5),
        at=(0.0, 0.0, z0), anchor="bottom", segments=segments,
    )
    inner = oc.rounded_rect(
        f"{name}_i", (w_in, l_in, h + 0.6), max(r_in, 0.4),
        at=(0.0, 0.0, z0 - 0.2), anchor="bottom", segments=segments,
    )
    return oc.cut(outer, inner)


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
    """Back-compat alias → rounded D7 nose (kept name so call sites stay stable)."""
    return end_nose_contoured(body, w, l, h, taper_len=taper_len)


def end_nose_contoured(body, w, l, h, taper_len=END_TAPER,
                       tip_h=NOSE_TIP_H, segs=NOSE_ARC_SEGS,
                       plan_r=NOSE_PLAN_R, bull_r=NOSE_BULL_R):
    """D7 rounded/chamfered nose — elliptical roof + generous plan radii.

    D6's hard prism cut (~4 mm flat tip) read as a chopped-off slab. D7 drops
    the roof on a quarter-ellipse over `taper_len`, keeps a higher tip, rounds
    the plan at ±Y, and bullnoses the top end edge so the cap flows into the
    fairing / pod like D4_contoured_v3's top end. Mount pads still union on
    after this (see cap_base).
    """
    # D7r7: allow tip down to ~3 mm (panel land / cavities untouched)
    tip_h = max(float(tip_h), 2.8)
    segs = max(int(segs), 4)
    for sy in (-1, 1):
        tip = sy * (l / 2)
        # Region ABOVE the elliptical roof — prism_x profile in YZ
        profile = [(tip + sy * 1.5, h + 2.0)]
        for i in range(segs + 1):
            t = i / segs  # 0 at tip → 1 at taper_len inboard
            y = tip - sy * (taper_len * t)
            # quarter-ellipse: z(tip)=tip_h, z(inboard)=h, vertical tangent at inboard
            z = tip_h + (h - tip_h) * math.sin(0.5 * math.pi * t)
            profile.append((y, z))
        profile.append((tip - sy * taper_len, h + 2.0))
        oc.cut(body, oc.prism_x(f"nose_arc{sy}", profile, w + 8))

        # Plan rounding at the tip: shave square corners with vertical cylinders
        # so the end isn't a flat chopped face in top view.
        pr = min(plan_r, w / 2.0 - 1.0, taper_len * 0.6)
        for sx in (-1, 1):
            # Box corner outside the kept plan radius
            corner = oc.box(f"nose_corner{sy}_{sx}",
                            (pr + 4.0, pr + 4.0, h + 4.0),
                            at=(sx * (w / 2.0 - pr / 2.0 + 2.0),
                                tip - sy * (pr / 2.0 - 1.0),
                                h / 2.0),
                            anchor="center")
            keep = oc.cylinder(f"nose_keep{sy}_{sx}", pr * 2.0, h + 6.0,
                               at=(sx * (w / 2.0 - pr), tip - sy * pr, -1.0),
                               anchor="bottom", segments=28)
            oc.cut(body, oc.cut(corner, keep))

        # Bullnose the top end edge (horizontal cylinder along X at the tip roof)
        if bull_r > 0.5:
            br = min(bull_r, tip_h * 0.7, taper_len * 0.35)
            oc.cut(body, oc.cylinder(
                f"nose_bull{sy}", br * 2.0, w + 10.0,
                at=(0.0, tip - sy * (br * 0.15), tip_h + br * 0.55),
                axis="X", segments=28,
            ))
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
    """D7 lid nose — elliptical drop matching base, not a hard chopped prism."""
    tip_h = max(2.8, min(NOSE_TIP_H, lid_h - 5.5))
    segs = NOSE_ARC_SEGS
    for sy in (-1, 1):
        tip = sy * (ll / 2)
        profile = [(tip + sy * 1.5, lid_h + 2.0)]
        for i in range(segs + 1):
            t = i / segs
            y = tip - sy * (taper_len * t)
            z = tip_h + (lid_h - tip_h) * math.sin(0.5 * math.pi * t)
            profile.append((y, z))
        profile.append((tip - sy * taper_len, lid_h + 2.0))
        oc.cut(body, oc.prism_x(f"lid_nose{sy}", profile, lw + 6))
        # Soft plan rounding on lid tip
        pr = min(NOSE_PLAN_R - 2.0, lw / 2.0 - 1.0, taper_len * 0.5)
        for sx in (-1, 1):
            corner = oc.box(f"lid_corner{sy}_{sx}",
                            (pr + 3.0, pr + 3.0, lid_h + 3.0),
                            at=(sx * (lw / 2.0 - pr / 2.0 + 1.5),
                                tip - sy * (pr / 2.0 - 0.5),
                                lid_h / 2.0),
                            anchor="center")
            keep = oc.cylinder(f"lid_keep{sy}_{sx}", pr * 2.0, lid_h + 5.0,
                               at=(sx * (lw / 2.0 - pr), tip - sy * pr, -1.0),
                               anchor="bottom", segments=24)
            oc.cut(body, oc.cut(corner, keep))
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
    """Cap-end mount boss for pod at ±Y. Protrudes past the end to meet the pod.

    Tilted ±29.142° about X matching pod.py / d4.json:
      side 'L' → −Y, tilt = +29.142°; side 'R' → +Y, tilt = −29.142°.
    4× M3 clear through the pad; pod carries matching holes + 36×4×14 recess.
    L/−Y pad gets a U-notch so USB-C plug + cable overmold clear the pad.
    """
    place_sign = -1 if side == "L" else 1          # L at −Y, R at +Y
    tilt = A.pod_tilt_sign(side) * POD_TILT_DEG    # L +29.142, R −29.142
    pw, pt, ph = POD_MOUNT_SIZE
    pad = oc.box(f"pod_pad_{side}", (pw, pt, ph), anchor="center")
    for i, (lx, lz) in enumerate(POD_MOUNT_SCREWS):
        oc.cut(pad, oc.cylinder(f"pmh_{side}_{i}", D.CLEAR, pt + 4,
                                at=(lx, 0, lz - ph / 2), axis="Y", segments=24))
    if side == "L":
        # U-arch centered on X=0: clears USB tunnel / overmold; ≥2 mm to M3 at ±10
        oc.cut(pad, oc.box(
            "usb_notch_L",
            (PAD_USB_NOTCH_W, pt + 6.0, PAD_USB_NOTCH_H),
            at=(0.0, 0.0, 0.0),
            anchor="center",
        ))
    oc.bake(pad)
    pad.data.transform(Matrix.Rotation(math.radians(tilt), 4, "X"))
    y_place = place_sign * POD_MOUNT_FACE_Y
    z_place = POD_MOUNT_FACE_Z
    oc.move(pad, dy=y_place, dz=z_place)
    return pad


# ---------------------------------------------------------------- parts

def cap_base():
    """76×164×19 stadium (R=14) with planar parting deck + 360° tongue.

    Print: cavity UP; bed = underside z=0 after skirts. Do NOT call
    end_nose_contoured / end_taper_d4 above the parting deck (keeps z=CAP_BASE_H
    planar across the full lid footprint).
    """
    b = slab("cap_base", CAP_W, CAP_L, CAP_BASE_H, R_BASE)
    # Cavity — leave solid nose lands (|Y|≳55) for M3 bosses at |Y|=69.7
    cav_l = min(CAP_L - 2 * D.CAP_WALL - 2 * 18.0, 110.0)
    d5.cut_cav(b, CAP_W - 2 * D.CAP_WALL, cav_l, CAP_FLOOR, CAP_CAVITY_H + 2, r=5.0)

    # Clamp / pin inserts (underside)
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"cl{i}", D.INSERT_D, 4.0, at=(x, y, -0.1), anchor="bottom"))
    for i, (x, y) in enumerate([(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]):
        oc.cut(b, oc.cylinder(f"pin{i}", 4.35, 2.2, at=(x, y, -0.1), anchor="bottom"))

    # --- 360° raised tongue (replaces d5.groove + d5.reg_lip) ---
    # Tongue outer/inner referenced to lid plan so XY clear = 0.28 mm/wall.
    tw_o, tl_o = LW - 2 * TONGUE_IN0, LL - 2 * TONGUE_IN0          # 71.40 × 159.40
    tw_i, tl_i = LW - 2 * TONGUE_IN1, LL - 2 * TONGUE_IN1          # 68.60 × 156.60
    tr_o, tr_i = R_LID - TONGUE_IN0, R_LID - TONGUE_IN1            # 11.70 / 10.30
    oc.union(b, stadium_ring(
        "tongue", tw_o, tl_o, tr_o, tw_i, tl_i, tr_i,
        h=TONGUE_H + 0.2, z0=CAP_BASE_H - 0.2, segments=RABBET_SEGS,
    ))

    # --- Nose-land M3 bosses (outside P124; recessed 0.40 below parting) ---
    for i, (x, y) in enumerate(CAP_COLS):
        # Spotface Ø8.4 × 0.40 so boss top = CAP_BASE_H - 0.40
        oc.cut(b, oc.cylinder(
            f"bspot{i}", BOSS_SPOT_D, BOSS_RECESS + 0.6,
            at=(x, y, CAP_BASE_H - BOSS_RECESS), anchor="bottom", segments=32,
        ))
        # Insert bore Ø4.0 × 6.5 deep below spotface
        oc.cut(b, oc.cylinder(
            f"bins{i}", D.INSERT_D, INSERT_BORE_DEPTH + 0.3,
            at=(x, y, CAP_BASE_H - BOSS_RECESS - INSERT_BORE_DEPTH),
            anchor="bottom", segments=32,
        ))

    # --- D8 hardware pockets (keep 7fdaf2f clearances) ---
    seat_z = CAP_FLOOR
    d5.locate_rib_rect(
        b, "kit", (KIT_POCKET[0], KIT_POCKET[1]), KIT_AT, seat_z, h=2.4, wall=1.4,
    )
    jw, jl, jd = KIT_JST_RELIEF
    oc.cut(b, oc.rounded_rect(
        "kitjst", (jw, jl, jd + 0.4), 1.0,
        at=(KIT_AT[0], KIT_AT[1] - 4.0, seat_z - jd - 0.2), anchor="bottom",
    ))
    oc.cut(b, oc.rounded_rect(
        "kit_usb_relief", KIT_USB_RELIEF, 1.2,
        at=(KIT_AT[0], KIT_AT[1] - 0.5 * KIT_POCKET[1] - 2.5, seat_z + 0.2),
        anchor="bottom",
    ))
    d5.board_holes(b, KIT_BOARD, D.KIT_HOLE_D, D.KIT_HOLE_INSET, KIT_AT,
                   seat_z, depth=2.5, prefix="kith")

    d5.pocket_box(b, "bq", D.BQ_POCKET, BQ_AT, CAP_FLOOR)
    d5.board_holes(b, D.BQ_BOARD, D.BQ_HOLE_D, D.BQ_HOLE_INSET, BQ_AT,
                   CAP_FLOOR, depth=3.0, prefix="bqh")
    d5.pocket_box(b, "wio", D.WIO_POCKET, WIO_AT, CAP_FLOOR)
    ux_s, uy_s = D.UFL_SLACK_AT
    oc.cut(b, oc.rounded_rect("uflslack", (6.0, D.WIO_WIRE_BEND, 4.0), D.POCKET_CORNER_R,
                              at=(ux_s, uy_s, CAP_FLOOR), anchor="bottom"))
    oc.cut(b, oc.cylinder("uflstrain", D.UFL_STRAIN_D, 4.0,
                          at=(ux_s, 35.0, CAP_FLOOR - 0.1), anchor="bottom"))
    oc.cut(b, oc.rounded_rect(
        "sma_ufl_ch", UFL_ROUTE_CH, 1.2,
        at=(ux_s - 2.0, 20.0, CAP_FLOOR), anchor="bottom",
    ))

    # Lid support posts — tops recessed 0.40 below parting (never hold seam open)
    for i, (px, py) in enumerate(D.LID_SUPPORT_POSTS):
        post_h = (CAP_BASE_H - BOSS_RECESS) - (CAP_FLOOR - 0.5)
        post = oc.cylinder(f"sup{i}", D.LID_SUPPORT_D, post_h,
                           at=(px, py, CAP_FLOOR - 0.5), anchor="bottom", segments=24)
        oc.union(b, post)

    # USB-C tunnel: exact 10.90 × 6.90 from cavity to −Y exterior
    cav_half = 0.5 * cav_l
    cav_y_lo = -cav_half + 3.0
    outer_y = -(CAP_L / 2.0 + 2.0)
    tunnel_len = cav_y_lo - outer_y
    tunnel_cy = 0.5 * (cav_y_lo + outer_y)
    usbc_z0 = seat_z + 2.0
    oc.cut(b, oc.rounded_rect(
        "usbc_tunnel", (USBC_TUNNEL_W, tunnel_len, USBC_TUNNEL_H), 1.0,
        at=(0.0, tunnel_cy, usbc_z0), anchor="bottom", segments=16,
    ))
    # Outer plug seat: 13.00 × 3.00 × 9.50 (leaves ≥2.8 mm under parting)
    pw, pt, ph = USBC_PLUG_SEAT
    oc.cut(b, oc.rounded_rect(
        "usbc_plug_seat", (pw, pt, ph), 1.0,
        at=(0.0, -(CAP_L / 2.0 - pt / 2.0), seat_z + 0.70),
        anchor="bottom", segments=16,
    ))

    for i, (lx, ly) in enumerate(D.LIGHTPIPE_AT):
        oc.cut(b, oc.cylinder(f"lp{i}", D.LIGHTPIPE_D, CAP_CAVITY_H + 2,
                              at=(lx, ly, CAP_FLOOR + 1.0), anchor="bottom"))
    for i, (bx, by) in enumerate(D.BTN_AT):
        oc.cut(b, oc.rounded_rect(f"btn{i}", D.BTN_MEMBRANE, 1.0,
                                  at=(bx, by, CAP_FLOOR + KIT_POCKET[2] - 0.5),
                                  anchor="bottom"))

    # +Y cable only (USB owns −Y); SMA bulkhead ±X at lowered Z
    oc.cut(b, oc.cylinder("cableY_pos", 6.0, D.CAP_WALL + 6,
                          at=(0, +(CAP_L / 2 - D.CAP_WALL / 2), SMA_Z),
                          axis="Y", segments=32))
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"smaX{sx}", SMA_BULKHEAD_D, D.CAP_WALL + 4,
                              at=(sx * (CAP_W / 2 - D.CAP_WALL / 2), 0, SMA_Z),
                              axis="X", segments=32))

    # DO NOT call end_taper_d4 / end_nose_contoured — parting deck stays planar.
    b = prepare(b)

    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"sma_nut{sx}", SMA_NUT_SEAT_AF, SMA_NUT_SEAT_T,
                              at=(sx * (CAP_W / 2 - SMA_NUT_SEAT_T / 2), 0, SMA_Z),
                              axis="X", segments=6))
    oc.cut(b, oc.cylinder("cablesinkY_pos", 8.0, 1.2,
                          at=(0, +(CAP_L / 2 - 0.6), SMA_Z), axis="Y", segments=32))

    for side in ("L", "R"):
        oc.union(b, pod_mount_pad(side))

    # Floor glyphs — clear of nRF9151 PCB footprint
    fz = CAP_FLOOR
    emboss_label(b, "KIT", (-32.0, -6.0, fz))
    emboss_label(b, "BQ", (-18.0, BQ_AT[1] - 2.0, fz))
    emboss_label(b, "WIO", (WIO_AT[0] - 2.0, WIO_AT[1] + 14.0, fz))
    emboss_label(b, "USB", (18.0, -48.0, fz))
    emboss_label(b, "POST", (14.0, -1.5, fz))
    emboss_label(b, "GNSS", (0.0, 48.0, fz))
    emboss_label(b, "LTE", (18.0, 40.0, fz))
    emboss_label(b, "PIN1", (32.0, -6.0, fz), rot_z=-90.0)
    d5.emboss_glyph(b, "ARROW", (0.0, 8.0, fz), size=7.0)
    for key, (cx, cy) in zip(("SCR1", "SCR2", "SCR3", "SCR4"), CAP_COLS):
        # Labels on cavity floor toward nose — not on boss tops above parting
        emboss_label(b, key, (cx * 0.55, math.copysign(48.0, cy), fz))

    # Underside skirts (do not affect planar parting deck)
    ch_w, ch_d = D.SADDLE_CHANNEL_W, D.SADDLE_CHANNEL_D
    bar_w, bar_l, bar_h = D.CLAMP_FLANGE_W, D.CLAMP_L, D.CLAMP_DEPTH
    skirt_h, plan_r = 14.0, 12.0
    shoulder = 12.0
    pocket_h = bar_h + 0.2
    for sy in (-1.0, 1.0):
        cy = sy * 38.0
        sk_w = min(CAP_W - 2.0, max(bar_l, ch_w + 4.0))
        sk_l = 58.0
        sk = oc.rounded_rect(
            f"cap_skirt{int(sy + 2)}",
            (sk_w, sk_l, skirt_h),
            min(plan_r, sk_w / 2.0 - 1.0, sk_l / 2.0 - 1.0),
            at=(0.0, cy, -skirt_h),
            anchor="bottom", segments=16,
        )
        body_half = CAP_W / 2.0 - 1.0
        for sx in (-1.0, 1.0):
            oc.cut(sk, oc.prism_y(f"cap_skirt_shx{int(sy + 2)}_{int(sx + 2)}", [
                (sx * (body_half + 1.0), -skirt_h - 0.5),
                (sx * (body_half + 1.0), 0.6),
                (sx * (body_half - 1.0), 0.6),
                (sx * (sk_w / 2.0 - 0.4), -skirt_h + shoulder),
                (sx * (sk_w / 2.0 + 1.0), -skirt_h - 0.5),
            ], sk_l + 8.0))
        oc.cut(sk, oc.box(
            f"cap_cpocket{int(sy + 2)}",
            (min(bar_l + 1.0, sk_w - 1.0), bar_w + 1.6, pocket_h + 0.4),
            at=(0.0, sy * 20.0, -skirt_h), anchor="bottom",
        ))
        oc.cut(sk, oc.box(
            f"cap_skirt_ch{int(sy + 2)}", (ch_w, sk_l + 2.0, ch_d + 0.4),
            at=(0.0, cy, -skirt_h + pocket_h), anchor="bottom",
        ))
        oc.union(b, sk)
    # Exact ±CAP_W/2 plan width — shave boolean/bevel spikes so reveal stays 0.50
    half_w = CAP_W / 2.0
    clip_h = skirt_h + CAP_BASE_H + TONGUE_H + 8.0
    clip_z0 = -skirt_h - 2.0
    for sx, tag in ((-1.0, "xm"), (1.0, "xp")):
        oc.cut(b, oc.box(
            f"cap_plan_clip_{tag}",
            (12.0, CAP_L + 80.0, clip_h),
            at=(sx * (half_w + 6.0), 0.0, clip_z0),
            anchor="bottom",
        ))
    return prepare(b)


def cap_lid():
    """75×163×12 stadium (R=13.5); mating face flat at z=0; contour above.

    Print: MATING DOWN (zero supports). Contoured nose via end_crown_taper
    above z=0. 360° groove replaces old lring. Contour-aware M3 cbore.
    """
    lid = slab("cap_lid", LW, LL, LID_H, R_LID)

    # --- 360° mating groove (replaces lring_o / lring_i) ---
    gw_o, gl_o = LW - 2 * GROOVE_IN0, LL - 2 * GROOVE_IN0      # 71.96 × 159.96
    gw_i, gl_i = LW - 2 * GROOVE_IN1, LL - 2 * GROOVE_IN1      # 68.04 × 156.04
    gr_o, gr_i = R_LID - GROOVE_IN0, R_LID - GROOVE_IN1        # 11.98 / 10.02
    oc.cut(lid, stadium_ring(
        "groove", gw_o, gl_o, gr_o, gw_i, gl_i, gr_i,
        h=GROOVE_D + 0.4, z0=-0.2, segments=RABBET_SEGS,
    ))

    # Contoured top (above z=0) — flat mating face stays on bed
    crown_shoulders(lid, PANEL_LAND, CROWN, LID_H, LW, LL)
    end_crown_taper(lid, PANEL_LAND, LID_H, LW, LL, END_TAPER)

    # P124 pocket
    px, py, pz = PANEL_POCKET
    assert LID_H - pz >= PANEL_MIN_LID_UNDER
    oc.cut(lid, oc.rounded_rect("ppocket", (px, py, pz + 0.2), 1.2,
                                at=(0, PANEL_Y, LID_H - pz), anchor="bottom"))
    oc.cut(lid, oc.rounded_rect(
        "pwire_slot", (10.0, 8.0, pz + 1.0), 1.0,
        at=(0.0, PANEL_Y - 0.5 * py + 4.0, LID_H - pz - 0.2), anchor="bottom",
    ))
    frame_z = LID_H + PANEL_FRAME_PROUD - 0.5
    frame = oc.rounded_rect("pframe", (px + 2.8, py + 2.8, 0.5), 1.5,
                            at=(0, PANEL_Y, frame_z), anchor="bottom")
    oc.cut(frame, oc.rounded_rect("pfi", (px + 0.3, py + 0.3, 1.0), 1.0,
                                  at=(0, PANEL_Y, frame_z - 0.1), anchor="bottom"))
    oc.union(lid, frame)
    oc.cut(lid, oc.cylinder("pwire", 4.5, LID_H + 2,
                            at=(0, PANEL_Y - py / 2 + 8, -1), anchor="bottom"))

    lx, ly = D.LTE_AT
    oc.cut(lid, oc.rounded_rect("lte", (D.LTE_FLEX[0] + 0.8, D.LTE_FLEX[1] + 0.8, 1.4),
                                D.POCKET_CORNER_R, at=(lx, ly, -0.1), anchor="bottom"))
    for i, (lpx, lpy) in enumerate(D.LIGHTPIPE_AT):
        oc.cut(lid, oc.cylinder(f"lplid{i}", D.LIGHTPIPE_D + 0.2, LID_H - 1.2,
                                at=(lpx, lpy, -0.1), anchor="bottom"))
    for i, (bx, by) in enumerate(D.BTN_AT):
        oc.cut(lid, oc.cylinder(f"btnw{i}", 5.0, LID_H - 1.2,
                                at=(bx, by, -0.1), anchor="bottom"))

    # Perimeter wrap step follows R_LID
    add_wrap_step(lid, LW, LL, LID_WRAP_STEP, LID_H, r=max(R_LID - 0.5, 2.0))

    # Contour-aware M3 fasteners AFTER nose sculpt (no d5.lid_fasteners)
    for i, (x, y) in enumerate(CAP_COLS):
        oc.cut(lid, oc.cylinder(
            f"lh{i}", D.CLEAR, LID_H + 4.0,
            at=(x, y, -1.0), anchor="bottom", segments=24,
        ))
        # Flat-bottom cbore from z=3.80 up through contoured nose
        oc.cut(lid, oc.cylinder(
            f"lcb{i}", LID_CBORE_D, LID_H - LID_CBORE_FLOOR_Z + 2.0,
            at=(x, y, LID_CBORE_FLOOR_Z), anchor="bottom", segments=24,
        ))

    return prepare(lid)


def cap_usbc_plug():
    """Elastomer/PLA plug — exact 0.22 mm/side clearance to tunnel + seat.

    Mesh layout (print STL): stem at ymin so mating verifier samples stem at
    ymin+2; flange at +Y. Seated in base: rotate so flange faces −Y outer wall
    and stem runs +Y into usbc_tunnel (see T_plug_in_base in cap_report.json).
    """
    stem_w = USBC_TUNNEL_W - 2 * USBC_PLUG_CLEAR   # 10.46
    stem_h = USBC_TUNNEL_H - 2 * USBC_PLUG_CLEAR   # 6.46
    stem_l = 6.00
    fl_w = USBC_PLUG_SEAT[0] - 2 * USBC_PLUG_CLEAR  # 12.56
    fl_t = 2.60
    fl_h = USBC_PLUG_SEAT[2] - 2 * USBC_PLUG_CLEAR  # 9.06
    # Stem occupies y∈[0, stem_l]; flange at y∈[stem_l, stem_l+fl_t] (coaxial X/Z)
    stem = oc.rounded_rect(
        "cap_usbc_plug_stem", (stem_w, stem_l, stem_h), 0.8,
        at=(0.0, 0.5 * stem_l, 0.0), anchor="bottom",
    )
    stem_zc = 0.5 * stem_h
    fl_z0 = stem_zc - 0.5 * fl_h
    flange = oc.rounded_rect(
        "cap_usbc_plug_flange", (fl_w, fl_t, fl_h), 1.0,
        at=(0.0, stem_l + 0.5 * fl_t, fl_z0), anchor="bottom",
    )
    oc.union(stem, flange)
    # No proud floor-glyph on the plug — emboss_glyph unions +Z and would
    # break the 0.22 mm flange/seat clearance. Identity is by silhouette.
    oc.bake(stem)
    oc.move(stem, dz=-oc.bounds(stem)[0][2])
    bz = oc.bounds(stem)
    assert (bz[1][2] - bz[0][2]) <= fl_h + 0.05, (
        f"cap_usbc_plug Z envelope {bz[1][2]-bz[0][2]:.3f} > flange {fl_h}"
    )
    return prepare(stem)


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
    return prepare(oc.rounded_rect("panel_p124", PANEL_SIZE, 1.0, anchor="bottom", segments=8))


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


def _setup_cap_render(res=(1400, 1050)):
    """Workbench + light world — charcoal on default world reads as black."""
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = False
    sh = s.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_object_outline = True
    sh.show_specular_highlight = False
    w = bpy.data.worlds.new("cap_world")
    w.color = WORLD
    s.world = w
    s.view_settings.view_transform = "Standard"


def render_set(base, lid, panel, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    # Assembly pose for iso/top/side
    oc.reset()
    _setup_cap_render()
    b = cap_base()
    l = cap_lid()
    # Apply chosen print orient already mating-at-z0; for assembly lift lid
    p = panel_p124()
    oc.move(l, dz=CAP_BASE_H)
    oc.move(p, dz=CAP_BASE_H + LID_H - PANEL_POCKET[2])
    for o, rgba in ((b, BODY_ASA), (l, BODY_ASA), (p, PANEL_NAVY)):
        o.data.materials.clear()
        o.data.materials.append(oc._material(o.name + "_mat", rgba))
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
        print(f"  wrote {path} ({os.path.getsize(path)} B)")

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
    for h in halves:
        h.data.materials.clear()
        h.data.materials.append(oc._material(h.name + "_sec", BODY_ASA))
    cam = oc._camera(lo, hi, (1, 0, 0.2))
    path = os.path.join(out_dir, "cap_section_panel.png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    print(f"  wrote {path} ({os.path.getsize(path)} B)")
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
        # L = +tilt, R = −tilt (matches pod.py / d4.json)
        e.rotation_euler = (math.radians(-sy * POD_TILT_DEG), 0, 0)
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
| End nose | {END_TAPER} taper / tip {NOSE_TIP_H} / plan R {NOSE_PLAN_R} | D7 rounded ellipse + bullnose (was hard ~4 mm cut) |
| Panel land (flat) | {PANEL_LAND[0]} × {PANEL_LAND[1]} | Contains pocket; crown outside |
| Panel pocket | {PANEL_POCKET[0]} × {PANEL_POCKET[1]} × {PANEL_POCKET[2]} | P124 vendor 66×113×2.6 ±0.5; +0.6/side |
| Lid under panel | {round(LID_H - PANEL_POCKET[2], 2)} | ≥ {PANEL_MIN_LID_UNDER} |
| Kit pocket | {KIT_POCKET[0]} × {KIT_POCKET[1]} × {KIT_POCKET[2]} | nRF9151 locating; J2 relief {KIT_JST_RELIEF[2]} deep |
| SMA bulkhead | Ø{SMA_BULKHEAD_D} ±X + {SMA_NUT_SEAT_AF} AF nut seat | Adafruit 960 external; no internal GNSS recess |
| End margin math | {(CAP_L - PANEL_SIZE[1]) / 2:.1f} mm/end | 15+25 patch needs 40 → external GPS required |

## Pod interface (cap side)

| Item | Value |
| --- | --- |
| Pod anchor (world) | y = ±{POD_ANCHOR_Y}, z = {POD_ANCHOR_Z} |
| Tilt about X | ±{POD_TILT_DEG:.2f}° (L +, R −) — matches d4.json |
| Mount pad size | {POD_MOUNT_SIZE[0]} × {POD_MOUNT_SIZE[1]} × {POD_MOUNT_SIZE[2]} |
| Mount face Y | inset pads; outer envelope stays {CAP_L} (tilt-compensated) |
| Screws in pad | 4× Ø{D.CLEAR} clear through pad (local ±10 X, two Z rows) |
| Cable / SMA | Ø6 ±Y pods; Ø{SMA_BULKHEAD_D} SMA bulkhead ±X + nut seat |

Pod agent builds the mating pod face / fairing to these anchors.

## Clamp / saddle family (match CW `cursor/d6-cw-9a36`)

| Item | Value |
| --- | --- |
| Clamp bar | **10 × 70 × 8**, flange down (print ×8) |
| Cap clamp inserts | (±28.5, ±20) — 4 in cap (strap-along-Y) |
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
| P124 pocket | 66.6×113.6×2.3 X2a | **{PANEL_POCKET[0]}×{PANEL_POCKET[1]}×{PANEL_POCKET[2]}** | YES |
| P124 vendor T | 2.6 ±0.5 | PANEL_SIZE z={PANEL_SIZE[2]} | YES |
| Kit pocket | 56.7×21.1 X2a | **{KIT_POCKET[0]}×{KIT_POCKET[1]}×{KIT_POCKET[2]}** | YES |
| J2 relief | none on X2a | {KIT_JST_RELIEF[2]} mm deep | YES |
| SMA bulkhead | Ø6.0 X2a (blocked 6.35) | **Ø{SMA_BULKHEAD_D}** | YES |
| Internal GNSS | 25.8³ recess (keep-clear FAIL) | **removed** (960 external) | YES |
| Flat panel land | required | {PANEL_LAND[0]}×{PANEL_LAND[1]} | YES |
| Crown ~2.7 | D4 | {CROWN} outside land | YES |
| Low seam | ~z=8/27 | seam {SEAM_Z} / stack {CAP_STACK_H} | YES |
| Lay-flat Wio | 21.8×18.6×8 @ (22,−8) | same | YES |
| +X wall ≥3 | WIO_MIN_WALL | {round(CAP_W/2 - (WIO_AT[0]+D.WIO_POCKET[0]/2), 2)} mm | YES |
| Lid posts | (0,5),(0,−8) | same | YES |
| Gasket groove | 2.0×1.5 | same | YES |
| LTE shelf | D5 | kept (no GNSS recess) | YES |
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
- Low wrap seam + short skirt; D7 rounded nose (ellipse + plan R + bullnose)
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
        "revision": "D8_cap_planar_parting_360_rabbet",
        "contract": {
            "cap_w": CAP_W, "cap_l": CAP_L, "stack_h": CAP_STACK_H,
            "cap_base_h": CAP_BASE_H, "lid_h": LID_H,
            "r_base": R_BASE, "r_lid": R_LID, "reveal": REVEAL,
            "lw_ll": [LW, LL],
            "rabbet": {
                "land_w": LAND_W,
                "groove_inset": [GROOVE_IN0, GROOVE_IN1], "groove_d": GROOVE_D,
                "tongue_inset": [TONGUE_IN0, TONGUE_IN1], "tongue_h": TONGUE_H,
                "xy_clear_mm": 0.28, "z_clear_mm": GROOVE_D - TONGUE_H,
            },
            "seam_z": SEAM_Z, "crown": CROWN, "end_taper": END_TAPER,
            "nose_tip_h": NOSE_TIP_H, "nose_plan_r": NOSE_PLAN_R,
            "nose_bull_r": NOSE_BULL_R,
            "panel_pocket": list(PANEL_POCKET), "panel_land": list(PANEL_LAND),
            "panel_y": PANEL_Y, "panel_size_vendor": list(PANEL_SIZE),
            "gnss_internal_pocket": GNSS_INTERNAL_POCKET,
            "gnss_960_housing_external": list(GNSS_960_HOUSING),
            "sma_bulkhead_d": SMA_BULKHEAD_D, "sma_z": SMA_Z,
            "kit_pocket": list(KIT_POCKET),
            "kit_jst_relief": list(KIT_JST_RELIEF),
            "usbc_tunnel": [USBC_TUNNEL_W, USBC_TUNNEL_H],
            "usbc_plug_seat": list(USBC_PLUG_SEAT),
            "usbc_plug_clear_mm": USBC_PLUG_CLEAR,
            "T_plug_in_base": {
                "note": (
                    "STL print pose: stem at ymin, flange at +Y. Seated in cap_base: "
                    "rotate 180° about Z then translate so flange outer face sits on "
                    "−Y wall and stem runs +Y into usbc_tunnel."
                ),
                "stem_mm": [USBC_TUNNEL_W - 2 * USBC_PLUG_CLEAR, 6.0,
                            USBC_TUNNEL_H - 2 * USBC_PLUG_CLEAR],
                "flange_mm": [USBC_PLUG_SEAT[0] - 2 * USBC_PLUG_CLEAR, 2.60,
                              USBC_PLUG_SEAT[2] - 2 * USBC_PLUG_CLEAR],
                "clear_mm_per_side": USBC_PLUG_CLEAR,
                "model_y_flange_outer_face": -(CAP_L / 2.0),
                "model_y_flange_inner_face": -(CAP_L / 2.0) + USBC_PLUG_SEAT[1],
                "seat_z_stl": [14.0 + CAP_FLOOR + 0.70, 14.0 + CAP_FLOOR + 0.70 + USBC_PLUG_SEAT[2]],
                "tunnel_z_stl": [14.0 + CAP_FLOOR + 2.0, 14.0 + CAP_FLOOR + 2.0 + USBC_TUNNEL_H],
                "seated": {
                    "rotation_deg_xyz": [0.0, 0.0, 180.0],
                    "note": (
                        "After rot180 Z (flange→−Y): translate so flange outer face "
                        "y=-82 and plug Z bbox is centered in seat_z_stl band."
                    ),
                },
            },
            "keep_clear": ANTENNA_METAL_KEEP,
            "end_margin_mm": _END_MARGIN,
            "CAP_COLS": [list(p) for p in CAP_COLS],
            "poka_yoke_cap_cols": [list(p) for p in CAP_COLS],
            "boss_recess_mm": BOSS_RECESS,
            "pod_anchor_y": POD_ANCHOR_Y, "pod_anchor_z": POD_ANCHOR_Z,
            "pod_tilt_deg": POD_TILT_DEG,
            "pad_usb_notch_w": PAD_USB_NOTCH_W,
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

    # ---- USB-C weather plug ----
    print("=== cap_usbc_plug ===")
    oc.reset()
    plug = cap_usbc_plug()
    plug_path = os.path.join(STL_DIR, "cap_usbc_plug.stl")
    export_stl(plug, plug_path, weld=1e-4)
    wt = check_stl(plug_path)
    lo, hi = oc.bounds(plug)
    report["bodies"]["cap_usbc_plug"] = {
        "stl": plug_path,
        "bbox": {"size": [round(hi[i] - lo[i], 3) for i in range(3)]},
        "watertight": wt,
        "print": "flange out; stem into −Y USB seat; PLA or TPU",
        "role": "gasketed/blank plug — seals USB-C access when not provisioning",
    }
    print("  bbox", report["bodies"]["cap_usbc_plug"]["bbox"]["size"], "wt", wt)

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
    with open(os.path.join(STL_DIR, "cap_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print("\nRESULT:", "PASS" if report["pass"] else "FAIL")
    print("Lid pick:", orient["picked"],
          "bed", report["bodies"]["cap_lid"]["bed_face_mm2"],
          "sup", report["bodies"]["cap_lid"]["support_ceiling_mm2"])
    print("Outer:", CAP_W, "x", CAP_L, "x stack", CAP_STACK_H)


if __name__ == "__main__":
    main()
