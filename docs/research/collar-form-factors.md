# Collar form factors: Halter, Nofence, Monil

Researched 2026-09-26. **Confirmed** = stated by the company, a patent, FCC or a peer-reviewed paper. **Inferred** = our reading. The Halter P5 FCC exhibits couldn't be reached (every mirror blocked automated access), so its chip list in `virtual-fence-gnss.md` stays as recorded there.

## Halter (P4/P5)

| Item | Finding | Status |
| --- | --- | --- |
| Layout | One top unit: two side pods joined by a narrower flexible bridge over the top of the neck. A perforated strap runs down from each pod and clips into a separate counterweight under the throat | Confirmed (design patent drawings, collaring guide) |
| Mass | Device on the neck 488 g, counterweight 912 g, 1.40 kg total. **Bottom : top = 1.87** | Confirmed (Verdon et al. 2026) |
| Counterweight | Shipped in its own box and clipped on at a chosen hole, which sets the collar size. Collars charge in the sun without it. Almost certainly dead mass, not battery. An earlier patent describes ≥ 1 kg of steel shot or sand | Dead mass: inferred (strongly) |
| Sizing | One top unit fits every animal; size is set at the counterweight | Confirmed |
| Solar | On top of the pods, under "bulletproof glass" that forms the outer face. Sources disagree between two and four panels; the design patent shows one window per pod. Wattage not published | Placement: confirmed |
| Battery | Patent: one LiFePO4 or Li-ion cell (3–4.2 V). A 2018 patent shows one battery per side under its panel. Capacity not published; small battery plus daily solar (inferred from 488 g) | Chemistry: patent |
| Cues | Two speakers, one per side, for left/right cues, 2,700 Hz. Vibration. Pulse 0.1 J default, 0.45 J max, not directional | Confirmed |
| Electrodes | One pair on opposite sides of the neck, 50–300 mm apart (patent) | Patent |
| Pulse hardware | Transformer 23.5 × 29.5 × 15.5 mm, 19.45 g, 1:20, run saturated; 3–20 µF capacitors | Patent |
| Sealing | "Weather-resistant, dust-sealed", tumble-tested on steel plate. No IP rating published | Confirmed |
| Dimensions | Not published. Bottom view in the design patent is ~5.4 × as long as wide | Unknown |

**Halter's patents cover this shape.** US design patent USD1089882S protects the look of the pods-and-bridge top unit. Utility patents cover the stabiliser (AU2022100012A4) and the pulse and electrodes (US20240156058A1, US11937578B2). We can match their numbers (mass, thickness, sizing at the counterweight), but not their appearance, and the pulse design needs a patent check before we build one.

## Nofence C2.5

| Item | Finding |
| --- | --- |
| Layout | One housing below the neck with battery, electronics and solar panel; metal chains carry the pulse |
| Size and mass | 15.3 × 14.5 × 5.4 cm box; ~1.5 kg on the animal |
| Battery | Li-ion 72 Wh, removable, 11–12 h wired charge; 6–12 months |
| Other | IP67, −20 to 60 °C, 82 dB at 1 m, LTE-M / 2G / BLE, GPS + GLONASS, silicone straps |

## Monil

| Item | Finding |
| --- | --- |
| Layout | One polycarbonate puck on top of the neck with the solar cell sealed inside; TPU strap; an aluminium weighted lock under the neck is the counterweight |
| Mass and fit | "Just over 2 pounds" including the lock (~0.95–1 kg); 75–130 cm neck circumference |
| Electronics | nRF9160 + nRF52833, Li-poly battery |
| Energy | Solar covers a grazing season; hand charging in deep forest or winter |

## What makes Halter slim

1. Most of the mass is a dumb weight: electronics are 35 % of the collar.
2. The volume is split into two thin side pods rather than one box.
3. Parts that must be left and right (speakers, electrodes) set the layout.
4. The panel is the lid: no separate panel housing.
5. A small, deliberately inefficient pulse stage.
6. A small battery with daily solar, against Nofence's 72 Wh.
7. All sizing hardware sits at the counterweight, so the top unit carries no buckles.

## Sources

- Mass split: Verdon et al. 2026, *Animal*, https://www.sciencedirect.com/science/article/pii/S1751731126000649
- Design patent USD1089882S: https://patents.google.com/patent/USD1089882S1/en
- Collaring guide: https://intercom.help.halter.io/en/articles/13541853-get-set-for-collaring-pdf-collaring-guide
- System overview and welfare charter: https://intercom.help.halter.io/en/articles/16538366-system-overview
- Patents: https://www.halterhq.com/en-us/patents, https://patents.google.com/patent/AU2022100012A4/en, https://patents.google.com/patent/US20240156058A1/en, https://patents.google.com/patent/US11937578B2/en
- Halter technology page: https://www.halterhq.com/en-us/our-technology
- Press: https://www.canadiancattlemen.ca/features/virtual-fencing-cattle-collars/, https://www.forbesindia.com/article/global-game/cross-border/craig-piggott-fresh-pastures/2993750/1, https://www.dtnpf.com/agriculture/web/ag/livestock/article/2026/04/30/halters-satellite-connected-cattle
- Nofence archived spec page: https://web.archive.org/web/20260422022615id_/https://www.nofence.com/en-ie/nofence-for-cattle/product-and-pricing/
- Monil: https://www.monil.com/us/product, https://www.nordicsemi.com/Nordic-news/2024/11/Monil-Collar-employs-nRF9160-SiP-and-nRF52833-SoC
- Extension overview: https://extension.arizona.edu/publication/foundations-virtual-fencing-specifics-collar-deployment-company
