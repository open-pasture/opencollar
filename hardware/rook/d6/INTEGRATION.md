# D6/D7r5 integration

Branch `cursor/d6-integrate-9a36`. Acceptance:
`python3 assembly_check.py out` → **143/143 PASS**.

## D7r5 deltas (vs D7r4 head `d1ae7ce`)
- **Clamp bars:** recessed into skirt/saddle pockets; ≤1 mm proud of underside;
  hidden from iso/hero/front; body material; channel 46.45×3.4 + screw access kept.
- **Buckle + keeper:** open rectangular frame (~24×30×3) flat on strap surface with
  tongue; thin keeper loop around band; both follow strap curvature (≤3 mm proud).
- **Stack roof:** continuous cap → fairing → pod line (ramp drop 5.5); no rear-lip
  plate; matching nose/pod plan R; ghost wire loops hidden in committed renders.
- **Pod shoulder:** deep flared skirt (H≈14) with R12 plan + soft tangent chamfer;
  rounded ends (no pointed tabs).
- **Lid detail:** clean recessed `001` (10 mm tall, 0.6 mm deep); no arrow engraving;
  solar panel = clean flat dark rectangle with crisp edge only.

## D7r4 carry-forward
- Charcoal default palette (~`#3A3C3E`); `--palette light` secondary; orange `#FF6A2B`.
- Slim strap band (≈44.45×3.0) on YZ ring; orange only dots/tab/screws/latch.
- Cavities / panel / Wio / 771.8 g / z=0 / watertight / rotation-only unchanged.

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
1. Clamps invisible under skirts (or flush ≤1 mm); no perpendicular slats in hero
2. Buckle = flat open frame on strap; keeper = thin loop; nothing >3 mm proud
3. Cap/fairing/pod roof = one continuous slope; no thin shelf at far end
4. Pod skirt = long R12 flare with rounded ends
5. Pod lid = clean `001` only; solar panel = clean dark rectangle
