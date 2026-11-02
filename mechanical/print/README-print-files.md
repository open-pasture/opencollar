# Node V1 print files

ASA (`print/p2s_asa`) is the final-build material. The tracked slices under `sliced/p2s_pla/` are PLA fit checks only.

How to start a print: see `../PRINTING.md`. Throughput notes: `../THROUGHPUT.md`. Print log: `../PRINT-HISTORY.md`.

| Part | STLs | Sliced P2S/PLA 3mf | Profile |
| --- | --- | --- | --- |
| Cap | `exports/node_v1_cap/` — `node_cap_base`, `node_cap_lid`, `node_cap_clamp_bar` | `sliced/p2s_pla/F2_cap.gcode.3mf` (base + lid + 2 clamp bars) | Fit: `p2s_pla/`. Final: `p2s_asa/`. |
| Counterweight | `exports/node_v1_cw/` — `node_cw_tub`, `node_cw_lid`, `node_cw_clamp_bar` | `sliced/p2s_pla/F3_counterweight.gcode.3mf` (tub + lid + 2 clamp bars) | Fit: `p2s_pla/`. Final: `p2s_asa/`. |
| Pod | `exports/node_v1_pod/` — `node_pod_base`, `node_pod_lid`, `node_pod_clamp_bar` | `sliced/p2s_pla/F4_pod_left.gcode.3mf` (base + lid + 2 clamp bars; left side) | Fit: `p2s_pla/`. Final: `p2s_asa/`. |

Also in `sliced/p2s_pla/`: `F1_fit_test.gcode.3mf` (`fit_test`), `F5_seal_box.gcode.3mf` (`seal_box_box` + `seal_box_lid`). Re-slice with `./slice_p2s_pla.sh` into the same folder. LAN start-print template (placeholder only): `tools/p2s_lan_start.tpl.py`.
