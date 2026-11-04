# Fence gossip integration (op-fw-starling / op-fw-rook-lte)

Portable library under `firmware/lora` + host sim under `firmware/sim`.
PLACEHOLDER names. Draft PR — do not merge.

Canonical APIs: **`oc_radio_*`** (HAL) and **`oc_fh_node_*`** (engine).

---

## Calls

| Call | Who | Notes |
|---|---|---|
| `oc_fh_node_init` | both | Once; supplies cfg, caller buffers, radio, sealed-manifest `verify`, `now_ms` |
| `oc_fh_node_set_store` | both | Optional; before inject/restore/poll |
| `oc_fh_node_set_payload_verify` | both (pilot) | Required to accept air `MANIFEST_LOCAL` |
| `oc_fh_node_restore` | both | After reboot if store set; loads active + HWM |
| `oc_fh_inject_opaque` | **Rook pilot** | Opaque v1-signed payload; builds unsigned local envelope |
| `oc_fh_inject_local` | Rook (later) | Farm-sealed manifest + payload |
| `oc_fh_node_poll` | both | Drive RX/TX/timers; call often |
| `oc_fh_active` / `oc_fh_stats` | both | Read current fence / counters |

### `oc_fh_node_init`

```c
void oc_fh_node_init(oc_fh_node_t *n, const oc_fh_config_t *cfg,
                     const oc_fh_buffers_t *buf, oc_radio_t *radio,
                     oc_fh_verify_fn verify, void *verify_ctx,
                     uint32_t (*now_ms)(void *), void *clock_ctx);
```

- `verify`: Ed25519 check for **sealed** manifests (`oc/fh/manifest/1 \|\| body`). Pilot Rook may still pass a farm verify for later sealed path; Starling needs the farm pubkey.
- `now_ms`: monotonic ms (same clock domain as radio scheduling is fine).
- Caller owns all buffers in `oc_fh_buffers_t` for the node lifetime.

### `oc_fh_node_poll`

- **Cadence:** every few ms while awake (tests use 5 ms sim steps). Non-blocking: drains up to 8 RX frames, then NEED/serve/trickle/pending-timeout.
- **Expects:** radio ready (`oc_radio_recv` with `timeout_ms=0`); cfg/buffers valid.
- **Returns:** void. Observe `n->last_event` and `oc_fh_stats(n)`.

### Rook pilot: `oc_fh_inject_opaque`

```c
int oc_fh_inject_opaque(oc_fh_node_t *n, const uint8_t *payload, size_t plen,
                        uint32_t fence_seq, uint32_t issued_at);
```

- `payload`: already-authenticated bytes (e.g. v1 signed JSON command).
- `fence_seq`: payload version; must be `1…OC_FH_SEQ_MAX` and `> hwm`.
- Envelope on air: `OC_FH_MSG_MANIFEST_LOCAL` (unsigned). Relays re-serve same wire.
- Receivers need `accept_local_air=1` **and** `payload_verify` set, or LOCAL is dropped (`reject_local_air`).
- `payload_verify(payload, len, fence_seq, ctx)` → 0 to accept after full reassembly.

### `oc_fh_node_restore`

Returns `OC_FH_OK` if an active fence loaded, `OC_FH_ERR_STORE` if empty.
Restores `active`, wire, and HWM from the store’s best A/B record.

---

## `oc_fh_store_t` (app over NVS)

Implement `get_hwm`, `set_hwm` (soft/optional), `save_active`, `load_active`.

**Contract** (see `fence_store.h`):

1. HWM + active fence in the **same** A/B record, each copy CRC’d; commit atomically in `save_active`.
2. Write inactive slot first; flip primary only when CRC valid.
3. Non-zero `save_active` → do not promote fence in RAM (`OC_FH_ERR_STORE` / `persist_fail`).
4. On restore, if **both** copies valid → pick **higher `fence_seq`**; do not trust a separate primary pointer.
5. Host reference: `oc_fh_store_ram` (+ `fail_next_save` / `tear_next_save` for tests).

---

## `radio_hal.h` (firmware/radio implements)

| Op | Contract |
|---|---|
| `oc_radio_init` | cfg + `oc_radio_limits_t` (max frame airtime, hourly budget, min TX gap) |
| `oc_radio_send` | opts may be NULL; `OC_RADIO_TX_FLAG_SKIP_CAD` skips CAD; duty/gap/airtime → `ERR_DUTY` / `ERR_GAP` / `ERR_AIRTIME` |
| `oc_radio_recv` | caller buf; `timeout_ms=0` non-block; fills `peer_id`, RSSI/SNR, `t_rx_us` |
| `oc_radio_cad` | `timeout_ms`; 0 = backend default (~50 ms SX1262) |
| `oc_radio_set_power` | default TX dBm |
| `oc_radio_airtime_us` | estimate for `len` |
| `oc_radio_duty_budget_us` / `airtime_left_us` | remaining hourly TX budget |
| `oc_radio_now_us` | monotonic µs |
| `oc_radio_sleep` | low power until next send/recv/cad |
| `oc_radio_backoff_ms` / `trickle_t_ms` | jitter helpers |

Host mock: `firmware/sim` (`sim_world_*`, `sim_radio`).

---

## Config

| Field | Default / rule |
|---|---|
| `starling_serve` | **OFF** (`OC_FH_STARLING_SERVE_DEFAULT`). Rooks always serve. Multi-hop tests set `1`. |
| `accept_local_air` | `0`; pilot receivers set `1` + `payload_verify` |
| `is_rook` | Rook=`1` |
| `farm_id[8]` | farm identity |
| `frag_data_max` | 0 → `OC_FH_DEFAULT_FRAG_DATA` (209) |
| `trickle_imin_ms` / `imax` / `k` | 0 → 1000 / 60000 / 1 |
| `pending_timeout_ms` | 0 → `OC_FH_PENDING_TIMEOUT_MS` (30000) |
| NEED caps | `OC_FH_NEED_HINT_MAX`=8/peer/window, global 64 / 5 s |
| `OC_FH_SEQ_MAX` | `0x7FFFFFFF` — refuse higher; server must not issue near `UINT32_MAX` |

---

## Stats to expose

From `oc_fh_stats_t`: `tx_frames`, `rx_frames`, `retransmit_frags`, `airtime_us`, `applied`, `reject_sig`, `reject_seq`, `reject_hash`, `reject_payload`, `manifest_wire_ovf`, `need_capped`, `need_tx`, `reject_local_air`, `pending_timeout`, `persist_fail`. Plus `last_event`.

---

## RAM footprint (host `sizeof`, approx)

| Object | Bytes |
|---|---|
| `oc_fh_node_t` | **~4992** (includes 2×1140 wire + manifest + frag bitmap) |
| Caller buffers (max) | active+pending payloads ≤2×`OC_FH_MAX_PAYLOAD` (12288) + RX MTU + TX scratch ≈ **26 KiB** |
| Typical pilot (2 KiB payloads, 512/1500 scratch) | buffers ≈ **6 KiB** |
| `oc_fh_store_ram_t` (host test only) | ~29 KiB (full max payload×2); flash backend should size to real fence max |

Node does not heap-allocate; app provides buffers.

---

## Minimal usage (against headers)

These snippets are exercised by `tests/test_integration_snippets.c`
(init + one `poll` each). Apps replace the infinite loops with sleep/IRQ.

### Rook (pilot)

```c
static uint8_t rook_active[2048], rook_pending[2048], rook_rx[256], rook_tx[1500];
static oc_fh_node_t rook_node;
static oc_fh_store_ram_t rook_store; /* replace with NVS-backed oc_fh_store_t */

void rook_main(oc_radio_t *radio, const uint8_t farm[8],
               oc_fh_verify_fn farm_verify, void *farm_ctx,
               oc_fh_payload_verify_fn pv, void *pv_ctx,
               uint32_t (*now_ms)(void *), void *clock)
{
	oc_fh_config_t cfg = {0};
	oc_fh_buffers_t buf = {
		rook_active, sizeof rook_active, rook_pending, sizeof rook_pending,
		rook_rx, sizeof rook_rx, rook_tx, sizeof rook_tx
	};
	cfg.node_id = 1;
	cfg.is_rook = 1;
	cfg.starling_serve = OC_FH_STARLING_SERVE_DEFAULT; /* OFF */
	cfg.accept_local_air = 1; /* if Rook also accepts peer LOCAL */
	memcpy(cfg.farm_id, farm, 8);
	cfg.frag_data_max = 209;

	oc_fh_store_ram_init(&rook_store); /* app: wire NVS ops instead */
	oc_fh_node_init(&rook_node, &cfg, &buf, radio, farm_verify, farm_ctx, now_ms,
	                clock);
	oc_fh_node_set_store(&rook_node, &rook_store.api);
	oc_fh_node_set_payload_verify(&rook_node, pv, pv_ctx);
	(void)oc_fh_node_restore(&rook_node);

	for (;;) {
		/* When core delivers a new v1-signed command: */
		/* oc_fh_inject_opaque(&rook_node, cmd, cmd_len, version, issued_at); */
		oc_fh_node_poll(&rook_node);
		/* sleep / yield; wake on radio IRQ or timer */
	}
}
```

### Starling

```c
/* Own node + buffers — do not reuse the Rook's. Same sizes as Rook example. */
static uint8_t star_active[2048], star_pending[2048], star_rx[256], star_tx[1500];
static oc_fh_node_t star_node;

void starling_main(oc_radio_t *radio, const uint8_t farm[8],
                   oc_fh_verify_fn farm_verify, void *farm_ctx,
                   oc_fh_payload_verify_fn pv, void *pv_ctx,
                   uint32_t (*now_ms)(void *), void *clock)
{
	oc_fh_config_t cfg = {0};
	oc_fh_buffers_t buf = {
		star_active, sizeof star_active, star_pending, sizeof star_pending,
		star_rx, sizeof star_rx, star_tx, sizeof star_tx
	};
	cfg.node_id = 2;
	cfg.is_rook = 0;
	cfg.starling_serve = OC_FH_STARLING_SERVE_DEFAULT; /* OFF = one-hop */
	/* Multi-hop gossip (explicit): cfg.starling_serve = 1; */
	cfg.accept_local_air = 1; /* pilot LOCAL from Rook */
	memcpy(cfg.farm_id, farm, 8);
	cfg.frag_data_max = 209;

	oc_fh_node_init(&star_node, &cfg, &buf, radio, farm_verify, farm_ctx, now_ms,
	                clock);
	oc_fh_node_set_payload_verify(&star_node, pv, pv_ctx);
	/* optional: oc_fh_node_set_store + oc_fh_node_restore */
	for (;;) {
		oc_fh_node_poll(&star_node);
		/* apply oc_fh_active(&star_node) to geofence when stats.applied bumps */
	}
}
```

See `NOTES.md`, `RUNBOOK.md`, and `make -C firmware/lora test`.
