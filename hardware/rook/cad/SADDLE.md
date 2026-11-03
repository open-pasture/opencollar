# Slim cap + printed strap saddle (`CAP_STYLE=saddle`)

Replaces the tall gabled underside (v3, 76×160×41.4) with a **flat-floor slim
cap** and a **separate printed strap saddle**. The gable v3 set stays under
`stl/node_v1_cap/` for fit tests; this style exports to `stl/node_v1_cap_saddle/`.

## Why

The gable rises `CHANNEL_W/2+0.3` (~23.5 mm) so the channel prints support-free.
That forces `CAP_FLOOR_Z ≈ 28.4` and a ~41.4 mm base (~156 g PLA on print #3).
Moving the channel into a separate saddle lets the sealed cap sit on a ~6 mm
floor + 13 mm cavity (**19 mm** base).

## Select in CAD

```sh
cd hardware/rook/cad
OC_CAP_STYLE=saddle ./build.sh node_v1 -- cap saddle
# or:  ./build.sh node_v1 -- cap --saddle
```

Default / `CAP_STYLE=gable` rebuilds `stl/node_v1_cap/` only (leave it alone
unless you intend to regenerate v3).

## Dimensions (this revision)

| Part | Size (mm) | Notes |
| --- | --- | --- |
| Cap base (slim) | **76 × 160 × 19** (+1.5 mm locating pins below z=0 → bbox 20.5) | Flat underside; no gable; no spine V |
| Cap lid | 76 × 160 × 7 | Unchanged (P124 pocket, inserts) |
| Strap saddle | **76 × 80 × 5.9** | Roof 2.5 + channel 3.4 |
| Clamp bar | 10 × 70 × 4 | Shared; positions (±20, ±28.5) unchanged |

Footprint stays **76×160** so the owned P124 (pocket 66.6×113.6, `PANEL_Y=+11`)
and 25 mm GPS patch still fit. `CAP_WALL` stays **5.0** (thinning to 4.0
deferred — seal + drop impact).

### Electronics / seal checks

- Cavity height **13 mm** kept (bq24074 assumed 11 mm; GPS patch 6 mm on lid).
- O-ring groove, lid screws (bonded washers), 8 insert columns, potted Ø6 cable
  entries unchanged in plan.
- Clamp inserts: Ø4.0 × 4.0 mm seat (flat bottom at z=4.0) with **2.0 mm**
  keep-out under the 6 mm floor (blind to the sealed volume). Do not deepen
  without raising the floor.
- Lid insert vs panel-pocket keep-out unchanged (~0.8 mm).

## Stack-up

From strap bottom to lid top (panel proud ignored):

```
strap protrusion below rails     0.6   (= STRAP_T − CHANNEL_D)
+ saddle height                  5.9   (roof 2.5 + channel 3.4)
+ slim cap base                 19.0
+ lid                            7.0
────────────────────────────────────
=                               32.5 mm   (gable v3 was ~48.4)
```

### Clamp screws (through bar → saddle → cap insert)

```
clamp bar          4.0
+ saddle           5.9
+ insert engage    4.0
=                 13.9 mm  →  use M3×16 button head
```

(Gable v3 used M3×8 with the bar flush on the underside.)

### Lid screws (through base columns → lid insert)

```
base above seat   14.0   (19 − ~5 seat)
+ insert engage    4.0
=                 18.0 mm  →  use M3×20 button head + sealing washer
```

(Gable v3 used M3×40 through the 41.4 mm base.)

## Saddle print

- **Orientation:** roof-down (flat roof on the bed), rails up.
- **Supports:** none. Channel lead-ins and spine V are ≥45° flanks.
- **Spine:** V relief through the rails only; roof stays intact under the cap.
- **Locating:** 4 pins on the cap underside into holes in the saddle roof
  (pins print on the top of a face-down base). Clamp screws also register XY.
- **Seal:** saddle is outside the O-ring; no gasket required. Optional thin
  TPU/EPDM in the roof picture-frame groove to keep grit out of the mate plane.
- **ASA:** brim on both the slim base and the saddle; closed chamber, bed
  ~90–100 °C. Large flat parts warp — keep the door closed; do not raise speeds.

## Mass (solid PA12 from `report.json`, this build)

| Body | Volume | Solid mass |
| --- | --- | --- |
| Slim base | 100.3 cm³ | ~101 g |
| Lid | 73.7 cm³ | ~74 g |
| Saddle | 21.2 cm³ | ~21 g |
| Clamp bar (×1) | 2.5 cm³ | ~2.5 g |

Gable v3 print #3 was **~156 g filament** for the tall base alone (PLA fast-fit).
Slim base solid ~101 g PA12; real ASA at 40 % infill prints lighter. Net printed
cap set still carries the lid (~74 g solid) + saddle (~21 g) + 2 bars — the big
win is deleting the gable/spine bulk and dropping stack height ~16 mm.

## Deferred

- `CAP_WALL` 5 → 4 mm (evaluate seal/drop).
- Smaller footprint (needs calipers proof vs P124 + patch).
- Floor 6 → ~3–4 mm with local underside bosses for inserts.
- Nest lip (tried; full-width recess left knife edges — revisit a narrower land).
- Core-out of solid floor between bosses (THROUGHPUT.md lever).
- Assembly script / mass budget not yet switched to `CAP_STYLE=saddle`.

## Assumed (still need calipers)

Strap thickness 4.0 mm; bq24074 height 11 mm; GPS patch height 6 mm; P124
outline from drawing.
