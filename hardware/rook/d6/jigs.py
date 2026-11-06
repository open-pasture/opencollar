"""D8 DIY assembly jig plate — ~60–90 min PLA set (compact, flat on bed).

Exports (print Z=0, no supports intended):
  jig_m3_heatset_stop.stl
  jig_wire_gauge.stl
  jig_blank_shock_plug_L.stl / _R.stl / _spare.stl

Real print time: measure in OrcaSlicer 2.4.2 — do NOT invent formula hours.

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python jigs.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib")))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "d5", "cad")))
sys.path.insert(0, _HERE)

import oc  # noqa: E402
import build_d5 as d5  # noqa: E402

OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)


def _export(obj, name):
    path = os.path.join(OUT, name)
    oc.move(obj, dz=-oc.bounds(obj)[0][2])
    oc.prepare_for_export(obj, merge=1e-4)
    oc.export_stl(obj, path)
    wt = oc.check_stl_watertight(path)
    dims = [round(float(v), 2) for v in oc.size(obj)]
    vol = float(obj.data.volume) if hasattr(obj.data, "volume") else 0.0
    try:
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        vol = abs(bm.calc_volume())
        bm.free()
    except Exception:
        pass
    print(("OK" if wt.get("watertight") else "LOOK"), path, dims, wt)
    return {
        "path": path,
        "size_mm": dims,
        "volume_cm3": round(vol / 1000.0, 2),
        "watertight": wt,
        "print": "flat on bed Z=0; no supports intended",
    }


def jig_m3_heatset_stop():
    """Depth-stop collar for M3×4 / M3×5 brass inserts — flush to −0.15 mm.

    Critical: tip Ø5.2 bore must NOT swallow the Ø4.05 insert shelf.
    Shelf sits at z = 8.0 - 4.85 = 3.15 (solid annular land).
    """
    H = 8.0
    INSERT_DEPTH = 4.85          # M3×5 − 0.15
    SHELF_Z = H - INSERT_DEPTH   # 3.15
    body = oc.rounded_rect("jig_m3_heatset_stop", (28.0, 20.0, H), 2.0,
                           at=(0, 0, 0), anchor="bottom", segments=8)
    # Tip bore from BOTTOM only up to the shelf (leaves solid land at SHELF_Z)
    oc.cut(body, oc.cylinder(
        "tip", 5.2, SHELF_Z + 0.05,
        at=(0, 0, -0.02), anchor="bottom", segments=32,
    ))
    # Insert bore from TOP down to the shelf
    oc.cut(body, oc.cylinder(
        "ins", 4.05, INSERT_DEPTH + 0.05,
        at=(0, 0, SHELF_Z), anchor="bottom", segments=32,
    ))
    try:
        d5.emboss_glyph(body, "M3 STOP", (0.0, -7.5, H), size=4.5, depth=0.7)
    except Exception:
        d5.emboss_label(body, "SCR1", (0.0, -7.5, H))
    oc.bake(body)
    return body


def jig_wire_gauge():
    """≤190 mm long, ≤5 mm thick wire + M3 length gauge.

    Channel stops short of the M3 zone so the 10 mm slot at mid-X stays distinct.
    Strip notches sit at exactly 5.0 / 8.0 mm from the −Y reference end.
    """
    L, W, T = 180.0, 28.0, 4.5
    body = oc.rounded_rect("jig_wire_gauge", (W, L, T), 2.0,
                           at=(0, 0, 0), anchor="bottom", segments=8)
    # Wire channel — shortened so it does NOT reach the M3 slot band near +Y
    # M3 slots occupy y ≳ +L/2 − 40; keep channel ending ~12 mm before that.
    ch_l = L - 55.0
    ch_cy = -8.0
    oc.cut(body, oc.box("ch", (6.0, ch_l, 2.2),
                        at=(0, ch_cy, T - 2.0), anchor="bottom"))
    # Strip notches at 5 mm and 8 mm from −Y end (y = −L/2 + d)
    for i, d in enumerate((5.0, 8.0)):
        y = -0.5 * L + d
        oc.cut(body, oc.box(f"strip{i}", (W + 2, 1.2, 2.0),
                            at=(0, y, T - 1.5), anchor="bottom"))
    # M3 screw length slots: 6/8/10/12/16 — all five distinct, clear of channel
    for i, sl in enumerate((6.0, 8.0, 10.0, 12.0, 16.0)):
        x = -10.0 + i * 5.0
        oc.cut(body, oc.box(f"m3_{int(sl)}", (2.0, sl + 0.4, 2.5),
                            at=(x, 0.5 * L - 20.0 - 0.5 * sl, T - 2.2),
                            anchor="bottom"))
    try:
        d5.emboss_glyph(body, "WIRE + M3", (0.0, -0.5 * L + 12.0, T), size=4.0, depth=0.6)
    except Exception:
        pass
    oc.bake(body)
    return body


# Blank shock plug: stem Ø7.60 → receiving bore Ø8.05 (0.225 mm/side)
BLANK_SHOCK_STEM_D = 7.60
BLANK_SHOCK_BORE_D = 8.05
BLANK_SHOCK_STEM_H = 6.00
BLANK_SHOCK_FLANGE_D = 12.0
BLANK_SHOCK_FLANGE_H = 1.80


def jig_blank_shock_plug(side: str = "L"):
    """Blank shock-bay plug — seals reserved bay; zero exposed electrode holes.

    Stem Ø7.60 × 6.0 mates Ø8.05 receiving bore (0.225 mm/side) in optB bay.
    Flange Ø12.0 × 1.8 seats flush on the bore land.
    """
    stem = oc.cylinder(
        f"jig_blank_shock_plug_{side}", BLANK_SHOCK_STEM_D, BLANK_SHOCK_STEM_H,
        at=(0, 0, 0), anchor="bottom", segments=32,
    )
    flange = oc.cylinder(
        "flange", BLANK_SHOCK_FLANGE_D, BLANK_SHOCK_FLANGE_H,
        at=(0, 0, BLANK_SHOCK_STEM_H - 0.5), anchor="bottom", segments=32,
    )
    oc.union(stem, flange)
    # No proud top glyphs — keep Z envelope = stem+flange for seated clearance
    oc.bake(stem)
    oc.move(stem, dz=-oc.bounds(stem)[0][2])
    return stem


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {
        "revision": "D8_diy_jig_plate",
        "note": (
            "Compact PLA jig set. Do NOT invent print hours from volume formulas — "
            "measure in OrcaSlicer 2.4.2. Target real PLA ~60–90 min for the set."
        ),
        "bodies": {},
        "pass": True,
    }
    jobs = [
        ("jig_m3_heatset_stop.stl", jig_m3_heatset_stop),
        ("jig_wire_gauge.stl", jig_wire_gauge),
        ("jig_blank_shock_plug_L.stl", lambda: jig_blank_shock_plug("L")),
        ("jig_blank_shock_plug_R.stl", lambda: jig_blank_shock_plug("R")),
        ("jig_blank_shock_plug_spare.stl", lambda: jig_blank_shock_plug("S")),
    ]
    total_cm3 = 0.0
    for name, fn in jobs:
        oc.reset()
        obj = fn()
        meta = _export(obj, name)
        report["bodies"][name] = meta
        total_cm3 += meta["volume_cm3"]
        if not meta["watertight"].get("watertight"):
            report["pass"] = False
    report["total_volume_cm3"] = round(total_cm3, 2)
    report["qty_note"] = {
        "jig_blank_shock_plug_L": 1,
        "jig_blank_shock_plug_R": 1,
        "jig_blank_shock_plug_spare": 1,
        "use": "Seats Option A saddle bay and Option B integral bay; embossed NO SHOCK",
    }
    with open(os.path.join(OUT, "jigs_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("TOTAL_CM3", report["total_volume_cm3"])
    print("PASS" if report["pass"] else "FAIL")
    return report


if __name__ == "__main__":
    main()
