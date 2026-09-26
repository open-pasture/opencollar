"""Bay: the cradle on the bottom of the strap and the ballast module.

The strap threads through the cradle's tunnel; the bay hangs at the lowest
point of the collar and its mass keeps the top unit upright. The module
fastens to the cradle with 2 × M3 × 20 knurled thumbscrews into heat-set
inserts. The ballast module holds a 64 × 46 × 16 mild steel slab (~370 g),
captured between the module and the cradle.

Print (ASA, 6 perimeters, 40 % infill):
  cradle  on its side (a long edge down) so the tunnel roof is a short bridge
  module  top face down
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import collar as c
import oc
from dims import STEEL_SLAB

oc.reset()
cradle = c.bay_cradle()
module = c.ballast_module()
slab = c.steel_slab()

sx, sy, sz = STEEL_SLAB["size"]
slab_g = sx * sy * sz / 1000 * STEEL_SLAB["density"]

oc.finish(
    "bay",
    {"bay_cradle": cradle, "bay_ballast_module": module},
    spec={
        "bay_cradle": {"size": (c.BAY[0], c.BAY[1], c.CRADLE_T)},
        "bay_ballast_module": {"size": (c.BAY[0], c.BAY[1], c.MODULE_H)},
    },
    refs=[slab],
    material="ASA",
    min_wall=1.2,
    section_axis="Y",
    notes=f"Steel slab {sx:.0f} × {sy:.0f} × {sz:.0f} mm ≈ {slab_g:.0f} g. "
          "2 × M3 × 20 knurled thumbscrews, 2 × M3 × 4 inserts.",
)
