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
| Colourway (proposed) | Light-gray shells | Cap/pod/CW/fairings | **PENDING op-brand review** — not locked; charcoal+orange accents stay |

## Colourway proposal (pending op-brand)

Light-gray shell colourway was floated in the durability / field-soil review (hides dust better than charcoal in some pastures). **Not approved.** Until op-brand signs off, print study parts in charcoal ASA/PETG with orange `#FF6A2B` service accents. Do not quote light-gray as the production colour.

## Panel (P124) — KEPT

**Decision:** Voltaic P124 **KEPT** on collar #1 — Cody, **2026-11-03**. Cap stays **76×160** (panel-included). Pocket retained. Metal/antenna **15 mm keep-clear** retained in CAD. Do not slim the cap for brand 1.3× strap on collar #1.

## RF keepout

- GNSS: sky-facing, **1–3 mm plastic** above patch, **no metal** in the cover stack. Recess opens into cavity from z=0 (export: openings face +Z with outer face on bed).
- Crest antennas opposite neck; cells in pods, steel in CW — both ≥**15 mm** from crest / LoRa.
- Clamp bars (channel section) under saddle at \|y\|≤28.5 — LoRa at y≈64 → clearance ≫15 mm.
- No CF filament in cap lid / antenna shelves. PA-CF only on saddle/clamps away from RF.

## Clamp print orientation / load path

Flange flat on bed, channel opens +Z. Strap compression along bar length **WITH layers** — never peel across layer lines. Farmer-swappable.

## Settings (starting points for op-maker)

- 0.4 mm nozzle; 0.2 mm layer shells; 0.16 mm label coupon.
- ASA: enclosure, brim 5–8 mm, dry filament.
- Walls ≥3; infill 30–40% gyroid on load parts (saddle, **channel clamps**, bases).
- TPU: 0.24–0.28 mm, slow, no cooling blast.
- Gasket groove: 2.0 mm cord; ≥2 mm inner land.
