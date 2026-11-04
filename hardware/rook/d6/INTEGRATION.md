# D6/D7r6 integration

Branch `cursor/d6-integrate-9a36`. Acceptance:
`python3 assembly_check.py out` → **144/144 PASS**.

## D7r6 deltas (vs D7r5 head `22a8f73`)
- **Wire hygiene:** D4 ghost WIRE boxes deleted from review blend; keeper/tongue/accents
  ≥2 mm solids; no leftover curves; `geometry_hygiene.json` check (no dim&lt;1 mm / non-mesh).
- **Closed pod lids:** convex dome across full outline; screw heads on flat rim; wall rim
  not above lid; skirt-aware `POD_MATING_Z` / `CAP_MATING_Z` so lids sit on mating.
- **Skirt flare:** width ≤ pod/cap outline (no side overhang); tangent down into strap.
- **Markings:** only recessed `001` (12×0.8 mm) + orange dot; no X/arrow; no cap “oo”
  (light-pipes stop short of outer crown).
- **Review-only roof bands:** `review_roof_band_L/R` boolean-union skins; printable
  fairing STLs unchanged (hidden in review).

## Carry-forward
Charcoal default; slim strap + flat buckle/keeper; clamps in pockets; 771.8 g /
z=0 / watertight / rotation-only / cavities unchanged.

## Review
- Renders: `renders/d6_assembly_{iso,front,side,top,joint}.png` (+ `*_light`)
- Blend: `review/d6_assembly.blend`
- Rebuild: `blender --background --python build_assembly_blend.py -- out/world out/d4_ghost out/assembly_review`
