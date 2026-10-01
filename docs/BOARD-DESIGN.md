# Designing the board without a big budget

Written 2026-09-26. The custom board is the step that makes 1,000 collars possible (`MANUFACTURING.md`). We don't have $25k for a design firm, so we build it ourselves with free tools, agents, and the free design reviews chip makers offer.

## Two boards, in order

### 1. Carrier board (start now)

A simple board that the parts we already bought **plug into**: the nRF9151 Connect Kit, the MAX-M10S breakout and the IMU sit on headers. The carrier board itself holds only the easy parts:

- Charger (bq24074 for now) and thermistor connector
- Buzzer driver and piezo
- Connectors for the panels, battery and strap harness
- Mounting holes that match the shell

**Why first:**
- **No radio design on it.** The antennas stay on the boards Nordic and SparkFun already got right, so there's nothing to certify and nothing hard to get wrong.
- **Cheap.** A 2-layer board; 5 assembled boards from JLCPCB cost roughly $30–100.
- **Useful straight away.** It replaces the jumper-wire mess in the alpha collars (5–10 units).
- **Teaches the whole process** (schematic, layout, ordering, assembly, bring-up) on a board where mistakes cost $50.

### 2. Integrated board (after the carrier board works)

Everything on one 4-layer board: the nRF9151 SiP, the GNSS module and antennas, a LiFePO4 charger (BQ25798), IMU, flash, eSIM and buzzer driver. The hard part is the radio sections (LTE and GNSS antenna feeds, matching, ground plane). We don't invent those:

- **Copy the reference designs exactly.** Nordic publishes nRF9151 reference layouts; u-blox publishes MAX-M10S integration guides. Following them closely is also what lets us reuse their certifications.
- **Free expert review.** Nordic reviews customers' schematics and layouts through private DevZone tickets. u-blox offers design support too. That's the review we'd otherwise pay a firm for.
- **Spins cost $100–300** at JLCPCB for 5 assembled boards. Plan on two or three spins.

## What agents can do

| Job | How |
| --- | --- |
| Part choice | Pick parts in JLCPCB's stocked library ("basic" parts avoid setup fees), check stock and price |
| Schematic | Write the circuit as code with **SKiDL** (Python that compiles to a KiCad netlist). Agents are good at text; every change is a reviewable diff |
| Checks | `kicad-cli` runs electrical and design-rule checks and exports renders, so agents can check their own work in a loop (like the Blender self-review in `DESIGN-TOOLING.md`) |
| Layout | Place parts by script; route the simple nets with an autorouter (Freerouting). Radio and power sections are placed by hand, following the reference layouts |
| Review prep | Assemble datasheet checklists, the power budget and a design-review pack for Nordic DevZone |
| Ordering | Generate Gerbers, the BOM and pick-and-place files in JLCPCB's format |

Community KiCad MCP servers exist and are worth trying so an agent can drive KiCad directly.

## Open-source reference designs: learn from them, don't copy them

The SparkFun and Adafruit breakout designs are published, but under **CC BY-SA** (share-alike). Copying them into our board would force our board under share-alike terms, which clashes with the licence plan in `STRATEGY.md`. Use them to learn and check our work, then draw our own circuits from the **chip makers' datasheets and reference designs**, which carry no such condition. The Makerdiary board files we vendored are Apache-2.0 and fine to reuse.

## What Cody can put in (time, not money)

- **KiCad is installed.** Do one beginner tutorial, so you can read a schematic and a layout when agents produce them. A weekend.
- **Bring-up.** When the carrier boards arrive: plug in parts, measure with the multimeter, report back. Agents can't hold a probe.
- **Shell measurements.** The board outline comes from the shell. Once the printed top unit exists, measure the inside space.
- **Accounts.** A Nordic DevZone account (free), a JLCPCB account.

## Costs

| Step | Cost |
| --- | --- |
| KiCad, SKiDL, Freerouting | Free |
| Carrier board, 5 assembled | ~$30–100 per spin |
| Integrated board, 5 assembled | ~$100–300 per spin, 2–3 spins |
| Nordic / u-blox design review | Free |
| **Total to a working integrated board** | **Under ~$1,000** plus our time |

Certification is still the expensive part later, but it only starts once this board works.

## Next steps

1. ~~Install KiCad and SKiDL.~~ Done 2026-09-26; see `DESIGN-PHASE.md`.
2. Write the carrier-board spec: which headers, which connectors, board size (from the shell design).
3. Agent drafts the carrier-board schematic in code, runs checks, renders it for review.
4. Layout, order 5 from JLCPCB, bring them up on the bench.
