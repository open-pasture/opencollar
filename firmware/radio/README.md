# firmware/radio — SX1262 Zephyr glue (op-fw-radio)

Implements **`firmware/lora/include/opencollar/radio_hal.h`** (op-fw-proto,
`ab5350e` on `proto-fence-gossip` / PR #6) on Zephyr's native SX126x driver
(NCS v3.4.1). Do not fork that header — include it from `firmware/lora/include`.

| Path | Contents |
| --- | --- |
| `include/opencollar/radio_sx1262.h` | `struct oc_radio`, bind helpers, US915 defaults |
| `src/oc_radio.c` | Full `oc_radio_*` incl. init/sleep/now_us/limits |
| `src/zephyr/` | `lora_*` backend (`CONFIG_LORA_MODULE_BACKEND_NATIVE`) |
| `src/mock/` | Host mock for limiter/scheduler tests |
| `boards/shields/wio_sx1262/` | In-repo Wio-SX1262 shield (not in Zephyr) |
| `boards/nrf9151_connectkit/` | PROPOSED Core1262 overlay |
| `samples/pingpong/` | Symmetric link test |
| `tests/host/` | CI-able unit tests |
| `docs/` | FCC, airtime table, scheduler design |
| `RUNBOOK.md` | Build/flash/pins/measurements |

This branch carries the header at `ab5350e` so CI can compile; the rest of
`firmware/lora` stays on PR #6.
