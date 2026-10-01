# Product strategy

Decided 2026-09-26.

## Three layers

| Layer | What | Open? |
| --- | --- | --- |
| **OpenCollar** | Off-the-shelf collar: published design, parts list, firmware. Sold assembled, also buildable DIY | Fully open |
| **Proprietary collar** (name TBD) | Our own engineered collar for farmers who want the best: custom hardware, better GNSS, battery, durability, pulse | Closed hardware and firmware, **open device API** |
| **OpenPasture software** | Agent-first farm management. Open-source core; paid hosted subscription | Open core + paid cloud |

## How they fit

- **OpenCollar is the way in.** A cheap, repairable, assembled collar gets animals collared with low risk. DIY builders and researchers can build their own.
- **The proprietary collar is the upgrade.** Same open API, so a farm can mix both on one herd and move up collar by collar.
- **Open integrations always.** Both collars speak the same published device protocol. Farmers never have to use our software; any software that implements the protocol can run either collar.
- **The subscription wins on merit,** not lock-in: it's the best software for running collars, but not the only one allowed.

## What this means now

- **Sell assembled OpenCollars first.** Kits and DIY stay available; assembled is the main product.
- **The device protocol is the contract** between all three layers. It must be versioned, documented and stable before the proprietary collar exists.
- **Licensing (decided 2026-10-01): permissive for code, weakly reciprocal for hardware.** Files at the repo root (`LICENSE`, `LICENSES/`, `NOTICE`, `CONTRIBUTING.md`):
  - Firmware, scripts and the protocol: Apache-2.0. Anyone can use them, including in closed products; its patent clause ends the patent licence of anyone who sues over the code.
  - Hardware and CAD: CERN-OHL-W-2.0. Anyone can build and sell the boards and enclosure, but a shipped modified version must publish its changes to these files. Their own add-ons can stay closed. This stops a larger company copying the collar and keeping its improvements private.
  - Docs, photos and renders: CC BY 4.0.
  - Why this still allows our proprietary collar: the licence binds others, not the copyright holder. CONTRIBUTING.md asks contributors to grant openpasture the right to relicense their contributions, so outside improvements can go into our own collars too.
  - The names and logo aren't licensed (`NOTICE`). That is what stops knockoffs sold as OpenCollar.
  - Loosening later is easy (W to P for future versions); a version already released permissively can't be taken back. That's why hardware starts at W.
  - Already vendored: Makerdiary board files (Apache-2.0) and Monocypher (CC0 or BSD-2-Clause), compatible.
- **Keep the proprietary collar's firmware in a separate private repo** that consumes shared, permissively licensed pieces (geofence engine, protocol library).
- **Check the name.** "OpenCollar" is already used by other projects (including a long-running Second Life project and some pet products). Do a trademark search before branding anything sold.
