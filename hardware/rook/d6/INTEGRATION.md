# D6/D7r3 integration

Branch `cursor/d6-integrate-9a36`. Acceptance:
`python3 assembly_check.py out` → **143/143 PASS**.

## D7r3 deltas (vs D7r2 head `3db3397`)
- **Orange brand accents** (#FF6A2B): clamp endcaps at bar **ends** (x=±35 for
  bars 1–6); orange strap-block saddle under each pod; pod-top dots + cue tabs;
  larger latch / Ø7 screws / Ø5 service dots. Body `#C9CBCC`; bars + fairings gray.
- **End fairings:** short rounded nose (run 16, W1=W0, TOP_CROWN=0) flush with
  pod tip outline — no sail flap past the pods, no crease lines.
- **Lids:** closed convex crowns (pod dome 1.8 mm; no dish); R6 tip perimeter;
  tip roof drop ~6 mm to fairing.
- **Cap rear lip:** D4-style raised rim (~2×3 mm) across −Y label end.
- Intact: panel/Wio/cavity size/771.8 g steel/mount interface (y=±126, z=−21.9,
  ±29.142°, 36×4×14, 4×M3)

## Reports
Per-part: `stl/*_report.json`. Assembly: `out/assembly_check.json`.
Print: `PRINT.md` (256 mm bed, 8 mm ASA brims). Cap_base Y+brim = 202.9 ≤ 256.

## Review
- Renders: `renders/d6_assembly_{iso,front,side,top,joint}.png`
- Blend: `review/d6_assembly.blend`
- Rebuild: `blender --background --python build_assembly_blend.py -- out/world out/d4_ghost out/assembly_review`

## Cody checklist
1. Orange accents readable at thumbnail (endcaps at ±35, pod saddles, lid dots)
2. Cap–pod fairing = short rounded nose flush with pod tip (no sail/crease)
3. Pod + cap tops closed convex; cap rear lip present
4. Strap path; buckle/keeper intentionally omitted until posed
5. CW lower than pod; 771.8 g steel intact
