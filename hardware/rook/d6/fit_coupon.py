"""D8 fit coupon — ~70 mm along-strap slice for PLA fast-fit.

Contains: one cap↔pod joint groove, pod strap-end shoulder flare, lid inset
lip, prism '001' pocket, and one screw-head recess. Lay flat on bed (Z-up).

Print: PLA, no brim required. Plate with other coupons on P0.

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python fit_coupon.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _HERE)

import oc  # noqa: E402
import d8_glyphs as g001  # noqa: E402

OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

# Coupon envelope — ~70 mm along Y (strap), ~80 mm across X
COUPON_Y = 70.0
COUPON_X = 80.0
COUPON_H = 12.0
BASE_H = 8.0
LID_H = 4.0
LID_INSET = 3.0
GROOVE_W = 1.5
GROOVE_D = 3.0
PLAN_R = 3.0
STRAP_FLARE_W = 76.0
MID_W = 68.0


def _clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_coupon():
    """Lay-flat coupon: base block + inset lid slab + features."""
    # Base: mid width with strap-end flare toward −Y
    base = oc.rounded_rect(
        "coupon_base", (MID_W, COUPON_Y, BASE_H), PLAN_R,
        at=(0.0, 0.0, 0.0), anchor="bottom", segments=10,
    )
    flare = oc.rounded_rect(
        "coupon_flare", (STRAP_FLARE_W, 22.0, BASE_H), PLAN_R,
        at=(0.0, -COUPON_Y * 0.28, 0.0), anchor="bottom", segments=10,
    )
    oc.union(base, flare)

    # Cap stub (+Y) with joint groove between stub and pod deck
    stub = oc.rounded_rect(
        "coupon_cap_stub", (MID_W + 4.0, 18.0, BASE_H + 4.0), PLAN_R,
        at=(0.0, COUPON_Y * 0.38, 0.0), anchor="bottom", segments=10,
    )
    oc.union(base, stub)
    # 1.5 mm groove at joint (top trough)
    oc.cut(
        base,
        oc.box(
            "coupon_groove",
            (COUPON_X, GROOVE_W, GROOVE_D + 0.5),
            at=(0.0, COUPON_Y * 0.18, BASE_H + 4.0 - GROOVE_D),
            anchor="bottom",
        ),
    )

    # Inset lid deck on the pod half (−Y side of groove)
    lw = MID_W - 2 * LID_INSET
    ll = COUPON_Y * 0.55
    lid = oc.rounded_rect(
        "coupon_lid", (lw, ll, LID_H), PLAN_R,
        at=(0.0, -COUPON_Y * 0.08, BASE_H), anchor="bottom", segments=10,
    )
    # Lip line: thin step shelf under lid (visible base rim)
    lip = oc.rounded_rect(
        "coupon_lip", (MID_W - 1.0, ll + 2.0, 1.2), PLAN_R,
        at=(0.0, -COUPON_Y * 0.08, BASE_H - 0.2), anchor="bottom", segments=8,
    )
    oc.union(base, lip)
    oc.union(base, lid)

    z_top = BASE_H + LID_H

    # Screw recess
    oc.cut(
        base,
        oc.cylinder(
            "coupon_screw", 1.0, 0.6,
            at=(lw * 0.35, -COUPON_Y * 0.22, z_top - 0.4),
            anchor="bottom", segments=16,
        ),
    )

    # Prism 001 on lid
    cutters, span = g001.make_001_cutters(
        size=6.0, depth=1.0, stroke=1.0, width=3.7, gap=1.2,
    )
    id_y = -COUPON_Y * 0.12
    id_z = z_top - 0.3
    for cutter in cutters:
        along = float(cutter.location.y)
        cutter.location = (0.0, id_y + along, id_z)
        for cc in list(cutter.users_collection):
            cc.objects.unlink(cutter)
        bpy.context.scene.collection.objects.link(cutter)
        oc.cut(base, cutter)
        try:
            bpy.data.objects.remove(cutter, do_unlink=True)
        except Exception:
            pass

    oc.bake(base)
    # Normalize z=0
    bb = oc.bounds(base)
    oc.move(base, dz=-bb[0][2])
    return base, span


def main():
    _clean()
    coupon, span = build_coupon()
    path = os.path.join(OUT, "d8_fit_coupon.stl")
    oc.export_stl(coupon, path)
    dims = list(oc.size(coupon))
    meta = {
        "name": "d8_fit_coupon",
        "stl": path,
        "dims_mm": [round(d, 2) for d in dims],
        "along_strap_mm": round(dims[1], 1),
        "features": [
            "1.5 mm cap↔pod joint groove",
            "pod strap-end flare ~76 mm",
            "lid inset 3 mm + lip",
            f"prism 001 span≈{span:.1f} mm",
            "Ø2 screw-head recess",
        ],
        "print": {
            "material": "PLA",
            "orientation": "lay-flat, features UP",
            "brim": "optional",
            "plate": "P0 with other floor coupons",
            "bed": "Bambu P2S 256",
        },
        "note": "Fit-check only — not a structural part. Owner must approve before any print.",
    }
    json.dump(meta, open(os.path.join(OUT, "d8_fit_coupon.json"), "w"), indent=2)
    # Simple plate layout note (ASCII + JSON) for P0
    plate = {
        "plate": "D8_P0_fit_coupon",
        "bed_mm": 256,
        "parts": [
            {"stl": "d8_fit_coupon.stl", "qty": 1, "material": "PLA"},
        ],
        "arrange": "centre; features UP; no brim required",
    }
    json.dump(plate, open(os.path.join(OUT, "d8_fit_coupon_plate.json"), "w"), indent=2)
    # ASCII plate layout (P2S 256, P0 with floor coupons) — matches PRINT.md / d5 plates
    layout = os.path.join(OUT, "d8_fit_coupon_plate.txt")
    with open(layout, "w") as f:
        f.write(
            "D8 P0 fit coupon — Bambu P2S 256×256 (PLA, features UP)\n"
            "┌────────────────────────────────────────┐\n"
            "│                 256 mm                 │\n"
            "│   ┌──────────┐                         │\n"
            "│   │ d8_fit_  │  ~76 × 71 mm             │\n"
            "│   │ coupon   │  centre; no brim req.   │\n"
            "│   └──────────┘                         │\n"
            "│   (optional: pod/cap/cw floor coupons) │\n"
            "└────────────────────────────────────────┘\n"
            "Owner must approve before any print.\n"
        )
    print("OK", path, dims, f"001_span={span:.1f}")
    print("plate", layout)


if __name__ == "__main__":
    main()
