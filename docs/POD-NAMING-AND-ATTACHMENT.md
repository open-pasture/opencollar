# Pod naming and strap attachment

Status: **DRAFT for Cody's review** (op-maker, overnight Fri Nov 13 → Sat Nov 14 2026 CT; action pods revised to the true D4 shell ~1 AM CT Sat Nov 14, "option b"). Nothing in here has been printed or fit-tested.
CAD: `hardware/pods/`. Renders: **`hardware/pods/review/r4_01`…`r4_06` (D4-style action pods, plate A3)** and `r4_07_shockbay_keepout_*` (shock-bay keep-out, FAIL, see `hardware/pods/checks/SHOCKBAY_KEEPOUT.md`). The r1–r3 review renders are not in git. Fit report: `hardware/pods/checks/FIT_REPORT_A3.md`.

## 1. Naming

| Pod (collar position) | Parts (file stems) | Former names | Notes |
|---|---|---|---|
| **action_pod_L** (left side) | `action_pod_L_base`, `action_pod_L_lid` | `pod_L_base`, `pod_L_lid` (PR #28 @ 352e734, prints #8/#9) | battery + buzzer pod |
| **action_pod_R** (right side) | `action_pod_R_base`, `action_pod_R_lid` | `pod_R_base`, `pod_R_lid` | mirror of L |
| **ballast_pod** (under the throat) | `ballast_pod_tub`, `ballast_pod_lid` | `cw_tub`, `cw_lid` (counterweight, print #10) | keeps the cap on top |
| **cap_pod** (top of the neck) | `cap_pod_base`, `cap_pod_lid` | `cap_base`, `cap_lid` (X2a, print #6) | electronics + P124 panel |
| clamp hardware (×4 pods) | `clamp_bar`, `spacer_0p5`, `spacer_1p0`, `spacer_2p0`, `width_shim` | `clamp_bar` (print #10, old tunnel design) | 2 bars per pod |

Rules: `<role>_pod[_<side>]_<part>`. Side is L/R as worn, looking from behind the animal. Parts are `base`/`tub` (the strap-side half, printed on the bed) and `lid` (the outer half). Plates are named `<stage>_<material>_<letter>_<contents>`, e.g. `overnight_petg_A3_d4` (current; supersedes `overnight_petg_A2_trim` and `overnight_petg_A_action_pods_clamps`).

## 2. Attachment: adjustable underside clamp (approved by Cody 11:18 PM CT Fri Nov 13)

- Every pod underside is **flat** (it prints on the bed). The strap runs along the pod's long axis (Y) under the pod. There is no tunnel.
- **2 clamp bars per pod**, each held by **2 × M3 screws** into **M3 heat-set inserts**.
  - **Action pods (A3, D4 shell):** inserts in **side ears** outside the cavity at **x = ±33.6**, Ø4.0 × 6.5 blind pockets from the flat underside, ear R5 × 9.4. Nothing under the cavity floor (no plinth). Bar centres at plan centre ±25 (L y −27.5/+22.5, R −22.5/+27.5). Pod width across the ears 77.2.
  - Ballast / cap pods (unchanged r3 design): pockets at x = ±29.3 under the floor, bar centres ±35 (ballast) / ±50 (cap).
- **Insert walls (action A3):** 3.0 mm of material around every pocket, 2.9 mm above it, 2.4 ring check misses 0.0 mm³. Screws can't reach the cavity: they stop in the ear.
- **Clamp bar:** **78** × 20 × 6.5 U-channel (holes re-fitted to x = ±33.6 for the A3 ears). ⚠ Ballast/cap pods still have inserts at ±29.3, so they need the r3 70 mm bar (holes ±29.3); `clamp.py` now builds only the 78 mm action-pod bar (4 mm base, 2.5 mm lips, 50.0 mm clear between the lips). It has three 45° triangular grip ribs 0.6 mm high across the strap, Ø3.4 holes, and a Ø6 × 1.5 head counterbore on the neck face. The **neck-face edges are rounded R2**, using a support-free 45°-start roll on the bed. The bar prints neck face down with the channel up.
- **Thickness adjustment:** C-clip spacers (OD 7, ID 3.4, 2.6 mm slot so they clip on the screw without taking it out) in 0.5, 1.0 and 2.0 mm. The kit per hole is 1×2 + 2×1 + 1×0.5 = 4.5 mm, which gives a lip-to-pod gap of 2.5–7.0 mm. ⚠ At 0.20 mm layers the 0.5 mm clip prints as **0.4 mm**.
- **Width adjustment:** two removable 2.3 mm width shims per bar (20 × 2.5 × 2.3, printed lying down) take the 50.0 channel to 45.4 for a 44.45 mm (1-3/4") strap. Take them out for straps up to about 49 mm.
- **Clamp screws (action A3):** tip = L − 5 − stack, keep ≤6.3 in the 6.5 pocket: **M3×10** for stack 0–0.5, **M3×12** for 1.0–2.5, **M3×14** for 3.0–4.5 (≥4.5 engagement each). For a 3.8 mm strap use a 1.5 mm stack (1.0 + 0.5) and M3×12: gap 4.0, ribs pinch about 0.4 mm.
- **Lid screws (action A3):** M3×8 countersunk (ISO 10642) into the original column inserts; M3×10 bottoms out.
- **Strap removal:** take out 2 screws per bar. The bar, clips and shims drop away and the strap lifts out of the open channel.

## 3. Support-free rule

- No supports in cavities, insert pockets, screw bores or strap paths. Strap paths are now a bed face (pod underside) plus an open channel (bar), so no strap surface ever touches support.
- No flat overhangs over 45° except short bridges. New outer surfaces use 45°-start rolls (bed edges) or convex rolls (up-facing edges).
- Plate A3 is sliced with supports **disabled** (`support_used=false`, 0 support extrusions). With supports forced on, Orca would only flag inherited internals:
  - the action-base +Y mount-recess ceiling (36 × ≈3.4 mm, anchored on 3 sides, now at z 19.3 with a 1 mm inner fin from z 16.3; it was tree-supported on #8)
  - the cavity-top rim-ledge chamfer, exactly 45° (no support at a 40° threshold, the same as #8)
  - the A3 lids' 45° edge chamfer (lid prints top-down; clean at 40°)
  - Ø4 insert-pocket ceilings
  - lid screw-bore steps (about 1.3 mm annuli)
  - the ballast 3.2 mm ledge at z 17.6 (printed unsupported on #10)
  - the cap-base ceiling at z 20.9 (the old cap printed with supports ON). **Plate B decision is open.**

## 4. Strap root cause (why the old pods did not take the strap)

- The printed pod skirt tunnel (#8, 352e734; the same pods as the failed #7) is a **closed tunnel 46.45 × 3.80 mm clear**, with a **flat 46 mm bridged roof** that needed supports. The CAD comment said 3.4 mm, but the printed STL measures 3.80.
- +5% fit allowance → **48.77 × 3.99 mm**.
- The strap is **Heritage 20266, 1-3/4" (44.45 mm) double-thick nylon**. Its **thickness is unmeasured**. Double-thick nylon is likely around 3.5–4.5 mm, which sits at or over a 3.80 mm tunnel with no allowance, and the flat 46 mm bridge sags into it. The clamp replaces the fixed tunnel with a 2.5–7.0 mm adjustable gap and a 50 mm channel.

## 5. Material (interim)

- **PETG (AMS A2, grey #7F7E83)**, Bambu Generic PETG profile (GFG99): **nozzle 255 °C, Textured PEI bed 65 °C** (plate A3; profile `filament_petg_bed65.json`), 0.20 mm layers, max volumetric 12 mm³/s. At 65 °C the `bed_temperature_too_high_than_filament` warning (bed = 70 °C vitrification) is gone. A2 was sliced at 70.
- Earlier messages said "about 245/75". **The values actually sliced are 255/65 (A3)**; A2 was 255/70.
- Interim only: the material decision (materials-decision-2026-11-03.md) still stands for production. A1 holds PLA but Cody is out of it, so **never map to A1**.

## 6. The three open issues and their fixes

| # | Issue | Fix in this drop | Still open |
|---|---|---|---|
| 1 | **The strap doesn't fit** the 46.45 × 3.80 closed tunnel (see §4) | Flat underside + adjustable clamp bars (2.5–7.0 gap, 50 → 45.4 width shims), on all 4 pods | Measure the strap thickness; physical fit test |
| 2 | **Supports in the strap path and cavities** (the tunnel roof is a 46 mm bridge on supports) | Tunnel removed; the strap path is a bed face and an open channel; plate A has supports disabled (0 support extrusions) | Plate B cap-base ceiling (z 20.9) support decision |
| 3 | **Boxy, sharp shells against the neck** | **Action pods (A3): true D4_contoured_v3 plan (R10/R19), R10.24 rolled shoulder + 45° lid chamfer (4.4 in over 9.84), flat underside, inserts in side ears, no plinth: 67 × 97 × 25.8** (A2 was 68 × 97 × 37.2; D4 21.3). Ballast/cap: r3 contour (R8/R14, rolls). Bar neck edges R2 | Action pods still **4.5 mm taller than D4** (locked cavity 20.7 internal + 2.5 floor + 2.6 lid); ears widen to 77.2; no on-animal check |

### Action pods A3 vs pr28 (honest list)
- **Tongue/groove dropped:** the lid is a flat 2.6 mm plate on the wall top, located by the original lid key and 4 screws. Less water/dust sealing than the old joint; add a gasket or bead if sealing matters.
- Floor thickened 1.4 → 2.5 (added below; cavity untouched). The old skirt/tunnel and the insert plinth are gone.
- The shoulder rolls in by 3.0 at the seam on all sides, including the +Y mount face above z ≈16: the fairing (POD.md: H 20, meets the lid roof at the seam) and the mount plate need a check against the rolled face.
- The floating sound-port boss was dropped again (it was a stray island).

### Dropped or changed relative to the printed sources (r3, all pods)
- Floating features in the printed STLs were removed: the pod sound-port boss (a 4 mm stray island above the mount-recess floor) and the cap end lugs (1.1 mm off the end face).
- Pod lid: the old `001` ID text and the 0.4 mm screw dots on the crown were not carried over.
- Ballast lid: the old strap rails were removed (3685 mm³). Cap lid: 919 mm³ removed by the side roll.
- Ballast/cap inserts at x = ±29.3; the ballast plinth is 11.5 mm and the cap plinth is 6.0 mm. (Action pods: see A3 above.)
