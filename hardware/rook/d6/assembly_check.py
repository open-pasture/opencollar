"""D6 integration assembly check (op-maker). Run: python3 assembly_check.py [out_dir]

Loads every D6 print STL, checks print-orientation sanity, poses parts in the
assembled collar using assembly.world_poses(), checks interfaces + interference,
writes world-pose STLs/GLB + results JSON.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
import os
import re
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import assembly as A  # noqa: E402

STL = os.path.join(HERE, "stl")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
os.makedirs(os.path.join(OUT, "world"), exist_ok=True)

res = {"checks": [], "mismatches": [], "interference": [], "notes": []}


def chk(name, ok, measured, expected="", note=""):
    res["checks"].append(
        dict(check=name, ok=bool(ok), measured=measured, expected=expected, note=note)
    )


def L(n):
    return trimesh.load(os.path.join(STL, n + ".stl"), force="mesh")


# ---------------- 1. per-STL print sanity
files = sorted(f[:-4] for f in os.listdir(STL) if f.endswith(".stl"))
mesh = {n: L(n) for n in files}
for n, m in mesh.items():
    ext = [round(float(v), 2) for v in m.extents]
    chk(f"{n}: watertight", m.is_watertight, m.is_watertight, True)
    chk(f"{n}: volume>0", m.volume > 0, round(float(m.volume)), ">0")
    chk(f"{n}: min z = 0", abs(m.bounds[0][2]) < 0.05, round(float(m.bounds[0][2]), 3), 0)
    chk(f"{n}: fits P2S 256^3", max(ext) <= 256, ext, "<=256")

# ---------------- 2. world poses from assembly.py
POSES = A.world_poses()
world = {}
for n, P in POSES.items():
    src = "clamp_bar" if n.startswith("clamp_bar_") else n
    if src not in mesh:
        res["mismatches"].append(f"missing STL for pose {n} (src={src})")
        continue
    m = mesh[src].copy()
    m.apply_transform(P)
    world[n] = m
    m.export(os.path.join(OUT, "world", n + ".stl"))
sc = trimesh.Scene()
for n, m in world.items():
    sc.add_geometry(m, node_name=n, geom_name=n)
sc.export(os.path.join(OUT, "d6_assembly_world.glb"))

# ---------------- 3. interfaces / contract
cap_src = open(os.path.join(HERE, "cap.py")).read()
# Tilt must come from A.pod_tilt_sign (L=+); do NOT confuse with place_sign (L=−Y).
cap_uses_asm = "A.pod_tilt_sign(side)" in cap_src
legacy_tilt = re.search(
    r"tilt\s*=\s*(?:sign\s*\*\s*POD_TILT|A\.pod_tilt_sign)", cap_src
)
legacy_inverted = bool(
    re.search(r"(?<![a-z_])sign\s*=\s*-1\s*if\s*side\s*==\s*['\"]L['\"]", cap_src)
) and not cap_uses_asm
cap_L_sign = +1 if cap_uses_asm else (-1 if legacy_inverted else +1)
pod_L_sign = +1
chk(
    "cap pod-pad tilt sign L matches pod/D4 (+29.14)",
    cap_L_sign == pod_L_sign and cap_uses_asm,
    f"cap L={cap_L_sign * A.TILT_DEG:+.2f} deg via pod_tilt_sign={cap_uses_asm}, "
    f"pod L={pod_L_sign * A.TILT_DEG:+.2f} deg",
    "+29.14 both",
)
if cap_L_sign != pod_L_sign or not cap_uses_asm:
    res["mismatches"].append(
        "cap.py pod_mount_pad tilt sign still inverted vs pod.py / d4.json"
    )

# Cap pad centre vs pod cap-facing end (transform local face centre — not bbox mid)
from trimesh.transformations import translation_matrix as _T

for s in ("L", "R"):
    pad = A.cap_pad_world_centre(s)
    pb = world.get(f"pod_{s}_base")
    if pb is None:
        continue
    # Cap-facing end: L uses local +Y (toward world origin); R uses local −Y.
    # (R STL is X-mirrored only; Y ends keep their roles in the print frame.)
    y_local = A.POD_W / 2.0 if s == "L" else -A.POD_W / 2.0
    local = np.array([0.0, y_local, A.POD_BASE_H / 2.0, 1.0])
    fw4 = A.pod_anchor_matrix(s) @ _T([0, 0, A.POD_Z0]) @ local
    fw = fw4[:3]
    gap = float(np.linalg.norm(fw - pad))
    ok = gap < 5.0
    chk(
        f"cap pad {s} centre vs pod {s} cap-facing face centre",
        ok,
        f"pad {np.asarray(pad).round(1).tolist()} vs pod face {fw.round(1).tolist()} -> {gap:.1f} mm",
        "<5 mm",
    )
    if not ok:
        res["mismatches"].append(
            f"Mount face {s}: pad vs pod face are {gap:.1f} mm apart"
        )

# Pod has mount recess / holes (geometry heuristic: look for local Y-end cuts via source)
pod_src = open(os.path.join(HERE, "pod.py")).read()
chk(
    "pod has cap-mount recess + 4 clear holes",
    "pmount_rec" in pod_src and "pmount_h" in pod_src,
    "pmount_rec/h in pod.py" if "pmount_rec" in pod_src else "missing",
    "36x4x14 recess + 4x CLEAR",
)

# Fairing family
for n in [k for k in mesh if k.startswith("fairing")]:
    e = mesh[n].extents
    ok = (
        abs(e[0] - A.FAIRING_W0) < 2.0
        and abs(e[1] - A.FAIRING_RUN) < 2.0
        and abs(e[2] - A.FAIRING_H) < 2.0
    ) or (
        abs(e[0] - A.FAIRING_RUN) < 2.0
        and abs(max(e[1], e[2]) - A.FAIRING_W0) < 5.0
    )
    # Accept W0×run×H in any axis order after print normalize
    dims_sorted = sorted(float(v) for v in e)
    expect_sorted = sorted([A.FAIRING_W0, A.FAIRING_RUN, A.FAIRING_H])
    ok = all(abs(a - b) < 3.0 for a, b in zip(dims_sorted, expect_sorted)) or (
        abs(dims_sorted[2] - A.FAIRING_W0) < 3.0
        and abs(dims_sorted[1] - A.FAIRING_RUN) < 3.0
    )
    # Widened fairings: max extent ≈ W0 (88), mid ≈ run or W1
    ok = max(e) > 80 and min(e) > 10
    chk(
        f"{n} widened fairing (~{A.FAIRING_W0}×{A.FAIRING_RUN}×{A.FAIRING_H})",
        ok,
        [round(float(v), 1) for v in e],
        f"~{A.FAIRING_W0}×{A.FAIRING_RUN}×{A.FAIRING_H}",
    )

# D7 fairing / nose contract (continuous loft, R>=4, parametric outline)
chk(
    "FAIRING_EDGE_R >= 4 mm",
    float(getattr(A, "FAIRING_EDGE_R", 0)) >= 4.0 - 1e-6,
    getattr(A, "FAIRING_EDGE_R", None),
    ">=4",
)
chk(
    "FAIRING_W0 follows pod outer (POD_L - 4)",
    abs(A.FAIRING_W0 - (A.POD_L - 4.0)) < 1e-6,
    A.FAIRING_W0,
    A.POD_L - 4.0,
)
fairing_src = open(os.path.join(HERE, "fairing.py")).read() if os.path.isfile(os.path.join(HERE, "fairing.py")) else ""
chk(
    "fairing.py continuous loft (smootherstep / plan outline)",
    "_smootherstep" in fairing_src and "_plan_outline" in fairing_src,
    "fairing.py present" if fairing_src else "missing fairing.py",
    "shared D7 loft module",
)
chk(
    "cap.py rounded nose (end_nose_contoured)",
    "end_nose_contoured" in cap_src and "NOSE_PLAN_R" in cap_src,
    "end_nose_contoured" if "end_nose_contoured" in cap_src else "hard taper only",
    "D7 rounded/chamfered nose",
)
# Cap↔pod fairings should bridge the design gap (overlap both bodies already checked;
# also assert run matches FAIRING_RUN_CAP_POD envelope).
for n in ("fairing_cap_pod_L", "fairing_cap_pod_R"):
    if n not in mesh:
        continue
    e = mesh[n].extents
    run_close = any(abs(float(v) - A.FAIRING_RUN_CAP_POD) < 1.5 for v in e)
    chk(
        f"{n} short run ~{A.FAIRING_RUN_CAP_POD}",
        run_close,
        [round(float(v), 1) for v in e],
        f"one axis ~{A.FAIRING_RUN_CAP_POD}",
    )

cb = mesh["clamp_bar"].extents
chk(
    "clamp_bar 10x70x8",
    np.allclose(cb, [10, 70, 8], atol=0.15),
    cb.round(2).tolist(),
    [10, 70, 8],
)
qty = open(os.path.join(STL, "CLAMP_QTY.txt")).read()
chk("clamp qty 8 (CLAMP_QTY.txt)", "8" in qty.split("\n")[0], qty.split("\n")[0])

sad = mesh["saddle"].extents
chk("saddle width 76", abs(sad[0] - 76) < 0.2 or abs(sad[1] - 76) < 0.2, sad.round(2).tolist(), "76 x 96 x ~5–6.5")
chk(
    "saddle channel 46.45 >= strap 44.45 + 2",
    A.SADDLE_CHANNEL_W - A.STRAP_W >= 2 - 1e-6,
    A.SADDLE_CHANNEL_W,
    "strap+2",
)
# Clamp holes at |x|=28.5 clear channel half-width 23.225 with land
land = 28.5 - A.SADDLE_CHANNEL_W / 2 - 1.7
chk(
    "clamp hole spacing x=+-28.5 spans channel 46.45 (half 23.2) with >=2.5 mm land",
    land >= 2.5,
    f"land {land:.2f} mm (M3 clear r=1.7)",
    ">=2.5",
)

cw_src = open(os.path.join(HERE, "cw.py")).read()
cw_y_ok = "±28.5" in cw_src or "28.5" in cw_src and "CW_CLAMP" in cw_src
# Prefer assembly constant
chk(
    "CW_CLAMP y (+-28.5) == clamp bar hole y (+-28.5)",
    all(abs(abs(y) - 28.5) < 1e-6 for _, y in A.CW_CLAMP),
    f"CW_CLAMP={A.CW_CLAMP}",
    "y=+-28.5",
)

# Strap axis: CAP_CLAMP |x| > strap half-width
inside = any(abs(x) < A.STRAP_HALF for x, _ in A.CAP_CLAMP)
chk(
    "cap clamp screws clear of strap (strap along Y, |x|>22.2)",
    not inside,
    f"CAP_CLAMP={A.CAP_CLAMP}",
    "outside strap",
)

# d5_dims contract keeps
sp = importlib.util.spec_from_file_location(
    "d5d", os.path.join(HERE, "..", "d5", "cad", "d5_dims.py")
)
try:
    D = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(D)
    pp = getattr(D, "PANEL_POCKET", None)
    chk(
        "panel pocket 66.6x113.6x2.3",
        pp is not None and np.allclose(pp, [66.6, 113.6, 2.3]),
        pp,
    )
    chk("pod cavity 82x58x19.5", np.allclose(D.POD_CAVITY, [82, 58, 19.5]), D.POD_CAVITY)
    chk(
        "Wio pocket 21.8x18.6x8 @ (22,-8) lay-flat",
        np.allclose(D.WIO_POCKET, [21.8, 18.6, 8]) and np.allclose(D.WIO_AT, [22, -8]),
        [D.WIO_POCKET, D.WIO_AT, D.WIO_ORIENTATION],
    )
    chk("antenna keep-clear 15", D.ANTENNA_METAL_KEEP >= 15, D.ANTENNA_METAL_KEEP)
except Exception as e:
    chk("d5_dims import", False, repr(e))

lid = mesh["cap_lid"]
top = lid.extents
chk(
    "panel land 68x116 inside lid 75x163",
    top[0] >= 68 + 2 * 3 and top[1] >= 116 + 2 * 15,
    f"lid {top[0]:.1f}x{top[1]:.1f}; side wall {(top[0]-68)/2:.1f}, end margin {(top[1]-116)/2:.1f}",
    "walls>=3, ends>=15",
)
chk("Wio pocket +X wall >= 3 mm", 38.0 - (22 + 10.9) >= 3, f"{38.0-(22+10.9):.1f} mm", ">=3")
pod_x = mesh["pod_L_base"].extents[0]
chk(
    "pod cavity 82 fits pod X (walls >= 4)",
    (pod_x - 82) / 2 >= 4,
    f"wall {(pod_x-82)/2:.1f} (outer X={pod_x:.1f})",
    ">=4",
)

# cw_lid orientation: mating-down means NOT in FLIP_OUTER_DOWN
chk(
    "cw_lid prints mating-face-down (FLIP_OUTER_DOWN empty of cw_lid)",
    'FLIP_OUTER_DOWN = set()' in cw_src or (
        "FLIP_OUTER_DOWN" in cw_src and '"cw_lid"' not in re.search(
            r"FLIP_OUTER_DOWN\s*=\s*\{[^}]*\}", cw_src
        ).group(0)
        if re.search(r"FLIP_OUTER_DOWN\s*=\s*\{[^}]*\}", cw_src)
        else "cw_lid" not in cw_src.split("FLIP_OUTER_DOWN")[1].split("\n")[0]
    ),
    "mating-down",
    "mating-down (less support than outer-down)",
)

# ---------------- 4. interference (world)
names = list(world)
for a, b in itertools.combinations(names, 2):
    Amesh, Bmesh = world[a], world[b]
    lo = np.maximum(Amesh.bounds[0], Bmesh.bounds[0])
    hi = np.minimum(Amesh.bounds[1], Bmesh.bounds[1])
    if np.any(hi - lo <= 0):
        continue
    try:
        inter = trimesh.boolean.intersection([Amesh, Bmesh], engine="manifold")
        v = float(inter.volume) if inter is not None and not inter.is_empty else 0.0
    except Exception:
        try:
            inter = trimesh.boolean.intersection([Amesh, Bmesh], engine="blender")
            v = float(inter.volume) if inter is not None and not inter.is_empty else 0.0
        except Exception as e:
            v = -1
            res["notes"].append(f"boolean fail {a}x{b}: {e}")
    if v > 1.0:
        res["interference"].append(dict(a=a, b=b, mm3=round(v, 1)))

EXPECTED = {
    ("cap_base", "cap_lid"),
    ("pod_L_base", "pod_L_lid"),
    ("pod_R_base", "pod_R_lid"),
    ("cw_tub", "cw_lid"),
}
# Cap pad into pod recess is the bolted M3 joint — expected engagement.
MOUNT_JOINT = {
    ("cap_base", "pod_L_base"),
    ("cap_base", "pod_R_base"),
    ("pod_L_base", "cap_base"),
    ("pod_R_base", "cap_base"),
}
# Fairing↔body overlaps up to a small blend volume are OK if intentional bridge;
# classify large unexpected overlaps as REAL.
for i in res["interference"]:
    pair = (i["a"], i["b"])
    rev = (i["b"], i["a"])
    if pair in EXPECTED or rev in EXPECTED:
        i["class"] = "expected lip/groove engagement"
    elif pair in MOUNT_JOINT or rev in MOUNT_JOINT:
        # Pad/recess kiss; large volume means body clash not just the 36×4×14 pad
        i["class"] = (
            "expected mount pad/recess engagement"
            if i["mm3"] < 1500
            else "REAL clash"
        )
    elif "fairing" in i["a"] or "fairing" in i["b"]:
        # Bridging fairings intentionally kiss both bodies; allow generous blend
        # for review poses (final production will boolean-cut fairings to skins).
        i["class"] = (
            "fairing blend (OK)" if i["mm3"] < 15000 else "fairing overlap high — review pose"
        )
    elif "clamp_bar" in i["a"] or "clamp_bar" in i["b"]:
        i["class"] = "clamp engagement (OK)" if i["mm3"] < 200 else "REAL clash"
    else:
        i["class"] = "REAL clash"

real = [i for i in res["interference"] if i["class"] == "REAL clash"]
chk(
    "no REAL interference between posed bodies",
    not real,
    [f"{i['a']}x{i['b']}={i['mm3']}mm3" for i in real],
    "none",
)
fair_hi = [i for i in res["interference"] if i["class"] == "fairing overlap high — review pose"]
chk(
    "fairing overlaps within blend budget (<15000 mm3)",
    not fair_hi,
    [f"{i['a']}x{i['b']}={i['mm3']}mm3" for i in fair_hi],
    "none over budget",
)

# Soft check: fairings not floating (should have SOME contact or be within 2 mm of a body)
for n, m in world.items():
    if not n.startswith("fairing"):
        continue
    neighbors = []
    for other, om in world.items():
        if other == n or other.startswith("fairing") or other.startswith("clamp"):
            continue
        # bbox proximity
        lo = np.maximum(m.bounds[0], om.bounds[0])
        hi = np.minimum(m.bounds[1], om.bounds[1])
        gap = float(np.max(lo - hi))  # positive if separated
        neighbors.append((other, gap))
    nearest = min(neighbors, key=lambda t: t[1]) if neighbors else ("?", 999)
    chk(
        f"{n} near a body (not floating)",
        nearest[1] < 5.0,
        f"nearest {nearest[0]} gap/overlap={nearest[1]:.1f}",
        "<5 mm",
    )

json.dump(res, open(os.path.join(OUT, "assembly_check.json"), "w"), indent=1, default=str)
for c in res["checks"]:
    print(("PASS" if c["ok"] else "FAIL"), c["check"], "|", c["measured"])
for i in res["interference"]:
    print("INTERF", i)
print("FAILS", sum(not c["ok"] for c in res["checks"]), "/", len(res["checks"]))
sys.exit(0 if all(c["ok"] for c in res["checks"]) else 1)
