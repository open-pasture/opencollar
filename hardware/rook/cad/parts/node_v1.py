"""Node V1 option 1 print files: cap (base, lid, 2 clamp bars), pod (base,
lid, 2 clamp bars; print two of each), counterweight casing (tub, lid,
2 clamp bars), plus assembly-aid test coupon / scale bar. Geometry in
lib/node_v1.py.

Cap underside styles (do not overwrite each other's STLs):
  gable   — v3 fit-test (76×160×41.4) → stl/node_v1_cap/
  saddle  — slim flat floor + printed strap saddle → stl/node_v1_cap_saddle/

Select style with OC_CAP_STYLE=saddle|gable, or after `--`:
  blender ... --python parts/node_v1.py -- cap saddle
  blender ... --python parts/node_v1.py -- --saddle
  blender ... --python parts/node_v1.py -- coupon

Print: MJF PA12 (no supports), or ASA on FDM (6 perimeters, 40 % infill,
100 % around bosses and the strap channels).
  gable bases     outside face down (gable + spine V are self-supporting)
  saddle bases    outside face down (flat underside; brim recommended for ASA)
  saddle          flank face on bed, roof+pins up
  lids            mating face down
  bars            flat
  coupon / scale  flat on bed
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "..", "common", "cad", "lib")))
os.environ.setdefault("OC_PRODUCT_ROOT", os.path.abspath(os.path.join(_HERE, "..", "..")))
import node_v1 as n
import oc
# STLs land in hardware/rook/stl/ (OC_PRODUCT_ROOT).


def _parse_args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    part = os.environ.get("OC_PART", "all")
    style = os.environ.get("OC_CAP_STYLE", "gable")
    for a in raw:
        if a in ("--saddle",) or a == "CAP_STYLE=saddle":
            style = "saddle"
        elif a in ("--gable",) or a == "CAP_STYLE=gable":
            style = "gable"
        elif a.startswith("CAP_STYLE="):
            style = a.split("=", 1)[1]
        elif a == "saddle":
            style = "saddle"
            if part == "all" and not any(x in raw for x in ("all", "cap", "pod", "cw", "coupon")):
                part = "cap"
        elif a == "gable":
            style = "gable"
        elif a in ("all", "cap", "pod", "cw", "coupon"):
            part = a
    return part, style


part, style = _parse_args()
n.set_cap_style(style)

# Engraved glyphs leave knife-edge wedges; allow the same class of thin area
# as fit_test (labels only — structural walls stay ≥1 mm elsewhere).
AID_THIN = 1100.0  # 5×7 bitmap glyph corners (pixel gaps ≈0.06 mm walls)

oc.reset()
if part in ("all", "cap"):
    if style == "saddle":
        base, lid, bar, saddle = n.cap_base(), n.cap_lid(), n.cap_bar(), n.cap_saddle()
        oc.move(lid, dx=n.CAP_W + 20)
        oc.move(bar, dx=-(n.CAP_W / 2 + 20))
        oc.move(saddle, dy=n.CAP_L / 2 + n.SADDLE_L / 2 + 20)
        refs = n.cap_refs()
        clamp_stack, clamp_screw = n.clamp_screw_stack_mm()
        lid_stack, lid_screw = n.lid_screw_stack_mm()
        oc.finish(
            "node_v1_cap_saddle",
            {"node_cap_base_saddle": base, "node_cap_lid": lid,
             "node_cap_clamp_bar": bar, "node_cap_saddle": saddle},
            spec={"node_cap_base_saddle": {"size": (n.CAP_W, n.CAP_L, n.CAP_BASE_H), "tol": 0.6},
                  "node_cap_lid": {"size": (n.CAP_W, n.CAP_L, n.CAP_LID_T)},
                  "node_cap_clamp_bar": {"size": n.CAP_BAR},
                  "node_cap_saddle": {"size": (n.SADDLE_W, n.SADDLE_L, n.SADDLE_H + n.SADDLE_PIN_H), "tol": 0.6}},
            refs=refs, material="PA12", min_wall=1.0, thin_area_allowed=AID_THIN,
            notes=("CAP_STYLE=saddle slim set + assembly-aid engraving (REV "
                   f"{n.AID_REV}). Lid M3x{lid_screw:.0f}; clamp M3x{clamp_screw:.0f}. "
                   "Inside-floor labels (bed face flat, no dimples); PIN marked. Supports off."))
    else:
        base, lid, bar = n.cap_base(), n.cap_lid(), n.cap_bar()
        oc.move(lid, dx=n.CAP_W + 20)
        oc.move(bar, dx=-(n.CAP_W / 2 + 20))
        refs = n.cap_refs()
        oc.finish(
            "node_v1_cap",
            {"node_cap_base": base, "node_cap_lid": lid, "node_cap_clamp_bar": bar},
            spec={"node_cap_base": {"size": (n.CAP_W, n.CAP_L, n.CAP_BASE_H)},
                  "node_cap_lid": {"size": (n.CAP_W, n.CAP_L, n.CAP_LID_T)},
                  "node_cap_clamp_bar": {"size": n.CAP_BAR}},
            refs=refs, material="PA12", min_wall=1.0, thin_area_allowed=60.0,
            notes="Print 2 clamp bars. 8 x M3x40 button head (ISO 7380, A2/304) + bonded M3 sealing washers (lid, from below), "
                  "4 x M3x8 button head (bars); 12 x M3x4 heat-set inserts (8 lid + 4 clamp bar). "
                  "thin_area_allowed: ~0.8 mm keep-out between 5 mm lid insert pockets and the 1.2 mm panel pocket.")

if part in ("all", "pod"):
    oc.reset()
    base_l, base_r = n.pod_base("L"), n.pod_base("R")
    lid, bar = n.pod_lid(), n.pod_bar()
    oc.move(base_r, dx=n.POD_L + 20)
    oc.move(lid, dy=n.POD_W + 20)
    oc.move(bar, dx=n.POD_L / 2 + 20, dy=-(n.POD_W / 2 + 20))
    oc.finish(
        "node_v1_pod",
        {"node_pod_base": base_l, "node_pod_base_R": base_r,
         "node_pod_lid": lid, "node_pod_clamp_bar": bar},
        spec={"node_pod_base": {"size": (n.POD_L, n.POD_W, n.POD_BASE_H), "tol": 0.8},
              "node_pod_base_R": {"size": (n.POD_L, n.POD_W, n.POD_BASE_H), "tol": 0.8},
              "node_pod_lid": {"size": (n.POD_L, n.POD_W, n.POD_LID_T)},
              "node_pod_clamp_bar": {"size": n.POD_BAR}},
        refs=n.pod_refs(), material="PA12", min_wall=1.0, thin_area_allowed=AID_THIN,
        notes=("Assembly aids REV "
               f"{n.AID_REV}: R9.4 cell cradle, buzzer L + ±Y slot rails, cable grooves, "
               "inside + outer-wall labels (bed face flat; −Y wall +90°X + mirror X). "
               "FDM: pods need supports for cavity rails/cradle. "
               "Print node_pod_base (L) and node_pod_base_R (or mirror L). "
               f"Per pod: 4 x M3x{n.POD_LID_SCREW:.0f} lid + sealing washers, 4 x M3x6 bars, 8 x M3x4 inserts."))

if part in ("all", "cw"):
    oc.reset()
    tub, lid, bar = n.cw_tub(), n.cw_lid(), n.pod_bar()
    oc.move(lid, dy=n.CW_W + 20)
    oc.move(bar, dx=n.CW_L / 2 + 20)
    oc.finish(
        "node_v1_cw",
        {"node_cw_tub": tub, "node_cw_lid": lid, "node_cw_clamp_bar": bar},
        spec={"node_cw_tub": {"size": (n.CW_L, n.CW_W, n.CW_TUB_H)},
              "node_cw_lid": {"size": (n.CW_L, n.CW_W, n.CW_LID_T)}},
        refs=n.cw_refs(), material="PA12", min_wall=1.0,
        notes=f"Steel: {n.STEEL_N} x 3 in of 2 x 1/4 in flat bar = {n.steel_mass_g():.0f} g. Print 2 bars. "
              "4 x M3x8 button head (lid, from the neck side), 4 x M3x6 (bars), 8 x M3x4 inserts. Foam pad on top of the steel.")

if part in ("all", "coupon"):
    oc.reset()
    coupon, scale = n.test_coupon(), n.scale_bar()
    oc.move(scale, dy=n.COUPON_OVERALL_Y / 2 + n.SCALE_Y / 2 + 10)
    plate = n.bases_plate_footprint_mm()
    oc.finish(
        "test_coupon",
        {"test_coupon": coupon, "scale_bar_xyz": scale},
        spec={"test_coupon": {"size": (n.COUPON_OVERALL_X, n.COUPON_OVERALL_Y,
                                       n.COUPON_GAUGE_MAX_H), "tol": 3.0},
              "scale_bar_xyz": {"size": (n.SCALE_X, n.SCALE_Y, n.SCALE_Z), "tol": 1.0}},
        material="PA12", min_wall=0.8, thin_area_allowed=AID_THIN,
        notes=("AID1 coupon + tri-axis scale. Insert ladder Ø4.0–4.8 × 6 mm, "
               "lid/clamp gap pads 0.1–0.4, M3x14/16/18 gauge (0.2 mm floor), "
               "blind tap/clear/sockets (1 mm floor), pins, bridge, "
               f"e-foot, O-ring sample, ANT stamp. Plate footprint ~{plate[0]}×{plate[1]} "
               "with cap+2 pods (246 usable)."))
