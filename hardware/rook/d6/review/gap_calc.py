#!/usr/bin/env python3
"""Reproduce Cody's flat-underside mid-gap under an elliptical neck.

Neck model: ellipse 25 × 42 cm at 107 cm circumference, scaled to 75 and 130 cm.
Pod centre 126 mm along strap from crest; pod length 97 mm; local station ~29–30° off crest.

Run: python3 hardware/rook/d6/review/gap_calc.py
"""
from __future__ import annotations

import math


def ellipse_perimeter_approx(a: float, b: float, n: int = 4000) -> float:
    """Ramanujan-ish via polyline — good enough for scaling."""
    acc = 0.0
    x0, y0 = a, 0.0
    for i in range(1, n + 1):
        t = 2.0 * math.pi * i / n
        x1, y1 = a * math.cos(t), b * math.sin(t)
        acc += math.hypot(x1 - x0, y1 - y0)
        x0, y0 = x1, y1
    return acc


def scale_ellipse(a0: float, b0: float, target_c: float):
    c0 = ellipse_perimeter_approx(a0, b0)
    s = target_c / c0
    return a0 * s, b0 * s, c0, s


def local_radius(a: float, b: float, t: float) -> float:
    """Radius of curvature of ellipse x=a cos t, y=b sin t."""
    # ρ = (a²sin²t + b²cos²t)^(3/2) / (a b)
    s, c = math.sin(t), math.cos(t)
    num = (a * a * s * s + b * b * c * c) ** 1.5
    return num / (a * b)


def chord_mid_gap(R: float, half_chord: float) -> float:
    """Gap under a flat chord of length 2*half_chord against a circle of radius R.

    Mid-gap = R - sqrt(R² - L²/4) for L = 2*half_chord (flat outside circle).
    """
    h = half_chord
    if h >= R:
        return float("nan")
    sagitta = R - math.sqrt(R * R - h * h)
    return sagitta


def main():
    # Base ellipse: 25 × 42 cm → a=210 mm (semi-major along?), b=125 mm
    # 25 cm × 42 cm are full diameters → semi-axes 125 mm × 210 mm
    a0, b0 = 210.0, 125.0  # mm semi-axes (42 cm, 25 cm)
    targets = {
        750.0: "75 cm",
        1070.0: "107 cm",
        1300.0: "130 cm",
    }
    pod_centre_arc = 126.0  # mm from crest along strap
    pod_len = 97.0
    half = 0.5 * pod_len

    print("Base ellipse diameters 42×25 cm → semi-axes a=210 b=125 mm")
    print(f"Pod length={pod_len} mm, centre arc from crest={pod_centre_arc} mm\n")

    # Design station: Cody's ~29–30° off crest (not arc/mean-R, which overshoots).
    t_design = math.radians(29.5)
    print(f"Design station t={math.degrees(t_design):.1f}° off crest\n")
    for C, label in targets.items():
        a, b, c0, s = scale_ellipse(a0, b0, C)
        R = local_radius(a, b, t_design)
        gap = chord_mid_gap(R, half)
        print(
            f"{label}: scale={s:.4f} a={a:.1f} b={b:.1f} "
            f"R_local(@29.5°)={R:.1f} mm  flat mid-gap={gap:.2f} mm"
        )

    print("\nCody quoted R ≈ 208 / 218 / 221 mm (authoritative for sizing):")
    for Rq, lab in ((208.0, "75"), (218.0, "107"), (221.0, "130")):
        print(f"  quoted R={Rq} → gap={chord_mid_gap(Rq, half):.2f} mm ({lab} cm)")

    print("\nRigid saddle R=220 vs quoted necks (residual mid-gap):")
    for R_neck, lab in ((208.0, "75"), (218.0, "107"), (221.0, "130")):
        g_n = chord_mid_gap(R_neck, half)
        g_s = chord_mid_gap(220.0, half)
        print(f"  {lab} cm: neck_gap={g_n:.2f} saddle_fill={g_s:.2f} residual≈{abs(g_n-g_s):.2f} mm")

    print(
        "\nNote: ellipse 25×42 cm is a sizing model — check against real neck "
        "measurements before locking R. Do not invent measurements."
    )


if __name__ == "__main__":
    main()
