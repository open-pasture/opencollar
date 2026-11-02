# OpenCollar print history (maintained by op-maker)

Printer: Bambu Lab P2S (home, Cody's LAN 192.168.1.248, cloud mode)

| # | Date | Part | Material | Status | Notes |
|---|------|------|----------|--------|-------|
| 1 | 2026-11-01 | Node V1 cap (node_cap_*) | PLA | Done (obsolete CAD) | First print on the new P2S. **Old geometry:** 62 × 142 mm cap with dual Voltaic P122 pockets (panels never bought). File/settings not fully captured. |
| 2 | 2026-11-02 | Node V1 cap (`F2_cap.gcode.3mf`) | PLA | Done (obsolete CAD) | Same old 62 × 142 / P122 CAD. Started via Bambu Connect on Openpasture-1. See PRINTING.md. |

## CAD change 2026-11-02 (not yet printed)

**Cap:** **76 × 160 × 41.4 mm** / lid 7 mm; one P124 pocket 66.6 × 113.6 × 1.2; channel gable + spine V; supports off.

**Pods (battery decision):** no 18650 / 1781 buy. **Battery pod (left) 100 × 90 × 26** holds the owned Adafruit 353 pack; **cue pod (right) 92 × 68 × 26** holds the one Qwiic Buzzer (mono cues). Old dual-cell `exports/node_v1_pod/` removed.

Offline Orca on earlier **76×160×29** STLs: stock PLA supports on 4h41m/140 g, supports off 4h06m/134 g, fast-fit 3h15m/133 g (vs old 62×142 cap 3h32m/93 g).

**Stale slices:** `F2_cap.gcode.3mf`, `F4_pod_left.gcode.3mf`. Re-slice current exports. F3 counterweight unchanged.
