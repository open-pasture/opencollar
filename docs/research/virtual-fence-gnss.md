# How commercial virtual-fence collars do GNSS

Researched 2026-09-25. "Confirmed" means stated by the company, a manual, or a published study. "Inferred" means our best reading of indirect evidence.

## By company

| Company | GNSS | Antenna / mechanical | Power | Link | Accuracy claims |
| --- | --- | --- | --- | --- | --- |
| **Halter** (NZ) | "GPS-enabled"; chip unknown. Patent on GPS module power management suggests a separate GNSS module (inferred) | Solar panels on top, housings on each side of the neck, 912 g bottom counterweight, ~1.4 kg total (confirmed) | Solar | LoRa to Halter's own towers; Starlink direct-to-satellite for beef (2026) | Not published |
| **Nofence** (Norway) | Multi-constellation; several fixes per second near the boundary, lower accuracy far from it (confirmed claim) | Housing on top, chains to strap, side solar panels, 1.3 kg (C2) | 72 Wh Li-ion + solar | 2G/4G; BLE beacons in shelters switch GNSS off under roofs | 2025 study: as accurate as a Lotek research collar or better, and more precise; accuracy tracked satellite count and dropped under canopy |
| **Monil** (Norway; US office in Kansas City) | nRF9160 (confirmed), so most likely its built-in GPS L1 + QZSS (inferred). Closest match to our V0 | 1 kg, lightest on the market by their claim | Li-poly + solar, IMU | LTE-M/NB-IoT, no towers | Not published |
| **Gallagher eShepherd** (AU, ex-CSIRO) | Chip unknown | Solar unit on top, counterweight under the chin | LiFePO4, 7–10 year battery claim | Cellular or LoRa base station; fence stays active 24 h without a link | **±1 m within 20 m of the fence** (confirmed claim) |
| **Vence / Merck** | GPS + GLONASS + BeiDou + Galileo, internal patch (confirmed, manual) | Counterweight near the bottom of the neck | Replaceable D-cell (Tadiran TL-4930), 6–9 months, no solar | LoRaWAN base station covering 5,000–10,000 acres | Not published |
| **Corral Technologies** (NE) | Unknown | Two solar panels | Solar | Cellular / satellite | Not published |

## What's inside (from FCC internal photos, retrieved 2026-09-25)

| Collar | GNSS | GNSS antenna | Other key parts |
| --- | --- | --- | --- |
| **Halter P5** (FCC 2A9LG-P5, filed 2025) | **u-blox M10 chip (UBX-M10050-KB)**, chip-down on the board | Separate `GPS` antenna feed (a `5G` cellular antenna is labelled too) | ST STM32WBA65 (MCU + BLE), Semtech SX1262 LoRa, Winbond 256 Mbit flash |
| **Vence Cattle Rider** (FCC 2AX22-VNC0100201, filed 2021) | **u-blox ZOE-M8B** (M8 system-in-package, low-power Super-E mode) | ~18 mm ceramic patch on the main board, U.FL alternative (J2) | ST MCU, LoRa radio under a shield, piezo buzzer, lithium cell on the board |
| **Nofence C2** (FCC 2A3V8C2, filed 2022) | Chip-down receiver next to the patch; marking not readable in the photos | **~25 mm ceramic patch centred on a large ground plane** at the crown of the board | u-blox SARA-R412M (LTE-M / NB-IoT / 2G), Ethertronics cellular antenna, Kingstate buzzer, supercapacitor bank + transformer for the pulse, Atmel MCU, solar input |

Takeaways:
- **Everyone uses u-blox**, single-band L1: M8 in 2021, M10 in Halter's 2025 collar. Nobody has moved to L5.
- **Antennas are ordinary 18–25 mm ceramic patches.** Nofence gives theirs the most ground plane. Nothing exotic.
- Schematics and block diagrams are confidential on all three filings.

## Independent accuracy data

Static field test of 24 Nofence C2 collars against 12 Lotek LiteTrack 420 research collars (2024, open access, doi:10.1186/s40317-025-00417-1):
- **Real accuracy error: ~5.4–5.5 m in grassland and shrubland, ~7.6 m in forest** (59 % canopy cover), measured against RTK-surveyed points.
- **Precision error: 4.98 m** for Nofence vs 8.75 m for Lotek.
- Nofence used more than twice as many satellites as Lotek, and that is what drove its advantage.
- Errors varied noticeably from day to day, even at the same spot.

**So the real-world bar is about 5 m, not the ±1 m in marketing claims.** A collar that holds 2–3 m in the open and under 5 m under trees would be clearly better than the market.

## What the industry does

1. **Antenna on top, weight on the bottom.** The GNSS antenna and solar sit on top of the neck, held there by a 0.9–1.5 kg counterweight under the chin. Every major vendor does this.
2. **Single-band L1, multi-constellation**, consumer-grade receivers. Nobody publicly claims L5 or RTK. eShepherd's ±1 m is the best accuracy claim.
3. **Adaptive fix rate.** Slow and low-accuracy far from the fence, ~1 Hz or faster within ~20 m.
4. **GNSS off in shelters**, using BLE beacons, instead of fighting for a fix under a roof.
5. **Fence logic runs on the collar** and keeps working without a link.
6. **Big energy budget.** Solar plus 20–70 Wh battery; Vence (D-cell) is the exception.

## Sources

- FCC internal photos: https://fccid.io/2A9LG-P5 (Halter P5), https://fccid.io/2AX22-VNC0100201 (Vence), https://fccid.io/2A3V8C2 (Nofence C2)
- Nofence accuracy study: https://link.springer.com/article/10.1186/s40317-025-00417-1

- Halter: https://www.halterhq.com/articles/a-closer-look-at-the-halter-collar, https://www.halterhq.com/en-us/patents, https://aws.amazon.com/blogs/industries/the-cow-collar-wearable-how-halter-benefits-from-freertos/, https://www.drovers.com/news/halter-launches-world-first-virtual-fencing-satellite
- Nofence: https://www.nofence.com/en-us/knowledge-hub/articles/how-the-virtual-fence-works/, https://www.nofence.com/en-us/nofence-for-cattle/product-and-pricing/, https://link.springer.com/article/10.1186/s40317-025-00417-1, https://link.springer.com/article/10.1186/s40317-024-00389-8
- Monil: https://www.nordicsemi.com/Nordic-news/2024/11/Monil-Collar-employs-nRF9160-SiP-and-nRF52833-SoC
- eShepherd: https://eshepherd.com/faq/
- Vence: https://manuals.plus/vence/cattle-rider-v3-livestock-collar-for-tracking-and-managing-cattle-manual
- Multi-vendor overview: https://extension.arizona.edu/publication/foundations-virtual-fencing-specifics-collar-deployment-company
- Modules: https://www.u-blox.com/en/product/max-m10-series, https://www.cnx-software.com/2026/07/06/u-blox-f11-low-power-dual-band-gnss-chips-and-modules-consume-just-7mw-in-leap-mode/, https://www.quectel.com/news-and-pr/gnss-lc76g-launch/, https://www.quectel.com/product/gnss-lc29h/
