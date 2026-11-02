"""Node V1, option 1 ("three modules"): a low top cap on the spine and a pod on
each side of the neck, plus an encased steel counterweight. See
docs/concepts/side-pod-options.html and docs/NODE-V1-BUILD.md.

Unit #1 is built from parts already on hand plus a small order:
  cap   nRF9151 Connect Kit (MCU, LTE-M, GNSS), bq24074 charger, ISM330 IMU,
        GPS patch, LTE flex antenna, 2 x Voltaic P122 panels on the lid
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
STRAP_T = d.STRAP["design_thickness"]       # 4.0 (measure)
CHANNEL_W = STRAP_W + 2.0
CHANNEL_D = STRAP_T - 0.6                   # 0.6 mm squeeze under the clamp bars
INSERT = d.INSERT_M3
GROOVE = d.ORING_2MM
CBORE_D, CBORE_DEPTH = 8.0, 4.0             # button head + bonded washer
CLEAR = d.M3["clear_d"]
CABLE_D = 6.0                               # potted cable entry, cable OD <= 5.5

# ---------------------------------------------------------------- bought parts (unit #1)

CELL = {"d": 18.4, "l": 69.0, "mass_g": 46}          # Adafruit 1781, pub
P122 = {"size": (52.0, 52.0, 3.0), "mass_g": 12.1}    # Voltaic P122, pub (Adafruit 5855: 52x52x3)
BQ_H = 11.0                                           # est: tallest part on the bq24074 board; measure
PATCH_H = 6.0                                         # est: ceramic 4 + board/LNA; measure
STEEL_PIECE = (76.2, 50.8, 6.35)                      # 3 in of 2 x 1/4 in flat bar
STEEL_N = 4

# ---------------------------------------------------------------- cap

CAP_W, CAP_L = 62.0, 142.0
CAP_WALL = 5.0
CAP_FLOOR_Z = 7.5          # cavity floor (solid below: channel, inserts, spine relief)
CAP_BASE_H = 20.5          # cavity 13 mm
CAP_LID_T = 7.0
SPINE_RELIEF = (28.0, 5.0)  # width across the neck, depth, outside the strap zone
CAP_COLS = [(sx * 22.5, y) for sx in (-1, 1) for y in (-60.0, -37.0, 37.0, 60.0)]
CAP_CLAMP = [(sx * 20.0, sy * 28.5) for sx in (-1, 1) for sy in (-1, 1)]
CAP_BAR = (10.0, 70.0, 4.0)
PANEL_Y = (-12.3, 41.7)    # panel pocket centres on the lid
PANEL_POCKET = (52.6, 52.6, 1.2)
PATCH_Y = -52.0


def _groove_loop(name, w, l, r, z_top, inset):
    """A rectangular O-ring groove cut downward from z_top, its centreline
    `inset` in from the outer edge of a w x l outline."""
    g, gd = GROOVE["groove_w"], GROOVE["groove_d"]
    outer = oc.rounded_rect(name + "_o", (w - 2 * (inset - g / 2), l - 2 * (inset - g / 2), gd + 1),
                            max(r - inset + g / 2, 0.6), at=(0, 0, z_top - gd), anchor="bottom")
    inner = oc.rounded_rect(name + "_i", (w - 2 * (inset + g / 2), l - 2 * (inset + g / 2), gd + 3),
                            max(r - inset - g / 2, 0.4), at=(0, 0, z_top - gd - 1), anchor="bottom")
    return oc.cut(outer, inner)


def cap_base():
    b = oc.rounded_rect("cap_base", (CAP_W, CAP_L, CAP_BASE_H), 10.0, anchor="bottom")
    # Cavity, then screw columns added back.
    cav = oc.rounded_rect("cav", (CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, CAP_BASE_H), 5.0,
                          at=(0, 0, CAP_FLOOR_Z), anchor="bottom")
    oc.cut(b, cav)
    cols = [oc.cylinder(f"col{i}", 8.0, CAP_BASE_H - CAP_FLOOR_Z + 0.2, at=(x, y, CAP_FLOOR_Z - 0.5), anchor="bottom")
            for i, (x, y) in enumerate(CAP_COLS)]
    oc.union(b, *cols)
    # Underside: strap channel across the neck, spine relief outside it, a gentle concave.
    oc.cut(b, oc.box("chan", (CAP_W + 2, CHANNEL_W, CHANNEL_D + 1), at=(0, 0, CHANNEL_D - (CHANNEL_D + 1) / 2)))
    zone = (CAP_L - CHANNEL_W) / 2
    for sy in (-1, 1):
        yc = sy * (CHANNEL_W / 2 + zone / 2)
        oc.cut(b, oc.box("spine", (SPINE_RELIEF[0], zone + 0.2, SPINE_RELIEF[1] + 1),
                         at=(0, yc, SPINE_RELIEF[1] - (SPINE_RELIEF[1] + 1) / 2)))
    # Through screws for the lid (from below) with counterbores; clamp-bar inserts.
    for i, (x, y) in enumerate(CAP_COLS):
        oc.cut(b, oc.cylinder(f"h{i}", CLEAR, CAP_BASE_H + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cylinder(f"cb{i}", CBORE_D, CBORE_DEPTH + 1, at=(x, y, -1), anchor="bottom"))
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ins{i}", INSERT["hole_d"], INSERT["hole_depth"] + 1, at=(x, y, -1), anchor="bottom"))
    # O-ring groove in the rim, centred on the wall.
    oc.cut(b, _groove_loop("groove", CAP_W, CAP_L, 10.0, CAP_BASE_H, CAP_WALL / 2))
    # Potted cable entries, one each side, to the pods.
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cable{sx}", CABLE_D, CAP_WALL + 4, at=(sx * (CAP_W / 2 - CAP_WALL / 2), 0, 14.0), axis="X"))
    return clean(b)


def cap_lid():
    slab = oc.rounded_rect("cap_lid", (CAP_W, CAP_L, 3.0), 10.0, anchor="bottom")
    top = oc.rounded_box("lid_top", (CAP_W, CAP_L, CAP_LID_T - 1.0), 2.5, at=(0, 0, 1.0), anchor="bottom")
    oc.intersect(top, oc.rounded_rect("trim", (CAP_W, CAP_L, CAP_LID_T + 2), 10.0, at=(0, 0, -1), anchor="bottom"))
    oc.union(slab, top)
    for i, (x, y) in enumerate(CAP_COLS):
        oc.cut(slab, oc.cylinder(f"li{i}", INSERT["hole_d"], 4.5 + 1, at=(x, y, -1), anchor="bottom"))
    for i, y in enumerate(PANEL_Y):
        px, py, pz = PANEL_POCKET
        oc.cut(slab, oc.rounded_rect(f"pocket{i}", (px, py, pz + 1), 1.0, at=(0, y, CAP_LID_T - pz), anchor="bottom"))
        oc.cut(slab, oc.cylinder(f"wire{i}", 4.0, CAP_LID_T + 2, at=(0, y, -1), anchor="bottom"))
    return slab


def cap_bar():
    x, y, z = CAP_BAR
    bar = oc.rounded_box("cap_bar", (x, y, z), 1.5, anchor="bottom")
    for sy in (-1, 1):
        oc.cut(bar, oc.cylinder(f"bh{sy}", CLEAR, z + 2, at=(0, sy * 28.5, -1), anchor="bottom"))
        oc.cut(bar, oc.cylinder(f"bc{sy}", d.M3_BUTTON["head_cbore_d"], d.M3_BUTTON["head_cbore_depth"] + 1,
                                at=(0, sy * 28.5, -1), anchor="bottom"))
    return bar


def cap_refs(z_lid=CAP_BASE_H):
    """Bought parts inside the cap, in cap coordinates."""
    k = d.NRF9151_KIT
    kb = k["board"]
    refs = [
        oc.box("ref_kit", (kb[1], kb[0], kb[2] + k["above_pcb"]), at=(-6.0, -6.0, CAP_FLOOR_Z + 2.0), anchor="bottom"),
        oc.box("ref_bq24074", (d.BQ24074["board"][1], d.BQ24074["board"][0], BQ_H), at=(0.0, 45.5, CAP_FLOOR_Z + 0.3), anchor="bottom"),
        oc.box("ref_ism330", (d.ISM330["board"][1], d.ISM330["board"][0], 3.2), at=(13.5, -8.0, CAP_FLOOR_Z + 2.0), anchor="bottom"),
        oc.box("ref_gps_patch", (25.0, 25.0, PATCH_H), at=(0, PATCH_Y, CAP_BASE_H - PATCH_H - 0.6), anchor="bottom"),
        oc.box("ref_lte_flex", (0.4, 44.0, 10.0), at=(CAP_W / 2 - CAP_WALL - 0.6, 10.0, 9.0), anchor="bottom"),
    ]
    for i, y in enumerate(PANEL_Y):
        px, py, pz = P122["size"]
        refs.append(oc.box(f"ref_p122_{i}", (px, py, pz), at=(0, y, z_lid + CAP_LID_T - PANEL_POCKET[2] + 0.05), anchor="bottom"))
    return [oc.reference(r) for r in refs]


# ---------------------------------------------------------------- pod

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
