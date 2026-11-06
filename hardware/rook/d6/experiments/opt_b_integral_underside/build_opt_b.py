"""EXPERIMENT → production-candidate Option B: integral R220 L + R pod bases.

Writes:
  experiments/.../stl/pod_{L,R}_base_optB_curveUP.stl
  experiments/.../stl/optb_bay_cover_{L,R}.stl
and promotes copies to hardware/rook/d6/stl/ (same names).

Does not delete Option A saddle STLs. Glyphs embossed after R mirror.

Run from this directory:
  blender --background --factory-startup --python build_opt_b.py
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_D6 = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.abspath(os.path.join(_D6, "..", "..", "common", "cad", "lib"))
_D5 = os.path.abspath(os.path.join(_D6, "..", "d5", "cad"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _D5)
sys.path.insert(0, _D6)

import oc  # noqa: E402
import build_d5 as d5  # noqa: E402

D6_STL = os.path.join(_D6, "stl")
OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

SADDLE_R = 220.0
POD_LEN = 97.0
CUT_W = 50.0


def _sagitta(R, half):
    return float(R - math.sqrt(max(R * R - half * half, 0.0)))


def _import_stl(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    o = [x for x in bpy.data.objects if x not in before][0]
    o.name = name
    return o


def _bed_face_area(obj, z_tol=0.4, n_z_max=-0.85):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    lo = min(v.co.z for v in bm.verts)
    area = 0.0
    for f in bm.faces:
        if f.normal.z > n_z_max:
            continue
        zc = sum(v.co.z for v in f.verts) / 3.0
        if abs(zc - lo) > z_tol:
            continue
        area += f.calc_area()
    bm.free()
    return float(area), float(lo)


def cut_integral_r220(body, R=SADDLE_R, length=POD_LEN, width=CUT_W):
    sag = _sagitta(R, 0.5 * length)
    cyl_z = -math.sqrt(max(R * R - (0.5 * length) ** 2, 0.0))
    cutter = oc.cylinder(
        "optb_r_cut", 2.0 * R, width + 10.0,
        at=(0.0, 0.0, cyl_z), axis="X", segments=96, anchor="center",
    )
    band = oc.box(
        "optb_cut_band", (width + 8.0, length + 4.0, sag + 2.0),
        at=(0.0, 0.0, -1.0), anchor="bottom",
    )
    oc.intersect(cutter, band)
    oc.cut(body, cutter)
    return sag


def cut_bay_keepout(body, sag):
    bw, bl, bh = 31.0, 46.0, min(10.0, sag + 4.0)
    oc.cut(
        body,
        oc.rounded_rect(
            "optb_module_bay", (bw, bl, bh + 1.0), 2.0,
            at=(0.0, 0.0, -0.5), anchor="bottom", segments=8,
        ),
    )
    gw, gl = bw + 8.0, bl + 8.0
    g_z = sag - 1.2
    ring_o = oc.rounded_rect("optb_gask_o", (gw, gl, 1.2), 2.5, at=(0, 0, g_z), anchor="bottom")
    ring_i = oc.rounded_rect(
        "optb_gask_i", (gw - 4.0, gl - 4.0, 1.6), 2.0, at=(0, 0, g_z - 0.1), anchor="bottom"
    )
    oc.cut(body, oc.cut(ring_o, ring_i))
    return {"bay_w": bw, "bay_l": bl, "bay_h": bh}


def service_lid(side: str):
    cover = oc.rounded_rect(
        f"optb_bay_cover_{side}", (28.0, 42.0, 2.5), 2.0,
        at=(0, 0, 0), anchor="bottom", segments=8,
    )
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        oc.cut(
            cover,
            oc.cylinder(f"h{i}", 3.4, 4.0, at=(sx * 10.0, sy * 16.0, -0.5),
                        anchor="bottom", segments=12),
        )
    try:
        d5.emboss_glyph(cover, "NO SHOCK", (0.0, 4.0, 2.5), size=3.5, depth=0.55)
        d5.emboss_glyph(cover, side, (0.0, -5.0, 2.5), size=5.0, depth=0.55)
    except Exception:
        pass
    oc.bake(cover)
    oc.move(cover, dz=-oc.bounds(cover)[0][2])
    return cover


def flip_curve_up(obj):
    lo, hi = oc.bounds(obj)
    cx = 0.5 * (lo[0] + hi[0])
    cy = 0.5 * (lo[1] + hi[1])
    cz = 0.5 * (lo[2] + hi[2])
    R = Matrix.Rotation(math.pi, 4, "X")
    T1 = Matrix.Translation(Vector((-cx, -cy, -cz)))
    T2 = Matrix.Translation(Vector((cx, cy, cz)))
    obj.matrix_world = T2 @ R @ T1 @ obj.matrix_world
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    oc.move(obj, dz=-oc.bounds(obj)[0][2])


def build_side(side: str, report: dict):
    src = os.path.join(D6_STL, f"pod_{side}_base.stl")
    if not os.path.isfile(src):
        # Fall back to L and X-mirror for geometry seed only; glyphs added later
        src = os.path.join(D6_STL, "pod_L_base.stl")
    oc.reset()
    body = _import_stl(src, f"pod_{side}_base_optB")
    oc.move(body, dz=-oc.bounds(body)[0][2])
    if side == "R" and "pod_R_base" not in src:
        # Seed from L: X-mirror geometry (glyphs not yet present on seed path)
        bpy.context.view_layer.objects.active = body
        body.select_set(True)
        bpy.ops.object.make_single_user(object=True, obdata=True)
        body.scale.x = -1.0
        bpy.ops.object.transform_apply(scale=True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        oc.move(body, dz=-oc.bounds(body)[0][2])

    sag = cut_integral_r220(body)
    bay = cut_bay_keepout(body, sag)
    oc.bake(body)
    oc.move(body, dz=-oc.bounds(body)[0][2])

    # Emboss side letter on cavity floor BEFORE flip (will be inverted in Z — re-emboss after)
    path_native = os.path.join(OUT, f"pod_{side}_base_optB_cavityUP.stl")
    oc.prepare_for_export(body, merge=1e-4)
    oc.export_stl(body, path_native)

    # Curve-UP orientation
    bpy.ops.wm.read_factory_settings(use_empty=True)
    oc.reset()
    body2 = _import_stl(path_native, f"pod_{side}_optB_flip")
    flip_curve_up(body2)
    # Glyphs after flip so text is readable on the print bed / outer
    try:
        z_top = oc.bounds(body2)[1][2]
        d5.emboss_glyph(body2, side, (0.0, -30.0, z_top), size=8.0, depth=0.7)
        d5.emboss_glyph(body2, "ARROW", (0.0, 30.0, z_top), size=6.0, depth=0.7)
    except Exception:
        pass
    oc.bake(body2)
    oc.move(body2, dz=-oc.bounds(body2)[0][2])

    path_flip = os.path.join(OUT, f"pod_{side}_base_optB_curveUP.stl")
    oc.prepare_for_export(body2, merge=1e-4)
    oc.export_stl(body2, path_flip)
    wt = oc.check_stl_watertight(path_flip)
    area, _ = _bed_face_area(body2)
    size = [round(float(v), 2) for v in oc.size(body2)]
    # Promote to production-candidate stl/
    promo = os.path.join(D6_STL, f"pod_{side}_base_optB_curveUP.stl")
    shutil.copy2(path_flip, promo)

    report["bodies"][f"pod_{side}_base_optB_curveUP"] = {
        "path": promo,
        "experiment_path": path_flip,
        "size_mm": size,
        "watertight": wt,
        "first_layer_area_mm2": round(area, 1),
        "sagitta_mm": round(sag, 2),
        "bay": bay,
        "print": "curve UP / cavity DOWN; brim recommended",
    }

    # Service lid
    oc.reset()
    lid = service_lid(side)
    lid_path = os.path.join(OUT, f"optb_bay_cover_{side}.stl")
    oc.prepare_for_export(lid, merge=1e-4)
    oc.export_stl(lid, lid_path)
    promo_lid = os.path.join(D6_STL, f"optb_bay_cover_{side}.stl")
    shutil.copy2(lid_path, promo_lid)
    report["bodies"][f"optb_bay_cover_{side}"] = {
        "path": promo_lid,
        "size_mm": list(oc.size(lid)),
        "watertight": oc.check_stl_watertight(lid_path),
    }
    return wt.get("watertight", False)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {
        "experiment": "opt_B_integral_R220_L_and_R",
        "warning": (
            "Production-candidate STLs under stl/ — still DRAFT / unprinted until Cody "
            "approves. assembly_check is geometry/interference only, not fit/print proof. "
            "R220 / 25×42 cm ellipse is a sizing model, not measured cattle."
        ),
        "chosen_orientation": "curve_UP_cavity_DOWN",
        "bodies": {},
        "pass": True,
    }
    for side in ("L", "R"):
        ok = build_side(side, report)
        if not ok:
            report["pass"] = False

    # Symmetry metrics
    import trimesh
    L = trimesh.load(os.path.join(D6_STL, "pod_L_base_optB_curveUP.stl"), force="mesh")
    R = trimesh.load(os.path.join(D6_STL, "pod_R_base_optB_curveUP.stl"), force="mesh")
    report["symmetry"] = {
        "L_extents_mm": [round(float(v), 2) for v in L.extents],
        "R_extents_mm": [round(float(v), 2) for v in R.extents],
        "L_volume_cm3": round(float(L.volume) / 1000.0, 2),
        "R_volume_cm3": round(float(R.volume) / 1000.0, 2),
        "extent_delta_mm": [round(float(a - b), 2) for a, b in zip(L.extents, R.extents)],
        "volume_delta_cm3": round(abs(float(L.volume) - float(R.volume)) / 1000.0, 3),
    }
    with open(os.path.join(_HERE, "opt_b_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    # Also copy cover alias
    shutil.copy2(
        os.path.join(D6_STL, "optb_bay_cover_L.stl"),
        os.path.join(D6_STL, "optb_bay_cover.stl"),
    )
    print(json.dumps(report["symmetry"], indent=2))
    print("PASS" if report["pass"] else "FAIL")
    return report


if __name__ == "__main__":
    main()
