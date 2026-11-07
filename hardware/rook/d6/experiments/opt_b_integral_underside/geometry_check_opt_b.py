"""Geometry sanity for opt-B experiment STLs.

This is a *geometry* check (watertight, bounds, bed proxy). It is NOT a fit
test and NOT a print test. It does not substitute for a real slice or a neck
fit coupon. Do not treat a PASS here (or an assembly_check pass count) as
proof of fit.

Does not touch PR #28 production STLs.
"""
from __future__ import annotations

import json
import os
import sys

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "stl")


def chk(name, ok, measured, expected=""):
    print(("PASS" if ok else "FAIL"), name, "|", measured, "|", expected)
    return bool(ok)


def main():
    print(
        "NOTE: geometry/interference-style check only — NOT a fit test, "
        "NOT a print test. assembly_check pass counts are not proof of fit."
    )
    report = json.load(open(os.path.join(HERE, "opt_b_report.json")))
    ok_all = True
    path = os.path.join(STL, "pod_L_base_optB_curveUP.stl")
    m = trimesh.load(path, force="mesh")
    ok_all &= chk("optB curveUP watertight", m.is_watertight, m.is_watertight, True)
    ok_all &= chk("optB volume>0", m.volume > 0, round(float(m.volume)), ">0")
    ext = [round(float(v), 2) for v in m.extents]
    ok_all &= chk("optB fits P2S 256", max(ext) <= 256, ext, "<=256")
    ok_all &= chk(
        "chosen orientation is curve-UP",
        report.get("chosen_orientation") == "2_cavity_DOWN_curve_UP",
        report.get("chosen_orientation"),
        "2_cavity_DOWN_curve_UP",
    )
    fl = report["orientations"]["2_cavity_DOWN_curve_UP"]["first_layer_area_mm2"]
    ok_all &= chk("first-layer area > 500 mm² (adhesion proxy)", fl > 500, fl, ">500")
    # Production cavity-up bed is ~1900 mm²; curve-UP is smaller — flag, not fail
    chk(
        "first-layer area vs prod cavity-up bed (~1900)",
        True,
        f"optB={fl} vs prod≈1900 — smaller; brim recommended",
        "info",
    )
    lid = os.path.join(STL, "optb_bay_cover.stl")
    if os.path.isfile(lid):
        ml = trimesh.load(lid, force="mesh")
        ok_all &= chk("optB service lid watertight", ml.is_watertight, ml.is_watertight, True)
    print("RESULT", "PASS" if ok_all else "FAIL")
    print(
        "Again: PASS means manifold/bounds sanity only. "
        "It does not prove neck fit, print success, or seal."
    )
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
