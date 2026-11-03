# Rook docs

Collar-facing docs for the Rook (LTE-M + GPS base-station collar). Hardware: [`hardware/rook/`](../../hardware/rook/).

## Firmware runbooks (target — owned by op-firmware)

When [PR #8](https://github.com/open-pasture/opencollar/pull/8) / the firmware migration lands, link these pages to the collar folder under `firmware/rook/`:

| Doc page (this tree) | Firmware runbook |
| --- | --- |
| [flash.md](flash.md) | `firmware/rook/FLASH.md` |
| [control.md](control.md) | `firmware/rook/CONTROL.md` |
| [provision.md](provision.md) | `firmware/rook/PROVISION.md` |

Also see `firmware/rook/README.md` and cross-collar behaviour in `firmware/docs/INTERFACES.md` (target layout in [`REPO-STRUCTURE.md`](../REPO-STRUCTURE.md); architecture draft in PR #8 / `docs/firmware/` once merged).
