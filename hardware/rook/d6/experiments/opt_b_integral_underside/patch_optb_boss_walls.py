#!/usr/bin/env python3
"""Surgical OptB patch on 749b9f4 curveUP (keep rabbet 0.28 / overlap≈0 / spotface).

Fixes for audit 5e4eaed:
  1. Keep tongue shave dy=0.22 → rigid-shift X=Y≈0.28
  2. Full-360 outer-land plate (lid\\tongue, lid-subtracted) → land_360_flush
  3. Outside-lid Y-end wall stitch + under-lid wall-foot boxes (inset)
  4. +Z M3 pads / 0.40 spotface / ≥45° top chamfer
  5. ≥45° cavity-shelf chamfer at (±22,−35) Z≈20.5 (hole + cone)
  6. Bay clear + RING land + ≥45° wall-rooted corbel (no cavity ceiling slab)
  7. Restore cover_seat_z=29.476; regenerate assembly_poses + out/world
     including shock-plug world STLs
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import numpy as np
import trimesh
from shapely.geometry import box as shapely_box, Polygon
from shapely.ops import unary_union

_HERE = os.path.dirname(os.path.abspath(__file__))
_D6 = os.path.abspath(os.path.join(_HERE, "..", ".."))
D6_STL = os.path.join(_D6, "stl")
D6_OUT = os.path.join(_D6, "out")
OUT = os.path.join(_HERE, "stl")

TONGUE_H = 1.20
BOSS_SPOT_D, BOSS_RECESS = 8.4, 0.40
INSERT_D, INSERT_DEPTH = 4.0, 5.9
OPTB_BED_COLS_L = [(-22.0, -36.0), (22.0, -36.0), (-19.0, 36.0), (22.0, 36.0)]
OPTB_BED_Y0_L = 2.5
OPTB_KEY_XY_L = (18.0, -28.0)
OPTB_LID_SEAT_Z = TONGUE_H
CAV_X, CAV_Y = 58.0, 82.0
IN0_X_749, IN0_Y_749 = 1.80, 1.58
IN1_X_749, IN1_Y_749 = 3.20, 2.98
SHAVE_DX, SHAVE_DY = 0.0, 0.22
COVER_SEAT_Z_46 = 29.4764419837619
COVER_W, COVER_L, COVER_R = 28.0, 42.0, 2.0
OPTB_COVER_COLS = [(-10.0, 14.0), (8.0, 14.0), (-7.0, -14.0), (10.0, -12.0)]
SHOCK_BORE_D = 8.05
SHOCK_FLANGE_SEAT_D = 12.50
TONGUE_IN0, TONGUE_IN1 = 1.80, 3.20


def _cyl(r, h, at, segs=48):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=segs)
    c.apply_translation([at[0], at[1], at[2] + 0.5 * h])
    return c


def _cone_frustum(r_bot, r_top, h, at, segs=48):
    ring0 = trimesh.creation.cylinder(radius=r_bot, height=0.02, sections=segs)
    ring0.apply_translation([0, 0, 0.01])
    ring1 = trimesh.creation.cylinder(radius=r_top, height=0.02, sections=segs)
    ring1.apply_translation([0, 0, h - 0.01])
    hull = trimesh.convex.convex_hull(
        np.vstack([ring0.vertices, ring1.vertices])
    )
    hull.apply_translation([at[0], at[1], at[2]])
    return hull


def _extrude_poly(poly, h):
    if poly is None or poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    try:
        return trimesh.creation.extrude_polygon(poly, height=h)
    except Exception:
        try:
            return trimesh.creation.extrude_polygon(poly.buffer(0), height=h)
        except Exception:
            return None


def _stad(w, l, r, y0=0.0):
    hw, hl = 0.5 * w, 0.5 * l
    rr = min(r, hw - 0.05, hl - 0.05)
    core = shapely_box(-hw + rr, -hl + rr + y0, hw - rr, hl - rr + y0)
    return core.buffer(rr)


def _shave_tongue(body, y0: float, seat: float,
                  dx: float = SHAVE_DX, dy: float = SHAVE_DY):
    tw_o = 62.0 - 2 * IN0_X_749
    tl_o = 91.0 - 2 * IN0_Y_749
    tw_i = 62.0 - 2 * IN1_X_749
    tl_i = 91.0 - 2 * IN1_Y_749
    r_o = max(3.0 - min(IN0_X_749, IN0_Y_749), 0.5)
    r_i = max(3.0 - min(IN1_X_749, IN1_Y_749), 0.4)
    tw_ot = 62.0 - 2 * (IN0_X_749 + dx)
    tl_ot = 91.0 - 2 * (IN0_Y_749 + dy)
    tw_it = 62.0 - 2 * (IN1_X_749 - dx)
    tl_it = 91.0 - 2 * (IN1_Y_749 - dy)
    shave_o = _stad(tw_o + 0.3, tl_o + 0.3, r_o + 0.2, y0).difference(
        _stad(tw_ot, tl_ot, max(r_o - max(dx, dy), 0.5), y0)
    )
    shave_i = _stad(tw_it, tl_it, max(r_i + max(dx, dy), 0.4), y0).difference(
        _stad(tw_i, tl_i, r_i, y0)
    )
    for label, poly in (("outer", shave_o), ("inner", shave_i)):
        if poly.is_empty:
            continue
        cut = _extrude_poly(poly, seat + 0.05)
        if cut is not None:
            body = body.difference(cut, engine="manifold")
            print(f"  tongue shave {label} area={poly.area:.1f}")
    print(f"  tongue shave ΔX={dx:+.3f} ΔY={dy:+.3f}")
    return body


def _lid_poly():
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
        return None
    verts = np.asarray(sec.vertices)
    polys = []
    for entity in sec.entities:
        idx = np.asarray(entity.points)
        if len(idx) < 3:
            continue
        try:
            polys.append(Polygon(verts[idx][:, :2]))
        except Exception:
            pass
    if not polys:
        return None
    return max(polys, key=lambda g: g.area)


def _lid_in_base_frame():
    if _D6 not in sys.path:
        sys.path.insert(0, _D6)
    import importlib
    import assembly as A
    importlib.reload(A)
    lid = trimesh.load(os.path.join(D6_STL, "pod_L_lid.stl"), force="mesh")
    optb = A.optb_world_poses()
    Mo = optb["pod_L_base_optB_curveUP"]
    Ml = optb["pod_L_lid_optB"]
    lid_p = lid.copy()
    lid_p.apply_transform(np.linalg.inv(Mo) @ Ml)
    return lid_p


def _section_exterior(mesh, z):
    """Largest filled XY exterior at plane z."""
    sec = mesh.section(
        plane_origin=[0.0, 0.0, float(z)],
        plane_normal=[0.0, 0.0, 1.0],
    )
    if sec is None:
        return None
    verts = np.asarray(sec.vertices)
    polys = []
    for entity in sec.entities:
        idx = np.asarray(entity.points)
        if len(idx) < 3:
            continue
        xy = verts[idx][:, :2]
        try:
            p = Polygon(xy)
            if p.is_valid and p.area > 1.0:
                polys.append(p)
        except Exception:
            continue
    if not polys:
        return None
    u = unary_union(polys)
    if u.geom_type == "MultiPolygon":
        u = max(u.geoms, key=lambda g: g.area)
    return Polygon(u.exterior)


def _outer_land_plate_360(body, y0: float, seat: float, lid_p):
    """Restore 360° outer land under lid (0.3–1.2 mm band), excluding bay.

    Two fills:
      1) band ring (lid outline \\ tongue \\ bay), thin near seat, lid-subtracted
      2) missing std-Y-flip deck silhouette vs current section (remate recipe)
    """
    lid_poly = _lid_poly()
    if lid_poly is None:
        print("  land plate: no lid poly")
        return body
    tw_o = 62.0 - 2 * (IN0_X_749 + SHAVE_DX)
    tl_o = 91.0 - 2 * (IN0_Y_749 + SHAVE_DY)
    r_o = max(3.0 - min(IN0_X_749 + SHAVE_DX, IN0_Y_749 + SHAVE_DY), 0.5)
    # 0.45 clears the 0.28 rabbet channel but keeps the outer 0.3–1.2 land band
    # (0.12 ate the rabbet; 0.85 ate the +Y land band).
    tongue = _stad(tw_o, tl_o, r_o, y0).buffer(0.45)
    bay = _stad(COVER_W + 2.0, COVER_L + 2.0, COVER_R + 1.0)
    band = lid_poly.difference(lid_poly.buffer(-1.35))
    ring = band.difference(tongue).difference(bay)
    if not ring.is_empty:
        h = 0.30
        z0 = seat - 0.31
        slab = _extrude_poly(ring, h)
        if slab is not None:
            slab.apply_translation([0.0, 0.0, z0])
            try:
                slab = slab.difference(lid_p, engine="manifold")
                if slab.is_volume:
                    body = body.union(slab, engine="manifold")
                    print(f"  outer-land band plate area={ring.area:.1f}")
                else:
                    print("  land band non-volume after lid subtract; skip")
            except Exception as exc:
                print("  land band failed:", exc)
    # Remate-style missing deck fill vs std Y-flip silhouette at seat.
    try:
        std = trimesh.load(os.path.join(D6_STL, "pod_L_base.stl"), force="mesh")
        # Std mating silhouette at z≈36 (std land), Y-negated into OptB y0 frame.
        std_poly = _section_exterior(std, 36.05)
        if std_poly is not None:
            # Y-flip about 0 then shift by y0 - (-2.5) = y0+2.5... OptB y0=+2.5,
            # std cavity centre −2.5; remate uses Y-negate into OptB bed frame.
            from shapely.affinity import affine_transform
            # Y -> -Y (std to OptB Y-flip), no extra shift: OptB bed y0=+2.5
            # matches negated std y0=-2.5.
            std_poly = affine_transform(std_poly, [1, 0, 0, -1, 0, 0])
            cur_poly = _section_exterior(body, seat + 0.05)
            if cur_poly is not None:
                missing = std_poly.difference(cur_poly.buffer(0.05))
                missing = missing.difference(bay)
                if (not missing.is_empty) and missing.area > 1.0:
                    fill = _extrude_poly(missing, 0.08)
                    if fill is not None:
                        fill.apply_translation([0.0, 0.0, seat - 0.02])
                        fill = fill.difference(lid_p, engine="manifold")
                        if fill.is_volume:
                            body = body.union(fill, engine="manifold")
                            print(f"  missing land-plate area={missing.area:.1f}")
                        else:
                            print("  missing land non-volume; skip")
                else:
                    print("  missing land empty")
            else:
                print("  missing land: no current section")
        else:
            print("  missing land: no std section")
    except Exception as exc:
        print("  missing land fill failed:", exc)
    if not body.is_volume:
        print("  WARN: body non-volume after land fills")
    return body


def _stitch_walls_outside_lid(body, y0: float, seat: float):
    lid_poly = _lid_poly()
    if lid_poly is None:
        return body
    lid_buf = lid_poly.buffer(0.40)
    parts = []
    for y_sign in (-1.0, +1.0):
        yc = y0 + y_sign * 43.0
        band = shapely_box(-36.0, yc - 5.0, 36.0, yc + 5.0)
        cav = shapely_box(
            -0.5 * CAV_X, y0 - 0.5 * CAV_Y,
            0.5 * CAV_X, y0 + 0.5 * CAV_Y,
        ).buffer(0.5)
        poly = band.difference(lid_buf).difference(cav)
        if poly.is_empty:
            continue
        slab = _extrude_poly(poly, seat + 0.15)
        if slab is not None:
            parts.append(slab)
    if not parts:
        print("  wall stitch: empty")
        return body
    collar = parts[0] if len(parts) == 1 else trimesh.util.concatenate(parts)
    body = body.union(collar, engine="manifold")
    print("  Y-end wall feet stitched outside lid")
    return body


def _wall_foot_boxes(body, y0: float, seat: float, lid_p=None):
    """Close remaining under-lid deck/wall 0.05 gaps at Y− end tongue feet.

    Boxes stay ≥0.55 inside tongue outer so rabbet clearance is untouched.
    Only the known gap clusters at y≈−41, |x|≈20..24 (lid-empty in z≥0).
    """
    del y0, lid_p
    # Stay inside tongue outer (y≳−41.2 after shave): centre y=−40.5, half-Y=0.4.
    for sx in (-1.0, +1.0):
        box = trimesh.creation.box(extents=(5.0, 0.8, seat + 0.05))
        box.apply_translation([sx * 22.0, -40.5, 0.5 * (seat + 0.05)])
        if not box.is_volume:
            continue
        try:
            body = body.union(box, engine="manifold")
            print(f"  wall-foot box @ x={sx*22:.0f},y=-40.5")
        except Exception as exc:
            print("  wall-foot box failed:", exc)
    return body


def _patch_bosses(body, cols, seat: float):
    pad_r = 0.5 * BOSS_SPOT_D + 1.0
    spot_r = 0.5 * BOSS_SPOT_D
    pad_h = INSERT_DEPTH + 1.5
    wipe_r = pad_r + 0.5
    chamfer_h = 1.20
    for i, (x, y) in enumerate(cols):
        body = body.difference(
            _cyl(wipe_r, seat - 0.05, (x, y, 0.05)), engine="manifold",
        )
        body = body.union(_cyl(pad_r, pad_h, (x, y, seat)), engine="manifold")
        spot = _cyl(spot_r, BOSS_RECESS + 0.02, (x, y, seat))
        core = _cyl(0.5 * INSERT_D + 0.15, BOSS_RECESS + 0.2, (x, y, seat - 0.05))
        body = body.difference(
            spot.difference(core, engine="manifold"), engine="manifold",
        )
        top_z = seat + pad_h
        cham = _cone_frustum(
            pad_r + 0.05, pad_r - chamfer_h, chamfer_h,
            (x, y, top_z - chamfer_h),
        )
        keep = _cyl(
            pad_r - chamfer_h - 0.05, chamfer_h + 0.4,
            (x, y, top_z - chamfer_h - 0.2),
        )
        try:
            body = body.difference(
                cham.difference(keep, engine="manifold"), engine="manifold",
            )
        except Exception as exc:
            print(f"  chamfer {i} soft-fail:", exc)
        body = body.difference(
            _cyl(0.5 * INSERT_D, pad_h + seat + 0.5, (x, y, 0.0)),
            engine="manifold",
        )
        print(f"  boss pad+spot+chamfer {i} @ ({x:.0f},{y:.0f})")
    return body


def _chamfer_cavity_shelves(body):
    """≥45° chamfer of flat ceilings at (±22,−35) Z≈20.5–21.2."""
    z0 = 20.55
    for x, y in [(22.0, -35.0), (-22.0, -35.0)]:
        try:
            # Wide hole through the thin slab, then 45° cone on the rim.
            body = body.difference(
                _cyl(8.5, 1.5, (x, y, z0 - 0.15)), engine="manifold",
            )
            cone = _cone_frustum(8.5 + 3.5, 8.5, 3.5, (x, y, z0 - 3.5))
            body = body.difference(cone, engine="manifold")
            print(f"  shelf hole+≥45° @ ({x:.0f},{y:.0f})")
        except Exception as exc:
            print(f"  shelf chamfer fail: {exc}")
    return body


def _bay_clear_and_seat(body, land_z: float):
    """Clear bay cavity, ring land at land_z, ≥45° wall-rooted corbel, tongue/shock.

    No flat downfacing slab over cavity air: land is a RING rooted to the side
    walls by a stair corbel (run=rise per step). Cover flange mates on the ring.
    """
    LAND_W = 2.2
    CHAM = 7.0
    N = 12
    dz = CHAM / N
    outer = _stad(COVER_W + 0.8, COVER_L + 0.8, COVER_R + 0.3)
    inner = _stad(
        COVER_W + 0.8 - 2 * LAND_W,
        COVER_L + 0.8 - 2 * LAND_W,
        max(COVER_R + 0.3 - LAND_W, 0.4),
    )
    # Deep clear of old roof/plugs down to ~deck shelf so no floating ceiling remains.
    clearer = _extrude_poly(outer.buffer(0.5), land_z + 2.5 - 21.0)
    if clearer is not None:
        clearer.apply_translation([0.0, 0.0, 21.0])
        body = body.difference(clearer, engine="manifold")
        print("  bay cavity cleared to Z≈21 (no floating slab)")

    # Thin land RING — top face at land_z (NOT a solid stadium plate).
    ring = outer.difference(inner)
    plate = _extrude_poly(ring, 0.35)
    if plate is not None:
        plate.apply_translation([0.0, 0.0, land_z - 0.35])
        body = body.union(plate, engine="manifold")
        print(f"  bay land RING area={ring.area:.1f}")

    # ≥45° corbel: under-land fill + outside grow (run=rise) rooted to walls.
    z_land_bot = land_z - 0.35
    corb = None
    for i in range(N):
        d_mid = (i + 0.5) * dz
        under = outer.difference(inner)
        outside = outer.buffer(d_mid + 0.01).difference(outer)
        layer_poly = unary_union([under, outside])
        layer = _extrude_poly(layer_poly, dz + 0.05)
        if layer is None:
            continue
        layer.apply_translation([0.0, 0.0, z_land_bot - (i + 1) * dz - 0.02])
        corb = layer if corb is None else corb.union(layer, engine="manifold")
    if corb is not None:
        body = body.union(corb, engine="manifold")
        print(f"  bay ≥45° wall corbel CHAM={CHAM:.1f} N={N}")

    # Bay tongue (slightly undersize for 0.28 clear).
    BAY_IN0 = TONGUE_IN0 + 0.12
    BAY_IN1 = TONGUE_IN1 + 0.12
    ring_bay = _stad(
        COVER_W - 2 * BAY_IN0, COVER_L - 2 * BAY_IN0, max(COVER_R - BAY_IN0, 0.4),
    ).difference(
        _stad(
            COVER_W - 2 * BAY_IN1, COVER_L - 2 * BAY_IN1, max(COVER_R - BAY_IN1, 0.3),
        )
    )
    bay_t = _extrude_poly(ring_bay, TONGUE_H)
    if bay_t is not None:
        bay_t.apply_translation([0.0, 0.0, land_z])
        body = body.union(bay_t, engine="manifold")
        print(f"  bay tongue IN0={BAY_IN0:.2f}")
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        pad_h = CHAM + 0.4
        body = body.union(
            _cyl(0.5 * BOSS_SPOT_D + 1.2, pad_h, (x, y, land_z - pad_h)),
            engine="manifold",
        )
        # ≥45° underside chamfer on bay boss pads.
        try:
            body = body.difference(
                _cone_frustum(
                    0.5 * BOSS_SPOT_D + 1.3,
                    max(0.5 * BOSS_SPOT_D + 1.2 - min(pad_h, 4.0) * 0.9, 1.0),
                    min(pad_h, 4.0),
                    (x, y, land_z - pad_h),
                ),
                engine="manifold",
            )
        except Exception as exc:
            print(f"  bay boss chamfer soft-fail {i}:", exc)
        body = body.difference(
            _cyl(0.5 * BOSS_SPOT_D, BOSS_RECESS + 0.05, (x, y, land_z - BOSS_RECESS)),
            engine="manifold",
        )
        body = body.difference(
            _cyl(0.5 * INSERT_D, pad_h + 1.0, (x, y, land_z - pad_h - 0.5)),
            engine="manifold",
        )
        body = body.difference(
            _cyl(0.5 * BOSS_SPOT_D + 0.15, 2.5, (x, y, land_z + TONGUE_H + 0.05)),
            engine="manifold",
        )
        print(f"  bay boss {i} @ ({x:.0f},{y:.0f})")
    body = body.difference(
        _cyl(0.5 * SHOCK_BORE_D, INSERT_DEPTH + 2.0, (0.0, 0.0, land_z - INSERT_DEPTH - 1.0)),
        engine="manifold",
    )
    body = body.difference(
        _cyl(0.5 * SHOCK_FLANGE_SEAT_D, BOSS_RECESS + 0.05,
             (0.0, 0.0, land_z - BOSS_RECESS)),
        engine="manifold",
    )
    body = body.difference(
        _cyl(0.5 * SHOCK_FLANGE_SEAT_D + 0.2, 2.5,
             (0.0, 0.0, land_z + TONGUE_H + 0.05)),
        engine="manifold",
    )
    print("  shock Ø8.05 bore + flange seat cleared")
    return body


def mirror_R(src_l, dst_r):
    src = src_l.replace(".stl", ".ply")
    if not os.path.isfile(src):
        src = src_l
    m = trimesh.load(src, force="mesh", process=False)
    T = np.array(
        [[-1.0, 0, 0, 0], [0, -1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
    )
    m.apply_transform(T)
    m.apply_translation([0.0, 0.0, -float(m.bounds[0, 2])])
    ply_r = dst_r.replace(".stl", ".ply")
    m.export(ply_r)
    m.export(dst_r)
    check = trimesh.load(ply_r, force="mesh", process=False)
    print(f"  R mirror ply_vol={check.is_volume}")
    return bool(check.is_volume)


def _write_seats_and_poses(body_h: float):
    seats_path = os.path.join(D6_STL, "optb_seats.json")
    seats = json.loads(open(seats_path).read()) if os.path.isfile(seats_path) else {}
    for side in ("L", "R"):
        s = seats.setdefault(side, {})
        s["cover_seat_z"] = float(COVER_SEAT_Z_46)
        s["body_h"] = float(body_h)
        s["lid_seat_z"] = float(OPTB_LID_SEAT_Z)
        s["tongue_tip_z"] = 0.0
        s["cover_h_print"] = 2.5
        s["cover_mating_from_bed"] = 0.0
        s["cover_h"] = 2.5
        s["cover_flange_seat_from_outer"] = 0.5
        s["plug_flange_underside_z"] = 5.5
        s["wire_gland_z"] = float(body_h)
        if side == "L":
            s["bed_cols"] = [list(c) for c in OPTB_BED_COLS_L]
            s["bed_y0"] = OPTB_BED_Y0_L
            s["bed_key_xy"] = list(OPTB_KEY_XY_L)
            s["wire_gland_y"] = 28.0
        else:
            s["bed_cols"] = [[-c[0], -c[1]] for c in OPTB_BED_COLS_L]
            s["bed_y0"] = -OPTB_BED_Y0_L
            s["bed_key_xy"] = [-OPTB_KEY_XY_L[0], -OPTB_KEY_XY_L[1]]
            s["wire_gland_y"] = -28.0
    with open(seats_path, "w") as f:
        json.dump(seats, f, indent=2)
        f.write("\n")
    print(f"  seats cover_seat_z={COVER_SEAT_Z_46}")

    if _D6 not in sys.path:
        sys.path.insert(0, _D6)
    import importlib
    import assembly as A
    importlib.reload(A)
    poses = A.all_assembly_poses()
    pose_json = {
        name: {
            "matrix_4x4": np.asarray(M, float).reshape(4, 4).tolist(),
            "translation_mm": np.asarray(M, float).reshape(4, 4)[:3, 3].tolist(),
        }
        for name, M in poses.items()
    }
    poses_path = os.path.join(D6_OUT, "assembly_poses.json")
    with open(poses_path, "w") as f:
        json.dump(pose_json, f, indent=2)
        f.write("\n")
    print(f"  wrote {poses_path}")
    world = os.path.join(D6_OUT, "world")
    os.makedirs(world, exist_ok=True)
    for name in (
        "pod_L_base_optB_curveUP", "pod_R_base_optB_curveUP",
        "optb_bay_cover_L", "optb_bay_cover_R",
        "jig_blank_shock_plug_L", "jig_blank_shock_plug_R",
        "pod_L_base", "pod_R_base",
    ):
        src = os.path.join(D6_STL, f"{name}.ply")
        if not os.path.isfile(src):
            src = os.path.join(D6_STL, f"{name}.stl")
        if name.startswith("jig_blank_shock_plug") and not os.path.isfile(src):
            src = os.path.join(D6_STL, "jig_blank_shock_plug_L.stl")
        if not os.path.isfile(src) or name not in poses:
            continue
        m = trimesh.load(src, force="mesh")
        w = m.copy()
        w.apply_transform(np.asarray(poses[name], float))
        w.export(os.path.join(world, f"{name}.stl"))
    tL = np.asarray(poses["optb_bay_cover_L"])[:3, 3]
    tP = np.asarray(poses["jig_blank_shock_plug_L"])[:3, 3]
    print(f"  cover_L translation {tL.round(3).tolist()}")
    print(f"  shock_L translation {tP.round(3).tolist()}")


def main():
    subprocess.check_call(
        ["git", "show", "749b9f4:hardware/rook/d6/stl/pod_L_base_optB_curveUP.ply"],
        stdout=open(os.path.join(D6_STL, "pod_L_base_optB_curveUP.ply"), "wb"),
    )
    body = trimesh.load(
        os.path.join(D6_STL, "pod_L_base_optB_curveUP.ply"), force="mesh"
    )
    assert body.is_volume, "749 seed must be volume"
    seat = float(OPTB_LID_SEAT_Z)
    y0 = float(OPTB_BED_Y0_L)
    cols = list(OPTB_BED_COLS_L)
    lid_p = _lid_in_base_frame()
    land_z = float(COVER_SEAT_Z_46)

    print("Shaving tongue for 0.28 rabbet…")
    body = _shave_tongue(body, y0, seat)
    print("Outer-land 360 plate…")
    body = _outer_land_plate_360(body, y0, seat, lid_p)
    print("Stitching walls outside lid…")
    body = _stitch_walls_outside_lid(body, y0, seat)
    print("Under-lid wall-foot boxes…")
    body = _wall_foot_boxes(body, y0, seat, lid_p=lid_p)
    print("Patching bosses…")
    body = _patch_bosses(body, cols, seat)
    print("Chamfering cavity shelves…")
    body = _chamfer_cavity_shelves(body)
    print("Bay clear + seat + shock bore…")
    body = _bay_clear_and_seat(body, land_z)
    assert body.is_volume, "patch lost volume"

    os.makedirs(OUT, exist_ok=True)
    ply_l = os.path.join(OUT, "pod_L_base_optB_curveUP.ply")
    out_l = os.path.join(OUT, "pod_L_base_optB_curveUP.stl")
    if not body.is_volume:
        # Last-resort repair before export.
        try:
            body.fill_holes()
        except Exception:
            pass
        print(f"  WARN pre-export vol={body.is_volume}")
    body.export(ply_l)
    body.export(out_l)
    shutil.copy2(out_l, os.path.join(D6_STL, "pod_L_base_optB_curveUP.stl"))
    shutil.copy2(ply_l, os.path.join(D6_STL, "pod_L_base_optB_curveUP.ply"))
    check = trimesh.load(ply_l, force="mesh", process=False)
    print(
        f"  L vol={body.is_volume} reload_vol={check.is_volume} "
        f"faces={len(body.faces)} h={body.bounds[1,2]-body.bounds[0,2]:.2f}"
    )
    assert check.is_volume, "PLY reload lost volume"

    promo_r = os.path.join(D6_STL, "pod_R_base_optB_curveUP.stl")
    print("Mirroring R…")
    mirror_R(ply_l, promo_r)
    shutil.copy2(promo_r, os.path.join(OUT, "pod_R_base_optB_curveUP.stl"))
    shutil.copy2(
        promo_r.replace(".stl", ".ply"),
        os.path.join(OUT, "pod_R_base_optB_curveUP.ply"),
    )

    _write_seats_and_poses(float(body.bounds[1, 2]))
    print("PASS")


if __name__ == "__main__":
    main()
