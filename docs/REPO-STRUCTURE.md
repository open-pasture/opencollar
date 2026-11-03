# OpenCollar repository structure

Map of the repo after the Rook / Starling hardware split. **Firmware and protocol trees are unchanged on this PR**; the firmware section below is the **target** layout owned by op-firmware (see [`firmware/ARCHITECTURE.md`](../firmware/ARCHITECTURE.md) and [`docs/firmware/`](firmware/)).

## Final tree (hardware + docs this PR; firmware target annotated)

```
opencollar/
├── README.md
├── docs/
│   ├── REPO-STRUCTURE.md          ← this file
│   ├── assembly/                  ← how to put a collar together
│   ├── rook/                      ← Rook collar docs (links to firmware runbooks)
│   ├── starling/                  ← Starling collar docs (links to firmware runbooks)
│   ├── firmware/                  ← pilot spec + Rook gap list (from PR #8)
│   └── …                          ← existing design / build docs
├── hardware/
│   ├── common/                    ← shared parametric CAD, STLs, fastener standard
│   │   ├── cad/lib/               ← oc.py, dims.py, collar.py
│   │   ├── cad/parts/             ← fit_test, seal_box, top_unit, bay
│   │   ├── cad/assembly/          ← V1-alpha collar assembly
│   │   ├── stl/                   ← shared STLs
│   │   └── bom/                   ← insert / clamp standard
│   ├── rook/                      ← Rook (LTE-M + GPS) Node V1 set
│   │   ├── cad/                   ← node_v1 geometry + assembly
│   │   ├── stl/                   ← node_v1_cap / pod / cw (+ alt_pods_unapproved)
│   │   ├── print/                 ← p2s_pla, p2s_asa, fix_bbl_3mf.py, sliced 3MF, PRINT-HISTORY
│   │   └── bom/HARDWARE-FIT.md
│   ├── starling/                  ← skeleton only (shares common strap/clamp/cap-interface)
│   │   ├── cad/  stl/  print/  bom/
│   └── carrier/                   ← PCB (unchanged location)
├── firmware/                      ← DO NOT restructure in this PR (op-firmware)
│   ├── ARCHITECTURE.md            ← target layout + ownership (PR #8)
│   ├── src/                       ← stays until migration PR after Nov 4
│   ├── boards/  scripts/  tests/  third_party/
│   └── (target) core/ lora/ radio/ rook/ starling/ sim/ docs/
└── protocol/                      ← unchanged (op-firmware / protocol owner)
```

## Old path → new path

| Old | New |
| --- | --- |
| `mechanical/lib/oc.py` | `hardware/common/cad/lib/oc.py` |
| `mechanical/lib/dims.py` | `hardware/common/cad/lib/dims.py` |
| `mechanical/lib/collar.py` | `hardware/common/cad/lib/collar.py` |
| `mechanical/parts/fit_test.py` | `hardware/common/cad/parts/fit_test.py` |
| `mechanical/parts/seal_box.py` | `hardware/common/cad/parts/seal_box.py` |
| `mechanical/parts/top_unit.py` | `hardware/common/cad/parts/top_unit.py` |
| `mechanical/parts/bay.py` | `hardware/common/cad/parts/bay.py` |
| `mechanical/assembly/collar.py` | `hardware/common/cad/assembly/collar.py` |
| `mechanical/assembly/collar_v1_alpha.blend` | `hardware/common/cad/assembly/collar_v1_alpha.blend` |
| `mechanical/exports/fit_test/` | `hardware/common/stl/fit_test/` |
| `mechanical/exports/seal_box/` | `hardware/common/stl/seal_box/` |
| `mechanical/exports/bay/` | `hardware/common/stl/bay/` |
| `mechanical/exports/top_unit/` | `hardware/common/stl/top_unit/` |
| `mechanical/build.sh` | `hardware/common/cad/build.sh` |
| `mechanical/package.sh` | `hardware/common/cad/package.sh` |
| `mechanical/lib/node_v1.py` | `hardware/rook/cad/lib/node_v1.py` |
| `mechanical/parts/node_v1.py` | `hardware/rook/cad/parts/node_v1.py` |
| `mechanical/assembly/node_v1.py` | `hardware/rook/cad/assembly/node_v1.py` |
| `mechanical/assembly/node_v1.blend` | `hardware/rook/cad/assembly/node_v1.blend` |
| `mechanical/assembly/node_concept.py` | `hardware/rook/cad/assembly/node_concept.py` |
| `mechanical/exports/node_v1_cap/` | `hardware/rook/stl/node_v1_cap/` |
| `mechanical/exports/node_v1_pod/` | `hardware/rook/stl/node_v1_pod/` |
| `mechanical/exports/node_v1_cw/` | `hardware/rook/stl/node_v1_cw/` |
| `mechanical/exports/alt_pods_unapproved/` | `hardware/rook/stl/alt_pods_unapproved/` |
| `mechanical/print/` (profiles, scripts, sliced) | `hardware/rook/print/` |
| `mechanical/PRINT-HISTORY.md` | `hardware/rook/print/PRINT-HISTORY.md` |
| `mechanical/PRINTING.md` | `hardware/rook/print/PRINTING.md` |
| `mechanical/PRINT-LIST.md` | `hardware/rook/print/PRINT-LIST.md` |
| `mechanical/THROUGHPUT.md` | `hardware/rook/print/THROUGHPUT.md` |
| `mechanical/HARDWARE-FIT.md` | `hardware/rook/bom/HARDWARE-FIT.md` |
| `mechanical/README.md` | `hardware/rook/README.md` (rewritten) |
| *(new)* | `hardware/common/README.md`, `hardware/starling/**` |
| *(new)* | `docs/rook/`, `docs/starling/`, `docs/assembly/` |

`mechanical/` is removed. `hardware/carrier/` and top-level `hardware/*.md` / `hardware/photos/` stay put.

## Conventions

### Naming

- **Rook** — base-station collar (LTE-M + GNSS, bigger battery). Mechanical plan of record = former Node V1.
- **Starling** — cheaper LoRa mesh-relay collar. Hardware is skeleton-only until designed.
- Shared geometry and bought-part numbers live in **common**; collar-specific shells live under the collar name.

### Where CAD / STL / print settings live

| Kind | Location |
| --- | --- |
| Shared parametric CAD (`oc`, `dims`, strap/clamp/alpha) | `hardware/common/cad/` |
| Collar-specific CAD | `hardware/<collar>/cad/` |
| STLs | `hardware/<collar>/stl/` (shared coupons in `hardware/common/stl/`) — was `exports/` |
| Slice profiles, `fix_bbl_3mf.py`, sliced `.gcode.3mf`, print history | `hardware/<collar>/print/` |
| Fit audit / collar BOM notes | `hardware/<collar>/bom/` |

Rook CAD sets `OC_PRODUCT_ROOT` to `hardware/rook` and imports helpers from `hardware/common/cad/lib`. Common builds default `OC_PRODUCT_ROOT` to `hardware/common`. `oc.finish()` writes STLs under `$OC_PRODUCT_ROOT/stl/`.

Profiles present today under Rook: `p2s_pla`, `p2s_asa`, `ender3v3se`, `ender3v3se_petg`. `p2s_pla_v21` is not in the repo yet.

### How Rook and Starling reuse common

- Both import `dims` (strap, `INSERT_M3`, O-ring, vent, M3 button) and `oc` from common.
- Starling has **no designed parts yet**; its README states it will share strap / clamp / cap-interface from common when CAD starts.
- Clamp bars for Rook modules are still generated inside `rook/cad/lib/node_v1.py` (same 70 mm / channel pattern); do not fork insert or strap numbers into the collar trees.
- Fit-test and seal-box STLs stay in common; current PLA slices for those coupons remain under `hardware/rook/print/sliced/` with the active print job.

## Firmware — target layout only (op-firmware)

**This PR does not move, rename or edit anything under `firmware/` or `protocol/`.**

Authoritative proposal: [`firmware/ARCHITECTURE.md`](../firmware/ARCHITECTURE.md) (merged via [PR #8](https://github.com/open-pasture/opencollar/pull/8)). Pilot notes: [`docs/firmware/pilot-firmware-spec.md`](firmware/pilot-firmware-spec.md), [`docs/firmware/rook-gap-list.md`](firmware/rook-gap-list.md). MCUboot / flashable merged hex draft: [PR #7](https://github.com/open-pasture/opencollar/pull/7) (pointer only).

### Target directories (not created by PR #8; describe only)

| Directory | Role | Owner (from ARCHITECTURE.md) |
| --- | --- | --- |
| `firmware/core/` | Portable C: geofence, cues, welfare hooks, signed boundary verify, fence store, … | op-firmware |
| `firmware/lora/` | Gossip / handoff protocol library + `radio_hal.h` | op-fw-proto |
| `firmware/radio/` | SX1262 HAL / Zephyr backends | op-fw-radio |
| `firmware/rook/` | Rook nRF9151 app | op-fw-rook-lte |
| `firmware/starling/` | Starling nRF52840 app | op-fw-starling |
| `firmware/sim/` | Host lossy N-node simulator | op-fw-proto |
| `firmware/docs/INTERFACES.md` | Rook ↔ Starling ↔ server behaviour | op-firmware |
| `firmware/boards/`, `tests/`, `third_party/`, `scripts/` | Already present; ownership per ARCHITECTURE.md | — |

`firmware/src/` **stays untouched** until op-firmware’s migration PR after Nov 4.

Each collar app folder is intended to grow `README.md`, `FLASH.md`, `CONTROL.md`, `PROVISION.md` (serial provisioning: farm public key, collar id, role; server registers the device).

### Docs pages that will link to those runbooks

| Collar docs | Links to (target) |
| --- | --- |
| [`docs/rook/flash.md`](rook/flash.md) | `firmware/rook/FLASH.md` |
| [`docs/rook/control.md`](rook/control.md) | `firmware/rook/CONTROL.md` |
| [`docs/rook/provision.md`](rook/provision.md) | `firmware/rook/PROVISION.md` |
| [`docs/starling/flash.md`](starling/flash.md) | `firmware/starling/FLASH.md` |
| [`docs/starling/control.md`](starling/control.md) | `firmware/starling/CONTROL.md` |
| [`docs/starling/provision.md`](starling/provision.md) | `firmware/starling/PROVISION.md` |

### Left for op-firmware to sequence

1. Create `firmware/core`, `lora`, `radio`, `rook`, `starling`, `sim`, and `firmware/docs/INTERFACES.md` when ready (PR #8 documented them; it did not create the folders).
2. Migration PR after Nov 4: move `firmware/src/` into `core/` + `rook/` per the table in `ARCHITECTURE.md`; keep in-flight draft PRs unblocked until then.
3. Per-collar `FLASH.md` / `CONTROL.md` / `PROVISION.md` under `firmware/rook` and `firmware/starling`.
4. Host-test layout under `tests/host/{core,lora,sim}` as in `ARCHITECTURE.md`.
5. Align any leftover path mentions once the migration lands; rebase hardware PRs if they touch shared docs.
6. MCUboot / merged.hex work continues on [PR #7](https://github.com/open-pasture/opencollar/pull/7).

## Protocol

Unchanged. v1 / v2 docs and vectors stay under `protocol/`. Firmware vector copies remain under `firmware/tests/host/vectors/` until op-firmware says otherwise.
