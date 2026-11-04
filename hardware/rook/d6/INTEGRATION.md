# D6 integration

Branch `cursor/d6-integrate-9a36` merges cap `c8ae9ce`, pod `99300d2`, cw `05ef563`
onto D5 `6b1f882`. Shared constants / world poses: `assembly.py`. Acceptance:
`python3 assembly_check.py out` (109/109 PASS at integrate).

## Reports
Per-part: `stl/cap_report.json`, `stl/pod_report.json`, `stl/cw_report.json`.
Assembly: `out/assembly_check.json`, world STLs `out/world/`, `out/d6_assembly_world.glb`.

## Review
- Renders: `renders/d6_assembly_{iso,front,side,top}.png` (D4 ghost overlay)
- Blend: `review/d6_assembly.blend` (collections `D6_assembly`, `D4_contoured_v3_ghost`)
- Rebuild: `blender --background --python build_assembly_blend.py -- out/world out/d4_ghost out/assembly_review`

## Cody Blender checklist
1. Cap–pod joint (tilt L+ / R−, pad/recess, gap)
2. Pod bulk vs D4 ghost (92 vs 67 wide — cavity-forced)
3. Fairing placement / continuous width taper 88→66 along run (D7 loft, R≥4)
3b. Cap rounded nose flowing into fairing (D7)
4. Strap path through saddle / clamps (along Y)
5. Counterweight size (D5 mass envelope 88×74×30 vs D4 ~59×85×24)
