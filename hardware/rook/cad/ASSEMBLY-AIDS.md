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
`stl/test_coupon/` (`test_coupon.stl`, `scale_bar_xyz.stl`).

## Part numbers + orientation

| # | Part | Label face | Print orientation |
| --- | --- | --- | --- |
| #1 | Cap base (slim) | Inside floor | Outside / bed face down, cavity up |
| #2 | Pod base L | Outer −Y wall | Outside face down, cavity up |
| #3 | Pod base R | Outer −Y wall | Outside face down, cavity up |
| #4 | Test coupon | Ladder top | Flat on bed |
| #5 | Scale bar (XYZ) | X-arm top | Flat on bed (Z post up) |

## Board clearances (`dims.py`)

| Board | dims.py size | Locator / rail clear | Notes |
| --- | --- | --- | --- |
| Qwiic Buzzer | 25.4 × 25.4 × 1.6 | **0.3 mm**/side (`BUZZER_CLEAR`); slot = 1.6+0.3 | L-corners outside footprint; ±Y 45° slot rails |
| Adafruit 4755 bq24074 | 38.10 × 33.02 × 1.6 | **0.3 mm**/side (`BQ_CLEAR`) | L-corners + Ø5×1 standoffs at hole pattern; rot=True at (0,52) |
| nRF9151 Connect Kit | 55.88 × 20.32 × 1.0 | Collar `kit_fence` inner = board+**0.3**/side | **Slim node_v1 cap has no kit_fence solid** (ref only at (−6,−6)). Collar fence clearance is 0.3 mm/side from dims. |
| XIAO nRF52840 / Wio-SX1262 | — | — | **Starling-only — skipped** (no Starling part in this repo yet) |

## Boss → screw (slim saddle)

| Boss | Stack | Screw |
| --- | --- | --- |
| Cap lid columns (through base → lid insert) | seat z=4 → through 15 + insert 4 | **M3×16** (~3 mm insert grip; M3×18 can bottom in 5 mm lid pocket) |
| Cap clamp inserts (bar → saddle → blind z=4 pocket) | 4+5.9+0.6=10.5 to mouth + 4 pocket | **M3×14** (M3×16 risks seal breach) |
| Pod lid columns | through pod → lid insert | **M3×25** |
| Heat-set inserts (all) | Adafruit 4255 M3×4 | hole Ø4.0 × 6 deep (`INSERT_M3`) |

Floor/wall labels: `M3x16` / `M3x14` on the cap floor near bosses; `M3x25` on the pod −Y wall.

## Cap base (slim)

| Aid | Use |
| --- | --- |
| `#1 CAP` + bq24074 L-corners + Ø5×1 standoffs at (0, 52) | ID + drop Adafruit 4755 |
| Inside-floor labels (5 × 0.8 bitmap) | Fastener / pin callouts |
| Floor arrow → +Y (south of bq seat) | Orient GPS / free end of the spine |
| Ø1 × 0.4 bed dimples by lid columns | Insert start cues |

Print outside-face down, cavity up, no supports. Bed face stays planar (no glyph cuts into z=0).

## Pod base (L and R)

| Aid | Use |
| --- | --- |
| `#2 POD L` / `#3 POD R` on −Y wall | Identify L vs R |
| Cell cradle (2× R9.4 arc ribs, 2.5 mm) | Seat Ø18.4 1781 |
| Buzzer L-corners + ±Y slot rails | Seat / hold 25.4 Qwiic board; ≥0.5 mm to column (37,27) |
| Floor grooves + arrow | Route leads; orient crest cable |

## Test coupon + tri-axis scale

| Feature | Use |
| --- | --- |
| Insert ladder Ø4.0 / 4.2 / 4.4 / 4.6 / 4.8 × 6 mm deep | Iron-fit for Adafruit 4255 (`INSERT_M3`) |
| Lid / clamp gap pads 0.1 / 0.2 / 0.3 / 0.4 mm proud | Mating-face clearance feel |
| Blind Ø2.8 tap + Ø3.2 clear at 4 / 5 / 6 mm | Tip clearance vs pocket depth |
| Pin sockets Ø4.2 / 4.35 / 4.5 × 2 + sample pins | Saddle pin fit |
| 20 mm bridge (2 mm roof) | Bridging check |
| Stepped M3×14 / ×16 / ×18 Ø2.8 blind gauge | Screw-length feel |
| Free 1×1×0.8 e-foot pad | First-layer spread |
| O-ring groove sample + ANT stamp | Cheap extras |
| `scale_bar_xyz.stl` | 100 X × 50 Y × 20 Z, 10 mm ticks |

## Plate footprint (246 × 246 usable)

Conservative pack of cap + 2 pods + coupon + scale: about **170 × 214 mm**
(`bases_plate_footprint_mm()` → 170.5 × 213.5), inside the P2S **246 × 246**
usable bed.

## Mass (solid PLA @ 1.24 g/cm³)

| Feature | Approx |
| --- | --- |
| Pod cell cradle + buzzer L + rails − grooves | ≈ 0 g net each pod |
| Cap bq24074 seat + engraving | ≈ +0.3 g |
| Coupon + scale | side print (~12 g + ~4 g solid) |

## Intentional omissions

- **Bed-face glyph engraving: dropped** (z≈0 STL slivers).
- **Slim cap kit_fence solid: not present** — collar reference uses 0.3 mm/side; add later if Cody wants kit L-rails.
- **Starling XIAO / Wio boards: skipped** (no Starling CAD yet).
- Raised nest lip on saddle: deferred.
- Pod column dimples removed.
