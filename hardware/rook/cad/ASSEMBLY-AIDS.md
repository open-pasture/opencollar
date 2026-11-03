# Assembly aids (REV AID1)

Print-time locators and labels on the slim-cap / pod bases plate so Cody can
assemble without a drawing. Budget: ~15 g PLA and ~30 min extra on the plate.

Build:

```sh
cd hardware/rook/cad
OC_CAP_STYLE=saddle ./build.sh node_v1 -- cap saddle
./build.sh node_v1 -- pod
./build.sh node_v1 -- coupon
```

STLs: `stl/node_v1_cap_saddle/`, `stl/node_v1_pod/` (includes `node_pod_base_R`),
`stl/test_coupon/` (`test_coupon.stl`, `scale_bar_100.stl`).

## Cap base (slim)

| Aid | Use |
| --- | --- |
| Inside-floor `CAP BASE`, `REV AID1` (4.5 × 0.7) | Identify the part during assembly |
| `M3x14 CLAMP`, `M3x16 LID`, `M3x4 INSERT` | Grab the right fasteners without the BOM |
| `PIN` | Match the saddle roof pins |
| Ø1 × 0.4 dimples on the bed face by lid columns | Visual / finger registration when starting inserts |

Bed face stays planar (dimples only — glyph cuts into z=0 left STL slivers).
Print outside-face down, cavity up, no supports.

## Pod base (L and R)

| Aid | Use |
| --- | --- |
| Cell cradle (2× R9.4 arc ribs, 2.5 mm) | Drop the Ø18.4 1781 in (no roll); leads toward the crest cable entry |
| Buzzer L-corners (1.2 × 1.5, +0.3 clear; +X/+Y trimmed) | Seat the 25.4 Qwiic board; ≥0.5 mm clear of column (37,27) |
| Floor cable grooves (3 × 1.2) | Route cell and buzzer leads to the Ø6 crest entry before potting |
| Floor box-stamps at cell / buzzer / stud / port | Tactile cues without font slivers |
| Outer −Y wall: `POD BASE`, `L`/`R`, rev, port, `BUZZER`, `M3x25 LID`, `M3x4 INSERT` | Readable callouts (bed face left flat) |
| Column dimples | Start heat-set inserts on the right bosses |

`node_pod_base.stl` is the left pod; `node_pod_base_R.stl` is a dedicated right
(asymmetric features + label). You can still mirror L if preferred.

## Test coupon + scale bar

| Feature | Use |
| --- | --- |
| Insert Ø3.9 / 4.0 / 4.1 | Pick the iron-fit hole for Adafruit 4255 on this filament |
| Blind Ø2.8 tap + Ø3.2 clear at 4 / 5 / 6 mm | Confirm tip clearance vs pocket depth |
| Pin sockets Ø4.2 / 4.35 / 4.5 × 2 mm | Match saddle pin fit |
| Sample pins Ø4.0 × 1.5 on plinth | Press into the winning socket |
| 20 mm bridge (2 mm roof) | Spot bridging before the real saddle |
| `scale_bar_100.stl` | 100 mm bar with a 20 mm step — measure shrink |

## Lid screw (slim cap)

CAD seat z=4.0, through base 15.0, lid pocket 5.0. **M3×16** — about 3 mm
insert engagement with ~2 mm spare in the pocket. M3×18 can bottom on the
pocket floor. Clamp stays **M3×14**. See `SADDLE.md`.

## Mass (solid PLA @ 1.24 g/cm³)

| Feature | Approx |
| --- | --- |
| Pod cell cradle (2 ribs) | +0.21 g each base |
| Pod buzzer L-locators ×4 | +0.07 g each base |
| Pod cable grooves | −0.5 g each base (cut) |
| Cap / pod engraving + dimples | −0.05 g each base |
| Net on bases plate (cap + 2 pods) | ≈ 0 g (cuts ≈ adds) |
| `test_coupon.stl` | ~9.4 g solid (~5–7 g @ typical infill) |
| `scale_bar_100.stl` | ~2.2 g solid |

Aids stay inside the ~15 g / ~30 min plate budget; the coupon is an optional
side print for fit learning.

## Intentional omissions

- Bed-face glyph engraving: removed (remeshed font into z=0 left multi-face
  STL slivers). IDs live on the inside floor (cap) or outer −Y wall (pod).
- Raised nest lip on saddle: still deferred (knife edges in earlier try).
- Pod electrode polarity beyond `STUD`: studs are unwired on unit #1.
- Coupon hole-size callouts are bar stamps (not font glyphs) so the top face
  stays watertight; sizes are documented here and in the build notes.
- Cap lid-screw length engraved as `M3x16` (not M3×18): tip spare in the 5 mm
  lid pocket; see § Lid screw above.
