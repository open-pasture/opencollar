# Housing height options (for Cody)

Review shell today (**D7r12**) with **unchanged print STLs**:

| Region | Height above strap outer | Set by | vs D4 (cap 27.6 / pod 17.5) |
| --- | ---: | --- | --- |
| Cap | **48.2 mm** | `cap_lid` panel land world z=41.4 (+1.5 skin); strap outer z0≈−5.35 | **1.75×** — cannot reach 1.4× (≈39 mm) without lowering the land |
| Pod | **25.0 mm** | Review silhouette target ≈1.4× D4; print lids hidden under shell. Local stack base 22.2 + lid 4.2 = 26.4 still in STLs | **1.43×** |

## Assumptions

| Item | Value | Source | Notes |
| --- | --- | --- | --- |
| Cell | Adafruit **1781**, Ø**18.4** × **69** mm, ~46 g | `HARDWARE-FIT.md`, `d5_dims.CELL_D/L` | Plan of record: **2×** (one per pod) |
| Capacity / cell | **3500 mAh** · **12.95 Wh** | *Estimated* — Adafruit 1781 public listing | Repo has **no mAh field**; Wh = 3.7 V × Ah |
| Dual pack | **7000 mAh** · **25.9 Wh** | *Estimated* = 2 × above | |
| Cell bay | Ø**19.4** × **76** | `CELL_POCKET_D` 19.2 + `CELL_BAY_ADJUST` 0.2; `CELL_BAY_L` | Horizontal axis-X cradle |
| Pod cavity | **82 × 58 × 19.5**; floor **1.5** | `POD_CAVITY`, `assembly.POD_FLOOR` | Floor already at print min |
| Pod base / lid | base **22.2** + lid **4.2** → stack **26.4** | `assembly.POD_BASE_H`, `POD_LID_T` | |
| Cap stack | base **19** + lid above **12** → **31**; land flat | `cap.py CAP_STACK_H`, `LID_ABOVE` | Mating world ≈29.4; land top ≈41.4 |
| Panel | Voltaic **P124** **113 × 66 × 3.1**, 1.2 W 6 V | `dims.P124_PANEL`, KEPT | Active area **113×66 = 7458 mm²** |
| Panel pocket | **66.6 × 113.6 × 2.3**; min lid-under **2.0** | `PANEL_POCKET`, `PANEL_MIN_LID_UNDER` | |
| Wio pocket | **21.8 × 18.6 × 8** lay-flat | `d5_dims.WIO_POCKET` | |

## Options table

| Option | Cap height (mm) | Pod height (mm) | Battery | Solar area | Print risk |
| --- | ---: | ---: | --- | --- | --- |
| **Current (print STLs frozen)** | **48.2** | **25** (review) / stack 26.4 in STL | 2×1781 ≈ **7000 mAh / 25.9 Wh** *(est.)* | P124 **7458 mm²**, 1.2 W | **Low** — no STL change |
| **(i) Two-cell pod base reduced** | **48.2** *(unchanged — cap-limited)* | **≈24** | Same **7000 mAh / 25.9 Wh** *(est.)* | Same **7458 mm²** | **Medium** — true floor: bay Ø19.4 + floor 1.5 → min `POD_BASE_H` ≈ **20.9** (today 22.2, only ~1.3 mm free). Lid re-pack / groove / skirt re-cut. **Cannot** drop to 18–19 without cutting into the cell. Risk: thin floor, insert-column clash |
| **(ii) Solar panel land lowered** | **≈39** (1.4× D4) | **25** *(or combine with i → ~24)* | Same **7000 mAh / 25.9 Wh** *(est.)* | Same **7458 mm²** if P124 kept; area drops **only** if panel swapped smaller | **High** — need land world z≈**32.2** (drop ~9 mm). Today lid-under panel ≈9.7 (min 2.0) **and** Wio 8 mm + panel pocket 2.3 fight a 39 mm shell. Requires lid+base stack redesign, not a review-skin trick. Re-qualify P124 keep-clear 15 mm |
| **(iii) Single-cell pod** | **48.2** *(cap still limits)* | **≈22–23** | **1×1781 ≈ 3500 mAh / 12.95 Wh** *(est.)* — **half** | Same **7458 mm²** | **Medium–High** — one Ø18.4 bay still needs ~19.4 Z; height win is mostly from dropping the second bay / X swell 68→~48 and thinner lid pack. New cavity/cradle; stereo buzzers? one pod cue-only (alt layout **NOT APPROVED**). Asymmetric mass |

### What sets the floors

| Lever | True minimum |
| --- | --- |
| Cap → 39 mm (1.4× D4) | **Blocked** at panel land z=41.4. Must drop land ~9 mm → redesign lid/base (Wio ≥8 + panel pocket 2.3 + lid-under ≥2). Review shell alone cannot hit 39. |
| Pod → 25 mm review | **Achieved** with lids hidden. Printed dual-cell stack clearing strap without hide still wants ≳26 mm local / ~25+ shell. |
| Pod with (i) | Dual-cell Z floor ≈ **20.9** base → review shell **≈24** above strap *(est. from stack delta)*. |
| Pod with (iii) | Single bay; review shell **≈22–23** *(est.)*; capacity halves. |
| Battery | Dual 1781 is plan of record. Adafruit 353 6600 mAh alt-pod is **not approved**. |
| Solar | P124 KEPT on collar #1 — area fixed unless Cody reopens panel choice. |

*Estimated* rows are marked. Linear dims from repo STLs / `assembly.py` / `d5_dims.py` / `HARDWARE-FIT.md` / `cap.py`.
