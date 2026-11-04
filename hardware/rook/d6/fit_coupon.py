"""D8 fit coupon — P0 PLA on Bambu P2S 256.

Carries:
  (a) three convex arc gauges R208 / R218 / R221 + bonus R350
  (b) flat-underside and saddle-underside 97 mm pod footprints (feeler-gap)
  (c) prior items: joint groove, strap flare, lid lip/inset, prism 001, Ø2 recess

Print: PLA, features UP, no brim required. Owner must approve before any print.

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

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib")))
sys.path.insert(0, _HERE)

import oc  # noqa: E402
import d8_glyphs as g001  # noqa: E402

OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

# Plate envelope — must fit P2S 256
BED = 256.0
PLATE_X = 248.0
PLATE_Y = 248.0

# Feature block (existing D8 coupon language)
FEAT_Y = 70.0
FEAT_X = 80.0
BASE_H = 8.0
LID_H = 4.0
LID_INSET = 3.0
GROOVE_W = 1.5
GROOVE_D = 3.0
GROOVE_FLOOR = 4.0
PLAN_R = 3.0
STRAP_FLARE_W = 76.0
MID_W = 68.0
POD_FOOT_L = 97.0
POD_FOOT_W = 52.0

# Neck gauges (Cody quoted local R at pod station)
GAUGE_RS = (208.0, 218.0, 221.0, 350.0)
GAUGE_CHORD = 97.0
GAUGE_W = 14.0
GAUGE_H = 12.0


def _clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _sagitta(R, half):
    return float(R - math.sqrt(max(R * R - half * half, 0.0)))


def _convex_gauge(name, R, chord, width, height):
    """Convex arc gauge: thin base + raised cylindrical ridge (pod rests on crest)."""
    half = 0.5 * chord
    sag = _sagitta(R, half)
    base_h = 2.0
    base = oc.rounded_rect(
        f"{name}_base", (width, chord + 4.0, base_h), 1.5,
        at=(0.0, 0.0, 0.0), anchor="bottom", segments=6,
    )
    # Cylinder axis X — keep only the thin upper cap (ridge)
    cyl_z = base_h - R + sag
    cyl = oc.cylinder(
        f"{name}_cyl", 2.0 * R, width - 2.0,
        at=(0.0, 0.0, cyl_z), axis="X", segments=64, anchor="center",
    )
    keep = oc.box(
        f"{name}_keep",
        (width, chord + 2.0, min(height, sag + 1.5)),
        at=(0.0, 0.0, base_h),
        anchor="bottom",
    )
    oc.intersect(cyl, keep)
    oc.union(base, cyl)
    oc.bake(base)
    return base, sag


def _footprint(name, curved):
    """97 mm pod footprint — flat or R220 saddle underside (concave cut)."""
    h = 6.0 if not curved else 8.0
    fp = oc.rounded_rect(
        name, (POD_FOOT_W, POD_FOOT_L, h), PLAN_R,
        at=(0.0, 0.0, 0.0), anchor="bottom", segments=8,
    )
    if curved:
        R = 220.0
        half = 0.5 * POD_FOOT_L
        sag = _sagitta(R, half)
        cyl = oc.cylinder(
            f"{name}_R", 2.0 * R, POD_FOOT_W + 4.0,
            at=(0.0, 0.0, h - sag + R), axis="X", segments=64, anchor="center",
        )
        keep = oc.box(
            f"{name}_k",
            (POD_FOOT_W + 6.0, POD_FOOT_L + 6.0, sag + 2.0),
            at=(0.0, 0.0, h - sag - 1.0),
            anchor="bottom",
        )
        oc.intersect(cyl, keep)
        oc.cut(fp, cyl)
    # Feeler slot mark at mid (0.5 mm deep scribe)
    oc.cut(
        fp,
        oc.box(f"{name}_feeler", (POD_FOOT_W + 2.0, 0.6, 0.6),
               at=(0.0, 0.0, h - 0.5), anchor="bottom"),
    )
    oc.bake(fp)
    return fp


def _feature_block():
    """Prior D8 coupon language: groove, flare, lip, 001, screw."""
    base = oc.rounded_rect(
        "feat_base", (MID_W, FEAT_Y, BASE_H), PLAN_R,
        at=(0.0, 0.0, 0.0), anchor="bottom", segments=10,
    )
    flare = oc.rounded_rect(
        "feat_flare", (STRAP_FLARE_W, 22.0, BASE_H), PLAN_R,
        at=(0.0, -FEAT_Y * 0.28, 0.0), anchor="bottom", segments=10,
    )
    oc.union(base, flare)
    # Strap-end notches (D4-like)
    for sx in (-1.0, 1.0):
        oc.cut(
            base,
            oc.box(
                f"feat_notch{int(sx+2)}",
                (6.0, 5.0, BASE_H + 2.0),
                at=(sx * (STRAP_FLARE_W * 0.5 - 3.0), -FEAT_Y * 0.45, BASE_H * 0.5),
                anchor="center",
            ),
        )
    stub = oc.rounded_rect(
        "feat_stub", (MID_W + 4.0, 18.0, BASE_H + 4.0), PLAN_R,
        at=(0.0, FEAT_Y * 0.38, 0.0), anchor="bottom", segments=10,
    )
    oc.union(base, stub)
    # Blind groove (closed ends + floor)
    depth = min(GROOVE_D, BASE_H + 4.0 - GROOVE_FLOOR)
    oc.cut(
        base,
        oc.box(
            "feat_groove",
            (MID_W - 6.0, GROOVE_W, depth),
            at=(0.0, FEAT_Y * 0.18, BASE_H + 4.0 - depth),
            anchor="bottom",
        ),
    )
    lw = MID_W - 2 * LID_INSET
    ll = FEAT_Y * 0.55
    # Stronger lip terrace
    lip = oc.rounded_rect(
        "feat_lip", (MID_W - 0.5, ll + 2.0, 1.8), PLAN_R,
        at=(0.0, -FEAT_Y * 0.08, BASE_H - 0.2), anchor="bottom", segments=8,
    )
    oc.union(base, lip)
    lid = oc.rounded_rect(
        "feat_lid", (lw, ll, LID_H), PLAN_R,
        at=(0.0, -FEAT_Y * 0.08, BASE_H + 1.5), anchor="bottom", segments=10,
    )
    oc.union(base, lid)
    z_top = BASE_H + 1.5 + LID_H
    oc.cut(
        base,
        oc.cylinder(
            "feat_screw", 1.0, 0.6,
            at=(lw * 0.35, -FEAT_Y * 0.22, z_top - 0.4),
            anchor="bottom", segments=16,
        ),
    )
    cutters, span = g001.make_001_cutters(
        size=6.0, depth=1.0, stroke=1.0, width=3.7, gap=1.2,
    )
    id_y = -FEAT_Y * 0.12
    for cutter in cutters:
        along = float(cutter.location.y)
        cutter.location = (0.0, id_y + along, z_top - 0.3)
        for cc in list(cutter.users_collection):
            cc.objects.unlink(cutter)
        bpy.context.scene.collection.objects.link(cutter)
        oc.cut(base, cutter)
        try:
            bpy.data.objects.remove(cutter, do_unlink=True)
        except Exception:
            pass
    oc.bake(base)
    return base, span


def build_coupon_plate():
    """Lay out all coupon elements on one P0 plate (separate bodies unioned
    with spacers so the STL is one printable plate)."""
    parts = []
    # Feature block at origin
    feat, span = _feature_block()
    parts.append(("feature", feat, (0.0, 0.0, 0.0)))

    # Arc gauges in a row along +X
    gx0 = 55.0
    for i, R in enumerate(GAUGE_RS):
        g, sag = _convex_gauge(f"gauge_R{int(R)}", R, GAUGE_CHORD, GAUGE_W, GAUGE_H)
        x = gx0 + i * (GAUGE_W + 6.0)
        parts.append((f"R{int(R)}", g, (x, 0.0, 0.0)))

    # Footprints below feature block (−Y)
    fp_flat = _footprint("foot_flat", curved=False)
    fp_sad = _footprint("foot_saddle", curved=True)
    parts.append(("foot_flat", fp_flat, (-90.0, -20.0, 0.0)))
    parts.append(("foot_saddle", fp_sad, (-90.0, 90.0, 0.0)))

    # Pack parts with thin 1.2 mm sprue links (no solid deck — keeps PLA volume down)
    root = None
    for tag, obj, (dx, dy, dz) in parts:
        oc.move(obj, dx=dx, dy=dy, dz=dz)
        if root is None:
            root = obj
        else:
            # sprue from previous centroid-ish toward this part
            oc.union(root, obj)
            sprue = oc.box(
                f"sprue_{tag}",
                (1.2, 1.2, 1.2),
                at=(dx * 0.5, dy * 0.5, 0.6),
                anchor="center",
            )
            oc.union(root, sprue)

    oc.bake(root)
    bb = oc.bounds(root)
    cx = 0.5 * (bb[0][0] + bb[1][0])
    cy = 0.5 * (bb[0][1] + bb[1][1])
    oc.move(root, dx=-cx, dy=-cy, dz=-bb[0][2])
    dims = list(oc.size(root))
    return root, span, dims, {
        "gauges_R_mm": list(GAUGE_RS),
        "gauge_sagitta_mm": {str(int(R)): round(_sagitta(R, 0.5 * GAUGE_CHORD), 2) for R in GAUGE_RS},
        "footprints": ["flat_underside_97", "saddle_R220_underside_97"],
        "001_span_mm": round(span, 1),
    }


def main():
    _clean()
    coupon, span, dims, feat_meta = build_coupon_plate()
    path = os.path.join(OUT, "d8_fit_coupon.stl")
    oc.export_stl(coupon, path)
    fit = max(dims[0], dims[1]) <= BED - 4.0
    # Est. PLA time: ~12 cm³/h ≈ 200 mm³/min + 10 min heat (re-slice before print)
    vol = float(oc.volume_mm3(coupon))
    est_h = (vol / 200.0 + 10.0) / 60.0
    meta = {
        "name": "d8_fit_coupon",
        "stl": path,
        "dims_mm": [round(d, 2) for d in dims],
        "fits_p2s_256": fit,
        "features": feat_meta,
        "also": [
            "blind 1.5 mm cap↔pod groove (floor + closed ends)",
            "strap-end flare + D4 notches",
            "lid inset 3 mm + strengthened lip",
            f"prism 001 span≈{span:.1f} mm",
            "Ø2 screw-head recess",
            "convex gauges R208/218/221 + R350",
            "flat + saddle 97 mm footprints (feeler mid-mark)",
        ],
        "print": {
            "material": "PLA",
            "plate": "P0",
            "orientation": "features UP",
            "brim": "optional",
            "bed": "Bambu P2S 256",
            "est_hours_pla": round(est_h, 2),
            "est_note": "rough volume heuristic — re-slice before any real plate",
        },
        "saddle_print_note": (
            "Full curved saddle (not this coupon): flat pod-face on bed, "
            "concave R220 UP, light bowl supports. Curve never on the bed. "
            "Side-print rejected as default — seal face would be vertical layers."
        ),
        "electrode_note": (
            "Shock-electrode bay + compliant/floating contact still required; "
            "rigid R220 alone is not skin contact. Ellipse 25×42 cm is a model — "
            "check against real neck measurements; do not invent them."
        ),
        "note": "Fit-check only. Owner must approve before any print.",
    }
    json.dump(meta, open(os.path.join(OUT, "d8_fit_coupon.json"), "w"), indent=2)
    plate = {
        "plate": "D8_P0_fit_coupon",
        "bed_mm": 256,
        "material": "PLA",
        "est_hours": round(est_h, 2),
        "parts": [
            {"stl": "d8_fit_coupon.stl", "qty": 1, "material": "PLA"},
        ],
        "arrange": "centre; features UP; no brim required; leave 4 mm margin",
        "contains": meta["also"],
    }
    json.dump(plate, open(os.path.join(OUT, "d8_fit_coupon_plate.json"), "w"), indent=2)
    with open(os.path.join(OUT, "d8_fit_coupon_plate.txt"), "w") as f:
        f.write(
            "D8 P0 fit coupon — Bambu P2S 256×256 (PLA, features UP)\n"
            f"bbox ≈ {dims[0]:.0f} × {dims[1]:.0f} × {dims[2]:.0f} mm  "
            f"est ≈ {est_h:.1f} h PLA\n"
            "Contents: feature block (groove/flare/lip/001) + R208/218/221/350\n"
            "gauges + flat & saddle 97 mm footprints.\n"
            "Owner must approve before any print.\n"
        )
    print("OK", path, [round(d, 1) for d in dims], f"fit256={fit} est_h={est_h:.2f}")


if __name__ == "__main__":
    main()
