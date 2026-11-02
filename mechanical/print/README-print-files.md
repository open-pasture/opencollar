# Node V1 print files

ASA (`print/p2s_asa`) is the final-build material. The tracked slices under `sliced/p2s_pla/` are PLA fit checks only.

How to start a print: see `../PRINTING.md`. Throughput notes: `../THROUGHPUT.md`. Print log: `../PRINT-HISTORY.md`. Hardware vs CAD: `../HARDWARE-FIT.md`.

| Part | STLs | Sliced P2S/PLA 3mf | Profile |
| --- | --- | --- | --- |
| Cap | `exports/node_v1_cap/` — base **76×160×41.4**, lid **76×160×7**, clamp bar 10×70×4 | `sliced/p2s_pla/F2_cap.gcode.3mf` — **STALE** (old 62×142 / dual-P122 cap from prints #1/#2; not the v3 76×160 gabled STLs). Re-slice. | Fit: `p2s_pla/` (supports off). Final: `p2s_asa/`. |
| Battery pod (left) | `exports/node_v1_pod_battery/` — base **100×90×26**, lid **100×90×6**, clamp bar | `sliced/p2s_pla/F4_pod_left.gcode.3mf` — **STALE** (old pod outline / dual-18650 bay; not battery+cue pods). Re-slice. | Fit: `p2s_pla/`. Final: `p2s_asa/`. |
| Cue pod (right) | `exports/node_v1_pod_cue/` — base **92×68×26**, lid **92×68×6**, clamp bar | same F4 — **STALE** (old pod outline). Re-slice. | Fit: `p2s_pla/`. Final: `p2s_asa/`. |
| Counterweight | `exports/node_v1_cw/` | `sliced/p2s_pla/F3_counterweight.gcode.3mf` | Fit: `p2s_pla/`. Final: `p2s_asa/`. |

## Layout

- **Cap:** one P124 pocket 66.6 × 113.6 × 1.2 (VHB); `PANEL_Y = +11` deliberate; channel gable ≥45°.
- **Battery pod:** owned **Adafruit 353** (69×54×18) in a 71×56×1.2 locator; foam/VHB; vent on −Y; power cable to the cap. **Do not buy 1781 cells.**
- **Cue pod:** one owned **Qwiic Buzzer** (mono cues for unit #1). No battery bay. A second buzzer (0x5B) is optional later for left/right cues.
- Clamp Y ±29.5 / 70 mm bars / strap channel unchanged across modules. Both pod outlines fit the P2S 256×256 plate.

## Offline Orca (earlier cap geometry — re-slice)

Pre-gable 76×160×29: stock supports on 4h41m/140 g; supports off 4h06m/134 g; fast-fit 3h15m/133 g; old 62×142 cap 3h32m/93 g.

Also in `sliced/p2s_pla/`: `F1_fit_test.gcode.3mf`, `F5_seal_box.gcode.3mf`. LAN template: `tools/p2s_lan_start.tpl.py`.
