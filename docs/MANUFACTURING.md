# Manufacturing 1,000 collars

Written 2026-09-26, before the first prototype is assembled. Estimates, not quotes.

## The one big change: a custom board

The prototype is breakout boards joined by jumper wires. That doesn't scale:

- **Labour:** two to three hours of hand soldering and wiring per collar. 1,000 collars is roughly a year of one person's time.
- **Reliability:** every connector and hand joint is a failure point on an animal that rubs, rolls and gets rained on.
- **Cost:** the breakout boards alone are most of the $260 parts bill.

So the collar becomes **one custom board**, shaped to the shell and assembled by a factory:

- nRF9151 SiP (LTE-M + fence logic) and MAX-M10S (GNSS) as modules, soldered by machine.
- Charger (BQ25798, LiFePO4), IMU, buzzer driver, flash, eSIM, antenna feeds, and connectors to the panels, battery and strap harness, all on the same board.
- **Test pads** on the board so a fixture can flash and test it in seconds.

With that, each collar takes about 15–20 minutes of final assembly instead of hours.

## Who builds what

| Part | Who | Notes |
| --- | --- | --- |
| Board design | Us, with a contract PCB designer to review | The prototype circuit is the reference. Budget $5–20k for outside review and layout help |
| Board assembly (PCBA) | Turnkey assembler: JLCPCB or PCBWay (cheapest), or a US shop like MacroFab (faster to talk to, higher cost) | They buy the parts, build and ship finished boards |
| Shell | MJF/SLS print service (PA12) for the first few hundred; injection moulding after the design freezes | See below |
| Battery packs | A pack maker assembles the LiFePO4 cells with protection and a connector | Must come with UN38.3 test reports for shipping |
| Solar panels | Voltaic (or a panel maker) at volume pricing, with our connector fitted | |
| Straps + harness | Livestock strap supplier; off-the-shelf M8 cordsets | |
| Final assembly, test, pack | **Us**, in a small workspace at first | Keeps quality in our hands while the design is still settling. Move to a contract manufacturer (box build) once stable |

## Shell: print first, mould later

- **Injection moulding:** tooling runs $10–40k per part family (top unit, lid, bay, clamps). The part then costs a dollar or two. It only pays off once the design stops changing.
- **MJF printing in PA12:** no tooling, roughly $15–40 per shell set at a service, and it's tough enough for the field.
- **So:** print the first 100–500, learn from the field, freeze the design, then cut moulds for the rest. The shell must be designed with moulding in mind from the start (draft angles, even walls) so switching doesn't mean a redesign.

## Certification (the long pole)

| What | Why | Rough cost / time |
| --- | --- | --- |
| FCC (US) | Any radio product sold in the US. Using pre-certified radio modules cuts this down a lot, but the finished collar still needs testing | $10–30k, 1–3 months |
| Carrier approval (PTCRB and/or AT&T/Verizon) | Required to run on US LTE-M networks | $15–40k, 2–3 months |
| ISED (Canada), CE (EU) | Only if selling there | Later |
| Battery shipping (UN38.3) | Lithium cells can't ship without it | Comes from the pack maker |
| Stimulus / animal welfare | When the pulse module ships. Some markets restrict it | Check before launch |

Start a pre-scan at a test lab as soon as the first custom boards work, so surprises come early.

## Stages

| Stage | Units | What it proves | Build method |
| --- | --- | --- | --- |
| Prototype | 1 | GPS, fence, cue, physical collar | Breakouts, hand-built (now) |
| Alpha | 5–10 | Same collar on real cattle | Breakouts, hand-built |
| EVT (custom board) | 10–20 | The board works | Turnkey PCBA, printed shells |
| DVT | 50–100 | Field pilot, certification testing, test fixture | Turnkey PCBA, printed shells |
| PVT | 100–200 | The production line works at pace | Full process, first paid customers |
| Production | 1,000 | | Moulded shells once the design is frozen |

Roughly **9–15 months** from a working prototype to 1,000 shipped, with certification and field testing setting the pace.

## Money

- **One-time costs:** board design help ($5–20k), certification ($25–70k), test fixtures ($3–10k), moulds when ready ($10–40k). Roughly **$50–140k**.
- **Per collar at 1,000:** parts and assembly about $110–150, plus $5–8 for packaging and freight.
- **Cash for the run:** about **$150–200k** before the first 1,000 are paid off. Pre-orders with deposits (the reservation page) and the kit business are the natural ways to fund it.

## The end-of-line test (every collar)

1. Fixture flashes firmware and checks the board (power rails, IMU, GNSS, modem) through the test pads.
2. After assembly: leak test (pressure decay through the vent port, or submersion on a sample).
3. Outdoor or GNSS-simulator check that the collar gets a fix, and an LTE-M check-in to our server.
4. Serial number, SIM and device ID recorded against the unit, then packed.

## Next decisions

- When the prototype works: find a PCB designer and get quotes from JLCPCB/PCBWay and one US assembler.
- Pick the test lab and book a pre-scan slot.
- Decide whether final assembly starts in-house (recommended for the first few hundred).
