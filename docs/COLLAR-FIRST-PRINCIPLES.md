# The collar from first principles

Written 2026-09-26. Goal: a slim, sleek collar, as close to Halter's as we can get, derived from what each part physically has to do rather than from the dev boards we happen to own. Competitor facts are in `research/collar-form-factors.md`. Numbers marked *est* are estimates to check; nothing here has been measured yet.

**Decided with Cody, 2026-09-26:** the battery is the counterweight (layout B); keep the 60-day no-sun target; the carrier board is a plain rectangle; left and right sound cues, as Halter does; design to average neck sizes with adjustment, not to measurements of the pilot animals.

## 1. What the physics forces

**The antenna and panels need the sky, so they sit on top of the neck.** The GNSS patch has to face up (`V1-REQUIREMENTS.md`). The panels need sun, and the top of the neck is the only place the animal doesn't shade.

**A collar on a neck rotates freely, so it needs a heavy bottom.** Gravity only turns the collar back upright if the mass below the neck clearly outweighs the mass above it. Every rub on a post, every roll and every lying-down tries to turn it. Halter's ratio is **1.87 : 1** (912 g counterweight under 488 g of device; Verdon et al. 2026). We take **≥ 1.8 : 1** as the design rule until our own rotation tests say otherwise.

**So the top unit's mass sets the whole collar's mass.** Every gram on top needs ~1.8 g more underneath.

**Draft 1 fails this rule.** Its ~500 g top unit sits over a ~505 g bay: 1 : 1. It's also 170 × 126 × 55 mm (1.2 L), a size that came from the dev boards on standoffs and the 18 mm pack. Draft 1 becomes the V1-alpha test box (section 7).

**Left and right cues need a sound source on each side of the neck.** Cattle localise sound poorly: their minimum audible angle is about 30° (Heffner & Heffner 1992). Two speakers a few centimetres apart on top of the neck sit almost on the animal's midline, so it can't tell them apart. One speaker on each side of the neck, close to each ear, gives a large left/right difference it can use. Halter's two speakers are one per side (`research/collar-form-factors.md`). Left/right cues matter for us: moves are sweeps, and turning an animal is part of a sweep (`protocol/README.md`).

## 2. The neck we design for

| | Value | Source |
| --- | --- | --- |
| Fit range, circumference where the collar sits (just behind the jaw) | **75–130 cm** | Monil's published fit range. Small indigenous cattle average ~70 cm (Ethiopian morphometric study); our 48" strap is 122 cm |
| Design centre | **~107 cm**, cross-section ~25 cm wide × 42 cm tall | The neck section in our assembly model (*est*) |
| Crest (top of the neck) radius | **~74 mm** at the design centre, ~52–90 mm across the fit range | Ellipse model: a² / b (*est*) |
| Side of the neck radius | **~350 mm** at the design centre: nearly flat | b² / a (*est*) |

**The crest is tight and the sides are nearly flat.** A rigid part across the top has to be narrow: a 60 mm-wide base on a 74 mm radius stands 6.4 mm proud at its edges, and a 120 mm base would stand 31 mm proud. Rigid parts belong on the flat sides; across the crest, only something narrow fits. This is also the first-principles reason behind Halter's side pods and flexible bridge.

**Adjustment lives at the bottom, equally on both sides.** The top unit clamps to the strap at a fixed point, so it's the same top unit for every animal, as with Halter. Adjusting only one side would put the bottom module off-centre on small and large necks. Its weight would then rotate the whole collar until it hung lowest, pulling the top unit off the crest. So both strap ends adjust at the bottom module and stay within one hole of each other (Halter's rule). The harness side's extra length (up to ~27 cm across the 75–130 cm range) is stored in a slack pocket in the bottom module.

## 3. What goes on top

Three parts, joined by the strap:

```
          ear pod ─── crest unit ─── ear pod        (top of the neck)
              \                          /
               \      strap + harness   /
                 ─── battery module ───              (under the throat: the counterweight)
```

| Part | Contents | Envelope *est* | Mass *est* |
| --- | --- | --- | --- |
| **Crest unit** | GNSS patch at one end under a clear window, main board (doubles as the patch's ground plane), LTE antenna, solar panel as the lid (~55–60 cm² of cells ≈ 1 W), buffer cell, harness socket | **~60 mm across the neck × ~130 mm along the spine × ≤ 18 mm tall** | ~170 g |
| **Ear pods ×2** | One piezo each behind an acoustic membrane; later, one pulse electrode each on the neck face. A thin cable, permanently fitted, to the crest unit, in a TPU sleeve along the strap | ~45 × 35 × 12 mm, on the flat sides ~120 mm of strap from the crest centre | 2 × ~40 g |
| Interconnect | Two short cables and the sleeve | | ~20 g |
| **Top total** | | | **~270 g** |

- **The panel lives only on the crest unit.** The pods sit on the near-vertical sides, where a panel sees little midday sun, so they stay small and simple. ~1 W on the crest harvests ~1.25 Wh/day in a Tennessee winter (*est*: 2.5 sun-hours × 50 % losses): ~4 × the load.
- **The pods also carry the pulse electrodes later.** They end up on opposite sides of the neck, ~200 mm apart: inside the 50–300 mm electrode spacing the literature uses. Check Halter's pulse patents before any stimulus design.
- **Our own look.** Halter's pods-and-bridge top unit is protected by a US design patent (USD1089882S). Ours is a crest unit with the GNSS antenna on top plus two small ear pods: a different form. Before production, get a quick freedom-to-operate check on Halter's utility patents as well.

## 4. The battery is the counterweight

Energy target: ~0.25–0.35 Wh/day with adaptive GNSS (`V1-DESIGN.md`), 60 days without sun, so **~20 Wh of LiFePO4** (2 × 26650 or 4 × 18650, ~160–170 g) in the **battery module** under the throat.

| | Mass *est* |
| --- | --- |
| Top (section 3) | ~270 g |
| Battery module: cells ~170 g, protection and fuel gauge ~10 g, shell ~80 g, steel to make up 1.87 × top ~245 g | ~505 g |
| Strap and harness | ~130 g |
| **Whole collar** | **~0.9 kg** (Halter 1.40, Nofence ~1.5, Monil ~1.0) |

- **If the strap wire is cut,** the crest unit runs on its own panel by day and its ~1–2 Wh buffer cell at night (~4–6 days), and reports a strap fault. The fence keeps working; only the no-sun reserve is lost.
- **The gate is harness durability on animals.** V1-alpha carries its battery in the bottom module over the harness from day one (section 7), so the alpha collars test layout B for real.

### The strap bus becomes a battery bus

With the battery at the bottom, the harness carries the pack itself, not a 5 V bus (this replaces the 5 V bus in `BOTTOM-BAY.md`):

**M8 8-pin**, not the 4-pin in `BOTTOM-BAY.md`. The charger needs the pack's thermistor, which now sits under the throat. Doubling the power conductors means one broken wire doesn't drop the pack.

| M8 pin | Wire (DIN 47100) | Signal |
| --- | --- | --- |
| 1 | white | SDA |
| 2 | brown | **BAT+** (pack voltage: LiFePO4 2.5–3.65 V on V1; Li-ion 3.0–4.2 V on V1-alpha) |
| 3 | green | GND |
| 4 | yellow | SCL |
| 5 | grey | NTC (pack thermistor) |
| 6 | pink | INT (module interrupt) |
| 7 | blue | GND |
| 8 | red | BAT+ |

- **Why not 5 V:** a 5 V bus would need a boost converter and a charger inside every battery module. A raw battery bus needs neither: the top unit's charger (BQ25798) charges the pack directly down the strap. Half an amp of charge over ~0.6 m of 22 AWG loses ~30 mV.
- **The pack's temperature** reaches the charger's TS input over pin 5, so charging stops in hardware when the pack is too cold or hot.
- **Every battery module** carries its own protection (with a fuse at the cells, because a crushed cable shorts the pack upstream of anything in the top unit) and an I2C fuel gauge that also identifies the module.
- **Camera modules** boost to 5 V for the GoPro inside the module, from their own pack.
- **The buffer cell** sits on the crest unit's system rail through its own small charger, diode-OR'd with the pack. That's a detailed-design task for the integrated board.

## 5. What this does to the boards

- **The integrated board is shaped to the crest unit**, ~55 × 125 mm, with the patch on the board. The pods hold only a piezo (and later an electrode), so they need no boards. The board drives the shell, not the other way round.
- **V1-alpha goes in a plain test box.** Dev boards can't fit a slim collar: the Connect Kit on sockets alone is ~15 mm tall. Draft 1 of the shell becomes that box. The alpha still proves what matters: GNSS, the left/right cue, the battery at the bottom and the harness on animals.
- **The carrier board is a rectangle under 100 × 100 mm** (JLCPCB's cheapest tier). It replaces the jumper wires in the alpha collars and gains what the alpha needs to test the new layout: the battery on the harness, and a left and a right cue port (`hardware/carrier/SPEC.md`).

## 6. Next steps

1. ~~Decisions~~ (done, above).
2. **Rotation test before any shell:** a strap with ~270 g on top (split crest / pods) and ~505 g at the bottom, worn by a person, then a steer. Does it stay upright? Cheap, fast, and it checks the 1.8 : 1 rule.
3. Carrier schematic (rev A2 spec: rectangle, battery and NTC on an 8-pin harness, two cue ports).
4. Draw the crest unit, ear pods and battery module in `mechanical/`; draft 1 stays as the alpha test box.
5. Integrated board outline from the crest unit.
6. Freedom-to-operate check on Halter's patents before production.

## 7. V1-alpha, the bridge to this design

| | V1-alpha (5–10 collars) | V1 (this design) |
| --- | --- | --- |
| Top | Draft-1 test box with the Connect Kit, MAX-M10S and IMU on the carrier | Crest unit with the integrated board |
| Cue | Two Qwiic Buzzers in printed ear pods, one per side, on Qwiic cables behind a protected, switched bus | Two piezos in ear pods |
| Battery | Adafruit 6600 mAh Li-ion in the bottom module, over the M8 harness | ~20 Wh LiFePO4 in the battery module |
| Charger | bq24074 on the carrier (Li-ion, 4.2 V fixed) | BQ25798 (LiFePO4, MPPT) |
| If the harness is cut | Runs from the panels in daylight (bq24074 powers OUT with no battery), off at night; the fault shows in the logs | Buffer cell carries it through the night |
