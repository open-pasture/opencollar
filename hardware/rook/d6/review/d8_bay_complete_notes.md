# D8 complete-version bay — notes (addenda 2–5)

**Draft only. No print. No merge.**

Pilot = production (Cody, 2026-11-04): each pod bay must hold the **complete** version even when only some components are populated.

## Location caveat (not decided)

**Where the pulse module finally goes is NOT decided.**

- Cody’s standing rule (Nov 4): each pod gets a spot → **pod bay is the working assumption** under that stance.
- `docs/BOTTOM-BAY.md` **l.95–97** (“Electric pulse: top unit, not the bay”) puts the pulse on an add-on board **inside the top unit**, electrodes under the top unit.
- `hardware/rook/cad/assembly/node_v1.py` **l.2** places “a pod low on each side … electrodes on the skin”.

**Do not treat either document as final.** The pod bay modelled here is a **working assumption** under Cody’s Nov 4 stance only. Interface draft: PR #30 `docs/SHOCK-MODULE-INTERFACE.md` (do not edit from this work).

## op-architect record O — reserved bay features (not populated)

Each pod’s reserved bay includes these as **reserved features, not populated parts**:

| Feature | CAD | Notes |
| --- | --- | --- |
| Connector position | `CONNECTOR_KEEP_OUT` pocket | Sense/ID so unfitted reads not-fitted |
| Wire path with strain relief | `wire_strain` + `wire_run` | Pod-to-cap harness path |
| Sealed pass-through | `wire_up` + `wire_gland` (+ blank `pod_*_wire_plug`) | Bay ↔ cell cavity via pod gland @ Y=−28 |
| Service lid | `pod_*_bay_cover` | Former blank cover → service lid; **gasket seat + screws**; opens bay **without** opening the cell cavity |
| **Electrode studs** | Ø6 bosses @ 25 mm | **Kept in the design** (record O); tips sealed when unfitted; not populated conductive parts |

## Skin contact — hinge / flexible pod? (plain answer)

Measured residual after the R220 saddle vs Cody’s R 208 / 218 / 221 mm: **≤ 0.32 mm** (75 cm), ~0.05 mm (107 cm), ~0.03 mm (130 cm).

| Option | Needed? |
| --- | --- |
| Compliant / floating electrode contact (spring or elastomer) | **YES** — required when fitted. Rigid saddle alone is not skin contact. |
| Hinged or flexible pod (hinge at 4×M3) | **NO** — not required for ≤0.32 mm residual. Overkill; revisit only if real-neck data shows a much larger mismatch. |

## Placeholders — not a spec

No shock module, driver board, or electrode has been chosen. In `pod_saddle.py` every `MODULE_*` / `DRIVER_*` / `WIRE_*` / `ELECTRODE_*` value is labelled **`placeholder, not a spec`**. Envelopes are parametric with generous XYZ margins so firmware can revise without a redesign.

| Keep-out | Placeholder size | Margin |
| --- | --- | --- |
| Electrode module | 40 × 25 × 8 mm | +3 XY / +2 Z |
| Driver board | 35 × 22 × 6 mm | +3 XY / +2 Z |
| Wire channel | Ø8 mm, ≥**8** conductors | spare over ~4–6 signals/pod |
| Electrodes | Ø6 @ 25 mm (+ stud bosses) | reserved geometry; sealed tips unfitted |

Signals (not a pinout): enable, fault, current sense, module-detect, ground, HV rail → size for **≥8** conductors.

## op-firmware addendum (point-by-point)

1. **Placeholders kept + labelled.** Module 40×25×8 mm; two Ø6 electrodes 25 mm apart. Every param and the notes say **`placeholder, not a spec`**. Nothing chosen.
2. **Adjustable envelope + separate driver keep-out.** `MODULE_MARGIN_*` / `DRIVER_MARGIN_*` on all three axes; `_bay_envelope()` / `_driver_envelope()` drive the cuts. Driver has its own bay (+Y toward cap) and shares the sealed wire path (strain relief + pass-through + plug).
3. **Wires — pod-to-cap channel, ≥8 conductors, placeholder.** Count/gauge unknown. Firmware needs ~4–6 signals/pod — **not a final pinout**. Channel + sealed pass-through sized for **≥8** and flagged PLACEHOLDER.
4. **Housing support (reserved features, not designs).** Connector sense/ID; reachable hardware kill via service lid without opening the cell cavity.
5. **Welfare TBD — easy to revise.** `SEAL_RULES_TBD` / `ISOLATION_CLEARANCE_TBD_MM` / `VENT_RULES_TBD` hooks only.

## Unfitted bay (what is actually there)

**Only:**

- service lid (`pod_*_bay_cover`) with gasket + screws — opens bay **without** opening the cell cavity  
- connector position with **sense/ID** so unfitted reads not-fitted  
- wire path with strain relief + sealed pass-through  
- blank **wire plug** (`pod_*_wire_plug`) sealing the pass-through  
- **electrode stud bosses** (kept in design, tips sealed — not populated)

**No** populated electrodes, **no** pulse circuit when unfitted.

### op-architect vs op-strategy (flag)

- op-architect (record O): **keep electrode studs in the design.**  
- op-strategy: unfitted bay holds no electrodes / no open conductive path.  
- **This CAD:** stud bosses kept; tips sealed when unfitted; open/populated studs only when fitted. **op-strategy to confirm** against sealed-stud vs fully-blank-land preference.

Reserved (not designed): hardware kill pocket. Seal / isolation / vent rules TBD from welfare reviewer — envelopes stay easy to revise.

## Height vs 25 mm pod lid-top

| Quantity | Value |
| --- | ---: |
| Review lid-top above strap (`REVIEW_POD_ROOF_MM`) | **25.0 mm** |
| Still holds with saddle + bay + service lid? | **Yes** |
| Height above strap from saddle/bay | **0 mm** |
| Resulting saddle/pod underside stack (`total_h`) | **13.7 mm** (toward neck) |
| Toward neck (R220 sagitta / gap fill) | **~5.4 mm** |
| Extra beyond sagitta (MODULE+DRIVER margins) | **~6.3 mm toward neck** |

**25 mm lid-top still holds.** Extra depth grows **toward the neck only**. Cell cavity 82×58×19.5 unchanged; solar + 15 mm keep-clear unchanged.

## Design guardrail (op-strategy / Halter look-alike)

Do **not** move toward: narrow low bridge, soft rounded blending, raised ribbed bridge top, vent slots at the pod–bridge joint, glass-look flat pod tops. **Keep** cap dominant and the faceted, segmented look: blind groove stays a **distinct step**, no soft blend; plan corners stay ≤ **R3**.

## Ellipse measurement ask

Check the 25×42 cm ellipse and R 208/218/221 mm against any real neck measurements on hand. **Do not invent measurements.**
