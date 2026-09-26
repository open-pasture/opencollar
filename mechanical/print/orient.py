"""Write every exported part in its print orientation (flat on z = 0,
centred) to print/stl/, for slicing. Run headless:

    blender -b --factory-startup --python print/orient.py
"""
import glob
import math
import os

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(HERE, "..", "exports")
OUT = os.path.join(HERE, "stl")

# Rotation (degrees about X) to reach print orientation; see PRINT-LIST.md.
ROTATE_X = {
    "bay_cradle": 90,            # on its side: the tunnel roof becomes a short bridge
    "bay_ballast_module": 180,   # top face down
}

os.makedirs(OUT, exist_ok=True)
for path in sorted(glob.glob(os.path.join(EXPORTS, "*", "*.stl"))):
    name = os.path.splitext(os.path.basename(path))[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    obj.data.transform(Matrix.Rotation(math.radians(ROTATE_X.get(name, 0)), 4, "X"))
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    obj.data.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))))
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, name + ".stl"), export_selected_objects=True)
    print("oriented", name, round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1), round(max(zs) - min(zs), 1))
