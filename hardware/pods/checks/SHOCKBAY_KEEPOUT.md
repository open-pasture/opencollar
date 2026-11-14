# Shock/electrode bay keep-out vs A3 action pod + U clamp (Sat Nov 14 2026, ~6:10 AM CT)

**Result: FAIL.** The A3 action pod has **no defined shock bay**, and the strap and clamp bars sit inside the space PR #28 reserved for it. This is CAD geometry only. Nothing has been printed or fit-tested.

Data: `checks/shockbay_keepout.json` (from `checks/shockbay_keepout.py`). Renders: `review/r4_07_shockbay_keepout_iso.png`, `_section_long.png` (x = 0), `_section_cross.png` (y = -27.5). Rebuild them with `review/build_r4_07_shockbay.py` and then `review/compose_r4_07.py`. The Blender scene is `review/r4_07_shockbay_keepout.blend`.

## Where the keep-out comes from
- **Pilot = production** (Cody, Nov 4): each pod keeps a complete, blank-plugged spot for the future shock module.
- The A3 staged CAD (`cad/`, README, FIT_REPORT_A3) does **not** define a shock bay.
- The last definition is PR #28 @ [352e734](https://github.com/open-pasture/opencollar/commit/352e734b2f5a40f99c3b160a3745250787409c1e), in `hardware/rook/d6/pod_saddle.py` (Option A neck saddle) and `pod.py`. All of its sizes are **placeholders, not a spec**.

| reserved item | size (mm) | pod-local position |
|---|---|---|
| module keep-out (40×25×8 + 3 XY / 2 Z) | 31 × 46 × 10 | x ±15.5, y −44.5…1.5, z −2.5…−12.5 |
| driver keep-out (35×22×6 + 3 / 2) | 28 × 41 × 8 | x ±14, y 3.5…44.5, z −2.5…−10.5 |
| saddle body (bay + 2.5 face wall + R220 neck face) | 52 × 97 × 13.7 | x ±26, y ±48.5, z 0…−13.7 |
| wire pass-through + gland | Ø8 / Ø12 | (0, −28) |
| saddle M3 mounts | Ø3.4 | (±18, ±32) |
| blank electrode lands (unfitted) | Ø10 | (0, −34), (0, −9), neck face |

The A3 base keeps the pr28 pod-local XY frame (mount face at +Y 46), so these positions carry over 1:1. On pr28 the saddle's flat face sat on the pod bed. Here that face is placed on the A3 underside (z = 0), with the bay toward the neck (−z).

## What A3 has at that spot
- The pr28 Ø8 wire pass-through at (0, −28) and the 4 saddle M3 holes at (±18, ±32) survive only as **blind stubs opening from the cavity side at z ≥ 1.75**. Underneath them is a **1.75 mm solid skin**, because the 1.1 mm floor was added below the old floor.
- Nothing opens from the underside. There is no plug seat and no saddle interface.

## Clearances: nominal clamp (3.8 strap, stack 1.0 + 0.5, lip gap 4.0, bars at y −27.5 / +22.5)
| pair | value (mm) | pass? |
|---|---|---|
| strap (z −4.0…−0.2) → module / driver keep-out top (z −2.5) | **−1.5 (overlap)**; 2139 / 1722 mm³ | FAIL |
| clamp bar base inside the keep-out footprint (z −8.0…−3.4, base 4.0 + ribs 0.6) | **4.6 thick overlap**; 2465 mm³ module (bar y −27.5), 2227 mm³ driver (bar y +22.5) | FAIL |
| bar bottom below keep-out top | 5.5 | n/a |
| M3 head (x 33.6, r 2.75) → module / driver keep-out | 15.35 / 16.85 | PASS |
| M3 shank → module keep-out | 16.6 | PASS |
| C-clip spacer (OD 7) → module keep-out | 14.6 | PASS |
| width shim (inner face x 22.7) → module keep-out | 7.2 | PASS |
| M3 head → 52 mm saddle envelope | 4.85 | PASS (lateral only) |
| strap / bars vs saddle envelope | strap 16384 mm³, bars 8465 mm³ inside | FAIL |
| saddle M3 (±18, ±32) and wire pass-through (0, −28) | all 4 mounts and the pass-through lie under a clamp bar (bars cover y −37.5…−17.5 and 12.5…32.5) | FAIL |

## Strap range
| case | strap z | strap intrusion | bar overlap |
|---|---|---|---|
| 3.0 strap, stack 0.5 (gap 3.0) | −3.0…0 | **0.5** (713 mm³ module) | 2465 mm³ |
| 3.8 strap, stack 1.5 (gap 4.0) | −4.0…−0.2 | **1.5** (2139 mm³) | 2465 mm³ |
| 7.5 strap, stack 4.5 (gap 7.0) | −7.0…0 | **4.5** (6417 mm³) | 2465 mm³ |

## Plain reading
- The U-clamp design puts the strap flat against the pod underside and puts the bars right under it. That is exactly the layer where the pr28 saddle and bay sat.
- The screws, spacers and inserts at x ±33.6 stay clear of the bay sideways.
- The strap and the bar bases do not stay clear.
- The 30 mm gap between the two bars is too short for the 46 mm module keep-out, even before counting the strap.

Options for Cody / op-architect (not done here):
1. **Hang the bay below the bars.** The keep-out top moves to z −10.5 at the nominal setting (−9.5 to −13.5 across the strap range), adding 7–11 mm of standoff from the neck. The saddle would also need new fasteners, because its M3 holes are under the bars.
2. **Integral bay (pr28 Option B).** Put the bay, about 29 × 43, in the pod itself and route the strap and bars around it. That means moving the bars to the pod ends or splitting the strap path, which changes the approved clamp layout.
3. **Move the shock module to the cap / top unit.** `docs/BOTTOM-BAY.md` l.95–97 already says this, and the location was never decided.

Whichever option is picked, A3 still needs a sealed, blank-plugged pass-through that opens toward the bay. Today it is closed by a 1.75 mm skin.
The R pod mirrors L (bars at y −22.5 / +27.5) and gives the same result.
