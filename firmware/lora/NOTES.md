# Fence gossip — design notes and assumptions

Owned by `firmware/lora` (portable C) and `firmware/sim` (host virtual radio).
Branch: `proto-fence-gossip` (mirrored to `cursor/proto-fence-gossip-c865` for agent PR tooling).

**All field and type names are PLACEHOLDERs** (see `firmware/ARCHITECTURE.md` on
`docs/firmware-architecture`). v2 wire ids in `protocol/v2/` are untouched.

## Protocol deviation (do not edit `lora.md`)

**`protocol/v2/lora.md` §1 says: "Nodes never relay: relaying means listening, and
listening costs more than talking."**

This library intentionally contradicts that for an optional multi-hop path:

| Mode | `starling_serve` (PLACEHOLDER) | Who serves verified fences | Matches `lora.md` §1? |
|---|---|---|---|
| One-hop star (default) | **OFF** (`OC_FH_STARLING_SERVE_DEFAULT`) | Rooks only | Yes |
| Multi-hop gossip | ON | Any node holding a verified fence | **No — deliberate product deviation** |

- Default is **OFF** until Starling listen energy is measured (ARCHITECTURE.md).
- Rooks **always** serve.
- Pilot **telemetry** stays one hop to the Rook (`lora.md` §8); only fence
  manifests/fragments may multi-hop when the flag is on.
- **`lora.md` is not edited in this PR.** The protocol owner decides whether to
  amend §1 or keep gossip as a firmware-only optional mode.

## Mapping to protocol and product names

| Product (Cody) | Protocol v2 (`lora.md`) | This library |
|---|---|---|
| Rook (LTE-M + GPS base) | Active anchor (role 2) that also gets fences from the server | `is_rook=1`; may `inject_local`; always may serve |
| Starling (LoRa collar) | Node (role 1) | `is_rook=0`; serves only if `starling_serve=1` |
| Fence / boundary | Boundary command (messages.md type 1) | Opaque payload + signed **manifest** |

Symmetric node protocol: Rook and Starling run the same exchange. A Rook is just a node that also receives the fence from the server.

## Spec ambiguities reconciled here

1. **Relay vs no-relay** — see deviation table above (`starling_serve`).

2. **Manifest vs full COSE boundary.**  
   Collar firmware today verifies v1 canonical-JSON Ed25519 (Monocypher). Protocol v2 uses COSE_Sign1. This library uses a **compact binary manifest** signed with Ed25519 over `oc/fh/manifest/1 || body`, injectable verify callback. Production may later wrap or replace with the COSE boundary bytes as the opaque payload; the gossip plane stays the same. Hashes are Blake2b (Monocypher-native), not SHA-256 — deliberate pilot choice.

3. **Fragment size.**  
   `lora.md` uses ≤209 data bytes in kind `0x22` frames. Gossip fragment data max is configurable (`frag_data_max`, default 209). Tests use smaller sizes to force multi-fragment paths.

4. **Beacons.**  
   Herd LoRa beacons (`0x20`) are HMAC-authenticated. Gossip freshness beacons (`OC_FH_MSG_BEACON`) are **unauthenticated hints**: they may only schedule a bounded NEED/serve, never change the active fence. Rate-limited. Covered by `test_forged_beacon`.

5. **Version / rollback.**  
   `messages.md` §4.6: reject version ≤ held (`stale`). We use monotonic `fence_seq`; reject `seq <= current`. Equal versions ⇒ no transfer. Last-good remains active until a newer fence is fully reassembled **and** signature-checked.

6. **Hop counter.**  
   Reserved on beacons (`hop_reserved`); always 0 on the fence path. No TTL — each hop is a fresh exchange.

7. **Identifiers are placeholders.**  
   All message type ids and names live in `include/opencollar/fence_ids.h`.

## Crypto / license

- Ed25519 via existing `firmware/third_party/monocypher` (BSD-2-Clause OR CC0) — compatible with Apache-2.0.
- No GPL code. No Meshtastic code, structure, or constants. Trickle timer implemented from RFC 6206 description only.

## API for later relay without redesign

- Any node that holds a **verified** fence stores the sealed manifest wire bytes and can re-transmit them unchanged (fleet/farm signature, not the relayer’s).
- `oc_fh_may_serve()` gates on `starling_serve || is_rook`.
- Freshness log: `fence_seq`, poly hash, `received_at`, `source_id`.
- N-node sim topologies: full mesh, chain, per-link loss, partition/heal.

## HAL (`radio_hal.h`) — reconciliation note for op-fw-radio

First commit shipped the agreed send/recv/CAD/set_power/airtime/duty/backoff shape.
Follow-up (this change) adds ARCHITECTURE.md sketch surface **without renaming** the
agreed `oc_radio_*` symbols:

| Architecture sketch | This header | Notes |
|---|---|---|
| `rhal_init(cfg, lim)` | `oc_radio_init` | cfg + limits (max frame airtime, hourly budget, min TX gap) |
| `rhal_set_power` | `oc_radio_set_power` | unchanged |
| `rhal_airtime_us` | `oc_radio_airtime_us` | unchanged |
| `rhal_send(..., at_us)` | `oc_radio_send` + `opts.at_us` | keeps per-packet TX power opts |
| `rhal_recv` | `oc_radio_recv` | meta now also has `t_rx_us` |
| `rhal_cad` | `oc_radio_cad` | unchanged |
| `rhal_sleep` | `oc_radio_sleep` | **added** |
| `rhal_now_us` | `oc_radio_now_us` | **added** |
| `rhal_airtime_left_us` | `oc_radio_duty_budget_us` / alias `oc_radio_airtime_left_us` | same meaning |
| limits | `oc_radio_limits_t` | max_frame_airtime_us, airtime_budget_us_per_h, min_tx_gap_ms |
| — | `OC_RADIO_ERR_GAP`, `OC_RADIO_ERR_AIRTIME` | **added** status codes |

Existing call sites that only used send/recv/CAD/power/airtime/duty/backoff remain source-compatible (`oc_radio_tx_opts_t` gained a trailing `at_us` field; zero-init still means “now”).

## native_sim (Zephyr)

Stub only. Host `firmware/sim` covers milestones; a Zephyr `native_sim` target can wrap the same library later if needed.
