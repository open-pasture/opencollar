# Rook hardware

Rook is the base-station collar: LTE-M + GPS, larger battery, Node V1 mechanical set (cap, dual-cell pods, counterweight). It reuses strap, clamp, insert and seal standards from [`hardware/common/`](../common/).

## Layout

| Path | What |
| --- | --- |
| `cad/lib/node_v1.py` | Rook Node V1 geometry (imports `oc` / `dims` from common); `CAP_STYLE` gable \| saddle |
| `cad/parts/node_v1.py` | Cap / pod / counterweight export script |
| `cad/SADDLE.md` | Slim cap + strap saddle design note (stack math, screws, print) |
| `cad/assembly/` | Assembled Rook on a neck (`node_v1.py`, `.blend`) |
| `stl/` | Print STLs (`node_v1_cap` gable v3, `node_v1_cap_saddle` slim, `node_v1_pod`, `node_v1_cw`, `alt_pods_unapproved`) |
| `print/` | Slice profiles (`p2s_pla`, `p2s_asa`, …), `fix_bbl_3mf.py`, sliced 3MF, `PRINT-HISTORY.md` |
| `bom/HARDWARE-FIT.md` | Fit audit and fastener budget |

## Build

```sh
cd cad
./build.sh node_v1                         # gable v3 cap → stl/node_v1_cap/
OC_CAP_STYLE=saddle ./build.sh node_v1 -- cap saddle   # slim + saddle → stl/node_v1_cap_saddle/
```

Sets `OC_PRODUCT_ROOT` to `hardware/rook` so STLs land in `stl/`. Shared helpers come from `hardware/common/cad/lib`. Do not rebuild gable when iterating on saddle if you need to keep the checked-in v3 STLs bit-identical.

## Print

See `print/PRINTING.md`, `print/README-print-files.md`, and `print/PRINT-HISTORY.md`. Slice with `print/slice_node_v1.sh` or `print/slice_p2s_pla.sh`.
