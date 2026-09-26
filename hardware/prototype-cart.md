# Prototype collar cart (simplified 2026-09-26)

The first build proves four things: GPS accuracy, the fence and cue, telemetry, and the physical collar (shell, strap, balance). Everything else waits for the second build.

Already owned: nRF9151 Connect Kit, LTE antenna, small U.FL GPS patch, SparkFun Qwiic Buzzer, 1200 mAh LiPo, jumper wires.

## Order (6 checkouts)

### DigiKey
| Item | Part | Qty | $ |
| --- | --- | --- | --- |
| SparkFun MAX-M10S GNSS breakout (SMA, Qwiic) | 1568-18037-ND | 1 | 45.95 |
| M6 screw-in ePTFE vent | 1754-1548-ND (VENT-PS2NGY-O8001) | 1 | 3.31 |

### Adafruit
| Item | Product | Qty | $ |
| --- | --- | --- | --- |
| Universal USB/DC/Solar charger, bq24074 (4.2 V fixed in hardware, 6–10 V solar in) | [4755](https://www.adafruit.com/product/4755) | 1 | 14.95 |
| Li-ion pack 3.7 V 6600 mAh, protection circuit, JST-PH | [353](https://www.adafruit.com/product/353) | 1 | 24.50 |
| 10K NTC thermistor (charge temperature cutoff) | [372](https://www.adafruit.com/product/372) | 1 | 4.00 |
| ISM330DHCX 6-DoF IMU, STEMMA QT/Qwiic (industrial, −40 to 105 °C) | [4502](https://www.adafruit.com/product/4502) | 1 | 19.95 |
| GPS active antenna 28 dB, SMA, 5 m cable (reference antenna for tests) | [960](https://www.adafruit.com/product/960) | 1 | 21.50 |
| SMA to U.FL adapter (existing patch on the M10S) | [851](https://www.adafruit.com/product/851) | 1 | 3.95 |
| STEMMA QT/Qwiic cable 100 mm | [4210](https://www.adafruit.com/product/4210) | 2 | 0.95 |
| STEMMA QT/Qwiic to female sockets 150 mm | [4397](https://www.adafruit.com/product/4397) | 2 | 1.25 |
| M3 × 4 brass heat-set inserts (50) | [4255](https://www.adafruit.com/product/4255) | 1 | 5.95 |

Adafruit rejects automated cart adds; add these by hand.

### Amazon
| Item | ASIN | $ |
| --- | --- | --- |
| M3 304 stainless screw assortment | B0GHMM79M9 | 8.99 |
| 2 mm silicone O-ring cord | B00QVB0ZG6 | 15.39 |
| 1.25 mm 2-pin connector pigtails (pack to the kit's battery socket) | B013JRWCBU | 6.99 |
| 22 AWG silicone wire kit | B07G2JWYDW | 15.99 |
| Adhesive-lined heat shrink kit | B0BVVMCY86 | 13.99 |

### Voltaic
| Item | Part | Qty | $ |
| --- | --- | --- | --- |
| 1.2 W 6 V ETFE panel, 66 × 113 mm | P124 | 2 | 14.00 |

### Heritage Animal Health
| Item | $ |
| --- | --- |
| 48" cow neck strap, 1-3/4" double-thick nylon, blue | 23.10 |

### Hologram
LTE-M SIM, promo code FREEPILOTSIM (confirm nano size).

**Approximate total: ~$260** plus shipping and tax. Qwiic cable prices are approximate.

## Not bought online
- About 500 g of steel for the ballast (flat bar or large fender washers).
- Superglue to join the O-ring cord.
- Soldering iron, solder, multimeter, flush cutters if you don't have them.
- Print material, from our fabrication partner.

## How it wires up (no configuration)
Panels (parallel) → bq24074 solar input. Li-ion pack → bq24074 battery plug, and the same pack → the nRF9151 kit's battery socket via a 1.25 mm lead. Thermistor taped to the pack. Every charger defaults to 4.2 V, correct for Li-ion, so nothing needs setting.

## Deferred to the second build
| Item | Why later |
| --- | --- |
| TI BQ25798 board + LiFePO4 cells, holders, BMS | LiFePO4 arrives with the V1-beta custom board |
| Power Profiler Kit II | Measure once firmware is power-optimized |
| Camera module (GoPro, microSD, power bank, mount, cables) | Add-on, not core |
| Wired-strap harness (M8 cordset + 2 sockets) | Only needed for powered modules |
| Piezo + driver | No louder than the Qwiic buzzer |
| Hall sensor + magnets | Product nicety |
| SPI flash, fuel gauge kit | Not needed yet |
