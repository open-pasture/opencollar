# Rook (Node V1) print files

ASA (`p2s_asa`) is the final-build material. The tracked slices under `sliced/p2s_pla/` are PLA fit checks only.

How to start a print: see `PRINTING.md`. Throughput notes: `THROUGHPUT.md`. Print log: `PRINT-HISTORY.md`. Hardware vs CAD: `../bom/HARDWARE-FIT.md`.

| Part | STLs | Sliced P2S/PLA 3mf | Profile |
| --- | --- | --- | --- |
| Cap (gable v3) | `../stl/node_v1_cap/` — base **76×160×41.4**, lid **76×160×7**, clamp bar 10×70×4 | `sliced/p2s_pla/F2_cap.gcode.3mf` — **STALE** (old 62×142 / dual-P122 cap from prints #1/#2; not the v3 76×160 gabled STLs). Re-slice. | Fit: `p2s_pla/` (supports off). Final: `p2s_asa/`. |
| Cap (slim + saddle) | `../stl/node_v1_cap_saddle/` — base **76×160×19**, saddle **76×80×5.9**, lid 7, clamp bar 10×70×4 | Not sliced yet (do not overwrite gable STLs). Build: `OC_CAP_STYLE=saddle ./build.sh node_v1 -- cap saddle`. | Fit: `p2s_pla/` (supports off; saddle roof-down). Final: `p2s_asa/` + **brim** on base and saddle. |
| Pod (×2, mirror one) | `../stl/node_v1_pod/` — base **92×68×24.5**, lid **92×68×6**, clamp bar | `sliced/p2s_pla/F4_pod_left.gcode.3mf` — **STALE** until re-sliced from the restored dual-cell STLs. | Fit: `p2s_pla/`. Final: `p2s_asa/`. |
| Counterweight | `../stl/node_v1_cw/` | `sliced/p2s_pla/F3_counterweight.gcode.3mf` | Fit: `p2s_pla/`. Final: `p2s_asa/`. |

**PROPOSED ALTERNATIVE, NOT APPROVED** (Adafruit 353 battery pod 100×90×26 + cue pod 92×68×26; was `node_v1_pod_battery` / `node_v1_pod_cue`): `../stl/alt_pods_unapproved/`. Dual-cell `../stl/node_v1_pod/` remains the plan of record.

Shared fit coupons (`F1_fit_test`, `F5_seal_box`) use STLs from `hardware/common/stl/`; slices stay here with the Rook print job until Starling has its own `print/` tree.

## Layout

- **Cap gable v3:** one P124 pocket 66.6 × 113.6 × 1.2 (VHB); `PANEL_Y = +11` deliberate; channel gable ≥45°.
- **Cap slim + saddle:** flat floor (no gable / spine V); strap channel lives in the printed saddle (roof-down, no supports). Stack ~32.5 mm strap→lid. Screws: lid M3×20, clamp M3×16. See `../cad/SADDLE.md`.
- **Pod (plan of record):** 1 × Adafruit 1781 + 1 × Qwiic Buzzer per pod (2×1781 pending Cody’s purchase approval). Identical left/right mirrors. Sound port +Y; crest cable +X. Mono vs stereo buzzer is Cody’s open call.
- Clamp bars 70 mm / strap channel unchanged across modules. Pod outline fits the P2S 256×256 plate.

## Offline Orca (earlier cap geometry — re-slice)

Pre-gable 76×160×29: stock supports on 4h41m/140 g; supports off 4h06m/134 g; fast-fit 3h15m/133 g; old 62×142 cap 3h32m/93 g. Gable v3 print #3 ~156 g / 3h51m. Slim+saddle not yet sliced.

Also in `sliced/p2s_pla/`: `F1_fit_test.gcode.3mf`, `F5_seal_box.gcode.3mf`. LAN template: `tools/p2s_lan_start.tpl.py`.
