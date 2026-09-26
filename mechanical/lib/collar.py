"""OpenCollar V1-alpha geometry, shared by the part scripts and the assembly.

Frame: X runs across the neck (along the strap), Y runs along the spine,
Z is up. The top unit's origin is the centre of its footprint at the lowest
point of its underside. The bay's origin is the centre of the cradle's
neck-side face.

Layout (see docs/V1-DESIGN.md): a sealed top unit with the GNSS patch under
the crown and a solar panel on each sloped face; a bay cradle at the bottom
of the strap carrying a swappable ballast module.
"""

import math

import oc
from dims import (BQ24074, GPS_PATCH, INSERT_M3, ISM330, LIION_6600, LTE_FLEX,
                  M3, M3_BUTTON, MAX_M10S, NRF9151_KIT, ORING_2MM, P124_PANEL,
                  QWIIC_BUZZER, STEEL_SLAB, STRAP, VENT_M6)

# ---------------------------------------------------------------- top unit

W, D = 170.0, 126.0          # footprint: across the neck, along the spine
CORNER_R = 10.0
BASE_H = 24.0
RIM = 13.0                   # solid band around the base top and lid bottom
WALL = 3.0

# Underside is a shallow arch so the unit sits on the neck, not on two edges.
# It stops 14 mm in from each end with a ~4 mm step onto flat feet: no
# knife edge, a flat seat for the strap clamp bars, and something to print on.
ARCH_R = 300.0
ARCH_HALF = W / 2 - 14.0
ARCH_SAG = ARCH_R - math.sqrt(ARCH_R ** 2 - (W / 2) ** 2)   # ≈ 12.3
ARCH_ZC = ARCH_SAG - ARCH_R

STRAP_T = STRAP["design_thickness"]
STRAP_W = STRAP["width"]
CHANNEL_W = STRAP_W + 1.5
CHANNEL_D = STRAP_T - 0.5    # strap stands 0.5 proud so the clamp bars grip it

# Lid: a roof. Eaves at the outer edge, crown over the GNSS patch.
EAVE_H = 8.0               # also the height of the lid's solid rim band
CROWN_HALF = 17.0
CROWN_H = 31.0               # lid height above the parting line
ROOF_DEG = math.degrees(math.atan((CROWN_H - EAVE_H) / (W / 2 - CROWN_HALF)))
TOTAL_H = BASE_H + CROWN_H

# Lid screws: up from the underside through the base's solid walls into
# inserts in the lid rim, outside the O-ring. From below so the solar panels
# never cover a screw head. All M3 × 16.
SCREW_INSET = 5.5
SCREWS = [(sx * (W / 2 - SCREW_INSET), sy * 40.0) for sx in (-1, 1) for sy in (-1, 1)] + \
         [(x, sy * (D / 2 - SCREW_INSET)) for x in (-45.0, 0.0, 45.0) for sy in (-1, 1)]
SCREW_LEN = 16.0
SCREW_SEAT_Z = BASE_H + INSERT_M3["length"] + 1.0 - SCREW_LEN   # head seat height in the base

# Strap clamp bars under each end of the unit.
BAR = (12.0, 70.0, 5.0)
BAR_X = W / 2 - 7.0        # on the flat feet
BAR_SCREW_Y = 29.0

# Board plane: every board sits on standoffs with its underside here.
BOARD_Z = 18.0


def arch_z(x):
    """Height of the underside arch at x."""
    if abs(x) > ARCH_HALF:
        return 0.0
    return ARCH_ZC + math.sqrt(ARCH_R ** 2 - x ** 2)


def floor_z(x, y):
    """Top of the base floor at (x, y): the arch plus the wall, plus the strap
    channel where the strap runs underneath."""
    z = ARCH_ZC + math.sqrt(ARCH_R ** 2 - x ** 2) + WALL
    if abs(y) < CHANNEL_W / 2 + 2:
        z += CHANNEL_D
    return z


def _arch_cutter(name, r, length, at_y=0.0, half=ARCH_HALF):
    """The arch as a cutting body, trimmed to |x| < half so it steps cleanly
    onto the flat feet instead of feathering out."""
    cyl = oc.cylinder(name, 2 * r, length, at=(0, at_y, ARCH_ZC), axis="Y", segments=256)
    return oc.intersect(cyl, oc.box("trim", (2 * half, length + 2, 2 * r), at=(0, at_y, 0)))


# Internal layout: (reference name, size, centre xy, z bottom, standoff holes)
def _layout():
    kit = NRF9151_KIT["board"]
    return {
        "battery": dict(size=(LIION_6600["size"][1], LIION_6600["size"][0], LIION_6600["size"][2]),
                        at=(0.0, 0.0), z=arch_z(0) + CHANNEL_D + WALL + 0.2),
        "nrf9151_kit": dict(size=(kit[1], kit[0], kit[2] + NRF9151_KIT["above_pcb"]),
                            at=(42.2, -16.0), z=BOARD_Z + NRF9151_KIT["below_pcb"]),
        "ism330_imu": dict(size=(ISM330["board"][1], ISM330["board"][0], 4.0),
                           at=(62.0, -31.3), z=BOARD_Z, holes=ISM330, rot=True),
        "qwiic_buzzer": dict(size=(25.4, 25.4, 1.6 + QWIIC_BUZZER["buzzer"]["size"][2]),
                             at=(57.7, 28.7), z=BOARD_Z, holes=QWIIC_BUZZER),
        "bq24074_charger": dict(size=(BQ24074["board"][1], BQ24074["board"][0], 8.0),
                                at=(-53.5, -25.0), z=BOARD_Z, holes=BQ24074, rot=True),
        "max_m10s_gnss": dict(size=(MAX_M10S["board"][1], MAX_M10S["board"][0], 9.0),
                              at=(-52.8, 19.0), z=BOARD_Z, holes=MAX_M10S, rot=True),
    }


def _board_holes(spec, at, size, rot):
    """Hole centres in unit coordinates. Board files give holes from the
    bottom-left corner with the long side along X; `rot` turns the board 90°
    so its long side runs along Y."""
    bx, by = spec["board"][0], spec["board"][1]
    out = []
    for hx, hy in spec["holes"]:
        lx, ly = hx - bx / 2, hy - by / 2
        if rot:
            lx, ly = -ly, lx
        out.append((at[0] + lx, at[1] + ly))
    return out


def top_base():
    base = oc.rounded_rect("top_base", (W, D, BASE_H), CORNER_R, anchor="bottom")
    oc.cut(base, _arch_cutter("arch", ARCH_R, D + 10))
    # Strap channel: follows the arch, then runs straight out through the feet.
    oc.cut(base, _arch_cutter("channel", ARCH_R + CHANNEL_D, CHANNEL_W))
    for sx in (-1, 1):
        oc.cut(base, oc.box("channel_foot", (W / 2 - ARCH_HALF + 2, CHANNEL_W, 2 * CHANNEL_D),
                            at=(sx * (ARCH_HALF + (W / 2 - ARCH_HALF) / 2 + 1), 0, 0)))

    # Cavity: RIM-thick walls, floor WALL above the arch (thicker over the strap channel).
    cavity = oc.rounded_rect("cavity", (W - 2 * RIM, D - 2 * RIM, 60), 4.0, at=(0, 0, -10), anchor="bottom")
    oc.cut(cavity, _arch_cutter("floor", ARCH_R + WALL, D + 10, half=W))
    oc.cut(cavity, _arch_cutter("floor_strap", ARCH_R + CHANNEL_D + WALL, CHANNEL_W + 4, half=W))
    oc.cut(base, cavity)

    # O-ring face groove in the rim top.
    g_in = (W - 2 * RIM + 2 * 1.5, D - 2 * RIM + 2 * 1.5)
    gw, gd = ORING_2MM["groove_w"], ORING_2MM["groove_d"]
    groove = oc.rounded_rect("groove", (g_in[0] + 2 * gw, g_in[1] + 2 * gw, gd + 1), 4.0 + 1.5 + gw,
                             at=(0, 0, BASE_H - gd), anchor="bottom")
    oc.cut(groove, oc.rounded_rect("groove_core", (g_in[0], g_in[1], 20), 4.0 + 1.5, at=(0, 0, BASE_H - 5)))
    oc.cut(base, groove)

    # Lid screws: clearance through the wall, counterbored from the underside.
    for (x, y) in SCREWS:
        oc.cut(base, oc.cylinder("lid_screw", M3["clear_d"], 80, at=(x, y, 0)))
        oc.cut(base, oc.cylinder("lid_screw_head", M3["head_cbore_d"], SCREW_SEAT_Z + 20,
                                 at=(x, y, -20), anchor="bottom"))

    # Clamp bar inserts, up into the end walls from the underside.
    tools = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * BAR_X
            z0 = arch_z(x) - 1
            tools.append(oc.cylinder("bar_insert", INSERT_M3["hole_d"], INSERT_M3["hole_depth"] + 1,
                                     at=(x, sy * BAR_SCREW_Y, z0), anchor="bottom"))
    oc.cut(base, *tools)

    # M6 vent through the -Y end wall, below the groove.
    vent_z = BASE_H - 6.5
    oc.cut(base, oc.cylinder("vent", VENT_M6["tap_drill_d"], RIM + 2, at=(30.0, -D / 2 + RIM / 2, vent_z), axis="Y"))
    # 45° cone that starts 0.5 outside the face and ends inside the tapped hole.
    d_out, d_in = VENT_M6["chamfer_d"] + 1.0, VENT_M6["tap_drill_d"] - 1.0
    chamfer = oc.cone("vent_chamfer", d_out, d_in, (d_out - d_in) / 2, segments=47)
    oc.rotate(chamfer, -90, "X")
    oc.move(chamfer, 30.0, -D / 2 - 0.5, vent_z)
    oc.cut(base, chamfer)

    _add_internals(base)
    return base


def _add_internals(base):
    """Standoffs for the boards, a pocket for the Connect Kit, battery locators."""
    parts = []
    for name, spec in _layout().items():
        if "holes" not in spec:
            continue
        for (x, y) in _board_holes(spec["holes"], spec["at"], spec["size"], spec.get("rot", False)):
            z0 = min(floor_z(x, y), floor_z(x + 3, y), floor_z(x - 3, y)) - 1.0
            post = oc.cylinder(f"{name}_post", 6.0, BOARD_Z - z0, at=(x, y, z0), anchor="bottom")
            oc.cut(post, oc.cylinder("pilot", 2.1, 20, at=(x, y, BOARD_Z - 7), anchor="bottom"))
            parts.append(post)

    # Connect Kit: four corner pads to its PCB underside plus a low fence.
    kit = _layout()["nrf9151_kit"]
    kx, ky = kit["at"]
    sx, sy = kit["size"][0], kit["size"][1]
    pcb_z = kit["z"]
    for cx in (-1, 1):
        for cy in (-1, 1):
            x, y = kx + cx * (sx / 2 - 2), ky + cy * (sy / 2 - 2)
            z0 = min(floor_z(x + dx, y + dy) for dx in (-2, 2) for dy in (-2, 2)) - 1.0
            parts.append(oc.box("kit_pad", (4, 4, pcb_z - z0), at=(x, y, z0), anchor="bottom"))
    fence = oc.box("kit_fence", (sx + 4.4, sy + 4.4, 3.0), at=(kx, ky, pcb_z + 1.0), anchor="bottom")
    oc.cut(fence, oc.box("kit_fence_in", (sx + 0.6, sy + 0.6, 10), at=(kx, ky, pcb_z)))
    oc.cut(fence, oc.box("kit_usb_gap", (12, 10, 10), at=(kx, ky - sy / 2, pcb_z)))  # USB-C end open
    imu = _layout()["ism330_imu"]
    iy0, iy1 = ky - sy / 2 - 5, imu["at"][1] + imu["size"][1] / 2 + 1
    oc.cut(fence, oc.box("kit_imu_gap", (6, iy1 - iy0, 10), at=(kx + sx / 2 + 2, (iy0 + iy1) / 2, pcb_z)))
    parts.append(fence)
    # Fence stands on legs so it clears the curved floor.
    for cx in (-1, 1):
        for cy in (-1, 1):
            x, y = kx + cx * (sx / 2 + 1.2), ky + cy * (sy / 2 + 1.2)
            z0 = min(floor_z(x + dx, y + dy) for dx in (-1.1, 1.1) for dy in (-1.1, 1.1)) - 1.0
            parts.append(oc.box("kit_leg", (2.2, 2.2, pcb_z + 1.1 - z0), at=(x, y, z0), anchor="bottom"))

    # Battery: four L-shaped corner locators, 2 mm thick, 8 mm legs.
    bat = _layout()["battery"]
    bx, by = bat["size"][0] / 2 + 0.5, bat["size"][1] / 2 + 0.5
    for cx in (-1, 1):
        for cy in (-1, 1):
            pts = [(bx, by - 8), (bx + 2, by - 8), (bx + 2, by + 2), (bx - 8, by + 2), (bx - 8, by), (bx, by)]
            pts = [(cx * x, cy * y) for x, y in pts]
            z0 = min(floor_z(x, y) for x, y in pts) - 1.0
            parts.append(oc.prism_z("bat_locator", pts, z0, BASE_H - 1.0 - z0))
    oc.union(base, *parts)


def _roof_profile(inset=0.0):
    """XZ outline of the lid, `inset` mm inside the outer surface."""
    t = math.tan(math.radians(ROOF_DEG))
    drop = inset / math.cos(math.radians(ROOF_DEG))
    xe = W / 2 - inset
    crown_z = CROWN_H - inset
    eave_z = EAVE_H - drop + inset * t
    xc = xe - (crown_z - eave_z) / t
    zb = -1.0 if inset else 0.0
    return [(-xe, zb), (xe, zb), (xe, eave_z), (xc, crown_z), (-xc, crown_z), (-xe, eave_z)]


def roof_z(x):
    """Outer roof height above the parting line at x."""
    t = math.tan(math.radians(ROOF_DEG))
    ax = abs(x)
    if ax <= CROWN_HALF:
        return CROWN_H
    return EAVE_H + (W / 2 - ax) * t


def _panel_frame(side):
    """Centre and rotation of the panel on the roof face on `side` (±1)."""
    t = math.radians(ROOF_DEG)
    slope_len = (W / 2 - CROWN_HALF) / math.cos(t)
    mid_x = side * (W / 2 + CROWN_HALF) / 2
    return (mid_x, 0.0, (EAVE_H + CROWN_H) / 2), side * ROOF_DEG, slope_len


def top_lid():
    """Modelled in assembly position (parting line at z = 0)."""
    outer = oc.prism_y("lid", _roof_profile(), D)
    oc.intersect(outer, oc.rounded_rect("fp", (W, D, 80), CORNER_R, at=(0, 0, -1), anchor="bottom"))
    inner = oc.prism_y("lid_in", _roof_profile(WALL), D - 2 * WALL)
    oc.intersect(inner, oc.rounded_rect("fp_in", (W - 2 * WALL, D - 2 * WALL, 80), CORNER_R - WALL,
                                        at=(0, 0, -2), anchor="bottom"))
    oc.cut(outer, inner)

    # Solid rim band that sits on the base rim.
    band = oc.rounded_rect("band", (W, D, EAVE_H), CORNER_R, anchor="bottom")
    oc.cut(band, oc.rounded_rect("band_in", (W - 2 * RIM, D - 2 * RIM, 20), 4.0))
    oc.union(outer, band)

    # Inserts for the lid screws, in the solid rim band.
    oc.cut(outer, *[oc.cylinder("lid_insert", INSERT_M3["hole_d"], INSERT_M3["hole_depth"] + 1,
                                at=(x, y, -1), anchor="bottom") for (x, y) in SCREWS])

    # Panel recesses, 1 mm deep, and a wire hole under each panel's pads.
    px, py = P124_PANEL["size"][1] + 1.0, P124_PANEL["size"][0] + 1.0
    for side in (-1, 1):
        centre, ang, _ = _panel_frame(side)
        pocket = oc.box("panel_pocket", (px, py, 2.0), at=(0, 0, 0))
        oc.rotate(pocket, ang, "Y")
        oc.move(pocket, *centre)
        oc.cut(outer, pocket)
        # P124 solder pads (drawing): two 4 × 4 pads at 6 mm pitch, 15.5 ± 1
        # from the +Y short edge, 26 ± 1 from a long edge. The slot is centred
        # across the panel so it reaches both pads whichever long edge is up.
        slot = oc.box("panel_wire", (14.0, 9.0, 12.0), at=(0, 0, 0))
        oc.rotate(slot, ang, "Y")
        oc.move(slot, centre[0], P124_PANEL["size"][0] / 2 - 17.0, centre[2])
        oc.cut(outer, slot)

    # Four posts under the crown that locate the GNSS patch.
    posts = []
    ps = GPS_PATCH["ceramic"][0] / 2 + 1.5
    for cx in (-1, 1):
        for cy in (-1, 1):
            posts.append(oc.box("patch_post", (2.5, 2.5, 4.0),
                                at=(cx * ps, cy * ps, CROWN_H - WALL - 4.0), anchor="bottom"))
    oc.union(outer, *posts)
    return outer


def clamp_bar():
    """Strap clamp bar, modelled flat on its top face (the face against the strap)."""
    bar = oc.rounded_rect("clamp_bar", BAR, 3.0, anchor="bottom")
    for sy in (-1, 1):
        oc.cut(bar, oc.cylinder("clear", M3["clear_d"], 20, at=(0, sy * BAR_SCREW_Y, 0)))
        oc.cut(bar, oc.cylinder("cbore", M3_BUTTON["head_cbore_d"], 2 * M3_BUTTON["head_cbore_depth"],
                                at=(0, sy * BAR_SCREW_Y, 0)))
    return bar


def top_refs(z_lid=BASE_H):
    """Bought parts inside the top unit, in unit coordinates."""
    refs = []
    for name, s in _layout().items():
        # 0.1 mm above its seat so resting on a post doesn't count as a collision.
        refs.append(oc.reference(oc.box(name, s["size"], at=(s["at"][0], s["at"][1], s["z"] + 0.1),
                                        anchor="bottom")))
    # GNSS patch (ceramic on its module) under the crown, and a ground plane below it.
    cer = GPS_PATCH["ceramic"]
    top = z_lid + CROWN_H - WALL - 0.3
    refs.append(oc.reference(oc.box("gps_patch", (cer[0], cer[1], 8.0), at=(0, 0, top - 8.0), anchor="bottom")))
    refs.append(oc.reference(oc.box("ground_plane", (70.0, 70.0, 0.8), at=(0, 0, top - 8.9), anchor="bottom")))
    # LTE flex antenna on the +Y end wall inside the lid, far from the patch.
    refs.append(oc.reference(oc.box("lte_antenna", (44.0, 0.4, 10.0),
                                    at=(0, D / 2 - WALL - 0.5, z_lid + 10.0), anchor="bottom")))
    return refs


def panels(z_lid=BASE_H):
    out = []
    px, py, pz = P124_PANEL["size"][1], P124_PANEL["size"][0], P124_PANEL["size"][2]
    for side in (-1, 1):
        centre, ang, _ = _panel_frame(side)
        p = oc.reference(oc.box(f"solar_panel_{'L' if side < 0 else 'R'}", (px, py, pz), at=(0, 0, pz / 2 - 0.9)))
        oc.rotate(p, ang, "Y")
        oc.move(p, centre[0], centre[1], centre[2] + z_lid)
        p["oc_panel"] = True
        out.append(p)
    return out


# ---------------------------------------------------------------- bay

BAY = (104.0, 66.0)
CRADLE_T = 16.0
TUNNEL = (CHANNEL_W, STRAP_T + 1.0)
TUNNEL_Z = 7.5               # from the cradle's module face
BAY_SCREW_X = 40.0
MODULE_H = 22.0
THUMB_RECESS = (11.0, 6.0)   # around a knurled M3 head ≤ 8 mm; depth sets 4 mm of thread in the insert
MODULE_R = 5.0


def bay_cradle():
    """Modelled module face down (z = 0), neck face up (z = CRADLE_T)."""
    c = oc.rounded_rect("bay_cradle", (BAY[0], BAY[1], CRADLE_T), 10.0, anchor="bottom")
    oc.cut(c, oc.box("tunnel", (BAY[0] + 2, TUNNEL[0], TUNNEL[1]), at=(0, 0, TUNNEL_Z), anchor="bottom"))
    # Open the top between the two strap loops so the strap is visible and the part is lighter.
    oc.cut(c, oc.box("window", (BAY[0] - 2 * 22.0, TUNNEL[0], 20), at=(0, 0, TUNNEL_Z + 1), anchor="bottom"))
    for sx in (-1, 1):
        oc.cut(c, oc.cylinder("thumb_insert", INSERT_M3["hole_d"], INSERT_M3["hole_depth"] + 1,
                              at=(sx * BAY_SCREW_X, 0, -1), anchor="bottom"))
    return c


def ballast_module():
    """Modelled in its mounted position: top face at z = 0, hanging below."""
    m = oc.rounded_box("ballast_module", (BAY[0], BAY[1], MODULE_H + MODULE_R), MODULE_R,
                       at=(0, 0, -MODULE_H), anchor="bottom")
    oc.cut(m, oc.box("trim", (BAY[0] + 2, BAY[1] + 2, 20), at=(0, 0, 0), anchor="bottom"))
    sx, sy, sz = STEEL_SLAB["size"]
    oc.cut(m, oc.box("slab_pocket", (sx + 1, sy + 1, sz + 0.5 + 1), at=(0, 0, -(sz + 0.5)), anchor="bottom"))
    for s in (-1, 1):
        x = s * BAY_SCREW_X
        oc.cut(m, oc.cylinder("thumb_clear", M3["clear_d"], MODULE_H + 4, at=(x, 0, -MODULE_H - 2), anchor="bottom"))
        oc.cut(m, oc.cylinder("thumb_head", THUMB_RECESS[0], THUMB_RECESS[1] + 1,
                              at=(x, 0, -MODULE_H - 1), anchor="bottom"))
    return m


def steel_slab():
    sx, sy, sz = STEEL_SLAB["size"]
    return oc.reference(oc.box("steel_slab", (sx, sy, sz), at=(0, 0, -sz - 0.25), anchor="bottom"))
