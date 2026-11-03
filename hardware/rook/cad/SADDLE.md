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
| Cap base (slim) | **76 × 160 × 19** | Completely flat underside (bed face); blind pin sockets Ø4.35 × 2.0; no gable / spine V |
| Cap lid | 76 × 160 × 7 | Unchanged (P124 pocket, inserts) |
| Strap saddle | **76 × 80 × 5.9** (+1.5 mm pins → bbox **7.4**) | Roof 2.5 + channel 3.4; pins on roof toward cap |
| Clamp bar | 10 × 70 × 4 | Shared; positions (±20, ±28.5) unchanged |

Footprint stays **76×160** so the owned P124 (pocket 66.6×113.6, `PANEL_Y=+11`)
and 25 mm GPS patch still fit. `CAP_WALL` stays **5.0**.

### Electronics / seal checks

- Cavity height **13 mm** kept (bq24074 assumed 11 mm; GPS patch 6 mm on lid).
- O-ring groove, lid screws (bonded washers), 8 insert columns, potted Ø6 cable
  entries unchanged in plan.
- Clamp inserts: Ø4.0 × 4.0 mm seat (flat bottom at z=4.0) with **2.0 mm**
  keep-out under the 6 mm floor (blind to the sealed volume).
- Pin sockets: Ø4.35 × 2.0 mm blind from the underside (keep-out to cavity ≥4 mm).
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

### Boss → screw (one line)

**Lid columns → M3×16**; **clamp inserts → M3×14**; inserts are M3×4 heat-set
(`INSERT_M3` length 4 / hole Ø4.0×6). Detail below; labels on the cap floor.

### Clamp screws (through bar → saddle → cap insert) — round DOWN

Bar rides on the 0.6 mm strap protrusion, so the screw crosses an air gap at
the clamp holes too:

```
clamp bar          4.0
+ saddle           5.9
+ strap gap        0.6
= to insert mouth 10.5 mm

blind pocket depth 4.0   (seat ends at z=4.0; floor/cavity at z=6.0)
max screw          14.5  →  stock M3×14 (do NOT use M3×16)
M3×14 tip into base      14 − 10.5 = 3.5 mm  (inside the 4.0 pocket)
```

M3×16 would put the tip at 5.5–6.1 mm into the base and risk breaking the seal.

### Lid screws (through base columns → lid insert)

CAD seat: Ø8 cbore cylinder ends / cone starts at **z = 4.0** (bonded washer
lands there). Lid insert pocket is **5.0 mm** deep from the mating face
(cylinder from z=−1 height 6); insert length 4.0 mm.

```
through base       15.0   (19.0 − 4.0 seat)

M3×16 tip into lid = 16 − 15 = 1.0 mm past the face → ~3 mm insert grip, ~2 mm pocket spare
M3×18 tip into lid = 18 − 15 = 3.0 mm  → can reach the pocket floor (0–0.5 mm spare) — avoid
M3×20 tip into lid = 20 − 15 = 5.0 mm  → bottoms — do not use
```

Use **M3×16** button head + sealing washer (gable v3 still uses M3×40).

## Print

### Cap base (slim)
- **Orientation:** outside / underside flat on the bed, cavity opening up.
- **Supports:** none. Underside is planar (pin sockets are blind recesses).
- Re-check: no downward-facing overhang steeper than 45° apart from the bed face
  (lid-screw cones are ≥45°; cavity ceiling is horizontal upward when printed
  this way — it is a floor of the cavity from the nozzle’s view only after
  walls rise; tree supports are not required for the self-supporting shell
  once the rim is up — same class as the gable base’s cavity).

### Saddle
- **Orientation (STL as exported):** flank / rail face on the bed, **roof +
  locating pins UP**. Channel opens toward the bed as a pocket (no bridge).
- **Supports:** none. Lead-ins and spine V flanks ≥45°.
- **Locating:** 4 pins on the roof into the cap’s blind sockets. Clamp screws
  also register XY.
- **Gasket:** large roof recess removed (it bridged off the bed). Optional
  thin TPU/EPDM grit gasket can be cut as a separate washer; a narrow groove
  may return in a follow-up.
- **ASA:** brim on base and saddle; closed chamber, bed ~90–100 °C.

## Mass (solid PA12, prior build order-of-magnitude)

| Body | Solid mass (approx.) |
| --- | --- |
| Slim base | ~100 g |
| Lid | ~74 g |
| Saddle | ~21 g |
| Clamp bar (×1) | ~2.5 g |

## Deferred

- `CAP_WALL` 5 → 4 mm; smaller footprint; floor core-out / local bosses.
- Narrow grit-gasket groove on the saddle roof (recess removed for printability).
- Assembly script mass budget for `CAP_STYLE=saddle`.

## Assumed (still need calipers)

Strap thickness 4.0 mm; bq24074 height 11 mm; GPS patch height 6 mm; P124
outline from drawing.
