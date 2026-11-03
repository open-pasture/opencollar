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

`make` must be installed (CI installs it explicitly). Then:

```bash
make -C firmware/starling/tests/host
```

Suites: `geofence_fake` (scripted track → fence/cue), `fence_store`
(adopt-newer / reject-stale-unsigned / NVS reboot), `gossip` (Rook adopt,
serve-to-older, reject peer when `starling_serve` off), `ubx_nmea`, `demo`
(prints the fake-GNSS walk).

## Zephyr / nRF52840 build

Needs nRF Connect SDK **v3.4.1** and `west`. **Set `ZEPHYR_BASE` explicitly** —
`firmware/starling/build.sh` only falls back to `/opt/nordic/ncs/v3.4.1/zephyr`
when it is unset.

Verified on NCS v3.4.1 (commit `c53eb49`): **0 warnings**, FLASH **98336 B** of
788 KB (**12.19%**), RAM **46716 B** of 256 KB (**17.82%**). From the repo root:

```bash
export PATH=$HOME/.nrfutil/bin:$PATH
export ZEPHYR_BASE=$HOME/ncs/v3.4.1/zephyr
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- west build -b xiao_ble/nrf52840 firmware/starling --build-dir /workspace/starling-build -p
```

Wrapper (same board; still set `ZEPHYR_BASE` first):

```bash
export ZEPHYR_BASE=$HOME/ncs/v3.4.1/zephyr   # or your NCS path
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/starling/build.sh
# flash:
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/starling/build.sh flash
```

Default board: `xiao_ble/nrf52840` (Seeed XIAO nRF52840 + Wio-SX1262). Override
with `BOARD=...`.

## Default `prj.conf`

| Flag | Default | Meaning |
| --- | --- | --- |
| `CONFIG_STARLING_GNSS_FAKE` | **y** | Fake GNSS on (scripted track) |
| `CONFIG_STARLING_SERVE` | **n** | Multi-hop serve off (Rook one-hop only) |
| `CONFIG_STARLING_BENCH_FENCE` | **y** | Demo fence when NVS empty |

## Open items

- op-firmware: `firmware/ARCHITECTURE.md`, CI west hook for nRF52840 image (set
  `ZEPHYR_BASE` explicitly in that job), coordinated `firmware/src` →
  `firmware/core` move.
- op-fw-proto: real `firmware/lora` Trickle gossip + beacon fields (`fence_seq` /
  hash vs existing `bver`).
- op-fw-radio: SX1262 behind `radio_hal`.
- Cody: welfare PLACEHOLDER caps (PR #2) — see PR description.
- Real MAX-M10S UART wiring when module arrives; I2C optional later.
