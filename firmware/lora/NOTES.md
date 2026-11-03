# Fence gossip — design notes and assumptions

Owned by `firmware/lora` (portable C) and `firmware/sim` (host virtual radio).
Branch: `proto-fence-gossip` (mirrored to `cursor/proto-fence-gossip-c865` for agent PR tooling).

**Canonical names for other teams:** `oc_radio_*` (HAL) and `oc_fh_node_*` (engine).
**All field and type names are PLACEHOLDERs.** `protocol/v2/` is not edited here.

## Protocol deviation (do not edit `lora.md`)

**`protocol/v2/lora.md` §1 says: "Nodes never relay…"**

| Mode | `starling_serve` (PLACEHOLDER) | Who serves | Matches §1? |
|---|---|---|---|
| One-hop star (**default**) | **OFF** | Rooks only | Yes |
| Multi-hop gossip | ON | Any verified holder | **No — deliberate; protocol owner decides** |

Default OFF until Starling listen energy is measured. Rooks always serve. Pilot
telemetry stays one hop to the Rook. **`lora.md` is not edited in this PR.**

## PILOT DECISION — opaque payload inject (Rook has no farm signing key)

The Rook in the pilot does **not** hold a farm/server Ed25519 key that can seal
gossip manifests. Therefore:

| Path | API | Envelope | Authenticity | Rollback key |
|---|---|---|---|---|
| **Pilot (now)** | `oc_fh_inject_opaque` | `OC_FH_MSG_MANIFEST_LOCAL` = type + body (**unsigned**) | Payload’s own Ed25519 (e.g. v1 signed JSON), checked by injectable `oc_fh_payload_verify_fn` **after full reassembly** | payload version = `fence_seq` |
| **Later / server** | `oc_fh_inject_local` | `OC_FH_MSG_MANIFEST` = type + sig + body (farm-signed) | Manifest Ed25519 over `oc/fh/manifest/1 \|\| body` | `fence_seq` in manifest |

- Relays re-serve the **same wire bytes** (local or sealed) unchanged.
- A forged/tampered opaque payload fails `payload_verify` and never becomes active
  (`test_pilot`).
- Keep the sealed path for when the server issues manifests.

## Freshness record (`oc_fh_freshness_t`) — canonical for op-fw-starling

Defined in `fence_manifest.h`. Exact layout (host endian for integers in RAM;
wire uses big-endian elsewhere):

| Field | Type | Width | Meaning |
|---|---|---|---|
| `farm_id` | `uint8_t[]` | **8** | Farm identifier |
| `fence_seq` | `uint32_t` | **4** | Monotonic fence version; **0 = none** |
| `poly_hash` | `uint8_t[]` | **32** | Blake2b-256 of full fence payload |
| `received_at_ms` | `uint32_t` | **4** | Local monotonic ms when activated |
| `source_id` | `uint16_t` | **2** | Node id that served us (or self on inject) |

Total packed logical size: 50 bytes. Do not rename fields without coordinating;
widths are part of the store blob contract.

## Manifest wire buffer

`OC_FH_MANIFEST_WIRE_MAX` = **1140** (= 1 + 64 + body with 64 fragment hashes),
derived from `OC_FH_MAX_FRAGMENTS` with compile-time static asserts.
Oversized wire → `OC_FH_ERR_MANIFEST_WIRE`, `stats.manifest_wire_ovf`, event
`OC_FH_EV_MANIFEST_WIRE_OVF` (no silent drop).  
Note: a 1140 B sealed frame exceeds LoRa MTU 255; `test_maxfrag` raises sim MTU
to exercise storage/re-serve. Production multi-frame manifests are future work.

## Persistence (`oc_fh_store_t`)

Apps implement NVS-backed `get_hwm` / `set_hwm` / `save_active` / `load_active`.
Host: `oc_fh_store_ram`. Rollback uses `max(active.fence_seq, hwm)` so reboot
cannot accept an older fence. `oc_fh_node_restore` reloads the active blob so a
restored node can serve.

## Unsigned beacon anti-DoS

Beacons never change the active fence. NEED requests while awaiting a real
manifest are capped per peer and per time window (`OC_FH_NEED_HINT_MAX`,
`OC_FH_NEED_WINDOW_*`). Flood → `stats.need_capped`, bounded `need_tx`/airtime
(`test_security` forged-beacon flood).

## Spec ambiguities (short)

- Blake2b hashes (Monocypher); sealed domain `oc/fh/manifest/1`.
- Placeholder msg types in `fence_ids.h` (`0xA0`–`0xA5`).
- `frag_data_max` default 209 (`lora.md`).

## Crypto / license

Monocypher (BSD-2-Clause OR CC0). No GPL / no Meshtastic code. Trickle from RFC 6206 only.

## HAL (`radio_hal.h`) — for op-fw-radio

| Sketch / request | This header | Notes |
|---|---|---|
| `rhal_init` | `oc_radio_init` | cfg + limits |
| `rhal_set_power` | `oc_radio_set_power` | |
| `rhal_airtime_us` | `oc_radio_airtime_us` | |
| `rhal_send` + `at_us` | `oc_radio_send` + `opts.at_us` | + per-packet TX power |
| `SKIP_CAD` | `OC_RADIO_TX_FLAG_SKIP_CAD` | **added** in `opts.flags` |
| `rhal_recv` | `oc_radio_recv` | + `t_rx_us`, **`peer_id`** |
| `rhal_cad(timeout)` | `oc_radio_cad(radio, out, timeout_ms)` | **timeout added** (0 = backend default / 50 ms on SX1262) |
| `rhal_sleep` | `oc_radio_sleep` | |
| `rhal_now_us` | `oc_radio_now_us` | |
| `rhal_airtime_left_us` | `oc_radio_duty_budget_us` / alias | |
| limits | `oc_radio_limits_t` | max frame airtime, hourly budget, min TX gap |
| errors | `ERR_GAP`, `ERR_AIRTIME` | |

## native_sim (Zephyr)

Stub only. Host `firmware/sim` covers milestones.
