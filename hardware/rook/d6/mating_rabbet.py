"""Shared 360° concentric tongue-and-groove rabbet (cap a189978 pattern).

Lid-referenced insets → 0.28 mm/wall XY clearance and 0.40 mm Z top clearance.
Import from pod.py / cw.py / opt_b builders. Do NOT change cap.py (frozen).
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
    """Union 360° raised tongue on base parting deck (lid-referenced)."""
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


def recess_insert_bosses(body, cols, z_parting, insert_d=4.0,
                         spot_d=BOSS_SPOT_D, recess=BOSS_RECESS,
                         depth=INSERT_BORE_DEPTH, prefix="bins"):
    """Spotface + insert bore so boss top sits `recess` below parting."""
    for i, (x, y) in enumerate(cols):
        oc.cut(body, oc.cylinder(
            f"{prefix}_spot{i}", spot_d, recess + 0.6,
            at=(x, y, z_parting - recess), anchor="bottom", segments=32,
        ))
        oc.cut(body, oc.cylinder(
            f"{prefix}_ins{i}", insert_d, depth + 0.3,
            at=(x, y, z_parting - recess - depth),
            anchor="bottom", segments=32,
        ))
    return body
