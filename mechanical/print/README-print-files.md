# Node V1 print files

ASA (`print/p2s_asa`) is the final-build material. The tracked slices under `sliced/p2s_pla/` are PLA fit checks only.

How to start a print: see `../PRINTING.md`. Throughput notes: `../THROUGHPUT.md`. Print log: `../PRINT-HISTORY.md`. Hardware vs CAD: `../HARDWARE-FIT.md`.

| Part | STLs | Sliced P2S/PLA 3mf | Profile |
| --- | --- | --- | --- |
| Cap | `exports/node_v1_cap/` — base **76×160×41.4**, lid **76×160×7**, clamp bar 10×70×4 | `sliced/p2s_pla/F2_cap.gcode.3mf` — **STALE** (old 62×142 / dual-P122 cap from prints #1/#2; not the v3 76×160 gabled STLs). Re-slice. | Fit: `p2s_pla/` (supports off). Final: `p2s_asa/`. |
| Pod (×2, mirror one) | `exports/node_v1_pod/` — base **92×68×24.5**, lid **92×68×6**, clamp bar | `sliced/p2s_pla/F4_pod_left.gcode.3mf` — **STALE** until re-sliced from the restored dual-cell STLs. | Fit: `p2s_pla/`. Final: `p2s_asa/`. |
| Counterweight | `exports/node_v1_cw/` | `sliced/p2s_pla/F3_counterweight.gcode.3mf` | Fit: `p2s_pla/`. Final: `p2s_asa/`. |

**PROPOSED ALTERNATIVE, NOT APPROVED** (Adafruit 353 battery pod 100×90×26 + cue pod 92×68×26; was `node_v1_pod_battery` / `node_v1_pod_cue`): `exports/alt_pods_unapproved/`. Dual-cell `exports/node_v1_pod/` remains the plan of record.

## Layout

- **Cap:** one P124 pocket 66.6 × 113.6 × 1.2 (VHB); `PANEL_Y = +11` deliberate; channel gable ≥45°.
- **Pod (plan of record):** 1 × Adafruit 1781 + 1 × Qwiic Buzzer per pod (2×1781 pending Cody’s purchase approval). Identical left/right mirrors. Sound port +Y; crest cable +X. Mono vs stereo buzzer is Cody’s open call.
- Clamp Y ±29.5 / 70 mm bars / strap channel unchanged across modules. Pod outline fits the P2S 256×256 plate.

## Offline Orca (earlier cap geometry — re-slice)

Pre-gable 76×160×29: stock supports on 4h41m/140 g; supports off 4h06m/134 g; fast-fit 3h15m/133 g; old 62×142 cap 3h32m/93 g.

Also in `sliced/p2s_pla/`: `F1_fit_test.gcode.3mf`, `F5_seal_box.gcode.3mf`. LAN template: `tools/p2s_lan_start.tpl.py`.
