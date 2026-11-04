# Starling hardware (skeleton)

Starling is the cheaper, smaller LoRa mesh-relay collar. **No designed parts yet.**

It is intended to share from [`hardware/common/`](../common/):

- strap channel and clamp-bar interface
- cap / module mounting pattern where the form factor allows
- M3×4 heat-set insert and fastener standard (`common/bom/`)
- fit-test and seal process

## Layout (empty placeholders)

| Path | Intent |
| --- | --- |
| `cad/` | Starling-specific parametric CAD (imports common) |
| `stl/` | Starling STLs |
| `print/` | Starling slice profiles and 3MF (separate from Rook) |
| `bom/` | Starling-only BOM lines |

Do not copy Rook STLs here. When Starling CAD starts, add parts under `cad/` and import shared dims/helpers from `hardware/common/cad/lib/`.
