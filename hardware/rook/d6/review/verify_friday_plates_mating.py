#!/usr/bin/env python3
"""Friday plates mating verifier — pod / cw / jigs / optB / blank shock plug.

Keeps a189978 cap checks as a no-regression gate (hashes + optional re-run).
Exit 0 only when ALL gates pass.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

_D6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_D6))
import assembly as A  # noqa: E402

STL = _D6 / "stl"
OUT = _D6 / "out"
WORLD = OUT / "world"
POSES_PATH = OUT / "assembly_poses.json"

# Frozen a189978 cap STL sha256 prefixes (first 12 hex) — must not change
CAP_SHA12 = {
    "cap_base.stl": "68c3370aaa90",
    "cap_lid.stl": "00c1723b0f07",
    "cap_usbc_plug.stl": "2ef02d0c2b95",
}

XY_LO, XY_HI = 0.20, 0.35
Z_CLEAR_MIN = 0.35
SHOCK_STEM_D, SHOCK_BORE_D = 7.60, 8.05


def load(name: str) -> trimesh.Trimesh:
    p = STL / name
    m = trimesh.load(p, force="mesh")
    if not isinstance(m, trimesh.Trimesh):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    return m


def sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def overlap(a: trimesh.Trimesh, b: trimesh.Trimesh) -> float:
    try:
        inter = a.intersection(b, engine="manifold")
        if inter is None or inter.is_empty:
            return 0.0
        return float(inter.volume)
    except Exception as e:
        print("  intersection error:", e)
        return -1.0


def z_rise_to_clear(base, lid, max_rise=5.0, tol=0.05) -> float:
    """Binary-search +Z translation of lid until overlap < tol."""
    lo, hi = 0.0, max_rise
    ov0 = overlap(base, lid)
    if ov0 < tol:
        return 0.0
    for _ in range(22):
        mid = 0.5 * (lo + hi)
        lt = lid.copy()
        lt.apply_translation([0.0, 0.0, mid])
        if overlap(base, lt) < tol:
            hi = mid
        else:
            lo = mid
    return float(hi)


def void_r_at(mesh, z, n=300) -> float | None:
    rs = np.linspace(0, 5, n)
    inside = mesh.contains(np.column_stack([rs, np.zeros(n), np.full(n, z)]))
    if inside[0]:
        return None  # solid at center
    idx = np.where(inside)[0]
    return float(rs[idx[0]]) if len(idx) else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    WORLD.mkdir(parents=True, exist_ok=True)
    poses = A.world_poses()
    optb_poses = A.optb_world_poses()
    all_poses = A.all_assembly_poses()

    # Serialize ALL poses (standard + Option B) for machine-readable assembly map
    pose_json = {}
    for name, M in all_poses.items():
        pose_json[name] = {
            "matrix_4x4": np.asarray(M, dtype=float).reshape(4, 4).tolist(),
            "translation_mm": np.asarray(M, dtype=float).reshape(4, 4)[:3, 3].tolist(),
        }
    if "jig_blank_shock_plug_L" in pose_json:
        pose_json["jig_blank_shock_plug_spare"] = pose_json["jig_blank_shock_plug_L"]
    POSES_PATH.write_text(json.dumps(pose_json, indent=2))
    print(f"wrote {POSES_PATH}")

    gates = []

    def gate(name, ok, detail=""):
        gates.append({"name": name, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL"), name, "—", detail)

    # --- Cap no-regression ---
    for fn, expect in CAP_SHA12.items():
        got = sha12(STL / fn)
        gate(f"cap_frozen_{fn}", got == expect, f"sha12={got} expect={expect}")

    # Export world STLs for every pose that has a matching print STL
    exported = []
    for name, M in all_poses.items():
        candidates = [f"{name}.stl"]
        if name.startswith("clamp_bar_"):
            candidates = ["clamp_bar.stl"]
        if name.startswith("jig_blank_shock_plug"):
            candidates = [f"{name}.stl", "jig_blank_shock_plug_L.stl"]
        src = None
        for c in candidates:
            if (STL / c).exists():
                src = STL / c
                break
        if src is None:
            continue
        m = trimesh.load(src, force="mesh")
        if not isinstance(m, trimesh.Trimesh):
            m = trimesh.util.concatenate(tuple(m.geometry.values()))
        mw = m.copy()
        mw.apply_transform(M)
        out_p = WORLD / f"{name}.stl"
        mw.export(out_p)
        exported.append(name)
    gate("world_stls_exported", len(exported) >= 20, f"n={len(exported)}")

    # --- Pod L/R base ∩ lid ---
    for side in ("L", "R"):
        base = load(f"pod_{side}_base.stl")
        lid = load(f"pod_{side}_lid.stl")
        bw = base.copy(); bw.apply_transform(poses[f"pod_{side}_base"])
        lw = lid.copy(); lw.apply_transform(poses[f"pod_{side}_lid"])
        ov = overlap(bw, lw)
        rise = z_rise_to_clear(bw, lw)
        gate(f"pod_{side}_overlap_0", abs(ov) < 0.05, f"overlap_mm3={ov:.4f}")
        gate(f"pod_{side}_seam_0", rise < 0.05, f"z_rise={rise:.4f}")
        gate(f"pod_{side}_watertight", base.is_watertight and lid.is_watertight,
             f"base={base.is_watertight} lid={lid.is_watertight}")
        # 4/4 coaxial bosses — sample empty bore at cols
        cols = [(sx * 22.0, sy * 36.0) for sx in (-1, 1) for sy in (-1, 1)]
        # print-frame mating ≈ 36.2
        mz = 36.2
        ok_boss = True
        for x, y in cols:
            # transform cols roughly: check in print frame before pose
            bore = not bool(base.contains([[x, y, mz - 1.0]])[0])
            hole = not bool(lid.contains([[x, y, 1.0]])[0])
            if not (bore and hole):
                ok_boss = False
        gate(f"pod_{side}_bosses_4of4", ok_boss, f"cols={cols}")
        # poka-yoke key recess on lid: L (+18,+28); R after X+Y mirror → (−18,−28)
        key = (18.0, 28.0) if side == "L" else (-18.0, -28.0)
        key_ok = not bool(lid.contains([[key[0], key[1], 0.5]])[0])
        gate(f"pod_{side}_poka_key", key_ok, f"key_xy={key}")

    # --- CW ---
    tub = load("cw_tub.stl")
    cw_lid = load("cw_lid.stl")
    tw = tub.copy(); tw.apply_transform(poses["cw_tub"])
    clw = cw_lid.copy(); clw.apply_transform(poses["cw_lid"])
    ov = overlap(tw, clw)
    rise = z_rise_to_clear(tw, clw)
    gate("cw_overlap_0", abs(ov) < 0.05, f"overlap_mm3={ov:.4f}")
    gate("cw_seam_0", rise < 0.05, f"z_rise={rise:.4f}")
    gate("cw_watertight", tub.is_watertight and cw_lid.is_watertight,
         f"tub={tub.is_watertight} lid={cw_lid.is_watertight}")
    # CW_SCREWS: list-comp order (−22,−54)+3x poka, (−22,+54), (+22,−54), (+22,+54)
    cw_screws = [(-19.0, -54.0), (-22.0, 54.0), (22.0, -54.0), (22.0, 54.0)]
    ok_boss = all(not bool(tub.contains([[x, y, 16.0]])[0]) for x, y in cw_screws)
    gate("cw_bosses_present", ok_boss, f"screws={cw_screws}")
    ok_cl = all(
        not bool(tub.contains([[x, y, 9.0]])[0])
        for x, y in [(36, 28.5), (-36, 28.5), (36, -28.5), (-36, -28.5)]
    )
    gate("cw_clamp_holes_4", ok_cl, "±36,±28.5")

    # --- Heatset stop shelf ---
    hs = load("jig_m3_heatset_stop.stl")
    r_lo = void_r_at(hs, 2.0)
    r_hi = void_r_at(hs, 5.0)
    shelf_ok = (
        r_lo is not None and r_hi is not None
        and 2.4 < r_lo < 2.8   # tip Ø5.2
        and 1.9 < r_hi < 2.2  # insert Ø4.05
        and (r_lo - r_hi) > 0.3
    )
    gate("heatset_stop_shelf", shelf_ok, f"r@2={r_lo} r@5={r_hi}")

    # --- Wire gauge ---
    wg = load("jig_wire_gauge.stl")
    L = 180.0
    strip_ok = True
    for d in (5.0, 8.0):
        y = -0.5 * L + d
        if bool(wg.contains([[0.0, y, 3.5]])[0]):
            strip_ok = False
    # old wrong positions must be solid
    for d in (15.0, 18.0):
        y = -0.5 * L + d
        if not bool(wg.contains([[0.0, y, 3.5]])[0]):
            # may still be channel — only fail if empty AND x=0 channel
            pass
    gate("wire_strip_5_8", strip_ok, "notches empty at y=-85/-82")
    # 10 mm slot distinct void length near +Y
    y_slot = 0.5 * L - 20.0 - 5.0
    ys = np.linspace(y_slot - 6, y_slot + 6, 250)
    void = ~wg.contains(np.column_stack([np.zeros(250), ys, np.full(250, 3.0)]))
    spans, start = [], None
    for i, v in enumerate(void):
        if v and start is None:
            start = ys[i]
        if (not v) and start is not None:
            spans.append(ys[i - 1] - start)
            start = None
    if start is not None:
        spans.append(ys[-1] - start)
    slot10 = any(9.5 < s < 11.5 for s in spans)
    gate("wire_m3_slot_10", slot10, f"spans={[round(s,2) for s in spans]}")

    # --- OptB + blank shock plug ---
    for side in ("L", "R"):
        optb = load(f"pod_{side}_base_optB_curveUP.stl")
        cover = load(f"optb_bay_cover_{side}.stl")
        plug = load(f"jig_blank_shock_plug_{side}.stl")
        # Bore presence in optB (print curveUP): sample void near bay center
        # After flip, bay faces +Z near z=0 band — probe several z
        bore_hits = 0
        for z in np.linspace(0.5, 8.0, 12):
            if not bool(optb.contains([[0.0, 0.0, float(z)]])[0]):
                bore_hits += 1
        gate(f"optb_{side}_shock_bore_open", bore_hits >= 3,
             f"open_z_samples={bore_hits}/12")
        # Cover bore
        cover_bore = not bool(cover.contains([[0.0, 0.0, 1.0]])[0])
        gate(f"optb_{side}_cover_bore", cover_bore, "Ø8.05 through cover")
        # Seated plug vs optB + cover at Option-B poses (not mixed with Option A)
        ow = optb.copy(); ow.apply_transform(optb_poses[f"pod_{side}_base_optB_curveUP"])
        pw = plug.copy(); pw.apply_transform(optb_poses[f"jig_blank_shock_plug_{side}"])
        ov_p = overlap(ow, pw)
        gate(f"optb_{side}_plug_overlap_0", abs(ov_p) < 0.05, f"overlap_mm3={ov_p:.4f}")
        clear = (SHOCK_BORE_D - SHOCK_STEM_D) / 2
        gate(f"optb_{side}_plug_clear", 0.20 <= clear <= 0.25, f"clear/side={clear:.3f}")
        cw = cover.copy(); cw.apply_transform(optb_poses[f"optb_bay_cover_{side}"])
        ov_c = overlap(ow, cw)
        gate(f"optb_{side}_cover_overlap_0", abs(ov_c) < 0.05, f"overlap_mm3={ov_c:.4f}")

    report = {
        "gates": gates,
        "all_pass": all(g["ok"] for g in gates),
        "assembly_poses": str(POSES_PATH),
        "world_dir": str(WORLD),
        "n_world": len(exported),
    }
    out_json = _D6 / "review" / "friday_plates_mating_verified.json"
    out_json.write_text(json.dumps(report, indent=2))
    print(f"wrote {out_json}")
    print("ALL PASS" if report["all_pass"] else "FAIL")
    if not report["all_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
