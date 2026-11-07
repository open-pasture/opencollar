# D8 saddle — neck standoff vs a6b2118 flat underside

**Draft only. No print. No merge. No geometry change yet — pick (a) or (b).**

Baseline: printable D8 @ `a6b2118` (flat pod underside, no neck saddle).  
Current saddle (PR #28): R220 concave, `total_h` = **13.7 mm**, sagitta **5.41 mm**, `extra_toward_neck` = **6.29 mm**.

## Strap plane vs saddle

| Layer (toward neck ↓) | Where it sits |
| --- | --- |
| Pod lid-top | Review: **25 mm above strap outer** (unchanged) |
| Strap plane / channel | In the pod skirt, **above** the saddle — same as a6b2118 |
| Pod skirt bed (flat underside) | Mates the saddle’s **flat** face |
| Saddle body | Between pod bed and neck; thickness **t(y)** below |
| Neck | Against saddle concave (R220) |

The saddle adds **0 mm above the strap**. It only changes how far the whole pod stack (strap + lid) sits off the **neck**.

Pod flat → lid-top stack is the same in both designs (~**31 mm**: ≈6 mm bed→strap-outer + 25 mm strap-outer→lid). Deltas below are therefore also the change in lid-top↔neck standoff.

## Saddle thickness t(y) (pod flat → neck face)

Concave R220 cut into a 13.7 mm blank → **thicker at the ends than at the centre**:

| Station | y from pod centre | t(y) |
| --- | ---: | ---: |
| Centre | 0 | **8.29 mm** (= `total_h − sagitta` = 2 + 6.29 bay extra) |
| Ends | ±48.5 mm | **13.70 mm** (= full `total_h` rim) |

**What drives it:** bay depth (`MODULE_H+margins` → stack need **13.7 mm**) was added as **uniform extra under the whole saddle**, then the R220 bowl was cut. Ends keep the full blank; centre is thinned only by the bowl sagitta.

## Neck → lid-top standoff (mm)

Chord model (Cody): flat 97 mm underside touches near the ends; mid-gap = sagitta of neck R.  
Saddle model: underside↔neck ≈ solid **t(y)** when the concave seats on the neck (R≈220 residual ≤0.32 mm at centre — ignored in the table as ≪ end lift).

| Neck R | Circ. | Station | **Flat a6b2118** neck→lid | **Saddle as-built** neck→lid | **Δ (saddle − flat)** — how much farther off the neck |
| ---: | --- | --- | ---: | ---: | ---: |
| 208 | 75 cm | Centre | 36.73 | 39.29 | **+2.55** |
| 208 | 75 cm | Ends | 31.00 | 44.70 | **+13.70** |
| 218 | 107 cm | Centre | 36.46 | 39.29 | **+2.82** |
| 218 | 107 cm | Ends | 31.00 | 44.70 | **+13.70** |
| 221 | 130 cm | Centre | 36.39 | 39.29 | **+2.90** |
| 221 | 130 cm | Ends | 31.00 | 44.70 | **+13.70** |

### Plain reading

**Yes — the pod rides higher above the animal with the as-built saddle.**

- **Centre:** ~**+2.6 to +2.9 mm** farther off the neck than flat a6b2118 (bay extra under the bowl floor: `t_centre − flat_gap` ≈ 8.29 − 5.4…5.7).  
- **Ends:** **+13.7 mm** farther off the neck (full rim thickness where the flat design had ~0 gap). **End lift is dominated by saddle thickness at the ends**, not by bay depth at the centre.

Strap-relative review height (25 mm lid-top above strap) is unchanged; the animal sees a taller pod because the stack is jacked up by the saddle, especially at the ends.

## Part count (per pod)

| Part | Qty |
| --- | ---: |
| `pod_*_base` | 1 |
| `pod_*_lid` | 1 |
| `pod_*_saddle` | 1 |
| `pod_*_bay_cover` (service lid) | 1 |
| `pod_*_wire_plug` | 1 |
| **Total per pod** | **5** |

(Collar: ×2 pods → +6 bodies vs pre-saddle.)

## Options (no CAD change yet — pick one)

| | **(a) As built** | **(b) Thinner ends / bay at centre or into pod** |
| --- | --- | --- |
| Idea | Keep current 13.7 mm blank + R220 bowl | Thin the saddle at the **ends** (aim end t ≈ sagitta/gap fill ~5–6 mm); keep bay depth only under the **centre** keep-outs, **or** move bay depth **up into the pod base** (cell-cavity side) so the saddle is mostly a thin R220 pad |
| End Δ vs flat | **+13.7 mm** | Target ~**+0–2 mm** at ends (gap-fill only) |
| Centre Δ vs flat | **+2.6–2.9 mm** | Similar or lower if bay moves into pod; if bay stays in saddle centre only, centre may stay ~+3 mm unless pod base absorbs it |
| Strap / 25 mm lid-top | Unchanged | Unchanged (still 0 mm above strap) |
| Parts / pod | **5** | **5** (same list; geometry only) |
| Trade | Simple; bay fully in saddle; ends jack the pod off the neck | Needs redesign: either variable-thickness saddle (bay pocket only mid-span) or pod-base floor/cavity reshuffle; seals/gasket path revisit |
| Risk | Animal sees high end standoff; skin contact at ends poor without compliance | CAD + possibly pod STL change; cavity 82×58×19.5 may move |

**Recommendation pending your pick.** (b) matches the original “fill the ~5 mm gap, grow toward neck only where the bay needs it” intent; (a) is what is in the draft STLs today.
