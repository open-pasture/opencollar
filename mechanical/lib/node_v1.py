"""Node V1, option 1 ("three modules"): a low top cap on the spine and a pod on
each side of the neck, plus an encased steel counterweight. See
docs/concepts/side-pod-options.html and docs/NODE-V1-BUILD.md.

Unit #1 is built from parts already on hand:
  cap      nRF9151 Connect Kit (MCU, LTE-M, GNSS), bq24074 charger, ISM330 IMU,
           GPS patch, LTE flex antenna, 1 x Voltaic P124 on the lid
           (see HARDWARE-FIT.md)
  battery  left pod: owned Adafruit 353 6600 mAh pack (power to the cap).
           Do not buy Adafruit 1781 cells.
  cue      right pod: the one owned Qwiic Buzzer (mono cues for unit #1).
           Both pods keep two electrode studs (not wired on unit #1).
  cw       four 3 in pieces of 2 x 1/4 in steel flat bar in a printed casing

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

# Owned Adafruit 353 pack (dims.LIION_6600). Not the never-bought 1781 cells.
PACK = d.LIION_6600
PACK_CLEAR = 1.0                                      # ~1 mm air per side around the pack
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

CAP_W, CAP_L = 76.0, 160.0
CAP_WALL = 5.0
# Floor clears the channel gable peak (CHANNEL_D + CHANNEL_ROOF_H) plus ≥1 mm,
# and the 45° spine V, under a 13 mm cavity.
CAP_FLOOR_Z = CHANNEL_D + CHANNEL_ROOF_H + 1.5   # ~28.4
CAP_BASE_H = CAP_FLOOR_Z + 13.0                  # ~41.4
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
    # Underside strap channel: rectangular strap pocket, then a single gable
    # across Y (ridge along X). No flat valleys — every ceiling flank is
    # steeper than 45° and anchored on the ±Y walls.
    half_c = CHANNEL_W / 2
    oc.cut(b, oc.box("chan", (CAP_W + 2, CHANNEL_W, CHANNEL_D + 1),
                     at=(0, 0, CHANNEL_D - (CHANNEL_D + 1) / 2)))
    # Gable cutter: vertical risers at the channel lips, then flanks to the ridge
    # so there is no leftover flat ledge at z = CHANNEL_D.
    oc.cut(b, oc.prism_x("chan_gable", [
        (-half_c, CHANNEL_D - 0.2),
        (half_c, CHANNEL_D - 0.2),
        (half_c, CHANNEL_D),
        (0.0, CHANNEL_D + CHANNEL_ROOF_H),
        (-half_c, CHANNEL_D),
    ], CAP_W + 4, at_x=0.0))
    zone = (CAP_L - CHANNEL_W) / 2
    half_w = SPINE_RELIEF_W / 2
    # Opening padded ±0.5; ridge high enough that flanks stay > 45°.
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
    # Through screws for the lid (from below). Counterbore is a cone that meets
    # the clearance hole (no leftover flat ceiling at z = CBORE_DEPTH).
    for i, (x, y) in enumerate(CAP_COLS):
        oc.cut(b, oc.cylinder(f"h{i}", CLEAR, CAP_BASE_H + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cone(f"cb{i}", CBORE_D, CLEAR, CBORE_DEPTH, at=(x, y, 0.0)))
    # Clamp-bar inserts: cylinder then cone starting at the cylinder top so
    # there is no annular flat (the old z≈3.2 rings).
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ins{i}", INSERT["hole_d"], 3.0, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cone(f"instip{i}", INSERT["hole_d"], 0.2, 3.0, at=(x, y, 2.0)))
    # O-ring groove in the rim, centred on the wall.
    oc.cut(b, _groove_loop("groove", CAP_W, CAP_L, 10.0, CAP_BASE_H, CAP_WALL / 2))
    # Potted cable entries, one each side, to the pods (mid-cavity height).
    cable_z = CAP_FLOOR_Z + (CAP_BASE_H - CAP_FLOOR_Z) / 2
    for sx in (-1, 1):
        oc.cut(b, oc.cylinder(f"cable{sx}", CABLE_D, CAP_WALL + 4,
                              at=(sx * (CAP_W / 2 - CAP_WALL / 2), 0, cable_z), axis="X"))
    return clean(b)


def cap_lid():
    # Single rounded body (no 3 mm slab step) so the mating-face-down print
    # has no flat ledge at z = 3.
    slab = oc.rounded_box("cap_lid", (CAP_W, CAP_L, CAP_LID_T), 2.5, anchor="bottom")
    oc.intersect(slab, oc.rounded_rect("trim", (CAP_W, CAP_L, CAP_LID_T + 2), 10.0, at=(0, 0, -1), anchor="bottom"))
    for i, (x, y) in enumerate(CAP_COLS):
        # Blind insert seat: short cylinder then a conical tip (no flat ceiling).
        oc.cut(slab, oc.cylinder(f"lih{i}", INSERT["hole_d"], 3.2, at=(x, y, -1), anchor="bottom"))
        oc.cut(slab, oc.cone(f"li{i}", INSERT["hole_d"], 0.2, 2.2, at=(x, y, 2.0)))
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


# ---------------------------------------------------------------- pods
# One battery pod (Adafruit 353) + one cue pod (Qwiic Buzzer). Cap holds the
# bq24074; the pack feeds it over the battery-pod cable. Cue pod has no cell.
# Strap channel / clamp Y (±29.5) / 70 mm bar match the other modules.

POD_WALL = 5.0
POD_FLOOR = 3.0
POD_LID_T = 6.0
POD_BASE_H = 26.0          # cavity 23 mm; lid screws M3×30 from the skin side
POD_BAR = (10.0, 70.0, 4.0)
POD_CLAMP_Y = 29.5         # shared with the 70 mm clamp bar

# Battery pod: pack 69×54×18 + 1 mm/side → 71×56 locator; columns clear the pack
# (pack half 34.5×27; column r=4 + 1 mm → centres beyond ≈40.5, 32). Outline
# is roomy enough that the O-ring groove stays clear of the column bosses.
POD_BAT_L, POD_BAT_W = 100.0, 90.0
POD_BAT_COLS = [(sx * 42.0, sy * 32.0) for sx in (-1, 1) for sy in (-1, 1)]
POD_BAT_CLAMP = [(sx * 36.0, sy * POD_CLAMP_Y) for sx in (-1, 1) for sy in (-1, 1)]
PACK_AT = (0.0, 0.0)
PACK_POCKET = (PACK["size"][0] + 2 * PACK_CLEAR, PACK["size"][1] + 2 * PACK_CLEAR, 1.2)
ELECTRODES_BAT = [(-20.0, -36.0), (20.0, -36.0)]  # −Y edge, clear of pack and side wall

# Cue pod: no battery bay; one buzzer + electrodes. Outline stays near the old 92×68.
POD_CUE_L, POD_CUE_W = 92.0, 68.0
POD_CUE_COLS = [(sx * 37.0, sy * 27.0) for sx in (-1, 1) for sy in (-1, 1)]
POD_CUE_CLAMP = [(sx * 32.0, sy * POD_CLAMP_Y) for sx in (-1, 1) for sy in (-1, 1)]
BUZZER_AT = (0.0, 10.0)
ELECTRODES_CUE = [(-28.0, -12.0), (28.0, -12.0)]

# Aliases so older call sites that expect a single outline still resolve.
POD_L, POD_W = POD_BAT_L, POD_BAT_W
POD_COLS = POD_BAT_COLS
POD_CLAMP = POD_BAT_CLAMP


def _pod_shell(name, length, width, cols):
    """Shared sealed shell: cavity, screw columns, conical counterbores, O-ring."""
    b = oc.rounded_box(name, (length, width, POD_BASE_H), 4.0, anchor="bottom")
    oc.union(b, oc.rounded_rect(name + "_rim", (length, width, 10.0), 9.0,
                                at=(0, 0, POD_BASE_H - 10.0), anchor="bottom"))
    oc.intersect(b, oc.rounded_rect(name + "_trim", (length, width, POD_BASE_H + 2), 9.0,
                                    at=(0, 0, -1), anchor="bottom"))
    cav = oc.rounded_rect(name + "_cav", (length - 2 * POD_WALL, width - 2 * POD_WALL, POD_BASE_H), 4.0,
                          at=(0, 0, POD_FLOOR), anchor="bottom")
    oc.cut(b, cav)
    bosses = [oc.cylinder(f"{name}_col{i}", 8.0, POD_BASE_H - POD_FLOOR + 0.5,
                          at=(x, y, POD_FLOOR - 0.5), anchor="bottom")
              for i, (x, y) in enumerate(cols)]
    oc.union(b, *bosses)
    for i, (x, y) in enumerate(cols):
        oc.cut(b, oc.cylinder(f"{name}_h{i}", CLEAR, POD_BASE_H + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cone(f"{name}_cb{i}", CBORE_D, CLEAR, CBORE_DEPTH, at=(x, y, 0.0)))
    oc.cut(b, _groove_loop(name + "_groove", length, width, 9.0, POD_BASE_H, POD_WALL / 2))
    return b


def _pod_electrodes(b, electrodes):
    for i, (x, y) in enumerate(electrodes):
        oc.cut(b, oc.cylinder(f"el{i}", 4.3, POD_FLOOR + 2, at=(x, y, -1), anchor="bottom"))
        oc.cut(b, oc.cylinder(f"elc{i}", 10.0, 2.0, at=(x, y, -1), anchor="bottom"))


def _pod_lid(name, length, width, cols, clamps):
    # Single rounded body (no slab step) so mating-face-down has no flat ledge.
    slab = oc.rounded_box(name, (length, width, POD_LID_T), 2.5, anchor="bottom")
    oc.intersect(slab, oc.rounded_rect(name + "_trim", (length, width, POD_LID_T + 2), 9.0,
                                       at=(0, 0, -1), anchor="bottom"))
    oc.cut(slab, oc.box(name + "_chan", (length + 2, CHANNEL_W, CHANNEL_D + 1),
                        at=(0, 0, POD_LID_T - CHANNEL_D + (CHANNEL_D + 1) / 2)))
    for i, (x, y) in enumerate(cols):
        # Blind insert from the mating face: cylinder then conical tip.
        oc.cut(slab, oc.cylinder(f"{name}_ih{i}", INSERT["hole_d"], 3.0, at=(x, y, -1), anchor="bottom"))
        oc.cut(slab, oc.cone(f"{name}_it{i}", INSERT["hole_d"], 0.2, 2.2, at=(x, y, 2.0)))
    for i, (x, y) in enumerate(clamps):
        # Clamp inserts from the outer face (open upward when printing mating-down).
        oc.cut(slab, oc.cylinder(f"{name}_ci{i}", INSERT["hole_d"], 4.5 + 1,
                                 at=(x, y, POD_LID_T - 4.5), anchor="bottom"))
    return slab


def pod_battery_base():
    """Left / battery pod: Adafruit 353 pack bay, electrodes, vent, crest cable."""
    b = _pod_shell("pod_bat", POD_BAT_L, POD_BAT_W, POD_BAT_COLS)
    _pod_electrodes(b, ELECTRODES_BAT)
    # 1.2 mm locator recess for the pack (foam / VHB fills the rest of the height).
    px, py, pz = PACK_POCKET
    oc.cut(b, oc.rounded_rect("pack_pocket", (px, py, pz + 1), 2.0,
                              at=(PACK_AT[0], PACK_AT[1], POD_FLOOR - 0.05), anchor="bottom"))
    # ePTFE vent patch seat (no sealed-battery pressure); −Y wall.
    oc.cut(b, oc.cylinder("pvent", 8.0, POD_WALL + 4,
                          at=(0.0, -(POD_BAT_W / 2 - POD_WALL / 2), 14.0), axis="Y"))
    # Potted cable to the cap (power + optional sense), crest end (+X).
    oc.cut(b, oc.cylinder("pcable", CABLE_D, POD_WALL + 4,
                          at=(POD_BAT_L / 2 - POD_WALL / 2, -2.0, 14.0), axis="X"))
    return clean(b)


def pod_battery_lid():
    return _pod_lid("pod_bat_lid", POD_BAT_L, POD_BAT_W, POD_BAT_COLS, POD_BAT_CLAMP)


def pod_cue_base():
    """Right / cue pod: one Qwiic Buzzer, electrodes, no battery bay."""
    b = _pod_shell("pod_cue", POD_CUE_L, POD_CUE_W, POD_CUE_COLS)
    _pod_electrodes(b, ELECTRODES_CUE)
    # Sound port toward the head (+Y), at the buzzer; acoustic membrane inside.
    oc.cut(b, oc.cylinder("port", 8.0, POD_WALL + 4,
                          at=(BUZZER_AT[0], POD_CUE_W / 2 - POD_WALL / 2, 12.0), axis="Y"))
    oc.cut(b, oc.cylinder("pcable", CABLE_D, POD_WALL + 4,
                          at=(POD_CUE_L / 2 - POD_WALL / 2, -2.0, 12.0), axis="X"))
    return clean(b)


def pod_cue_lid():
    return _pod_lid("pod_cue_lid", POD_CUE_L, POD_CUE_W, POD_CUE_COLS, POD_CUE_CLAMP)


def pod_bar():
    x, y, z = POD_BAR
    bar = oc.rounded_box("pod_bar", (x, y, z), 1.5, anchor="bottom")
    cb_d, cb_h = d.M3_BUTTON["head_cbore_d"], d.M3_BUTTON["head_cbore_depth"]
    for sy in (-1, 1):
        oc.cut(bar, oc.cylinder(f"pbh{sy}", CLEAR, z + 2, at=(0, sy * POD_CLAMP_Y, -1), anchor="bottom"))
        oc.cut(bar, oc.cone(f"pbc{sy}", cb_d, CLEAR, cb_h, at=(0, sy * POD_CLAMP_Y, 0.0)))
    return bar


def pod_battery_refs():
    px, py, pz = PACK["size"]
    refs = [
        oc.box("ref_pack", (px, py, pz),
               at=(PACK_AT[0], PACK_AT[1], POD_FLOOR + PACK_POCKET[2] + 0.05), anchor="bottom"),
    ]
    for i, (x, y) in enumerate(ELECTRODES_BAT):
        refs.append(oc.cylinder(f"ref_electrode_bat{i}", 7.0, 2.2, at=(x, y, -2.2), anchor="bottom"))
    return [oc.reference(r) for r in refs]


def pod_cue_refs():
    qb = d.QWIIC_BUZZER
    refs = [
        oc.box("ref_buzzer", (qb["board"][0], qb["board"][1], qb["board"][2] + qb["buzzer"]["size"][2]),
               at=(BUZZER_AT[0], BUZZER_AT[1], POD_FLOOR + 2.0), anchor="bottom"),
    ]
    for i, (x, y) in enumerate(ELECTRODES_CUE):
        refs.append(oc.cylinder(f"ref_electrode_cue{i}", 7.0, 2.2, at=(x, y, -2.2), anchor="bottom"))
    return [oc.reference(r) for r in refs]


# Back-compat names used by older scripts (battery pod geometry).
def pod_base():
    return pod_battery_base()


def pod_lid():
    return pod_battery_lid()


def pod_refs():
    return pod_battery_refs() + pod_cue_refs()


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
