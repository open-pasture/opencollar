"""Render D8 saddle + bay: iso and section. Saves under review/ + artifacts.

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python render_saddle_bay.py
"""
from __future__ import annotations

import os
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib")))
sys.path.insert(0, _HERE)

import oc  # noqa: E402

STL = os.path.join(_HERE, "stl")
REV = os.path.join(_HERE, "review")
ART = "/opt/cursor/artifacts"
os.makedirs(REV, exist_ok=True)
os.makedirs(ART, exist_ok=True)

CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
OAT = (0xC8 / 255, 0xBE / 255, 0xA8 / 255, 1.0)


def _mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgba[:3], 1.0)
    return m


def _import(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    o = [x for x in bpy.data.objects if x not in before][0]
    o.name = name
    return o


def _setup():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = "BOTH"
    w = bpy.data.worlds.new("w")
    w.color = (0.92, 0.91, 0.88)
    sc.world = w


def _bounds(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _render(objs, path, look, pad=1.2):
    lo, hi = _bounds(objs)
    ctr = (lo + hi) * 0.5
    ext = max((hi - lo).length, 1.0)
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = ext * pad
    cam_d.clip_end = 1e5
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.scene.collection.objects.link(cam)
    d = Vector(look).normalized()
    cam.location = ctr + d * ext * 2.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("wrote", path)


def _section_yz(obj):
    """Keep +X half for a YZ section through the bay centre."""
    lo, hi = oc.bounds(obj)
    cutter = oc.box(
        "sec",
        (hi[0] - lo[0] + 4.0, hi[1] - lo[1] + 4.0, hi[2] - lo[2] + 4.0),
        at=(lo[0] - 2.0, 0.5 * (lo[1] + hi[1]), 0.5 * (lo[2] + hi[2])),
        anchor="center",
    )
    # shift cutter so it removes −X half
    oc.move(cutter, dx=-(hi[0] - lo[0]) * 0.5 - 1.0)
    oc.cut(obj, cutter)
    return obj


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _setup()
    sad = _import(os.path.join(STL, "pod_L_saddle.stl"), "saddle")
    cov = _import(os.path.join(STL, "pod_L_bay_cover.stl"), "cover")
    sad.data.materials.append(_mat("sad", CHARCOAL))
    cov.data.materials.append(_mat("cov", OAT))
    # Cover above saddle neck face for iso readability
    oc.move(cov, dz=list(oc.size(sad))[2] + 4.0)

    iso = os.path.join(REV, "d8_saddle_bay_iso.png")
    _render([sad, cov], iso, (1.3, -1.4, 0.9), pad=1.25)
    shutil.copy2(iso, os.path.join(ART, "d8_saddle_bay_iso.png"))

    # Section: cut −X half, look along +X at the bay/electrode cut face
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _setup()
    sad2 = _import(os.path.join(STL, "pod_L_saddle.stl"), "saddle_sec")
    sad2.data.materials.append(_mat("sad2", CHARCOAL))
    _section_yz(sad2)
    sec = os.path.join(REV, "d8_saddle_bay_section.png")
    _render([sad2], sec, (1.0, 0.05, 0.02), pad=1.15)
    shutil.copy2(sec, os.path.join(ART, "d8_saddle_bay_section.png"))
    print("DONE")


if __name__ == "__main__":
    main()
