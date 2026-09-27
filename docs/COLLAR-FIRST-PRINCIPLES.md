# The collar from first principles

Written 2026-09-26. Goal: a slim, sleek collar, as close to Halter's as we can get, derived from what each part physically has to do rather than from the dev boards we happen to own. Competitor facts are in `research/collar-form-factors.md`. Numbers marked *est* are estimates to check; nothing here has been measured yet.

## 1. What the physics forces

**The antenna and panels need the sky, so they sit on top of the neck.** The GNSS patch has to face up (`V1-REQUIREMENTS.md`). The panels need sun, and the top of the neck is the only place the animal doesn't shade.

**A collar on a neck rotates freely, so it needs a heavy bottom.** Gravity only turns the collar back upright if the mass below the neck clearly outweighs the mass above it. Every rub on a post, every roll and every lying-down tries to turn it. Halter's ratio is **1.87 : 1** (912 g counterweight under 488 g of device; Verdon et al. 2026). We take **≥ 1.8 : 1** as the design rule until our own rotation tests say otherwise.

**So the top unit's mass sets the whole collar's mass.** Every gram on top needs ~1.8 g more underneath. A heavy top unit makes a heavy collar twice over.

**Draft 1 fails this rule.** Its ~500 g top unit sits over a ~505 g bay: 1 : 1, so almost nothing turns it back upright. It's also 170 × 126 × 55 mm (1.2 L). Its size came from the dev boards on standoffs and the 18 mm Li-ion pack, not from anything the collar needs.

## 2. What must be on top, and nothing else

| Part | Why it's on top | Size | Mass *est* |
| --- | --- | --- | --- |
| GNSS patch | Must face the sky | 25 × 25 × 4 mm, on a ≥ 60 mm ground plane | 10 g |
| Solar cells | Must face the sun | ~65–70 cm² of cells ≈ 1.1–1.2 W (P124-class 24 % cells) | 30 g |
| LTE antenna | Height and clear sky help; kept away from the patch | Flex, ~44 × 10 mm | 3 g |
| Main board | Next to both antennas. **It doubles as the patch's ground plane** | ~110 × 60 mm, 4-layer | 15 g |
| Piezo | Loudest where the ears are | Ø12–17 mm | 5 g |
| Shell, seal, screws, strap clamp | | PA12, 2.5 mm walls, ribbed | 110 g |
| Buffer cell (see 3) | Keeps the fence running if the strap wire is cut | ~1–2 Wh, flat | 20 g |
| **Top unit** | | | **~195–225 g** |

**The battery isn't on the list: it doesn't need the sky.** It's the heaviest functional part, and the collar needs mass at the bottom anyway.

## 3. The main decision: where the battery goes

Energy target unchanged: ~0.25–0.35 Wh/day with adaptive GNSS (`V1-DESIGN.md`), 60 days without sun, so **~20 Wh of LiFePO4** (2 × 26650 or 4 × 18650, ~160–170 g).

| | **A. Halter layout**: battery on top, dead counterweight | **B. The battery is the counterweight**: small buffer on top |
| --- | --- | --- |
| Top unit | ~365 g *est*. The 18650 diameter sets the thickness: **~26 mm** | ~225 g *est*, **~16–18 mm** thick (the flat buffer cell and the patch set it) |
| Bottom | ~680 g of dead steel (1.87 × top) | ~420 g: ~170 g of cells plus protection, shell, and ~180 g of steel to make up the ratio |
| **Whole collar** (with a ~130 g strap) | **~1.18 kg**: at our 1.2 kg limit, lighter than Halter's 1.40 | **~0.78 kg**: lighter than Monil's ~1 kg, the lightest on the market |
| Wire in the strap | Optional (only for bay modules) | **Required** for the 60-day reserve. Power runs down the harness we already planned for every sold collar (`BOTTOM-BAY.md`) |
| If the strap wire is cut | Nothing changes | The top runs on its own panels by day and its ~1–2 Wh buffer at night (~4–6 days *est*), and reports a strap fault. You lose the no-sun reserve, not containment |
| Bay modules | Ballast by default | The bottom *is* the battery module. The Battery Extension becomes standard; Battery + Camera is the same pack with a mount |
| Risk | Proven by Halter | Depends on the harness surviving on animals. We already planned to test that on V1-alpha from day one |

**Recommendation: B.** The collar has to carry ~400 g or more at the bottom whatever we do. Making that mass the battery takes ~400 g off the collar and ~10 mm off the top unit, and it uses the wired strap we'd already committed to. **The gate is the harness durability test on V1-alpha.** If the cable doesn't survive cattle, we fall back to A, and the top unit gets ~10 mm thicker to take the cells.

The cost is on the board. It needs a power path with two batteries: the BQ25798 charges the bottom pack over the strap, and a small separate charger keeps the buffer cell full, diode-OR'd into the system rail. That's a detailed-design task for the integrated board, not a reason to pick A.

## 4. The top unit's shape

What follows from sections 1–3, not a drawing yet:

- **One rigid, low puck on the crest of the neck**, with a curved TPU pad underneath so it sits on the neck, not on two edges. Target envelope **≤ 120 × 80 mm footprint, ≤ 18 mm tall, ≤ 250 g**. Draft 1's volume is ~1.2 L; this is ~0.17 L.
- **The panel is the lid**, as Halter does it: an ETFE panel bonded into the lid on a VHB gasket (Voltaic's mounting method for the P124), not a panel sitting on a separate roof.
- **The patch sits beside the panel, not under it.** Solar cells are metal-backed and block GNSS. The patch goes at one end of the puck with a clear window over it, still on the crest line.
- **Flat, not sloped, panels.** Two faces tilted either side waste area at noon and make the unit taller. One flat face on top uses the footprint best. Panel area matters more than angle: ~70 cm² of cells harvests ~1.4 Wh/day in a Tennessee winter *est*, about 4–5 × the load.
- **Sizing lives at the bottom**, as Halter does it. The top clamps to the strap at a fixed point, so it's the same top unit for every animal. The harness runs along the fixed-length side, and the buckle that sets the size sits on the other side at the bottom module.
- **Room for the pulse.** V1 is audio-first, but the puck's two ends are ~100 mm apart across the neck: inside the 50–300 mm electrode spacing the literature uses. Checking Halter's pulse patents comes before any stimulus design.
- **Left/right sound later.** Halter cues left and right with one speaker per side. A puck is too narrow for a strong left/right effect; if sweeps need directional cues, that's the one argument for side pods.

**Our own look.** Halter's pods-and-bridge shape is protected by a US design patent (USD1089882S). We match their numbers (mass, thickness, sizing at the counterweight), not their appearance. A single crest puck is a different form from theirs.

## 5. What this does to the boards

- **The integrated board is shaped to the puck** (~110 × 60 mm, patch on the board). It's no longer "one board shaped to draft 1's box". It drives the shell, not the other way round.
- **Dev boards can't fit a slim collar.** The Connect Kit on sockets alone is ~15 mm tall before the shell. So V1-alpha (5–10 collars proving GNSS, the cue and the harness on animals) goes in a **plain test box**: its looks don't matter, and draft 1 of the shell becomes that box.
- **The carrier board stops being shaped to a shell.** It becomes a **rectangle under 100 × 100 mm** (JLCPCB's cheapest tier), carrying the same circuits as `hardware/carrier/SPEC.md`. That replaces the ring-board question in the spec. It still earns its place: it replaces the jumper wires in the alpha collars, proves the charger, harness port and test-pad approach, and teaches the pipeline on a $50 board.

## 6. Decisions for Cody

1. **Battery as the counterweight (B)**, gated on the alpha harness test? Or Halter's layout (A)?
2. **Keep the 60-day no-sun target?** It's what makes the battery ~20 Wh. Halter relies on daily sun with a smaller cell. If 20–30 days is enough, the pack halves in B, or the top gets thinner in A.
3. **Carrier board becomes a plain rectangle under 100 × 100 mm**, not shaped to a shell. OK?
4. **One crest puck** rather than two side pods, accepting weaker left/right cues?

## 7. Measurements needed (pilot animals)

- Neck circumference where the collar sits (just behind the jaw), on the smallest and largest animals.
- The crest's curvature there: a contour gauge or a bent strip of solder wire traced on paper is enough. It sets the pad under the puck.
- Where a strap-mounted cable gets caught or rubbed: watch the alpha harness.

## 8. Next steps

1. Cody decides section 6.
2. Rotation test before any shell: a strap with a ~225 g top mass and a ~420 g bottom mass, worn by a person first, then a steer. Does it stay upright? Cheap, fast, and it checks the 1.8 : 1 rule.
3. Revise the carrier spec to the rectangle and restart the schematic.
4. Draw the puck and the bottom battery module in `mechanical/` (new parts; draft 1 stays as the alpha test box).
5. Integrated board outline from the puck.
