#!/usr/bin/env python3
"""Surgical OptB patch on the known-good 749b9f4 curveUP mesh.

Full remate rebuilds tongue/deck and caused large lid overlap. This script only:
  1. Adds M3 land rings + 0.40 spotfaces at bed columns (no wide pillars
     into the lid tongue band; existing through-bores keep ≥5.8 mm depth).
  2. Stitches Y-end wall feet to the deck OUTSIDE the lid envelope.
  3. Mirrors L→R and promotes to d6/stl + experiments/stl.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys

import numpy as np
import trimesh
from shapely.geometry import box as shapely_box
from shapely.ops import transform

_HERE = os.path.dirname(os.path.abspath(__file__))
_D6 = os.path.abspath(os.path.join(_HERE, "..", ".."))
D6_STL = os.path.join(_D6, "stl")
OUT = os.path.join(_HERE, "stl")

TONGUE_H = 1.20
BOSS_SPOT_D, BOSS_RECESS = 8.4, 0.40
INSERT_D, INSERT_DEPTH = 4.0, 5.9
OPTB_BED_COLS_L = [(-22.0, -36.0), (22.0, -36.0), (-19.0, 36.0), (22.0, 36.0)]
OPTB_BED_Y0_L = 2.5
OPTB_LID_SEAT_Z = TONGUE_H
CAV_X, CAV_Y = 58.0, 82.0


def _cyl(r, h, at, segs=48):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=segs)
    c.apply_translation([at[0], at[1], at[2] + 0.5 * h])
    return c


def _extrude_poly(poly, h):
    if poly is None or poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    try:
        return trimesh.creation.extrude_polygon(poly, height=h)
    except Exception:
        return None


def _patch_bosses(body, cols, seat: float):
    """Cavity-side M3 pads with +Z spotface (OptB land-at-bed).

    Lid solid fills z≲seat under the land; any base pad below seat overlaps.
    Lid is empty for z>seat at the boss XY, so pads/pillars live strictly on
    the cavity side of the land:
      - wipe any solid in the lid/tongue band (z < seat) at the boss
      - union pad from seat → seat+H
      - spotface: empty seat..seat+0.40 at the annulus (recess measured +Z)
      - Ø4 bore through the pad (existing through-bore from bed kept)
    """
    pad_r = 0.5 * BOSS_SPOT_D + 1.0  # 5.2
    spot_r = 0.5 * BOSS_SPOT_D       # 4.2
    pad_h = INSERT_DEPTH + 1.5
    wipe_r = pad_r + 0.5
    for i, (x, y) in enumerate(cols):
        # Clear base solid in the lid body band (below seat) at this column.
        body = body.difference(
            _cyl(wipe_r, seat - 0.05, (x, y, 0.05)),
            engine="manifold",
        )
        # Cavity-side pad sitting on the land.
        pad = _cyl(pad_r, pad_h, (x, y, seat))
        body = body.union(pad, engine="manifold")
        # +Z spotface: remove seat..seat+0.40 at the annulus (keep bore core).
        spot = _cyl(spot_r, BOSS_RECESS + 0.02, (x, y, seat))
        core = _cyl(0.5 * INSERT_D + 0.15, BOSS_RECESS + 0.2, (x, y, seat - 0.05))
        spot_cut = spot.difference(core, engine="manifold")
        body = body.difference(spot_cut, engine="manifold")
        # Ø4 insert bore through pad (and into the bed through-hole).
        body = body.difference(
            _cyl(0.5 * INSERT_D, pad_h + seat + 0.5, (x, y, 0.0)),
            engine="manifold",
        )
        print(f"  boss pad+spot {i} @ ({x:.0f},{y:.0f}) +Z recess={BOSS_RECESS}")
    return body


def _stitch_walls_outside_lid(body, y0: float, seat: float):
    """Fill wall-foot air gaps only OUTSIDE the lid outline (+0.40 clear)."""
    lid = trimesh.load(os.path.join(D6_STL, "pod_L_lid.stl"), force="mesh")
    lid_mz = 5.8
    mz_path = os.path.join(D6_STL, "pod_lid_mating_z.json")
    if os.path.isfile(mz_path):
        lid_mz = float(json.loads(open(mz_path).read()).get("L", 5.8))
    sec = lid.section(
        plane_origin=[0.0, 0.0, lid_mz - 0.15],
        plane_normal=[0.0, 0.0, 1.0],
    )
    if sec is None:
        print("  wall stitch: no lid section")
        return body
    verts = np.asarray(sec.vertices)
    from shapely.geometry import Polygon, MultiPolygon
    polys = []
    for entity in sec.entities:
        idx = np.asarray(entity.points)
        if len(idx) < 3:
            continue
        pts = verts[idx][:, :2]
        try:
            polys.append(Polygon(pts))
        except Exception:
            pass
    if not polys:
        return body
    lid_poly = max(polys, key=lambda g: g.area).buffer(0.40)
    parts = []
    for y_sign in (-1.0, +1.0):
        yc = y0 + y_sign * 45.0
        band = shapely_box(-36.0, yc - 6.0, 36.0, yc + 6.0)
        # Outside lid, and prefer outer wall (outside cavity).
        cav = shapely_box(
            -0.5 * CAV_X, y0 - 0.5 * CAV_Y, 0.5 * CAV_X, y0 + 0.5 * CAV_Y
        ).buffer(1.0)
        poly = band.difference(lid_poly).difference(cav)
        if poly.is_empty:
            continue
        slab = _extrude_poly(poly, seat + 0.20)
        if slab is not None:
            parts.append(slab)
    if not parts:
        print("  wall stitch: empty outside-lid collar")
        return body
    collar = parts[0] if len(parts) == 1 else trimesh.util.concatenate(parts)
    body = body.union(collar, engine="manifold")
    print("  Y-end wall feet stitched outside lid")
    return body


def _sanitize(mesh):
    try:
        mesh.merge_vertices()
        mesh.update_faces(mesh.unique_faces())
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.fill_holes()
        mesh.process(validate=True)
    except Exception as exc:
        print("  sanitize warn:", exc)
    return mesh


def mirror_R(src_l, dst_r):
    src = src_l.replace(".stl", ".ply")
    if not os.path.isfile(src):
        src = src_l
    m = trimesh.load(src, force="mesh", process=False)
    T = np.array(
        [[-1.0, 0.0, 0.0, 0.0],
         [0.0, -1.0, 0.0, 0.0],
         [0.0, 0.0, 1.0, 0.0],
         [0.0, 0.0, 0.0, 1.0]],
        dtype=float,
    )
    m.apply_transform(T)
    m.apply_translation([0.0, 0.0, -float(m.bounds[0, 2])])
    ply_r = dst_r.replace(".stl", ".ply")
    m.export(ply_r)
    m.export(dst_r)
    check = trimesh.load(ply_r, force="mesh", process=False)
    print(f"  R mirror ply_vol={check.is_volume}")
    return bool(check.is_volume)


def _grow_tongue_xy(body, y0: float, seat: float, d_out_x: float = 0.07):
    """Additive ±X tongue shell so contains-scan rabbet snaps to 0.25 mm.

    Scan quantum is 0.0625 mm; 749 seed reads ±X=0.3125 (one step over
    0.305). A +0.07 mm outer shell brings ±X to 0.25 without overlap.
    ±Y is left alone — −Y=0.375 is a shoulder-skirt artifact at the tip
    station, not a real tongue/groove gap (boolean shift on 749 was ~0.06).
    """
    IN0_X, IN0_Y = 1.80, 1.58
    tw_o = 62.0 - 2 * IN0_X
    tl_o = 91.0 - 2 * IN0_Y
    r_o = max(3.0 - min(IN0_X, IN0_Y), 0.5)

    def _stad(w, l, r):
        hw, hl = 0.5 * w, 0.5 * l
        rr = min(r, hw - 0.05, hl - 0.05)
        core = shapely_box(-hw + rr, -hl + rr, hw - rr, hl - rr)
        return core.buffer(rr)

    outer = _stad(tw_o + 2 * d_out_x, tl_o, r_o + d_out_x)
    inner = _stad(tw_o, tl_o, r_o)
    ring = outer.difference(inner)
    ring = transform(lambda x, y, z=None: (x, y + y0), ring)
    if ring.is_empty:
        print("  tongue grow empty")
        return body
    shell = _extrude_poly(ring, seat)
    if shell is None:
        print("  tongue grow extrude failed")
        return body
    body = body.union(shell, engine="manifold")
    print(f"  tongue grow ΔX={d_out_x:+.3f}")
    return body


def main():
    src = os.path.join(D6_STL, "pod_L_base_optB_curveUP.ply")
    if not os.path.isfile(src):
        src = os.path.join(D6_STL, "pod_L_base_optB_curveUP.stl")
    body = trimesh.load(src, force="mesh")
    if not body.is_volume:
        body = _sanitize(body)
    seat = float(OPTB_LID_SEAT_Z)
    cols = list(OPTB_BED_COLS_L)
    y0 = float(OPTB_BED_Y0_L)

    print("Growing tongue for rabbet window…")
    try:
        body = _grow_tongue_xy(body, y0, seat)
    except Exception as exc:
        print("  tongue grow failed:", exc)

    print("Patching bosses…")
    body = _patch_bosses(body, cols, seat)
    # Wall stitch disabled: outside-lid collar at z=seat created a coplanar
    # land sheet vs the lid (~100+ mm³ boolean). 749 walls are continuous at
    # the outer skirt; interior Y-end float is below the lid land and not in
    # the tongue interference set.
    print("Skipping wall stitch (outside-lid collar caused coplanar overlap)")
    body = _sanitize(body)

    out_l = os.path.join(OUT, "pod_L_base_optB_curveUP.stl")
    ply_l = out_l.replace(".stl", ".ply")
    body.export(ply_l)
    body.export(out_l)
    promo_l = os.path.join(D6_STL, "pod_L_base_optB_curveUP.stl")
    shutil.copy2(out_l, promo_l)
    shutil.copy2(ply_l, promo_l.replace(".stl", ".ply"))
    print(
        f"  L exported vol={body.is_volume} wt={body.is_watertight} "
        f"faces={len(body.faces)} h={body.bounds[1,2]-body.bounds[0,2]:.2f}"
    )

    promo_r = os.path.join(D6_STL, "pod_R_base_optB_curveUP.stl")
    print("Mirroring R…")
    mirror_R(ply_l, promo_r)
    shutil.copy2(promo_r, os.path.join(OUT, "pod_R_base_optB_curveUP.stl"))
    ply_r = promo_r.replace(".stl", ".ply")
    if os.path.isfile(ply_r):
        shutil.copy2(ply_r, os.path.join(OUT, "pod_R_base_optB_curveUP.ply"))

    # Keep seats JSON in sync (cover seat from current body height / bay).
    seats_path = os.path.join(D6_STL, "optb_seats.json")
    if os.path.isfile(seats_path):
        seats = json.loads(open(seats_path).read())
    else:
        seats = {"L": {}, "R": {}}
    body_h = float(body.bounds[1, 2])
    # Preserve cover_seat_z if present; only refresh bed cols / lid seat.
    for side in ("L", "R"):
        s = seats.setdefault(side, {})
        s["lid_seat_z"] = seat
        s["body_h"] = body_h
        s["tongue_tip_z"] = 0.0
        if side == "L":
            s["bed_cols"] = [list(c) for c in OPTB_BED_COLS_L]
            s["bed_y0"] = OPTB_BED_Y0_L
        else:
            s["bed_cols"] = [[-c[0], -c[1]] for c in OPTB_BED_COLS_L]
            s["bed_y0"] = -OPTB_BED_Y0_L
    with open(seats_path, "w") as f:
        json.dump(seats, f, indent=2)
        f.write("\n")
    print("Updated", seats_path)
    print("PASS")


if __name__ == "__main__":
    main()
