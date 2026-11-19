# OpenCollar print history (maintained by op-maker)

Printer: Bambu Lab P2S (home, Cody's LAN 192.168.1.248, cloud mode)

| # | Date | Part | Material | Status | Notes |
|---|------|------|----------|--------|-------|
| 1 | 2026-11-01 | Node V1 cap (node_cap_*) | PLA | Done (obsolete CAD) | First print on the new P2S. **Old geometry:** 62 × 142 mm cap with dual Voltaic P122 pockets (panels never bought). File/settings not fully captured. |
| 2 | 2026-11-02 | Node V1 cap (`F2_cap.gcode.3mf`) | PLA | Done — looks great (obsolete CAD) | Same old 62 × 142 / P122 CAD. Started via Bambu Connect on Openpasture-1. See PRINTING.md. |
| 3 | 2026-11-02 | Node V1 cap v3 (76×160, P124 pocket, gabled roof, no supports) | PLA (Bambu PLA, AMS A1) | Started | From commit `951e057`. P2S Openpasture-1. Fast-fit profile (0.28 mm, 21 mm³/s, 10% gyroid, no supports). 148 layers; estimate 3h51m, 156.27 g. Started ~3:53 PM CT via Bambu Connect on Cody's Mac. |
| 4 | 2026-11-02 | Bases-only plate: slim `node_cap_base_saddle` + `node_pod_base` (L) + pod R mirrored | PLA | Stopped (~16 min) | Pre-aids STLs (no cradle/labels). 0.16 mm layer, 153 layers; est 5h55m, 173.3 g. Started 8:19 PM CT via Bambu Connect on Openpasture-1; Cody stopped ~8:35 PM CT to restart with assembly aids (REV AID1). **Lid screw decision: M3×16** (clamp M3×14). |
| 5 | 2026-11-02 | Aids plate v7: slim cap base + pod L + pod R + test coupon + XYZ scale bar (main `7a3660f`, PR #18 `f906926`) | PLA | Started 10:33 PM CT, result pending | `aids_plate_0.16_PLA_p2s.gcode.3mf` (cap_set_v7), 0.16 mm, 15% gyroid, 4 walls, tree supports on pods only, 153 layers, estimate 6h55m / 192.39 g. Sent via Bambu Connect on Openpasture-1, PLA in AMS A1. 15% gyroid is a fit test only, not a strength test. |
| 11 | 2026-11-16 | bars_petg_A3c_nominal | PETG AMS A2 | Done FINISH 32/32 | first LAN print; sha fee11ea0…; dry-fit not logged |
| 12 | 2026-11-16 | infinity_cubes_x2_pla_A4 | PLA AMS A4 | Done FINISH | sha ea3c0868… |
| 13 | 2026-11-17 | kid_turtles4_aroundcubes_pla_A4 | PLA AMS A4 | FAILED L0 (FOD) | sha dbe25b2c… |
| 14 | 2026-11-17 | kid_turtles4_aroundcubes_noFOD_pla_A4 | PLA AMS A4 | FAILED (cause unknown) | sha 40350e4b… |

## Print #11 — bars_petg_A3c_nominal — Done (Mon Nov 16, 2026) — first LAN-started print
- sha256 `fee11ea0fc4f33ab5fe71f2d020a04d5f8b60c9f4fc6ee1ddab6c8e93f8ac96c`, plate dir `hardware/pods/plates/bars_petg_A3c_nominal/`
- 4 clamp bars, 8 spacers (1.5 mm), 8 width shims. PETG AMS A2, 32 layers, slice estimate 56m 37s / 22.71 g, no supports.
- First direct LAN start from the garage host (lan_p2s.py over MQTT), not Bambu Connect, under Cody's typed go. The first attempt failed with `mqtt message verify failed` (err 84033543) until Developer Mode was turned on. Started ~4:40 PM CT.
- Result: FINISH, print_error 0, 32/32 at the 5:58 PM CT check. Quality / dry-fit not logged.

## Prints #12–#14 — overnight kid plates (Nov 16–17, 2026) — LAN from garage, PLA AMS A4 (non-collar fun prints)
- #12 infinity_cubes_x2_pla_A4 (sha ea3c0868…4c224cc9; Sturdy Infinity Cube by Jan Pieper, CC0, https://makerworld.com/en/models/21188-sturdy-infinity-cube). Started 9:41 PM CT under Cody's typed go. FINISH, print_error 0, ~12:50 AM CT.
- #13 kid_turtles4_aroundcubes_pla_A4 (sha dbe25b2c…06bd8ee3; Cutie Baby Turtle by squinn, CC BY-NC-SA, https://www.printables.com/model/504361-cutie-baby-turtle), printed around the cubes left on the bed under Cody's one-time waiver (keep-out zone, ABL and calibrations off). Started ~12:51 AM CT; paused at layer 0 on foreign-object detection, error 83918958 / 0500-806E (it saw the cubes). Stopped. FAILED, no plastic.
- #14 kid_turtles4_aroundcubes_noFOD_pla_A4 (sha 40350e4b240ac5501b8d7e31a29df1994f3814d69b8fed51f7f851ae5e7ab772; M972 S24/S26/S42 commented out, md5 regenerated, 0 keep-out violations). Started 12:57:29 AM CT; last read RUNNING L1/115, error 0 at 1:06 AM CT, ETA ~2:59 AM. FAILED per Cody (7:08 AM CT Nov 17), cause unknown.
- Printing paused per Cody, 7:08 AM CT Nov 17, until he returns and lifts it himself.

## CAD change 2026-11-02

**Cap:** **76 × 160 × 41.4 mm** / lid 7 mm; one P124 pocket 66.6 × 113.6 × 1.2; channel gable + spine V; supports off. Print #3 is this geometry.

**Pods (plan of record):** dual-cell **92 × 68 × 24.5** — 1 × Adafruit 1781 + 1 × Qwiic Buzzer per pod (2×1781 pending Cody’s purchase approval). Restored `stl/node_v1_pod/`. Battery/cue redesign (100×90×26 + 92×68×26): **PROPOSED ALTERNATIVE, NOT APPROVED** under `stl/alt_pods_unapproved/` (was `node_v1_pod_battery` / `node_v1_pod_cue`). Mono vs stereo buzzer is Cody’s open call.

Offline Orca on earlier **76×160×29** STLs: stock PLA supports on 4h41m/140 g, supports off 4h06m/134 g, fast-fit 3h15m/133 g (vs old 62×142 cap 3h32m/93 g).

**Stale slices:** `F2_cap.gcode.3mf` (old 62×142 cap), `F4_pod_left.gcode.3mf` (old pod outline). Re-slice current exports. F3 counterweight unchanged.

## Fix history — cap insert pockets / lid screw length

**Cap v3 (print #3, Nov 2, `951e057`)** has shallow heat-set insert pockets (lid ~2.2 mm; base clamp ~2 mm) so an M3×4 insert cannot seat, and the lid through-screw note said M3×20 which cannot reach the lid through the 41.4 mm base. CAD fix: Ø4.0 × ~5 mm insert pockets (lid + clamp), deeper Ø8 counterbore + cone for **M3×40** button + bonded washer.

**Rescue the printed #3 without reprint:** drill each lid insert pocket and each base clamp-bar pocket with a **4 mm bit to 5 mm deep** before pressing inserts; deepen the base lid-screw counterbore to accept the M3×40 head (Ø8 to ~z=4–6), or reprint the fixed STLs.

## Template notes — slim cap + assembly aids (REV AID1)

**Next print plate (bases, restart after #4):** slim `node_cap_base_saddle` + `node_pod_base` + `node_pod_base_R` (+ optional `test_coupon` / `scale_bar_xyz`). PLA fit; **cap slim supports off**; **pods need supports** for cavity rails/cradle in FDM (re-slice — do not trust stale `F4_pod_left`). Brim for ASA later. Watertight STLs (bed face flat; labels on inside floor / outer wall).

| Callout | Value |
| --- | --- |
| Cap lid / clamp | **M3×16** / **M3×14** (M3×18 can bottom in the 5 mm lid pocket) |
| Pod lid | **M3×25** |
| Inserts | M3×4 (Adafruit 4255) |
| Cap / pod labels | `REV AID1` — see `cad/ASSEMBLY-AIDS.md` (5 × 0.8 mm bitmap; not on bed face) |
| Aids budget | ~**13 g** / ~**50 min** on the bases plate before coupon ladder + XYZ scale |

Log the restart plate here when started (file, material, layers, estimate, route).
