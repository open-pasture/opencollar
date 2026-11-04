<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 openpasture contributors
-->

# Starling runbook

Low-power LoRa collar app (nRF52840 + external u-blox GNSS). Pilot milestone:
build + run the fence from **simulated GNSS**. Real GNSS and SX1262 when parts
arrive.

**Merge order (op-firmware):** PR #6 (proto) → #12 (rook) → **#9 (this) last**.
Do **not** merge this PR; keep draft until op-firmware says go.

## Layout

| Path | Owner / role |
| --- | --- |
| `firmware/starling/` | This app |
| `firmware/lora/` | PR #6 — `oc_radio_*`, `oc_fh_node_*`, `INTEGRATION.md` |
| `firmware/starling/pending_opencollar/` | **TEMPORARY** freshness-only shim — **delete when #6 merges** |
| `firmware/starling/src/oc_fh_store_nvs.*` | NVS `oc_fh_store_t` (A/B+CRC HWM+active) per INTEGRATION |
| `firmware/core/welfare.h` | Cue gate hooks; honors shut-off (no numeric caps; PR #2) |
| `firmware/src/{geofence,cue,…}` | Shared portable core (do not move here) |

## INTEGRATION.md conformity (PR #6)

Starling calls exactly:

| Call | When |
| --- | --- |
| `oc_fh_node_init` | Bind radio |
| `oc_fh_node_set_store` | After init (NVS backend) |
| `oc_fh_node_set_payload_verify` | Pilot LOCAL authenticity |
| `oc_fh_node_restore` | Boot — **before any radio poll** |
| `oc_fh_inject_opaque` | Pilot inject (host/Rook path) |
| `oc_fh_node_poll` | Tick / radio IRQ |

Config: `starling_serve` default **OFF**, `accept_local_air=1` (pilot),
`frag_data_max` → `OC_FH_DEFAULT_FRAG_DATA` (209). Freshness widths per
NOTES.md: farm 8 / seq 4 / poly 32 / recv 4 / source 2.

## Host tests

```bash
make -C firmware/starling/tests/host
# pin tip: PROTO_REF=origin/proto-fence-gossip make -C firmware/starling/tests/host clean deps test
```

Suites: `geofence_fake`, `fence_store`, `ubx_nmea`, `demo`, `gossip_hwm`
(restore + inject_opaque + reject-stale), `gossip_opaque` (payload_verify /
field widths).

`PROTO_REF` defaults to `origin/proto-fence-gossip` (PR #6 tip). Archive lands
in `tests/host/.deps/` (gitignored).

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

When `firmware/lora` is present (after #6), CMake links `oc_fh_*` +
`oc_fh_store_nvs` and defines `STARLING_HAS_LORA`. Otherwise
`pending_opencollar` (freshness only; gossip disabled).

## Default `prj.conf`

| Flag | Default | Meaning |
| --- | --- | --- |
| `CONFIG_STARLING_GNSS_FAKE` | **y** | Fake GNSS on |
| `CONFIG_STARLING_SERVE` | **n** | Maps to `starling_serve` / `OC_FH_STARLING_SERVE_DEFAULT` |
| `CONFIG_STARLING_BENCH_FENCE` | **y** | Demo fence when NVS empty |

## Persistence

| Store | Ids | Contract |
| --- | --- | --- |
| `oc_fh_store_nvs` | `0x50`/`0x51` A/B, `0x52` primary | HWM+active same CRC’d record; higher `fence_seq` wins |
| `fence_store` (geo mirror) | `0x40` active, `0x43` hwm | Vertices / demo path; reject `seq <= hwm` |

Boot: `starling_gossip_restore` → load HWM + active **before** radio traffic.
Fence move calls `cue_rearm` only — never `cue_clear_shutoff` (PR #22).

## Welfare / shut-off (PR #22 merged, #25 draft)

- **#22:** auto shut-off stays until caretaker `cue_clear_shutoff`; fence
  `cue_rearm` must not resume. Starling wires `welfare_hooks_init_shutoff`
  so the welfare gate suppresses cues while `cue.enforcement_off`.
- **#25 (draft):** persist shut-off + signed remote re-arm (`welfare_store`,
  `rearm_seq`). **Not wired in Starling yet** — needs Cody decision (see
  below). No numeric welfare caps here (PR #2).

### TODO(cody)

1. Should Starling boot-restore shut-off from `STORE_ID_WELFARE` (#25) the
   same way the main collar app does?
2. Remote re-arm over LoRa vs serial-only on Starling?
3. PR #2 numeric welfare caps (escape_cycle_limit / max_outside_cues).

## Open / blocked

- Blocked on **PR #6** merge for `firmware/lora` on `main` (then delete
  `pending_opencollar/`).
- op-fw-radio: SX1262 backend for `oc_radio_t`.
- Draft PR #25: persist shut-off + signed rearm (Starling hook only so far).
- Real MAX-M10S UART when module arrives.
