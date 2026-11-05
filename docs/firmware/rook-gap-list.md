# Rook collar gap list (2026-11-02, CT)

Rook = nRF9151 LTE-M + GPS base collar; receives signed fences from server, hands them to Starlings over LoRa (one-hop star, `protocol/v2/lora.md`), relays telemetry up.
Source: local checkout `/workspace/opencollar` @ ca73590 (main) + uncommitted MCUboot work in the tree (sysbuild.conf, sysbuild/mcuboot.overlay, partitions_mcuboot.dtsi). Remote PRs #1-#5 exist; #2 (welfare) is open, not merged; #5 is CAD only. No repo changes made by me.
Legend: DEF = defined in repo docs; HAVE = alpha part on hand per BUILD-LOG/orders; MISSING = not in repo / not owned. "Verified" = read in a file; everything else is assumed.

## 1. Electronics BOM

| Item | Alpha (bench/prototype) | V1 production target | Status | Evidence |
|---|---|---|---|---|
| nRF9151 board/SiP | Makerdiary nRF9151 Connect Kit (nRF9151-LACA, mfw 2.0.4, BQ25180, TPS63901, nano-SIM slot, U.FL LTE+GPS) x1 | nRF9151 SiP on custom board | HAVE x1 (need 2nd for 2 Rooks: MISSING) | hardware/bom.md; BUILD-LOG.md L8-18 |
| GNSS receiver | nRF9151 built-in GNSS (fix 2.2 m verified 2026-09-25); MAX-M10S breakout for comparison | u-blox MAX-M10S (MAX-F10S upgrade) | built-in HAVE; M10S ordered, last log says not arrived (Oct 2) | V1-DESIGN.md L57-58; BUILD-LOG.md L20-22, L372; orders-2026-09-26.md |
| GNSS antenna | 1575R-A ceramic patch U.FL; Adafruit 960 active ref antenna | 25x25 mm patch, >=60 mm ground plane | HAVE (patch); prod DEF | bom.md; prototype-cart.md; V1-DESIGN L59 |
| LTE antenna | Flexible adhesive U.FL | Flex LTE antenna on far edge | HAVE; DEF | bom.md; V1-DESIGN L62 |
| **LoRa radio** | none | none in V1-DESIGN (lora.md defines the air plan only) | **MISSING** - add SX1262 915 MHz on SPI (e.g. Wio-SX1262 / Core1262-HF; op-office pricing) | protocol/v2/lora.md L39-47 (902-928 MHz, 500 kHz SF8); not in bom.md/V1-DESIGN |
| **LoRa antenna 915 MHz** | none | none | **MISSING** (also no placement in CAD; op-maker) | - |
| SIM | Hologram Hyper eUICC nano-SIM (ordered; activation not logged) | Soldered MFF2 eSIM, multi-carrier | ordered/likely HAVE, **not activated** (assumed); prod DEF | orders-2026-09-26.md; BUILD-LOG L16, L371; V1-DESIGN L61 |
| Battery | Adafruit 353 6600 mAh Li-ion (owned), 1200 mAh LiPo (owned); 2x Adafruit 1781 18650 pending Cody approval (plan of record per bom.md) | 2x 26650 LiFePO4 (~22 Wh) | HAVE (Li-ion); 18650s pending; prod DEF | bom.md; V1-DESIGN L66 |
| Charger / solar | Kit BQ25180 (onboard); Adafruit bq24074 + 10K NTC; 2x Voltaic P124 panels | TI BQ25798 MPPT, charge-enable held off in HW; 2x ~0.8 W ETFE | HAVE (alpha); prod DEF | BUILD-LOG L17, L54-55; orders; V1-DESIGN L67-68 |
| Fuel gauge / battery ADC | none | MAX17260 coulomb counter | **MISSING** on alpha (deferred); prod DEF. Interim: nRF9151 ADC/divider or modem `%XVBAT` (assumed workable, not tested) | V1-DESIGN L69; BUILD-LOG L55 (fuel gauge deferred) |
| Buzzer | SparkFun Qwiic Buzzer BOB-24474 (I2C 0x34) | piezo | HAVE; prod DEF | bom.md; V1-DESIGN L129 |
| IMU | Adafruit ISM330DHCX | LSM6DSV16X or BMI270 | HAVE (ordered/arrived), no driver; prod DEF | prototype-cart.md; V1-DESIGN L63 |
| SPI flash, hall sensor, status LED | deferred | DEF | MISSING on alpha | BUILD-LOG L55; V1-DESIGN L71, L148 |
| BLE | none (nRF9151 has no BLE, confirmed in Nordic PS) | nRF54L15 V1-beta only | n/a for pilot | V1-DESIGN; op-firmware-notes.md |
| Cables | Qwiic-jumper cables, MX1.25 pigtails, USB-C | - | HAVE (orders); USB-C data cable on "still needed" list in bom.md (assumed resolved) | bom.md; prototype-cart.md |

## 2. Firmware status

| Subsystem | Status | Notes / evidence |
|---|---|---|
| GNSS fix | DONE | firmware/src/app.c; on-board fix verified |
| Geofence + shapes + slots | DONE | geofence.c, shape.c, slots.c |
| Buzzer / cue | DONE | buzzer.c, cue.c (buzzer wiring on bench not logged as tested) |
| Console / provisioning | DONE | console.c, provision.c |
| Storage (NVS) | DONE | store_nvs.c |
| Boundary signature (Ed25519, herd_id) | DONE | command.c, protocol.c; host tests |
| MCUboot + merged.hex | IN PROGRESS | uncommitted sysbuild in tree, dev key only (sysbuild.conf); `/workspace/mcuboot-merged-hex.patch` does NOT exist; not flashed |
| v1 HTTPS reporting | MISSING | no HTTP client in src; protocol/v2/http.md is v2; v1 = Record A option 3 |
| Boundary download over LTE | MISSING | main.c waits for SIM; boundary pasted on console |
| Battery reading | MISSING | no ADC/fuel-gauge code |
| LoRa SX1262 driver | MISSING | no LoRa in src/prj.conf |
| Fence-fragment handoff (beacon/fragment/need, v2 lora.md) | MISSING (spec only) | lora.md frame 22, 13-byte header |
| Welfare caps | IN MAIN (PR #2) | `WELFARE_DEFAULT_*` in `cue.h` (3 / 3 / 24 h); Starling wires via welfare hooks |
| PSM / eDRX power mgmt | MISSING | grep: no PSM/eDRX config |
| OTA firmware over LTE-M (FOTA) | MISSING | needs MCUboot + slot1 + download client |
| Watchdog | MISSING | no WDT in src |
| Reset / fault logging | MISSING | no reset-reason / coredump |
| IMU | MISSING | not in src |
| Zephyr build in CI | MISSING | CI runs host tests only |

## 3. Plan to close gaps (max aggression)

| Gap | Owner | Target |
|---|---|---|
| MCUboot merged.hex draft PR, flash on kit, verify boot | op-firmware (Cody flashes if no remote bench) | PR Tue Nov 3; on-board Fri Nov 6 |
| Zephyr build in CI | op-firmware | Wed Nov 4 |
| Watchdog + reset-reason/fault log | op-firmware | Wed Nov 4 |
| Battery reading (interim ADC / %XVBAT; MAX17260 later) | op-firmware | Thu Nov 5 (host); bench Fri Nov 6 |
| Welfare caps on by default (PR #2 merged) | op-firmware | Done on main; Starling stacked PR wires hooks |
| v1 HTTPS reporting + boundary download | op-fw-rook-lte | host/mock server Thu Nov 5; live needs SIM |
| Activate Hologram SIM, insert, confirm attach | Cody | Tue Nov 3 (blocks all live LTE tests) |
| PSM/eDRX | op-fw-rook-lte | Fri Nov 6 (PPK2 not owned: power numbers unverified) |
| FOTA over LTE-M (dev key) | op-fw-rook-lte | code Fri Nov 6; live test week of Nov 9 |
| Fence fragment protocol + 2-radio host simulator | op-fw-proto | sim passes Wed Nov 4 |
| SX1262 driver (Zephyr lora API) on Connect Kit SPI | op-fw-radio | host/compile Thu Nov 5; on-air Sat Nov 7 if parts by Fri Nov 6 |
| Rook beacon/downlink scheduler | op-fw-proto + op-fw-radio | Fri Nov 6 |
| Starling receive side | op-fw-starling | Fri Nov 6 (sim) |
| Order SX1262 x2 + 915 MHz antennas + 2nd Connect Kit | op-office (Cody approves card) | order Mon/Tue Nov 2-3; arrive Fri Nov 6 (assumed 2-day) |
| Confirm free SPI+BUSY/DIO1/RST pins on kit header | op-firmware | Tue Nov 3 (not yet verified) |
| LoRa antenna placement in top unit | op-maker | week of Nov 9 |
| On-air Rook->Starling signed handoff | op-fw-radio + Cody (bench) | Sat-Sun Nov 7-8; fallback Wed Nov 11 |
| Production key (replace MCUboot dev key), BQ25798/LiFePO4/MAX17260 board | op-firmware / Cody | before any field build; V1-beta |

## Top 5 gaps
1. No LoRa radio or antenna anywhere in the Rook BOM or firmware; SX1262 + 915 MHz antenna must be bought and pins checked.
2. No cellular uplink: no HTTPS reporting, no boundary download, SIM not activated.
3. No bootloader on hardware yet, so no FOTA; MCUboot is uncommitted, dev-key only.
4. No battery reading, PSM/eDRX, or watchdog; no fuel gauge on the alpha.
5. Welfare caps are in main (PR #2); Starling app must keep `WELFARE_DEFAULT_*`.
