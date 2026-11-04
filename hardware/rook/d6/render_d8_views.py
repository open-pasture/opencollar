"""D8 review cams: assembled printable top + side, fit-coupon oblique.

D4 reference top: look −Z; screen-up = −X; screen-right = +Y (strap horizontal).
Side along strap: look +X; strap runs left–right in frame.

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python render_d8_views.py
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

import assembly as A  # noqa: E402
import numpy as np  # noqa: E402

STL = os.path.join(_HERE, "stl")
OUT = os.path.join(_HERE, "out", "d8_views")
REV = os.path.join(_HERE, "review")
ART = "/opt/cursor/artifacts"
for d in (OUT, REV, ART):
    os.makedirs(d, exist_ok=True)

CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
OAT = (0xC8 / 255, 0xBE / 255, 0xA8 / 255, 1.0)
SLATE = (0x5A / 255, 0x63 / 255, 0x6E / 255, 1.0)

PARTS = [
    ("cap_base", CHARCOAL),
    ("cap_lid", OAT),
    ("pod_L_base", CHARCOAL),
    ("pod_L_lid", OAT),
    ("pod_R_base", CHARCOAL),
    ("pod_R_lid", OAT),
    ("fairing_cap_pod_L", SLATE),
    ("fairing_cap_pod_R", SLATE),
    ("fairing_pod_strap_L", SLATE),
    ("fairing_pod_strap_R", SLATE),
]


def _mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgba[:3], 1.0)
    return m


def _import_stl(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    if not new:
        raise RuntimeError(f"STL import failed: {path}")
    obj = new[0]
    obj.name = name
    return obj


def _apply_pose(obj, M4):
    # Assign world matrix (mesh data.transform drops translation on some builds).
    M = Matrix([list(map(float, row)) for row in np.asarray(M4, dtype=float)])
    obj.matrix_world = M


def _setup(res=(1600, 1200)):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sh = sc.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_object_outline = True
    w = bpy.data.worlds.new("d8_world")
    w.color = (0.92, 0.91, 0.88)
    sc.world = w
    sc.view_settings.view_transform = "Standard"


def _bounds(objs):
    pts = []
    for o in objs:
        for v in o.bound_box:
            pts.append(o.matrix_world @ Vector(v))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def _render(objs, path, look, up, pad=1.12, d4_top=False):
    lo, hi = _bounds(objs)
    centre = (lo + hi) * 0.5
    extent = max((hi - lo).length, 1.0)
    cam_d = bpy.data.cameras.new("d8_cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = extent * pad
    cam_d.clip_start = 0.1
    cam_d.clip_end = 1e5
    cam = bpy.data.objects.new("d8_cam", cam_d)
    bpy.context.scene.collection.objects.link(cam)
    if d4_top:
        # D4 ref: screen-up −X, screen-right +Y, look −Z
        o = centre + Vector((0.0, 0.0, extent * 2.0))
        r, u, b = Vector((0, 1, 0)), Vector((-1, 0, 0)), Vector((0, 0, 1))
        cam.matrix_world = Matrix((
            (r.x, u.x, b.x, o.x),
            (r.y, u.y, b.y, o.y),
            (r.z, u.z, b.z, o.z),
            (0.0, 0.0, 0.0, 1.0),
        ))
        cam.location = o
    else:
        d = Vector(look).normalized()
        cam.location = centre + d * extent * 2.0
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        # Optional roll so preferred `up` matches camera +Y when not D4-top
        del up  # track_quat already biases world +Y
    bpy.context.view_layer.update()
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    try:
        bpy.data.cameras.remove(cam_d)
    except Exception:
        pass
    print("wrote", path, "extent", round(extent, 1))


def build_assembly():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _setup()
    poses = A.world_poses()
    objs = []
    for name, rgba in PARTS:
        path = os.path.join(STL, f"{name}.stl")
        if not os.path.isfile(path) or name not in poses:
            print("skip", name)
            continue
        obj = _import_stl(path, name)
        obj.data.materials.clear()
        obj.data.materials.append(_mat(name, rgba))
        _apply_pose(obj, poses[name])
        objs.append(obj)
    return objs


def render_coupon():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _setup()
    path = os.path.join(STL, "d8_fit_coupon.stl")
    obj = _import_stl(path, "d8_fit_coupon")
    obj.data.materials.clear()
    obj.data.materials.append(_mat("coupon", OAT))
    return [obj]


def _publish(src, name):
    for dest in (os.path.join(OUT, name), os.path.join(REV, name), os.path.join(ART, name)):
        shutil.copy2(src, dest)
        print("copied", dest)


def main():
    objs = build_assembly()
    top = os.path.join(OUT, "_tmp_top.png")
    side = os.path.join(OUT, "_tmp_side.png")
    # D4 ref top: look −Z; screen-up −X; screen-right +Y
    _render(objs, top, look=(0, 0, 1), up=Vector((-1, 0, 0)), pad=1.08, d4_top=True)
    # Side along strap: look −X (strap horizontal in frame)
    _render(objs, side, look=(1, 0, 0.0001), up=Vector((0, 0, 1)), pad=1.15)
    _publish(top, "d8_assembly_top.png")
    _publish(side, "d8_assembly_side.png")

    coup = render_coupon()
    obliq = os.path.join(OUT, "_tmp_coupon.png")
    _render(coup, obliq, look=(1.2, -1.4, 0.9), up=Vector((0, 0, 1)), pad=1.25)
    _publish(obliq, "d8_fit_coupon_oblique.png")
    print("DONE")


if __name__ == "__main__":
    main()
