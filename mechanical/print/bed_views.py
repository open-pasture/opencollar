"""Render every print-oriented part (print/stl/) sitting on a print bed, for
the print-lab hand-off sheet. Run orient.py first, then headless:

    blender -b --factory-startup --python print/bed_views.py
"""
import glob
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import oc

STL = os.path.join(HERE, "stl")
OUT = os.path.join(HERE, "bed_views")
BED = 6.0         # bed margin around the part, mm
BED_T = 1.5

os.makedirs(OUT, exist_ok=True)
for path in sorted(glob.glob(os.path.join(STL, "*.stl"))):
    name = os.path.splitext(os.path.basename(path))[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=path)
    part = bpy.context.selected_objects[0]
    (lo, hi) = oc.bounds(part)
    bed = oc.box("bed", (hi[0] - lo[0] + 2 * BED, hi[1] - lo[1] + 2 * BED, BED_T),
                 at=((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, -BED_T / 2))
    oc._setup_render(res=(900, 700))
    part.data.materials.append(oc._material("part", (0.86, 0.86, 0.84, 1)))
    bed.data.materials.append(oc._material("bed", (0.30, 0.32, 0.36, 1)))
    blo = [min(oc.bounds(o)[0][i] for o in (part, bed)) for i in range(3)]
    bhi = [max(oc.bounds(o)[1][i] for o in (part, bed)) for i in range(3)]
    oc._camera(blo, bhi, oc.VIEWS["iso"])
    bpy.context.scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)
