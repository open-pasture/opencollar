# D8 X2a hardware clearance audit

**Draft only. No print. No merge.**  
Baseline: Plate X2a as staged at `4e52f6c` (`cap_base.stl` / `cap_lid.stl` / `cap.py`).  
Updated: this PR’s D8 `cap.py` (datasheet-corrected).

`assembly_check` = **geometry / interference only** — not a physical fit or print test.  
25×42 cm neck ellipse / R220 = **sizing model**, not measured cattle.

Machine-readable twin: `d8_x2a_hardware_clearance_audit.json`.  
Cross-section figure (trimesh on `4e52f6c`): `x2a_clearance_cross_sections.png` (attached in review thread).

## Vendor sources (locked)

| Part | Source | Key dims |
| --- | --- | --- |
| Adafruit #960 | [GPS-01.pdf](https://cdn-shop.adafruit.com/datasheets/GPS-01.pdf) | Housing **41.2 × 38.5 × 13.3** mm; 5 m RG174; SMA male; magnetic IP66 |
| SMA↔U.FL bulkhead | Adafruit 851 class | 1/4"-36 UNEF = **Ø6.35** thread; hex nut ~8–10 mm AF; 15 cm RG178 → U.FL |
| nRF9151 Connect Kit | makerdiary wiki / product | PCB **55.88 × 20.32 × 1.0**; height no headers **6.21**; USB-C 9.0 w / +3.26 / +1.5 overhang; J2 **−1.95** |
| Voltaic P124 | [P124_ds.pdf](https://voltaicsystems.com/content/P124_ds.pdf) | **113 × 66 × 2.6** mm ±0.5 (brief 2.8 is NOT vendor) |

## Summary

| Component | X2a (`4e52f6c`) | Updated D8 (mesh-verified) |
| --- | --- | --- |
| nRF9151 | no locating walls; **no J2 recess**; KIT/PIN1 glyphs under PCB; **no USB-C access** | Raised locating ribs **57.6 × 21.4** clear; J2 **2.8 mm** drop in STL; glyphs clear; **USB tunnel open**; `cap_usbc_plug.stl` |
| Adafruit #960 | internal GNSS recess 25.8³ sized for bare patch; **FAIL** vs 41.2×38.5×13.3; Ø6.0 SMA **blocks** Ø6.35 bulkhead; keep-clear **violated** (5.4 mm overlap) | **External mount only**; internal recess **removed**; SMA bulkhead **Ø6.6** + 10 mm AF nut seat; U.FL route channel |
| Voltaic P124 | pocket 66.6 × 113.6 × **2.3** → panel 0.3–0.5 **proud** | Pocket **67.2 × 114.2 × 3.1** (+0.6/side; flush for 2.6–2.8 + thin VHB) |

### Mesh bug fixed after `a07db1b`

`a07db1b` coded kit/J2/USB against `CAP_FLOOR=6` with `pocket_box` cutting *up into cavity air* and a wall-only USB punch — **none of those cuts appeared in `cap_base.stl`** (floor stayed flat at z≈20; J2 only 0.1 mm; USB solid y≈−55..−77). Fix: raised `locate_rib_rect` fence, J2 cut *down* into floor solid, full cavity→exterior USB tunnel, glyphs moved outside PCB footprint, export `stl/cap_usbc_plug.stl`. Verified by `review/verify_cap_base_x2a_mesh.py` on the exported STL (PASS).

## Honest end-margin math (why 960 is external)

Centered P124 on 164 mm cap:

\[
\frac{164 - 113}{2} = 25.5\ \mathrm{mm\ per\ end}
\]

A 25 mm ceramic patch with a strict **15 mm** keep-clear from the panel edge needs **15 + 25 = 40 mm** beyond the panel — **14.5 mm shortfall**. Do **not** cut an internal GNSS recess that pretends to honor the keep-clear while the 113 mm panel sits on the 164 mm lid. Weekend path: strap/seat the **41.2 × 38.5 × 13.3** puck outside the cap (away from P124 metal), route via SMA-female bulkhead → U.FL into the nRF9151.

## (a) makerdiary nRF9151 Connect Kit

Physical: PCB **55.88 × 20.32 × 1.0**; USB-C overhang **+1.5** → length **57.38**; USB **+3.26** above; J2 **−1.95** below; 4×Ø1.4 inset 1.27; top height no headers **6.21**.

| Axis | X2a (`4e52f6c`) mesh/CAD | Clearance | Updated D8 | Clearance |
| --- | ---: | ---: | ---: | ---: |
| Locating pocket X | none (cavity 66; intent 56.7) | unlocated | **57.6** | **+0.86** vs 55.88 (+0.43/side) |
| Locating pocket Y | none (intent 21.1) | unlocated | **21.4** | **+0.54** vs 20.32 (+0.27/side) — ≥0.4/side intent with USB budget in X |
| USB overhang L | — | −0.68 vs 56.7 intent | 57.6 | **+0.22** vs 57.38 |
| Z pocket | 7.2 intent; floor flat | +0.99 vs 6.21 | **7.5** | +1.29 |
| J2 underside | **FAIL** — no recess (floor z≈20.0) | rocks on J2 | **20 × 12 × 2.6** relief | ≥2.5 deep |
| Floor glyphs under PCB | **FAIL** — KIT / PIN1 raised under footprint | rocks | KIT/PIN1 moved **beside** pocket | flat seating pads |
| USB-C 115200 access | **FAIL** — no wall opening aligned | board out | plugged **10.5×9×6.5** port + **13×3.5×11** elastomer seat at −Y | in-situ path + weather plug |
| Lid-post gap | 1.45 mm to Ø8 post | WARN | unchanged posts | check dry-fit |

## (b) Adafruit #960 + SMA-female bulkhead

Physical housing **41.2 × 38.5 × 13.3** (NOT 28.5×28.5×8.6). Lid only 12 mm thick; base cavity free height ~12.6 → housing **cannot** fit inside.

| Axis | X2a (`4e52f6c`) | vs 960 / rule | Updated D8 | vs 960 / rule |
| --- | ---: | ---: | ---: | ---: |
| Internal recess XY | 25.8 × 25.8 | **−15.4 / −12.7** vs housing | **removed** | N/A (external) |
| Internal recess Z | 4.3 | **−9.0** vs 13.3 | **removed** | N/A |
| Keep-clear to P124 | recess y 51.1..76.9 vs panel to 56.5 | **FAIL** (−5.4 overlap) | no internal patch | **honored** by omission |
| Keep-clear to M3 | edge-to-edge ~14.9 | FAIL marginal | no internal patch | N/A |
| SMA through-wall | Ø**6.0** ±X | **blocks** Ø6.35 1/4"-36 | Ø**6.6** + 10 AF × 1.5 nut seat | **+0.25** vs thread |
| U.FL / RG178 slack | none dedicated | — | 6×28×4 channel to Wio | present |
| Mount | — | — | **external** crest/tail, clear of P124 | weekend walk |

## (c) Voltaic P124

Physical panel **113 × 66 × 2.6** ±0.5 (vendor). Code pocket axes = (X across, Y along).

| Axis | X2a (`4e52f6c`) | Clearance | Updated D8 | Clearance |
| --- | ---: | ---: | ---: | ---: |
| X (across 66) | 66.6 | +0.30/side (tight at +0.5 tol) | **67.2** | **+0.60/side** |
| Y (along 113) | 113.6 | +0.30/side | **114.2** | **+0.60/side** |
| Z depth | 2.3 | **−0.3** vs 2.6 (−0.5 if 2.8) | **3.1** | **+0.5** vs 2.6 (+0.3 vs 2.8) |
| Floor under pocket | ~9.7 | ≥2.0 OK | 12−3.1=**8.9** | ≥2.0 OK |
| Wire exit | Ø4 at y≈46.8 | WARN | 10×8 slot + Ø4.5 | relieved |
| PANEL_Y | 0 (centered) | end margin 25.5 | **0** (centered) | honest; no fake GNSS keep-clear |

## Fixes applied in `cap.py`

- Local D8 overrides only (D5 `d5_dims.py` headlines untouched).
- `PANEL_POCKET=(67.2,114.2,3.1)`, `PANEL_SIZE` z=2.6 vendor, centered `PANEL_Y=0`.
- `KIT_POCKET=(57.6,21.4,7.5)`, `KIT_JST_RELIEF` 2.6 deep, USB plug seat, glyphs clear of PCB.
- Internal GNSS recess **deleted**; `SMA_BULKHEAD_D=6.6` + nut seat; U.FL route channel.
- Cap lid fastener poka-yoke: SCR1 shifted **+3 mm X** (180° reject).

## Still needs Cody caliper (Meat-Proxy)

- P124 actual L×W×T + VHB thickness; proud height in new 3.1 pocket.
- nRF9151 J2 rock check after relief; USB plug body vs seat.
- 960 housing + SMA hex/bulkhead OD vs Ø6.6 (do not ream unasked on printed X2a).
- Confirm elastomer USB plug stock on hand.
