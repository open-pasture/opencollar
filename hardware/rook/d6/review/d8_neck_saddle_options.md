# D8 neck contact — one table before anything becomes the plan

**Draft only. No print. No merge.**  
op-strategy: compare **A / B / C in one table** before picking. The as-drafted saddle (A) conflicts with Cody’s **ease of build** and **same production design** rules (extra parts, end standoff).

**Location:** pulse module in the **side pods** (Cody). Shock off in all builds for now. Interface draft PR #30 — do not edit from this work.

**How to read height:** numbers below are **neck → pod lid-top standoff (mm)**, not “mm above the strap.” Strap-relative review height is a different metric; do **not** treat “25 mm holds” as a neck-fit claim. Measured standoffs use the height-clarification stack (underside end-plane → lid-top ≈ **31 mm** constant + local underside↔neck). Detail: `d8_saddle_height_standoff.md`.

**assembly_check note:** `assembly_check.py` is a **geometry / interference** check on posed STLs. It is **not** a fit test and **not** a print test. A pass count is **not** proof of fit. Opt-B was checked with a separate geometry sanity script only (see below).

---

## A / B / C comparison

| | **(A) Saddle as drafted** (separate part / pod) | **(B) Integral R≈220 underside on pod base** | **(C) B + thin compliant pad later** |
| --- | --- | --- | --- |
| **Idea** | Flat→pod / R220→neck saddle STL; bay + service lid in the saddle | Cut R≈220 concave into the **pod base** skirt bed; **no** extra saddle part | Same hard geometry as B; add a thin TPU/elastomer pad for electrodes when fitted |
| **Parts added / pod** | **+3** (saddle, service lid, wire plug) | **+1** (service lid on neck-face bay) | **+2** (service lid + compliant pad) |
| **Parts / pod total** | **5** (base, lid, saddle, service lid, wire plug) | **3** (base-with-curve, lid, service lid) | **4** (B + pad) |
| **Parts added / collar** | **+6** | **+2** | **+4** |
| **Height above the strap** | **0 mm** added (saddle is neck-side only) | **0 mm** added (curve cut into existing skirt) | **0 mm** hard goods; pad is neck-side when fitted |
| **Neck → lid-top @ centre (mm)** R208 / 218 / 221 | **39.29 / 39.29 / 39.29** (Δ vs flat a6b2118: **+2.55 / +2.82 / +2.90**) | **31.32 / 31.05 / 31.03** (Δ vs flat: **−5.41 / −5.41 / −5.36** — fills mid-gap) | Same as B for the hard shell; pad adds ~1–2 mm toward neck when fitted (TBD) |
| **Neck → lid-top @ ends (mm)** R208 / 218 / 221 | **44.70 / 44.70 / 44.70** (Δ vs flat: **+13.70** all) | **31.00 / 31.00 / 31.00** (Δ vs flat: **0**) | Same as B (+ pad if it covers ends) |
| **What drives standoff** | Bay blank is **thickest at the ends** (rim 13.7 mm); centre solid ~8.3 mm | Gap-fill only (~5.4 mm sagitta into the skirt); **ends stay on the old bed plane** | B + soft stack when populated |
| **Gap vs neck @ 75 / 107 / 130 cm** (flat mid-gap R208/218/221) | Rigid R220 residual after fill: **0.32 / 0.05 / 0.03 mm** — still need compliant electrodes when fitted | Same residual to the hard curve (**≤0.32 mm**); centre air gap of flat design is removed | Hard residual same as B; **pad** takes animal/hair variation |
| **Print orientation** | Saddle: **flat pod-face on bed**, concave UP, light bowl supports (bed rule OK) | **Chosen after test:** curve UP / cavity DOWN — see experiment | Same hard print as B; pad: flat on bed (TPU) |
| **Supports / first layer / bed rule** | Bowl supports on saddle only; pod base still cavity-UP on a **large flat bed** (~1900 mm²) | **Bed rule OK** (curve off bed). First-layer area **~872 mm²** (vs ~1900 cavity-UP) — brim recommended. Overhang area on cavity-down features **~8600 mm²** — needs supports under lips/columns + light bowl supports in the concave | Same as B for the base |
| **Prints cleanly?** | Saddle: yes (proven pattern). Extra plate / ASA part. | **Candidate, not proven on a machine.** Manifold STL built; geometry sanity PASS. Cavity-down is a real process change (supports, adhesion). Side-print rejected. Curve-on-bed rejected. | Same as B + easy TPU pad |
| **Assembly steps** | Print saddle; screw/gasket to pod bed; fit service lid + wire plug; later drop in module | Print curved base; fit service lid on neck-face bay; no saddle mate step | Same as B; stick/seat pad on lands when module fitted |
| **Bay + service lid** | In the **saddle** (module+driver keep-outs, gasket, service lid, wire plug) | **Into the pod base**, opening through the curved underside; service lid on the **neck face** of that opening (PLACEHOLDER envelope in experiment) | Same as B; electrodes on the **module**; pad on the skin side |
| **Ease of build / same production design** | **Conflicts** — +3 parts/pod, end lift +13.7 mm off the neck | **Better** — no extra saddle; same pod count +1 lid; standoff not jacked at ends | Still simple; pad is optional later |
| **CAD status** | **PR #28 current** (`stl/pod_*_saddle.stl`, …) | **Experiment only** — `experiments/opt_b_integral_underside/` (does **not** overwrite PR #28) | Experiment path same as B; pad not modelled as a solid yet |

---

## Opt-B experiment (actually tested)

Path: `hardware/rook/d6/experiments/opt_b_integral_underside/`

| Artefact | Role |
| --- | --- |
| `build_opt_b.py` | Copies `stl/pod_L_base.stl`, cuts R220 underside + placeholder bay, exports experiment STLs |
| `stl/pod_L_base_optB_curveUP.stl` | Chosen orientation (curve UP) |
| `stl/pod_L_base_optB_cavityUP.stl` | Reject orientation (curve on bed) |
| `stl/optb_bay_cover.stl` | Placeholder service lid |
| `opt_b_report.json` | Sagitta, orientations, standoff, overhangs |
| `geometry_check_opt_b.py` | Watertight / bounds / first-layer proxy — **not** a fit/print proof |

Run geometry sanity: `python3 experiments/opt_b_integral_underside/geometry_check_opt_b.py`

**Plain result:** integral R220 cut is manifold; chosen print is curve-UP with supports; first layer smaller than today’s cavity-UP bed; **not** machine-printed here; **not** assembly_check–qualified as a drop-in for PR #28.

---

## Ellipse measurement ask

Check the 25×42 cm ellipse and R 208 / 218 / 221 mm against any real neck measurements on hand. **Do not invent measurements.**

## Pending pick

op-strategy / Cody: choose **A**, **B**, or **C** before any of this becomes the production plan. Until then PR #28 keeps **A** as drafted geometry; **B/C** live only under `experiments/opt_b_integral_underside/`.
