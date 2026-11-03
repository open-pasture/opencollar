# firmware/radio — SX1262 Zephyr glue (op-fw-radio)

Implements the portable `radio_hal.h` sketch from op-firmware's architecture
note on Zephyr's native SX126x driver (NCS v3.4.1).

| Path | Contents |
| --- | --- |
| `include/radio_hal.h` | Proposed HAL (canonical will live in `firmware/lora/`) |
| `src/` | Airtime, duty/dwell, backoff, scheduler, HAL core |
| `src/zephyr/` | `lora_*` backend (`CONFIG_LORA_MODULE_BACKEND_NATIVE`) |
| `src/mock/` | Host mock for limiter/scheduler tests |
| `boards/shields/wio_sx1262/` | In-repo Wio-SX1262 shield (not in Zephyr) |
| `boards/nrf9151_connectkit/` | PROPOSED Core1262 overlay |
| `samples/pingpong/` | Symmetric link test |
| `tests/host/` | CI-able unit tests |
| `docs/` | FCC, airtime table, scheduler design |
| `RUNBOOK.md` | Build/flash/pins/measurements |

Does **not** edit `firmware/lora`, `firmware/rook`, `firmware/starling`, or
the protocol library beyond this proposed header.
