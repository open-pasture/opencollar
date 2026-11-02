"""Node V1 option 1 print files: cap, battery pod, cue pod, counterweight.
Geometry in lib/node_v1.py.

Print: MJF PA12 (no supports), or ASA on FDM (6 perimeters, 40 % infill,
100 % around bosses and the strap channels).
  bases and tubs  outside face down (cap spine V + channel gable are 45° — no supports)
  lids            mating face down
  bars            flat

Cap: 76 x 160 with one Voltaic P124 pocket.
Battery pod (left): Adafruit 353 6600 mAh pack.
Cue pod (right): one Qwiic Buzzer; no battery bay.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import node_v1 as n
import oc

part = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "all"

oc.reset()
if part in ("all", "cap"):
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
        refs=refs, material="PA12", min_wall=1.0,
        notes="Print 2 clamp bars. 8 x M3x20 button head + bonded M3 sealing washers (lid, from below), "
              "4 x M3x8 button head (bars); 12 x M3x4 heat-set inserts. "
              "One Voltaic P124 in the lid pocket; GPS patch at the −Y end.")

if part in ("all", "pod", "pod_battery"):
    oc.reset()
    base, lid, bar = n.pod_battery_base(), n.pod_battery_lid(), n.pod_bar()
    oc.move(lid, dy=n.POD_BAT_W + 20)
    oc.move(bar, dx=n.POD_BAT_L / 2 + 20)
    oc.finish(
        "node_v1_pod_battery",
        {"node_pod_battery_base": base, "node_pod_battery_lid": lid, "node_pod_clamp_bar": bar},
        spec={"node_pod_battery_base": {"size": (n.POD_BAT_L, n.POD_BAT_W, n.POD_BASE_H)},
              "node_pod_battery_lid": {"size": (n.POD_BAT_L, n.POD_BAT_W, n.POD_LID_T)},
              "node_pod_clamp_bar": {"size": n.POD_BAR}},
        refs=n.pod_battery_refs(), material="PA12", min_wall=1.0,
        notes="Left / battery pod. 1 x Adafruit 353 pack in the locator recess (foam/VHB). "
              "4 x M3x30 button head + sealing washers, 4 x M3x6 (bars), 8 x M3x4 inserts, "
              "2 x M4x10 A2 pan head + nut + O-ring (electrodes). ePTFE vent patch on −Y. "
              "Print 2 clamp bars shared with the cue pod.")

if part in ("all", "pod", "pod_cue"):
    oc.reset()
    base, lid, bar = n.pod_cue_base(), n.pod_cue_lid(), n.pod_bar()
    oc.move(lid, dy=n.POD_CUE_W + 20)
    oc.move(bar, dx=n.POD_CUE_L / 2 + 20)
    oc.finish(
        "node_v1_pod_cue",
        {"node_pod_cue_base": base, "node_pod_cue_lid": lid, "node_pod_clamp_bar": bar},
        spec={"node_pod_cue_base": {"size": (n.POD_CUE_L, n.POD_CUE_W, n.POD_BASE_H)},
              "node_pod_cue_lid": {"size": (n.POD_CUE_L, n.POD_CUE_W, n.POD_LID_T)},
              "node_pod_clamp_bar": {"size": n.POD_BAR}},
        refs=n.pod_cue_refs(), material="PA12", min_wall=1.0,
        notes="Right / cue pod. 1 x Qwiic Buzzer (owned). No battery bay. "
              "4 x M3x30 button head + sealing washers, 4 x M3x6 (bars), 8 x M3x4 inserts, "
              "2 x M4x10 electrodes. Acoustic membrane on the +Y sound port. "
              "Unit #1 uses one buzzer (mono); a second BOB-24474 at 0x5B is optional later.")

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
