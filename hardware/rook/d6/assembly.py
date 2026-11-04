"""D6 shared assembly constants and world poses (integrator).

Frame: origin at cap centre; X across strap width; Y along spine/strap; Z up; mm.
Print STLs stay in print orientation; this module only defines the assembled pose.

Strap-path decision (see DECISIONS.md):
  D4 / contract put the strap along Y. D5 CAP_CLAMP was (±20, ±28.5) — a
  cross-strap layout that would pierce the 44.45 mm strap when the channel
  runs along Y. D6 rotates the family to CAP_CLAMP = (±28.5, ±20) so the
  M3 inserts sit outside the strap (|x|=28.5 > 22.225) and the saddle
  channel is 46.45 wide in X × run along Y. Clamp bars stay 10×70×8 with
  holes at ±28.5 along the bar; under the cap/saddle they are rotated 90°
  about Z so those holes land on x=±28.5. CW tub pitch Y matches the bars
  at ±28.5 (was ±29.5).
"""
from __future__ import annotations

import math

import numpy as np

# ---------------------------------------------------------------- D4 anchors (d4.json) + D6 shifts

TILT_DEG = 29.141828721535205
TILT = math.radians(TILT_DEG)

# D4 pod anchors were ±113.830 / −27.839. D6 grows the pod X to 92 (D5 cavity
# 82 + 2×5 walls) so the D4 anchors clash with the 76×164 cap. Shift outboard
# along the strap (~10 mm) for a 2–3 mm fairing-bridged body gap while the
# bolted pad faces still meet.
# Outboard of D4 ±113.8 so the 92 mm-wide D6 pods clear the 164 mm cap body
# with a ~2–3 mm fairing-bridged gap; pad/recess still meet (joint engagement).
POD_ANCHOR_Y = 126.0
# Raised from D4 −27.839 so the cap-facing end meets the print-safe pad
# (pad local z = CAP_FLOOR+5; must stay above bed after ±29° tilt).
POD_ANCHOR_Z = -21.9
POD_Z0 = -4.3
POD_BASE_H = 22.2          # as-exported mating plane (tip roof drops below); cavity still 19.5
POD_LID_T = 4.2            # as-exported lid thickness (~4.0 modeled + ribs)
POD_L = 92.0               # max X = cell swell (tips taper to ~70 toward D4's 67)
POD_X_END = 70.0           # tip width from pod.py (R≥8 → reads ~66–68)
POD_W = 92.0               # along strap — LOCKED for mount face at ±POD_W/2 (D4 was 97)
POD_FLOOR = 1.5
POD_PLAN_R = 8.0           # outer tip plan R (pod.py PLAN_R)

CAP_Z0 = -3.6              # D4 cap_base world min z
CAP_BASE_H = 19.0
CAP_W = 76.0
CAP_L = 164.0

CW_ANCH_Z = -465.75
CW_Z0 = -3.2
# D7 CW: 2×2 steel pack → longer along strap / shallower (was 88×74×30)
CW_TUB_H = 18.0
CW_LID_T = 7.5
CW_L, CW_W = 89.4, 115.8

STRAP_W = 44.45
STRAP_T = 3.4              # channel depth family (SADDLE_CHANNEL_D)
STRAP_HALF = STRAP_W / 2.0  # 22.225

# Cap↔pod M3 joint (shared by cap.py pad + pod.py recess)
POD_MOUNT_SIZE = (36.0, 4.0, 14.0)   # W × thickness × H
POD_MOUNT_SCREWS = [(sx * 10.0, sz) for sx in (-1, 1) for sz in (3.0, 10.0)]
CLEAR = 3.4

# Strap-along-Y clamp family (replaces D5 CAP_CLAMP (±20, ±28.5) for D6)
CAP_CLAMP = [(sx * 28.5, sy * 20.0) for sx in (-1, 1) for sy in (-1, 1)]
# CW tub / lid: keep X=±36 (bar stations); unify Y with clamp_bar holes
CW_CLAMP = [(sx * 36.0, sy * 28.5) for sx in (-1, 1) for sy in (-1, 1)]
CLAMP_HOLE_PITCH_Y = 28.5
CLAMP_BAR = (10.0, 70.0, 8.0)
CLAMP_QTY = 8

SADDLE_W = 76.0
SADDLE_L = 96.0
SADDLE_CHANNEL_W = STRAP_W + 2.0   # 46.45 — across X
SADDLE_CHANNEL_D = STRAP_T
SADDLE_ROOF = 1.6
SADDLE_H = SADDLE_ROOF + SADDLE_CHANNEL_D

# Fairings (D7 continuous wedge) — re-loft from slim pod tip + D7 CW.
# Cap–pod / pod–strap kiss the ~70 mm tip (not the 92 mm swell). CW fairings
# kiss CW_L≈89.4 and run into the saddle with no step.
FAIRING_POD_OUTER_X = POD_L              # 92 swell (reference)
FAIRING_POD_TIP_X = POD_X_END            # 70 — actual join width at ±Y ends
FAIRING_POD_OUTER_Y = POD_W
FAIRING_POD_PLAN_R = POD_PLAN_R          # 8
FAIRING_CAP_W = CAP_W                    # 76
FAIRING_CAP_PLAN_R = 7.0
FAIRING_CW_OUTER = CW_L                  # 89.4
FAIRING_RUN = 28.0
FAIRING_RUN_CAP_POD = 18.0
FAIRING_RUN_CW = 32.0                    # longer blend saddle ↔ lower CW
# Default W0/W1 follow the slim tip; fairing_cw() overrides W0 to CW outer.
FAIRING_W0 = FAIRING_POD_TIP_X           # 70 — wide end = slim tip (no plan step)
FAIRING_W1 = 56.0                        # narrow end toward strap / mate
FAIRING_W0_CW = FAIRING_CW_OUTER         # 89.4 — wide end = CW outer (no plan step)
FAIRING_W1_CW = FAIRING_W1               # 56
FAIRING_H = 14.0                         # match mount-pad height (36×4×14)
FAIRING_H_CW = 12.0                      # lower D7 CW face band
FAIRING_EDGE_R = 4.0
# Edge bevel pulls the plan silhouette in ~0.5–0.7 mm; oversize the loft so the
# finished outer width still kisses POD_X_END / CW_L (seam ≤ FAIRING_SEAM_STEP_MAX).
FAIRING_BEVEL_OVERSIZE = 0.75
FAIRING_PLAN_R0 = max(FAIRING_POD_PLAN_R, 8.0)
FAIRING_PLAN_R1 = max(FAIRING_CAP_PLAN_R, 6.0)
FAIRING_TOP_CROWN = 1.2
FAIRING_INTERFERE_TOL = 0.2
FAIRING_SEAM_STEP_MAX = 0.5              # mm — no visible step at fairing joins
FAIRING_CAP_POD_GAP = 1.3

# Explicit world centres — bridge the 1.3 mm joint; CW beside longer tub.
FAIRING_CENTRES = {
    "fairing_cap_pod_L": (0.0, -85.5, 7.4),
    "fairing_cap_pod_R": (0.0, 85.5, 7.4),
    "fairing_pod_strap_L": (0.0, -178.0, -36.0),
    "fairing_pod_strap_R": (0.0, 178.0, -36.0),
    # CW half-length ≈57.9; place just outboard so the wedge kisses tub + saddle
    # CW tub world top after pose ≈ -462.6; centre fairing mid-height there
    "fairing_cw_L": (0.0, 70.0, -468.5),
    "fairing_cw_R": (0.0, -70.0, -468.5),
}
# Back-compat alias
D4_FAIRING_CENTRES = FAIRING_CENTRES


def pod_tilt_sign(side: str) -> float:
    """L = +29.142°, R = −29.142° (matches pod.py / d4.json)."""
    return +1.0 if side == "L" else -1.0


def pod_anchor_matrix(side: str):
    """4×4 world matrix for the pod anchor empty (numpy)."""
    from trimesh.transformations import rotation_matrix as R
    from trimesh.transformations import translation_matrix as T
    s = -1.0 if side == "L" else 1.0
    # L: +tilt about X; R: −tilt about X
    return T([0.0, s * POD_ANCHOR_Y, POD_ANCHOR_Z]) @ R(
        math.radians(-s * TILT_DEG), [1, 0, 0]
    )


def cap_pad_world_centre(side: str):
    """Approximate cap mount-pad centre in world (for joint checks)."""
    s = -1.0 if side == "L" else 1.0
    # Matches cap.py: y = ±POD_MOUNT_FACE_Y, z = CAP_FLOOR+5 (+ CAP_Z0).
    y = s * 88.3
    z = CAP_Z0 + 11.0
    return np.array([0.0, y, z], dtype=float)


def world_poses():
    """Name → 4×4 pose for every assembled body (print-STL → world)."""
    from trimesh.transformations import rotation_matrix as R
    from trimesh.transformations import translation_matrix as T

    X = [1, 0, 0]
    Zax = [0, 0, 1]
    poses = {
        "cap_base": T([0, 0, CAP_Z0]),
        "cap_lid": T([0, 0, CAP_Z0 + CAP_BASE_H]),
        # Saddle STL: channel along Y (width X); roof was bed → flip 180 X so roof
        # sits under the cap, no extra Z rot needed for strap-along-Y.
        "saddle": T([0, 0, CAP_Z0]) @ R(math.pi, X),
    }
    for side in ("L", "R"):
        A = pod_anchor_matrix(side)
        poses[f"pod_{side}_base"] = A @ T([0, 0, POD_Z0])
        poses[f"pod_{side}_lid"] = (
            A @ T([0, 0, POD_Z0 + POD_BASE_H]) @ R(math.pi, X) @ T([0, 0, -POD_LID_T])
        )

    CWA = T([0, 0, CW_ANCH_Z]) @ R(math.pi, X)
    poses["cw_tub"] = CWA @ T([0, 0, CW_Z0])
    # cw_lid now prints mating-down (= assembled pose), same as cap_lid
    poses["cw_lid"] = CWA @ T([0, 0, CW_Z0 + CW_TUB_H])

    # Fairings at explicit bridge centres. Print STL has bed at z=0..H; place so
    # the mid-height sits at the centre, then tilt about that centre (not origin).
    for name, (x, y, z) in FAIRING_CENTRES.items():
        h = FAIRING_H_CW if "fairing_cw" in name else FAIRING_H
        # T_center @ R @ T_to_local_origin : rotate about mid-height, then place
        P = T([x, y, z]) @ T([0, 0, h / 2.0])
        if "cap_pod_L" in name:
            P = P @ R(math.radians(+TILT_DEG), X)
        elif "cap_pod_R" in name:
            P = P @ R(math.radians(-TILT_DEG), X)
        P = P @ T([0, 0, -h / 2.0])
        poses[name] = P

    # Clamp bars ×8
    # 2 under cap saddle: long axis along X (holes → x=±28.5), at y=±20
    bars = []
    for y in (-20.0, 20.0):
        bars.append(
            T([0, y, CAP_Z0 - SADDLE_H - STRAP_T - CLAMP_BAR[2]])
            @ R(math.pi / 2, Zax)
        )
    # 2 per pod: along local X after tilt
    for side in ("L", "R"):
        A = pod_anchor_matrix(side)
        for dy in (-25.0, 25.0):
            bars.append(
                A
                @ T([0, dy, POD_Z0 - STRAP_T - CLAMP_BAR[2]])
                @ R(math.pi / 2, Zax)
            )
    # 2 under CW: long axis along Y (no Z rot) — holes at y=±28.5, bars at x=±36
    for x in (-36.0, 36.0):
        bars.append(CWA @ T([x, 0, CW_Z0 - STRAP_T - CLAMP_BAR[2]]))
    for i, B in enumerate(bars):
        poses[f"clamp_bar_{i + 1}"] = B
    return poses
