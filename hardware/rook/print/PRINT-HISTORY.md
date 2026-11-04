# OpenCollar print history (maintained by op-maker)

Printer: Bambu Lab P2S (home, Cody's LAN 192.168.1.248, cloud mode)

| # | Date | Part | Material | Status | Notes |
|---|------|------|----------|--------|-------|
| 1 | 2026-11-01 | Node V1 cap (node_cap_*) | PLA | Done (obsolete CAD) | First print on the new P2S. **Old geometry:** 62 × 142 mm cap with dual Voltaic P122 pockets (panels never bought). File/settings not fully captured. |
| 2 | 2026-11-02 | Node V1 cap (`F2_cap.gcode.3mf`) | PLA | Done — looks great (obsolete CAD) | Same old 62 × 142 / P122 CAD. Started via Bambu Connect on Openpasture-1. See PRINTING.md. |
| 3 | 2026-11-02 | Node V1 cap v3 (76×160, P124 pocket, gabled roof, no supports) | PLA (Bambu PLA, AMS A1) | Started | From commit `951e057`. P2S Openpasture-1. Fast-fit profile (0.28 mm, 21 mm³/s, 10% gyroid, no supports). 148 layers; estimate 3h51m, 156.27 g. Started ~3:53 PM CT via Bambu Connect on Cody's Mac. |
| 4 | 2026-11-02 | Bases-only plate: slim `node_cap_base_saddle` + `node_pod_base` (L) + pod R mirrored | PLA | Stopped (~16 min) | Pre-aids STLs (no cradle/labels). 0.16 mm layer, 153 layers; est 5h55m, 173.3 g. Started 8:19 PM CT via Bambu Connect on Openpasture-1; Cody stopped ~8:35 PM CT to restart with assembly aids (REV AID1). **Lid screw decision: M3×16** (clamp M3×14). |
| 5 | 2026-11-02 | Aids plate v7: slim cap base + pod L + pod R + test coupon + XYZ scale bar (main `7a3660f`, PR #18 `f906926`) | PLA | Started 10:33 PM CT, result pending | `aids_plate_0.16_PLA_p2s.gcode.3mf` (cap_set_v7), 0.16 mm, 15% gyroid, 4 walls, tree supports on pods only, 153 layers, estimate 6h55m / 192.39 g. Sent via Bambu Connect on Openpasture-1, PLA in AMS A1. 15% gyroid is a fit test only, not a strength test. |

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
