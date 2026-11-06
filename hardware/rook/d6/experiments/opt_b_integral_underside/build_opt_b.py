"""Option B: integral R220 L+R pod bases + bay covers.

Pipeline (manifold-preserving):
  1. Seed standard pod_*_base.stl
  2. Cut R220 + bay pocket + bay mating (cavityUP)
  3. Voxel remesh → watertight
  4. Flip curveUP; remesh → watertight
  5. Re-add bed tongue + bay tongue/bosses/shock
  6. Fine remesh (0.18–0.28) → watertight volume for Boolean gates

Run:
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
import mating_rabbet as MR  # noqa: E402

D6_STL = os.path.join(_D6, "stl")
OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

SADDLE_R = 220.0
POD_LEN = 97.0
CUT_W = 50.0
COVER_W, COVER_L, COVER_R = 28.0, 42.0, 2.0
COVER_H = 2.5
LAND_FLOOR_T = 6.0
INNER_W, INNER_L = 18.0, 28.0
OPTB_COVER_COLS = [(-10.0, 14.0), (8.0, 14.0), (-7.0, -14.0), (10.0, -12.0)]
SHOCK_BORE_D = 8.05
SHOCK_BOSS_D = 14.0
SHOCK_FLANGE_SEAT_D = 12.40
INSERT_D = 4.0
INSERT_DEPTH = 5.6
POD_LID_W, POD_LID_L, POD_LID_R = 62.0, 91.0, 3.0


def _sagitta(R, half):
    return float(R - math.sqrt(max(R * R - half * half, 0.0)))


def _import_stl(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    o = [x for x in bpy.data.objects if x not in before][0]
    o.name = name
    return o


def _prepare(obj, merge=0.02):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge)
    bmesh.ops.dissolve_degenerate(bm, dist=merge, edges=list(bm.edges))
    boundary = [e for e in bm.edges if len(e.link_faces) < 2]
    if boundary:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=8)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def _remesh(obj, voxel=0.32):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    vox = obj.modifiers.new("optb_vox", "REMESH")
    vox.mode = "VOXEL"
    vox.voxel_size = voxel
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    return _prepare(obj, merge=max(0.015, voxel * 0.5))


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


def cut_bay_pocket(body, sag):
    land_z = float(max(sag, LAND_FLOOR_T + 1.0))
    rebate_w, rebate_l = COVER_W + 1.0, COVER_L + 1.0
    oc.cut(
        body,
        oc.rounded_rect(
            "optb_cover_rebate", (rebate_w, rebate_l, land_z + 0.5), 2.2,
            at=(0.0, 0.0, -0.5), anchor="bottom", segments=8,
        ),
    )
    floor = oc.rounded_rect(
        "optb_land_floor", (rebate_w - 0.2, rebate_l - 0.2, LAND_FLOOR_T), 2.0,
        at=(0.0, 0.0, land_z), anchor="bottom", segments=8,
    )
    oc.union(body, floor)
    oc.cut(
        body,
        oc.rounded_rect(
            "optb_inner_keep", (INNER_W, INNER_L, land_z + LAND_FLOOR_T + 2.0), 2.0,
            at=(0.0, 0.0, -0.5), anchor="bottom", segments=8,
        ),
    )
    return land_z, rebate_w, rebate_l


def apply_bay_mating_cavityUP(body, land_z):
    tw_o = COVER_W - 2 * MR.TONGUE_IN0
    tl_o = COVER_L - 2 * MR.TONGUE_IN0
    tw_i = COVER_W - 2 * MR.TONGUE_IN1
    tl_i = COVER_L - 2 * MR.TONGUE_IN1
    oc.union(body, MR.stadium_ring(
        "optb_bay_tongue", tw_o, tl_o, COVER_R - MR.TONGUE_IN0,
        tw_i, tl_i, COVER_R - MR.TONGUE_IN1,
        h=MR.TONGUE_H + 0.05, z0=land_z - MR.TONGUE_H,
    ))
    oc.union(body, oc.cylinder(
        "shock_boss", SHOCK_BOSS_D, LAND_FLOOR_T,
        at=(0.0, 0.0, land_z), anchor="bottom", segments=32,
    ))
    oc.cut(body, oc.cylinder(
        "shock_bore", SHOCK_BORE_D, LAND_FLOOR_T + 2.0,
        at=(0.0, 0.0, land_z - 0.5), anchor="bottom", segments=32,
    ))
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        oc.cut(body, oc.cylinder(
            f"optb_spot{i}", MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.25,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))
        oc.cut(body, oc.cylinder(
            f"optb_ins{i}", INSERT_D, INSERT_DEPTH + 0.2,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))


def apply_curveUP_mating(body, side: str, land_z: float):
    y0 = -2.5 if side == "L" else 2.5
    cols = (
        [(-22.0, 36.0), (22.0, 36.0), (-19.0, -36.0), (22.0, -36.0)]
        if side == "L"
        else [(22.0, -36.0), (-22.0, -36.0), (19.0, 36.0), (-22.0, 36.0)]
    )
    MR.add_base_tongue(
        body, POD_LID_W, POD_LID_L, POD_LID_R, 0.0,
        at_xy=(0.0, y0), prefix=f"optb_bed_tongue_{side}",
    )
    for i, (x, y) in enumerate(cols):
        oc.cut(body, oc.cylinder(
            f"bed_spot{i}", MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.35,
            at=(x, y, -0.05), anchor="bottom", segments=24,
        ))
        oc.cut(body, oc.cylinder(
            f"bed_ins{i}", INSERT_D, INSERT_DEPTH,
            at=(x, y, -0.05), anchor="bottom", segments=24,
        ))
    tw_o = COVER_W - 2 * MR.TONGUE_IN0
    tl_o = COVER_L - 2 * MR.TONGUE_IN0
    tw_i = COVER_W - 2 * MR.TONGUE_IN1
    tl_i = COVER_L - 2 * MR.TONGUE_IN1
    oc.union(body, MR.stadium_ring(
        "optb_bay_tongue_up", tw_o, tl_o, COVER_R - MR.TONGUE_IN0,
        tw_i, tl_i, COVER_R - MR.TONGUE_IN1,
        h=MR.TONGUE_H + 0.05, z0=land_z,
    ))
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        oc.cut(body, oc.cylinder(
            f"top_spot{i}", MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.25,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))
        oc.cut(body, oc.cylinder(
            f"top_ins{i}", INSERT_D, INSERT_DEPTH,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))
    oc.cut(body, oc.cylinder(
        "top_shock", SHOCK_BORE_D, INSERT_DEPTH + 1.0,
        at=(0, 0, land_z - 0.05), anchor="bottom", segments=32,
    ))
    oc.cut(body, oc.cylinder(
        "top_shock_spot", SHOCK_FLANGE_SEAT_D, MR.BOSS_RECESS + 0.15,
        at=(0, 0, land_z - 0.05), anchor="bottom", segments=32,
    ))


def service_lid(side: str):
    cover = oc.rounded_rect(
        f"optb_bay_cover_{side}", (COVER_W, COVER_L, COVER_H), COVER_R,
        at=(0, 0, 0), anchor="bottom", segments=16,
    )
    MR.cut_lid_groove(cover, COVER_W, COVER_L, COVER_R, prefix=f"optb_cov_groove_{side}")
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        oc.cut(cover, oc.cylinder(
            f"h{i}", 3.4, COVER_H + 2.0, at=(x, y, -0.5), anchor="bottom", segments=16,
        ))
        oc.cut(cover, oc.cylinder(
            f"cb{i}", 6.2, 1.35, at=(x, y, COVER_H - 1.20), anchor="bottom", segments=16,
        ))
    oc.cut(cover, oc.cylinder(
        "plug_bore", SHOCK_BORE_D, COVER_H + 2.0, at=(0, 0, -0.5), anchor="bottom", segments=32,
    ))
    oc.cut(cover, oc.cylinder(
        "plug_flange_seat", SHOCK_FLANGE_SEAT_D, 0.55,
        at=(0, 0, COVER_H - 0.50), anchor="bottom", segments=32,
    ))
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


def _measure_land_z(path):
    import trimesh
    import numpy as np
    m = trimesh.load(path, force="mesh")
    angs = np.linspace(0, 2 * math.pi, 16, endpoint=False)
    tops = []
    for a in angs:
        x, y = 11.0 * math.cos(a), 11.0 * math.sin(a)
        lo, hi = float(m.bounds[0, 2]), float(m.bounds[1, 2])
        found = None
        for _ in range(22):
            mid = 0.5 * (lo + hi)
            if bool(m.contains([[x, y, mid]])[0]):
                lo = mid
                found = mid
            else:
                hi = mid
        if found is not None:
            tops.append(found)
    return float(np.median(tops)) if tops else float(m.bounds[1, 2]) - 2.0


def build_side(side: str, report: dict):
    src = os.path.join(D6_STL, f"pod_{side}_base.stl")
    oc.reset()
    body = _import_stl(src, f"pod_{side}_base_optB")
    oc.move(body, dz=-oc.bounds(body)[0][2])
    h_before = float(oc.bounds(body)[1][2])

    sag = cut_integral_r220(body)
    land_cav, rebate_w, rebate_l = cut_bay_pocket(body, sag)
    apply_bay_mating_cavityUP(body, land_cav)
    oc.bake(body)
    body = _remesh(body, voxel=0.32)
    oc.move(body, dz=-oc.bounds(body)[0][2])
    h_cavity = float(oc.bounds(body)[1][2])

    path_native = os.path.join(OUT, f"pod_{side}_base_optB_cavityUP.stl")
    oc.prepare_for_export(body, merge=1e-4)
    oc.export_stl(body, path_native)
    print(f"  {side} cavityUP wt={oc.check_stl_watertight(path_native).get('watertight')}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    oc.reset()
    body2 = _import_stl(path_native, f"pod_{side}_optB_flip")
    flip_curve_up(body2)
    body2 = _remesh(body2, voxel=0.32)
    oc.move(body2, dz=-oc.bounds(body2)[0][2])
    h_flip = float(oc.bounds(body2)[1][2])
    land_nom = float(max(h_flip - land_cav, MR.TONGUE_H + LAND_FLOOR_T))

    try:
        d5.emboss_glyph(body2, side, (0.0, -30.0, 0.7), size=8.0, depth=0.7)
        d5.emboss_glyph(body2, "ARROW", (0.0, 30.0, 0.7), size=6.0, depth=0.7)
        oc.bake(body2)
    except Exception as exc:
        print(f"  optB {side} glyph: {exc}")

    apply_curveUP_mating(body2, side, land_nom)
    _prepare(body2, merge=0.015)
    oc.move(body2, dz=-oc.bounds(body2)[0][2])

    # Fine remesh closes boolean seams from mating unions/cuts. Do NOT re-cut
    # after this remesh (that re-opens the mesh). Features survive ≤0.22 mm.
    wt = {"watertight": False}
    path_flip = os.path.join(OUT, f"pod_{side}_base_optB_curveUP.stl")
    for vx in (0.18, 0.22, 0.28, 0.35):
        body2 = _remesh(body2, voxel=vx)
        oc.move(body2, dz=-oc.bounds(body2)[0][2])
        oc.prepare_for_export(body2, merge=1e-4)
        oc.export_stl(body2, path_flip)
        wt = oc.check_stl_watertight(path_flip)
        print(f"  {side} fine@{vx} wt={wt.get('watertight')} bad={wt.get('bad_edges')}")
        if wt.get("watertight"):
            break

    h_final = float(oc.bounds(body2)[1][2])
    cover_seat_z = _measure_land_z(path_flip)
    area, _ = _bed_face_area(body2)
    promo = os.path.join(D6_STL, f"pod_{side}_base_optB_curveUP.stl")
    shutil.copy2(path_flip, promo)

    bay = {
        "bay_w": rebate_w, "bay_l": rebate_l,
        "land_floor_t": LAND_FLOOR_T,
        "shock_bore_d": SHOCK_BORE_D,
        "cover_cols": [list(c) for c in OPTB_COVER_COLS],
        "cover_seat_z_curveUP": cover_seat_z,
        "body_h_curveUP": h_final,
        "h_cavityUP": h_cavity,
        "h_before": h_before,
        "land_cav": land_cav,
    }
    report["bodies"][f"pod_{side}_base_optB_curveUP"] = {
        "path": promo,
        "size_mm": [round(float(v), 2) for v in oc.size(body2)],
        "watertight": wt,
        "first_layer_area_mm2": round(area, 1),
        "sagitta_mm": round(sag, 2),
        "bay": bay,
    }

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
        "cols": [list(c) for c in OPTB_COVER_COLS],
        "cover_h": COVER_H,
    }
    return bool(wt.get("watertight"))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {
        "experiment": "opt_B_integral_R220_L_and_R",
        "warning": "DRAFT — assembly_check is geometry only, not fit/print proof.",
        "chosen_orientation": "curve_UP_cavity_DOWN",
        "bodies": {},
        "pass": True,
    }
    for side in ("L", "R"):
        if not build_side(side, report):
            report["pass"] = False
    seats = {}
    for side in ("L", "R"):
        bay = report["bodies"][f"pod_{side}_base_optB_curveUP"]["bay"]
        cover_meta = report["bodies"][f"optb_bay_cover_{side}"]
        seats[side] = {
            "cover_seat_z": bay["cover_seat_z_curveUP"],
            "body_h": bay["body_h_curveUP"],
            "cols": bay["cover_cols"],
            "cover_h_print": cover_meta["size_mm"][2],
            "cover_mating_from_bed": 0.0,
            "cover_h": COVER_H,
            "cover_flange_seat_from_outer": 0.50,
            "plug_flange_underside_z": 5.5,
        }
    report["optb_seats"] = seats
    with open(os.path.join(_HERE, "opt_b_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    with open(os.path.join(D6_STL, "optb_seats.json"), "w") as f:
        json.dump(seats, f, indent=2)
    shutil.copy2(
        os.path.join(D6_STL, "optb_bay_cover_L.stl"),
        os.path.join(D6_STL, "optb_bay_cover.stl"),
    )
    print(json.dumps(seats, indent=2))
    print("PASS" if report["pass"] else "FAIL")
    return report


if __name__ == "__main__":
    main()
