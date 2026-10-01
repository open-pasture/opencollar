# OpenCollar

Open hardware virtual-fence collar. Off-the-shelf parts, open protocol, works with any software that speaks it.

- `docs/BUILD-LOG.md` — dated record of every step, result, and decision
- `docs/PROTOTYPE-V0.md` — current state of the V0 prototype
- `docs/V1-DESIGN.md` — the V1 collar design and cost estimates
- `docs/MANUFACTURING.md` — how we get to 1,000 collars, and why FCC and carrier approval matter
- `docs/BOARD-DESIGN.md` — designing the custom board on a small budget
- `docs/DESIGN-PHASE.md` — board design toolchain and workflow (KiCad + SKiDL)
- `docs/COLLAR-FIRST-PRINCIPLES.md` — the slim collar worked out from first principles
- `docs/TEST-FIXTURE.md` — how every board gets tested, explained from zero, with pictures
- `docs/CARRIER-EXPLAINED.md` — every part on the carrier board, what it does, and where it sits in the collar
- `docs/STRATEGY.md` — product strategy and licensing
- `hardware/prototype-cart.md` — parts for the first prototype
- `hardware/orders-2026-09-26.md` — what was ordered and paid
- `hardware/tools.md` — tools for building a collar
- `hardware/bom.md` — parts list
- `hardware/photos/` — build photos

## Licence

OpenCollar is open so anyone can build, repair and improve their own collar.

| What | Licence | Folders |
| --- | --- | --- |
| Firmware, scripts and the protocol | [Apache-2.0](LICENSE) | `firmware/`, `protocol/`, and code anywhere else |
| Hardware and CAD (boards, enclosure, print files) | [CERN-OHL-W-2.0](LICENSES/CERN-OHL-W-2.0.txt) | `hardware/`, `mechanical/` |
| Docs, photos and renders | [CC BY 4.0](LICENSES/CC-BY-4.0.txt) | `docs/`, `hardware/photos/`, `mechanical/renders/` |

In plain terms:

- **Firmware and protocol:** use them for anything, including closed products. Keep the copyright notice and [NOTICE](NOTICE).
- **Hardware:** build, sell and change the boards and the enclosure. If you ship a modified version of these design files, publish your changes to them under the same licence. Your own add-ons can stay closed.
- **Docs:** reuse them with credit to openpasture.

Third-party files keep their own licences: `firmware/boards/makerdiary/` (Apache-2.0, plus Nordic's 5-clause licence where its headers say so) and `firmware/third_party/monocypher/` (CC0 or BSD-2-Clause).

The names openpasture and OpenCollar and the openpasture logo aren't covered by these licences; see [NOTICE](NOTICE). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).
