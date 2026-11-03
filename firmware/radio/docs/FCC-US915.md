# US 915 MHz compliance assumptions (bring-up)

## Regime implemented in this HAL

**FCC Part 15.247(a)(1) — frequency hopping** for the 125 kHz SF7–SF10 preset:

| Rule | HAL behaviour |
| --- | --- |
| Hop across channels (system design needs ≥ 50 channels for the classic hop path) | Channel selection is protocol-owned; HAL accounts dwell **per `freq_hz`** |
| ≤ 400 ms dwell on one channel in any 20 s | `dwell_limit_us` / `dwell_window_ms` (defaults 400 ms / 20 s); send → `RHAL_E_BUDGET` |
| Conducted power | `tx_power_cap_dbm` default **+14 dBm** (conservative until grant/antenna measured); SX1262 silicon ceiling +22 |

Additional **software** limits (not FCC numbers — herd fairness / battery /
beacon+gossip headroom):

| Limit | Default | Effect |
| --- | --- | --- |
| `airtime_budget_us_per_h` | 36 s/hour (~1 %) | `RHAL_E_BUDGET` when spent |
| `min_tx_gap_ms` | 100 ms | rate-limit between our own sends |
| `max_frame_airtime_us` | 400 ms | refuse frames that cannot meet dwell |

CAD before every TX (unless `skip_cad` in tests) implements listen-before-talk.

## Not the default: Plan 1 / 15.247(a)(2)

Protocol v2 `US915_500` (SF8 / 500 kHz / digital modulation, no hop, PSD
≤ 8 dBm in any 3 kHz, +20 dBm conducted) remains the **one-hop star** plan in
`protocol/v2/lora.md`. Switching the HAL preset to 500 kHz is a Kconfig /
`rhal_cfg.bw_khz_code = 2` choice. **op-firmware must decide** which preset
ships first; measured 6 dB bandwidth and PSD on the real module+antenna are
still open (`lora.md` open question 2).

## Open measurements (boards arrive)

See RUNBOOK.md measurement plans: conducted power, occupied bandwidth, PSD,
dwell under gossip load, and average current for RX-window schemes.
