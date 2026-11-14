# ⛔ HOLD: overnight_petg_A3_d4 (NOT SENT). Supersedes overnight_petg_A2_trim.
- File: overnight_petg_A3_d4.gcode.3mf
- sha256: **5dec437a8c36697ca29997d16ea8a7fedda2c6c90499c2fd2f2d974d48e0ac0c**
- Contents (28 objects): action_pod_L_base, action_pod_R_base, action_pod_L_lid, action_pod_R_lid (new D4-style shells, lids printed top-down), clamp_bar ×8 (holes re-fitted to x = ±33.6), spacer_0p5 ×4, spacer_1p0 ×4, spacer_2p0 ×4, width_shim ×4 (5 mm outer brim).
- OrcaSlicer 2.4.2 CLI, N7 patch (fix_bbl rc 0, printer_model_id N7), P2S, 0.4 nozzle, **Textured PEI**, Generic PETG @BBL P2S (GFG99) 255 °C / **bed 65 °C** (M140/M190 S65), colour #7F7E83, 0.20 mm layers, 3 walls, 15% infill, **supports disabled** (support_used=false).
- 1 plate, **4h 43m 22s**, **150.00 g**, **116 layers**, max Z 23.2. Extrusion window X 5.61–248.79 / Y 5.21–232.94, **min margin 5.21 mm** (≥4 mm OK).
- G-code audit: **0 support extrusions** (no Support / Support-interface features). **Brim moves 1570, all within the 4 width-shim footprints** (spatial check; no brim on any other object).
- File warnings: **none** (the bed_temperature_too_high_than_filament warning from A2 is gone at bed 65 °C).
- Layout: layout_A3_d4.json. G-code plot: overnight_petg_A3_d4_plate_1_layout.png. Renders: ../../review/r4_04_plate_A3_top.png, r4_05_plate_A3_34.png, r4_06_plate_A3_gcode_layers.png.
- AMS: filament 1 → **A2 PETG**, nothing on A1, AMS backup OFF (see AMS_MAPPING.md).

## Gate
Cody reviews (Blender: ../../review/overnight_review_r4.blend), bed clear is confirmed, there is a typed go naming **overnight_petg_A3_d4** + sha **5dec437a8c36697ca29997d16ea8a7fedda2c6c90499c2fd2f2d974d48e0ac0c**, and A2 is mapped at send.

## Known risks
- Support-free audit (Orca supports ON, threshold 40°, audit only): lids, spacers, shims clean. Base flags only (a) the 4 insert-pocket ceilings (Ø4 bridges at z 6.5) and (b) the inherited mount-recess ceiling at z 19.3 (36 mm wide, ≈3.4 mm deep, anchored on 3 sides; a 1 mm inner fin bottoms at z 16.3). Bars: the two Ø6 counterbore ceilings (z 1.5). All are short bridges except the recess ceiling, which is inherited from the locked mount face (it was tree-supported on print #8).
- At threshold 45° Orca also flags the inherited 45° rim-ledge chamfers inside the cavity (from pr28) and the lids' 45° edge chamfer (top-down print). They are exactly 45°.
- spacer_0p5 prints 0.4 mm at 0.20 layers; shim 2.2; bar 6.4. No brim on spacers or bars. Generic PETG profile.
- No fit test yet: inserts in side ears, new lid seat (tongue/groove dropped) and the clamp are untested in PETG.
