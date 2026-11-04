# D8 neck contact — one design for 75–130 cm

**Draft only. No print. No merge.**  
Pilot unit **is** the production design (Cody, 2026-11-04): leave room for the completed shock module on this same geometry.

**Location caveat:** where the pulse module finally goes is **NOT decided**. `docs/BOTTOM-BAY.md` l.95–97 puts it in the top unit; `hardware/rook/cad/assembly/node_v1.py` l.2 says side pods. Do not treat either as final. The **pod bay is the working assumption** under Cody’s Nov 4 stance.

## What the D8 pod underside actually is

Measured on `stl/pod_L_base.stl` (print frame, cavity UP, bed = z=0):

| Region | Shape | Notes |
| --- | --- | --- |
| Skirt / channel floor | **Flat** | Large bed face ≈ 46.5 × 67 mm at z=0 (strap channel 46.45 × 3.4 + clamp lands) |
| Clamp pockets | **Flat steps** | Recessed in the skirt, still planar |
| Skirt outer walls | **Curved in section** | Quarter-ellipse flare pod-width → strap-width over ~18 mm vertical — **not** a neck-radius curve |
| Body outline above skirt | Contoured plan | Mid 68 / tip 66 / strap-end flare 76; R3 corners |
| `fairing_pod_strap_*` | Wedge loft | Blends pod → strap; plan/height ramp — **not** R≈220 neck saddle |

So Cody’s “flat underside” estimate matches the **print bed face** (skirt+channel). The only curves today are the skirt flare walls and the strap fairing — neither is sized to the neck.

Pod centre is 126 mm along-strap from crest; pod length 97 mm. Cody’s quoted local R at that station ≈ 208 / 218 / 221 mm for 75 / 107 / 130 cm (see `gap_calc.py`).

## Gap under a flat 97 mm chord

Independent calc (`review/gap_calc.py`), using Cody’s quoted local radii (authoritative — the raw ellipse@29.5° does not reproduce 208/218/221 without a measured neck model):

| Circumference | Quoted R | Flat mid-gap | R220 fill | Residual |
| --- | ---: | ---: | ---: | ---: |
| 75 cm | 208 mm | 5.73 mm | 5.41 mm | **0.32 mm** |
| 107 cm | 218 mm | 5.46 mm | 5.41 mm | **0.05 mm** |
| 130 cm | 221 mm | 5.39 mm | 5.41 mm | **0.03 mm** |

Matches Cody’s ~5–6 mm flat gap. **Ask: verify the 25×42 cm ellipse / those radii against any real neck measurements. Do not invent measurements.**

## Options (one design, 75–130 cm)

| | (1) Rigid curved saddle/pad | (2) Flexible TPU contact pad | (3) Hinge/slide at 4×M3 cap joint |
| --- | --- | --- | --- |
| **Idea** | Separate part/pod: flat → pod, concave R≈220 → neck | Soft pad takes residual + animal variation | Let the rigid pod rock to average contact |
| **Part count** | **+1 saddle / pod** (+ service lid + wire blank plug) | +1 TPU pad / pod (+ hard carrier or overmold) | 0 new bodies; more fasteners/bushings at joint |
| **Height above strap** | **0** if saddle lives in the ~5–6 mm underside gap | **0** if pad ≤ gap; thicker foam grows inward only | **0** above strap; joint stack may grow along strap |
| **Height toward neck** | Fills ~5.4 mm (R220 sagitta) | Same budget; compliance in the pad | None by itself — still needs a pad/electrodes |
| **Print** | **ASA**, flat pod-face **on bed**, concave neck-face **up** with light bowl supports (preferred). Side-print also possible but puts layer lines on the seal face. Curved face never on the bed. | TPU on flat bed (pad flat or lightly crowned); ASA carrier if needed | Existing ASA parts; no new curved print |
| **Pros** | Predictable geometry; one hard interface for bay/electrodes; fits all three sizes within ~0.4 mm | Best animal comfort / hair / mud forgiveness | Keeps underside simple |
| **Cons** | Rigid curve ≠ every neck; **must not** be the only electrode contact | Extra material/process; sealing harder | Caps joint stiffness/IP; doesn’t create electrode land |

### Recommendation (confirmed)

**(1) separate rigid saddle per pod**, with Part B’s sealed blank bay and **reserved electrode compliance** (spring or elastomer-backed studs — unpopulated). Evidence:

- Gap math shows R220 leaves ≤0.4 mm residual across 75–130 cm — good enough for a hard locator.
- Flat bed face already exists on the pod — saddle mates flat-to-flat without redesigning the print bed rule.
- Hinge/slide (3) does not create electrode lands or a module bay.
- TPU (2) remains available later as a **skin cover** over the saddle electrodes; it is not required to define the bay.

**Print method pick:** flat pod-mating face on the bed, concave R220 up, light supports in the bowl. Why: mating/seal face gets bed accuracy; curve is never on the bed; supports only touch non-critical concave skin. **Reject upside-down-with-lid** (puts the curve on the bed — violates the bed rule). **Reject side-print as default** (gasket/land would be vertical layers). Same write-up: `review/d8_fit_coupon_notes.md`.

## Electrode contact — hinge vs compliant (from residual vs R 208–221)

Measured residual after R220 saddle: **≤0.32 mm** (75 cm) / ~0.05 mm (107/130).

| Need | Verdict |
| --- | --- |
| **Compliant / floating electrode contact** | **YES — required** when fitted (spring or elastomer). Rigid curve alone is not skin contact. |
| **Hinge at the 4×M3 joint** | **NOT required** for ≤0.32 mm residual. Overkill; revisit only if real-neck data shows a much larger mismatch. |

A rigid R220 saddle matches **one** ideal ellipse — the 25×42 cm model is **not** measured cattle. Bay reserves travel / compliance (PLACEHOLDER). Still unpopulated when bay is blank.

## Open measurement ask

**Please check the 25×42 cm ellipse (and the 208/218/221 mm local radii) against any real neck measurements on hand. Do not invent measurements.** Until then, treat the ellipse as a sizing model only.
