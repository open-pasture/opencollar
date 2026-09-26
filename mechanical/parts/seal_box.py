"""Seal test box: proves a printed shell, O-ring and heat-set inserts keep
water out before we commit to the top unit.

A small box and lid with the same seal design the top unit will use: 2 mm
silicone O-ring cord in a face groove in the lid, closed by four M3 screws
into brass heat-set inserts, plus the M6 ePTFE vent. Test: close it with a
dry paper towel inside, hold it 1 m under water for 30 min (IP67), open it,
check the towel.

Print: box open side up; lid groove side up (the counterbores and vent
chamfer face the bed and bridge fine). ASA, 100 % infill within 3 mm of
the groove and the insert holes (or 6 perimeters), 0.2 mm layers.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import oc
from dims import INSERT_M3, M3, ORING_2MM, VENT_M6

OUTER = 76.0         # box footprint, square
CORNER_R = 8.0
CAVITY = 50.0        # inside, square
CAVITY_R = 3.0
HEIGHT = 30.0        # box, outside
FLOOR = 3.0
LID = 6.0            # leaves 2.8 under the screw heads; vent needs ≥ 4
SCREW_AT = 31.0      # screw centres at (±SCREW_AT, ±SCREW_AT)
LAND = 1.5           # flat seal face between cavity and groove

oc.reset()

# ---- box
box = oc.rounded_rect("box", (OUTER, OUTER, HEIGHT), CORNER_R, anchor="bottom")
cavity = oc.rounded_rect("cavity", (CAVITY, CAVITY, HEIGHT), CAVITY_R,
                         at=(0, 0, FLOOR), anchor="bottom")
oc.cut(box, cavity)
for sx in (-1, 1):
    for sy in (-1, 1):
        oc.cut(box, oc.cylinder("insert", INSERT_M3["hole_d"], INSERT_M3["hole_depth"] + 0.5,
                                at=(sx * SCREW_AT, sy * SCREW_AT, HEIGHT - INSERT_M3["hole_depth"]),
                                anchor="bottom"))

# ---- lid (modelled groove side up, as printed)
lid = oc.rounded_rect("lid", (OUTER, OUTER, LID), CORNER_R, at=(0, 0, 0), anchor="bottom")
g_in = CAVITY + 2 * LAND
g_out = g_in + 2 * ORING_2MM["groove_w"]
groove = oc.rounded_rect("groove", (g_out, g_out, ORING_2MM["groove_d"] + 0.5),
                         CAVITY_R + LAND + ORING_2MM["groove_w"],
                         at=(0, 0, LID - ORING_2MM["groove_d"]), anchor="bottom")
oc.cut(groove, oc.rounded_rect("groove_core", (g_in, g_in, 20), CAVITY_R + LAND))
oc.cut(lid, groove)
for sx in (-1, 1):
    for sy in (-1, 1):
        at = (sx * SCREW_AT, sy * SCREW_AT, 0)
        oc.cut(lid, oc.cylinder("clear", M3["clear_d"], 20, at=at))
        # Counterbore on the outside face (the bed side as printed).
        oc.cut(lid, oc.cylinder("cbore", M3["head_cbore_d"], M3["head_cbore_depth"] * 2, at=at))
oc.cut(lid, oc.cylinder("vent", VENT_M6["tap_drill_d"], 20, at=(0, 0, 0)))
# 45° chamfer on the outside face where the vent's O-ring seats.
d_out, d_in = VENT_M6["chamfer_d"] + 1.0, VENT_M6["tap_drill_d"] - 1.0
oc.cut(lid, oc.cone("vent_chamfer", d_out, d_in, (d_out - d_in) / 2, at=(0, 0, -0.5)))

# Cord length along the groove centreline (a rounded square).
side = g_in + ORING_2MM["groove_w"]
r_mid = CAVITY_R + LAND + ORING_2MM["groove_w"] / 2
cord_length = 4 * (side - 2 * r_mid) + 2 * math.pi * r_mid

# Show the lid beside the box for the renders.
oc.move(lid, dx=OUTER + 12)

oc.finish(
    "seal_box",
    {"seal_box_box": box, "seal_box_lid": lid},
    spec={
        "seal_box_box": {"size": (OUTER, OUTER, HEIGHT)},
        "seal_box_lid": {"size": (OUTER, OUTER, LID)},
    },
    material="ASA",
    min_wall=1.2,
    section_axis="Y",
    notes=f"O-ring cord along the groove centreline: {cord_length:.0f} mm "
          "(cut a little long, butt-join with superglue).",
)
