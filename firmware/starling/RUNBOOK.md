<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 openpasture contributors
-->

# Starling runbook

Low-power LoRa collar app (nRF52840 + external u-blox GNSS). Pilot milestone:
build + run the fence from **simulated GNSS**. Real GNSS and SX1262 when parts
arrive.

**Merge order (op-firmware):** PR #6 (proto) → #12 (rook) → **#9 (this) last**.

## Layout

| Path | Owner / role |
| --- | --- |
| `firmware/starling/` | This app |
| `firmware/lora/` | PR #6 — `oc_radio_*`, `oc_fh_node_*`, `oc_fh_freshness_t` |
| `firmware/starling/pending_opencollar/` | **TEMPORARY** freshness-only shim until #6 merges — then delete |
| `firmware/core/welfare.h` | Cue gate hooks only (no numeric caps; PR #2) |
| `firmware/src/{geofence,cue,…}` | Shared portable core (do not move here) |

Starling does **not** ship `radio_hal.h` / `fence_gossip` stubs. The app calls
`oc_fh_node_init` / `oc_fh_node_poll` / `oc_fh_inject_local` and supplies
`oc_radio_t` + the NVS store.

## Host tests

`make` must be installed. Host gossip tests fetch PR #6 into
`tests/host/.deps/` (gitignored):

```bash
make -C firmware/starling/tests/host
# optional: PROTO_REF=origin/cursor/proto-fence-gossip-c865 make -C firmware/starling/tests/host deps
```

Suites: `geofence_fake`, `fence_store` (incl. **fence_seq high-water** across
reboot), `ubx_nmea`, `demo`, `gossip_hwm` (links PR #6 `oc_fh_*` + sim).

Shared CI: op-firmware `firmware-build.yml` (Starling no longer ships its own
workflow).

## Zephyr / nRF52840 build

Set `ZEPHYR_BASE` explicitly — `build.sh` only falls back to
`/opt/nordic/ncs/v3.4.1/zephyr` when unset.

Verified on NCS v3.4.1 (commit `c53eb49`): **0 warnings**, FLASH **98336 B** of
788 KB (**12.19%**), RAM **46716 B** of 256 KB (**17.82%**). From the repo root:

```bash
export PATH=$HOME/.nrfutil/bin:$PATH
export ZEPHYR_BASE=$HOME/ncs/v3.4.1/zephyr
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- west build -b xiao_ble/nrf52840 firmware/starling --build-dir /workspace/starling-build -p
```

When `firmware/lora` is present (after #6), CMake links `oc_fh_*` and defines
`STARLING_HAS_LORA`. Otherwise it uses `pending_opencollar` (freshness only;
gossip disabled).

## Default `prj.conf`

| Flag | Default | Meaning |
| --- | --- | --- |
| `CONFIG_STARLING_GNSS_FAKE` | **y** | Fake GNSS on |
| `CONFIG_STARLING_SERVE` | **n** | Maps to `starling_serve` / `OC_FH_STARLING_SERVE_DEFAULT` |
| `CONFIG_STARLING_BENCH_FENCE` | **y** | Demo fence when NVS empty |

## Persistence

NVS ids: active fence (`0x40`), **fence_seq high-water** (`0x43`). Adopt only
`verified && fence_seq > hwm`. Reboot cannot roll back to an older signed fence.
When op-fw-proto publishes the official store hook, switch to it and drop the
Starling-local save path.

## Open items

- Blocked on **PR #6** for real `oc_radio_*` / `oc_fh_*` on tree (delete
  `pending_opencollar/`).
- op-fw-radio: SX1262 backend for `oc_radio_t`.
- Cody / PR #2: welfare numeric caps (hooks only here).
- Real MAX-M10S UART when module arrives.
