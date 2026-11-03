# D5 materials

| Class | Material | Parts | Notes |
| --- | --- | --- | --- |
| Shells | **ASA** (preferred outdoor) or **PETG** | Cap/pod/CW bases+lids, saddle, fairings, keeper, buckle | ASA needs enclosure; PETG = reproducible off Bambu |
| Seals / soft | **TPU** 85–95A | `usbc_cap`, button membranes, optional gasket cord | Farmer-swappable |
| Mesh | PETG or TPU | `buzz_mesh` ×2 | Press into port counterbore |
| Non-RF structure | ASA/PETG or **PA-CF** | Saddle, clamp bars **only if** ≥12 mm from antennas | PA-CF OK away from RF |
| **Forbidden near RF** | Carbon fiber, metal foil, large metal plates | Cap crest, GNSS cover, LTE/LoRa runs | Keep inserts/screws/CW/cells 10–15 mm from antennas |
| Verify | **PLA** | `fit_coupon`, `label_coupon` first | Do not field PLA shells |
| Cosmetic | ASA charcoal `#26282B` / orange `#FF6A2B` | Plugs, latch | Orange = service |

## RF keepout

- GNSS: sky-facing, **1–3 mm plastic** above patch, **no metal** in the cover stack.
- Crest antennas opposite neck; cells live in pods, steel in CW — both ≥ keepout from crest.
- No CF filament in cap lid / antenna shelves.

## Settings (starting points for op-maker)

- 0.4 mm nozzle; 0.2 mm layer shells; 0.16 mm label coupon.
- ASA: enclosure, brim 5–8 mm, dry filament.
- Walls ≥3; infill 30–40% gyroid on load parts (saddle, clamps, bases).
- TPU: 0.24–0.28 mm, slow, no cooling blast.
