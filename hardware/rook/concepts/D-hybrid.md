# D — Hybrid (D3 cow-look study)

Target look Cody liked: **tall slim matte-charcoal cap slab** with generous
radii on the collar; strap with webbing slot, keeper and buckle; **small low
counterweight**; orange only on the **latch and 2–3 screws**.

Look / proportion study on the same draft PR as D/D2. **Not print-ready.**

## Cap proportion (locked envelope)

| Locked | D3 study |
| --- | --- |
| Footprint **76×160** | **Kept** |
| Columns `(±29.5, ±68/±42)` | **Kept** |
| Clamp `(±20, ±28.5)` | **Kept** |
| Cavity height **≥13** | **13 mm** (floor 5 → base 18) |
| Plan corners | Softened to **R10** (still inside 76×160) |
| Slim profile | Visual only — long low slab + soft R + flat lid (no XY shrink) |
| Lid tops | Clean flat planes (no crown bevel / hairline) |
| Seam | Inset reveal **0.55 mm** |

**Cap does not break the locked envelope.** Slimness is radii + proportion, not a smaller footprint.

## Orange (brand option 1)

Orange = open / replace:

- Lid **latch** (cosmetic placeholder)
- **3** cap service screw plugs: `(±29.5, 42)` and `(+29.5, 68)`
- All other plugs charcoal (including pod, tub, remaining cap screws)
- Strap buckle stays **charcoal** this round (orange budget is latch + screws)

## Strap interface (indicative, separate STLs)

| Part | File | Role |
| --- | --- | --- |
| Saddle / webbing slot | `saddle.stl` | Under-cap slot for 44 mm webbing |
| Keeper loop | `keeper.stl` | Strap tail keeper |
| Buckle | `buckle.stl` | Simple frame + crossbar |
| Strap | `strap.stl` | Black webbing bar (render) |

## What fits vs what doesn’t

### Fits
- Cap 76×160, columns, clamp, cavity ≥13
- Cap soft R10 inside the locked outline
- Pod XY outer 92×68 with cavity footprint 82×58 and columns `(±37, ±27)`
- Inset seam language on cap / pod / tub
- Option-1 minimal orange (latch + 3 screws)

### Flagged / breaks guide (deliberate for the cow silhouette)
| Item | Study | Guide | Why |
| --- | --- | --- | --- |
| Pod height | **20 mm** base | Cavity **21.5** needs ~24.5 | Low slab — pack may not fit |
| CW outer | **80×64×22** | ~**88×74×30** | Small low counterweight look |
| CW screws | `(±20, ±26)` | `(±22, ±31.5)` | Inboard for smaller tub |

## Colour

| Role | Hex |
| --- | --- |
| Matte charcoal body / lids / strap hardware / most plugs | `#26282B` |
| Oat lid variant (optional render) | `#EFE8D8` |
| Blaze orange latch + 3 service plugs | `#FF6A2B` |
| Strap | near-black |

## Build

```sh
cd hardware/rook/concepts/cad
blender --background --factory-startup --python build_concept_d.py
```

STLs → [`stl/D_hybrid/`](stl/D_hybrid/) · renders → [`images/`](images/).  
Envelope audit also in `stl/D_hybrid/report.json`.

**Draft only — do not merge. Do not print without Cody’s OK.**
