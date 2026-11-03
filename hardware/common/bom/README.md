# Shared BOM / fastener standard

Insert and screw standards for every collar that mounts on the shared strap:

| Item | Spec | Source |
| --- | --- | --- |
| Heat-set insert | M3×4 brass, Adafruit 4255 | `cad/lib/dims.py` → `INSERT_M3` |
| Clamp screws | M3 button head (ISO 7380) | `dims.M3_BUTTON` |
| O-ring cord | 2 mm silicone face seal | `dims.ORING_2MM` |
| Vent | Amphenol M6×0.75 ePTFE | `dims.VENT_M6` |

Tune hole sizes with `stl/fit_test/` before production prints. Rook-specific qty and fit audit: `hardware/rook/bom/HARDWARE-FIT.md`.
