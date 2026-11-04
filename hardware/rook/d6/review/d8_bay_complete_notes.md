# D8 complete-version bay — notes (addenda 2–5)

**Draft only. No print. No merge.**

Pilot = production (Cody, 2026-11-04): each pod bay must hold the **complete** version even when only some components are populated.

## Location caveat (not decided)

Where the pulse module finally goes is **NOT decided**. Cody’s standing rule says each pod gets a spot; `docs/BOTTOM-BAY.md` (≈l.95–97 / pulse-in-top language) and older CAD (`hardware/rook/cad/assembly/node_v1.py`) disagree. **Do not treat either as final.** The **pod bay is a working assumption** under Cody’s Nov 4 stance. Interface draft: PR #30 `docs/SHOCK-MODULE-INTERFACE.md` (do not edit from this work).

## Placeholders — not a spec

No shock module, driver board, or electrode has been chosen. In `pod_saddle.py` every `MODULE_*` / `DRIVER_*` / `WIRE_*` / `ELECTRODE_*` value is labelled **`placeholder, not a spec`**. Envelopes are parametric with generous XYZ margins so firmware can revise without a redesign.

| Keep-out | Placeholder size | Margin |
| --- | --- | --- |
| Electrode module | 40 × 25 × 8 mm | +3 XY / +2 Z |
| Driver board | 35 × 22 × 6 mm | +3 XY / +2 Z |
| Wire channel | Ø8 mm, ≥**8** conductors | spare over ~4–6 signals/pod |
| Electrodes | Ø6 @ 25 mm | reserved geometry only when unfitted |

Signals (not a pinout): enable, fault, current sense, module-detect, ground, HV rail → size for **≥8** conductors.

## Unfitted bay (what is actually there)

**Only:**

- service lid (`pod_*_bay_cover`) with gasket + screws — opens bay **without** opening the cell cavity  
- connector position with **sense/ID** so unfitted reads not-fitted  
- wire path with strain relief + sealed pass-through  
- blank **wire plug** (`pod_*_wire_plug`) sealing the pass-through  
- blank/flat skin-contact lands (no open electrode holes)

**No** fitted electrodes, **no** pulse circuit when unfitted.

### op-architect vs op-strategy (flag)

- op-architect: keep electrode studs in the design.  
- op-strategy: unfitted bay holds no electrodes.  
- **This CAD:** reserved stud keep-outs + **blank sealed lands** when unfitted; open studs only when fitted. **op-strategy to resolve.**

Reserved (not designed): hardware kill pocket (cuts driver rail independent of firmware, reachable via service lid). Seal / isolation / vent rules TBD from welfare reviewer — envelopes stay easy to revise.

## Height vs 25 mm pod lid-top

| Quantity | Value |
| --- | ---: |
| Review lid-top above strap (`REVIEW_POD_ROOF_MM`) | **25.0 mm** |
| Still holds with saddle + bay + service lid? | **Yes** |
| Height above strap from saddle/bay | **0 mm** |
| Resulting saddle/pod underside stack (`total_h`) | **13.7 mm** (toward neck) |
| Toward neck (R220 sagitta / gap fill) | **~5.4 mm** |
| Extra beyond sagitta (MODULE+DRIVER margins) | **~6.3 mm toward neck** |

**25 mm lid-top still holds.** Driver: saddle + module/driver bay stack lives on the neck side of the strap. Extra depth from PLACEHOLDER envelopes grows **toward the neck only**, not above the strap. Print pod stack above strap unchanged; cell cavity 82×58×19.5 unchanged; solar + 15 mm keep-clear unchanged.

## Hinge vs compliant floating contact (from gap R 208–221)

Residual after R220 saddle vs Cody’s radii: **≤ 0.32 mm** (75 cm) and ~0.05 mm at 107/130 cm.

- **Compliant / floating electrode contact: YES — required** when fitted (spring-loaded or elastomer-backed). Rigid curve alone is not skin contact; ellipse is a model, not measured cattle.  
- **Hinge at the 4×M3 joint: NOT required** for this residual. A hinge is overkill for ≤0.3 mm. Revisit only if real neck measurements show a much larger mismatch.

## Design guardrail (op-strategy / Halter look-alike)

Do **not** move toward: narrow low bridge, soft rounded blending, raised ribbed bridge top, vent slots at the pod–bridge joint, glass-look flat pod tops. **Keep** cap dominant and the faceted, segmented look: blind groove stays a **distinct step**, no soft blend; pod/saddle changes must not flatten pod tops or add vents/ribs on the bridge; plan corners stay ≤ **R3**.

## Ellipse measurement ask

Check the 25×42 cm ellipse and R 208/218/221 mm against any real neck measurements on hand. **Do not invent measurements.**
