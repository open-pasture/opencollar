# D6/D7r4 integration

Branch `cursor/d6-integrate-9a36`. Acceptance:
`python3 assembly_check.py out` → **143/143 PASS**.

## D7r4 deltas (vs D7r3 head `7e3530e`)
- **Palette:** review blend DEFAULT = charcoal (~`#3A3C3E`, roughness 0.6,
  matched to D4_contoured_v3 when blend present); `--palette light` secondary.
  Orange unchanged `#FF6A2B`.
- **Strap:** slim flat band (≈44.45×3.0) on YZ ring through saddle channel and
  under CW clamp; D4-style buckle + keeper (dark gray).
- **Orange trim-back:** remove pod saddle teeth + clamp endcaps. Orange only:
  one small dot per pod lid, one collar tab, tiny screw heads + latch.
- **Flared skirts:** under each pod and cap ±Y ends; 7 mm flare wrapping strap;
  channel 46.45×3.4 kept; clamp bars accessible.
- **Silhouette:** lower cap crown (1.4) / nose tip (5.5) / wrap step (3.5);
  fairing roof ramp (drop 3.5) toward pod; cavities unchanged.
- **Lids (review):** four corner screws + one pod dot; public ID `001`
  recessed on pod lid outer (~9 mm, 0.5 mm).

## Reports
Per-part: `stl/*_report.json`. Assembly: `out/assembly_check.json`.
Print: `PRINT.md` (256 mm bed, 8 mm ASA brims).

## Review
- Renders: `renders/d6_assembly_{iso,front,side,top,joint}.png` (charcoal)
  + optional `*_light.png` via `--palette light`
- Blend: `review/d6_assembly.blend`
- Rebuild:
  `blender --background --python build_assembly_blend.py -- out/world out/d4_ghost out/assembly_review`
  `blender ... --palette light` for the secondary pack

## Cody checklist
1. Charcoal body reads like D4; orange only dots/tab/screws/latch
2. Strap = thin flat band through saddle + under CW; buckle/keeper present
3. Skirts blend pod/cap into strap; no orange fins
4. Cap→pod = smooth ramp (no tall ledge / sail)
5. Pod lid shows `001` + four corner screws + one orange dot
