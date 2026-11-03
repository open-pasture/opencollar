"""Node V1 option 1 print files: cap (base, lid, 2 clamp bars), pod (base,
lid, 2 clamp bars; print two of each), counterweight casing (tub, lid,
2 clamp bars). Geometry in lib/node_v1.py.

Cap underside styles (do not overwrite each other's STLs):
  gable   — v3 fit-test (76×160×41.4) → stl/node_v1_cap/
  saddle  — slim flat floor + printed strap saddle → stl/node_v1_cap_saddle/

Select style with OC_CAP_STYLE=saddle|gable, or after `--`:
  blender ... --python parts/node_v1.py -- cap saddle
  blender ... --python parts/node_v1.py -- --saddle

Print: MJF PA12 (no supports), or ASA on FDM (6 perimeters, 40 % infill,
100 % around bosses and the strap channels).
  gable bases     outside face down (gable + spine V are self-supporting)
  saddle bases    outside face down (flat underside; brim recommended for ASA)
  saddle          roof face down (flat on bed; rails up; no supports)
  lids            mating face down
  bars            flat
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
            # Bare "saddle" is the style; alone it also means "build the cap set".
            style = "saddle"
            if part == "all" and not any(x in raw for x in ("all", "cap", "pod", "cw")):
                part = "cap"
        elif a == "gable":
            style = "gable"
        elif a in ("all", "cap", "pod", "cw"):
            part = a
    return part, style


part, style = _parse_args()
n.set_cap_style(style)

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
            # Base Z includes underside locating pins (SADDLE_PIN_H below z=0).
            spec={"node_cap_base_saddle": {"size": (n.CAP_W, n.CAP_L, n.CAP_BASE_H + n.SADDLE_PIN_H), "tol": 0.6},
                  "node_cap_lid": {"size": (n.CAP_W, n.CAP_L, n.CAP_LID_T)},
                  "node_cap_clamp_bar": {"size": n.CAP_BAR},
                  "node_cap_saddle": {"size": (n.SADDLE_W, n.SADDLE_L, n.SADDLE_H), "tol": 0.6}},
            refs=refs, material="PA12", min_wall=1.0, thin_area_allowed=60.0,
            notes=("CAP_STYLE=saddle slim set. Does NOT overwrite stl/node_v1_cap/ (gable v3). "
                   f"Lid: {lid_screw:.0f} mm button head + sealing washer (stack ~{lid_stack:.1f} mm). "
                   f"Clamp: {clamp_screw:.0f} mm button head (stack ~{clamp_stack:.1f} mm) through bar + "
                   "saddle into underside inserts (blind to cavity). "
                   "Print saddle roof-down. ASA: brim on base and saddle. "
                   "thin_area_allowed: lid insert vs panel pocket keep-out."))
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
    base, lid, bar = n.pod_base(), n.pod_lid(), n.pod_bar()
    oc.move(lid, dy=n.POD_W + 20)
    oc.move(bar, dx=n.POD_L / 2 + 20)
    oc.finish(
        "node_v1_pod",
        {"node_pod_base": base, "node_pod_lid": lid, "node_pod_clamp_bar": bar},
        spec={"node_pod_base": {"size": (n.POD_L, n.POD_W, n.POD_BASE_H)},
              "node_pod_lid": {"size": (n.POD_L, n.POD_W, n.POD_LID_T)},
              "node_pod_clamp_bar": {"size": n.POD_BAR}},
        refs=n.pod_refs(), material="PA12", min_wall=1.0,
        notes="Per collar: 2 bases and 2 lids (print the second pair mirrored), 4 bars. Per pod: 4 x M3x25 button head + sealing washers, "
              "4 x M3x6 button head (bars), 8 x M3x4 inserts, 2 x M4x10 A2 pan head + nut + O-ring (electrodes). "
              "Plan of record: 1 x Adafruit 1781 + 1 x Qwiic Buzzer per pod.")

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
