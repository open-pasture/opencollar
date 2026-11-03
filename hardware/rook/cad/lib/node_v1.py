"""Node V1, option 1 ("three modules"): a low top cap on the spine and a pod on
each side of the neck, plus an encased steel counterweight. See
docs/concepts/side-pod-options.html and docs/NODE-V1-BUILD.md.

Unit #1 is built from parts already on hand plus a small order:
  cap   nRF9151 Connect Kit (MCU, LTE-M, GNSS), bq24074 charger, ISM330 IMU,
        GPS patch, LTE flex antenna, 1 x Voltaic P124 panel on the lid
        (113 x 66; see HARDWARE-FIT.md)
  pods  one protected 18650 (Adafruit 1781) and one Qwiic Buzzer each,
        two electrode studs through the neck-side floor (not wired on unit #1)
  cw    four 3 in pieces of 2 x 1/4 in steel flat bar in a printed casing

Each part is modelled in its own print frame: X along its long axis, Z up.
  cap: X across the neck, Y along the spine, Z up from the strap.
  pod: X along the strap (down the side of the neck), Y along the spine,
       Z out from the neck (z = 0 is the face that touches the skin).
  cw:  X across the throat, Y along the spine, z = 0 is the face to the ground.

All sealed housings: one O-ring (2 mm cord) in the base rim, lid screws
M3 from the outside face with bonded sealing washers, cable entries potted.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "..", "common", "cad", "lib")))
import bmesh
import dims as d
import oc


def clean(obj, dist=1e-3):
    """Merge the near-duplicate vertices and zero-length edges that exact
    booleans leave where two cuts nearly touch, so the mesh is manifold."""
    oc.bake(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return obj

STRAP_W = d.STRAP["width"]                  # 44.45
STRAP_T = d.STRAP["design_thickness"]       # 4.0 assumed — verify with calipers
CHANNEL_W = STRAP_W + 2.0
CHANNEL_D = STRAP_T - 0.6                   # 0.6 mm squeeze under the clamp bars
# Single gable across the short axis (Y): ridge along X. Rise is half-width
# plus 0.3 mm so flanks are slightly steeper than 45° (avoids FP overhang flags).
CHANNEL_ROOF_H = CHANNEL_W / 2 + 0.3
INSERT = d.INSERT_M3
GROOVE = d.ORING_2MM
CBORE_D, CBORE_DEPTH = 8.0, 4.0             # button head + bonded washer
CLEAR = d.M3["clear_d"]
CABLE_D = 6.0                               # potted cable entry, cable OD <= 5.5

# ---------------------------------------------------------------- bought parts (unit #1)

CELL = {"d": 18.4, "l": 69.0, "mass_g": 46}          # Adafruit 1781, pub (Cody ordering 2×)
# Voltaic P124 from dims.py (owned); pocket below adds clearance around the ETFE laminate.
P124 = d.P124_PANEL
BQ_H = 11.0                                           # assumed, verify with calipers
PATCH_H = 6.0                                         # assumed, verify with calipers
STEEL_PIECE = (76.2, 50.8, 6.35)                      # 3 in of 2 x 1/4 in flat bar
STEEL_N = 4

# ---------------------------------------------------------------- cap
# Option A (HARDWARE-FIT.md): one owned P124. Outline ~76 x 160; pocket is the
# panel plus 0.3 mm per side. GPS patch sits at the free (−Y) end of the lid;
# the pocket is shifted a few mm toward +Y so a 25 mm patch fits in that end.
#
# CAP_STYLE selects the underside:
#   "gable"  — v3 fit-test geometry (76×160×41.4): channel gable + spine V in
#              the base. Exports stay under stl/node_v1_cap/.
#   "saddle" — slim flat-floor base (~19 mm) + separate printed strap saddle.
#              Exports under stl/node_v1_cap_saddle/; v3 STLs are never overwritten.

CAP_W, CAP_L = 76.0, 160.0
CAP_WALL = 5.0          # keep 5.0 for now (seal + drop); 4.0 deferred — see SADDLE.md
CAP_CAVITY_H = 13.0     # electronics: bq24074 11 mm + margin; GPS patch on lid
CAP_LID_T = 7.0
SPINE_RELIEF_W = 28.0      # opening across the neck, outside the strap zone
# Flank height > half-opening so flanks stay steeper than 45° after the ±0.5 pad.
SPINE_RELIEF_H = SPINE_RELIEF_W / 2 + 1.0
CAP_COLS = [(sx * 29.5, y) for sx in (-1, 1) for y in (-68.0, -42.0, 42.0, 68.0)]
CAP_CLAMP = [(sx * 20.0, sy * 28.5) for sx in (-1, 1) for sy in (-1, 1)]
CAP_BAR = (10.0, 70.0, 4.0)
# Pocket: X across neck (= panel short side), Y along spine (= panel long side).
# Depth is a VHB recess only: dims.P124_PANEL is 3.1 mm thick (drawing 2.8±0.3),
# but a full-depth pocket would break into the lid insert holes (columns sit
# under the panel footprint). Panel sits proud on the gasket.
PANEL_POCKET = (66.6, 113.6, 1.2)
# Deliberate +Y offset: a centred 113.6 mm pocket on CAP_L=160 leaves only
# ~23 mm at each end — too short for the 25 mm GPS patch — so the pocket
# shifts +Y and the patch takes the −Y cavity end (see HARDWARE-FIT.md).
PANEL_Y = 11.0
PATCH_Y = -60.0

# Gable (v3) floor clears the channel gable peak + spine V under the cavity.
CAP_FLOOR_Z_GABLE = CHANNEL_D + CHANNEL_ROOF_H + 1.5   # ~28.4
CAP_BASE_H_GABLE = CAP_FLOOR_Z_GABLE + CAP_CAVITY_H    # ~41.4

# Slim / saddle: flat underside, no gable, no spine V. Floor thick enough that
# Ø4.0 × ~4.5 mm clamp-insert pockets leave ≥1.0 mm keep-out to the cavity
# (no through-hole into the sealed volume). Target base 18–20 mm.
CAP_FLOOR_Z_SADDLE = 6.0
CAP_BASE_H_SADDLE = CAP_FLOOR_Z_SADDLE + CAP_CAVITY_H  # 19.0

# Strap saddle (CAP_STYLE=saddle only). Print roof-down: flat roof on the bed,
# rails up. Roof mates against the cap floor; clamp bars squeeze the strap
# against the saddle roof. Same CAP_CLAMP / CAP_BAR interface as gable.
SADDLE_ROOF_T = 2.5
SADDLE_H = SADDLE_ROOF_T + CHANNEL_D          # ~5.9
SADDLE_L = 80.0                               # covers clamp Y ±28.5 with margin
SADDLE_W = CAP_W                              # 76 — same width as the cap footprint
# Locating: 4 pins on the cap underside (top of a face-down print) into blind
# holes in the saddle roof. No nest pocket — a full-width recess left knife
# edges against the outer wall (see build log). Optional grit gasket is a
# note / shallow groove on the saddle roof only.
SADDLE_NEST_D = 0.0                           # flat mate (no nest); kept for stack math
SADDLE_GASKET_D = 0.4                         # optional TPU/EPDM grit gasket recess
SADDLE_GASKET_INSET = 4.0
SADDLE_LEAD_IN = 3.0                          # chamfer length at strap entries (±X)
SADDLE_PIN_D = 4.0
SADDLE_PIN_H = 1.5                            # protrudes below cap z=0 into the saddle
SADDLE_PINS = [(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]

# Active style (mutable via set_cap_style). Default preserves v3 exports.
CAP_STYLE = "gable"
CAP_FLOOR_Z = CAP_FLOOR_Z_GABLE
CAP_BASE_H = CAP_BASE_H_GABLE


def set_cap_style(style):
    """Select 'gable' (v3) or 'saddle' (slim + printed strap saddle)."""
    global CAP_STYLE, CAP_FLOOR_Z, CAP_BASE_H
    if style not in ("gable", "saddle"):
        raise ValueError(f"CAP_STYLE must be 'gable' or 'saddle', got {style!r}")
    CAP_STYLE = style
    if style == "saddle":
        CAP_FLOOR_Z = CAP_FLOOR_Z_SADDLE
        CAP_BASE_H = CAP_BASE_H_SADDLE
    else:
        CAP_FLOOR_Z = CAP_FLOOR_Z_GABLE
        CAP_BASE_H = CAP_BASE_H_GABLE
    return CAP_STYLE


def clamp_screw_stack_mm(style=None):
    """Clamp screw stack (bar + path into insert). Returns (stack_mm, recommend_mm)."""
    s = style or CAP_STYLE
    bar = CAP_BAR[2]
    insert = INSERT["length"]
    if s == "saddle":
        # Bar flush on saddle flank; screw through full saddle height into
        # the heat-set insert in the cap floor (nest does not shorten the
        # plastic path — the insert mouth is at the nest floor).
        stack = bar + SADDLE_H + insert  # 4 + 5.9 + 4 = 13.9
        return stack, 16.0  # M3×16
    stack = bar + insert  # gable: bar flush on underside into insert
    return stack, 8.0     # M3×8


def lid_screw_stack_mm(style=None):
    """Lid through-screw from head seat to lid-insert engagement."""
    s = style or CAP_STYLE
    h = CAP_BASE_H_SADDLE if s == "saddle" else CAP_BASE_H_GABLE
    seat = 5.0            # Ø8 cbore + cone; head seats ~z=5
    engage = INSERT["length"]
    stack = (h - seat) + engage
    return stack, (20.0 if s == "saddle" else 40.0)


def stack_height_strap_to_lid_mm(style=None):
    """Overall height from strap bottom to lid top (panel proud ignored)."""
    s = style or CAP_STYLE
    if s == "saddle":
        # 0.6 mm strap protrusion below rails + saddle + flat-mate cap + lid.
        return (STRAP_T - CHANNEL_D) + SADDLE_H - SADDLE_NEST_D + CAP_BASE_H_SADDLE + CAP_LID_T
    return CAP_BASE_H_GABLE + CAP_LID_T  # ~48.4; strap lives in the gable channel


def _groove_loop(name, w, l, r, z_top, inset):
    """A rectangular O-ring groove cut downward from z_top, its centreline
    `inset` in from the outer edge of a w x l outline."""
    g, gd = GROOVE["groove_w"], GROOVE["groove_d"]
    outer = oc.rounded_rect(name + "_o", (w - 2 * (inset - g / 2), l - 2 * (inset - g / 2), gd + 1),
                            max(r - inset + g / 2, 0.6), at=(0, 0, z_top - gd), anchor="bottom")
    inner = oc.rounded_rect(name + "_i", (w - 2 * (inset + g / 2), l - 2 * (inset + g / 2), gd + 3),
                            max(r - inset - g / 2, 0.4), at=(0, 0, z_top - gd - 1), anchor="bottom")
    return oc.cut(outer, inner)


def _cap_base_shell():
    """Shared sealed shell: outline, cavity, columns, lid screws, O-ring, cables.
    Underside features (gable channel vs saddle nest) are added by callers."""
    b = oc.rounded_rect("cap_base", (CAP_W, CAP_L, CAP_BASE_H), 10.0, anchor="bottom")
    cav = oc.rounded_rect("cav", (CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, CAP_BASE_H), 5.0,
                          at=(0, 0, CAP_FLOOR_Z), anchor="bottom")
    oc.cut(b, cav)
    cols = [oc.cylinder(f"col{i}", 8.0, CAP_BASE_H - CAP_FLOOR_Z + 0.2, at=(x, y, CAP_FLOOR_Z - 0.5), anchor="bottom")
            for i, (x, y) in enumerate(CAP_COLS)]
    oc.union(b, *cols)
    # Through screws for the lid (from below). Cylinder counterbore then a 45°
    # cone into the clearance hole (no flat ceiling; base prints face-down).
    for i, (x, y) in enumerate(CAP_COLS):
        oc.cut(b, oc.cylinder(f"h{i}", CLEAR, CAP_BASE_H + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cylinder(f"cbc{i}", CBORE_D, 5.0, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cone(f"cb{i}", CBORE_D, CLEAR, 4.0, at=(x, y, 4.0)))
    oc.cut(b, _groove_loop("groove", CAP_W, CAP_L, 10.0, CAP_BASE_H, CAP_WALL / 2))
    cable_z = CAP_FLOOR_Z + (CAP_BASE_H - CAP_FLOOR_Z) / 2
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cable{sx}", CABLE_D, CAP_WALL + 4,
                              at=(sx * (CAP_W / 2 - CAP_WALL / 2), 0, cable_z), axis="X"))
    return b


def _cap_base_gable_underside(b):
    """v3 underside: strap channel + gable roof + spine V reliefs + clamp inserts."""
    half_c = CHANNEL_W / 2
    oc.cut(b, oc.box("chan", (CAP_W + 2, CHANNEL_W, CHANNEL_D + 1),
                     at=(0, 0, CHANNEL_D - (CHANNEL_D + 1) / 2)))
    oc.cut(b, oc.prism_x("chan_gable", [
        (-half_c, CHANNEL_D - 0.2),
        (half_c, CHANNEL_D - 0.2),
        (half_c, CHANNEL_D),
        (0.0, CHANNEL_D + CHANNEL_ROOF_H),
        (-half_c, CHANNEL_D),
    ], CAP_W + 4, at_x=0.0))
    zone = (CAP_L - CHANNEL_W) / 2
    half_w = SPINE_RELIEF_W / 2
    spine_xz = [
        (-half_w - 0.5, -1.0),
        (half_w + 0.5, -1.0),
        (half_w + 0.5, 0.0),
        (0.0, SPINE_RELIEF_H),
        (-half_w - 0.5, 0.0),
    ]
    for sy in (-1, 1):
        yc = sy * (CHANNEL_W / 2 + zone / 2)
        oc.cut(b, oc.prism_y(f"spine{sy}", spine_xz, zone + 0.4, at_y=yc))
    # Clamp-bar inserts: Ø4.0 × 5 mm deep (cylinder from z=-1 height 6) then tip.
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ins{i}", INSERT["hole_d"], 6.0, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cone(f"instip{i}", INSERT["hole_d"], 0.2, 2.0, at=(x, y, 5.0)))
    return b


def _cap_base_saddle_underside(b):
    """Slim underside: flat floor, locating pins into the saddle roof, clamp
    inserts that stop ≥1 mm short of the cavity (no seal breach)."""
    # Pins hang from z=0 into the saddle (top of a face-down print — no overhang).
    for i, (x, y) in enumerate(SADDLE_PINS):
        pin = oc.cylinder(f"pin{i}", SADDLE_PIN_D, SADDLE_PIN_H,
                          at=(x, y, -SADDLE_PIN_H), anchor="bottom")
        oc.union(b, pin)
    # Clamp inserts: Ø4.0 × 4.0 mm seat (insert length) from underside; flat
    # bottom at z=4.0 → 2.0 mm keep-out under CAP_FLOOR_Z=6 (no cavity breach).
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ins{i}", INSERT["hole_d"], 5.0, at=(x, y, -1), anchor="bottom"))
    return b


def cap_base(style=None):
    if style is not None:
        set_cap_style(style)
    b = _cap_base_shell()
    if CAP_STYLE == "saddle":
        _cap_base_saddle_underside(b)
    else:
        _cap_base_gable_underside(b)
    return clean(b)


def cap_saddle():
    """Printed strap saddle for CAP_STYLE=saddle. Print roof-down (z=0 on bed):
    flat roof, channel rails up, no overhangs steeper than 45°, no supports.
    Outside the seal — no gasket required; optional grit-gasket groove on roof."""
    s = oc.rounded_rect("cap_saddle", (SADDLE_W, SADDLE_L, SADDLE_H), 2.0, anchor="bottom")
    # Strap channel through ±X; depth CHANNEL_D from the top (rail) face.
    oc.cut(s, oc.box("schan", (SADDLE_W + 2, CHANNEL_W, CHANNEL_D + 1),
                     at=(0, 0, SADDLE_H - CHANNEL_D + (CHANNEL_D + 1) / 2)))
    # Lead-in chamfers at both strap entries (±X): 45° ramps, support-free.
    for sx in (-1, 1):
        tip_x = sx * (SADDLE_W / 2 + 0.2)
        inner_x = sx * (SADDLE_W / 2 - SADDLE_LEAD_IN)
        oc.cut(s, oc.prism_y(f"lead{sx}", [
            (tip_x, SADDLE_H + 0.2),
            (tip_x, SADDLE_ROOF_T - 0.2),
            (inner_x, SADDLE_H + 0.2),
        ], CHANNEL_W + 0.4, at_y=0.0))
    # Spine relief: V through the rails only (roof stays intact). Flanks ≥45°.
    half_w = SPINE_RELIEF_W / 2
    oc.cut(s, oc.prism_x("spine_v", [
        (-half_w - 0.5, SADDLE_ROOF_T - 0.2),
        (half_w + 0.5, SADDLE_ROOF_T - 0.2),
        (half_w + 0.5, SADDLE_ROOF_T),
        (0.0, SADDLE_H + 0.2),
        (-half_w - 0.5, SADDLE_ROOF_T),
    ], SADDLE_W + 4, at_x=0.0))
    # Clamp screw clearances (same XY as cap inserts / bars).
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(s, oc.cylinder(f"scl{i}", CLEAR, SADDLE_H + 2, at=(x, y, -1), anchor="bottom"))
    # Locating holes for the cap's underside pins (roof / bed face).
    for i, (x, y) in enumerate(SADDLE_PINS):
        oc.cut(s, oc.cylinder(f"spin{i}", SADDLE_PIN_D + 0.35, SADDLE_PIN_H + 0.8,
                              at=(x, y, -0.2), anchor="bottom"))
    # Optional grit-gasket picture-frame groove on the roof (z=0) face.
    gw = SADDLE_W - 2 * SADDLE_GASKET_INSET
    gl = SADDLE_L - 2 * SADDLE_GASKET_INSET
    gd = SADDLE_GASKET_D
    if gw > 20 and gl > 20:
        outer = oc.rounded_rect("gask_o", (gw, gl, gd + 1), 1.5,
                                at=(0, 0, gd - (gd + 1) / 2))
        inner = oc.rounded_rect("gask_i", (gw - 5.0, gl - 5.0, gd + 3), 1.0,
                                at=(0, 0, gd - (gd + 3) / 2 - 0.5))
        oc.cut(s, oc.cut(outer, inner))
    return clean(s)


def cap_lid():
    # Single rounded body (no 3 mm slab step) so the mating-face-down print
    # has no flat ledge at z = 3.
    slab = oc.rounded_box("cap_lid", (CAP_W, CAP_L, CAP_LID_T), 2.5, anchor="bottom")
    oc.intersect(slab, oc.rounded_rect("trim", (CAP_W, CAP_L, CAP_LID_T + 2), 10.0, at=(0, 0, -1), anchor="bottom"))
    for i, (x, y) in enumerate(CAP_COLS):
        # Blind insert seat Ø4.0 × 5 mm deep (from z=-1 height 6 → top z=5).
        # No cone tip: panel pocket floor is at z=CAP_LID_T−1.2=5.8, so a tip
        # above z=5 would break the ≥0.8 mm keep-out under the panel pocket.
        # Flat 4 mm bridge is acceptable (lid prints mating-face-down).
        oc.cut(slab, oc.cylinder(f"lih{i}", INSERT["hole_d"], 6.0, at=(x, y, -1), anchor="bottom"))
    px, py, pz = PANEL_POCKET
    oc.cut(slab, oc.rounded_rect("pocket", (px, py, pz + 1), 1.0, at=(0, PANEL_Y, CAP_LID_T - pz), anchor="bottom"))
    # Panel lead hole near the +Y end of the pocket (away from the GPS patch).
    oc.cut(slab, oc.cylinder("wire", 4.0, CAP_LID_T + 2, at=(0, PANEL_Y + py / 2 - 8.0, -1), anchor="bottom"))
    return slab


def cap_bar():
    x, y, z = CAP_BAR
    bar = oc.rounded_box("cap_bar", (x, y, z), 1.5, anchor="bottom")
    cb_d = d.M3_BUTTON["head_cbore_d"]
    cb_h = d.M3_BUTTON["head_cbore_depth"]
    for sy in (-1, 1):
        oc.cut(bar, oc.cylinder(f"bh{sy}", CLEAR, z + 2, at=(0, sy * 28.5, -1), anchor="bottom"))
        # Conical button-head seat meeting the clearance hole (no flat ceiling).
        oc.cut(bar, oc.cone(f"bc{sy}", cb_d, CLEAR, cb_h, at=(0, sy * 28.5, 0.0)))
    return bar


def cap_refs(z_lid=CAP_BASE_H):
    """Bought parts inside the cap, in cap coordinates."""
    k = d.NRF9151_KIT
    kb = k["board"]
    # P124 short side across the neck (X), long side along the spine (Y).
    p124_x, p124_y, p124_z = P124["size"][1], P124["size"][0], P124["size"][2]
    cable_z = CAP_FLOOR_Z + (CAP_BASE_H - CAP_FLOOR_Z) / 2
    refs = [
        oc.box("ref_kit", (kb[1], kb[0], kb[2] + k["above_pcb"]), at=(-6.0, -6.0, CAP_FLOOR_Z + 2.0), anchor="bottom"),
        oc.box("ref_bq24074", (d.BQ24074["board"][1], d.BQ24074["board"][0], BQ_H),
               at=(0.0, 52.0, CAP_FLOOR_Z + 0.3), anchor="bottom"),
        oc.box("ref_ism330", (d.ISM330["board"][1], d.ISM330["board"][0], 3.2),
               at=(18.0, -8.0, CAP_FLOOR_Z + 2.0), anchor="bottom"),
        oc.box("ref_gps_patch", (25.0, 25.0, PATCH_H),
               at=(0, PATCH_Y, CAP_BASE_H - PATCH_H - 0.6), anchor="bottom"),
        oc.box("ref_lte_flex", (0.4, 44.0, 10.0),
               at=(CAP_W / 2 - CAP_WALL - 0.6, 10.0, cable_z - 5.0), anchor="bottom"),
        oc.box("ref_p124", (p124_x, p124_y, p124_z),
               at=(0, PANEL_Y, z_lid + CAP_LID_T - PANEL_POCKET[2] + 0.05), anchor="bottom"),
    ]
    return [oc.reference(r) for r in refs]


# ---------------------------------------------------------------- pod
# Plan of record: two identical pods, each with one Adafruit 1781 cell and one
# Qwiic Buzzer (Cody ordering 2×1781). An unapproved 353-pack alternative lives
# under stl/alt_pods_unapproved/.

POD_L, POD_W = 92.0, 68.0
POD_WALL = 5.0
POD_FLOOR = 3.0
POD_BASE_H = 24.5          # cavity 21.5 for the 18.4 mm cell; lid screws are M3 x 25
POD_LID_T = 6.0
POD_COLS = [(sx * 37.0, sy * 27.0) for sx in (-1, 1) for sy in (-1, 1)]
POD_CLAMP = [(sx * 32.0, sy * 29.5) for sx in (-1, 1) for sy in (-1, 1)]
POD_BAR = (10.0, 70.0, 4.0)
CELL_AT = (-2.0, -13.0)
BUZZER_AT = (20.0, 15.0)   # board centre
ELECTRODES = [(-30.0, 15.0), (-8.0, 15.0)]


def pod_base():
    b = oc.rounded_box("pod_base", (POD_L, POD_W, POD_BASE_H), 4.0, anchor="bottom")
    oc.union(b, oc.rounded_rect("rim", (POD_L, POD_W, 10.0), 9.0, at=(0, 0, POD_BASE_H - 10.0), anchor="bottom"))
    oc.intersect(b, oc.rounded_rect("trim", (POD_L, POD_W, POD_BASE_H + 2), 9.0, at=(0, 0, -1), anchor="bottom"))
    cav = oc.rounded_rect("pcav", (POD_L - 2 * POD_WALL, POD_W - 2 * POD_WALL, POD_BASE_H), 4.0,
                          at=(0, 0, POD_FLOOR), anchor="bottom")
    oc.cut(b, cav)
    cols = [oc.cylinder(f"pcol{i}", 8.0, POD_BASE_H - POD_FLOOR + 0.5, at=(x, y, POD_FLOOR - 0.5), anchor="bottom")
            for i, (x, y) in enumerate(POD_COLS)]
    oc.union(b, *cols)
    for i, (x, y) in enumerate(POD_COLS):
        oc.cut(b, oc.cylinder(f"ph{i}", CLEAR, POD_BASE_H + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cylinder(f"pcb{i}", CBORE_D, CBORE_DEPTH + 1, at=(x, y, -1), anchor="bottom"))
    oc.cut(b, _groove_loop("pgroove", POD_L, POD_W, 9.0, POD_BASE_H, POD_WALL / 2))
    # Electrode studs (M4 pan head from the skin side, O-ring seat under the head).
    for i, (x, y) in enumerate(ELECTRODES):
        oc.cut(b, oc.cylinder(f"el{i}", 4.3, POD_FLOOR + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cylinder(f"elc{i}", 10.0, 1.0 + 1, at=(x, y, -1), anchor="bottom"))
    # Sound port toward the head (+Y wall), at the buzzer; an acoustic membrane is bonded inside.
    oc.cut(b, oc.cylinder("port", 8.0, POD_WALL + 4, at=(BUZZER_AT[0], POD_W / 2 - POD_WALL / 2, 11.0), axis="Y"))
    # Potted cable entry on the end toward the crest (+X).
    oc.cut(b, oc.cylinder("pcable", CABLE_D, POD_WALL + 4, at=(POD_L / 2 - POD_WALL / 2, -2.0, 12.0), axis="X"))
    return b


def pod_lid():
    slab = oc.rounded_rect("pod_lid", (POD_L, POD_W, 3.0), 9.0, anchor="bottom")
    top = oc.rounded_box("plid_top", (POD_L, POD_W, POD_LID_T - 1.0), 2.5, at=(0, 0, 1.0), anchor="bottom")
    oc.intersect(top, oc.rounded_rect("ptrim", (POD_L, POD_W, POD_LID_T + 2), 9.0, at=(0, 0, -1), anchor="bottom"))
    oc.union(slab, top)
    oc.cut(slab, oc.box("pchan", (POD_L + 2, CHANNEL_W, CHANNEL_D + 1), at=(0, 0, POD_LID_T - CHANNEL_D + (CHANNEL_D + 1) / 2)))
    for i, (x, y) in enumerate(POD_COLS):
        oc.cut(slab, oc.cylinder(f"pli{i}", INSERT["hole_d"], 4.8 + 1, at=(x, y, -1), anchor="bottom"))
    for i, (x, y) in enumerate(POD_CLAMP):
        oc.cut(slab, oc.cylinder(f"pci{i}", INSERT["hole_d"], 4.8 + 1, at=(x, y, POD_LID_T - 4.8), anchor="bottom"))
    return slab


def pod_bar():
    x, y, z = POD_BAR
    bar = oc.rounded_box("pod_bar", (x, y, z), 1.5, anchor="bottom")
    for sy in (-1, 1):
        oc.cut(bar, oc.cylinder(f"pbh{sy}", CLEAR, z + 2, at=(0, sy * 29.5, -1), anchor="bottom"))
        oc.cut(bar, oc.cylinder(f"pbc{sy}", d.M3_BUTTON["head_cbore_d"], d.M3_BUTTON["head_cbore_depth"] + 1,
                                at=(0, sy * 29.5, z - d.M3_BUTTON["head_cbore_depth"]), anchor="bottom"))
    return bar


def pod_refs():
    qb = d.QWIIC_BUZZER
    refs = [
        oc.cylinder("ref_cell", CELL["d"], CELL["l"], at=(CELL_AT[0], CELL_AT[1], POD_FLOOR + CELL["d"] / 2 + 0.4), axis="X"),
        oc.box("ref_buzzer", (qb["board"][0], qb["board"][1], qb["board"][2] + qb["buzzer"]["size"][2]),
               at=(BUZZER_AT[0], BUZZER_AT[1], POD_FLOOR + 3.0), anchor="bottom"),
    ]
    for i, (x, y) in enumerate(ELECTRODES):
        refs.append(oc.cylinder(f"ref_electrode{i}", 7.0, 2.2, at=(x, y, -2.2), anchor="bottom"))
    return [oc.reference(r) for r in refs]


# ---------------------------------------------------------------- counterweight

CW_L, CW_W = 88.0, 74.0
CW_TUB_H = 30.0            # floor 3, cavity 27 for 4 x 6.35 steel + foam
CW_LID_T = 6.0
CW_SCREWS = [(sx * 22.0, sy * 31.5) for sx in (-1, 1) for sy in (-1, 1)]
CW_CLAMP = [(sx * 36.0, sy * 29.5) for sx in (-1, 1) for sy in (-1, 1)]
CW_BAR = (10.0, 70.0, 4.0)


def cw_tub():
    t = oc.rounded_box("cw_tub", (CW_L, CW_W, CW_TUB_H), 5.0, anchor="bottom")
    oc.union(t, oc.rounded_rect("cwrim", (CW_L, CW_W, 8.0), 10.0, at=(0, 0, CW_TUB_H - 8.0), anchor="bottom"))
    oc.intersect(t, oc.rounded_rect("cwtrim", (CW_L, CW_W, CW_TUB_H + 2), 10.0, at=(0, 0, -1), anchor="bottom"))
    sx, sy, sz = STEEL_PIECE
    oc.cut(t, oc.rounded_rect("cwcav", (sx + 1.2, sy + 1.2, CW_TUB_H), 1.5, at=(0, 0, 3.0), anchor="bottom"))
    # Lid screws come in from the lid (neck) side into inserts in the rim; nothing breaks the ground face.
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.cut(t, oc.cylinder(f"cwi{i}", INSERT["hole_d"], INSERT["hole_depth"] + 1, at=(x, y, CW_TUB_H - INSERT["hole_depth"]), anchor="bottom"))
    return t


def cw_lid():
    slab = oc.rounded_rect("cw_lid", (CW_L, CW_W, 3.0), 10.0, anchor="bottom")
    top = oc.rounded_box("cwl_top", (CW_L, CW_W, CW_LID_T - 1.0), 2.5, at=(0, 0, 1.0), anchor="bottom")
    oc.intersect(top, oc.rounded_rect("cwltrim", (CW_L, CW_W, CW_LID_T + 2), 10.0, at=(0, 0, -1), anchor="bottom"))
    oc.union(slab, top)
    oc.cut(slab, oc.box("cwchan", (CW_L + 2, CHANNEL_W, CHANNEL_D + 1), at=(0, 0, CW_LID_T - CHANNEL_D + (CHANNEL_D + 1) / 2)))
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.cut(slab, oc.cylinder(f"cwlh{i}", CLEAR, CW_LID_T + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(slab, oc.cylinder(f"cwlc{i}", d.M3_BUTTON["head_cbore_d"], d.M3_BUTTON["head_cbore_depth"] + 1,
                                 at=(x, y, CW_LID_T - d.M3_BUTTON["head_cbore_depth"]), anchor="bottom"))
    for i, (x, y) in enumerate(CW_CLAMP):
        oc.cut(slab, oc.cylinder(f"cwci{i}", INSERT["hole_d"], 4.8 + 1, at=(x, y, CW_LID_T - 4.8), anchor="bottom"))
    return slab


def cw_refs():
    sx, sy, sz = STEEL_PIECE
    return [oc.reference(oc.box(f"ref_steel{i}", (sx, sy, sz), at=(0, 0, 3.0 + 0.3 + i * (sz + 0.1)), anchor="bottom"))
            for i in range(STEEL_N)]


def steel_mass_g():
    sx, sy, sz = STEEL_PIECE
    return sx * sy * sz * STEEL_N / 1000 * d.STEEL_SLAB["density"]
