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
- **Licensing must allow our own proprietary collar.** Use permissive licences for the open collar so we (and others) can reuse the work:
  - Firmware: Apache-2.0
  - Hardware and CAD: CERN-OHL-P (permissive)
  - Docs: CC BY 4.0
  - Strongly reciprocal licences (GPL, CERN-OHL-S) would force the proprietary collar to be open if it reused OpenCollar code or designs. Accept outside contributions under a contributor agreement or keep contributions under the same permissive terms.
  - Already vendored: Makerdiary board files (Apache-2.0), compatible.
- **Keep the proprietary collar's firmware in a separate private repo** that consumes shared, permissively licensed pieces (geofence engine, protocol library).
- **Check the name.** "OpenCollar" is already used by other projects (including a long-running Second Life project and some pet products). Do a trademark search before branding anything sold.
