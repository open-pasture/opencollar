# D5 production notes

## Envelope (locked)

| Module | Footprint / height | Notes |
| --- | --- | --- |
| Cap | 76 × 160; base 19 + lid 6.5 | P124-sized; brand 1.3× strap conflict flagged |
| Pod L/R | 92 × 68; base 24.5 + lid 6 | Full cavity (taller than cap) — intentional |
| CW | 88 × 74 × 30 + lid 6 | Steel pack; **no electronics / antennas** |
| Saddle | 76 × 96 × ~5.9 | Wider than look-study to kill overhang rock |
| Fairings | 28 mm run, R7 | Separate from lids; print slope as WALL |
| Seam | waist frac ~0.745; reveal 0.5 mm | Shared family; ~0.75 datum |
| Plan / crown | R7 / soft R2.5 look | Print as clean flat + soft plan (no dust ledge) |
| Strap | W 44.45 (V); T **4.0 U** | VERIFY WITH CALIPERS |

Orange = farmer service: latch `#FF6A2B` + 3 end screws on cap. Cell swap = M3 driver only (pod lids).

## Pocket layout (op-firmware)

Sources: headline dims from enclosure-component-spec (V/U). Spec path on shared box may be `/workspace/enclosure-component-spec.md`.

### Cap (electronics)

- **Rook Connect Kit** 55.88 × 20.32 × 1.0 PCB → pocket **56.7 × 21.1 × 7.2** (≈17 w/ socketed headers). USB-C +3.26 on short end (−Y). JST +1.95 underside recess. Holes Ø1.4 inset 1.27. LTE/GNSS U.FL at antenna end; nano-SIM on board.
- **bq24074** (Adafruit 4755) → **38.9 × 33.8 × 12**. Holes Ø2.5 @ 2.54 inset. **Do not pot solid** — leave service air gap.
- **Wio-SX1262** → **21.8 × 18.6 × 23** (height U 21–23) + **20 mm** U.FL wire bend / strain relief toward crest.
- **USB-C** charge port + TPU gasket cap (`usbc_cap.stl`).
- **Light pipes** Ø2.5 over kit LEDs; **press-through membranes** over buttons.
- **Antennas on crest (+Y)**, away from neck and cells:
  - GNSS ceramic 25 × 25 × 4 under **1–3 mm** plastic, **no metal above**.
  - LTE flex ~44 × 10 shelf under lid.
  - 915 MHz LoRa U.FL or SMA on crest.
  - Metal inserts / screws / steel CW / cells **10–15 mm** away (CAD keepout **12 mm**).

### Pods

- Protected **18650** (Adafruit 1781) Ø18.4 × 69 → bay Ø**19.2 + 2 adjust** × **70 + 3 mm/end**. Adafruit **353 not approved**. LP503562 flat LiPo U — use adjust clearance, not a second boolean bay.
- **Buzzer** (BOB-24474) 25.4² → **26.2²** pocket; open sound port + press-in **buzz_mesh** disc.

### Counterweight

- Tub stays **free of electronics**. Steel only.

### Starling

- XIAO nRF52840 + Wio stack → same XY **21.8 × 18.6**; **small cells only**. Separate CAD TBD.

## Clearance policy

`BOARD_CLEAR = 0.4` mm per side. Fit coupon sweeps **0.2 / 0.4 / 0.6** for kit before locking production clearances.

## Load paths & print orientation

| Part | Bed | Load WITH layers |
| --- | --- | --- |
| Cap / pod / CW bases | cavity up (underside on bed) | Clamp → inserts; walls take drop |
| Lids | mating face down | Screws into base inserts |
| Saddle | flank on bed; channel = pocket | Strap tension → rails → clamp → cap |
| Fairings | long axis on bed | Visible slope is a WALL |
| Clamp bars | flat | Compression along bar |

Never print so drop/tension peels layers apart across the bed plane.

## Materials (summary)

See `MATERIALS.md`. Shells ASA or PETG; seals/caps TPU; **no CF or metal near RF**; PA-CF only on non-RF parts (saddle/clamps away from antennas).

## Plates / time (honest)

From `plates/plates.json` (Orca CLI **not** available — op-maker slices):

| Bed | Verify PLA plates / h | Field ASA/PETG plates / h |
| --- | --- | --- |
| P2S 256 | 5 / ~25.5 h | 5 / ~31.5 h |
| 220 Ender-class | 9 / ~28.5 h | 9 / ~36 h |

Spares plate ~1.8 h (see `SPARES.md`). Starling ~3 P2S / ~4×220 once CAD exists.

## Farmer repair

- Orange plugs = open/replace lids.
- Cell swap: M3 driver, pod lid only.
- USB-C gasket cap, clamp bars, latch, plugs, mesh discs, O-ring blank = spares plate.
- Target: common spares printable **&lt; 2 h**.

## Brand conditions

- Fairings 25–30 mm, continuous R7 lid plane.
- Seam 0.5 mm reveal / ~0.75 waist datum.
- Orange latch + 3 farmer end screws.
- Cap ≤ ~1.3× strap **conflict** with 76 mm / P124 — documented, not silently broken.
- ROOK-001 label + label coupon.
- No visible supports on show faces (orientations above).
- P124: **OPEN** decision.
