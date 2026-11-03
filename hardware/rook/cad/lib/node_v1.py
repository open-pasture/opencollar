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

# Strap saddle (CAP_STYLE=saddle only). STL is exported in print orientation:
# flank/rail face on the bed, roof + locating pins UP (toward the cap). Channel
# opens toward the bed as a pocket — no bridge. Same CAP_CLAMP / CAP_BAR interface.
SADDLE_ROOF_T = 2.5
SADDLE_H = SADDLE_ROOF_T + CHANNEL_D          # ~5.9
SADDLE_L = 80.0                               # covers clamp Y ±28.5 with margin
SADDLE_W = CAP_W                              # 76 — same width as the cap footprint
SADDLE_NEST_D = 0.0                           # flat mate (no nest); kept for stack math
SADDLE_LEAD_IN = 3.0                          # chamfer length at strap entries (±X)
# Locating: pins on the saddle roof (print face-up) into blind holes in the
# flat cap underside. Cap base must sit fully flat on the bed.
SADDLE_PIN_D = 4.0
SADDLE_PIN_H = 1.5
SADDLE_PIN_HOLE_D = SADDLE_PIN_D + 0.35       # ~Ø4.35 clearance in the cap
SADDLE_PIN_HOLE_DEPTH = 2.0                   # blind; keep-out under CAP_FLOOR_Z=6
SADDLE_PINS = [(sx * 28.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]
# Lid through-screw: Ø8 cbore cylinder ends / cone starts at this z (washer seat).
LID_SCREW_SEAT_Z = 4.0
# Lid insert pocket: cylinder from z=-1 height 6 → blind depth 5.0 from face.
LID_INSERT_POCKET_DEPTH = 5.0

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
    """Clamp screw path and recommended length. Returns (to_insert_mouth_mm, recommend_mm).

    Saddle: the bar rides on the 0.6 mm strap protrusion, so the screw crosses
    bar + saddle + strap gap before the insert mouth. Pocket is blind at z=4.0
    under a 6.0 mm floor — round the screw DOWN so the tip stays in the pocket.
    """
    s = style or CAP_STYLE
    bar = CAP_BAR[2]
    if s == "saddle":
        strap_gap = STRAP_T - CHANNEL_D          # 0.6
        to_mouth = bar + SADDLE_H + strap_gap    # 4 + 5.9 + 0.6 = 10.5
        pocket = 4.0                             # insert seat depth in slim floor
        # Max screw that bottoms at pocket floor; round DOWN to stock length.
        max_screw = to_mouth + pocket            # 14.5 → M3×14
        recommend = 14.0
        return to_mouth, recommend
    return bar + INSERT["length"], 8.0           # gable: bar flush into insert


def lid_screw_stack_mm(style=None):
    """Lid through-screw path and recommended length.

    Seat = LID_SCREW_SEAT_Z (Ø8 cbore cylinder top / cone start). Lid pocket is
    LID_INSERT_POCKET_DEPTH from the mating face; insert is 4.0 mm. Pick a stock
    length that engages the insert without bottoming the tip on the pocket floor.
    """
    s = style or CAP_STYLE
    h = CAP_BASE_H_SADDLE if s == "saddle" else CAP_BASE_H_GABLE
    seat = LID_SCREW_SEAT_Z
    through_base = h - seat
    if s == "saddle":
        # Through base 15.0 (19 − seat 4). M3×16 → tip 1.0 past the face into the
        # insert (≈3 mm of the 4 mm insert engaged if counted from under-head
        # seating with washer stack ≈ seat; practical grip ~3 mm, 2 mm pocket
        # spare). M3×18 tips at ~3–5 mm and can bottom on the 5 mm pocket floor.
        return through_base + INSERT["length"], 16.0
    # Gable: long base; M3×40 with ~4.6 mm into the lid insert (historical).
    return through_base + INSERT["length"], 40.0


# ---------------------------------------------------------------- assembly aids (print-plate learning)
# Engraved labels + light locators. Budget ~15 g PLA / ~30 min on the bases plate.
# See cad/ASSEMBLY-AIDS.md.

AID_REV = "AID1"
ENGRAVE_D = 0.7             # ≥0.6 mm so glyphs stay readable after slice
ENGRAVE_SIZE = 4.5          # 4–5 mm height
ENGRAVE_OVER = 0.5          # cutter past the face so booleans stay clean
CRADLE_H = 2.5              # cell ribs; ≤3 mm into cavity
CRADLE_R = 9.4              # arc seat (~cell R 9.2 + 0.2 clearance)
LOCATOR_H = 1.2
LOCATOR_T = 1.5
BUZZER_CLEAR = 0.3
CABLE_GROOVE_W = 3.0
CABLE_GROOVE_D = 1.2
DIMPLE_D = 1.0
DIMPLE_DEPTH = 0.4


def _manifold_text(name, body, size, depth, at, align="CENTER"):
    """Font mesh remeshed so the boolean stays manifold (Blender 4 curve text
    alone leaves hundreds of non-manifold edges on this toolchain)."""
    obj = oc.text(name, body, size, depth, at=at, align=align)
    m = obj.modifiers.new("aid_remesh", "REMESH")
    m.mode = "SMOOTH"
    m.octree_depth = 7
    m.scale = 0.9
    oc.apply_modifiers(obj)
    return obj


def _engrave_cut(name, body, size, at, z_face, depth=ENGRAVE_D, into="+Z"):
    """Text cutter for engraving into a face.

    into='+Z': cut downward from z_face (inside floor / top face). Cutter
    protrudes past the face so the boolean does not graze coplanar.
    into='-Y'/into='+Y'/into='-X'/into='+X': vertical outer-wall engraving
    (preferred over bed-face cuts — bed-face glyph booleans leave z≈0 slivers).
    """
    if into == "+Z":
        return _manifold_text(name, body, size, depth + ENGRAVE_OVER,
                              at=(at[0], at[1], z_face - depth))
    # Vertical wall: build text along +Z, rotate so depth points into the part.
    txt = _manifold_text(name, body, size, depth + ENGRAVE_OVER, at=(0, 0, 0))
    ax, ay = at[0], at[1]
    az = at[2] if len(at) > 2 else z_face
    if into == "-Y":
        oc.rotate(txt, 90.0, "X")
        oc.bake(txt)
        oc.move(txt, dx=ax, dy=ay - ENGRAVE_OVER, dz=az)
    elif into == "+Y":
        oc.rotate(txt, -90.0, "X")
        oc.bake(txt)
        oc.move(txt, dx=ax, dy=ay + ENGRAVE_OVER, dz=az)
    elif into == "-X":
        oc.rotate(txt, -90.0, "Y")
        oc.bake(txt)
        oc.move(txt, dx=ax - ENGRAVE_OVER, dy=ay, dz=az)
    elif into == "+X":
        oc.rotate(txt, 90.0, "Y")
        oc.bake(txt)
        oc.move(txt, dx=ax + ENGRAVE_OVER, dy=ay, dz=az)
    else:
        raise ValueError(f"unsupported engrave into={into!r}")
    oc.bake(txt)
    return txt


def _l_corner(name, cx, cy, z, sx, sy, t=LOCATOR_T, h=LOCATOR_H, arm=4.0):
    """L-shaped locator at a board corner. (sx,sy) is the inward quadrant."""
    a = oc.box(f"{name}_a", (arm, t, h), at=(cx + sx * arm / 2, cy, z), anchor="bottom")
    b = oc.box(f"{name}_b", (t, arm, h), at=(cx, cy + sy * arm / 2, z), anchor="bottom")
    return oc.union(a, b)


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
    """Slim underside: completely flat bed face, blind pin sockets, clamp
    inserts that stop ≥1 mm short of the cavity (no seal breach)."""
    # Locating pin sockets (blind). Pins live on the saddle roof.
    for i, (x, y) in enumerate(SADDLE_PINS):
        oc.cut(b, oc.cylinder(f"pin_sock{i}", SADDLE_PIN_HOLE_D, SADDLE_PIN_HOLE_DEPTH + 1,
                              at=(x, y, SADDLE_PIN_HOLE_DEPTH - (SADDLE_PIN_HOLE_DEPTH + 1) / 2)))
    # Clamp inserts: Ø4.0 × 4.0 mm seat from underside; flat bottom at z=4.0 →
    # 2.0 mm keep-out under CAP_FLOOR_Z=6 (no cavity breach).
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ins{i}", INSERT["hole_d"], 5.0, at=(x, y, -1), anchor="bottom"))
    return b


def _cap_assembly_aids(b):
    """Inside-floor labels + bed-face dimples for the slim cap.

    Labels stay off the bed face: remeshed glyph booleans into z=0 left hundreds
    of multi-face sliver edges in the STL. Inside floor (CAP_FLOOR_Z) cuts are
    watertight; bed face stays planar (dimples only).
    """
    _, lid_screw = lid_screw_stack_mm("saddle")
    _, clamp_screw = clamp_screw_stack_mm("saddle")
    floor = CAP_FLOOR_Z
    # Mid-field away from clamp inserts / pin sockets / columns.
    labels = [
        _engrave_cut("cap_name", "CAP BASE", ENGRAVE_SIZE, (0, 20), floor),
        _engrave_cut("cap_rev", f"REV {AID_REV}", ENGRAVE_SIZE, (0, 12), floor),
        _engrave_cut("cap_clamp", f"M3x{clamp_screw:.0f} CLAMP", ENGRAVE_SIZE, (0, -12), floor),
        _engrave_cut("cap_lid", f"M3x{lid_screw:.0f} LID", ENGRAVE_SIZE, (0, -20), floor),
        _engrave_cut("cap_ins", "M3x4 INSERT", ENGRAVE_SIZE, (0, -28), floor),
        _engrave_cut("cap_pins", "PIN", ENGRAVE_SIZE, (0, 0), floor),
    ]
    oc.cut(b, *labels)
    # Bed-face dimples only (simple cylinders — no glyph slivers).
    for i, (x, y) in enumerate(CAP_COLS):
        oc.cut(b, oc.cylinder(f"cdim{i}", DIMPLE_D, DIMPLE_DEPTH + 0.1,
                              at=(x - (5.5 if x > 0 else -5.5), y, 0.0), anchor="bottom"))
    return b


def cap_base(style=None):
    if style is not None:
        set_cap_style(style)
    b = _cap_base_shell()
    if CAP_STYLE == "saddle":
        _cap_base_saddle_underside(b)
        b = clean(b)
        _cap_assembly_aids(b)
        return b
    _cap_base_gable_underside(b)
    return clean(b)


def cap_saddle():
    """Printed strap saddle. Exported print-ready: flank/rail face on the bed
    (z=0), roof + locating pins UP toward the cap. Channel opens toward the
    bed (pocket, no bridge). No supports; lead-ins and spine V ≥45°."""
    # Build in roof-at-z=0 frame first (channel cut from the +Z face), then
    # flip 180° about X so the flank face lands on the bed and pins point up.
    s = oc.rounded_rect("cap_saddle", (SADDLE_W, SADDLE_L, SADDLE_H), 2.0, anchor="bottom")
    oc.cut(s, oc.box("schan", (SADDLE_W + 2, CHANNEL_W, CHANNEL_D + 1),
                     at=(0, 0, SADDLE_H - CHANNEL_D + (CHANNEL_D + 1) / 2)))
    for sx in (-1, 1):
        tip_x = sx * (SADDLE_W / 2 + 0.2)
        inner_x = sx * (SADDLE_W / 2 - SADDLE_LEAD_IN)
        oc.cut(s, oc.prism_y(f"lead{sx}", [
            (tip_x, SADDLE_H + 0.2),
            (tip_x, SADDLE_ROOF_T - 0.2),
            (inner_x, SADDLE_H + 0.2),
        ], CHANNEL_W + 0.4, at_y=0.0))
    half_w = SPINE_RELIEF_W / 2
    oc.cut(s, oc.prism_x("spine_v", [
        (-half_w - 0.5, SADDLE_ROOF_T - 0.2),
        (half_w + 0.5, SADDLE_ROOF_T - 0.2),
        (half_w + 0.5, SADDLE_ROOF_T),
        (0.0, SADDLE_H + 0.2),
        (-half_w - 0.5, SADDLE_ROOF_T),
    ], SADDLE_W + 4, at_x=0.0))
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(s, oc.cylinder(f"scl{i}", CLEAR, SADDLE_H + 2, at=(x, y, -1), anchor="bottom"))
    # Pins on the roof pointing toward the cap (−Z here); after the flip they
    # stand up off the roof for the cap's blind sockets. Large flat gasket
    # recess removed (bridged off the bed) — optional grit gasket is a note.
    for i, (x, y) in enumerate(SADDLE_PINS):
        pin = oc.cylinder(f"spin{i}", SADDLE_PIN_D, SADDLE_PIN_H,
                          at=(x, y, -SADDLE_PIN_H), anchor="bottom")
        oc.union(s, pin)
    # Flip: roof+pins up, flank face on bed. Shift so z_min = 0.
    oc.rotate(s, 180.0, "X")
    oc.bake(s)
    lo, _ = oc.bounds(s)
    oc.move(s, dz=-lo[2])
    oc.bake(s)
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
POD_LID_SCREW = 25.0       # M3×25 through pod base into lid inserts


def _pod_assembly_aids(b, side="L"):
    """Cell cradle, buzzer L-locators, cable grooves, labels, column dimples."""
    sx = 1.0 if side == "L" else -1.0
    cell_xy = (sx * CELL_AT[0], CELL_AT[1])
    buzz_xy = (sx * BUZZER_AT[0], BUZZER_AT[1])
    cable_xy = (sx * (POD_L / 2 - POD_WALL / 2), -2.0)

    # (1) Cell cradle: two arc-seat ribs (R=CRADLE_R) under the Ø18.4 cell.
    # Keep clear of corner columns (±37, ±27) — cell-to-column gap stays ≥0.8.
    for i, dx in enumerate((-18.0, 18.0)):
        rx = cell_xy[0] + sx * dx
        rib = oc.box(f"crib{side}{i}", (5.0, 14.0, CRADLE_H),
                     at=(rx, cell_xy[1], POD_FLOOR), anchor="bottom")
        # Cylindrical seat: axis at cell Y / z=POD_FLOOR+R so the top of the
        # 2.5 mm rib becomes an R≈9.4 trough (cell cannot roll on a flat).
        oc.cut(rib, oc.cylinder(f"cseat{side}{i}", 2.0 * CRADLE_R, 7.0,
                                at=(rx, cell_xy[1], POD_FLOOR + CRADLE_R), axis="X"))
        oc.union(b, rib)

    # (2) Buzzer L-corner locators (25.4 board + 0.3 clearance each side).
    # Trim the corner nearest column (±37, +27) so locator-to-column ≥0.5 mm.
    bw = d.QWIIC_BUZZER["board"][0] + 2 * BUZZER_CLEAR
    half = bw / 2
    col_sx = 1 if side == "L" else -1
    for i, (csx, csy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        near_col = (csx == col_sx) and (csy == 1)
        inset = 2.0 if near_col else 0.0
        arm = 2.5 if near_col else 4.0
        cx = buzz_xy[0] + csx * (half - inset)
        cy = buzz_xy[1] + csy * (half - inset)
        loc = _l_corner(f"bl{side}{i}", cx, cy, POD_FLOOR, -csx, -csy, arm=arm)
        oc.union(b, loc)

    # (3) Cable grooves in the floor: cell lead end → crest entry; buzzer → entry.
    cell_lead = (cell_xy[0] + sx * (CELL["l"] / 2 - 2.0), cell_xy[1])
    groovers = []
    mid_x = cable_xy[0] - sx * 6.0
    groovers.append(oc.box(f"cg_cell_x{side}", (abs(mid_x - cell_lead[0]) + CABLE_GROOVE_W,
                                                CABLE_GROOVE_W, CABLE_GROOVE_D + 1),
                           at=((cell_lead[0] + mid_x) / 2, cell_lead[1],
                               POD_FLOOR - CABLE_GROOVE_D), anchor="bottom"))
    groovers.append(oc.box(f"cg_cell_y{side}", (CABLE_GROOVE_W,
                                                abs(cable_xy[1] - cell_lead[1]) + CABLE_GROOVE_W,
                                                CABLE_GROOVE_D + 1),
                           at=(mid_x, (cell_lead[1] + cable_xy[1]) / 2,
                               POD_FLOOR - CABLE_GROOVE_D), anchor="bottom"))
    groovers.append(oc.box(f"cg_buzz{side}", (abs(cable_xy[0] - buzz_xy[0]) + CABLE_GROOVE_W,
                                              CABLE_GROOVE_W, CABLE_GROOVE_D + 1),
                           at=((buzz_xy[0] + cable_xy[0]) / 2, buzz_xy[1],
                               POD_FLOOR - CABLE_GROOVE_D), anchor="bottom"))
    groovers.append(oc.box(f"cg_buzz2{side}", (CABLE_GROOVE_W,
                                               abs(cable_xy[1] - buzz_xy[1]) + CABLE_GROOVE_W,
                                               CABLE_GROOVE_D + 1),
                           at=(cable_xy[0] - sx * 2.0, (buzz_xy[1] + cable_xy[1]) / 2,
                               POD_FLOOR - CABLE_GROOVE_D), anchor="bottom"))
    oc.cut(b, *groovers)

    # (4) Labels on the outer −Y wall (bed face stays flat; floor fonts near
    # grooves/ports left zero-area slivers on the R mirror).
    # Polarity / port cues are box stamps on the floor (watertight).
    floor_marks = [
        # + / − next to the cell (lead end = + toward cable for L).
        oc.box(f"pplus{side}", (3.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
               at=(cell_xy[0] + sx * (CELL["l"] / 2 - 8), cell_xy[1] + 8,
                   POD_FLOOR - ENGRAVE_D), anchor="bottom"),
        oc.box(f"pminus{side}", (3.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
               at=(cell_xy[0] - sx * (CELL["l"] / 2 - 8), cell_xy[1] + 8,
                   POD_FLOOR - ENGRAVE_D), anchor="bottom"),
        # Port arrow toward +X cable entry.
        oc.box(f"pport{side}", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
               at=(sx * 28.0, -2.0, POD_FLOOR - ENGRAVE_D), anchor="bottom"),
        oc.box(f"pbuzz{side}", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
               at=(buzz_xy[0], buzz_xy[1] - 16, POD_FLOOR - ENGRAVE_D), anchor="bottom"),
        oc.box(f"pstud{side}", (5.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
               at=(sx * ELECTRODES[0][0], ELECTRODES[0][1] - 8,
                   POD_FLOOR - ENGRAVE_D), anchor="bottom"),
    ]
    oc.cut(b, *floor_marks)
    wall_y = -(POD_W / 2)
    wall_z = POD_BASE_H / 2
    wall = [
        _engrave_cut(f"pname{side}", "POD BASE", ENGRAVE_SIZE,
                     (0, wall_y, wall_z + 6), wall_z, into="-Y"),
        _engrave_cut(f"pside{side}", side, ENGRAVE_SIZE + 1.5,
                     (sx * 28.0, wall_y, wall_z + 1), wall_z, into="-Y"),
        _engrave_cut(f"prev{side}", f"REV {AID_REV}", ENGRAVE_SIZE,
                     (0, wall_y, wall_z - 4), wall_z, into="-Y"),
        _engrave_cut(f"plid{side}", f"M3x{POD_LID_SCREW:.0f} LID", ENGRAVE_SIZE,
                     (0, wall_y, wall_z - 9), wall_z, into="-Y"),
        _engrave_cut(f"pins{side}", "M3x4 INSERT", ENGRAVE_SIZE,
                     (0, wall_y, wall_z - 14), wall_z, into="-Y"),
        _engrave_cut(f"pportw{side}", "+X PORT" if side == "L" else "-X PORT",
                     ENGRAVE_SIZE, (sx * 20.0, wall_y, wall_z + 6), wall_z, into="-Y"),
        _engrave_cut(f"pbuzzw{side}", "BUZZER", ENGRAVE_SIZE,
                     (sx * -20.0, wall_y, wall_z + 6), wall_z, into="-Y"),
    ]
    oc.cut(b, *wall)

    # (5) Alignment dimples at screw columns (inside floor).
    for i, (x, y) in enumerate(POD_COLS):
        oc.cut(b, oc.cylinder(f"pdim{side}{i}", DIMPLE_D, DIMPLE_DEPTH + ENGRAVE_OVER,
                              at=(x + (6.0 if x > 0 else -6.0), y, POD_FLOOR - DIMPLE_DEPTH),
                              anchor="bottom"))
    return b


def pod_base(side="L"):
    """Pod base. side='L' is the canonical STL; side='R' mirrors asymmetric
    features and labels for a dedicated right-hand print (optional)."""
    sx = 1.0 if side == "L" else -1.0
    b = oc.rounded_box(f"pod_base_{side}", (POD_L, POD_W, POD_BASE_H), 4.0, anchor="bottom")
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
    for i, (x, y) in enumerate(ELECTRODES):
        oc.cut(b, oc.cylinder(f"el{i}", 4.3, POD_FLOOR + 2, at=(sx * x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cylinder(f"elc{i}", 10.0, 1.0 + 1, at=(sx * x, y, -1), anchor="bottom"))
    buzz = (sx * BUZZER_AT[0], BUZZER_AT[1])
    oc.cut(b, oc.cylinder("port", 8.0, POD_WALL + 4, at=(buzz[0], POD_W / 2 - POD_WALL / 2, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("pcable", CABLE_D, POD_WALL + 4,
                          at=(sx * (POD_L / 2 - POD_WALL / 2), -2.0, 12.0), axis="X"))
    b = clean(b)
    _pod_assembly_aids(b, side=side)
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
    # Cell sits in the R=CRADLE_R arc seat (axis at floor+R); top under the rim.
    cell_z = POD_FLOOR + CRADLE_R
    # Buzzer board above the L-locators.
    buzz_z = POD_FLOOR + LOCATOR_H + 0.3
    refs = [
        oc.cylinder("ref_cell", CELL["d"], CELL["l"], at=(CELL_AT[0], CELL_AT[1], cell_z), axis="X"),
        oc.box("ref_buzzer", (qb["board"][0], qb["board"][1], qb["board"][2] + qb["buzzer"]["size"][2]),
               at=(BUZZER_AT[0], BUZZER_AT[1], buzz_z), anchor="bottom"),
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


# ---------------------------------------------------------------- test coupon + scale bar

COUPON_W, COUPON_L, COUPON_H = 40.0, 34.0, 6.0


def test_coupon():
    """~40×34×6 block + 14 mm pin plinth (overall ~56×34×6): insert Ø, blind
    depths, pin sockets, sample pins, short bridge. Target ~5–8 g printed."""
    p = oc.rounded_rect("test_coupon", (COUPON_W, COUPON_L, COUPON_H), 2.0, anchor="bottom")
    # Sample pins first: sink into the plinth, remesh the stick so the pin/plinth
    # union is a single watertight solid, then join to the block.
    px = COUPON_W / 2 + 9.0
    plinth = oc.box("pin_plinth", (14.0, 12.0, 2.0), at=(px, 2.0, 0), anchor="bottom")
    for i in range(3):
        y = -2.0 + i * 4.0
        oc.union(plinth, oc.cylinder(f"spin{i}", 4.0, 1.7,
                                     at=(px, y, 1.8), anchor="bottom"))
    m = plinth.modifiers.new("pin_remesh", "REMESH")
    m.mode = "SMOOTH"
    m.octree_depth = 6
    m.scale = 0.9
    oc.apply_modifiers(plinth)
    oc.union(p, plinth)

    tools, labels = [], []
    for i, dia in enumerate((3.9, 4.0, 4.1)):
        x = -12.0 + i * 12.0
        tools.append(oc.cylinder(f"ins{i}", dia, 5.0 + ENGRAVE_OVER,
                                 at=(x, 12.0, COUPON_H - 5.0), anchor="bottom"))
        # Small box-digit labels (no remesh font) keep the top face watertight.
        labels.append(oc.box(f"insl{i}", (6.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                             at=(x, 7.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    labels.append(oc.box("insrow", (14.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(0, 15.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    for i, depth in enumerate((4.0, 5.0, 6.0)):
        x = -12.0 + i * 12.0
        tools.append(oc.cylinder(f"tap{i}", 2.8, depth + ENGRAVE_OVER,
                                 at=(x, 3.5, COUPON_H - depth), anchor="bottom"))
        tools.append(oc.cylinder(f"clr{i}", 3.2, depth + ENGRAVE_OVER,
                                 at=(x, -3.0, COUPON_H - depth), anchor="bottom"))
        labels.append(oc.box(f"depl{i}", (4.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                             at=(x, -6.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    for i, dia in enumerate((4.2, 4.35, 4.5)):
        x = -12.0 + i * 12.0
        tools.append(oc.cylinder(f"psock{i}", dia, 2.0 + ENGRAVE_OVER,
                                 at=(x, -9.0, COUPON_H - 2.0), anchor="bottom"))
        labels.append(oc.box(f"psl{i}", (5.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                             at=(x, -12.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    labels.append(oc.box("pinlbl", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(px, 10.0, 2.0 - ENGRAVE_D), anchor="bottom"))
    # Inset bridge pocket (20 mm span, 2 mm roof).
    tools.append(oc.box("bridge", (18.0, 6.0, 4.0 + ENGRAVE_OVER),
                        at=(0, -10.0, -ENGRAVE_OVER), anchor="bottom"))
    labels.append(oc.box("brl", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(0, COUPON_L / 2 - 2.2, COUPON_H - ENGRAVE_D), anchor="bottom"))
    labels.append(oc.box("title", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(0, 0.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    oc.cut(p, *tools)
    oc.cut(p, *labels)
    return p


def scale_bar():
    """100 × 10 × 2 mm flat bar with a 20 mm step for shrink measurement."""
    bar = oc.box("scale_bar", (100.0, 10.0, 2.0), anchor="bottom")
    # 20 mm step: drop a 20 mm span by 1 mm (starts at world x=0 → local +40).
    step = oc.box("step", (20.0, 10.2, 1.0 + ENGRAVE_OVER),
                  at=(40.0, 0, 2.0 - 1.0), anchor="bottom")
    oc.cut(bar, step)
    ticks = []
    for x in range(0, 101, 20):
        ticks.append(oc.box(f"tick{x}", (0.4, 4.0, ENGRAVE_D + ENGRAVE_OVER),
                            at=(x - 50.0, -3.0, 2.0 - ENGRAVE_D), anchor="bottom"))
        # Bar stamps instead of font glyphs (watertight).
        ticks.append(oc.box(f"tl{x}", (3.0 if x < 100 else 4.0, 1.0, ENGRAVE_D + ENGRAVE_OVER),
                            at=(x - 50.0, 2.5, 2.0 - ENGRAVE_D), anchor="bottom"))
    bar = clean(bar)
    oc.cut(bar, *ticks)
    return bar
