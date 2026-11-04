"""D7 continuous fairing loft (shared by pod.py + cw.py).

D6 built fairings as a constant-Y trapezoid prism (width taper lived in Z),
which reads as a square block bolted between bodies. D7 lofts along the run
so width eases W0→W1 with long tangents, soft end caps, and edge fillets
R >= 4 mm — D4_contoured_v3 style.

Parametric outline: FAIRING_* in assembly.py read POD_L / POD_W / PLAN_R /
CAP_W so a later slim-pod outline can re-loft without rewriting the solid.
"""
from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _HERE)

import oc  # noqa: E402
import assembly as A  # noqa: E402


def _smootherstep(t: float) -> float:
    """Zero 1st/2nd derivative at 0 and 1 — long tangent blend into neighbours."""
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _plan_outline(run: float, w0: float, w1: float, r0: float, r1: float,
                  n_side: int = 16, n_arc: int = 10):
    """Closed XY outline of a continuous wedge (CCW from +Z).

    Wide end at y = -run/2 (width w0), narrow at y = +run/2 (width w1).
    Side edges use smootherstep so the 88→66 taper blends into neighbours
    with low long tangents (no hard kink at the seam). Ends are stadium-rounded.
    """
    r0 = min(max(r0, 0.5), w0 / 2.0 - 0.2, run / 3.0)
    r1 = min(max(r1, 0.5), w1 / 2.0 - 0.2, run / 3.0)
    y0 = -run / 2.0
    y1 = +run / 2.0

    def width_at(y: float) -> float:
        t = (y - y0) / run
        return w0 + (w1 - w0) * _smootherstep(t)

    pts = []

    # +X side, wide → narrow (between end radii)
    y_a = y0 + r0
    y_b = y1 - r1
    for i in range(n_side + 1):
        y = y_a + (y_b - y_a) * (i / n_side)
        pts.append((width_at(y) / 2.0, y))

    # Narrow end (+Y) stadium arc: right shoulder → tip → left shoulder
    # Arc centre line at y = y1 - r1; right centre x = +(w1/2 - r1)
    for i in range(1, n_arc + 1):
        a = math.pi * i / n_arc  # 0..π ; skip 0 (already at +X shoulder)
        if a <= math.pi / 2.0:
            x = (w1 / 2.0 - r1) + r1 * math.cos(a)
        else:
            x = -(w1 / 2.0 - r1) + r1 * math.cos(a)
        y = (y1 - r1) + r1 * math.sin(a)
        pts.append((x, y))

    # -X side, narrow → wide
    for i in range(n_side + 1):
        y = y_b - (y_b - y_a) * (i / n_side)
        pts.append((-width_at(y) / 2.0, y))

    # Wide end (−Y) stadium arc: left shoulder → tip → right shoulder
    for i in range(1, n_arc + 1):
        a = math.pi + math.pi * i / n_arc  # π..2π ; skip π (already at -X)
        if a <= 3.0 * math.pi / 2.0:
            x = -(w0 / 2.0 - r0) + r0 * math.cos(a)
        else:
            x = (w0 / 2.0 - r0) + r0 * math.cos(a)
        y = (y0 + r0) + r0 * math.sin(a)
        pts.append((x, y))

    return pts


def _bevel_safe(obj, r: float, segments: int = 4) -> float:
    """Bevel all edges; fall back to smaller R if the modifier collapses."""
    for trial in (r, max(4.0, r * 0.85), 4.0):
        try:
            oc.bake(obj)
            vol0 = oc.volume_mm3(obj)
            oc.bevel(obj, trial, segments=segments)
            oc.apply_modifiers(obj)
            vol1 = oc.volume_mm3(obj)
            if vol1 > 0.5 * vol0 and vol1 > 100.0:
                return float(trial)
        except Exception:
            # Restore attempt: caller will prepare() anyway; try smaller R
            continue
    return 0.0


def fairing_body(name: str,
                 run: float | None = None,
                 w0: float | None = None,
                 w1: float | None = None,
                 h: float | None = None,
                 *,
                 edge_r: float | None = None,
                 plan_r0: float | None = None,
                 plan_r1: float | None = None,
                 top_crown: float | None = None,
                 bevel_oversize: float | None = None):
    """Continuous D4-style fairing wedge.

    Prints flat on its widest face (z=0 bed); slope walls need no large supports.
    Width tapers along Y (the bridge run), not as a vertical trapezoid block.
    """
    run = float(run if run is not None else A.FAIRING_RUN)
    w0 = float(w0 if w0 is not None else A.FAIRING_W0)
    w1 = float(w1 if w1 is not None else A.FAIRING_W1)
    h = float(h if h is not None else A.FAIRING_H)
    edge_r = float(edge_r if edge_r is not None else A.FAIRING_EDGE_R)
    plan_r0 = float(plan_r0 if plan_r0 is not None else A.FAIRING_PLAN_R0)
    plan_r1 = float(plan_r1 if plan_r1 is not None else A.FAIRING_PLAN_R1)
    top_crown = float(
        top_crown if top_crown is not None else getattr(A, "FAIRING_TOP_CROWN", 1.2)
    )
    # Bevel shrinks plan width; grow loft so finished outer ≈ design W0/W1.
    # Cap↔pod stadium (constant W, large plan R) barely shrinks — pass 0 there.
    over = float(
        bevel_oversize
        if bevel_oversize is not None
        else getattr(A, "FAIRING_BEVEL_OVERSIZE", 0.0)
    )
    w0 = w0 + over
    w1 = w1 + over

    outline = _plan_outline(run, w0, w1, plan_r0, plan_r1)
    f = oc.prism_z(name, outline, 0.0, h)

    # Soft top crown — shallow long-edge drop so the top isn't a flat slab
    if top_crown > 0.05:
        land = 0.55 * min(w0, w1)
        for sx in (-1.0, 1.0):
            oc.cut(f, oc.prism_y(f"{name}_crown{int(sx + 2)}", [
                (sx * land / 2.0, h + 0.5),
                (sx * (max(w0, w1) / 2.0 + 2.0), h + 0.5),
                (sx * (max(w0, w1) / 2.0 + 2.0), h - top_crown),
                (sx * land / 2.0, h + 0.05),
            ], run + 4.0))

    applied = _bevel_safe(f, max(edge_r, 4.0), segments=4)
    # Stash on object for report hooks (custom props)
    try:
        f["fairing_edge_r"] = applied
    except Exception:
        pass
    oc.bake(f)
    return f


def fairing_cap_pod(side: str = "L"):
    """Cap↔pod bridge: short rounded nose + roof ramp (cap shoulder → pod roof).

    D7r4: constant-width stadium (no sail), TOP_CROWN=0 (no crease), then a
    longitudinal roof cut so the top slopes from the taller cap end down to the
    pod roof — one smooth band instead of a ledge + overhanging tip.
    """
    run = float(getattr(A, "FAIRING_RUN_CAP_POD", 16.0))
    w0 = float(A.FAIRING_W0)
    w1 = float(getattr(A, "FAIRING_W1_CAP_POD", w0))
    h = float(getattr(A, "FAIRING_H_CAP_POD", A.FAIRING_H))
    over = float(getattr(A, "FAIRING_BEVEL_OVERSIZE_CAP_POD", 0.0))
    # Match cap/pod tip plan R (D8 R3) so the hero roof has no shadow line
    r_nose = min(max(A.FAIRING_PLAN_R0, 3.0), run / 2.0, w0 / 2.0 - 0.5)
    f = fairing_body(
        f"fairing_cap_pod_{side}",
        run=run, w0=w0, w1=w1, h=h,
        plan_r0=r_nose,
        plan_r1=r_nose,
        top_crown=0.0,
        bevel_oversize=over,
    )
    # Roof ramp: full H toward cap (inboard), drop toward pod tip (outboard).
    # L fairing at −Y: cap = +Y local. R fairing at +Y: cap = −Y local (flip).
    drop = float(getattr(A, "FAIRING_RAMP_DROP", 3.5))
    if drop > 0.2:
        y0, y1 = -run / 2.0, run / 2.0
        if side == "R":
            # High at −Y (cap), low at +Y (pod)
            profile = [
                (y0 - 1.0, h + 2.0),
                (y0, h + 0.05),
                (y1, h - drop),
                (y1 + 1.0, h + 2.0),
                (y0 - 1.0, h + 2.0),
            ]
        else:
            # High at +Y (cap), low at −Y (pod)
            profile = [
                (y0 - 1.0, h + 2.0),
                (y0, h - drop),
                (y1, h + 0.05),
                (y1 + 1.0, h + 2.0),
                (y0 - 1.0, h + 2.0),
            ]
        oc.cut(f, oc.prism_x(f"fairing_cap_pod_{side}_ramp", profile, w0 + 8.0))
        oc.bake(f)
    # D8: 1.5 mm visual groove at mid-run (cap↔pod joint) — top trough only;
    # keeps lower body + mount path intact for fastening/fit.
    groove_w = float(getattr(A, "JOINT_GROOVE_W", 1.5))
    groove_d = float(getattr(A, "JOINT_GROOVE_D", 3.0))
    if groove_w > 0.4 and groove_d > 0.4:
        oc.cut(
            f,
            oc.box(
                f"fairing_cap_pod_{side}_groove",
                (w0 + 6.0, groove_w, groove_d + 0.4),
                at=(0.0, 0.0, h - groove_d),
                anchor="bottom",
            ),
        )
        oc.bake(f)
    return f


def fairing_pod_strap(side: str = "L"):
    """Pod↔strap bridge: brand 28 mm run; wide end = D8 strap-end flare."""
    w0 = float(getattr(A, "FAIRING_W0_POD_STRAP", A.FAIRING_W0))
    return fairing_body(
        f"fairing_pod_strap_{side}",
        run=A.FAIRING_RUN, w0=w0, w1=A.FAIRING_W1, h=A.FAIRING_H,
        plan_r0=A.FAIRING_PLAN_R0,
        plan_r1=min(A.FAIRING_PLAN_R1, A.STRAP_HALF * 0.9),
    )


def fairing_cw(side: str = "L"):
    """CW↔saddle continuous wedge — tangent to lower/longer D7 CW, no step."""
    run = float(getattr(A, "FAIRING_RUN_CW", A.FAIRING_RUN))
    w0 = float(getattr(A, "FAIRING_W0_CW", A.FAIRING_W0))
    w1 = float(getattr(A, "FAIRING_W1_CW", A.FAIRING_W1))
    h = float(getattr(A, "FAIRING_H_CW", A.FAIRING_H))
    return fairing_body(
        f"fairing_cw_{side}",
        run=run, w0=w0, w1=w1, h=h,
        plan_r0=max(A.FAIRING_PLAN_R0, 8.0),
        plan_r1=min(A.FAIRING_PLAN_R1, A.STRAP_HALF * 0.9),
    )
