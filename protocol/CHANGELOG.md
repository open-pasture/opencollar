# Protocol changelog

Wire-visible changes, newest first. Versions name the protocol, not any firmware or server
release.

## 2026-10-26

### v2.0.0-draft.1 (new, draft)

LoRa-first and transport-neutral ([v2/](v2/README.md)). Nothing implements it on a collar
yet; op-protocol has the reference codec and vectors.

- Messages are deterministic CBOR with integer keys and no floats. Commands are COSE_Sign1
  with EdDSA, a signed type in payload key 0, `herd` required, optional `expires_at`, no
  key cap, carried as opaque bytes by every transport.
- New commands: membership, roster, bind, handover, confirm, owner, firmware, resend,
  release. Boundaries and configs keep v1's meaning (rings delta-encoded in e7, margins in
  centimetres; config gains `fix_s`, `track_s`, `endpoint_pin`, `anchor_hold_s`; herd moves
  to membership; polling is gone).
- Uplink records, each with a per-collar `seq` for deduplication: status, fixes, cue,
  episode, ack, health, device, slots, anchor, firmware.
- Frames sealed per collar with AES-128-CCM under a key from X25519 between the device key
  and the server key.
- LoRa binding: GNSS-timed minute, beacon, slots from the short address, broadcast
  boundaries with per-collar `got`/`need` and selective repeat, anchor hand-on and failover,
  join by hello.
- HTTP binding for anchors and direct collars: signed batches, downlinks in the reply,
  status and retry rules; CoAP mapping reserved.
- Identity: collar-generated device keys, factory records, claim codes and binds; server key
  handover with confirm and fallback; an optional owner recovery key; release and factory
  reset.
- Firmware: release manifests signed by the release key or an enrolled image key, server
  update commands, the collar's install rules (battery, no move, no escape), test boot and
  rollback.
- Registries for every enumerated value, with private ranges.

### v1.1 (no change to messages)

- The status line no longer claims firmware 0.2 talks to a server: it has no network code.
- `wrong_herd` **and `bad_sig`** refusals are offered again once the collar holds its new
  config (servers already did this; the text said only `wrong_herd`).
- Forward compatibility written down: unknown fields ignored; unknown cue kinds, episode
  outcomes, ack and slot statuses and reject codes kept as sent, never failing a whole
  report or ack. openpasture's server now does this for every uplink value.
- HTTP status and retry rules for v1 collars ([v2/http.md §8](v2/http.md#v1-binding)) and
  server obligations ([v2/server.md](v2/server.md)).
- The `sim` cap: a simulated collar says so.
- Test vectors moved here ([vectors/](vectors/README.md)) as the source of truth; the herd
  change joins the shared `slots.json`; new `cue.json` for the cue rule.
- `contracts.md` (the retired agent kit's server contract) moved to [archive/](archive/).

## 2026-09-27: v1

Holes, staged slots, collar-scoped boundaries, track mode, episodes and signed configs, as
firmware 0.2 and openpasture's server implement them. Every new field optional, so a
firmware 0.1 command serializes byte for byte as before.

## 2026-09: v0

One ring of up to 64 vertices, no caps (firmware 0.1, bench prototypes only).
