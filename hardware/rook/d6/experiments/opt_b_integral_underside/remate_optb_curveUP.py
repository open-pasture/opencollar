#!/usr/bin/env python3
"""Remate OptB curveUP from existing shell (no Blender).

Tongue tip on bed, land at TONGUE_H, Y-negated bed bosses, std-deck flare
enforcer. Mirrors R from L. Updates stl/ + optb_seats.json.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import transform, unary_union

_HERE = os.path.dirname(os.path.abspath(__file__))
_D6 = os.path.abspath(os.path.join(_HERE, "..", ".."))
D6_STL = os.path.join(_D6, "stl")
OUT = os.path.join(_HERE, "stl")

TONGUE_H = 1.20
# Locked to mating_rabbet.py (cap a189978 / pod Friday)
TONGUE_IN0, TONGUE_IN1 = 1.80, 3.20
BOSS_SPOT_D, BOSS_RECESS = 8.4, 0.40
INSERT_D, INSERT_DEPTH = 4.0, 5.6
POD_LID_W, POD_LID_L, POD_LID_R = 62.0, 91.0, 3.0
COVER_W, COVER_L, COVER_R = 28.0, 42.0, 2.0
OPTB_COVER_COLS = [(-10.0, 14.0), (8.0, 14.0), (-7.0, -14.0), (10.0, -12.0)]
SHOCK_BORE_D = 8.05
SHOCK_FLANGE_SEAT_D = 12.50
SHOCK_FLANGE_CB_DEPTH = 1.85
COVER_H = 2.5
WIRE_GLAND_Y_L, WIRE_GLAND_Y_R = 28.0, -28.0
OPTB_BED_COLS_L = [(-22.0, -36.0), (22.0, -36.0), (-19.0, 36.0), (22.0, 36.0)]
OPTB_BED_Y0_L = 2.5
OPTB_KEY_XY_L = (18.0, -28.0)
OPTB_LID_SEAT_Z = TONGUE_H


def _cyl(r, h, at, segs=32):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=segs)
    c.apply_translation([at[0], at[1], at[2] + 0.5 * h])
    return c


def _section_exterior(mesh, z):
    """Largest filled XY exterior at plane z (3D-vertex projection, frame-safe)."""
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
        # Fallback via to_2D (may rotate frame — last resort only)
        try:
            planar, _ = sec.to_2D()
            polys = list(getattr(planar, "polygons_full", []) or [])
        except Exception:
            return None
        if not polys:
            return None
    u = unary_union(polys)
    if isinstance(u, MultiPolygon):
        u = max(u.geoms, key=lambda g: g.area)
    return Polygon(u.exterior)


def _std_yflip_deck_poly():
    """Std pod_L_base mating silhouette, Y-negated into OptB curveUP bed frame."""
    std = trimesh.load(os.path.join(D6_STL, "pod_L_base.stl"), force="mesh")
    poly = _section_exterior(std, 36.05)
    if poly is None:
        return None
    return transform(lambda x, y, z=None: (x, -y), poly)


def _extrude_poly(poly, h: float):
    """Extrude Polygon / MultiPolygon to a watertight mesh of height h."""
    if poly is None or poly.is_empty:
        return None
    geoms = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
    parts = []
    for g in geoms:
        if g is None or g.is_empty or g.area < 0.5:
            continue
        try:
            parts.append(trimesh.creation.extrude_polygon(g, height=float(h)))
        except Exception:
            try:
                parts.append(
                    trimesh.creation.extrude_polygon(g.buffer(0), height=float(h))
                )
            except Exception:
                pass
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else trimesh.util.concatenate(parts)


def _deck_fill_from_std(h: float):
    """Full std Y-flip silhouette extruded to h — restores flare + tip nest.

    Prior tip-only pads at |x|≈36.6 left a 33..35 gap under the lid flare
    (≈25 mm² Area(lid\\deck)). Unioning the std outline closes that gap and
    extends the +Y tip past lid y=48.
    """
    poly = _std_yflip_deck_poly()
    if poly is None:
        return None
    solid = _extrude_poly(poly, h)
    if solid is None:
        print("  deck fill extrude failed")
        return None
    print(f"  deck fill stdYflip area={poly.area:.1f} h={h}")
    return solid


def _deck_enforcer(h: float, y0: float):
    """Outer-shoulder only: std mating silhouette minus FULL lid outline.

    Must punch the flared lid envelope (±35), not just the 62×91 rabbet
    plan — otherwise the shoulder collides under the lid flare.
    """
    del y0  # retained for call-site compat; punch uses real lid outline
    poly = _std_yflip_deck_poly()
    if poly is None:
        return None

    # Frozen lid outline at mating (print frame, then Y already matches OptB)
    lid = trimesh.load(os.path.join(D6_STL, "pod_L_lid.stl"), force="mesh")
    # Mating near max Z of outer-down lid
    lid_mz = float(json.loads(
        open(os.path.join(D6_STL, "pod_lid_mating_z.json")).read()
    ).get("L", 5.8)) if os.path.isfile(os.path.join(D6_STL, "pod_lid_mating_z.json")) else 5.8
    lid_poly = _section_exterior(lid, lid_mz - 0.15)
    if lid_poly is None:
        # Fallback oversized stadium covering flare
        lid_poly = Polygon([
            (-36, -45), (36, -45), (36, 50), (-36, 50)
        ])

    # Shoulder = base outline \ inflated lid outline (0.40 mm XY clearance)
    lid_buf = lid_poly.buffer(0.40)
    shoulder = poly.difference(lid_buf)
    if shoulder.is_empty:
        print("  deck enforcer: empty shoulder")
        return None
    solid = _extrude_poly(shoulder, h)
    if solid is None:
        print("  deck enforcer extrude failed")
        return None
    print(
        f"  deck enforcer shoulder area={shoulder.area:.1f} h={h} "
        f"lid_punch_area={lid_buf.area:.1f}"
    )
    return solid


def remate(side: str, shell_path: str, out_path: str, land_nom: float) -> bool:
    shell = trimesh.load(shell_path, force="mesh")
    if not shell.is_volume:
        try:
            shell.fill_holes()
            shell.process(validate=True)
        except Exception:
            pass
    if not shell.is_watertight:
        print("shell not watertight")
        return False

    cols = list(OPTB_BED_COLS_L)
    y0 = OPTB_BED_Y0_L
    key_xy = OPTB_KEY_XY_L
    seat = float(OPTB_LID_SEAT_Z)
    land_z = float(land_nom) + seat

    shell.apply_translation([0.0, 0.0, seat])

    # Restore missing std Y-flip silhouette (flare corners + tip past lid y=48).
    # ONLY a thin land plate near z=seat — a full-height slab through z=0..seat
    # collides with the lid body (~26 mm³). Outer skirt (below) handles bed
    # adhesion outside lid+0.28.
    try:
        std_poly = _std_yflip_deck_poly()
        cur_poly = _section_exterior(shell, seat + 0.05)
        if std_poly is not None and cur_poly is not None:
            missing = std_poly.difference(cur_poly.buffer(0.05))
            if not missing.is_empty and missing.area > 1.0:
                # Thin plate spanning seat .. seat+0.45 — must NOT start below
                # seat or it kisses the lid underside (~1.2 mm³ sheet overlap).
                fill = _extrude_poly(missing, 0.45)
                if fill is not None:
                    fill.apply_translation([0.0, 0.0, seat])
                    shell = shell.union(fill, engine="manifold")
                    print(f"  missing land-plate area={missing.area:.1f} unioned")
            else:
                print(f"  missing deck fill empty/area={getattr(missing,'area',0)}")
        else:
            print("  missing deck fill: section failed — tip pad fallback")
            pads = []
            for sx in (-1.0, +1.0):
                pad = trimesh.creation.box(extents=(6.0, 20.0, 0.50))
                pad.apply_translation([sx * 34.5, 47.0, seat + 0.20])
                pads.append(pad)
            tip = trimesh.creation.box(extents=(70.0, 4.0, 0.50))
            tip.apply_translation([0.0, 49.5, seat + 0.20])
            pads.append(tip)
            shell = shell.union(trimesh.util.concatenate(pads), engine="manifold")
    except Exception as exc:
        print("  deck fill failed:", exc)

    # Outer printable shoulder (std \\ lid+0.40) — bed adhesion only.
    # Lives strictly outside the lid envelope. Use 0.40 (not 0.28) so remesh
    # chords on the flare cannot kiss the frozen lid (~0.1 mm³ sheet overlap
    # was observed at 0.28). XY registration is the male tongue, not the skirt.
    try:
        shoulder = _deck_enforcer(seat + 0.45, y0)
        if shoulder is not None:
            shell = shell.union(shoulder, engine="manifold")
            print("  outer shoulder skirt unioned")
    except Exception as exc:
        print("  shoulder skirt failed:", exc)

    # Male tongue tip on bed — rounded stadium ring (not a sharp box) so
    # corners match the lid groove. Width uses nominal TONGUE_IN0 (=0.30 mm
    # XY); length is 0.25 mm longer/side so ±Y shift lands in 0.22..0.35
    # (groove ends were ~0.50 mm open with symmetric insets).
    LEN_IN0 = TONGUE_IN0 - 0.22  # 1.58 — ±Y ~0.25..0.38 without end kiss
    LEN_IN1 = TONGUE_IN1 - 0.22  # 2.98
    tw_o = POD_LID_W - 2 * TONGUE_IN0
    tl_o = POD_LID_L - 2 * LEN_IN0
    tw_i = POD_LID_W - 2 * TONGUE_IN1
    tl_i = POD_LID_L - 2 * LEN_IN1
    r_o = max(POD_LID_R - TONGUE_IN0, 0.5)
    r_i = max(POD_LID_R - TONGUE_IN1, 0.4)

    def _stadium_poly(w, l, r):
        # Axis-aligned rounded rect of exact extents (w, l): shrink by r, buffer r.
        from shapely.geometry import box as shapely_box
        hw, hl = 0.5 * w, 0.5 * l
        rr = min(r, hw - 0.05, hl - 0.05)
        core = shapely_box(-hw + rr, -hl + rr, hw - rr, hl - rr)
        return core.buffer(rr)

    try:
        outer_p = _stadium_poly(tw_o, tl_o, r_o)
        inner_p = _stadium_poly(tw_i, tl_i, r_i)
        ring_p = outer_p.difference(inner_p)
        # Shift to y0
        ring_p = transform(lambda x, y, z=None: (x, y + y0), ring_p)
        bed_tongue = _extrude_poly(ring_p, seat)
        if bed_tongue is None:
            raise RuntimeError("stadium tongue extrude empty")
        body = shell.union(bed_tongue, engine="manifold")
        print(
            f"  stadium tongue outer={tw_o:.2f}x{tl_o:.2f}r{r_o:.2f} "
            f"inner={tw_i:.2f}x{tl_i:.2f}r{r_i:.2f}"
        )
    except Exception as exc:
        print("tongue failed:", exc)
        return False

    for i, (x, y) in enumerate(cols):
        try:
            body = body.difference(
                _cyl(0.5 * BOSS_SPOT_D, BOSS_RECESS + 0.15, (x, y, seat)),
                engine="manifold",
            )
            body = body.difference(
                _cyl(0.5 * INSERT_D, INSERT_DEPTH, (x, y, seat)),
                engine="manifold",
            )
        except Exception as exc:
            print(f"boss {i} failed:", exc)
            return False

    try:
        kx, ky = key_xy
        key = trimesh.creation.box(extents=(3.6, 4.6, 1.8))
        key.apply_translation([kx, ky, seat - 0.9])
        body = body.difference(key, engine="manifold")
    except Exception as exc:
        print("key failed:", exc)

    # Shell already has bay tongue from cavityUP. Re-cut shock bore + cover
    # bosses + wire gland at the raised land so blank-plug / wire_plug seat.
    print(f"  bay land_z={land_z:.2f} (shock/wire/boss re-cut only)")
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        try:
            body = body.difference(
                _cyl(0.5 * BOSS_SPOT_D, BOSS_RECESS + 0.25, (x, y, land_z)),
                engine="manifold",
            )
            body = body.difference(
                _cyl(0.5 * INSERT_D, INSERT_DEPTH, (x, y, land_z)),
                engine="manifold",
            )
        except Exception as exc:
            print(f"  bay boss {i} failed:", exc)
            return False
    try:
        # Through-land shock bore: cut both +Z (roof) and −Z (into cavity).
        body = body.difference(
            _cyl(0.5 * SHOCK_BORE_D, INSERT_DEPTH + 1.0, (0.0, 0.0, land_z - INSERT_DEPTH)),
            engine="manifold",
        )
        body = body.difference(
            _cyl(0.5 * SHOCK_FLANGE_SEAT_D, BOSS_RECESS + 0.15, (0.0, 0.0, land_z)),
            engine="manifold",
        )
    except Exception as exc:
        print("  shock failed:", exc)
        return False
    gy = WIRE_GLAND_Y_L
    try:
        # Modest gland bore from the high face — not a 20 mm tunnel through bed.
        z_top = float(body.bounds[1, 2])
        body = body.difference(
            _cyl(4.15, 8.0, (0.0, gy, z_top - 8.0)),
            engine="manifold",
        )
    except Exception as exc:
        print("  wire gland failed:", exc)
        return False

    body.apply_translation([0.0, 0.0, -float(body.bounds[0, 2])])
    # Also write a PLY that preserves volume for Boolean gates (binary STL
    # round-trip of ~1.5M-face manifold meshes often loses watertight).
    ply_path = out_path.replace(".stl", ".ply")
    try:
        body.export(ply_path)
    except Exception as exc:
        print("  ply export:", exc)
        ply_path = None
    body.export(out_path)
    check = trimesh.load(out_path, force="mesh", process=False)
    ply_ok = False
    if ply_path and os.path.isfile(ply_path):
        ply = trimesh.load(ply_path, force="mesh", process=False)
        ply_ok = bool(ply.is_volume)
        print(f"  ply wt={ply.is_watertight} vol={ply.is_volume}")
    print(
        f"  remate ok mem_wt={body.is_watertight} mem_vol={body.is_volume} "
        f"stl_wt={check.is_watertight} stl_vol={check.is_volume} "
        f"h={body.extents[2]:.2f} faces={len(body.faces)}"
    )
    return bool(body.is_volume or ply_ok)


def _top_solid_from_above(mesh, x, y, z_lo=15.0):
    """First solid hit via ray from max-Z downward (bay/gland faces)."""
    z_hi = float(mesh.bounds[1, 2]) + 1.0
    origins = np.array([[x, y, z_hi]], float)
    dirs = np.array([[0.0, 0.0, -1.0]], float)
    locs, _, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=True)
    if locs is None or len(locs) == 0:
        return None
    zs = sorted((float(z) for z in np.atleast_2d(locs)[:, 2]), reverse=True)
    for z in zs:
        if z >= z_lo:
            return z
    return zs[0] if zs else None


def _measure_land_z(path):
    m = trimesh.load(path, force="mesh", process=False)
    angs = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    tops = []
    for a in angs:
        x, y = 11.0 * math.cos(a), 18.0 * math.sin(a)
        found = _top_solid_from_above(m, x, y, z_lo=20.0)
        if found is not None and found > 25.0:
            tops.append(found)
    return float(np.median(tops)) if tops else float(m.bounds[1, 2]) - 2.0


def _measure_wire_gland_z(path, side):
    m = trimesh.load(path, force="mesh", process=False)
    gy = WIRE_GLAND_Y_L if side == "L" else WIRE_GLAND_Y_R
    vals = []
    for a in np.linspace(0, 2 * math.pi, 12, endpoint=False):
        x = 8.0 * math.cos(a)
        y = gy + 8.0 * math.sin(a)
        found = _top_solid_from_above(m, x, y, z_lo=25.0)
        if found is not None and found > 28.0:
            vals.append(found)
    return float(np.median(vals)) if vals else float(m.bounds[1, 2]) - 0.8


def mirror_R(src_l, dst_r):
    # Prefer PLY source (volume-stable); fall back to STL.
    # X+Y mirror ≡ 180° about Z (det = +1) — do NOT invert winding.
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


def main():
    shell = os.path.join(OUT, "pod_L_base_optB_shell.stl")
    out_l = os.path.join(OUT, "pod_L_base_optB_curveUP.stl")
    land_nom = 30.8  # prior bay land before seat raise
    print("Remating L…")
    ok = remate("L", shell, out_l, land_nom)
    if not ok:
        sys.exit(1)
    promo_l = os.path.join(D6_STL, "pod_L_base_optB_curveUP.stl")
    shutil.copy2(out_l, promo_l)
    ply_l = out_l.replace(".stl", ".ply")
    if os.path.isfile(ply_l):
        shutil.copy2(ply_l, os.path.join(D6_STL, "pod_L_base_optB_curveUP.ply"))

    out_r = os.path.join(OUT, "pod_R_base_optB_curveUP.stl")
    promo_r = os.path.join(D6_STL, "pod_R_base_optB_curveUP.stl")
    print("Mirroring R…")
    if not mirror_R(ply_l if os.path.isfile(ply_l) else promo_l, promo_r):
        print("R mirror non-volume (continuing)")
    if os.path.isfile(promo_r):
        shutil.copy2(promo_r, out_r)
    ply_r = promo_r.replace(".stl", ".ply")
    if os.path.isfile(ply_r):
        shutil.copy2(ply_r, os.path.join(OUT, "pod_R_base_optB_curveUP.ply"))

    # Cover sits just above the raised bay land (design land_nom+seat; bump
    # +0.25 so remesh fuzz cannot kiss the cover).
    seat = float(OPTB_LID_SEAT_Z)
    cover_seat_l = land_nom + seat + 0.25  # 32.25 — clears remesh fuzz
    body_h = float(trimesh.load(ply_l if os.path.isfile(ply_l) else promo_l, force="mesh").bounds[1, 2])
    # Flange seats on the high-Z saddle face near body top (measured channel
    # is roomy; z≈body_h keeps the frozen Ø7.6 plug clear of the walls).
    wire_z_l = body_h
    print(f"  cover_seat_z → {cover_seat_l:.2f} wire_gland_z → {wire_z_l:.2f}")
    seats = {}
    for side in ("L", "R"):
        cols = [list(c) for c in OPTB_COVER_COLS]
        bed_cols = [list(c) for c in OPTB_BED_COLS_L]
        bed_y0 = OPTB_BED_Y0_L
        bed_key = list(OPTB_KEY_XY_L)
        gy = WIRE_GLAND_Y_L
        if side == "R":
            cols = [[-x, -y] for x, y in OPTB_COVER_COLS]
            bed_cols = [[-x, -y] for x, y in OPTB_BED_COLS_L]
            bed_y0 = -OPTB_BED_Y0_L
            bed_key = [-OPTB_KEY_XY_L[0], -OPTB_KEY_XY_L[1]]
            gy = WIRE_GLAND_Y_R
        seats[side] = {
            "cover_seat_z": cover_seat_l,
            "body_h": body_h,
            "cols": cols,
            "cover_h_print": COVER_H,
            "cover_mating_from_bed": 0.0,
            "cover_h": COVER_H,
            # 0.5 matches the cover CB floor (not full flange thickness).
            "cover_flange_seat_from_outer": 0.5,
            "plug_flange_underside_z": 5.5,
            "wire_gland_z": wire_z_l,
            "wire_gland_y": gy,
            "wire_gland_note": (
                "OptB curveUP: former skirt bed gland is on the high-Z saddle "
                "face after Rx(π). Channel is intentionally wider than the "
                "frozen Ø7.6 wire_plug stem (RTV strain relief); do not edit "
                "pod_*_wire_plug.stl."
            ),
            "lid_seat_z": float(OPTB_LID_SEAT_Z),
            "bed_cols": bed_cols,
            "bed_y0": float(bed_y0),
            "bed_key_xy": bed_key,
            "tongue_tip_z": 0.0,
        }
    body_h_r = float(
        trimesh.load(
            ply_r if os.path.isfile(ply_r) else promo_r, force="mesh", process=False
        ).bounds[1, 2]
    )
    seats["R"]["cover_seat_z"] = cover_seat_l
    seats["R"]["wire_gland_z"] = body_h_r
    seats["R"]["body_h"] = body_h_r

    with open(os.path.join(D6_STL, "optb_seats.json"), "w") as f:
        json.dump(seats, f, indent=2)
    print(json.dumps(seats, indent=2))
    print("PASS")


if __name__ == "__main__":
    main()
