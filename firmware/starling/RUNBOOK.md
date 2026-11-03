<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 openpasture contributors
-->

# Starling runbook

Low-power LoRa collar app (nRF52840 + external u-blox GNSS). Pilot milestone:
build + run the fence from **simulated GNSS**. Real GNSS and SX1262 when parts
arrive.

## Layout

| Path | Owner / role |
| --- | --- |
| `firmware/starling/` | This app (Starling engineer) |
| `firmware/core/` | Portable shared headers + `portable.mk` (sources still in `firmware/src` until op-firmware moves them) |
| `firmware/starling/stubs/lora` | Stub of op-fw-proto gossip API |
| `firmware/starling/stubs/radio` | Stub of op-fw-radio `radio_hal` |
| `firmware/src/{geofence,cue,shape,protocol}.c` | Shared portable core (do not move here) |

## Host tests (no hardware, CI)

```bash
make -C firmware/starling/tests/host
```

Suites: `geofence_fake` (scripted track → fence/cue), `fence_store`
(adopt-newer / reject-stale-unsigned / NVS reboot), `gossip` (Rook adopt,
serve-to-older, reject peer when `starling_serve` off), `ubx_nmea`, `demo`
(prints the fake-GNSS walk).

## Zephyr / nRF52840 build

Needs nRF Connect SDK (Rook uses NCS v3.4.1) and `west`:

```bash
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/starling/build.sh
# flash:
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/starling/build.sh flash
```

Default board: `xiao_ble/nrf52840` (Seeed XIAO nRF52840 + Wio-SX1262). Override
with `BOARD=...`.

If `ZEPHYR_BASE` / NCS is missing (typical cloud VM), host tests still run; the
Zephyr build is skipped with exit 2 from `build.sh`.

## Config flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `CONFIG_STARLING_GNSS_FAKE` | y | Scripted track backend |
| `CONFIG_STARLING_SERVE` | n | Multi-hop serve to Starling neighbors; off = Rook one-hop only |
| `CONFIG_STARLING_BENCH_FENCE` | y | Demo fence when NVS empty |

## Open items

- op-firmware: `firmware/ARCHITECTURE.md`, CI hook for nRF52840 image, coordinated `firmware/src` → `firmware/core` move.
- op-fw-proto: real `firmware/lora` Trickle gossip + beacon fields (`fence_seq` / hash vs existing `bver`).
- op-fw-radio: SX1262 behind `radio_hal`.
- Cody: welfare PLACEHOLDER caps (PR #2) — see PR description.
- Real MAX-M10S UART wiring when module arrives; I2C optional later.
