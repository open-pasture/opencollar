# Node V1 print files

ASA (`print/p2s_asa`) is the final-build material. The tracked slices under `sliced/p2s_pla/` are PLA fit checks only.

How to start a print: see `../PRINTING.md`. Throughput notes: `../THROUGHPUT.md`. Print log: `../PRINT-HISTORY.md`. Hardware vs CAD: `../HARDWARE-FIT.md`.

| Part | STLs | Sliced P2S/PLA 3mf | Profile |
| --- | --- | --- | --- |
| Cap | `exports/node_v1_cap/` — `node_cap_base` **76×160×29**, `node_cap_lid` **76×160×7**, `node_cap_clamp_bar` 10×70×4 | `sliced/p2s_pla/F2_cap.gcode.3mf` — **STALE** (old 62×142 / dual-P122; prints #1/#2). Re-slice the current STLs (self-supporting channel + conical seats; see below). | Fit: `p2s_pla/` (supports off — spine V + corrugated channel roof are 45°). Final: `p2s_asa/`. |
| Counterweight | `exports/node_v1_cw/` — `node_cw_tub`, `node_cw_lid`, `node_cw_clamp_bar` | `sliced/p2s_pla/F3_counterweight.gcode.3mf` (tub + lid + 2 clamp bars) | Fit: `p2s_pla/`. Final: `p2s_asa/`. |
| Pod | `exports/node_v1_pod/` — `node_pod_base`, `node_pod_lid`, `node_pod_clamp_bar` | `sliced/p2s_pla/F4_pod_left.gcode.3mf` (base + lid + 2 clamp bars; left side) | Fit: `p2s_pla/`. Final: `p2s_asa/`. |

## Cap pocket and layout

- Lid pocket: one Voltaic P124, **66.6 × 113.6 × 1.2 mm** (XY from `dims.P124_PANEL` 113×66 + 0.3 mm/side).
- **Pocket depth stays 1.2 mm** (VHB recess). `dims.P124_PANEL` thickness is **3.1 mm** (drawing 2.8±0.3), but a full-depth pocket would break into the lid insert holes under the panel footprint. The panel sits proud on the gasket.
- **`PANEL_Y = +11 mm` is deliberate:** a centred 113.6 mm pocket on a 160 mm lid leaves only ~23 mm at each end — too short for the 25 mm GPS patch — so the pocket shifts +Y and the patch takes the −Y end.
- Pod battery bay not changed yet (owner decision pending).

## Offline Orca slices (pre-chamfer 76×160×29)

Cody’s offline Orca results for the **pre-chamfer** P124 cap (flat channel ceiling / cylindrical counterbores — the geometry before the self-support follow-up). **Re-slice the current STLs**; these numbers are historical only.

| Profile | Time | Filament | Notes |
| --- | --- | --- | --- |
| Stock `p2s_pla`, supports on | 4h41m | 140 g | |
| Stock `p2s_pla`, supports off | 4h06m | 134 g | |
| Fast-fit: 0.28 mm layer, 21 mm³/s flow, 10% gyroid, no supports | 3h15m | 133 g | |
| Old 62×142 cap (for comparison) | 3h32m | 93 g | Prints #1/#2 |

Also in `sliced/p2s_pla/`: `F1_fit_test.gcode.3mf` (`fit_test`), `F5_seal_box.gcode.3mf` (`seal_box_box` + `seal_box_lid`). Re-slice with `./slice_p2s_pla.sh` into the same folder. LAN start-print template (placeholder only): `tools/p2s_lan_start.tpl.py`.
