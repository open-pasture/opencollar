# Protocol changelog

Wire-visible changes, newest first. Versions name the protocol, not any firmware or server
release.

## 2026-11-04

### Report telemetry for the farmer app (read-only; protocol record N)

Not a wire version bump. Host-tested; **nothing was run on hardware.** Does
not change welfare or cue behaviour. Does not edit Rook LTE (PR #12). No
report `armed` field (`welfare.enforcement` from the rearm work covers it).

Exact field names (also in firmware `wire_fields.h` for easy rename):

- **`health.last_cue_at`** (RFC3339 Z): time of the most recent cue the collar
  delivered (warn / outside / future pulse-equivalent). Omitted if none since
  boot or GNSS time untrusted. **Lost on reboot** (not persisted).
- **`fixes[].hdop`** (existing v1): encoded on valid fixes when GNSS provides
  it (nRF PVT `hdop`); omitted otherwise. `accuracy_m` unchanged. Does not
  invent a new field or alter `health.charging`.
- **`health.cell.rsrp_dbm`** (existing v1 nested field): filled via
  `report_set_signal_dbm()` (Rook LTE wires the modem reading) as a partial
  `cell` object when only RSRP is known. Omitted until set. **No flat
  `health.rsrp_dbm`.**
- **`battery`**: still omitted when unknown; never reported as `0` to mean
  unknown (host test covers this).

Vectors: [`vectors/report.json`](vectors/report.json).

### Signed remote rearm + persisted shut-off (Cody)

Not a full wire version bump; new optional cap and report fields. Host-tested only;
**nothing was run on hardware.**

- **Persist shut-off** in NVS id 5 (`enforcement_off`, `shutoff_at`, escape-cycle
  counters, `rearm_seq`). Boot restores shut-off so a hard reboot does not resume
  enforcement. A fence / boundary change still never clears it (2026-11-03).
- **`rearm_seq`**: lifetime monotonic counter per collar. Never reset or lowered
  (provision wipe, serial `rearm`, boot, or a server DB restore that goes
  backwards). Reject `rearm_seq <= held` as `stale`.
- **Signed `rearm` command** (cap `rearm`): JSON
  `{type, command_id, collar_id, herd_id?, rearm_seq, issued_at, expires_at,
  shutoff_at, reason_code, sig}` — Ed25519 over canonical JSON without `sig`
  (same as boundary/config). `shutoff_at` must equal the persisted shut-off
  time exactly or `stale` (also when not shut off). `reason_code` is a short
  token; free-text reason stays on the server. On success: clear shut-off,
  persist `rearm_seq`, emit `enforcement_resumed` with `by:"server"` and
  `rearm_seq`, ack `applied` with `version=rearm_seq`.
- **No trusted time:** accept an otherwise valid rearm (exception to `not_now`;
  see registry). With trusted time, `expires_at` in the past is `expired`
  (reject code 22, now also used in v1).
- **Report:** `welfare {enforcement, shutoff_at?, escape_cycles, rearm_seq}`,
  optional `welfare_events[]`, device cap `rearm`.
- **Serial `rearm`:** physical caretaker clear (`by:"serial"`); clears
  persisted shut-off; does not change `rearm_seq`.
- **v2:** same fields as a signed CBOR (COSE) command when that record lands.
  Field names are centralized in firmware `wire_fields.h` for easy rename.
- **Vectors:** [`vectors/rearm.json`](vectors/rearm.json).

## 2026-11-03

### Auto shut-off: caretaker re-arm only (Cody)

Not a wire version bump. A fence move must not clear welfare auto shut-off.

- **Decision (Cody, Nov 3):** once `escape_cycle_limit` trips, enforcement
  stays off until a person re-arms that collar. A new boundary (`cue_rearm`)
  never clears shut-off or resets escape-cycle counters.
- **Caretaker path:** `cue_clear_shutoff` / serial `rearm` clears shut-off,
  resets the counters, and emits `enforcement_resumed`.
- **`cue.json`:** `rearm` is a new boundary only; new step
  `clear_shutoff`; case `boundary_change_does_not_clear_shutoff`;
  `auto_shutoff_after_three_escape_cycles` ends with caretaker clear.
- Docs and registry wording updated
  ([`docs/WELFARE-POLICY.md`](../docs/WELFARE-POLICY.md)).

## 2026-11-01

### Welfare safeguards (firmware; vectors + registry prep)

Not a wire version bump: welfare events are serial / local today. Cue rule and
`cue.json` document the behaviour so openpasture and the collar stay aligned.

- **Pulse cutoff:** at most `max_outside_cues` outside cues per crossing
  (default **3**), then silent until clear inside the geofence; still bounded
  by `outside_max_ms` (10 s).
- **Auto shut-off:** `escape_cycle_limit` escape→return cycles
  (default **3**) inside a fixed `escape_cycle_window_ms` (default **24 h**,
  starts at the first escape and resets after that window) turns enforcement
  off until an explicit caretaker re-arm (see 2026-11-03; provisional text
  here said a new boundary cleared it).
- **`cue.json`:** config carries the three welfare fields; cases
  `pulse_cutoff_after_three_outside_cues` and
  `auto_shutoff_after_three_escape_cycles`. Optional `expect.welfare` is
  documented for a later runner update.
- **Registry:** welfare event kinds `pulse_cutoff` / `returned` /
  `auto_shutoff` / `enforcement_resumed` reserved (codes 1–4); report uplink
  TBD.
- Thresholds are **conservative defaults that need animal-welfare review**
  before pulse hardware ships ([`docs/WELFARE-POLICY.md`](../docs/WELFARE-POLICY.md)).

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
