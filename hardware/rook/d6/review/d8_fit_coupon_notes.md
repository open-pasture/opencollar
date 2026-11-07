# D8 P0 fit coupon — notes (op-strategy)

**Draft only. No print. No merge.** Owner must approve before any print.

Coupon STL: `stl/d8_fit_coupon.stl` · plate: `stl/d8_fit_coupon_plate.json`

## (1) How the curved saddle prints (pick + why)

The coupon’s “saddle footprint” is only a feeler gauge. The **real** `pod_*_saddle` is a separate ASA part.

| Method | Orientation | Pros | Cons |
| --- | --- | --- | --- |
| **A — preferred** | Flat pod-mating face **on the bed**; concave R220 **UP**; **light supports in the bowl** | Mating/seal face gets bed accuracy; curve never lies on the bed; supports only touch non-critical concave skin | Small support scars inside the bowl (sand or leave) |
| B — rejected as default | Side-print (curve as a wall) | Fewer bowl supports | Seal/gasket face = vertical layers (weaker, leakier) |
| C — rejected as default | Upside-down: concave on bed, flat up (“with the lid”) | — | **Violates the bed rule** (nothing curved on the bed); first layers squash the R220; mating face is not on the bed |

**Pick: Method A.** Flat on bed + bowl supports. Do **not** print the curved face on the bed, and do **not** default to upside-down-with-lid.

## (2) Shock bay + compliant electrode contact still required

A rigid R220 saddle matches **one** ideal neck shape. The **25 × 42 cm ellipse is a sizing model, not measured cattle.**

- The design **must not** rely on the rigid saddle alone for electrode skin contact.
- Complete-version bay: electrode **module** keep-out **and** **driver** keep-out (both PLACEHOLDER, not a spec), sealed wire path ≥8 conductors + blank plug, service lid.
- Residual vs R 208–221 after R220: **≤0.32 mm** → **compliant/floating contact YES; hinge NO.**
- Unfitted (op-strategy): **NO electrodes, NO pulse** — service lid, connector, wire path + strain relief, sealed pass-through; skin land = **blank/flat only**. Studs = reserved sealed internal geometry; flag architect-vs-strategy for op-strategy.
- Design guardrail: no Halter-like narrow bridge / soft blend / ribbed bridge / vents / glass tops; blind groove stays a distinct step; corners ≤ **R3**.

## (3) Measurement ask

**Please check the 25 × 42 cm ellipse (and the quoted local radii 208 / 218 / 221 mm) against any real neck measurements on hand. Do not invent measurements.** Until then, treat those numbers as a model only.
