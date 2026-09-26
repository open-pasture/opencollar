# Materials and strap

The CAD will be open source so anyone can print the collar. That means designing for printers people actually have, in materials that survive a cow.

## Approach: buy the strap, print the modules

Don't print the strap. Commercial cattle neck straps (~50 mm woven nylon or polyester, stainless buckle, adjustable) are cheap, proven on animals, and available from any livestock supplier. We print only the rigid parts that mount to it:

- **Top unit**: the strap passes through slots moulded into its underside and is clamped with a printed bar and screws.
- **Bay cradle**: same slot-and-clamp mount at the bottom of the strap; modules lock into it with thumbscrews.
- **Strap wires** (prototype): flexible silicone wire in a braided sleeve, fixed along the strap's non-adjusting side with stitched loops or printed TPU clips, ending in the IP68 connectors. Later: a strap with conductors woven or moulded in.

Anyone rebuilding the collar buys a standard strap and prints the rest.

## What to print each part in

| Part | Material | Why |
| --- | --- | --- |
| Top unit shell and lid | **ASA** (desktop FDM) or **PA12** (MJF/SLS service) | Rigid, UV-stable, handles heat. ASA prints on most enclosed desktop printers; PA12 from a print service or a lab machine is tougher and needs no supports |
| Bay cradle and module shells | ASA or PA12 | Takes knocks from the ground, posts and other cattle |
| Strap clamps, bumpers, strap clips, cable strain reliefs | **TPU 95A** (flexible) | Absorbs impact, grips the strap, won't crack |
| Seals | **Silicone O-rings** (bought), not printed | Printed gaskets don't seal reliably over time |

### Why not PLA or PETG

- **PLA** softens around 55–60 °C. A collar in July sun gets hotter than that, so PLA creeps and deforms. It also goes brittle outdoors.
- **PETG** handles heat better but yellows and weakens in UV over a season.
- **ASA** is essentially outdoor-grade ABS: built for sun and weather.
- **Nylon with carbon fibre** (PA-CF) is stronger still, but absorbs moisture, which makes it swell and weaken in wet pastures unless sealed. Not a first choice.

### Colour

Light colours (white, light grey, tan). A dark shell in full sun runs much hotter, which is bad for the battery (LiFePO4 is happiest below ~45 °C), the electronics, and the material.

## Printing guidelines for the open design

- **Walls:** at least 2.5–3 mm (6 perimeters at 0.4 mm), with ribs rather than solid thickness.
- **Infill:** 40 % or more in load-bearing areas; 100 % around screw bosses and the strap slots.
- **Screws:** brass heat-set inserts for every screw that gets opened more than once.
- **Sealing:** O-ring groove in the lid, designed for the printer's tolerance; sealed flat faces sanded or vapour-smoothed where the O-ring sits.
- **Print orientation:** noted per part, so layer lines never run across a load path (for example, strap slots printed so layers wrap around the slot).
- **Test prints:** each release is checked for water (submersion), drops and heat before it's published.

## Questions for the fabrication partner

- Which printers: desktop FDM (which brand, enclosed or not), resin, MJF/SLS?
- Which materials does he already run: ASA, PC, PA12, TPU?
- Build volume (the top unit is roughly 130 × 90 × 45 mm)?
- Can he do heat-set inserts and a submersion test at the lab?
