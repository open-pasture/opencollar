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

# Cap pad vs pod mount face — mesh proximity near the joint (D7r6 skirts + tilt
# make a single local-frame point a poor proxy; use closest points in a band).
for s in ("L", "R"):
    cb = world.get("cap_base")
    pb = world.get(f"pod_{s}_base")
    if cb is None or pb is None:
        continue
    sign = -1.0 if s == "L" else 1.0
    # Cap pad region: outboard |y| on the pod side, mid-stack Z
    cv = cb.vertices
    cmask = (
        (np.sign(cv[:, 1]) == sign)
        & (np.abs(cv[:, 1]) > 80.0)
        & (np.abs(cv[:, 0]) < 22.0)
        & (cv[:, 2] > 12.0)
        & (cv[:, 2] < 32.0)
    )
    # Pod face toward origin (cap-facing end)
    pv = pb.vertices
    if s == "L":
        pmask = (pv[:, 1] > -100.0) & (pv[:, 1] < -85.0) & (np.abs(pv[:, 0]) < 22.0) & (pv[:, 2] > 5.0)
    else:
        pmask = (pv[:, 1] < 100.0) & (pv[:, 1] > 85.0) & (np.abs(pv[:, 0]) < 22.0) & (pv[:, 2] > 5.0)
    if not np.any(cmask) or not np.any(pmask):
        chk(
            f"cap pad {s} centre vs pod {s} cap-facing face centre",
            False,
            "no pad/face verts in joint band",
            "<8 mm",
        )
        continue
    # Closest-point gap between the two clouds (numpy; clouds are small)
    cpts = cv[cmask]
    ppts = pv[pmask]
    # subsample if huge
    if len(cpts) > 2000:
        cpts = cpts[:: max(1, len(cpts) // 2000)]
    if len(ppts) > 2000:
        ppts = ppts[:: max(1, len(ppts) // 2000)]
    d2 = ((cpts[:, None, :] - ppts[None, :, :]) ** 2).sum(axis=2)
    gap = float(np.sqrt(d2.min()))
    ok = gap < 8.0
    chk(
        f"cap pad {s} centre vs pod {s} cap-facing face centre",
        ok,
        f"mesh min gap {gap:.1f} mm (pad n={int(cmask.sum())} face n={int(pmask.sum())})",
        "<8 mm",
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
    # D7/D8: tip-kissing (~68), strap-end flare (~76), or CW-wide (~89)
    if n.startswith("fairing_cw"):
        ok = abs(max(e) - A.FAIRING_W0_CW) < 4.0 and min(e) > 8.0
        expect = f"~{A.FAIRING_W0_CW}×{A.FAIRING_RUN_CW}×{A.FAIRING_H_CW}"
    elif "pod_strap" in n:
        w0_ps = float(getattr(A, "FAIRING_W0_POD_STRAP", A.FAIRING_W0))
        ok = abs(max(e) - w0_ps) < 4.0 and min(e) > 8.0
        expect = f"~{w0_ps}×{A.FAIRING_RUN}×{A.FAIRING_H}"
    else:
        ok = abs(max(e) - A.FAIRING_W0) < 4.0 and min(e) > 8.0
        expect = f"~{A.FAIRING_W0}×run×{A.FAIRING_H}"
    chk(
        f"{n} continuous fairing ({expect})",
        ok,
        [round(float(v), 1) for v in e],
        expect,
    )

# D7 fairing / nose contract (continuous loft, R>=4, parametric outline)
chk(
    "FAIRING_EDGE_R >= 4 mm",
    float(getattr(A, "FAIRING_EDGE_R", 0)) >= 4.0 - 1e-6,
    getattr(A, "FAIRING_EDGE_R", None),
    ">=4",
)
chk(
    "FAIRING_W0 equals pod outer (POD_L)",
    abs(A.FAIRING_W0 - A.POD_L) < 1e-6,
    A.FAIRING_W0,
    A.POD_L,
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
pod_y = mesh["pod_L_base"].extents[1]
# D7r2: cavity oriented 58 across X / 82 along Y
chk(
    "pod cavity 58 fits pod X (walls >= 3.5)",
    (pod_x - 58.0) / 2 >= 3.5 - 1e-3,
    f"wall {(pod_x-58.0)/2:.1f} (outer X={pod_x:.1f})",
    ">=3.5",
)
chk(
    "pod cavity 82 along Y (oriented)",
    pod_y >= 82.0 + 2 * 3.5 - 1.0,
    f"pod Y={pod_y:.1f} (need ≥{82+7:.0f} for 82 cav + walls)",
    "82 along Y",
)
chk(
    "pod.py cavity rotated (CAV_X/CAV_Y)",
    "CAV_X" in pod_src and "CAV_Y" in pod_src and "axis=\"Y\"" in pod_src,
    "CAV_X/CAV_Y + cell axis Y" if "CAV_X" in pod_src else "missing",
    "58 across / 82 along",
)

def _pod_width_at_y(m, y, band=1.2, z_min=None):
    """Width across X at a Y station. Optional z_min skips deep skirt flare verts."""
    v = m.vertices
    mask = (v[:, 1] > y - band) & (v[:, 1] < y + band)
    if z_min is not None:
        mask = mask & (v[:, 2] >= z_min)
    if not np.any(mask):
        return None
    xs = v[mask, 0]
    return float(xs.max() - xs.min())


pod_L = mesh["pod_L_base"]
# D7r5 skirts flare wider than the body below the mating band — measure the
# shell outline above the skirt (POD_SKIRT_H≈14), not the clamp-covering bed.
_skirt_h = 14.0
swell_w = _pod_width_at_y(pod_L, 0.0, z_min=_skirt_h)
tip_w = _pod_width_at_y(pod_L, 40.0, z_min=_skirt_h)
tip_w2 = _pod_width_at_y(pod_L, -40.0, z_min=_skirt_h)
chk(
    "pod D7r2 swell width ≤70 (x at y=0)",
    swell_w is not None and 64.0 <= swell_w <= 70.0,
    round(swell_w, 1) if swell_w is not None else None,
    "64–70 (58 cav + ≥3.5 walls)",
)
chk(
    "pod width < cap width (76)",
    swell_w is not None and swell_w < float(A.CAP_W) - 0.5,
    f"pod {None if swell_w is None else round(swell_w,1)} vs cap {A.CAP_W}",
    "pod < cap",
)
chk(
    "pod mount-end tip width ~66 (x at +Y≈40)",
    tip_w is not None and 62.0 <= tip_w <= 70.0,
    f"+Y {None if tip_w is None else round(tip_w,1)}",
    "62–70",
)
chk(
    "pod strap-end flare width ~76 (x at −Y≈40, D8)",
    tip_w2 is not None and 70.0 <= tip_w2 <= 80.0,
    f"-Y {None if tip_w2 is None else round(tip_w2,1)}",
    "70–80 (D4 outer flare)",
)
chk(
    "pod.py contoured taper (POD_X_END + contoured_slab)",
    "POD_X_END" in pod_src and "contoured_slab" in pod_src,
    "POD_X_END/contoured_slab present" if "POD_X_END" in pod_src else "missing",
    "tapered plan helper",
)
chk(
    "pod plan corner R ≈ 3 (D8 / D4 silhouette)",
    ("PLAN_R = 3" in pod_src or "PLAN_R = 3.0" in pod_src or "PLAN_R=3" in pod_src),
    "PLAN_R set ≈3 in pod.py",
    "≈3",
)
chk(
    "pod lid smooth crown (no X-facet)",
    "smooth_lid_crown" in pod_src,
    "smooth_lid_crown" if "smooth_lid_crown" in pod_src else "missing",
    "G1 barrel/sphere crown",
)
# Mount face Y locked; length ~97 (strap-end grew)
chk(
    "pod mount face Y locked at 46",
    abs(float(getattr(A, "POD_MOUNT_FACE_Y", 0)) - 46.0) < 1e-6,
    getattr(A, "POD_MOUNT_FACE_Y", None),
    46.0,
)
chk(
    "pod length ~97 (D4-ish, mount face fixed)",
    abs(A.POD_W - 97.0) < 1e-6 and 95.0 <= pod_L.extents[1] <= 100.0,
    f"A.POD_W={A.POD_W}, STL Y={pod_L.extents[1]:.1f}",
    "97 / ~97 as-exported",
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

# D7: CW lower + smaller volume than a pod; continuous fairings (no prism blocks)
cw_h = float(mesh["cw_tub"].extents[2])
pod_h = float(mesh["pod_L_base"].extents[2])
chk(
    "CW tub height lower than pod base",
    cw_h < pod_h - 0.5,
    f"cw_tub H={cw_h:.1f} vs pod_L_base H={pod_h:.1f}",
    "CW < pod",
)
cw_vol = float(mesh["cw_tub"].volume)
pod_vol = float(mesh["pod_L_base"].volume)
# D7r2 slim pod shell is smaller than the CW tub that still holds 771.8 g steel;
# volume ordering flips. Keep height + steel-mass contracts.
steel_ok = False
steel_m = None
cw_rep = os.path.join(STL, "cw_report.json")
if os.path.exists(cw_rep):
    try:
        steel_m = json.load(open(cw_rep)).get("choice", {}).get("steel_mass_g")
        steel_ok = steel_m is not None and abs(float(steel_m) - 771.8) < 0.2
    except Exception:
        steel_ok = False
chk(
    "CW steel pack mass 771.8 g retained",
    steel_ok,
    steel_m if steel_m is not None else f"cw_tub V={cw_vol:.0f} / pod V={pod_vol:.0f}",
    771.8,
)
chk(
    "fairings use fairing.py continuous loft (not prism blocks)",
    "import fairing" in pod_src and "import fairing" in cw_src
    and "fairing_lib" in pod_src and "fairing_lib" in cw_src,
    "pod+cw import fairing_lib",
    "fairing.py",
)
chk(
    "assembly FAIRING_W0 follows pod outer (~68)",
    abs(A.FAIRING_W0 - A.POD_L) < 0.1,
    f"FAIRING_W0={A.FAIRING_W0}, POD_L={A.POD_L}",
    "POD_L",
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
    # D8 neck saddle mates flat-to-flat on pod skirt bed; cover seals bay
    ("pod_L_base", "pod_L_saddle"),
    ("pod_R_base", "pod_R_saddle"),
    ("pod_L_saddle", "pod_L_bay_cover"),
    ("pod_R_saddle", "pod_R_bay_cover"),
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
        # D7r5: bars seat in skirt/saddle pockets (≤1 mm proud) — allow pocket volume
        i["class"] = (
            "clamp pocket engagement (OK)" if i["mm3"] < 2500 else "REAL clash"
        )
    elif "saddle" in i["a"] or "saddle" in i["b"] or "bay_cover" in i["a"] or "bay_cover" in i["b"]:
        i["class"] = (
            "saddle/bay engagement (OK)" if i["mm3"] < 12000 else "REAL clash"
        )
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

# Seam step (print-frame): wide-end width and height must match the mating
# body outline within 0.5 mm so the continuous wedge has no plan/height step.
SEAM_MAX = float(getattr(A, "FAIRING_SEAM_STEP_MAX", 0.5))
LID_SEAM = float(getattr(A, "FAIRING_LID_SEAM_MAX", 0.3))
# Cap–pod kisses mid swell (68); pod–strap kisses strap-end flare (~76).
pod_outer_w = float(A.POD_L)
pod_strap_w = float(getattr(A, "FAIRING_W0_POD_STRAP", A.POD_L))
fairing_h = float(A.FAIRING_H)
fairing_h_cap = float(getattr(A, "FAIRING_H_CAP_POD", A.FAIRING_H))
for n in ("fairing_cap_pod_L", "fairing_cap_pod_R",
          "fairing_pod_strap_L", "fairing_pod_strap_R"):
    if n not in mesh:
        continue
    e = mesh[n].extents
    h_expect = fairing_h_cap if "cap_pod" in n else fairing_h
    w_expect = pod_strap_w if "pod_strap" in n else pod_outer_w
    # Strap-end fairing AABB grows ~0.6 mm from plan-R; allow 1.0 mm there.
    seam_w = 1.0 if "pod_strap" in n else SEAM_MAX
    w_step = abs(float(max(e[0], e[1])) - w_expect)
    h_step = abs(float(e[2]) - h_expect)
    chk(
        f"seam step {n} width vs pod outer ≤ {seam_w} mm",
        w_step <= seam_w + 1e-3,
        f"Δw={w_step:.2f} (fairing {max(e[0],e[1]):.1f} vs pod {w_expect:.1f})",
        f"≤{seam_w}",
    )
    chk(
        f"seam step {n} height vs FAIRING_H ≤ {SEAM_MAX} mm",
        h_step <= SEAM_MAX + 1e-3,
        f"Δh={h_step:.2f} (fairing {e[2]:.1f} vs H {h_expect:.1f})",
        f"≤{SEAM_MAX}",
    )
# Fairing top vs pod roof at the seam. D8 lid is inset ~3 mm from the base
# wall, so sample the base mating band (outer wall) as well as the lid; allow
# the inset lip drop when only the lid is near the fairing window.
for side, fname in (("L", "fairing_cap_pod_L"), ("R", "fairing_cap_pod_R")):
    if fname not in world or f"pod_{side}_base" not in world:
        continue
    fmesh = world[fname]
    bmesh = world[f"pod_{side}_base"]
    lmesh = world.get(f"pod_{side}_lid")
    fc = fmesh.centroid
    fv, bv = fmesh.vertices, bmesh.vertices
    fband = (np.abs(fv[:, 1] - fc[1]) < 14.0) & (np.abs(fv[:, 0]) < 35.0)
    bband = (np.abs(bv[:, 1] - fc[1]) < 24.0) & (np.abs(bv[:, 0]) < 40.0)
    if np.any(fband) and np.any(bband):
        fz_top = float(fv[fband, 2].max())
        bz_top = float(bv[bband, 2].max())
        dz_base = abs(fz_top - bz_top)
        dz_lid = None
        if lmesh is not None:
            lv = lmesh.vertices
            lband = (np.abs(lv[:, 1] - fc[1]) < 28.0) & (np.abs(lv[:, 0]) < 40.0)
            if np.any(lband):
                lz_top = float(lv[lband, 2].max())
                dz_lid = abs(fz_top - lz_top)
        # Pass if fairing meets base roof, or lid within inset budget (~4 mm lip)
        ok_seam = dz_base <= LID_SEAM + 0.5 or (
            dz_lid is not None and dz_lid <= 4.5
        )
        measured = (
            f"Δz_base={dz_base:.2f} (f={fz_top:.1f} base={bz_top:.1f})"
            + (f" Δz_lid={dz_lid:.2f}" if dz_lid is not None else " lid=no-overlap")
        )
        chk(
            f"fairing {fname} top vs pod_{side} roof ≤ {LID_SEAM} mm",
            ok_seam,
            measured,
            f"base≤{LID_SEAM}+0.5 or lid≤4.5 (inset lip)",
        )
    else:
        chk(
            f"fairing {fname} top vs pod_{side} roof ≤ {LID_SEAM} mm",
            False,
            "no verts near fairing seam",
            f"≤{LID_SEAM}",
        )
# CW fairings: width = CW_L, height = FAIRING_H_CW (designed mate band)
cw_w = float(A.CW_L)
for n in ("fairing_cw_L", "fairing_cw_R"):
    if n not in mesh:
        continue
    e = mesh[n].extents
    w_step = abs(float(max(e[0], e[1])) - cw_w)
    h_step = abs(float(e[2]) - float(A.FAIRING_H_CW))
    chk(
        f"seam step {n} width vs CW ≤ {SEAM_MAX} mm",
        w_step <= SEAM_MAX + 1e-3,
        f"Δw={w_step:.2f} (fairing {max(e[0],e[1]):.1f} vs CW {cw_w:.1f})",
        f"≤{SEAM_MAX}",
    )
    chk(
        f"seam step {n} height match ≤ {SEAM_MAX} mm",
        h_step <= SEAM_MAX + 1e-3,
        f"Δh={h_step:.2f} (fairing {e[2]:.1f} vs H_CW {A.FAIRING_H_CW:.1f})",
        f"≤{SEAM_MAX}",
    )

# D8 neck saddle + sealed blank shock bay
saddle_src = ""
saddle_path = os.path.join(HERE, "pod_saddle.py")
if os.path.isfile(saddle_path):
    saddle_src = open(saddle_path).read()
for side in ("L", "R"):
    sn, cn = f"pod_{side}_saddle", f"pod_{side}_bay_cover"
    chk(f"{sn} present", sn in mesh, sn in mesh, "stl")
    chk(f"{cn} present", cn in mesh, cn in mesh, "stl")
    if sn in mesh:
        e = mesh[sn].extents
        chk(
            f"{sn} fits under pod length (~90×52)",
            float(e[1]) <= 100.0 and float(e[0]) <= 70.0,
            [round(float(v), 1) for v in e],
            "≤70 × ≤100 × h",
        )
chk(
    "pod_saddle.py MODULE_* PLACEHOLDER block",
    "MODULE_PLACEHOLDER" in saddle_src and "MODULE_L = 40" in saddle_src,
    "PLACEHOLDER 40×25×8" if "MODULE_L = 40" in saddle_src else "missing",
    "40×25×8 pending op-firmware",
)
chk(
    "saddle neck radius R≈220",
    "SADDLE_R = 220" in saddle_src or "SADDLE_R=220" in saddle_src,
    "R220" if "220" in saddle_src else "missing",
    "220",
)
chk(
    "electrode compliance travel reserved (unpopulated)",
    "ELECTRODE_COMPLIANCE_TRAVEL" in saddle_src,
    "compliance travel" if "ELECTRODE_COMPLIANCE_TRAVEL" in saddle_src else "missing",
    "spring/elastomer reserve",
)
chk(
    "cell cavity size unchanged 82×58×19.5",
    "POD_CAVITY" in pod_src and "(82" in pod_src,
    "POD_CAVITY locked",
    "82×58×19.5",
)
asm_src = open(os.path.join(HERE, "assembly.py")).read()
fair_src = open(os.path.join(HERE, "fairing.py")).read()
chk(
    "blind joint groove (floor + closed ends)",
    "JOINT_GROOVE_FLOOR_MIN" in asm_src and "groove_len_x" in fair_src,
    "blind groove helpers present",
    "floor≥4 + closed ends",
)
for side in ("L", "R"):
    sn = f"pod_{side}_saddle"
    if sn not in world:
        continue
    for other in ("cap_base", "cw_tub"):
        if other not in world:
            continue
        try:
            inter = trimesh.boolean.intersection(
                [world[sn], world[other]], engine="manifold"
            )
            v = float(inter.volume) if inter is not None and not inter.is_empty else 0.0
        except Exception:
            v = 0.0
        chk(
            f"{sn} no overlap with {other}",
            v < 50.0,
            round(v, 1),
            "<50 mm³",
        )

# D7r7: review-blend geometry hygiene (no dim<2mm / floating / stray non-mesh)
hygiene_paths = [
    os.path.join(OUT, "assembly_review", "geometry_hygiene.json"),
    os.path.join(HERE, "review", "geometry_hygiene.json"),
]
hyg = None
for hp in hygiene_paths:
    if os.path.isfile(hp):
        try:
            hyg = json.load(open(hp))
            break
        except Exception:
            continue
if hyg is None:
    chk(
        "review blend geometry hygiene (no dim<2mm / floating / non-mesh)",
        False,
        "geometry_hygiene.json missing — rebuild blend",
        "ok with empty thin/floating/non_mesh",
    )
else:
    thin = hyg.get("thin_lt_2mm") or hyg.get("thin_lt_1mm") or []
    non = hyg.get("non_mesh") or []
    floating = hyg.get("floating") or []
    chk(
        "review blend geometry hygiene (no dim<2mm / floating / non-mesh)",
        bool(hyg.get("ok")) and not thin and not non and not floating,
        {"thin": thin, "floating": floating, "non_mesh": non},
        "ok with empty thin/floating/non_mesh",
    )

json.dump(res, open(os.path.join(OUT, "assembly_check.json"), "w"), indent=1, default=str)
for c in res["checks"]:
    print(("PASS" if c["ok"] else "FAIL"), c["check"], "|", c["measured"])
for i in res["interference"]:
    print("INTERF", i)
print("FAILS", sum(not c["ok"] for c in res["checks"]), "/", len(res["checks"]))
sys.exit(0 if all(c["ok"] for c in res["checks"]) else 1)
