# Fence gossip — design notes and assumptions

Owned by `firmware/lora` (portable C) and `firmware/sim` (host virtual radio).
Branch: `proto-fence-gossip` (mirrored to `cursor/proto-fence-gossip-c865` for agent PR tooling).

## Mapping to protocol and product names

| Product (Cody) | Protocol v2 (`lora.md`) | This library |
|---|---|---|
| Rook (LTE-M + GPS base) | Active anchor (role 2) that also gets fences from the server | `is_rook=1`; may `inject_local` |
| Starling (LoRa collar) | Node (role 1) | `is_rook=0`; with `starling_serve=1` re-serves verified fences |
| Fence / boundary | Boundary command (messages.md type 1) | Opaque payload + signed **manifest** |

Symmetric node protocol: Rook and Starling run the same exchange. A Rook is just a node that also receives the fence from the server.

## Spec ambiguities reconciled here

1. **`lora.md` §1 says nodes never relay; Cody/op-firmware require Starling-to-Starling gossip.**  
   Resolved with runtime `starling_serve`: `0` = one-hop star (only Rooks serve); `1` = multi-hop. Message formats and state machine support multi-hop from day one; milestone (a) is one-hop.

2. **Manifest vs full COSE boundary.**  
   Collar firmware today verifies v1 canonical-JSON Ed25519 (Monocypher). Protocol v2 uses COSE_Sign1. This library uses a **compact binary manifest** signed with Ed25519 over `oc/fh/manifest/1 || body`, injectable verify callback. Production may later wrap or replace with the COSE boundary bytes as the opaque payload; the gossip plane stays the same. Hashes are Blake2b (Monocypher-native), not SHA-256 — noted as a deliberate pilot choice.

3. **Fragment size.**  
   `lora.md` uses ≤209 data bytes in kind `0x22` frames. Gossip fragment data max is configurable (`frag_data_max`, default 209). Tests use smaller MTUs to force multi-fragment paths.

4. **Beacons.**  
   Herd LoRa beacons (`0x20`) are HMAC-authenticated. Gossip freshness beacons (`OC_FH_MSG_BEACON`) are **unauthenticated hints** per op-firmware: they may only schedule a bounded NEED/serve, never change the active fence. Rate-limited.

5. **Version / rollback.**  
   `messages.md` §4.6: reject version ≤ held (`stale`). We use monotonic `fence_seq`; reject `seq <= current` on inject and on verified manifests. Equal versions ⇒ no transfer. Last-good remains active until a newer fence is fully reassembled **and** signature-checked.

6. **Hop counter.**  
   Reserved on beacons (`hop_reserved`); always 0 on the fence path. No TTL — each hop is a fresh exchange. Field kept for later telemetry relay.

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

## HAL

`include/opencollar/radio_hal.h` — agreed with op-fw-radio. Hardware backend: `firmware/radio` (not this PR). Sim backend: `firmware/sim`.

## native_sim (Zephyr)

Stub only. Host `firmware/sim` covers milestones; a Zephyr `native_sim` target can wrap the same library later if needed.
