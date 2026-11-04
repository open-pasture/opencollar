"""EXPERIMENT — option B: integral R220 curved underside on a COPY of pod base.

Does NOT overwrite PR #28 production STLs under hardware/rook/d6/stl/.
Writes only under this experiment folder.

Idea: cut an R≈220 concave into the existing flat skirt bed so the pod
itself fills the ~5.4 mm flat-underside mid-gap — no separate saddle part.

Print orientations tested (report picks one):
  1) cavity UP, curve on bed      — REJECT (bed rule: nothing curved on bed)
  2) cavity DOWN, curve UP + bowl supports — candidate
  3) side-print (curve as wall)   — weak skin face / reject as default

Run:
  cd hardware/rook/d6/experiments/opt_b_integral_underside
  blender --background --factory-startup --python build_opt_b.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_D6 = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.abspath(os.path.join(_D6, "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _D6)

import oc  # noqa: E402

D6_STL = os.path.join(_D6, "stl")
OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

SADDLE_R = 220.0
POD_LEN = 97.0          # along Y
CUT_W = 50.0            # across X — inside skirt / channel bed
HALF = 0.5 * POD_LEN


def _sagitta(R, half):
    return float(R - math.sqrt(max(R * R - half * half, 0.0)))


def _import_stl(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    o = [x for x in bpy.data.objects if x not in before][0]
    o.name = name
    return o


def _bed_face_area(obj, z_tol=0.4, n_z_max=-0.85):
    """Approx first-layer area: faces near min-z with normal ≈ −Z."""
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


def _overhang_faces(obj, max_angle_from_h=45.0):
    """Count faces whose normal is more than max_angle below horizontal (need support)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    # Overhang if normal · −Z > cos(angle from vertical)... 
    # Bridge/overhang: face points downward more than `max_angle_from_h` past horizontal.
    # Horizontal normal.z=0; downward normal.z=-1. Angle from horizontal: asin(-nz).
    thresh = math.sin(math.radians(max_angle_from_h))  # nz < -thresh → overhang
    n = 0
    area = 0.0
    for f in bm.faces:
        if f.normal.z < -thresh:
            n += 1
            area += f.calc_area()
    bm.free()
    return n, float(area)


def cut_integral_r220(body, R=SADDLE_R, length=POD_LEN, width=CUT_W):
    """Recess R220 concave into the flat bed (z≈0) toward +Z (into the part).

    After cut: ends stay near z=0; centre recessed to +sagitta. When worn,
    concave faces the neck (assembly Rxπ same as today's saddle).
    """
    sag = _sagitta(R, 0.5 * length)
    # Cylinder axis X; centre below bed so upper surface is z=sag at y=0, z=0 at ends.
    cyl_z = -math.sqrt(max(R * R - (0.5 * length) ** 2, 0.0))
    cutter = oc.cylinder(
        "optb_r_cut",
        2.0 * R,
        width + 10.0,
        at=(0.0, 0.0, cyl_z),
        axis="X",
        segments=96,
        anchor="center",
    )
    # Only cut the underside band (do not eat the whole skirt)
    band = oc.box(
        "optb_cut_band",
        (width + 8.0, length + 4.0, sag + 2.0),
        at=(0.0, 0.0, -1.0),
        anchor="bottom",
    )
    oc.intersect(cutter, band)
    oc.cut(body, cutter)
    return sag


def service_lid_blank():
    """Placeholder service lid for bay opening through the curve (not production)."""
    cover = oc.rounded_rect(
        "optb_bay_cover",
        (28.0, 42.0, 2.5),
        2.0,
        at=(0.0, 0.0, 0.0),
        anchor="bottom",
        segments=8,
    )
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        oc.cut(
            cover,
            oc.cylinder(
                f"optb_bc_h{i}",
                3.4,
                4.0,
                at=(sx * 10.0, sy * 16.0, -0.5),
                anchor="bottom",
                segments=12,
            ),
        )
    oc.bake(cover)
    oc.move(cover, dz=-oc.bounds(cover)[0][2])
    return cover


def cut_bay_keepout_through_curve(body, sag):
    """Reserved module keep-out opening through the curved underside (PLACEHOLDER).

    Bay depth taken from the skirt/curve side — not a separate saddle.
    Service lid seats on the neck face of this opening.
    """
    # Module envelope placeholder 40×25×8 + margins → ~31×46×10
    bw, bl, bh = 31.0, 46.0, min(10.0, sag + 4.0)
    oc.cut(
        body,
        oc.rounded_rect(
            "optb_module_bay",
            (bw, bl, bh + 1.0),
            2.0,
            at=(0.0, 0.0, -0.5),
            anchor="bottom",
            segments=8,
        ),
    )
    # Gasket seat on neck face around opening (approximate)
    gw, gl = bw + 8.0, bl + 8.0
    g_z = sag - 1.2
    ring_o = oc.rounded_rect("optb_gask_o", (gw, gl, 1.2), 2.5, at=(0.0, 0.0, g_z), anchor="bottom")
    ring_i = oc.rounded_rect(
        "optb_gask_i", (gw - 4.0, gl - 4.0, 1.6), 2.0, at=(0.0, 0.0, g_z - 0.1), anchor="bottom"
    )
    oc.cut(body, oc.cut(ring_o, ring_i))
    return {"bay_w": bw, "bay_l": bl, "bay_h": bh}


def analyze_orientation(obj, label):
    area, z0 = _bed_face_area(obj)
    oh_n, oh_a = _overhang_faces(obj)
    size = [round(float(v), 2) for v in oc.size(obj)]
    return {
        "label": label,
        "size_mm": size,
        "bed_z0": round(z0, 3),
        "first_layer_area_mm2": round(area, 1),
        "overhang_faces": oh_n,
        "overhang_area_mm2": round(oh_a, 1),
    }


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src = os.path.join(D6_STL, "pod_L_base.stl")
    if not os.path.isfile(src):
        raise SystemExit(f"missing production STL copy source: {src}")

    report = {
        "experiment": "opt_B_integral_R220_underside",
        "warning": (
            "EXPERIMENT ONLY — does not replace PR #28 geometry. "
            "assembly_check is a geometry/interference check, NOT a fit or print test."
        ),
        "source_stl": src,
        "R_mm": SADDLE_R,
        "pass": True,
        "orientations": {},
        "bodies": {},
    }

    # --- Build cavity-UP (native) with curve cut into bed ---
    oc.reset()
    body = _import_stl(src, "pod_L_base_optB")
    # Ensure bed at z=0
    oc.move(body, dz=-oc.bounds(body)[0][2])
    sag = cut_integral_r220(body)
    bay = cut_bay_keepout_through_curve(body, sag)
    oc.bake(body)
    oc.move(body, dz=-oc.bounds(body)[0][2])

    # Orientation 1: as-built cavity UP — curve sits on bed (BAD)
    orient1 = analyze_orientation(body, "cavity_UP_curve_on_bed")
    orient1["verdict"] = "REJECT — curved face on bed (violates bed rule); rim-only first layer"
    orient1["supports"] = "none for curve-on-bed, but first layer is a thin rim — fails bed rule"
    report["orientations"]["1_cavity_UP"] = orient1

    path_native = os.path.join(OUT, "pod_L_base_optB_cavityUP.stl")
    oc.prepare_for_export(body, merge=1e-4)
    oc.export_stl(body, path_native)
    wt = oc.check_stl_watertight(path_native)
    report["bodies"]["pod_L_base_optB_cavityUP"] = {
        "path": path_native,
        "size_mm": list(oc.size(body)),
        "watertight": wt,
        "sagitta_mm": round(sag, 2),
        "bay_placeholder": bay,
    }
    if not wt.get("watertight"):
        report["pass"] = False

    # Orientation 2: flip 180° about X → cavity DOWN, curve UP (candidate)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    oc.reset()
    body2 = _import_stl(path_native, "pod_L_base_optB_flip")
    # Rotate 180 about X around bbox centre
    lo, hi = oc.bounds(body2)
    cx = 0.5 * (lo[0] + hi[0])
    cy = 0.5 * (lo[1] + hi[1])
    cz = 0.5 * (lo[2] + hi[2])
    R = __import__("mathutils").Matrix.Rotation(math.pi, 4, "X")
    T1 = __import__("mathutils").Matrix.Translation(Vector((-cx, -cy, -cz)))
    T2 = __import__("mathutils").Matrix.Translation(Vector((cx, cy, cz)))
    body2.matrix_world = T2 @ R @ T1 @ body2.matrix_world
    bpy.context.view_layer.update()
    # Apply and re-ground (STL import may share mesh data — make single-user)
    bpy.context.view_layer.objects.active = body2
    body2.select_set(True)
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # Recalc normals after 180° flip
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    oc.move(body2, dz=-oc.bounds(body2)[0][2])

    orient2 = analyze_orientation(body2, "cavity_DOWN_curve_UP")
    orient2["verdict"] = (
        "CANDIDATE — curve off the bed; bowl needs light supports; "
        "mating rim / cavity features face down (may need supports under lips)"
    )
    orient2["supports"] = (
        "light tree/bowl supports in the R220 concave; optional supports under "
        "cavity-down lips/columns; brim on the (now flat-ish) outer roof islands"
    )
    orient2["why"] = (
        "Bed rule kept (nothing curved on bed). First layer is the former outer "
        "roof / tip patches — smaller than today's cavity-up bed, so watch adhesion."
    )
    report["orientations"]["2_cavity_DOWN_curve_UP"] = orient2
    report["chosen_orientation"] = "2_cavity_DOWN_curve_UP"

    path_flip = os.path.join(OUT, "pod_L_base_optB_curveUP.stl")
    oc.prepare_for_export(body2, merge=1e-4)
    oc.export_stl(body2, path_flip)
    wt2 = oc.check_stl_watertight(path_flip)
    report["bodies"]["pod_L_base_optB_curveUP"] = {
        "path": path_flip,
        "size_mm": list(oc.size(body2)),
        "watertight": wt2,
        "print_orientation": "curve UP / cavity DOWN",
        "first_layer_area_mm2": orient2["first_layer_area_mm2"],
        "overhang_area_mm2": orient2["overhang_area_mm2"],
    }
    if not wt2.get("watertight"):
        report["pass"] = False

    # Orientation 3: side note (not exported as primary)
    report["orientations"]["3_side_print"] = {
        "label": "side_print_curve_as_wall",
        "verdict": "REJECT as default — skin/seal face = vertical layers; weaker, leakier",
        "supports": "minimal, but quality on neck face is poor",
    }

    # Service lid blank for this experiment
    oc.reset()
    lid = service_lid_blank()
    path_lid = os.path.join(OUT, "optb_bay_cover.stl")
    oc.prepare_for_export(lid, merge=1e-4)
    oc.export_stl(lid, path_lid)
    report["bodies"]["optb_bay_cover"] = {
        "path": path_lid,
        "size_mm": list(oc.size(lid)),
        "watertight": oc.check_stl_watertight(path_lid),
        "role": "service lid on neck face of integral bay opening",
    }

    # Standoff numbers for option B (integral curve, gap-fill only — no extra blank under ends)
    U2L = 31.0  # underside end-plane → lid-top (same stack as height clarification)

    def g_flat(R, y):
        half = HALF
        return math.sqrt(R * R - y * y) - math.sqrt(R * R - half * half)

    standoff = {}
    for R, lab in ((208.0, "75"), (218.0, "107"), (221.0, "130")):
        # B: ends still define the contact plane (rim at former bed); centre filled
        # neck→lid at ends ≈ U2L; at centre ≈ U2L + residual vs R220
        g220 = g_flat(220.0, 0.0)
        resid = abs(g_flat(R, 0.0) - g220)
        standoff[lab] = {
            "R": R,
            "centre_neck_to_lid_mm": round(U2L + resid, 2),
            "ends_neck_to_lid_mm": round(U2L, 2),
            "flat_a6b2118_centre": round(U2L + g_flat(R, 0.0), 2),
            "flat_a6b2118_ends": round(U2L, 2),
            "delta_centre_vs_flat": round((U2L + resid) - (U2L + g_flat(R, 0.0)), 2),
            "delta_ends_vs_flat": 0.0,
        }
    report["neck_standoff_opt_B"] = standoff
    report["sagitta_mm"] = round(sag, 2)

    # Geometry sanity (NOT a fit/print proof)
    report["geometry_sanity"] = {
        "note": (
            "Watertight + bounds only. If wired into assembly_check, that tool is a "
            "geometry/interference check — NOT a fit test and NOT a print test. "
            "Do not treat its pass count as proof of fit."
        ),
        "watertight_curveUP": bool(wt2.get("watertight")),
        "first_layer_area_curveUP_mm2": orient2["first_layer_area_mm2"],
        "overhang_area_curveUP_mm2": orient2["overhang_area_mm2"],
    }

    out_json = os.path.join(_HERE, "opt_b_report.json")
    with open(out_json, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({
        "sag": report["sagitta_mm"],
        "chosen": report["chosen_orientation"],
        "first_layer_mm2": orient2["first_layer_area_mm2"],
        "overhang_mm2": orient2["overhang_area_mm2"],
        "wt": wt2.get("watertight"),
        "standoff_75": standoff["75"],
    }, indent=2))
    print("PASS" if report["pass"] else "FAIL")
    return report


if __name__ == "__main__":
    main()
