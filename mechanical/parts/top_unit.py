"""Top unit: sealed base and roof lid, plus the two strap clamp bars.

Everything electronic lives here. The GNSS patch sits under the crown with
nothing over it; a solar panel is bonded into the recess on each roof face.
The base walls are solid 13 mm bands carrying the O-ring groove, and the lid
is held by 10 × M3 × 16 screws from underneath, so no panel ever covers a
screw. The strap runs in a channel across the arched underside and is
clamped at each end by a bar and 2 × M3 button-head screws.

Print (ASA, 6 perimeters, 40 % infill):
  base   underside down, with tree supports under the arch; rim up
  lid    rim down, tree supports inside the roof
  bars   flat
PA12 (MJF/SLS) needs no supports.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import collar as c
import oc

oc.reset()
base = c.top_base()
lid = c.top_lid()
oc.move(lid, dz=c.BASE_H)
bar = c.clamp_bar()
oc.move(bar, dx=c.W / 2 + 25)

refs = c.top_refs() + c.panels()

oc.finish(
    "top_unit",
    {"top_unit_base": base, "top_unit_lid": lid, "top_unit_clamp_bar": bar},
    spec={
        "top_unit_base": {"size": (c.W, c.D, c.BASE_H)},
        "top_unit_lid": {"size": (c.W, c.D, c.CROWN_H)},
        "top_unit_clamp_bar": {"size": c.BAR},
    },
    refs=refs,
    material="ASA",
    min_wall=1.2,
    section_axis="Y",
    notes="Print 2 clamp bars. Screws: 10 × M3 × 16 socket head (lid), "
          "4 × M3 × 8 button head (bars); 14 × M3 × 4 heat-set inserts.",
)
