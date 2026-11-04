# D8 complete-version bay — notes (addenda 2–5)

**Draft only. No print. No merge.**

Pilot = production (Cody, 2026-11-04): each pod bay must hold the **complete** version even when only some components are populated. Shock-module interface: draft PR #30 `docs/SHOCK-MODULE-INTERFACE.md` — **do not edit** from this work.

## Location caveat (not decided)

**Where the pulse module finally goes is NOT decided.**

- Cody’s standing rule (Nov 4): each pod gets a spot → **pod bay is the working assumption** under that stance (placement still pending Cody).
- `docs/BOTTOM-BAY.md` **l.95–97** puts the pulse in the **top unit**.
- `hardware/rook/cad/assembly/node_v1.py` **l.2** places side pods / electrodes on the skin.

**Do not treat either document as final.**

## Design guardrail (op-strategy / op-office Halter comparison)

Do **NOT** move toward these traits (Halter design-patent look-alike):

- a narrow low bridge between dominant pods  
- soft rounded blending  
- a raised ribbed bridge top  
- vent slots at the pod–bridge joint  
- glass-look flat pod tops  

**KEEP** the cap dominant and the faceted, segmented look:

- the **blind groove** at the cap-to-pod joint stays a **distinct step** — no soft blending  
- pod and saddle changes must **not** flatten pod tops or add vents or ribs on the bridge  
- plan corners stay ≤ **R3** (`PLAN_R` / `SADDLE_PLAN_R` = 3) — nothing in the earlier fixes rounds corners beyond that target  

## Unfitted bay — how it looks and seals (op-strategy)

The unfitted bay holds **NO electrodes** and **NO pulse circuit**.

**Only:**

1. **Service lid** (`pod_*_bay_cover`) with gasket seat + screws — opens the bay **without** opening the cell cavity (or a blank plug in the same role)  
2. **Connector position** (sense/ID → unfitted reads not-fitted)  
3. **Wire path with strain relief**  
4. **Sealed pass-through** (+ blank `pod_*_wire_plug` when the harness is not fitted)  
5. **Skin-contact land = blank / flat surface only** (`elec_land_blank*`) — no studs proud of the skin face, no open holes  

**How it seals with nothing fitted:** service lid compresses the gasket around the combined module+driver opening; blank wire plug seats in the sealed pass-through; skin lands are continuous blank/flat faces over sealed internal keep-outs. No electrode openings, no pulse path.

### Flag for op-strategy (architect vs strategy)

| Source | Ask |
| --- | --- |
| op-architect (record O) | Keep electrode studs in the design |
| op-strategy (this addendum) | Unfitted bay holds **no electrodes**; studs/pass-throughs = reserved geometry only, sealed or blank |

**This CAD:** blank/flat skin lands + **internal** sealed stud keep-out (`ELECTRODE_STUD_KEEP_OUT`). No open electrode or pass-through holes in the unfitted state. **op-strategy to resolve** whether internal reserved stud geometry stays or is removed entirely.

## op-architect record O — reserved features (not populated)

| Feature | CAD |
| --- | --- |
| Connector position | `CONNECTOR_KEEP_OUT` |
| Wire path with strain relief | `wire_strain` + `wire_run` |
| Sealed pass-through | `wire_up` + `wire_gland` + blank plug |
| Service lid | `pod_*_bay_cover` (gasket + screws) |
| Electrode studs | reserved **internal** keep-out only when unfitted |

## Skin contact — hinge / flexible pod? (plain answer)

Residual after R220 vs R 208 / 218 / 221 mm: **≤ 0.32 mm** (75 cm).

| Option | Needed? |
| --- | --- |
| Compliant / floating electrode contact | **YES** when fitted |
| Hinged / flexible pod | **NO** for ≤0.32 mm residual |

## Placeholders — not a spec

No shock module, driver board, or electrode has been chosen. Every `MODULE_*` / `DRIVER_*` / `WIRE_*` / `ELECTRODE_*` value is **`placeholder, not a spec`**.

| Keep-out | Placeholder size | Margin |
| --- | --- | --- |
| Electrode module | 40 × 25 × 8 mm | +3 XY / +2 Z |
| Driver board | 35 × 22 × 6 mm | +3 XY / +2 Z |
| Wire channel (pod-to-cap) | Ø8 mm, ≥**8** conductors | spare over ~4–6 signals/pod |
| Electrodes | Ø6 @ 25 mm | reserved internal; blank/flat land unfitted |

## Height vs 25 mm pod lid-top

| Quantity | Value |
| --- | ---: |
| Review lid-top above strap | **25.0 mm** |
| Still holds? | **Yes** |
| Above strap from saddle/bay | **0 mm** |
| Saddle `total_h` | **13.7 mm toward neck** |

## Ellipse measurement ask

Check the 25×42 cm ellipse and R 208/218/221 mm against any real neck measurements on hand. **Do not invent measurements.**
