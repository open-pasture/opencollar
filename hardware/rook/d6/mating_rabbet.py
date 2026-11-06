"""Shared 360° concentric tongue-and-groove rabbet (cap a189978 pattern).

Lid-referenced insets → 0.28 mm/wall XY clearance and 0.40 mm Z top clearance.

Pod Friday fix: female groove on base (curveUP-printable on z=0), male tongue
on lid (prints outer-down so tongue is last layers). Cap/cw keep prior usage.
"""
from __future__ import annotations

import oc  # noqa: F401 — caller ensures oc is on path

# Locked clearances (match cap a189978)
LAND_W = 1.80
GROOVE_IN0, GROOVE_IN1, GROOVE_D = 1.52, 3.48, 1.60
TONGUE_IN0, TONGUE_IN1, TONGUE_H = 1.80, 3.20, 1.20
XY_CLEAR = 0.28          # (GROOVE_IN0 - TONGUE_IN0) == (TONGUE_IN1 - GROOVE_IN1)
Z_CLEAR = GROOVE_D - TONGUE_H  # 0.40
BOSS_RECESS = 0.40
BOSS_SPOT_D = 8.4
INSERT_BORE_DEPTH = 6.5
RABBET_SEGS = 32
# Closed-end 45° roof chamfer depth (parallel walls cover full tongue engagement)
CHAMFER_D = Z_CLEAR  # 0.40


def stadium_ring(name, w_out, l_out, r_out, w_in, l_in, r_in, h, z0,
                 segments=RABBET_SEGS, at_xy=(0.0, 0.0)):
    """Concentric stadium ring (outer − inner) as a solid for union/cut."""
    ax, ay = at_xy
    outer = oc.rounded_rect(
        f"{name}_o", (w_out, l_out, h), max(r_out, 0.5),
        at=(ax, ay, z0), anchor="bottom", segments=segments,
    )
    inner = oc.rounded_rect(
        f"{name}_i", (w_in, l_in, h + 0.6), max(r_in, 0.4),
        at=(ax, ay, z0 - 0.2), anchor="bottom", segments=segments,
    )
    return oc.cut(outer, inner)


def add_base_tongue(body, lid_w, lid_l, lid_r, z_parting, at_xy=(0.0, 0.0),
                    prefix="tongue"):
    """Union 360° raised tongue on base parting deck (lid-referenced).

    Used by cw (and legacy). Pods use cut_base_groove + add_lid_tongue instead.
    """
    tw_o, tl_o = lid_w - 2 * TONGUE_IN0, lid_l - 2 * TONGUE_IN0
    tw_i, tl_i = lid_w - 2 * TONGUE_IN1, lid_l - 2 * TONGUE_IN1
    tr_o, tr_i = lid_r - TONGUE_IN0, lid_r - TONGUE_IN1
    oc.union(body, stadium_ring(
        prefix, tw_o, tl_o, tr_o, tw_i, tl_i, tr_i,
        h=TONGUE_H + 0.2, z0=z_parting - 0.2, at_xy=at_xy,
    ))
    return body


def cut_lid_groove(lid, lid_w, lid_l, lid_r, at_xy=(0.0, 0.0), prefix="groove"):
    """Cut 360° mating groove into lid face at z=0 (print mating-down)."""
    gw_o, gl_o = lid_w - 2 * GROOVE_IN0, lid_l - 2 * GROOVE_IN0
    gw_i, gl_i = lid_w - 2 * GROOVE_IN1, lid_l - 2 * GROOVE_IN1
    gr_o, gr_i = lid_r - GROOVE_IN0, lid_r - GROOVE_IN1
    oc.cut(lid, stadium_ring(
        prefix, gw_o, gl_o, gr_o, gw_i, gl_i, gr_i,
        h=GROOVE_D + 0.4, z0=-0.2, at_xy=at_xy,
    ))
    return lid


def cut_base_groove(body, lid_w, lid_l, lid_r, z_parting, at_xy=(0.0, 0.0),
                    prefix="groove", chamfer=True):
    """Cut 360° female groove into base parting (opens at z_parting, into −Z).

    Parallel walls for full tongue engagement (TONGUE_H), then optional 45°
    closed-end chamfer in the remaining Z_CLEAR so curveUP (parting on bed)
    needs 0 support moves inside the groove.
    """
    gw_o, gl_o = lid_w - 2 * GROOVE_IN0, lid_l - 2 * GROOVE_IN0
    gw_i, gl_i = lid_w - 2 * GROOVE_IN1, lid_l - 2 * GROOVE_IN1
    gr_o, gr_i = lid_r - GROOVE_IN0, lid_r - GROOVE_IN1
    # Parallel engagement section (full tongue height + tiny float)
    eng_h = TONGUE_H + 0.05
    oc.cut(body, stadium_ring(
        f"{prefix}_eng", gw_o, gl_o, gr_o, gw_i, gl_i, gr_i,
        h=eng_h + 0.2, z0=z_parting - eng_h, at_xy=at_xy,
    ))
    if chamfer and CHAMFER_D > 0.05:
        # 45° step: inset walls by CHAMFER_D over depth CHAMFER_D
        cw_o = lid_w - 2 * (GROOVE_IN0 + CHAMFER_D)
        cl_o = lid_l - 2 * (GROOVE_IN0 + CHAMFER_D)
        cw_i = lid_w - 2 * (GROOVE_IN1 - CHAMFER_D)
        cl_i = lid_l - 2 * (GROOVE_IN1 - CHAMFER_D)
        cr_o = max(lid_r - GROOVE_IN0 - CHAMFER_D, 0.5)
        cr_i = max(lid_r - GROOVE_IN1 + CHAMFER_D, 0.4)
        if cw_o > cw_i + 1.0 and cl_o > cl_i + 1.0:
            oc.cut(body, stadium_ring(
                f"{prefix}_ch", cw_o, cl_o, cr_o, cw_i, cl_i, cr_i,
                h=CHAMFER_D + 0.15, z0=z_parting - GROOVE_D, at_xy=at_xy,
            ))
    return body


def add_lid_tongue(lid, lid_w, lid_l, lid_r, at_xy=(0.0, 0.0), prefix="tongue"):
    """Union 360° male tongue protruding −Z from lid mating face at z=0.

    Print outer-down: after flip_outer_down the tongue becomes last layers on
    the up-facing mating face (no overhang).
    """
    tw_o, tl_o = lid_w - 2 * TONGUE_IN0, lid_l - 2 * TONGUE_IN0
    tw_i, tl_i = lid_w - 2 * TONGUE_IN1, lid_l - 2 * TONGUE_IN1
    tr_o, tr_i = lid_r - TONGUE_IN0, lid_r - TONGUE_IN1
    oc.union(lid, stadium_ring(
        prefix, tw_o, tl_o, tr_o, tw_i, tl_i, tr_i,
        h=TONGUE_H + 0.05, z0=-TONGUE_H, at_xy=at_xy,
    ))
    return lid


def recess_insert_bosses(body, cols, z_parting, insert_d=4.0,
                         spot_d=BOSS_SPOT_D, recess=BOSS_RECESS,
                         depth=INSERT_BORE_DEPTH, prefix="bins",
                         through_tongue=True):
    """Spotface + insert bore so boss top sits `recess` below parting.

    When `through_tongue` (default), the spotface cutter extends above the
    parting deck through any male tongue (TONGUE_H) so a floating 0.6 mm
    bridge cannot remain at z_parting..z_parting+TONGUE_H (CW d6bae12 defect).
    """
    spot_h = recess + 0.6
    if through_tongue:
        # From (z_parting - recess) up past tongue tip + margin.
        spot_h = recess + TONGUE_H + 1.2
    for i, (x, y) in enumerate(cols):
        oc.cut(body, oc.cylinder(
            f"{prefix}_spot{i}", spot_d, spot_h,
            at=(x, y, z_parting - recess), anchor="bottom", segments=32,
        ))
        oc.cut(body, oc.cylinder(
            f"{prefix}_ins{i}", insert_d, depth + 0.3,
            at=(x, y, z_parting - recess - depth),
            anchor="bottom", segments=32,
        ))
    return body


def add_base_tongue_corbel(body, lid_w, lid_l, lid_r, z_parting,
                           at_xy=(0.0, 0.0), prefix="corbel",
                           depth=None, n_steps=5):
    """≤45° corbel under the male tongue so it is not a mid-air bridge.

    Single ring filling the 45° wedge AABB: outer on the solid perimeter
    land, inner at tongue_inner−depth. Depth capped so 2×18650 clearance
    is preserved. `n_steps` retained for call-site compat (unused).
    """
    del n_steps
    if depth is None:
        depth = float(TONGUE_IN1 - TONGUE_IN0) + 0.35  # ~1.75 mm
    depth = float(max(0.8, min(depth, 2.2)))
    ax, ay = at_xy
    wall_in0 = max(0.25, TONGUE_IN0 - 1.55)  # ≈0.25 → outer ~±30.75
    in_i = TONGUE_IN1 + depth
    in_o = wall_in0
    w_o, l_o = lid_w - 2 * in_o, lid_l - 2 * in_o
    w_i, l_i = lid_w - 2 * in_i, lid_l - 2 * in_i
    r_o, r_i = max(lid_r - in_o, 0.5), max(lid_r - in_i, 0.4)
    # Top of corbel stays ≤ z_parting − 0.02 so it never kisses the lid
    # land (h = depth + 0.15 with z0 = z_part − depth − 0.05 peaked +0.10
    # above land and created a ~67 mm³ sheet overlap with pod lids).
    oc.union(body, stadium_ring(
        prefix, w_o, l_o, r_o, w_i, l_i, r_i,
        h=depth, z0=z_parting - depth - 0.02, at_xy=(ax, ay),
    ))
    return body
