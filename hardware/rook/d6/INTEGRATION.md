# D6/D7 integration

Branch `cursor/d6-integrate-9a36` merges D5 `6b1f882` + D6 agents, then D7
pod `ea74432` / cap `abacc41` / cw `9e348d7` (based on PR #24 head `96f3b30`).
Shared constants / world poses: `assembly.py`. Acceptance:
`python3 assembly_check.py out` → **136/136 PASS**.

## D7 deltas
- Pod: swell 92 at cells, tip ~70, lower tip roof (contoured plan)
- Cap: rounded nose; continuous `fairing.py` loft (`FAIRING_*` follow `POD_L`)
- CW: 89.4×115.8×18, 2×2 steel pack still **771.8 g**; calm gray ASA palette
- Fairings re-lofted to slim tip + CW outer; bevel oversize keeps seam Δw ≤ 0.5 mm
- Checks: CW height/volume < pod; fairing seam step ≤ 0.5 mm

## Reports
Per-part: `stl/cap_report.json`, `stl/pod_report.json`, `stl/cw_report.json`.
Assembly: `out/assembly_check.json`, world STLs `out/world/`, `out/d6_assembly_world.glb`.
Print plan: `PRINT.md` (256 mm bed, 8 mm ASA brims).

## Review
- Renders: `renders/d6_assembly_{iso,front,side,top,joint}.png` + per-part `cap_*` / `pod_*` / `cw_*`
- Blend: `review/d6_assembly.blend` (compressed; D7 calm-gray palette)
- Rebuild: `blender --background --python build_assembly_blend.py -- out/world out/d4_ghost out/assembly_review`

## Cody Blender checklist
1. Cap–pod joint (tilt L+ / R−, pad/recess, gap)
2. Pod bulk vs D4 ghost (92 swell / ~70 tip — cavity-forced)
3. Fairing continuous wedge, no seam step > 0.5 mm (tip / CW / height)
3b. Cap rounded nose flowing into fairing
4. Strap path through saddle / clamps (along Y)
5. Counterweight lower/longer than D5 tower; 771.8 g steel intact
