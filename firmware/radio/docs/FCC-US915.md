# US 915 MHz pilot radio defaults (bench / private-farm)

**Not a compliance claim.** These are pilot defaults for bring-up, bench
tests, and private-farm experiments. Certification measurements and legal
review are Cody's responsibility before any field deployment. Do not treat
this document as FCC advice.

## Pilot default (configurable)

| Setting | Pilot default | Notes |
| --- | --- | --- |
| Band plan intent | 15.247(a)(1)-style frequency hopping | Software dwell accounting only |
| Bandwidth | 125 kHz (`bw_khz_code = 0`) | Kconfig / `oc_radio_cfg` |
| Spreading factor | SF8 (SF7–SF10 supported) | |
| Coding rate | 4/5 | |
| TX power cap | **+14 dBm** | Until conducted power is measured on the real module+antenna; SX1262 silicon can go higher |
| Soft hourly airtime budget | ~1 % of an hour | Fairness / battery / gossip headroom — not a regulatory number |
| Min TX gap | 100 ms | Software rate limit |
| Per-channel dwell accounting | 400 ms / 20 s window | Matches the hopping dwell figure for planning; not a lab result |

HAL behaviour: CAD before TX; refuse sends that would exceed the configured
hourly budget (`ERR_DUTY`), min gap (`ERR_GAP`), or max frame airtime
(`ERR_AIRTIME`).

## Alternate preset (not default)

Protocol v2 Plan 1 (`US915_500`: SF8 / 500 kHz / 15.247(a)(2)-style digital
modulation) can be selected later via `bw_khz_code = 2` / Kconfig
`RADIO_BW_KHZ_CODE`. Keep it off until op-firmware chooses it and the
hardware path is characterized.

## Measurement plans before any field use

See RUNBOOK.md (conducted power, occupied bandwidth / PSD, dwell under load,
average current). Results go to Cody for certification planning — this tree
does not declare a pass/fail against Part 15.
