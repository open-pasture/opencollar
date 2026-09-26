"""Fit test coupon: tunes every tolerance-critical feature to the printer
before we print a shell.

One plate with a row of each feature at a few sizes around the nominal. Print
it, try the real part in each, and pick the size that fits. The winning
values go into lib/dims.py and every part picks them up.

  Row A  M3 heat-set insert holes (press an insert into each with the iron)
  Row B  M3 screw clearance holes (a screw should drop through, not rattle)
  Row C  2 mm O-ring cord grooves (cord should press in and sit proud by
         about 0.4–0.5 mm, the squeeze that seals)
  Row D  M6 vent tap-drill holes (tap M6 × 0.75 and screw the vent in)

Sizes are engraved beside each feature. Print flat, top face up, ASA, 0.2 mm
layers, 6 perimeters.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import oc
from dims import INSERT_M3, M3, ORING_2MM, VENT_M6

T = 8.0            # plate thickness: deeper than the insert hole
PITCH = 16.0       # spacing between features in a row
ROW = 20.0         # spacing between rows
LABEL = 3.6        # label text height
ENGRAVE = 0.6
OVER = 0.5         # cutting tools poke above the top face so booleans stay clean

rows = [
    ("A", "hole", [INSERT_M3["hole_d"] + d for d in (-0.2, 0.0, 0.2, 0.4)], INSERT_M3["hole_depth"]),
    ("B", "hole", [M3["clear_d"] + d for d in (-0.2, 0.0, 0.2, 0.4)], None),
    ("C", "groove", [ORING_2MM["groove_w"] + d for d in (-0.2, 0.0, 0.2, 0.4)], ORING_2MM["groove_d"]),
    ("D", "hole", [VENT_M6["tap_drill_d"] + d for d in (-0.1, 0.0, 0.1, 0.2)], None),
]

W = PITCH * 4 + 14
H = ROW * len(rows) + 6

oc.reset()
plate = oc.rounded_rect("plate", (W, H, T), 3.0, anchor="bottom")

tools, labels = [], []
for r, (letter, kind, sizes, depth) in enumerate(rows):
    y = H / 2 - 3 - ROW * r - ROW / 2 + 3.5
    labels.append(oc.text(f"row{letter}", letter, LABEL + 1, ENGRAVE + OVER,
                         at=(-W / 2 + 5, y, T - ENGRAVE)))
    for i, s in enumerate(sizes):
        x = -W / 2 + 12 + PITCH * i + PITCH / 2
        if kind == "hole":
            d = depth if depth else T + OVER  # no depth: through hole
            tools.append(oc.cylinder(f"{letter}{i}", s, d + OVER,
                                     at=(x, y, T - d), anchor="bottom"))
        else:
            # A short straight groove; press a length of cord into it.
            tools.append(oc.box(f"{letter}{i}", (s, 9.0, depth + OVER),
                                at=(x, y, T - depth), anchor="bottom"))
        labels.append(oc.text(f"{letter}{i}_label", f"{s:.1f}", LABEL, ENGRAVE + OVER,
                             at=(x, y - 7.5, T - ENGRAVE)))
# Features first, then the labels, so a font glitch can never eat a feature.
oc.cut(plate, *tools)
oc.cut(plate, *labels)

oc.finish(
    "fit_test",
    {"fit_test": plate},
    spec={"fit_test": {"size": (W, H, T)}},
    material="ASA",
    min_wall=1.2,
    # Engraved size labels: glyph corners (6, 9, 3) leave knife-edge wedges
    # (~62 mm²). Without labels the thinnest wall is 2.0 mm, under row A.
    thin_area_allowed=80.0,
    section_axis="X",
)
