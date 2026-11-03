# firmware/radio — SX1262 Zephyr glue (op-fw-radio)

Implements **`firmware/lora/include/opencollar/radio_hal.h`** (op-fw-proto,
commit `f0a51bb` on `proto-fence-gossip` / PR #6) on Zephyr's native SX126x
driver (NCS v3.4.1). Do not fork that header — include it from
`firmware/lora/include`.

| Path | Contents |
| --- | --- |
| `include/opencollar/radio_sx1262.h` | `struct oc_radio`, open/cfg, Zephyr/mock binders |
| `src/oc_radio.c` | `oc_radio_send/recv/cad/set_power/airtime/duty/backoff/trickle` |
| `src/zephyr/` | `lora_*` backend (`CONFIG_LORA_MODULE_BACKEND_NATIVE`) |
| `src/mock/` | Host mock for limiter/scheduler tests |
| `boards/shields/wio_sx1262/` | In-repo Wio-SX1262 shield (not in Zephyr) |
| `boards/nrf9151_connectkit/` | PROPOSED Core1262 overlay |
| `samples/pingpong/` | Symmetric link test |
| `tests/host/` | CI-able unit tests |
| `docs/` | FCC, airtime table, scheduler design |
| `RUNBOOK.md` | Build/flash/pins/measurements |

This branch cherry-picks only `f0a51bb` (the header) so CI can compile; the
rest of `firmware/lora` stays on PR #6.
