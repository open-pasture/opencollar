# hardware/pods: D4-style action pods (A3) + adjustable clamp (Nov 14 2026)

Draft for Cody's review. Nothing here has been printed or fit-tested. Plate `overnight_petg_A3_d4` is on HOLD.

| path | what |
|---|---|
| `src_pr28_352e734/` | NOT in git (46 MB): printed PR #28 @ [352e734](https://github.com/open-pasture/opencollar/tree/352e734b2f5a40f99c3b160a3745250787409c1e/hardware/rook/d6/stl) `pod_{L,R}_{base,lid}.stl`; download into this folder to rebuild |
| `ref_d4/` | flat-aligned comparison STLs: D4_contoured_v3, PR #21, A2/pr28; `d4_pod_plan_flat.json` = D4 plan outline |
| `cad/d4pod.py` | builds action_pod_L/R base + lid: D4 plan + shoulder, flat underside, side-ear inserts, flat lid seat; writes `checks/d4pod_report.json` |
| `cad/stlclean.py` | post-export clean (float32 slivers → manifold STL). Run after d4pod.py |
| `cad/clamp.py` | clamp bar (holes x=±33.6), C-clip spacers, width shim |
| `cad/wallcheck.py`, `cad/overhang.py`, `cad/thinmap.py` | min-wall 2.4 check, overhang/bridge audit, thin-face map |
| `cad/oc.py` | shared CAD/check helpers |
| `stl/` | print STLs (+ `_asm_*` lids in the assembled frame for renders); hashes in `checks/stl_manifest.json` |
| `profiles/` | Orca 2.4.2 machine / process / `filament_petg_bed65.json` (+ support-audit process variants) |
| `plates/tools/` | run_plate.py (per-object overrides + POS layout + N7 fix + G-code audit), run_slice1.py, fix_bbl_3mf.py, layout.py, sup_where.py |
| `plates/layout_A3_d4.json` | object centres on the 256 bed |
| `plates/overnight_petg_A3_d4/` | HOLD_README, AMS_MAPPING, SHA256, slice JSON, layout PNG (the .gcode.3mf stays on the box) |
| `review/` | build_r4.py (Blender renders + .blend), compose_r4.py (annotations + G-code layer plot), check_blend_r4.py (10/10) |
| `checks/` | FIT_REPORT_A3.md and JSON reports; SHOCKBAY_KEEPOUT.md (+ shockbay_keepout.py/.json): shock-bay keep-out vs strap/clamp, **FAIL** |
| `review/r4_07_*` | shock/electrode bay keep-out renders (build_r4_07_shockbay.py + compose_r4_07.py, r4_07_shockbay_keepout.blend) |

Rebuild (from `hardware/pods/`):
```
cd cad && python3 d4pod.py && python3 clamp.py && python3 stlclean.py && python3 wallcheck.py && python3 overhang.py ../stl/*.stl && cd ..
# copy STLs into plates/src_A3/ (names = layout keys), then:
cd plates && PROFDIR=$PWD/../profiles FIL=filament_petg_bed65.json POS="$(cat layout_A3_d4.json)" \
  python3 tools/run_plate.py overnight_petg_A3_d4 overnight_petg_A3_d4 process_petg_020.json 1 '{"width_shim":{"brim_type":"outer_only","brim_width":"5"}}' src_A3/*.stl
cd ../review && python3 build_r4.py && python3 compose_r4.py && python3 check_blend_r4.py
```
Paths are repo-relative. The slicer is found via `ORCA` / `ORCA_LIBS` env vars (default: the box install). Python needs manifold3d, trimesh, shapely and the bpy module.
Ballast and cap pods are unchanged from the r3 drop (not part of A3).
