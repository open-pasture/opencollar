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
# Engraved labels + light locators. Aids ~13 g PLA / ~50 min on the bases plate
# (before coupon ladder + XYZ scale).
# See cad/ASSEMBLY-AIDS.md.

AID_REV = "AID1"
ENGRAVE_D = 0.8             # ≥0.6 mm; deeper so remesh glyphs survive the slice
ENGRAVE_SIZE = 5.0          # ≥4 mm height
ENGRAVE_OVER = 0.5          # cutter past the face so booleans stay clean
CRADLE_H = 2.5              # cell ribs; ≤3 mm into cavity
CRADLE_R = 9.4              # arc seat (~cell R 9.2 + 0.2 clearance)
LOCATOR_H = 1.2
LOCATOR_T = 1.5
BUZZER_CLEAR = 0.3
# Buzzer slot rails: board 1.6 + clear slides under a 45° lip (no supports).
BUZZER_RAIL_LIP = 1.5
BUZZER_RAIL_WALL = 1.5
BUZZER_RAIL_LEN = 16.0          # between L-corner arms; truncated for column keep-out
CABLE_GROOVE_W = 3.0
CABLE_GROOVE_D = 1.2
DIMPLE_D = 1.0
DIMPLE_DEPTH = 0.4
# Slim-cap bq24074 seat (matches cap_refs; collar.py rot=True long-side along Y).
BQ_AT = (0.0, 52.0)
BQ_CLEAR = 0.3
BQ_STAND_H = 1.0               # printable pad; board top of pad
BQ_STAND_D = 5.0
BQ_PILOT_D = 2.1               # self-tap pilot for Ø2.5 board holes
BQ_LOC_H = 3.0
BQ_LOC_ARM = 4.0


# 5×7 bitmap glyphs (rows top→bottom). Built from boxes so engraving booleans
# stay manifold without remesh — Blender font curves + remesh either destroyed
# letterforms (SMOOTH) or left bad_edges (VOXEL) on the real cap/pod bodies.
_FONT_5X7 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10001", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    "x": ["00000", "10001", "01010", "00100", "01010", "10001", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "#": ["01010", "01010", "11111", "01010", "11111", "01010", "01010"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def _manifold_text(name, body, size, depth, at, align="CENTER"):
    """Manifold 5×7 box-bitmap text cutter (no font-curve remesh).

    `size` is the capital height in mm (≥4). Depth is the extrusion along +Z,
    with the mesh sitting on z=at[2] (bottom) up to z=at[2]+depth — matching
    oc.text's footprint so `_engrave_cut` placements stay valid. Bed-face (−Z)
    engraving is still avoided (z≈0 slivers).
    """
    import bpy
    cell = size / 7.0
    gap = cell * 0.2
    cw = 5 * cell + gap  # character pitch
    body = body.upper().replace("×", "x")
    chars = list(body)
    width = max(len(chars) * cw - gap, cell)
    # Origin: same as oc.text CENTER — mid-glyph in XY, bottom at at[2].
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
            # Merge contiguous runs into one box per run (fewer shells).
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
                py = y0 + (6 - row + 0.5) * cell  # row0 at top
                # 0.92× cell: small gap keeps cubes as separate manifold shells
                # so join+difference stays watertight (abut/overlap both failed).
                pixels.append(oc.box(
                    f"{name}_{ci}_{row}_{start}",
                    (run * cell * 0.92, cell * 0.92, depth),
                    at=(px, py, z0), anchor="bottom"))
    if not pixels:
        return oc.box(name, (cell, cell, depth), at=(at[0], at[1], z0), anchor="bottom")
    if len(pixels) == 1:
        pixels[0].name = name
        return pixels[0]
    # Join disconnected manifold cubes — boolean-safe, no remesh.
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for p in pixels:
        p.select_set(True)
    bpy.context.view_layer.objects.active = pixels[0]
    bpy.ops.object.join()
    pixels[0].name = name
    return pixels[0]


def _engrave_cut(name, body, size, at, z_face, depth=ENGRAVE_D, into="+Z"):
    """Text cutter for engraving into a face.

    into='+Z': cut downward from z_face (inside floor / top face).
    into='-Y'/'+Y'/'-X'/'+X': outer-wall engraving. Bed-face (−Z) engraving
    is intentionally unsupported — glyph booleans into z=0 left STL slivers.

    −Y wall: +90° about X makes letter-up → +Z (readable upright from outside).
    Do not mirror X — an extra X flip reads as left-to-right mirror from outside
    (e.g. "#2 POD L" → "J DO9 S#"). Depth runs −Y; cutter straddles the outer face.
    """
    if into == "+Z":
        return _manifold_text(name, body, size, depth + ENGRAVE_OVER,
                              at=(at[0], at[1], z_face - depth))
    from mathutils import Matrix
    dcut = depth + ENGRAVE_OVER
    txt = _manifold_text(name, body, size, dcut, at=(0, 0, 0))
    ax, ay = at[0], at[1]
    az = at[2] if len(at) > 2 else z_face
    if into == "-Y":
        # +90° X: letter-up (+Y) → +Z; extrusion (+Z) → −Y. No X mirror.
        oc.rotate(txt, 90.0, "X")
        oc.bake(txt)
        # Cutter spans y ∈ [origin−dcut, origin]; put origin so it bites ~depth
        # into the wall from the outside face at ay.
        oc.move(txt, dx=ax, dy=ay - 0.2 + dcut, dz=az)
    elif into == "+Y":
        oc.rotate(txt, -90.0, "X")
        oc.bake(txt)
        txt.data.transform(Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0)))
        txt.data.flip_normals()
        oc.move(txt, dx=ax, dy=ay + 0.2 - dcut, dz=az)
    elif into == "-X":
        oc.rotate(txt, 90.0, "Y")
        oc.bake(txt)
        oc.move(txt, dx=ax - 0.2, dy=ay, dz=az)
    elif into == "+X":
        oc.rotate(txt, -90.0, "Y")
        oc.bake(txt)
        oc.move(txt, dx=ax + 0.2, dy=ay, dz=az)
    else:
        raise ValueError(f"unsupported engrave into={into!r}")
    oc.bake(txt)
    return txt


def _l_corner(name, cx, cy, z, sx, sy, t=LOCATOR_T, h=LOCATOR_H, arm=4.0):
    """L-shaped locator at a board corner. (sx,sy) is the inward quadrant."""
    a = oc.box(f"{name}_a", (arm, t, h), at=(cx + sx * arm / 2, cy, z), anchor="bottom")
    b = oc.box(f"{name}_b", (t, arm, h), at=(cx, cy + sy * arm / 2, z), anchor="bottom")
    return oc.union(a, b)


def _slot_rail_y(name, y_edge, x_at, length, z0, side="+Y",
                 slot_h=None, lip=BUZZER_RAIL_LIP, wall=BUZZER_RAIL_WALL):
    """Slot rail along a board edge parallel to X (holds the board down).

    `side='+Y'`: wall outside toward +Y, lip grows −Y over the board.
    `side='-Y'`: mirrored. Lip underside is 45° (lip rise = lip run) so the
    cavity-up print needs no supports.
    """
    if slot_h is None:
        slot_h = d.QWIIC_BUZZER["board"][2] + BUZZER_CLEAR
    h = slot_h + lip
    if side == "+Y":
        # YZ profile CCW from +X: outer wall + 45° lip over the board.
        profile = [
            (y_edge + wall, z0),
            (y_edge + wall, z0 + h),
            (y_edge, z0 + h),
            (y_edge - lip, z0 + slot_h),
            (y_edge, z0 + slot_h),
            (y_edge, z0),
        ]
    elif side == "-Y":
        profile = [
            (y_edge - wall, z0),
            (y_edge, z0),
            (y_edge, z0 + slot_h),
            (y_edge + lip, z0 + slot_h),
            (y_edge, z0 + h),
            (y_edge - wall, z0 + h),
        ]
    else:
        raise ValueError(f"unsupported slot rail side={side!r}")
    return oc.prism_x(name, profile, length, at_x=x_at)


def _bq_hole_xy(at=BQ_AT):
    """bq24074 hole centres in cap coords (board rot=True, long side along Y)."""
    bx, by = d.BQ24074["board"][0], d.BQ24074["board"][1]
    out = []
    for hx, hy in d.BQ24074["holes"]:
        lx, ly = hx - bx / 2, hy - by / 2
        lx, ly = -ly, lx  # 90° CCW — matches collar._board_holes(rot=True)
        out.append((at[0] + lx, at[1] + ly))
    return out


def _arrow_stamp(name, tip, toward="+X", z_face=0.0, length=10.0, width=6.0, depth=ENGRAVE_D):
    """Engraved chevron (box stamps) pointing toward a cable/port axis.

    toward: '+X' | '-X' | '+Y' | '-Y'. Tip is the arrow point XY.
    """
    tx, ty = tip
    half = width / 2
    shaft_w = width * 0.35
    # Shaft rectangle + triangular tip approximated by a short wide box.
    if toward in ("+X", "-X"):
        s = 1.0 if toward == "+X" else -1.0
        shaft = oc.box(f"{name}_s", (length * 0.55, shaft_w, depth + ENGRAVE_OVER),
                       at=(tx - s * (length * 0.35), ty, z_face - depth), anchor="bottom")
        head = oc.box(f"{name}_h", (length * 0.35, width, depth + ENGRAVE_OVER),
                      at=(tx - s * (length * 0.15), ty, z_face - depth), anchor="bottom")
    else:
        s = 1.0 if toward == "+Y" else -1.0
        shaft = oc.box(f"{name}_s", (shaft_w, length * 0.55, depth + ENGRAVE_OVER),
                       at=(tx, ty - s * (length * 0.35), z_face - depth), anchor="bottom")
        head = oc.box(f"{name}_h", (width, length * 0.35, depth + ENGRAVE_OVER),
                      at=(tx, ty - s * (length * 0.15), z_face - depth), anchor="bottom")
    return [shaft, head]


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


def _cap_bq_seat(b):
    """L-corner fence + hole-pattern standoffs for Adafruit 4755 (bq24074).

    Placement matches cap_refs / collar rot=True at BQ_AT. No overhanging
    kit_fence frame — a horizontal ledge would need supports on the cavity-up
    print — so this is L-corners (vertical walls) + Ø5×1 mm standoffs only.
    Slim cap has no kit_fence solid to collide with; kit ref sits at (−6,−6).
    L-walls sit fully outside the board footprint (inner face at board+clear).
    """
    # World half-sizes after rot=True: X=board[1]/2, Y=board[0]/2.
    hx = d.BQ24074["board"][1] / 2 + BQ_CLEAR + LOCATOR_T / 2
    hy = d.BQ24074["board"][0] / 2 + BQ_CLEAR + LOCATOR_T / 2
    z0 = CAP_FLOOR_Z
    for i, (csx, csy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        cx = BQ_AT[0] + csx * hx
        cy = BQ_AT[1] + csy * hy
        loc = _l_corner(f"bql{i}", cx, cy, z0, -csx, -csy,
                        t=LOCATOR_T, h=BQ_LOC_H, arm=BQ_LOC_ARM)
        oc.union(b, loc)
    for i, (x, y) in enumerate(_bq_hole_xy()):
        post = oc.cylinder(f"bqst{i}", BQ_STAND_D, BQ_STAND_H,
                           at=(x, y, z0), anchor="bottom")
        oc.cut(post, oc.cylinder(f"bqpi{i}", BQ_PILOT_D, BQ_STAND_H + 0.5,
                                 at=(x, y, z0 - 0.1), anchor="bottom"))
        oc.union(b, post)
    return b


def _cap_assembly_aids(b):
    """bq24074 seat + inside-floor labels for the slim cap.

    Labels stay off the bed face (glyph cuts into z=0 left STL slivers). Bed
    face stays planar — column dimples removed (read as buried 1 mm cubes).
    """
    _cap_bq_seat(b)
    _, lid_screw = lid_screw_stack_mm("saddle")
    _, clamp_screw = clamp_screw_stack_mm("saddle")
    floor = CAP_FLOOR_Z
    # Mid-field away from clamp inserts / pin sockets / columns / bq seat.
    labels = [
        _engrave_cut("cap_num", "#1 CAP", ENGRAVE_SIZE, (0, 28), floor),
        _engrave_cut("cap_name", "CAP BASE", ENGRAVE_SIZE, (0, 20), floor),
        _engrave_cut("cap_rev", f"REV {AID_REV}", ENGRAVE_SIZE, (0, 12), floor),
        _engrave_cut("cap_clamp", f"M3x{clamp_screw:.0f} CLAMP", ENGRAVE_SIZE, (0, -12), floor),
        _engrave_cut("cap_lid", f"M3x{lid_screw:.0f} LID", ENGRAVE_SIZE, (0, -20), floor),
        _engrave_cut("cap_ins", "M3x4 INSERT", ENGRAVE_SIZE, (0, -28), floor),
        _engrave_cut("cap_pins", "PIN", ENGRAVE_SIZE, (0, 0), floor),
        _engrave_cut("cap_b16", f"M3x{lid_screw:.0f}", ENGRAVE_SIZE - 1.0,
                     (18.0, 40.0), floor),
        _engrave_cut("cap_b14", f"M3x{clamp_screw:.0f}", ENGRAVE_SIZE - 1.0,
                     (12.0, -36.0), floor),
    ]
    oc.cut(b, *labels)
    oc.cut(b, *_arrow_stamp("cap_arrow", (0, 26), toward="+Y", z_face=floor,
                            length=10.0, width=6.0))
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
        # +0.3 above standoff tops so the clearance check doesn't see coplanar contact.
        oc.box("ref_bq24074", (d.BQ24074["board"][1], d.BQ24074["board"][0], BQ_H),
               at=(BQ_AT[0], BQ_AT[1], CAP_FLOOR_Z + BQ_STAND_H + 0.3), anchor="bottom"),
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
# Board edge at x = BUZZER_AT[0] + 12.7; column (37,27) surface at x=33.
# Keep ≥0.5 mm clear → centre ≤ 19.8. Use 19.5 for margin.
BUZZER_AT = (19.5, 15.0)   # board centre
ELECTRODES = [(-30.0, 15.0), (-8.0, 15.0)]
POD_LID_SCREW = 25.0       # M3×25 through pod base into lid inserts


def _pod_assembly_aids(b, side="L"):
    """Cell cradle, buzzer L-locators + rails, cable grooves, wall/floor labels."""
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

    # (2) Buzzer L-corner locators — walls fully outside the board footprint
    # (inner face at board+clear) so the PCB can sit on the floor in the slots.
    # Trim the corner nearest column (±37, +27) so locator-to-column ≥0.5 mm.
    half = d.QWIIC_BUZZER["board"][0] / 2 + BUZZER_CLEAR + LOCATOR_T / 2
    col_sx = 1 if side == "L" else -1
    for i, (csx, csy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        near_col = (csx == col_sx) and (csy == 1)
        # Near column: pull the corner in (−X) and shorten arms (≥0.5 clear).
        arm = 2.5 if near_col else 4.0
        shrink = 2.0 if near_col else 0.0
        cx = buzz_xy[0] + csx * (half - shrink)
        cy = buzz_xy[1] + csy * half
        loc = _l_corner(f"bl{side}{i}", cx, cy, POD_FLOOR, -csx, -csy, arm=arm)
        oc.union(b, loc)

    # (2b) Slot rails on ±Y board edges — board slides in along X (open toward
    # the column end). 45° lip holds the 1.6 mm PCB down; length stays between
    # the L-arms and ≥0.5 mm from column (±37, +27).
    bh = d.QWIIC_BUZZER["board"][1] / 2  # 12.7
    # Bias rail centre away from the column (±X) so the +X end clears 0.5 mm.
    rail_x = buzz_xy[0] - sx * 2.0
    for i, (side_y, y_edge) in enumerate((("+Y", buzz_xy[1] + bh),
                                          ("-Y", buzz_xy[1] - bh))):
        rail = _slot_rail_y(f"brail{side}{i}", y_edge, rail_x, BUZZER_RAIL_LEN,
                            POD_FLOOR, side=side_y)
        oc.union(b, rail)

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
    # Orientation arrow on the floor toward the crest cable entry (±X).
    oc.cut(b, *_arrow_stamp(f"parrow{side}", (sx * 22.0, -2.0),
                            toward=("+X" if side == "L" else "-X"),
                            z_face=POD_FLOOR, length=10.0, width=6.0))
    # Outer −Y wall labels. Five rows at cell 4/3/3/3/3 fit the 24.5 mm
    # wall with ≥1.5 mm bbox gaps and ≥1.5 mm above the bed. PORT/BUZZER
    # and M3 LID/INS stay on separate rows inside x∈[-40, +40].
    wall_y = -(POD_W / 2)
    pod_num = "#2 POD L" if side == "L" else "#3 POD R"
    # cell → centre z: title 4@21.5 · POD 3@16.5 · REV 3@12.0 · PORT 3@7.5
    # · M3 3@3.0. Spans ≈ centre±size/2; gaps 1.5 mm; M3 bottom = 1.5.
    wall = [
        _engrave_cut(f"pnum{side}", pod_num, 4.0,
                     (0, wall_y, 21.5), 21.5, into="-Y"),
        _engrave_cut(f"pname{side}", "POD BASE", 3.0,
                     (0, wall_y, 16.5), 16.5, into="-Y"),
        _engrave_cut(f"pside{side}", side, 3.0,
                     (sx * 30.0, wall_y, 16.5), 16.5, into="-Y"),
        _engrave_cut(f"prev{side}", f"REV {AID_REV}", 3.0,
                     (0, wall_y, 12.0), 12.0, into="-Y"),
        _engrave_cut(f"pportw{side}", "+X PORT" if side == "L" else "-X PORT",
                     3.0, (sx * 22.0, wall_y, 7.5), 7.5, into="-Y"),
        _engrave_cut(f"pbuzzw{side}", "BUZZER", 3.0,
                     (sx * -22.0, wall_y, 7.5), 7.5, into="-Y"),
        _engrave_cut(f"plid{side}", f"M3x{POD_LID_SCREW:.0f} LID", 3.0,
                     (sx * 18.0, wall_y, 3.0), 3.0, into="-Y"),
        _engrave_cut(f"pins{side}", "M3x4 INS", 3.0,
                     (sx * -18.0, wall_y, 3.0), 3.0, into="-Y"),
    ]
    oc.cut(b, *wall)
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
    # Board sits on the floor in the ±Y slot rails; inset Y so the 1.5 mm lips
    # (intentional hold-downs) are not flagged as clearance failures.
    buzz_z = POD_FLOOR
    refs = [
        oc.cylinder("ref_cell", CELL["d"], CELL["l"], at=(CELL_AT[0], CELL_AT[1], cell_z), axis="X"),
        oc.box("ref_buzzer", (qb["board"][0],
                              qb["board"][1] - 2 * BUZZER_RAIL_LIP - 0.2,
                              qb["board"][2] + qb["buzzer"]["size"][2]),
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

# Coupon overall: block + pin plinth (+X) + screw gauge (−X) + insert ladder (+Y)
# + free e-foot. Ladder plinth is 8 mm tall so INSERT hole_depth 6 stays blind.
COUPON_GAUGE_W = 10.0
COUPON_GAUGE_MAX_H = 18.0   # tallest screw-gauge step (M3×18)
COUPON_LADDER_H = 8.0
COUPON_LADDER_Y = COUPON_L / 2 + 8.0   # centre of +Y insert-ladder plinth
COUPON_OVERALL_X = (COUPON_W / 2 + COUPON_GAUGE_W) + (COUPON_W / 2 + 18.5)  # 68.5
COUPON_OVERALL_Y = COUPON_LADDER_Y + 6.0 + (COUPON_L / 2 + 3.5)  # ladder + e-foot
SCALE_X, SCALE_Y, SCALE_Z = 100.0, 50.0, 20.0
SCALE_ARM_W = 8.0


def test_coupon():
    """Fit coupon: insert ladder, mating-face gaps, screw gauge, pins, bridge.

    - M3 heat-set ladder Ø4.0/4.2/4.4/4.6/4.8 × INSERT.hole_depth (6 mm) on an
      8 mm plinth (blind).
    - Lid / clamp mating-face gap pads 0.1–0.4 mm proud of the block top.
    - Stepped M3×14/16/18 Ø2.8 blind screw-length gauge (−X).
    - Legacy pin sockets / sample pins / bridge / e-foot retained.
    - Cheap extras: O-ring groove sample + ANT keep-out stamp.
    """
    p = oc.rounded_rect("test_coupon", (COUPON_W, COUPON_L, COUPON_H), 2.0, anchor="bottom")
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

    # +Y insert-ladder plinth (tall enough for blind Ø holes at real depth).
    ly = COUPON_LADDER_Y
    oc.union(p, oc.box("ins_plinth", (48.0, 12.0, COUPON_LADDER_H),
                       at=(0, ly, 0), anchor="bottom"))

    gx = -(COUPON_W / 2 + COUPON_GAUGE_W / 2)
    tools, labels = [], []
    for i, length in enumerate((14.0, 16.0, 18.0)):
        y = -12.0 + i * 12.0
        step = oc.box(f"gstep{i}", (COUPON_GAUGE_W, 10.0, length),
                      at=(gx, y, 0), anchor="bottom")
        oc.union(p, step)
        # 0.2 mm floor so M3×L under-head seats nearly flush (1 mm floor left
        # the head ~1 mm proud — M3×14 looked like it belonged on the 16 step).
        # Overcut only upward — ENGRAVE_OVER below the floor would punch through.
        tools.append(oc.cylinder(f"gpilot{i}", 2.8, length - 0.2 + ENGRAVE_OVER,
                                 at=(gx, y, 0.2), anchor="bottom"))
        labels.append(oc.box(f"glen{i}", (length / 4.0, 1.0, ENGRAVE_D + ENGRAVE_OVER),
                             at=(gx, y + 4.0, length - ENGRAVE_D), anchor="bottom"))

    oc.union(p, oc.box("efoot", (1.0, 1.0, 0.8),
                       at=(px + 9.0, -(COUPON_L / 2 + 3.0), 0),
                       anchor="bottom"))

    # M3 heat-set insert ladder (dims.INSERT_M3 hole_depth = 6).
    ins_depth = INSERT["hole_depth"]
    for i, dia in enumerate((4.0, 4.2, 4.4, 4.6, 4.8)):
        x = -16.0 + i * 8.0
        tools.append(oc.cylinder(f"ins{i}", dia, ins_depth + ENGRAVE_OVER,
                                 at=(x, ly, COUPON_LADDER_H - ins_depth),
                                 anchor="bottom"))
        labels.append(oc.box(f"insl{i}", (5.0, 1.0, ENGRAVE_D + ENGRAVE_OVER),
                             at=(x, ly - 4.5, COUPON_LADDER_H - ENGRAVE_D),
                             anchor="bottom"))
    labels.append(oc.box("insrow", (16.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(0, ly + 4.5, COUPON_LADDER_H - ENGRAVE_D),
                         anchor="bottom"))

    # Mating-face clearance pads (proud of block top) — lid row / clamp row.
    for i, gap in enumerate((0.1, 0.2, 0.3, 0.4)):
        x = -12.0 + i * 8.0
        oc.union(p, oc.box(f"lidgap{i}", (6.0, 6.0, gap),
                           at=(x, 10.0, COUPON_H), anchor="bottom"))
        oc.union(p, oc.box(f"clgap{i}", (6.0, 6.0, gap),
                           at=(x, -14.0, COUPON_H), anchor="bottom"))
    labels.append(oc.box("lidgaplbl", (10.0, 1.0, ENGRAVE_D + ENGRAVE_OVER),
                         at=(0, 14.0, COUPON_H - ENGRAVE_D), anchor="bottom"))
    labels.append(oc.box("clgaplbl", (10.0, 1.0, ENGRAVE_D + ENGRAVE_OVER),
                         at=(0, -10.0, COUPON_H - ENGRAVE_D), anchor="bottom"))

    # Tap/clear depth + pin sockets — keep ≥1 mm floor (6 mm tap used to
    # break through the 6 mm block; Ø4.35 socket stays blind too).
    for i, depth in enumerate((4.0, 5.0, 6.0)):
        x = -12.0 + i * 12.0
        blind = min(depth, COUPON_H - 1.0)
        tools.append(oc.cylinder(f"tap{i}", 2.8, blind + ENGRAVE_OVER,
                                 at=(x, 3.5, COUPON_H - blind), anchor="bottom"))
        tools.append(oc.cylinder(f"clr{i}", 3.2, blind + ENGRAVE_OVER,
                                 at=(x, -3.0, COUPON_H - blind), anchor="bottom"))
        labels.append(oc.box(f"depl{i}", (4.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                             at=(x, -6.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    for i, dia in enumerate((4.2, 4.35, 4.5)):
        x = -12.0 + i * 12.0
        sock_d = min(2.0, COUPON_H - 1.0)
        tools.append(oc.cylinder(f"psock{i}", dia, sock_d + ENGRAVE_OVER,
                                 at=(x, -9.0, COUPON_H - sock_d), anchor="bottom"))
        labels.append(oc.box(f"psl{i}", (5.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                             at=(x, -12.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    labels.append(oc.box("pinlbl", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(px, 10.0, 2.0 - ENGRAVE_D), anchor="bottom"))
    tools.append(oc.box("bridge", (18.0, 6.0, 4.0 + ENGRAVE_OVER),
                        at=(0, -10.0, -ENGRAVE_OVER), anchor="bottom"))

    # O-ring groove sample (dims.ORING_2MM) on the ladder +Y edge — cheap.
    gw, gd = GROOVE["groove_w"], GROOVE["groove_d"]
    tools.append(oc.box("oring", (20.0, gw, gd + ENGRAVE_OVER),
                        at=(0, ly + 6.0 - gw / 2,
                            COUPON_LADDER_H - gd), anchor="bottom"))
    # Antenna keep-out stamp (box cue, not a tuned RF mark).
    labels.append(oc.box("ant", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(16.0, 0.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    labels.append(oc.box("title", (8.0, 1.2, ENGRAVE_D + ENGRAVE_OVER),
                         at=(0, 0.5, COUPON_H - ENGRAVE_D), anchor="bottom"))
    # Part number on ladder wall (+Y face) via floor stamp on plinth top.
    oc.cut(p, _engrave_cut("cnum", "#4 COUPON", ENGRAVE_SIZE - 1.0,
                           (0, ly), COUPON_LADDER_H))
    oc.cut(p, *tools)
    oc.cut(p, *labels)
    return p


def scale_bar():
    """Tri-axis L-bar: 100 X × 50 Y × 20 Z with 10 mm ticks (low print height)."""
    w = SCALE_ARM_W
    # Corner at origin; arms along +X / +Y; Z post at the corner.
    xarm = oc.box("sx", (SCALE_X, w, 3.0), at=(SCALE_X / 2, w / 2, 0), anchor="bottom")
    yarm = oc.box("sy", (w, SCALE_Y, 3.0), at=(w / 2, SCALE_Y / 2, 0), anchor="bottom")
    zpost = oc.box("sz", (w, w, SCALE_Z), at=(w / 2, w / 2, 0), anchor="bottom")
    oc.union(xarm, yarm, zpost)
    ticks = []
    for x in range(0, int(SCALE_X) + 1, 10):
        ticks.append(oc.box(f"tx{x}", (0.4, 3.0, ENGRAVE_D + ENGRAVE_OVER),
                            at=(x, w - 1.5, 3.0 - ENGRAVE_D), anchor="bottom"))
    for y in range(0, int(SCALE_Y) + 1, 10):
        ticks.append(oc.box(f"ty{y}", (3.0, 0.4, ENGRAVE_D + ENGRAVE_OVER),
                            at=(w - 1.5, y, 3.0 - ENGRAVE_D), anchor="bottom"))
    for z in range(0, int(SCALE_Z) + 1, 10):
        # Tick on +X face of the Z post (vertical face — cut as thin horizontal kerf).
        ticks.append(oc.box(f"tz{z}", (ENGRAVE_D + ENGRAVE_OVER, 3.0, 0.4),
                            at=(w - ENGRAVE_D / 2, w / 2, z), anchor="bottom"))
    oc.cut(xarm, *ticks)
    oc.cut(xarm, _engrave_cut("snum", "#5 SCALE", ENGRAVE_SIZE - 1.0,
                              (SCALE_X / 2, w / 2), 3.0))
    return xarm


def bases_plate_footprint_mm():
    """Conservative AABB if cap + 2 pods + coupon + scale share one 246 plate.

    Layout assumed (mm gaps ≥2): cap at origin; pods stacked +X of cap;
    coupon + scale along −Y of the pods. Returns (width, depth).
    """
    gap = 2.0
    # Cap 76×160; pods 92×68 stacked in Y beside cap.
    w = CAP_W + gap + POD_L                     # 76+2+92 = 170
    d = max(CAP_L, 2 * POD_W + gap)              # max(160, 138) = 160
    # Coupon + scale along −Y of the pack.
    d += gap + max(COUPON_OVERALL_Y, SCALE_Y)    # +~54
    w = max(w, COUPON_OVERALL_X + gap + SCALE_X)  # coupon+scale side by side
    return (round(w, 1), round(d, 1))
