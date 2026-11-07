# Experiment: option B — integral R220 pod underside

**Not production. Does not overwrite PR #28 STLs.**

Builds a *copy* of `../../stl/pod_L_base.stl` with an R≈220 concave cut into the skirt bed and a PLACEHOLDER bay opening through the curve.

```bash
cd hardware/rook/d6/experiments/opt_b_integral_underside
blender --background --factory-startup --python build_opt_b.py
python3 geometry_check_opt_b.py   # geometry only — NOT a fit/print proof
```

Chosen print orientation: **curve UP / cavity DOWN** (bed rule). See `opt_b_report.json` and the A/B/C table in `../../review/d8_neck_saddle_options.md`.
