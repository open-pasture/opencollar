"""Option B: integral R220 L+R pod bases + bay covers.

Pipeline (manifold-preserving):
  1. Seed standard pod_*_base.stl
  2. Cut R220 + bay pocket + bay mating (cavityUP)
  3. Voxel remesh → watertight
  4. Flip curveUP; remesh → watertight
  5. Re-add bed tongue + bay tongue/bosses/shock
  6. Fine remesh (0.18–0.28) → watertight volume for Boolean gates

Run:
  blender --background --factory-startup --python build_opt_b.py
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_D6 = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.abspath(os.path.join(_D6, "..", "..", "common", "cad", "lib"))
_D5 = os.path.abspath(os.path.join(_D6, "..", "d5", "cad"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _D5)
sys.path.insert(0, _D6)

import oc  # noqa: E402
import build_d5 as d5  # noqa: E402
import mating_rabbet as MR  # noqa: E402

D6_STL = os.path.join(_D6, "stl")
OUT = os.path.join(_HERE, "stl")
os.makedirs(OUT, exist_ok=True)

SADDLE_R = 220.0
POD_LEN = 97.0
CUT_W = 50.0
COVER_W, COVER_L, COVER_R = 28.0, 42.0, 2.0
COVER_H = 2.5
LAND_FLOOR_T = 6.0
INNER_W, INNER_L = 18.0, 28.0
OPTB_COVER_COLS = [(-10.0, 14.0), (8.0, 14.0), (-7.0, -14.0), (10.0, -12.0)]
SHOCK_BORE_D = 8.05
SHOCK_BOSS_D = 14.0
SHOCK_FLANGE_SEAT_D = 12.50  # Ø12.5 counterbore for Ø12.0 blank-plug flange
SHOCK_FLANGE_CB_DEPTH = 1.85  # ≥ blank flange 1.80 → flush exterior seat
INSERT_D = 4.0
INSERT_DEPTH = 5.6
POD_LID_W, POD_LID_L, POD_LID_R = 62.0, 91.0, 3.0
# Wire gland (frozen plug STL) — physical seat after curveUP flip
WIRE_GLAND_Y_L = 28.0   # former −28 after Rx(π) about centre
WIRE_GLAND_Y_R = -28.0
# curveUP Rx(π) about X negates Y. Frozen pod_*_lid.stl is itself
# outer-down-flipped, so lid holes/groove sit on the Y-negated POD_COLS /
# POD_Y0. Bed bosses + tongue MUST use the same Y-negated frame.
OPTB_BED_COLS_L = [
    (-22.0, -36.0),  # was (+Y −X) before flip
    (22.0, -36.0),   # was (+Y +X)
    (-19.0, 36.0),   # poka (was −Y −X at −19)
    (22.0, 36.0),    # was (−Y +X)
]
OPTB_BED_Y0_L = 2.5          # −POD_Y0 after Rx(π)
OPTB_KEY_XY_L = (18.0, -28.0)  # Y-negated POD_KEY_XY
OPTB_LID_SEAT_Z = MR.TONGUE_H  # land at +1.20; tongue tip on bed z=0


def _sagitta(R, half):
    return float(R - math.sqrt(max(R * R - half * half, 0.0)))


def _import_stl(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    o = [x for x in bpy.data.objects if x not in before][0]
    o.name = name
    return o


def _prepare(obj, merge=0.02):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge)
    bmesh.ops.dissolve_degenerate(bm, dist=merge, edges=list(bm.edges))
    boundary = [e for e in bm.edges if len(e.link_faces) < 2]
    if boundary:
        bmesh.ops.holes_fill(bm, edges=boundary, sides=8)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def _remesh(obj, voxel=0.32):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    vox = obj.modifiers.new("optb_vox", "REMESH")
    vox.mode = "VOXEL"
    vox.voxel_size = voxel
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    return _prepare(obj, merge=max(0.015, voxel * 0.5))


def _bed_face_area(obj, z_tol=0.4, n_z_max=-0.85):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    lo = min(v.co.z for v in bm.verts)
    area = 0.0
    for f in bm.faces:
        if f.normal.z > n_z_max:
            continue
        zc = sum(v.co.z for v in f.verts) / 3.0
        if abs(zc - lo) > z_tol:
            continue
        area += f.calc_area()
    bm.free()
    return float(area), float(lo)


def cut_integral_r220(body, R=SADDLE_R, length=POD_LEN, width=CUT_W):
    sag = _sagitta(R, 0.5 * length)
    cyl_z = -math.sqrt(max(R * R - (0.5 * length) ** 2, 0.0))
    cutter = oc.cylinder(
        "optb_r_cut", 2.0 * R, width + 10.0,
        at=(0.0, 0.0, cyl_z), axis="X", segments=96, anchor="center",
    )
    band = oc.box(
        "optb_cut_band", (width + 8.0, length + 4.0, sag + 2.0),
        at=(0.0, 0.0, -1.0), anchor="bottom",
    )
    oc.intersect(cutter, band)
    oc.cut(body, cutter)
    return sag


def cut_bay_pocket(body, sag):
    land_z = float(max(sag, LAND_FLOOR_T + 1.0))
    rebate_w, rebate_l = COVER_W + 1.0, COVER_L + 1.0
    oc.cut(
        body,
        oc.rounded_rect(
            "optb_cover_rebate", (rebate_w, rebate_l, land_z + 0.5), 2.2,
            at=(0.0, 0.0, -0.5), anchor="bottom", segments=8,
        ),
    )
    floor = oc.rounded_rect(
        "optb_land_floor", (rebate_w - 0.2, rebate_l - 0.2, LAND_FLOOR_T), 2.0,
        at=(0.0, 0.0, land_z), anchor="bottom", segments=8,
    )
    oc.union(body, floor)
    oc.cut(
        body,
        oc.rounded_rect(
            "optb_inner_keep", (INNER_W, INNER_L, land_z + LAND_FLOOR_T + 2.0), 2.0,
            at=(0.0, 0.0, -0.5), anchor="bottom", segments=8,
        ),
    )
    return land_z, rebate_w, rebate_l


def apply_bay_mating_cavityUP(body, land_z):
    tw_o = COVER_W - 2 * MR.TONGUE_IN0
    tl_o = COVER_L - 2 * MR.TONGUE_IN0
    tw_i = COVER_W - 2 * MR.TONGUE_IN1
    tl_i = COVER_L - 2 * MR.TONGUE_IN1
    oc.union(body, MR.stadium_ring(
        "optb_bay_tongue", tw_o, tl_o, COVER_R - MR.TONGUE_IN0,
        tw_i, tl_i, COVER_R - MR.TONGUE_IN1,
        h=MR.TONGUE_H + 0.05, z0=land_z - MR.TONGUE_H,
    ))
    oc.union(body, oc.cylinder(
        "shock_boss", SHOCK_BOSS_D, LAND_FLOOR_T,
        at=(0.0, 0.0, land_z), anchor="bottom", segments=32,
    ))
    oc.cut(body, oc.cylinder(
        "shock_bore", SHOCK_BORE_D, LAND_FLOOR_T + 2.0,
        at=(0.0, 0.0, land_z - 0.5), anchor="bottom", segments=32,
    ))
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        oc.cut(body, oc.cylinder(
            f"optb_spot{i}", MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.25,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))
        oc.cut(body, oc.cylinder(
            f"optb_ins{i}", INSERT_D, INSERT_DEPTH + 0.2,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))


def flatten_parting_deck(body, probe_x=32.0, pad=0.05):
    """After curveUP flip the seed tongue tip sits on the bed and the true
    outer parting deck is elevated by ~TONGUE_H. Cut everything below the
    outer-deck plane so z=0 is a continuous 360° land enclosing the lid.
    """
    import bmesh
    lo, hi = oc.bounds(body)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    # Outer-wall verts (|x| large or |y| near ends) — their min Z is the deck.
    outer_z = [
        float(v.co.z) for v in bm.verts
        if abs(v.co.x) >= probe_x - 0.5 or abs(v.co.y) >= 42.0
    ]
    bm.free()
    if outer_z:
        deck_z = float(sorted(outer_z)[max(0, int(0.05 * len(outer_z)))])  # ~5th %ile
    else:
        deck_z = float(lo[2]) + MR.TONGUE_H
    # Only cut if the deck is meaningfully above the current bed (inverted tongue)
    if deck_z - float(lo[2]) < 0.35:
        print(f"  flatten_parting_deck: skip (deck_z={deck_z:.3f} ≈ bed)")
        oc.move(body, dz=-oc.bounds(body)[0][2])
        return float(deck_z)
    cut_z = float(deck_z) - pad
    oc.cut(
        body,
        oc.box(
            "optb_flatten_deck",
            (hi[0] - lo[0] + 8.0, hi[1] - lo[1] + 8.0, cut_z - lo[2] + 2.0),
            at=(0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), lo[2] - 1.0),
            anchor="bottom",
        ),
    )
    oc.move(body, dz=-oc.bounds(body)[0][2])
    print(f"  flatten_parting_deck: cut_z={cut_z:.3f} deck_z≈{deck_z:.3f}")
    return float(deck_z)


def _optb_bed_frame(side: str):
    """Y-negated lid-matching bed frame (L explicit; R = X+Y mirror of L)."""
    if side == "L":
        return list(OPTB_BED_COLS_L), OPTB_BED_Y0_L, OPTB_KEY_XY_L
    cols = [(-x, -y) for x, y in OPTB_BED_COLS_L]
    return cols, -OPTB_BED_Y0_L, (-OPTB_KEY_XY_L[0], -OPTB_KEY_XY_L[1])


def apply_curveUP_mating(body, side: str, land_z: float):
    """Tongue tip on bed (z=0), outer land at OPTB_LID_SEAT_Z, Y-negated bosses.

    Frozen pod_*_lid has a female groove and mates from −Z. Raising the shell
    by TONGUE_H before adding the tongue puts the tip on the build plate and
    the lid seat land at +1.20 mm (printable with the existing OptB supports
    + brim). Boss XY matches the outer-down lid holes (Y-negated POD_COLS).
    """
    cols, y0, key_xy = _optb_bed_frame(side)
    seat = float(OPTB_LID_SEAT_Z)
    # Raise flattened deck so land sits at +seat; tongue fills [0, seat].
    oc.move(body, dz=seat)
    land_z = float(land_z) + seat
    tw_o = POD_LID_W - 2 * MR.TONGUE_IN0
    tl_o = POD_LID_L - 2 * MR.TONGUE_IN0
    tw_i = POD_LID_W - 2 * MR.TONGUE_IN1
    tl_i = POD_LID_L - 2 * MR.TONGUE_IN1
    oc.union(body, MR.stadium_ring(
        f"optb_bed_tongue_{side}",
        tw_o, tl_o, POD_LID_R - MR.TONGUE_IN0,
        tw_i, tl_i, POD_LID_R - MR.TONGUE_IN1,
        h=seat, z0=0.0, at_xy=(0.0, y0),
    ))
    for i, (x, y) in enumerate(cols):
        # Spotface + bore open from the land into +Z (away from the lid).
        oc.cut(body, oc.cylinder(
            f"bed_spot{i}", MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.15,
            at=(x, y, seat), anchor="bottom", segments=24,
        ))
        oc.cut(body, oc.cylinder(
            f"bed_ins{i}", INSERT_D, INSERT_DEPTH,
            at=(x, y, seat), anchor="bottom", segments=24,
        ))
    kx, ky = key_xy
    oc.cut(body, oc.box(
        "optb_bed_key",
        (3.6, 4.6, 1.8),
        at=(kx, ky, seat - 1.6),
        anchor="bottom",
    ))
    tw_o = COVER_W - 2 * MR.TONGUE_IN0
    tl_o = COVER_L - 2 * MR.TONGUE_IN0
    tw_i = COVER_W - 2 * MR.TONGUE_IN1
    tl_i = COVER_L - 2 * MR.TONGUE_IN1
    oc.union(body, MR.stadium_ring(
        "optb_bay_tongue_up", tw_o, tl_o, COVER_R - MR.TONGUE_IN0,
        tw_i, tl_i, COVER_R - MR.TONGUE_IN1,
        h=MR.TONGUE_H + 0.05, z0=land_z,
    ))
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        oc.cut(body, oc.cylinder(
            f"top_spot{i}", MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.25,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))
        oc.cut(body, oc.cylinder(
            f"top_ins{i}", INSERT_D, INSERT_DEPTH,
            at=(x, y, land_z - 0.05), anchor="bottom", segments=24,
        ))
    oc.cut(body, oc.cylinder(
        "top_shock", SHOCK_BORE_D, INSERT_DEPTH + 1.0,
        at=(0, 0, land_z - 0.05), anchor="bottom", segments=32,
    ))
    # Receiving land for blank-plug stem (no flange CB on base — flange seats
    # in the bay cover's exterior Ø12.5 counterbore).
    oc.cut(body, oc.cylinder(
        "top_shock_spot", SHOCK_FLANGE_SEAT_D, MR.BOSS_RECESS + 0.15,
        at=(0, 0, land_z - 0.05), anchor="bottom", segments=32,
    ))


def service_lid(side: str):
    cover = oc.rounded_rect(
        f"optb_bay_cover_{side}", (COVER_W, COVER_L, COVER_H), COVER_R,
        at=(0, 0, 0), anchor="bottom", segments=16,
    )
    MR.cut_lid_groove(cover, COVER_W, COVER_L, COVER_R, prefix=f"optb_cov_groove_{side}")
    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        oc.cut(cover, oc.cylinder(
            f"h{i}", 3.4, COVER_H + 2.0, at=(x, y, -0.5), anchor="bottom", segments=16,
        ))
        oc.cut(cover, oc.cylinder(
            f"cb{i}", 6.2, 1.35, at=(x, y, COVER_H - 1.20), anchor="bottom", segments=16,
        ))
    oc.cut(cover, oc.cylinder(
        "plug_bore", SHOCK_BORE_D, COVER_H + 2.0, at=(0, 0, -0.5), anchor="bottom", segments=32,
    ))
    # Exterior Ø12.5 × 1.85 counterbore — blank flange seats flush from outside.
    oc.cut(cover, oc.cylinder(
        "plug_flange_seat", SHOCK_FLANGE_SEAT_D, SHOCK_FLANGE_CB_DEPTH + 0.05,
        at=(0, 0, COVER_H - SHOCK_FLANGE_CB_DEPTH), anchor="bottom", segments=32,
    ))
    oc.bake(cover)
    oc.move(cover, dz=-oc.bounds(cover)[0][2])
    return cover


def _measure_wire_gland_z(path, side: str):
    """Flange-seat Z = top of the gland pad land (outside the stem bore)."""
    import trimesh
    import numpy as np
    m = trimesh.load(path, force="mesh")
    gy = WIRE_GLAND_Y_L if side == "L" else WIRE_GLAND_Y_R
    # Probe the pad land at r≈7 (outside Ø8.2 bore, inside Ø16 pad)
    tops = []
    for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        x = 7.0 * np.cos(a)
        y = gy + 7.0 * np.sin(a)
        lo, hi = float(m.bounds[0, 2]), float(m.bounds[1, 2]) + 0.5
        found = None
        for _ in range(24):
            mid = 0.5 * (lo + hi)
            if bool(m.contains([[x, y, mid]])[0]):
                lo = mid
                found = mid
            else:
                hi = mid
        if found is not None:
            tops.append(found)
    if tops:
        return float(np.median(tops))
    return float(m.bounds[1, 2]) - 0.5


def _stadium_ring_mesh(w_out, l_out, r_out, w_in, l_in, r_in, h, z0, at_xy=(0.0, 0.0)):
    """Watertight concentric stadium ring via trimesh (manifold-ready)."""
    import trimesh
    ax, ay = at_xy
    outer = trimesh.creation.rounded_prism(
        height=h,
        extents=(w_out, l_out),
        radius=max(r_out, 0.5),
        sections=16,
    )
    # rounded_prism may not exist — fall back to box+cylinders stadium approx
    try:
        _ = outer.vertices
    except Exception:
        outer = None
    if outer is None or not hasattr(trimesh.creation, "rounded_prism"):
        outer = trimesh.creation.box(extents=(w_out, l_out, h))
        inner = trimesh.creation.box(extents=(w_in, l_in, h + 0.4))
    else:
        inner = trimesh.creation.rounded_prism(
            height=h + 0.4,
            extents=(w_in, l_in),
            radius=max(r_in, 0.4),
            sections=16,
        )
    outer.apply_translation([ax, ay, z0 + 0.5 * h])
    inner.apply_translation([ax, ay, z0 + 0.5 * h])
    ring = outer.difference(inner, engine="manifold")
    if ring is None or ring.is_empty:
        return None
    ring.remove_unreferenced_vertices()
    return ring


def _cyl(r, h, at, segs=32):
    import trimesh
    c = trimesh.creation.cylinder(radius=r, height=h, sections=segs)
    c.apply_translation([at[0], at[1], at[2] + 0.5 * h])
    return c


def _deck_enforcer_from_std(side: str, h: float, y0: float):
    """Outer-shoulder enforcer from std mating outline (Y-flipped).

    Lid plan is punched out so the male tongue channel stays clear.
    """
    import numpy as np
    import trimesh
    from shapely.geometry import Polygon, MultiPolygon
    from shapely.ops import unary_union, transform

    src = os.path.join(D6_STL, f"pod_{side}_base.stl")
    if not os.path.isfile(src):
        src = os.path.join(D6_STL, "pod_L_base.stl")
    std = trimesh.load(src, force="mesh")
    mz = 36.2
    try:
        sec = std.section(
            plane_origin=[0.0, 0.0, mz - 0.15],
            plane_normal=[0.0, 0.0, 1.0],
        )
    except Exception as exc:
        print(f"  deck enforcer section failed: {exc}")
        return None
    if sec is None:
        print("  deck enforcer: empty section")
        return None
    try:
        planar, _ = sec.to_2D()
    except Exception as exc:
        print(f"  deck enforcer to_2D failed: {exc}")
        return None
    polys = list(getattr(planar, "polygons_full", []) or [])
    if not polys:
        loops = getattr(planar, "discrete", None) or []
        best, best_a = None, -1.0
        for loop in loops:
            if loop is None or len(loop) < 4:
                continue
            xy = np.asarray(loop)[:, :2]
            a = 0.5 * abs(
                np.dot(xy[:, 0], np.roll(xy[:, 1], 1))
                - np.dot(xy[:, 1], np.roll(xy[:, 0], 1))
            )
            if a > best_a:
                best_a = float(a)
                best = Polygon(xy)
        if best is None:
            return None
        poly = best
    else:
        poly = unary_union(polys)
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda g: g.area)
        poly = Polygon(poly.exterior)
    poly = transform(lambda x, y, z=None: (x, -y), poly)
    try:
        solid = trimesh.creation.extrude_polygon(poly, height=float(h))
    except Exception as exc:
        print(f"  deck enforcer extrude failed: {exc}")
        return None
    cut = trimesh.creation.box(
        extents=(POD_LID_W + 1.0, POD_LID_L + 1.0, float(h) + 0.6)
    )
    cut.apply_translation([0.0, y0, 0.5 * float(h)])
    try:
        solid = solid.difference(cut, engine="manifold")
    except Exception as exc:
        print(f"  deck enforcer lid punch failed: {exc}")
        return None
    print(
        f"  deck enforcer: outer-shoulder area≈{poly.area:.1f} mm² h={h:.2f}"
    )
    return solid


def _apply_curveUP_mating_manifold(shell_path, out_path, side: str, land_z: float) -> bool:
    """Tongue tip on bed, land at OPTB_LID_SEAT_Z, Y-negated bosses, flare deck."""
    import trimesh
    import numpy as np

    shell = trimesh.load(shell_path, force="mesh")
    if not shell.is_volume:
        try:
            shell.fill_holes()
            shell.process(validate=True)
        except Exception:
            pass
    if not shell.is_watertight:
        print(f"  manifold mating: shell not watertight")
        return False

    cols, y0, key_xy = _optb_bed_frame(side)
    seat = float(OPTB_LID_SEAT_Z)
    land_z = float(land_z) + seat

    # 1) Raise shell so former z=0 deck becomes the lid seat at +seat.
    shell.apply_translation([0.0, 0.0, seat])

    # 2) Restore remesh-eroded strap-flare tip as an OUTER shoulder only
    #    (lid plan punched out so the male tongue channel stays clear).
    enforcer = _deck_enforcer_from_std("L", h=seat, y0=OPTB_BED_Y0_L)
    if side == "R" and enforcer is not None:
        enforcer.apply_scale([-1.0, -1.0, 1.0])
        enforcer.invert()
    if enforcer is not None:
        try:
            shell = shell.union(enforcer, engine="manifold")
        except Exception as exc:
            print(f"  deck enforcer union failed (continuing): {exc}")

    # 3) Male tongue tip on bed (z=0..seat) — enters frozen lid groove from +Z.
    tw_o = POD_LID_W - 2 * MR.TONGUE_IN0
    tl_o = POD_LID_L - 2 * MR.TONGUE_IN0
    tw_i = POD_LID_W - 2 * MR.TONGUE_IN1
    tl_i = POD_LID_L - 2 * MR.TONGUE_IN1
    bed_outer = trimesh.creation.box(extents=(tw_o, tl_o, seat))
    bed_outer.apply_translation([0.0, y0, 0.5 * seat])
    bed_inner = trimesh.creation.box(extents=(tw_i, tl_i, seat + 0.4))
    bed_inner.apply_translation([0.0, y0, 0.5 * seat])
    try:
        bed_tongue = bed_outer.difference(bed_inner, engine="manifold")
        body = shell.union(bed_tongue, engine="manifold")
    except Exception as exc:
        print(f"  bed tongue union failed: {exc}")
        return False

    # 4) Spotfaces + Ø4 insert bores from the land into +Z (lid-matching XY).
    for i, (x, y) in enumerate(cols):
        try:
            body = body.difference(
                _cyl(0.5 * MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.15, (x, y, seat)),
                engine="manifold",
            )
            body = body.difference(
                _cyl(0.5 * INSERT_D, INSERT_DEPTH, (x, y, seat)),
                engine="manifold",
            )
        except Exception as exc:
            print(f"  bed boss cut {i} failed: {exc}")
            return False

    # 5) Poka key recess on the land (matches flipped lid lug).
    try:
        kx, ky = key_xy
        key = trimesh.creation.box(extents=(3.6, 4.6, 1.8))
        key.apply_translation([kx, ky, seat - 0.9])
        body = body.difference(key, engine="manifold")
    except Exception as exc:
        print(f"  bed key cut failed (continuing): {exc}")

    # 6) Bay tongue / bosses / shock at raised land_z
    bw_o = COVER_W - 2 * MR.TONGUE_IN0
    bl_o = COVER_L - 2 * MR.TONGUE_IN0
    bw_i = COVER_W - 2 * MR.TONGUE_IN1
    bl_i = COVER_L - 2 * MR.TONGUE_IN1
    bay_o = trimesh.creation.box(extents=(bw_o, bl_o, MR.TONGUE_H + 0.05))
    bay_o.apply_translation([0.0, 0.0, land_z + 0.5 * (MR.TONGUE_H + 0.05)])
    bay_i = trimesh.creation.box(extents=(bw_i, bl_i, MR.TONGUE_H + 0.45))
    bay_i.apply_translation([0.0, 0.0, land_z + 0.5 * (MR.TONGUE_H + 0.05)])
    try:
        bay_tongue = bay_o.difference(bay_i, engine="manifold")
        body = body.union(bay_tongue, engine="manifold")
    except Exception as exc:
        print(f"  bay tongue union failed: {exc}")
        return False

    for i, (x, y) in enumerate(OPTB_COVER_COLS):
        try:
            body = body.difference(
                _cyl(0.5 * MR.BOSS_SPOT_D, MR.BOSS_RECESS + 0.25, (x, y, land_z)),
                engine="manifold",
            )
            body = body.difference(
                _cyl(0.5 * INSERT_D, INSERT_DEPTH, (x, y, land_z)),
                engine="manifold",
            )
        except Exception as exc:
            print(f"  bay boss cut {i} failed: {exc}")
            return False
    try:
        body = body.difference(
            _cyl(0.5 * SHOCK_BORE_D, INSERT_DEPTH + 1.0, (0.0, 0.0, land_z)),
            engine="manifold",
        )
        body = body.difference(
            _cyl(0.5 * SHOCK_FLANGE_SEAT_D, MR.BOSS_RECESS + 0.15, (0.0, 0.0, land_z)),
            engine="manifold",
        )
    except Exception as exc:
        print(f"  shock cut failed: {exc}")
        return False

    # Wire gland: stem bore only (RTV strain relief vs frozen Ø7.6 plug).
    gy = WIRE_GLAND_Y_L if side == "L" else WIRE_GLAND_Y_R
    try:
        z_top = float(body.bounds[1, 2])
        body = body.difference(
            _cyl(4.15, 20.0, (0.0, gy, z_top - 18.0)),
            engine="manifold",
        )
    except Exception as exc:
        print(f"  wire gland bore failed: {exc}")
        return False

    body.apply_translation([0.0, 0.0, -float(body.bounds[0, 2])])
    if not body.is_watertight:
        try:
            body.fill_holes()
            body.process(validate=True)
        except Exception:
            pass
    body.export(out_path)
    print(
        f"  manifold mating ok wt={body.is_watertight} vol={body.is_volume} "
        f"h={body.extents[2]:.2f} seat={seat:.2f} y0={y0} cols={cols}"
    )
    return bool(body.is_watertight and body.is_volume)


def flip_curve_up(obj):
    lo, hi = oc.bounds(obj)
    cx = 0.5 * (lo[0] + hi[0])
    cy = 0.5 * (lo[1] + hi[1])
    cz = 0.5 * (lo[2] + hi[2])
    R = Matrix.Rotation(math.pi, 4, "X")
    T1 = Matrix.Translation(Vector((-cx, -cy, -cz)))
    T2 = Matrix.Translation(Vector((cx, cy, cz)))
    obj.matrix_world = T2 @ R @ T1 @ obj.matrix_world
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    oc.move(obj, dz=-oc.bounds(obj)[0][2])


def _measure_land_z(path):
    import trimesh
    import numpy as np
    m = trimesh.load(path, force="mesh")
    angs = np.linspace(0, 2 * math.pi, 16, endpoint=False)
    tops = []
    for a in angs:
        x, y = 11.0 * math.cos(a), 11.0 * math.sin(a)
        lo, hi = float(m.bounds[0, 2]), float(m.bounds[1, 2])
        found = None
        for _ in range(22):
            mid = 0.5 * (lo + hi)
            if bool(m.contains([[x, y, mid]])[0]):
                lo = mid
                found = mid
            else:
                hi = mid
        if found is not None:
            tops.append(found)
    return float(np.median(tops)) if tops else float(m.bounds[1, 2]) - 2.0


def build_side(side: str, report: dict):
    src = os.path.join(D6_STL, f"pod_{side}_base.stl")
    oc.reset()
    body = _import_stl(src, f"pod_{side}_base_optB")
    oc.move(body, dz=-oc.bounds(body)[0][2])
    h_before = float(oc.bounds(body)[1][2])

    sag = cut_integral_r220(body)
    land_cav, rebate_w, rebate_l = cut_bay_pocket(body, sag)
    apply_bay_mating_cavityUP(body, land_cav)
    oc.bake(body)
    body = _remesh(body, voxel=0.32)
    oc.move(body, dz=-oc.bounds(body)[0][2])
    h_cavity = float(oc.bounds(body)[1][2])

    path_native = os.path.join(OUT, f"pod_{side}_base_optB_cavityUP.stl")
    oc.prepare_for_export(body, merge=1e-4)
    oc.export_stl(body, path_native)
    print(f"  {side} cavityUP wt={oc.check_stl_watertight(path_native).get('watertight')}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    oc.reset()
    body2 = _import_stl(path_native, f"pod_{side}_optB_flip")
    flip_curve_up(body2)
    body2 = _remesh(body2, voxel=0.32)
    oc.move(body2, dz=-oc.bounds(body2)[0][2])
    # Seed tongue tip is on the bed after flip — flatten so outer deck = z=0.
    flatten_parting_deck(body2)
    h_flip = float(oc.bounds(body2)[1][2])
    land_nom = float(max(h_flip - land_cav, MR.TONGUE_H + LAND_FLOOR_T))

    try:
        d5.emboss_glyph(body2, side, (0.0, -30.0, 0.7), size=8.0, depth=0.7)
        d5.emboss_glyph(body2, "ARROW", (0.0, 30.0, 0.7), size=6.0, depth=0.7)
        oc.bake(body2)
    except Exception as exc:
        print(f"  optB {side} glyph: {exc}")

    # Fine remesh the body shell BEFORE adding mating (same pattern as
    # standard pod export_part) so voxel remesh cannot fatten/erase the tongue.
    wt = {"watertight": False}
    path_flip = os.path.join(OUT, f"pod_{side}_base_optB_curveUP.stl")
    for vx in (0.22, 0.28, 0.35):
        body2 = _remesh(body2, voxel=vx)
        oc.move(body2, dz=-oc.bounds(body2)[0][2])
        # Re-flatten if remesh reintroduced sub-deck blobs
        flatten_parting_deck(body2)
        oc.prepare_for_export(body2, merge=1e-4)
        oc.export_stl(body2, path_flip)
        wt = oc.check_stl_watertight(path_flip)
        print(f"  {side} fine@{vx} wt={wt.get('watertight')} bad={wt.get('bad_edges')}")
        if wt.get("watertight"):
            break

    h_flip = float(oc.bounds(body2)[1][2])
    land_nom = float(max(h_flip - land_cav, MR.TONGUE_H + LAND_FLOOR_T))
    # Export watertight SHELL first — Blender mating booleans reopen the mesh.
    # Apply tongue/bosses/shock via manifold3d in Python so the result stays volume.
    oc.prepare_for_export(body2, merge=1e-4)
    shell_path = os.path.join(OUT, f"pod_{side}_base_optB_shell.stl")
    oc.export_stl(body2, shell_path)
    wt = oc.check_stl_watertight(shell_path)
    print(f"  {side} shell wt={wt.get('watertight')} bad={wt.get('bad_edges')}")
    path_flip = os.path.join(OUT, f"pod_{side}_base_optB_curveUP.stl")
    ok_m = _apply_curveUP_mating_manifold(shell_path, path_flip, side, land_nom)
    if not ok_m:
        # Fallback: Blender mating + remesh (may soften features)
        print(f"  {side} manifold mating failed — blender fallback")
        apply_curveUP_mating(body2, side, land_nom)
        for vx in (0.14, 0.18, 0.28):
            body2 = _remesh(body2, voxel=vx)
            oc.move(body2, dz=-oc.bounds(body2)[0][2])
            oc.prepare_for_export(body2, merge=1e-4)
            oc.export_stl(body2, path_flip)
            wt = oc.check_stl_watertight(path_flip)
            print(f"  {side} fallback@{vx} wt={wt.get('watertight')}")
            if wt.get("watertight"):
                break
    else:
        wt = oc.check_stl_watertight(path_flip)

    import trimesh as _tm
    _final = _tm.load(path_flip, force="mesh")
    h_final = float(_final.bounds[1, 2])
    cover_seat_z = _measure_land_z(path_flip)
    wire_gland_z = _measure_wire_gland_z(path_flip, side)
    area, _ = _bed_face_area(body2)
    promo = os.path.join(D6_STL, f"pod_{side}_base_optB_curveUP.stl")
    shutil.copy2(path_flip, promo)
    # Prefer trimesh volume/watertight — Blender STL checker can disagree
    # after manifold export.
    tm_ok = bool(_final.is_watertight and _final.is_volume)
    wt = {"watertight": tm_ok, "blender": wt, "trimesh_volume": _final.is_volume}

    bay = {
        "bay_w": rebate_w, "bay_l": rebate_l,
        "land_floor_t": LAND_FLOOR_T,
        "shock_bore_d": SHOCK_BORE_D,
        "cover_cols": [list(c) for c in OPTB_COVER_COLS],
        "cover_seat_z_curveUP": cover_seat_z,
        "body_h_curveUP": h_final,
        "h_cavityUP": h_cavity,
        "h_before": h_before,
        "land_cav": land_cav,
        "wire_gland_z": wire_gland_z,
        "wire_gland_y": WIRE_GLAND_Y_L if side == "L" else WIRE_GLAND_Y_R,
    }
    report["bodies"][f"pod_{side}_base_optB_curveUP"] = {
        "path": promo,
        "size_mm": [round(float(v), 2) for v in _final.extents],
        "watertight": wt,
        "first_layer_area_mm2": round(area, 1),
        "sagitta_mm": round(sag, 2),
        "bay": bay,
    }

    oc.reset()
    lid = service_lid(side)
    lid_path = os.path.join(OUT, f"optb_bay_cover_{side}.stl")
    oc.prepare_for_export(lid, merge=1e-4)
    oc.export_stl(lid, lid_path)
    promo_lid = os.path.join(D6_STL, f"optb_bay_cover_{side}.stl")
    shutil.copy2(lid_path, promo_lid)
    report["bodies"][f"optb_bay_cover_{side}"] = {
        "path": promo_lid,
        "size_mm": list(oc.size(lid)),
        "watertight": oc.check_stl_watertight(lid_path),
        "cols": [list(c) for c in OPTB_COVER_COLS],
        "cover_h": COVER_H,
    }
    # Manifold export can reload as non-volume under trimesh even when the
    # in-memory mesh was watertight — prefer the mating ok flag.
    ok = bool(ok_m or tm_ok)
    print(f"  {side} build_side return ok={ok} tm_ok={tm_ok} ok_m={ok_m}")
    return ok


def _mirror_optb_R_from_L(report: dict) -> bool:
    """If R failed to seal, derive R by X+Y mirror of the sealed L body/cover."""
    import trimesh
    src = os.path.join(D6_STL, "pod_L_base_optB_curveUP.stl")
    dst = os.path.join(D6_STL, "pod_R_base_optB_curveUP.stl")
    if not os.path.isfile(src):
        return False
    m = trimesh.load(src, force="mesh")
    # Match standard pod_R: Scale X=-1, Y=-1 (equivalent to 180° about Z)
    # X+Y mirror ≡ Rz(π) (det=+1) — do NOT invert winding.
    import numpy as _np
    _T = _np.array(
        [[-1.0, 0.0, 0.0, 0.0],
         [0.0, -1.0, 0.0, 0.0],
         [0.0, 0.0, 1.0, 0.0],
         [0.0, 0.0, 0.0, 1.0]],
        dtype=float,
    )
    m.apply_transform(_T)
    m.apply_translation([0.0, 0.0, -float(m.bounds[0, 2])])
    m.export(dst)
    shutil.copy2(dst, os.path.join(OUT, "pod_R_base_optB_curveUP.stl"))
    # Cover
    csrc = os.path.join(D6_STL, "optb_bay_cover_L.stl")
    cdst = os.path.join(D6_STL, "optb_bay_cover_R.stl")
    cm = trimesh.load(csrc, force="mesh")
    cm.apply_transform(_T)
    cm.apply_translation([0.0, 0.0, -float(cm.bounds[0, 2])])
    cm.export(cdst)
    shutil.copy2(cdst, os.path.join(OUT, "optb_bay_cover_R.stl"))
    # Clone bay meta with mirrored cols / gland Y
    bay_l = report["bodies"]["pod_L_base_optB_curveUP"]["bay"]
    cols_r = [[-x, -y] for x, y in bay_l["cover_cols"]]
    bay_r = dict(bay_l)
    bay_r["cover_cols"] = cols_r
    bay_r["wire_gland_y"] = WIRE_GLAND_Y_R
    bay_r["wire_gland_z"] = _measure_wire_gland_z(dst, "R")
    bay_r["cover_seat_z_curveUP"] = _measure_land_z(dst)
    bay_r["body_h_curveUP"] = float(m.bounds[1, 2])
    report["bodies"]["pod_R_base_optB_curveUP"] = {
        "path": dst,
        "size_mm": [round(float(v), 2) for v in m.extents],
        "watertight": {"watertight": bool(m.is_watertight)},
        "first_layer_area_mm2": report["bodies"]["pod_L_base_optB_curveUP"].get(
            "first_layer_area_mm2", 0.0
        ),
        "sagitta_mm": report["bodies"]["pod_L_base_optB_curveUP"].get("sagitta_mm", 0.0),
        "bay": bay_r,
        "derived_from": "mirror_L",
    }
    report["bodies"]["optb_bay_cover_R"] = {
        "path": cdst,
        "size_mm": [round(float(v), 2) for v in cm.extents],
        "watertight": {"watertight": bool(cm.is_watertight)},
        "cols": cols_r,
        "cover_h": COVER_H,
        "derived_from": "mirror_L",
    }
    print(f"  R derived by X+Y mirror of L; wt={m.is_watertight}")
    return bool(m.is_watertight)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    report = {
        "experiment": "opt_B_integral_R220_L_and_R",
        "warning": "DRAFT — assembly_check is geometry only, not fit/print proof.",
        "chosen_orientation": "curve_UP_cavity_DOWN",
        "bodies": {},
        "pass": True,
    }
    # Build L fully; derive R by X+Y mirror so L/R stay congruent and R
    # doesn't inherit flip/remesh non-manifold failure modes.
    ok_l = build_side("L", report)
    ok_r = False
    if ok_l:
        print("  Deriving R by X+Y mirror of sealed L")
        ok_r = _mirror_optb_R_from_L(report)
    if not (ok_l and ok_r):
        report["pass"] = False
        # Fallback: try a native R build if mirror failed
        if ok_l and not ok_r:
            print("  Mirror failed — attempting native R build")
            ok_r = build_side("R", report)
            report["pass"] = bool(ok_l and ok_r)
    seats = {}
    for side in ("L", "R"):
        key = f"pod_{side}_base_optB_curveUP"
        ckey = f"optb_bay_cover_{side}"
        if key not in report["bodies"] or ckey not in report["bodies"]:
            print(f"  skip seats[{side}]: missing body")
            report["pass"] = False
            continue
        bay = report["bodies"][key]["bay"]
        cover_meta = report["bodies"][ckey]
        cols = bay["cover_cols"]
        if side == "R":
            cols = [[-x, -y] for x, y in OPTB_COVER_COLS]
        bed_cols, bed_y0, bed_key = _optb_bed_frame(side)
        seats[side] = {
            "cover_seat_z": bay["cover_seat_z_curveUP"],
            "body_h": bay["body_h_curveUP"],
            "cols": cols,
            "cover_h_print": cover_meta["size_mm"][2],
            "cover_mating_from_bed": 0.0,
            "cover_h": COVER_H,
            # Exterior CB floor depth from outer face (= SHOCK_FLANGE_CB_DEPTH)
            "cover_flange_seat_from_outer": SHOCK_FLANGE_CB_DEPTH,
            "plug_flange_underside_z": 5.5,
            "wire_gland_z": bay.get("wire_gland_z", bay["body_h_curveUP"]),
            "wire_gland_y": bay.get(
                "wire_gland_y",
                WIRE_GLAND_Y_L if side == "L" else WIRE_GLAND_Y_R,
            ),
            "wire_gland_note": (
                "OptB curveUP: former skirt bed gland is on the high-Z saddle "
                "face after Rx(π). Channel is intentionally wider than the "
                "frozen Ø7.6 wire_plug stem (RTV strain relief); do not edit "
                "pod_*_wire_plug.stl."
            ),
            # Lid mates on the raised land; tongue tip stays on the bed.
            "lid_seat_z": float(OPTB_LID_SEAT_Z),
            "bed_cols": [list(c) for c in bed_cols],
            "bed_y0": float(bed_y0),
            "bed_key_xy": [float(bed_key[0]), float(bed_key[1])],
            "tongue_tip_z": 0.0,
        }
    report["optb_seats"] = seats
    with open(os.path.join(_HERE, "opt_b_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    with open(os.path.join(D6_STL, "optb_seats.json"), "w") as f:
        json.dump(seats, f, indent=2)
    shutil.copy2(
        os.path.join(D6_STL, "optb_bay_cover_L.stl"),
        os.path.join(D6_STL, "optb_bay_cover.stl"),
    )
    print(json.dumps(seats, indent=2))
    print("PASS" if report["pass"] else "FAIL")
    return report


if __name__ == "__main__":
    main()
