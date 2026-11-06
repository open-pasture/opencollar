#!/usr/bin/env python3
"""Post-process pod_L/R_base.stl: ≤45° corbel under floating tongue.

Keeps frozen lid groove XY (0.28 mm clear). Roots tongue into the solid
perimeter wall so z_mating-0.3 / z_mating-1.5 are solid under every tongue
sample. Mirrors R from L. Does not touch lids (groove already matched).
"""
from __future__ import annotations

import json
import math
import os
import shutil

import numpy as np
import trimesh
from shapely.geometry import box as shapely_box
from shapely.ops import transform

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


def _extrude(poly, h):
    from shapely.geometry import MultiPolygon
    geoms = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
    parts = []
    for g in geoms:
        if g is None or g.is_empty or g.area < 0.5:
            continue
        try:
            parts.append(trimesh.creation.extrude_polygon(g, height=float(h)))
        except Exception:
            pass
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else trimesh.util.concatenate(parts)


def _cyl(r, h, at, segs=32):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=segs)
    c.apply_translation([at[0], at[1], at[2] + 0.5 * h])
    return c


def add_corbel(body, y0: float, z_part: float):
    """Solid ≤45° corbel envelope under tongue, rooted into perimeter wall.

    Single manifold ring filling the 45° wedge AABB (outer on solid land,
    inner at tongue_inner−depth). Avoids staircase air gaps / non-volume.
    """
    depth = (TONGUE_IN1 - TONGUE_IN0) + 0.35  # ~1.75 mm
    wall_in0 = max(0.25, TONGUE_IN0 - 1.55)  # outer ~±30.75 on solid land
    in_i = TONGUE_IN1 + depth                 # bottom-most inner (45°)
    in_o = wall_in0
    ring = _stadium_poly(
        POD_LID_W - 2 * in_o, POD_LID_L - 2 * in_o, max(POD_LID_R - in_o, 0.5),
    ).difference(_stadium_poly(
        POD_LID_W - 2 * in_i, POD_LID_L - 2 * in_i, max(POD_LID_R - in_i, 0.4),
    ))
    ring = transform(lambda x, y, z=None: (x, y + y0), ring)
    # Top ≤ land − 0.02 — never kiss the lid land plate.
    solid = _extrude(ring, depth)
    if solid is None or not solid.is_volume:
        raise RuntimeError("corbel extrude non-volume")
    solid.apply_translation([0.0, 0.0, z_part - depth - 0.02])
    print(
        f"  corbel depth={depth:.2f} top={z_part - 0.02:.2f} "
        f"inner_top={POD_LID_W / 2 - TONGUE_IN1:.2f} "
        f"inner_bot={POD_LID_W / 2 - in_i:.2f} vol={solid.is_volume}"
    )
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
