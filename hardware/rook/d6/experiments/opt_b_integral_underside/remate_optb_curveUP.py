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
INSERT_D, INSERT_DEPTH = 4.0, 5.9  # ≥5.8 mm heat-set depth gate
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
# Seed shell keeps std POD_Y0=−2.5 battery cavity; OptB lid/tongue use +2.5.
STD_CAVITY_Y0 = -2.5
CAV_X, CAV_Y = 58.0, 82.0
BOSS_PILLAR_R = 4.0          # ≥3.8 mm closed wall around Ø4 bore
BOSS_PILLAR_H = 22.0         # from land up into cavity (z_print 1.6..~20)


def _cyl(r, h, at, segs=32):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=segs)
    c.apply_translation([at[0], at[1], at[2] + 0.5 * h])
    return c


def _rounded_cavity_box(w, l, h, at_xy, z0, r=2.0):
    """Axis-aligned rounded box with bottom at z0 (height h)."""
    from shapely.geometry import box as shapely_box
    hw, hl = 0.5 * w, 0.5 * l
    rr = min(r, hw - 0.05, hl - 0.05)
    poly = shapely_box(-hw + rr, -hl + rr, hw - rr, hl - rr).buffer(rr)
    poly = transform(
        lambda x, y, z=None: (x + at_xy[0], y + at_xy[1]), poly
    )
    box = _extrude_poly(poly, h)
    if box is None:
        box = trimesh.creation.box(extents=(w, l, h))
        box.apply_translation([at_xy[0], at_xy[1], z0 + 0.5 * h])
        return box
    box.apply_translation([0.0, 0.0, z0])
    return box


def _realign_battery_cavity(shell, y0: float, seat: float):
    """Fill seed-shell cavity (std POD_Y0) and re-cut at OptB Y-flip centre.

    Frozen lid / bed tongue sit on y0=+2.5; the imported shell still has the
    battery pocket at POD_Y0=−2.5. Open the new cavity at the land plane
    (not seat+0.35) — a raised cavity floor kisses the lid underside.
    """
    # Fill old void (slightly oversized so remnant ledges disappear).
    fill_h = 28.0
    fill = _rounded_cavity_box(
        CAV_X + 2.5, CAV_Y + 2.5, fill_h,
        (0.0, STD_CAVITY_Y0), seat - 0.05, r=2.5,
    )
    shell = shell.union(fill, engine="manifold")
    print(
        f"  cavity fill at y={STD_CAVITY_Y0:+.1f} "
        f"({CAV_X + 2.5:.0f}x{CAV_Y + 2.5:.0f}x{fill_h:.0f})"
    )
    # Re-cut through the deck (from near bed) so no 1.15–1.55 membrane
    # remains under the lid. Pillars are re-added afterward.
    cut_h = 28.0
    cut = _rounded_cavity_box(
        CAV_X, CAV_Y, cut_h, (0.0, y0), 0.10, r=2.0,
    )
    shell = shell.difference(cut, engine="manifold")
    print(f"  cavity re-cut at y={y0:+.1f} through-deck ({CAV_X:.0f}x{CAV_Y:.0f})")
    return shell


def _bed_boss_pillars(body, cols, y0: float, seat: float):
    """Cavity-side M3 pads with +Z spotface (OptB land-at-bed).

    Lid solid fills z≲seat under the land; pads/pillars live strictly on the
    cavity side (z≥seat). Spotface empty seat..seat+0.40 at the annulus.
    """
    del y0  # webs omitted — sleeve/pad only (see patch_optb_boss_walls.py)
    pad_r = 0.5 * BOSS_SPOT_D + 1.0
    spot_r = 0.5 * BOSS_SPOT_D
    pad_h = INSERT_DEPTH + 1.5
    wipe_r = pad_r + 0.5
    for i, (x, y) in enumerate(cols):
        body = body.difference(
            _cyl(wipe_r, seat - 0.05, (x, y, 0.05)), engine="manifold",
        )
        pad = _cyl(pad_r, pad_h, (x, y, seat))
        body = body.union(pad, engine="manifold")
        spot = _cyl(spot_r, BOSS_RECESS + 0.02, (x, y, seat))
        core = _cyl(0.5 * INSERT_D + 0.15, BOSS_RECESS + 0.2, (x, y, seat - 0.05))
        body = body.difference(spot.difference(core, engine="manifold"), engine="manifold")
        body = body.difference(
            _cyl(0.5 * INSERT_D, pad_h + seat + 0.5, (x, y, 0.0)),
            engine="manifold",
        )
        print(f"  bed boss pad+spot {i} @ ({x:.0f},{y:.0f})")
    return body


def _clear_above_land_in_lid(body, y0: float, seat: float, cols, tongue_inner):
    """Remove cavity floor membranes / ribs under the lid — not the walls.

    XY is inset ≥2 mm from the cavity wall so Y-end walls stay continuous
    from the deck. Z band is a thin lid-kiss slab (seat−0.08 .. seat+0.55).
    Pillar keep-outs protect M3 sleeves.
    """
    from shapely.geometry import box as shapely_box

    del tongue_inner  # retained for call-site compat
    # Inset from cavity walls so we never notch the perimeter shell.
    inset = 2.5
    hw, hl = 0.5 * CAV_X - inset, 0.5 * CAV_Y - inset
    rr = min(1.5, hw - 0.05, hl - 0.05)
    poly = shapely_box(-hw + rr, -hl + rr + y0, hw - rr, hl - rr + y0).buffer(rr)
    clear_h = 0.65  # seat-0.08 → seat+0.57
    clearer = _extrude_poly(poly, clear_h)
    if clearer is None:
        return body
    clearer.apply_translation([0.0, 0.0, seat - 0.08])
    keep = []
    for x, y in cols:
        # Protect land ring + hole-fit sleeve (OD ~5.6 / 1.7).
        keep.append(_cyl(0.5 * BOSS_SPOT_D + 1.6, clear_h + 0.4, (x, y, seat - 0.15)))
    if keep:
        keep_m = keep[0] if len(keep) == 1 else trimesh.util.concatenate(keep)
        clearer = clearer.difference(keep_m, engine="manifold")
    body = body.difference(clearer, engine="manifold")
    print("  cleared cavity-floor membranes under lid (walls+pillars kept)")
    return body


def _stitch_walls_to_deck(body, y0: float, seat: float):
    """Close 0.05 mm air gaps where Y-end walls float above the deck."""
    from shapely.geometry import box as shapely_box

    # Thin collar rings at each Y-end wall foot, from bed to seat+0.15.
    parts = []
    for y_sign in (-1.0, +1.0):
        # Wall foot near |y|≈41–48 along the deck.
        yc = y0 + y_sign * 43.0
        poly = shapely_box(-30.0, yc - 4.0, 30.0, yc + 4.0)
        # Only the outer wall band (outside cavity).
        cav = shapely_box(-0.5 * CAV_X, y0 - 0.5 * CAV_Y,
                          0.5 * CAV_X, y0 + 0.5 * CAV_Y).buffer(0.5)
        poly = poly.difference(cav)
        if poly.is_empty:
            continue
        slab = _extrude_poly(poly, seat + 0.15)
        if slab is not None:
            parts.append(slab)
    if not parts:
        return body
    collar = parts[0] if len(parts) == 1 else trimesh.util.concatenate(parts)
    body = body.union(collar, engine="manifold")
    print("  Y-end wall feet stitched to deck")
    return body


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
        return (False, 0.0)

    cols = list(OPTB_BED_COLS_L)
    y0 = OPTB_BED_Y0_L
    key_xy = OPTB_KEY_XY_L
    seat = float(OPTB_LID_SEAT_Z)

    shell.apply_translation([0.0, 0.0, seat])
    # Bay land tracks the raised shell roof (not a stale hard-coded land_nom).
    # land_nom is retained as a floor so a damaged shell cannot drop the seat.
    try:
        tmp = os.path.join(OUT, "_optb_shell_raised_tmp.ply")
        shell.export(tmp)
        measured_land = _measure_land_z(tmp)
        try:
            os.remove(tmp)
        except OSError:
            pass
    except Exception:
        measured_land = float(land_nom) + seat
    if measured_land is not None and measured_land > 20.0:
        land_z = float(measured_land)
    else:
        land_z = float(land_nom) + seat
    print(f"  measured bay land={measured_land} → land_z={land_z:.3f}")

    # Battery cavity: seed shell is still on std POD_Y0=−2.5; move it to the
    # OptB Y-flip centre before deck/tongue/boss work so land_360_flush and
    # M3 pillars are not carved open.
    try:
        shell = _realign_battery_cavity(shell, y0, seat)
    except Exception as exc:
        print("  cavity realign failed:", exc)
        return (False, 0.0)

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
                # Hairline plate at the land only — taller slabs above seat
                # kiss the lid ceiling (46dc5f7 overlap).
                fill = _extrude_poly(missing, 0.08)
                if fill is not None:
                    fill.apply_translation([0.0, 0.0, seat - 0.02])
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

    # Male tongue tip on bed — stadium matching frozen lid groove.
    # 749b9f4 length insets (IN0−0.22) + X-inner −0.09 for remesh → 0.245–0.305
    # once above-land interference is gone (overlap forced shift=0 on 46dc5f7).
    IN0_X = TONGUE_IN0              # 1.80
    IN1_X = TONGUE_IN1 - 0.09       # 3.11
    IN0_Y = TONGUE_IN0 - 0.22       # 1.58
    IN1_Y = TONGUE_IN1 - 0.22       # 2.98
    tw_o = POD_LID_W - 2 * IN0_X
    tl_o = POD_LID_L - 2 * IN0_Y
    tw_i = POD_LID_W - 2 * IN1_X
    tl_i = POD_LID_L - 2 * IN1_Y
    r_o = max(POD_LID_R - min(IN0_X, IN0_Y), 0.5)
    r_i = max(POD_LID_R - min(IN1_X, IN1_Y), 0.4)

    def _stadium_poly(w, l, r):
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
        return (False, 0.0)

    # Pillars AFTER cavity re-cut: closed 360° wall + webs above land, then
    # −0.40 spotface + Ø4 bore into the +Z pillar (curveUP land on bed).
    try:
        body = _bed_boss_pillars(body, cols, y0, seat)
    except Exception as exc:
        print("boss pillars failed:", exc)
        return (False, 0.0)

    # Kill cavity-floor slabs / ribs / key bumps above the land under the lid.
    try:
        body = _clear_above_land_in_lid(body, y0, seat, cols, (tw_i, tl_i))
    except Exception as exc:
        print("  above-land clear failed:", exc)
        return (False, 0.0)

    # Stitch Y-end walls that floated 0.05 mm above the deck.
    try:
        body = _stitch_walls_to_deck(body, y0, seat)
    except Exception as exc:
        print("  wall stitch failed:", exc)

    try:
        kx, ky = key_xy
        # Key pocket only below the land — never a raised boss into the lid.
        key = trimesh.creation.box(extents=(3.6, 4.6, 1.8))
        key.apply_translation([kx, ky, seat - 0.9])
        body = body.difference(key, engine="manifold")
        body = body.difference(
            _cyl(3.5, 2.0, (kx, ky, seat + 0.02)), engine="manifold",
        )
    except Exception as exc:
        print("key failed:", exc)

    # Restore continuous bay cover land + male tongue, then re-cut shock/bosses.
    # Prior remates left a patchy deck (centre ~21.9 mm) while seats.json posed
    # the cover at a hard-coded 32.25 mm → open seam / floating cover.
    print(f"  bay land_z={land_z:.2f} (clear old bay + land plate + tongue)")
    try:
        from shapely.geometry import box as shapely_box

        def _stad(w, l, r):
            hw, hl = 0.5 * w, 0.5 * l
            rr = min(r, hw - 0.05, hl - 0.05)
            return shapely_box(-hw + rr, -hl + rr, hw - rr, hl - rr).buffer(rr)

        # Clear any prior bay tongue / ragged roof above land−0.5 inside cover.
        clearer = _extrude_poly(_stad(COVER_W + 2.0, COVER_L + 2.0, COVER_R + 1.0), 8.0)
        if clearer is not None:
            clearer.apply_translation([0.0, 0.0, land_z - 0.5])
            body = body.difference(clearer, engine="manifold")
            print("  old bay roof cleared")

        # Land plate top flush at land_z.
        land_poly = _stad(COVER_W + 0.8, COVER_L + 0.8, COVER_R + 0.3)
        land_plate = _extrude_poly(land_poly, 1.0)
        if land_plate is not None:
            land_plate.apply_translation([0.0, 0.0, land_z - 1.0])
            body = body.union(land_plate, engine="manifold")
            print(f"  bay land plate unioned area={land_poly.area:.1f}")
        # Bay tongue slightly under-size vs cover groove (0.28 clear + remesh pad).
        BAY_IN0 = TONGUE_IN0 + 0.12
        BAY_IN1 = TONGUE_IN1 + 0.12
        twc_o = COVER_W - 2 * BAY_IN0
        tlc_o = COVER_L - 2 * BAY_IN0
        twc_i = COVER_W - 2 * BAY_IN1
        tlc_i = COVER_L - 2 * BAY_IN1
        ring_bay = _stad(twc_o, tlc_o, max(COVER_R - BAY_IN0, 0.4)).difference(
            _stad(twc_i, tlc_i, max(COVER_R - BAY_IN1, 0.3))
        )
        bay_tongue = _extrude_poly(ring_bay, TONGUE_H)
        if bay_tongue is not None:
            bay_tongue.apply_translation([0.0, 0.0, land_z])
            body = body.union(bay_tongue, engine="manifold")
            print(f"  bay tongue unioned IN0={BAY_IN0:.2f}")
    except Exception as exc:
        print("  bay land/tongue failed:", exc)
        return (False, 0.0)
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        try:
            # Bay M3: pad flush with land_z; spotface floor at land_z−0.40.
            pad_h = 1.2
            pad = _cyl(0.5 * BOSS_SPOT_D + 1.2, pad_h, (x, y, land_z - pad_h))
            body = body.union(pad, engine="manifold")
            body = body.difference(
                _cyl(0.5 * BOSS_SPOT_D, BOSS_RECESS + 0.05,
                     (x, y, land_z - BOSS_RECESS)),
                engine="manifold",
            )
            body = body.difference(
                _cyl(0.5 * INSERT_D, INSERT_DEPTH + 0.05,
                     (x, y, land_z - BOSS_RECESS - INSERT_DEPTH)),
                engine="manifold",
            )
            # Vacuum debris above the bay tongue tip only — do not notch the
            # male tongue ring that may graze these columns.
            body = body.difference(
                _cyl(0.5 * BOSS_SPOT_D + 0.15, 2.5,
                     (x, y, land_z + TONGUE_H + 0.05)),
                engine="manifold",
            )
        except Exception as exc:
            print(f"  bay boss {i} failed:", exc)
            return (False, 0.0)
    try:
        body = body.difference(
            _cyl(0.5 * SHOCK_BORE_D, INSERT_DEPTH + 0.05,
                 (0.0, 0.0, land_z - INSERT_DEPTH)),
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
    except Exception as exc:
        print("  shock failed:", exc)
        return (False, 0.0)
    gy = WIRE_GLAND_Y_L
    try:
        z_top = float(body.bounds[1, 2])
        body = body.difference(
            _cyl(4.15, 8.0, (0.0, gy, z_top - 8.0)),
            engine="manifold",
        )
    except Exception as exc:
        print("  wire gland failed:", exc)
        return (False, 0.0)

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
    return (bool(body.is_volume or ply_ok), float(land_z))


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
    ok, land_z_l = remate("L", shell, out_l, land_nom)
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

    # Cover seats on remate land_z (+ hairline to avoid coplanar sheet overlap).
    # Do NOT re-measure after boss pads — pads pollute the land probe.
    cover_seat_l = float(land_z_l) + 0.02
    body_h = float(trimesh.load(ply_l if os.path.isfile(ply_l) else promo_l, force="mesh").bounds[1, 2])
    wire_z_l = body_h
    print(f"  cover_seat_z → {cover_seat_l:.2f} (land_z+0.02) wire_gland_z → {wire_z_l:.2f}")
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
