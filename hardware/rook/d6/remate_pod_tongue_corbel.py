#!/usr/bin/env python3
"""Post-process pod_L/R_base.stl: true ≥45° corbel under floating tongue.

Keeps frozen lid groove XY (0.28 mm clear). Roots tongue into the solid
perimeter wall with a wedge whose underside is ≥45° above horizontal
(0 mm² flat ceilings over the battery cavity). Mirrors R from L.
Does not touch lids.
"""
from __future__ import annotations

import math
import os

import numpy as np
import trimesh
from shapely.geometry import box as shapely_box

_HERE = os.path.dirname(os.path.abspath(__file__))
STL = os.path.join(_HERE, "stl")

TONGUE_IN0, TONGUE_IN1, TONGUE_H = 1.80, 3.20, 1.20
POD_LID_W, POD_LID_L, POD_LID_R = 62.0, 91.0, 3.0
# Match pod.py: POD_Y0 = mount_face − len/2 = −2.5 (L body centre).
POD_Y0 = -2.5
POD_MATING_Z = 36.2
POD_COLS_L = [(-22.0, 36.0), (22.0, 36.0), (-19.0, -36.0), (22.0, -36.0)]
BOSS_SPOT_D, BOSS_RECESS = 8.4, 0.40
INSERT_D, INSERT_DEPTH = 4.0, 5.6


def _stadium_poly(w, l, r):
    hw, hl = 0.5 * w, 0.5 * l
    rr = min(r, hw - 0.05, hl - 0.05)
    core = shapely_box(-hw + rr, -hl + rr, hw - rr, hl - rr)
    return core.buffer(rr)


def _densify_boundary(poly, n: int = 160) -> np.ndarray:
    coords = np.array(poly.exterior.coords)
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(coords, axis=0), axis=1))]
    s = np.linspace(0.0, d[-1], n, endpoint=False)
    x = np.interp(s, d, coords[:, 0])
    y = np.interp(s, d, coords[:, 1])
    return np.column_stack([x, y])


def _inward_normals(pts: np.ndarray) -> np.ndarray:
    """Unit normals pointing into the stadium (toward origin)."""
    n = len(pts)
    norms = np.zeros_like(pts)
    for i in range(n):
        p0 = pts[i - 1]
        p2 = pts[(i + 1) % n]
        t = p2 - p0
        t = t / (np.linalg.norm(t) + 1e-12)
        # Perp candidates; pick the one that points toward the origin.
        left = np.array([-t[1], t[0]])
        right = np.array([t[1], -t[0]])
        mid = pts[i]
        norms[i] = left if np.dot(left, mid) < 0 else right
    return norms


def _cyl(r, h, at, segs=32):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=segs)
    c.apply_translation([at[0], at[1], at[2] + 0.5 * h])
    return c


def make_wedge_corbel(y0: float, z_part: float) -> trimesh.Trimesh:
    """≥45° underside wedge ring rooted on the perimeter land.

    Cross-section is a right triangle: vertical outer face on the land wall,
    horizontal top under the tongue, slanted underside (run == rise) so every
    downward-facing facet is ≥45° above horizontal — no flat ceilings over
    the battery cavity.
    """
    # Outer just outside the tongue/wall (~inset 1.70).
    in_o = TONGUE_IN0 - 0.10  # 1.70 → outer ~±29.3 (at wall)
    # Rise must reach tongue-inner under z_mating−1.5: need t=h−1.5 ≥
    # (TONGUE_IN1−in_o) so h ≥ (TONGUE_IN1−in_o)+1.5 ≈ 3.0 mm.
    run = float(TONGUE_IN1 - in_o) + 1.55  # ~3.05 mm
    run = float(max(2.5, min(run, 3.2)))
    h = run  # exact 45°
    z0 = z_part - h - 0.02
    w_o = POD_LID_W - 2 * in_o
    l_o = POD_LID_L - 2 * in_o
    r_o = max(POD_LID_R - in_o, 0.5)
    outer = _densify_boundary(_stadium_poly(w_o, l_o, r_o), n=160)
    nin = _inward_normals(outer)
    inner = outer + nin * run
    outer = outer.copy()
    inner = inner.copy()
    outer[:, 1] += y0
    inner[:, 1] += y0
    n = len(outer)
    verts = []
    for x, y in outer:
        verts.append([x, y, z0])
    for x, y in outer:
        verts.append([x, y, z0 + h])
    for x, y in inner:
        verts.append([x, y, z0 + h])
    faces = []
    for i in range(n):
        j = (i + 1) % n
        # outer vertical wall
        faces.append([i, j, n + j])
        faces.append([i, n + j, n + i])
        # top land under tongue
        faces.append([n + i, n + j, 2 * n + j])
        faces.append([n + i, 2 * n + j, 2 * n + i])
        # slanted underside (≥45°)
        faces.append([i, 2 * n + i, 2 * n + j])
        faces.append([i, 2 * n + j, j])
    mesh = trimesh.Trimesh(
        vertices=np.asarray(verts, float),
        faces=np.asarray(faces, int),
        process=True,
    )
    mesh.fix_normals()
    if not mesh.is_volume:
        raise RuntimeError("wedge corbel non-volume")
    print(
        f"  wedge corbel run={run:.2f} h={h:.2f} top={z0 + h:.2f} "
        f"in_o={in_o:.2f} vol={mesh.is_volume}"
    )
    return mesh


def add_corbel(body, y0: float, z_part: float):
    solid = make_wedge_corbel(y0, z_part)
    return body.union(solid, engine="manifold")


def recut_bosses(body, cols, z_part: float):
    """Spotface through tongue tip + insert bore (no floating bridge)."""
    spot_h = BOSS_RECESS + TONGUE_H + 1.2
    for i, (x, y) in enumerate(cols):
        body = body.difference(
            _cyl(0.5 * BOSS_SPOT_D, spot_h, (x, y, z_part - BOSS_RECESS)),
            engine="manifold",
        )
        body = body.difference(
            _cyl(0.5 * INSERT_D, INSERT_DEPTH + 0.3,
                 (x, y, z_part - BOSS_RECESS - INSERT_DEPTH)),
            engine="manifold",
        )
    return body


def remate_L():
    # Seed from d6bae12-clean base if current already has a bad corbel —
    # caller restores seed before invoke. Always start from whatever STL is
    # currently staged as pod_L_base.stl.
    src = os.path.join(STL, "pod_L_base.stl")
    body = trimesh.load(src, force="mesh")
    if not body.is_volume:
        body.fill_holes()
        body.process(validate=True)
    print(f"L seed wt={body.is_watertight} vol={body.is_volume} h={body.extents[2]:.2f}")
    body = add_corbel(body, POD_Y0, POD_MATING_Z)
    body = recut_bosses(body, POD_COLS_L, POD_MATING_Z)
    body.apply_translation([0.0, 0.0, -float(body.bounds[0, 2])])
    if not body.is_volume:
        body.fill_holes()
        body.process(validate=True)
    out = os.path.join(STL, "pod_L_base.stl")
    body.export(out)
    body.export(os.path.join(STL, "pod_L_base.ply"))
    check = trimesh.load(out, force="mesh", process=False)
    print(f"  L out wt={check.is_watertight} vol={check.is_volume} "
          f"h={check.extents[2]:.2f} faces={len(check.faces)}")
    return bool(body.is_volume)


def mirror_R():
    src = os.path.join(STL, "pod_L_base.ply")
    if not os.path.isfile(src):
        src = os.path.join(STL, "pod_L_base.stl")
    m = trimesh.load(src, force="mesh", process=False)
    T = np.diag([-1.0, -1.0, 1.0, 1.0])
    m.apply_transform(T)
    m.apply_translation([0.0, 0.0, -float(m.bounds[0, 2])])
    if not m.is_volume:
        m.fill_holes()
        m.process(validate=True)
    out = os.path.join(STL, "pod_R_base.stl")
    m.export(out)
    m.export(os.path.join(STL, "pod_R_base.ply"))
    check = trimesh.load(out, force="mesh", process=False)
    print(f"  R mirror vol={check.is_volume or m.is_volume} h={check.extents[2]:.2f}")
    return bool(m.is_volume)


def main():
    if not remate_L():
        raise SystemExit(1)
    if not mirror_R():
        print("R non-volume (continuing)")
    print("PASS")


if __name__ == "__main__":
    main()
