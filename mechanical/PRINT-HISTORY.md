# OpenCollar print history (maintained by op-maker)

Printer: Bambu Lab P2S (home, Cody's LAN 192.168.1.248, cloud mode)

| # | Date | Part | Material | Status | Notes |
|---|------|------|----------|--------|-------|
| 1 | 2026-11-01 | Node V1 cap (node_cap_*) | PLA | Done (obsolete CAD) | First print on the new P2S. **Old geometry:** 62 × 142 mm cap with dual Voltaic P122 pockets (panels never bought). File/settings not fully captured. |
| 2 | 2026-11-02 | Node V1 cap (`F2_cap.gcode.3mf`) | PLA | Done (obsolete CAD) | Same old 62 × 142 / P122 CAD. Started via Bambu Connect on Openpasture-1. See PRINTING.md. |

## CAD change 2026-11-02 (not yet printed)

Cap resized for **one owned Voltaic P124** (see `HARDWARE-FIT.md`): outline **76 × 160 × 29 mm** base / **7 mm** lid, pocket **66.6 × 113.6 × 1.2 mm** (VHB depth — panel is 3.1 mm in `dims.py` but a full pocket would hit lid inserts), GPS patch at the −Y lid end (`PANEL_Y = +11` deliberate), spine relief is a **45° V-groove**, strap-channel ceiling is a **corrugated 45° V roof**, lid/base/bar screw seats are conical (no flat overhangs). Supports off.

Offline Orca on the **pre-chamfer** STLs (flat channel / cylindrical cbores): stock PLA supports on 4h41m/140 g, supports off 4h06m/134 g, fast-fit 3h15m/133 g (vs old 62×142 cap 3h32m/93 g). Those STLs were superseded — **re-slice** `exports/node_v1_cap/*.stl`.

**Stale slices:** `print/sliced/p2s_pla/F2_cap.gcode.3mf` still contains the old 62 × 142 parts. Pod / counterweight STLs and F3/F4 slices are unchanged.
