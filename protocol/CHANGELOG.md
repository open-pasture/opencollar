# Protocol changelog

Wire-visible changes, newest first. Versions name the protocol, not any firmware or server
release.

## 2026-10-27

### v2.0.0-draft.2

From the protocol freeze review. Every change below has a test vector or a reference test.
Not frozen yet; [v2/README.md](v2/README.md#open-questions) lists what the owner decides.

- **Slots** ([lora.md §3](v2/lora.md#3-the-minute)): fast windows no longer collide with
  other groups. Each slot of each minute has one owner; spare phases go round the groups for
  fast collars; membership key 22 `groups`; one schedule per net. Capacity restated: a full
  fast window for 300 collars per net, up to 1 500 at the normal rate.
- **Every record fits a frame** ([messages.md §6](v2/messages.md#6-records-up)): at most
  109 bytes; device and slots records go in parts (`part`, device key 16, slots element 4).
  Device record keys 17 `device_key`, 18 `plans`, 19 `zone_limits`.
- **Beacons are authenticated** ([lora.md §9](v2/lora.md#9-security-on-the-air)): an 8-byte
  HMAC tag under the herd's beacon key, wrapped for each collar in its membership (key 23).
  `heard` is a radio receipt only; collars keep records at least 7 days after it. Beacon key
  6 is now `handon` [short, minute] (was `next`), key 7 `term`.
- **Anchor election** ([lora.md §5](v2/lora.md#5-anchors)): terms, an absolute hand-on minute,
  a tie-break, and listen minutes so two active anchors find each other and converge.
- **Join** ([lora.md §6](v2/lora.md#6-join)): net-0 hellos, dst 0 for joining collars,
  `pending` 0, backoff, hello size.
- **Zones and leases** ([messages.md §4.7](v2/messages.md#47-zones-and-leases-what-the-collar-enforces-itself)):
  commands 12 `zones` and 13 `lease`, boundary key 21 `policy`, reject 32 `in_exclusion`, cap
  `zones`. The collar enforces permanent no-go zones under every boundary and takes a staged
  one only under a current lease.
- **Counters** ([messages.md §7.1](v2/messages.md#71-counters-that-never-repeat)): `seq`,
  `fcnt` and the batch counter are lifetime counters with write-ahead reservation, never
  reset; servers keep a replay window and flag conflicting duplicates.
- **Handover** ([identity.md §6](v2/identity.md#6-handover-rotating-the-server-key-or-moving-to-other-software)):
  confirm key 17 names the handover's digest; deadline bounded (`bad_config`); dual posting
  until the deadline; what old and new servers keep for members that miss a step.
- **Ownership**: release, transfer and the first owner change need the owner key when one is
  enrolled; a transfer (handover key 21 `new_owner`) moves the owner key; `recode` over USB
  or BLE with a magnet.
- **Claim time**: commands issued before the collar's claim are `stale`. Repeats are
  recognised by digest.
- **Scope**: `device` required for config, membership, bind, resend, release; a command with
  `expires_at` and no GNSS time waits (`not_now`); membership plan, groups and handover
  deadline checked.
- **Firmware** ([firmware.md](v2/firmware.md)): the nRF52840 boot profile; trust updates
  (document 68, command 14) to revoke and replace release keys; two release keys at
  manufacture; install conditions from the collar's own state; confirmation on local
  evidence only, never the link; no-fix retries before an image is refused.
- **Strict decoding**: protocol maps have unsigned integer keys only; no tags in payloads,
  records or link maps; the unprotected header is empty; known fields present with the wrong
  type or out of range refuse their message or record; records are decoded one by one by
  extent; frames at most 255 bytes; fragment counts and reassembly bounded.
- **JSON view**: unknown registry values show as their numbers, not `"other"`.
- **v1 migration** ([identity.md §10](v2/identity.md#10-from-v1)): v2 herd id from the v1 id
  by hash; the device key travels in the v1 report and the device record.
- Conformance: every vector declares the CDDL schema's verdict; the Python reader checks
  records, beacons and the slot schedule independently; the Rust reference fuzzes every
  decoder.

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
