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
- The shock-electrode **bay remains required** (PLACEHOLDER module 40×25×8, unpopulated).
- Reserve **travel / compliance** for the electrodes (e.g. spring-loaded or elastomer-backed contact studs) inside the bay — still unpopulated. See `ELECTRODE_COMPLIANCE_TRAVEL` in `pod_saddle.py`.

## (3) Measurement ask

**Please check the 25 × 42 cm ellipse (and the quoted local radii 208 / 218 / 221 mm) against any real neck measurements on hand. Do not invent measurements.** Until then, treat those numbers as a model only.
