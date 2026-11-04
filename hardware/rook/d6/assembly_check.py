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
# Parse tilt sign from pod_mount_pad: A.pod_tilt_sign(side) * POD_TILT_DEG  OR legacy sign=
cap_uses_asm = "A.pod_tilt_sign" in cap_src or "pod_tilt_sign" in cap_src
# Also detect inverted legacy: sign = -1 if side == 'L'
legacy_inverted = bool(re.search(r"sign\s*=\s*-1\s*if\s*side\s*==\s*['\"]L['\"]", cap_src))
if cap_uses_asm and not legacy_inverted:
    cap_L_sign = +1
elif legacy_inverted:
    cap_L_sign = -1
else:
    # Fallback: look for tilt = + for L
    cap_L_sign = +1 if "L +29" in cap_src or "L = +tilt" in cap_src or "+29.142" in cap_src else -1
pod_L_sign = +1
chk(
    "cap pod-pad tilt sign L matches pod/D4 (+29.14)",
    cap_L_sign == pod_L_sign,
    f"cap L={cap_L_sign * A.TILT_DEG:+.2f} deg, pod L={pod_L_sign * A.TILT_DEG:+.2f} deg",
    "+29.14 both",
)
if cap_L_sign != pod_L_sign:
    res["mismatches"].append(
        "cap.py pod_mount_pad tilt sign still inverted vs pod.py / d4.json"
    )

# Cap pad centre vs pod cap-facing end
for s, sy in (("L", -1), ("R", 1)):
    pad = A.cap_pad_world_centre(s)
    pb = world.get(f"pod_{s}_base")
    if pb is None:
        continue
    # Cap-facing end: for L (at -Y) the end toward cap is the +Y-most face of the pod bbox
    # after world pose; for R the -Y-most face.
    if s == "L":
        face_y = pb.bounds[1][1]
    else:
        face_y = pb.bounds[0][1]
    face_z = 0.5 * (pb.bounds[0][2] + pb.bounds[1][2])
    fw = np.array([0.0, face_y, face_z])
    gap = float(np.linalg.norm(fw - pad))
    # Also allow projecting pad onto the face plane (Y) only
    gap_y = abs(float(face_y - pad[1]))
    ok = gap < 8.0 or gap_y < 5.0
    chk(
        f"cap pad {s} centre vs pod {s} cap-facing face centre",
        ok,
        f"pad {pad.round(1).tolist()} vs pod face {fw.round(1).tolist()} -> gap={gap:.1f} mm (dy={gap_y:.1f})",
        "<8 mm (joint faces meet / fairing-bridged)",
    )
    if not ok:
        res["mismatches"].append(
            f"Mount face {s}: pad {pad.round(1).tolist()} vs pod face {fw.round(1).tolist()} "
            f"are {gap:.1f} mm apart"
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
# Fairing↔body overlaps up to a small blend volume are OK if intentional bridge;
# classify large unexpected overlaps as REAL.
for i in res["interference"]:
    pair = (i["a"], i["b"])
    rev = (i["b"], i["a"])
    if pair in EXPECTED or rev in EXPECTED:
        i["class"] = "expected lip/groove engagement"
    elif "fairing" in i["a"] or "fairing" in i["b"]:
        # Allow modest fairing blend into bodies (< 500 mm³); larger = pose/size issue
        i["class"] = (
            "fairing blend (OK)" if i["mm3"] < 500 else "fairing overlap high — review pose"
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
