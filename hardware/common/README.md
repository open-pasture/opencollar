# Shared collar hardware

Parametric CAD, STLs and fastener/insert standards reused by **Rook** and **Starling**. Collar-specific shells live under `hardware/rook/` and `hardware/starling/`; they import from here so strap, clamp, cap-interface and insert geometry is not duplicated.

## Layout

| Path | What |
| --- | --- |
| `cad/lib/oc.py` | Shared Blender helpers (primitives, export, checks) |
| `cad/lib/dims.py` | Bought-part and tolerance dimensions (strap, M3 inserts, O-ring, vent, …) |
| `cad/lib/collar.py` | V1-alpha strap/clamp/top-unit/bay geometry (legacy shared shell) |
| `cad/parts/` | Part scripts: `fit_test`, `seal_box`, `top_unit`, `bay` |
| `cad/assembly/` | Alpha collar assembly |
| `stl/` | Exported STLs (mm) for the shared parts |
| `bom/` | Shared fastener / insert notes |

## Build

```sh
cd cad
./build.sh            # every shared part
./build.sh fit_test   # one part
```

Needs Blender 5.x (`BLENDER=/path/to/blender`). STLs write to `stl/` via `OC_PRODUCT_ROOT`.

## What Rook and Starling reuse

- Strap channel width/thickness (`dims.STRAP`)
- M3×4 brass heat-set insert standard (`dims.INSERT_M3`, Adafruit 4255)
- M3 button-head clamp conventions (`dims.M3_BUTTON`)
- Fit-test coupon and seal-box process
- Clamp-bar / cap-interface pattern (Starling has no designed parts yet; see `hardware/starling/README.md`)
