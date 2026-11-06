#!/usr/bin/env python3
"""Mesh-level verification of D8 X2a cuts on exported cap_base.stl.

NOT a fit/print test — geometry only. Exit 0 iff all checks pass.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(HERE, "..", "stl", "cap_base.stl")
KIT_AT = (0.0, -24.0)
KIT_BOARD = (55.88, 20.32)
KIT_POCKET = (57.6, 21.4)
J2_DEPTH = 2.6


def max_hit_z(mesh, xs, ys, z0=50.0):
    origins = np.column_stack([xs, ys, np.full(len(xs), z0)])
    dirs = np.tile([0.0, 0.0, -1.0], (len(xs), 1))
    locs, rays, _ = mesh.ray.intersects_location(origins, dirs)
    hits = defaultdict(list)
    for p, r in zip(locs, rays):
        hits[int(r)].append(float(p[2]))
    return np.array([max(hits[i]) if i in hits else np.nan for i in range(len(xs))])


def main():
    m = trimesh.load(STL, force="mesh")
    assert m.is_watertight, "cap_base not watertight"
    report = {"stl": STL, "bounds": m.bounds.tolist(), "checks": []}

    def chk(name, ok, detail):
        report["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL"), name, "|", detail)

    # --- seating plane near kit (outside J2 pocket) ---
    pad_xs = np.array([-20.0, -12.0, 12.0, 20.0])
    pad_ys = np.full(4, -20.0)  # +Y side of kit, away from J2
    pad_z = max_hit_z(m, pad_xs, pad_ys)
    seat = float(np.nanmedian(pad_z))
    chk("PCB seating plane found", np.isfinite(seat), f"seat_z≈{seat:.2f}")

    # --- J2 depth ≥2.6 below seating ---
    j2_z = float(max_hit_z(m, np.array([0.0]), np.array([-28.0]))[0])
    j2_drop = seat - j2_z
    chk("J2 relief depth ≥2.6 mm", j2_drop >= 2.55, f"seat={seat:.2f} j2={j2_z:.2f} drop={j2_drop:.2f}")

    # --- locating ribs: 0.8 mm above seat, ring around 57.6×21.4 ---
    z_rib = seat + 0.8
    # sample on pocket inner edge mid-sides (should hit rib top ≥ seat+1.5 or be solid wall)
    # ribs rise h=2.4 from seat → top ≈ seat+2.4; at z=seat+0.8 a horizontal slice
    # through ribs: points just outside clear opening should be inside solid.
    hx, hy = 0.5 * KIT_POCKET[0] + 0.7, 0.5 * KIT_POCKET[1] + 0.7  # in rib wall
    rib_pts = np.array([
        [KIT_AT[0] + hx, KIT_AT[1], z_rib],
        [KIT_AT[0] - hx, KIT_AT[1], z_rib],
        [KIT_AT[0], KIT_AT[1] + hy, z_rib],
        [KIT_AT[0], KIT_AT[1] - hy, z_rib],
    ])
    rib_inside = m.contains(rib_pts)
    chk("locating ribs present 0.8 mm above seat", bool(rib_inside.sum() >= 3),
        f"inside_count={int(rib_inside.sum())}/4 at z={z_rib:.2f}")

    # clear opening centre should be EMPTY at seat+0.8 (no floor fill)
    centre = np.array([[KIT_AT[0], KIT_AT[1], z_rib]])
    chk("kit pocket interior open at seat+0.8", not bool(m.contains(centre)[0]),
        f"centre_inside={bool(m.contains(centre)[0])}")

    # --- glyphs under PCB footprint must not raise above seat ---
    bx, by = 0.5 * KIT_BOARD[0] - 1.0, 0.5 * KIT_BOARD[1] - 1.0
    grid = []
    for x in np.linspace(KIT_AT[0] - bx, KIT_AT[0] + bx, 9):
        for y in np.linspace(KIT_AT[1] - by, KIT_AT[1] + by, 7):
            # skip J2 relief zone (y around -28)
            if abs(y - (KIT_AT[1] - 4.0)) < 5.0 and abs(x) < 10.0:
                continue
            grid.append([x, y])
    grid = np.array(grid)
    gz = max_hit_z(m, grid[:, 0], grid[:, 1])
    over = gz[np.isfinite(gz)] - seat
    n_proud = int(np.sum(over > 0.35))  # allow tiny weld noise; glyphs are ≥0.6
    chk("no glyph proud above seat inside PCB footprint", n_proud == 0,
        f"proud_pts={n_proud} max_over={float(np.nanmax(over)):.2f}")

    # --- USB-C through tunnel ---
    # cavity empty ~y=-48; solid was -60..-75; exterior ~y=-82
    usbc_z = seat + 2.0 + 3.0  # mid aperture
    ys = np.linspace(-48.0, -86.0, 20)
    pts = np.column_stack([np.zeros(len(ys)), ys, np.full(len(ys), usbc_z)])
    inside = m.contains(pts)
    # Through-channel ⇒ mostly NOT inside along the axis
    solid_frac = float(inside.mean())
    chk("USB-C through-channel open cavity→exterior", solid_frac < 0.25,
        f"solid_frac={solid_frac:.2f} along y=-48..-86 at z={usbc_z:.1f}")

    plug = os.path.join(HERE, "..", "stl", "cap_usbc_plug.stl")
    chk("cap_usbc_plug.stl exported", os.path.isfile(plug), plug)
    if os.path.isfile(plug):
        pm = trimesh.load(plug, force="mesh")
        chk("cap_usbc_plug watertight", pm.is_watertight, f"V={pm.volume:.1f}")

    report["pass"] = all(c["pass"] for c in report["checks"])
    out = os.path.join(HERE, "verify_cap_base_x2a_mesh.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print("RESULT:", "PASS" if report["pass"] else "FAIL")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
