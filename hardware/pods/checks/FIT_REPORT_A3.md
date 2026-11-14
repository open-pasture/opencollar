# Fit report: D4-style action pods (A3), Sat Nov 14 2026 ~1:15 AM CT. CAD only, nothing printed or fit-tested.

Data: `checks/fit_report_A3.json`, `checks/d4pod_report.json`, `checks/wallcheck_oc_2p4.json`, `checks/overhang_audit.json`.

## Cavity vs locked spec (POD.md: 82 × 58 × 19.5, 58 across X / 82 along Y)
| | spec | A3 L | A3 R | pr28 printed |
|---|---|---|---|---|
| cavity X × Y | 58 × 82 | 58.0 × 82.25 | 58.0 × 82.25 | 58.0 × 82.25 |
| floor → lid underside | ≥19.5 | **20.7** (1.2 headroom) | 20.7 | 20.7 |
| floor | — | **2.5** (added 1.1 below) | 2.5 | 1.4 |
| internals (columns, buzzer seat (0,28), cell bay, glyphs, rim ledge, mount recess/port, lid key) | locked | copied from the printed pr28 STL, not re-modelled; material in the cavity prism 4758.6 → 4761.8 mm³ (slice diffs ≤0.5 mm²) | same | — |

## Inserts (moved out of the cavity, nothing under the floor)
- 4 × M3 heat-set per pod in **side ears** at x = ±33.6; L y = −27.5 / +22.5, R y = −22.5 / +27.5 (plan centre ± 25).
- Pocket Ø4.0 × 6.5 deep, blind, opening on the flat underside. Ear R5.0 × 9.4 high.
- Measured wall around the pocket **3.0 mm** at z 1 / 4 / 6 (nearest surface = ear outside); 2.9 mm cap above the pocket; the 2.4 ring check misses 0.0 mm³ at all 4.
- Pod is **77.2 mm wide across the ears** (67.0 plan).

## Clamp screws (bar 6.5 with Ø6 × 1.5 counterbore → 5.0 in the bar; tip = L − 5 − stack; pocket 6.5, keep tip ≤6.3)
| stack (mm) | lip-to-pod gap | screw | tip into ear |
|---|---|---|---|
| 0–0.5 | 2.5–3.0 | M3×10 | 5.0–4.5 |
| 1.0–2.5 | 3.5–5.0 | M3×12 | 6.0–4.5 |
| 3.0–4.5 | 5.5–7.0 | M3×14 | 6.0–4.5 |
M3×12 bottoms below a 0.7 mm stack; M3×14 bottoms below 2.7 mm. For a 3.8 mm strap: 1.0 + 0.5 stack, M3×12 (gap 4.0, ribs pinch ~0.4). Bar holes at ±33.6 = insert x; bar centres = insert y.

## Lid screws
- Same 4 columns as pr28 (L (±22,36), (−19,−36), (22,−36); R mirrored). Column top z 22.8 (0.4 under the seam, as before), insert bore bottom z 16.3.
- Lid 2.6 thick with ISO 10642 countersinks (Ø6.3 × 1.45). **Use M3×8 countersunk**: 5.0 engagement, tip 1.5 above the bore bottom. M3×6 gives only 3.0; **M3×10 bottoms out**.

## Heights and shape
| | PR #21 (old) | A2 (pr28 reskin) | **A3 (new)** | D4_contoured_v3 |
|---|---|---|---|---|
| size (mm) | 69.8 × 92 × 26.2 | 68 × 97 × 37.2 | **67.0 × 97.0 × 25.8** (77.2 at ears) | 67 × 97.2 × 21.3 |
| plan corners | R≈7 | R9 | **D4 plan, R10/19** | R10/19 |
| top edge | square | roll ≈2.4 × 2.5 | **R10.24 arc (vertical → 45°) on the base + 1.2 land + 1.4 × 45° chamfer on the lid: 4.4 in over a 9.84 drop** | shoulder ≈9 drop over 7.4 |
| crown | 0 | 0 | 0 (flat lid) | ≈0.4 |
| underside | flat | flat | **flat** | flat |
Why not 21.3: floor 2.5 + locked internal 20.7 + lid 2.6 = 25.8. The shoulder run is limited to 4.4 by the 4.5 mm side wall outside the 58 mm cavity (D4 runs 7.4 because its cavity is smaller).

## Walls / manifold (oc.check_printable, min wall 2.4)
| part | manifold | thin area new vs printed source (mm²) | note |
|---|---|---|---|
| action_pod_L/R_base | **yes** (source: 2 bad edges) | 2512 / 2534 vs 3739 | remaining thin faces are copied internals (rim ledge, lintel fin, glyphs, column bores) |
| action_pod_L/R_lid | **yes** | 759 / 760 vs 2564 | countersink rims (2.6 lid − 1.45 csk) and the copied lid key |
| clamp_bar | yes | 7.1 | 1.74 at the c'bore |
| spacers | yes | — | 0.5/1.0/2.0 thick by design; 0.5 prints 0.4 |
| width_shim | yes | — | 2.3 by design |

## Support-free
- Plate sliced with supports **off**: 0 support extrusions.
- Mesh audit (faces >45° from vertical, not on the bed): base 221 mm² total, of which bridges = 4 × Ø4 insert-pocket ceilings (z 6.5), 1.2 mm rim-ledge step (z 22.95), and the **inherited mount-recess ceiling at z 19.3 (36 × ≈3.4 mm, anchored on 3 sides; a 1 mm inner fin starts at z 16.3)**. Lid 2 mm². Bar: 2 × Ø6 c'bore ceilings.
- Orca audit with supports forced on at 40°: lids/spacers/shims 0; bases only at the insert pockets and the mount recess; bars at the c'bores.
