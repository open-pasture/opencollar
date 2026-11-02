# OpenCollar print history (maintained by op-maker)

Printer: Bambu Lab P2S (home, Cody's LAN 192.168.1.248, cloud mode)

| # | Date | Part | Material | Status | Notes |
|---|------|------|----------|--------|-------|
| 1 | 2026-11-01 | Node V1 cap (node_cap_*) | PLA | Done (obsolete CAD) | First print on the new P2S. **Old geometry:** 62 × 142 mm cap with dual Voltaic P122 pockets (panels never bought). File/settings not fully captured. |
| 2 | 2026-11-02 | Node V1 cap (`F2_cap.gcode.3mf`) | PLA | Done (obsolete CAD) | Same old 62 × 142 / P122 CAD. Started via Bambu Connect on Openpasture-1. See PRINTING.md. |

## CAD change 2026-11-02 (not yet printed)

Cap resized for **one owned Voltaic P124** (see `HARDWARE-FIT.md`): outline **76 × 160 × 29 mm** base / **7 mm** lid, pocket **66.6 × 113.6 × 1.2 mm**, GPS patch at the −Y lid end, spine relief is a **45° V-groove** (no supports). Clamp bar / strap channel / insert spacing unchanged.

**Stale slices:** `print/sliced/p2s_pla/F2_cap.gcode.3mf` still contains the old 62 × 142 parts. Re-slice the new `exports/node_v1_cap/*.stl` on `p2s_pla` (supports off) before the next cap print. Pod / counterweight STLs and F3/F4 slices are unchanged.
