# Collar protocol, v1

How software talks to an OpenCollar: boundaries and configuration go down,
acks and position reports come up. Any software that speaks this can run the
collars; openpasture is the first. Its side of the same formats is
[`crates/op-protocol`](https://github.com/open-pasture/openpasture/tree/main/crates/op-protocol)
and the
[Device endpoints](https://github.com/open-pasture/openpasture/blob/main/docs/API.md#device-endpoints-collars)
section of `docs/API.md` in open-pasture/openpasture. The server contract they
grew from is in [`contracts.md`](contracts.md).

Status: firmware 0.2 implements everything here and checks it against the
shared test vectors. Boundary download over LTE waits for the SIM; until then
a signed command can be pasted on the serial console (see Provisioning).

## Principles

- **Fence logic runs on the collar.** The collar holds its boundary and cues
  the animal without the network. The server only changes what the boundary is.
- **The collar keeps the last good boundary.** A lost connection, a bad
  message, a power cut or a reboot never leaves an animal without a fence.
- **Versions only go up.** A collar accepts only versions above every version
  it holds.
- **Everything is signed and acknowledged.** A boundary counts as active only
  once the collar reports it applied.
- **GNSS time is the collar's only clock** for when a boundary takes effect.
  Nothing unsigned from a server sets it.
- **Only a crossing is cued.** See below.

## Collar rule: only cue a crossing

The collar cues "outside" only when the animal goes from inside (or the
warning zone) to outside under the boundary it holds.

- At boot and whenever a new boundary is applied, the fence is **unarmed**. The
  first fix inside the fenced area arms it. If that fix is in the warning
  zone, the warning cue plays at once, which is how a moved boundary pushes an
  animal.
- While unarmed and outside, the collar is silent and reports state `outside`.
  A boundary that leaves an animal outside never cues it.
- A crossing cues the outside tone for up to 10 s, then disarms. An animal
  walking back in is not cued in the warning zone on its way; a fix clear of
  the warning zone arms the fence again.
- Warning-zone cues are otherwise unchanged: louder toward the edge, at most
  20 s of continuous cueing, then 30 s of rest.
- Holes work the same way: walking into a hole is a crossing (outside tone up
  to 10 s, then disarm). A hole drawn on top of an animal leaves it outside
  after rearm: silent while it walks out, armed once clear.

Why: an audio cue only teaches when the animal can escape it by moving away
from the edge. A fence drawn on top of an animal, or behind it, gives no
direction, only noise. In the firmware this is `cue.c`.

## Limits

| Limit | LEGACY (fw 0.1, no `caps`) | V0 (nRF9151, fw 0.2) | V1 (+16 MB NOR) |
|---|---|---|---|
| Outer ring vertices | 3–64 | 3–128 | 3–128 |
| Holes | 0 | ≤ 16 | ≤ 16 |
| Vertices per hole | – | 3–32 | 3–32 |
| Total vertices | 64 | ≤ 384 | ≤ 384 |
| Slots (1 active + staged) | 2 | 16 | 32 |
| Slot bytes (all held records) | – | ≤ 24 576 | ≤ 262 144 |
| Command size | – | ≤ 12 288 bytes | ≤ 12 288 bytes |
| Ids (`command_id`, `herd_id`, `collar_id`) | ≤ 64 bytes | ≤ 64 bytes | ≤ 64 bytes |

A slot record takes 192 bytes plus 8 per vertex (`int32` lon and lat × 1e7,
lossless because the server rounds to 7 decimals): 3 264 bytes at most, under
400 for a typical strip. Vertex counts are taken after conversion to e7 with
consecutive duplicates and a closing vertex removed.

## Boundary command (down)

```json
{
  "command_id": "bnd_01J8...",
  "herd_id": "herd_01J7...",
  "collar_id": "col_01J9...",
  "version": 57,
  "effective_at": "2026-09-27T12:00:00Z",
  "boundary": [[-92.41,38.12],[-92.4,38.12],[-92.4,38.13],[-92.41,38.13]],
  "holes": [[[-92.406,38.124],[-92.404,38.124],[-92.404,38.126]]],
  "cue_mode": "track",
  "warn_m": 5.0,
  "hysteresis_m": 1.0,
  "sig": "base64..."
}
```

- Rings are unclosed `[longitude, latitude]` arrays, WGS 84, at most 7
  decimals. Winding is ignored. `holes` is omitted when empty.
- `herd_id`: the herd the boundary is for. A collar rejects another herd's
  boundary (`wrong_herd`). Commands without it (older servers) are accepted.
- `collar_id`: only on one collar's own boundary (escape pens, per-collar
  restaged copies). Signed, so it can't be replayed to another collar.
- `cue_mode`: `audio` (the default, never sent) or `track`: evaluate the
  fence and report state, with no sound, no cues and no episodes.
- `effective_at`: absent means now. Whole seconds, `Z`.
- `warn_m`, `hysteresis_m`: absent means the collar's defaults (5 m, 1 m).
- Every new field is optional and omitted when empty or default, so a
  V0-shaped command serializes byte for byte as it did before v1.
- **Negotiation:** the server never sends a field that is not in the collar's
  `caps` (`holes`, `slots`, `collar_id`, `cue_mode`, `episodes`, `config`).
  LEGACY collars get the outer ring fitted to 64 vertices with holes dropped;
  the server's own fence for that collar uses the same ring.

### Signing

Ed25519 over `canonical_json(command without "sig")`: object keys sorted
bytewise, no whitespace outside strings, strings and numbers exactly as
serde_json writes them (shortest round trip, so `5.0` stays `5.0` and tiny
values print as `1e-7`). The server's wire body is serde_json compact output,
so every token on the wire is already canonical; the collar only reorders
keys and strips whitespace.

How the collar checks it, without building a JSON tree: objects occur only at
the top level, so it records up to 16 top-level key/value spans, sorts them
by key bytes and streams `{"key":value,...}` (value tokens copied verbatim,
whitespace outside strings removed, `sig` left out) straight into SHA-512
(Monocypher: `crypto_sha512_*`, `crypto_eddsa_reduce`,
`crypto_eddsa_check_equation`). Unknown top-level keys are signed and ignored.
Numbers may use exponents (`1e-7`); coordinates are converted to e7 integers
exactly from the decimal text, with no float round trip (half away from
zero).

Checked in this order; the first failure is the rejection code:

1. `too_large`: more than 12 288 bytes.
2. `bad_json`: not UTF-8; not one JSON object; a nested object anywhere
   (inside arrays too); arrays nested deeper than 4; a key with a backslash
   escape; a duplicate key; more than 16 keys; anything after the object; a
   raw control character in a string.
3. `bad_sig`: no `sig`; `sig` not a plain base64 string of 64 bytes (standard
   alphabet, canonical padding); a signature that doesn't verify with the
   server key from provisioning.
4. `bad_json`: the fields don't make a command: wrong types, a missing
   `command_id`, `version` or `boundary`, an id empty or over 64 bytes.

Then, in the slot store: `wrong_herd`, `wrong_collar`, re-ack or `stale`, the
shape rules, `slots_full`.

## Validation

A rejected command is acked `rejected` with a `code`. Every code except
`slots_full` is permanent: the server doesn't offer that version to that
collar again.

- `bad_sig` · `wrong_herd` (herd_id present and not the collar's) ·
  `wrong_collar` (collar_id present and not the collar's) · `bad_json` ·
  `too_large` · `stale` (version below the highest held; a version equal to
  one held is re-acked with that version's current status instead)
- `out_of_range` (|lon| > 180, |lat| > 90) · `too_few_vertices` (a ring with
  fewer than 3 distinct vertices) · `too_many_vertices` (per ring or total) ·
  `too_many_holes`
- `self_intersecting` · `rings_cross` (touching counts) · `hole_outside`
  (every hole strictly inside the outer ring) · `holes_overlap`
- `zero_area` (outer ring under 1 m²) · `hole_too_small` (under 100 m²) ·
  `hole_too_close` (any two rings closer than **2 · warn_m + 2 m**, 12 m at
  the defaults, so no corridor is all warning zone)
- `bad_margins` (warn_m or hysteresis_m not finite or outside 0–1000) ·
  `slots_full` (no free slot, or the record doesn't fit the slot bytes left
  after pruning dead slots) · `bad_config` (config only)

The shape rules run in this order: `bad_margins`, `too_many_holes`,
`out_of_range`, `too_few_vertices`, `too_many_vertices`, `self_intersecting`,
`rings_cross`, `hole_outside`, `holes_overlap`, `zero_area`,
`hole_too_small`, `hole_too_close`.

How: topology (crossings, containment) with exact int64 orientation tests on
the e7 integers (each product is a longitude difference times a latitude
difference, under 2^63, and products are compared, not subtracted).
Containment of a hole is tested with its first vertex. Areas and gaps are
single precision in metres, projected about the outer ring's first vertex
(`kx = (float)(M_PER_DEG_LAT · cos(lat0) · 1e-7)`, `ky = (float)(M_PER_DEG_LAT
· 1e-7)`, `M_PER_DEG_LAT = 6 371 008.8 · π / 180`); an area is the fan sum from
the ring's first vertex, the gap between rings the least vertex-to-edge
distance. The firmware is built without fused multiply-add, so its
single-precision steps match openpasture's `op_geo::shape` operation for
operation (only `cos` comes from each side's own maths library, before the
result is rounded to single precision). The server checks gaps
against 2 · warn_m + 2.5 m, so rounding never makes a collar reject what the
server accepted.

## Geofence and cues

- Every ring is projected about the outer ring's first vertex (doubles).
  Inside = inside the outer ring and outside every hole, even-odd per ring.
  The margin is ± the distance to the nearest edge of any ring, positive
  inside; `nearest_ring` is 0 for the outer ring, 1.. for holes.
- The state machine, hysteresis and accuracy gating (fixes worse than 10 m
  don't change state) are those of firmware 0.1; the warning zone runs along
  hole edges too.
- Cue kinds: `warn` and `outside`. The boot chirp is not a cue.
- Episode: a run of armed warning cues, ending `turned_back` (reached
  inside), `crossed`, `rest` (the 20 s cap) or `boundary_changed`.

## Slots

The boundary in effect at time t is the **highest version whose activation
time (effective_at, else the time it was received) is at or before t**. A
staged version is **dead** when a higher version activates at or before it.

- **Accept** only versions above every version held.
- **Immediate** (no effective_at, or it has passed on the GNSS clock):
  validate, swap into the fence, rearm the cue, persist, drop every lower
  version, ack `applied`.
- **Future:** persist as staged, ack `received`, prune dead slots. No free
  slot or not enough slot bytes after pruning: `slots_full`.
- **Tick** on every fix, with that fix's GNSS UTC: apply the highest due
  version, drop lower ones, ack `applied` with the real apply time. Staged
  slots that are superseded get no ack; `slots` in the next report is the
  ground truth.
- **Reboot:** load the records, check format and CRC, enforce the latest
  active boundary at once (no clock needed); staged slots wait for the first
  GNSS fix.
- **First boot with no boundary:** no cues; fixes go up without
  `boundary_version`; poll every 60 s; the collar never invents a fence. An
  unprovisioned collar runs GNSS only.
- Any immediate boundary (sweep step, pen, farmer draw) drops lower staged
  slots, so the server re-stages schedules above it. A pen (`collar_id`
  command) drops that collar's staged slots; when the escape ends the server
  restages per-collar copies.

### Persistence

Zephyr NVS on a 64 KB `storage` partition, by id: 1 provisioning, 2 pending
acks, 3 config, 0x100 + i slot i (one id more than the slot count, so a new
record is always written before the records it replaces are deleted). An
entry counts once it is completely written, so a power cut leaves the old
record or the new one, and boot tidies up whatever a cut left behind. The
store is behind `store.h`, so a NOR backend can replace NVS.

Slot record: a 192-byte header, then the vertices, outer ring first.

| Offset | Field |
|---|---|
| 0 | magic `OCS1` |
| 4 | format (1) |
| 5 | flags: applied, track, collar-scoped, has herd, has effective_at, has received_at, has applied_at |
| 6 | holes |
| 7 | outer ring vertices |
| 8 | total vertices (u16) |
| 10, 11 | command_id length, herd_id length |
| 12 | version (u32) |
| 16, 20, 24 | effective_at, received_at, applied_at (u32 Unix seconds) |
| 28, 36 | warn_m, hysteresis_m (f64) |
| 44 | hole lengths [16] |
| 60 | command_id [64] |
| 124 | herd_id [64] |
| 188 | CRC-32 of the whole record, this field zero |

## Endpoints

HTTP + JSON, `Authorization: Bearer <collar key>`.

- `GET /collar/v1/boundary?have=<highest version held, applied or staged>&free=<slots − held>&free_bytes=<slot bytes left>`
  → 200 with a command, or 204. The server picks:
  1. The collar's boundary set: its herd's boundaries, or its own
     `collar_id` boundaries while on an escape, split by the rule above into
     the active one A and the alive staged ones S (ascending).
  2. Leave out versions this collar rejected with a permanent code.
  3. If A.version > have, serve A.
  4. Else if `free` > 0 (absent = LEGACY, 1) and the lowest s in S with
     s.version > have fits `free_bytes` (absent = no byte limit), serve s.
  5. Else 204.
- `POST /collar/v1/ack` `{ command_id, version, status: received|applied|rejected, reason?, code?, at }`.
  `at` is the real apply time for `applied` (GNSS time, possibly in the past
  for a boundary applied offline); acks without GNSS time carry modem network
  time. Pending acks survive a reboot (NVS id 2) until delivered. When a
  command fails before its fields can be trusted (`bad_sig`, `bad_json`), the
  collar still acks it if its `command_id` and `version` can be read.
- `POST /collar/v1/report` → `{ latest_version, config? }`. `latest_version`
  is the highest alive version for this collar. `config` carries the collar's
  current signed config command when the report's `device.config_version` is
  lower or absent and the collar has the `config` cap. There is no unsigned
  server time or herd id: herd changes arrive only through the signed config,
  and nothing unsigned sets the collar's clock.

## Config command (down, inside the report response)

```json
{
  "command_id": "cfg_01J9...",
  "collar_id": "col_01J9...",
  "version": 3,
  "herd_id": "herd_01J7...",
  "endpoint": "https://farm.example.com/collar/v1",
  "report_s": 60,
  "poll_s": 60,
  "fast_report_s": 10,
  "fast_poll_s": 10,
  "fast_until": "2026-09-27T13:10:00Z",
  "sig": "base64..."
}
```

- A flat object, scanned, signed and canonicalized exactly like a boundary
  command. `command_id`, `collar_id`, `version`, `report_s` and `poll_s` are
  required.
- Checks, in order: ids (`bad_json`), `wrong_collar`, `stale` (version at or
  below the one held), `bad_config` (an interval outside 10–3600 s,
  `fast_until` without both fast intervals, an endpoint that isn't
  `https://…` or is over 256 bytes).
- `herd_id` replaces the provisioning herd for `wrong_herd` checks.
- `report_s`/`poll_s` are the base cadence. `fast_*` apply until `fast_until`
  (GNSS time), then the collar returns to base without another command, so a
  collar that loses contact mid-sweep doesn't stay in fast mode. With no GNSS
  time since boot the base cadence applies.
- `endpoint`: absent keeps the current one. A new one is used from the next
  report; the first successful report there makes it the endpoint, and if it
  has failed for 24 h the collar goes back to the previous one, so a bad URL
  never strands it.
- The collar persists the config (NVS id 3), applies it at boot and reports
  `device.config_version`. A rejected config is reported once as
  `device.config_reject {version, code}`, and the server stops resending that
  version.

## Position report (up)

Sent on the report cadence. Fixes are batched. Every field added in v1 is
optional.

```json
{
  "boundary_version": 57,
  "device": {"fw": "0.2.0", "caps": ["holes","slots","collar_id","cue_mode","episodes","config"],
             "limits": {"outer":128,"holes":16,"hole_vertices":32,"total":384,"slots":16,"slot_bytes":24576},
             "config_version": 3},
  "slots": [{"version":57,"status":"applied"},{"version":58,"status":"received","effective_at":"2026-09-27T12:00:00Z"}],
  "fixes": [{"at":"…","point":[-92.405,38.124],"accuracy_m":1.8,"sats":9,"cn0":41.0,"hdop":0.9}],
  "cues": [{"at":"…","kind":"warn","level":2,"dur_ms":300,"margin_m":1.4,"ring":2,"boundary_version":57}],
  "episodes": [{"start":"…","end":"…","boundary_version":57,"ring":2,"cues":4,"max_level":3,"min_margin_m":0.8,"outcome":"turned_back"}],
  "battery": 0.81,
  "health": {"fix_attempts":120,"fix_ok":118,
             "cell": {"rsrp_dbm":-104,"rsrq_db":-11,"snr_db":6,"mode":"ltem","band":12,"cell_id":"1A2B3C","tac":1234,"at":"…"},
             "still_s":40,"tilt_deg":12,"temp_c":21.5,"battery_v":3.31,"charging":true,"uptime_s":86400,"reset":"power_on"}
}
```

- `boundary_version`: the fence the collar is enforcing. On cues and
  episodes always; on fixes only when it differs from the report's (a staged
  boundary applied offline can split one batch).
- `slots` present is the complete list the collar holds (the server replaces
  its record of them); absent means unknown (LEGACY).
- `cell` only when measured (never on GNSS-only boards). `still_s` and
  `tilt_deg` only with an IMU.
- Training mode has no collar flag: only `warn_m` changes.

## Provisioning over USB serial

The collar's card carries a QR code with one compact JSON payload:

```json
{"v":1,"c":"<collar id>","h":"<herd id>","k":"<collar key>","e":"<base>/collar/v1","s":"<server public key, base64>"}
```

The collar reads lines on its console UART (the board's USB serial, 115 200
baud). A handheld USB scanner in keyboard mode types the QR into a serial
terminal, so a printed card is enough to set up a collar. Physical access is
ownership: provisioning is allowed at any time.

| Line | Reply |
|---|---|
| `provision <payload>` | `ok <collar id>`, or `error <code>` |
| `status` | `collar <id> herd <id> fw 0.2.0 config <version or -> active <version or -> slots <versions or ->` (`unprovisioned fw 0.2.0` before provisioning) |
| `boundary <command>` | `applied <version>`, `received <version>`, `rejected <version> <code>`, or `error <code>`: the same path as a download |
| `config <command>` | `ok <version>`, or `error <code>`: the same path as a report response |

Provisioning checks the payload in this order, each failure being its code:
`bad_json` (not a flat JSON object), `bad_version` (`v` is not 1),
`bad_collar_id` / `bad_herd_id` (not a string of 1–64 bytes), `bad_key` (`k`
not 16–128 printable ASCII characters), `bad_endpoint` (`e` not `https://…`
or over 256 bytes), `bad_server_key` (`s` not base64 of 32 bytes). Unknown
keys are ignored. A valid payload wipes slots, config and pending acks first
(no boundary, so no cues), then is stored as sent in NVS id 1
(`error store_failed` if the flash write fails) and checked again at every
boot. Other replies: `error unprovisioned`, `error too_long`, `error
unknown_command`.

## Test vectors

openpasture writes them (`crates/op-protocol/tests/vectors/`, regenerated by
`OP_WRITE_VECTORS=1 cargo test -p op-protocol --test vectors`) and the
firmware copies them byte-identical into `firmware/tests/host/vectors/`. Both
sides run every case. Signing key: Ed25519 seed bytes `00 01 02 … 1f`.

| File | Cases |
|---|---|
| `commands.json` | wire text as received: V0 shape, holes, collar_id, compact and pretty, shuffled keys, `1e-7`, tampered and stripped fields, duplicate keys, nested objects, more than 16 keys, oversize; expected code and canonical bytes |
| `config.json` | valid, missing collar_id, wrong collar, stale, bad intervals, http endpoint, duplicate keys |
| `shapes.json` | each shape code minimal, exact limit passes and limit + 1 fails, both windings, gaps at ±0.1 m |
| `geofence.json` | margins (1 mm), inside, nearest ring, around and inside holes |
| `slots.json` | supersede, dead prune, duplicate re-ack, stale, slots_full by count and by bytes, boot without clock, wrong collar |

## Transport

HTTP + JSON over LTE-M for now, to the endpoint from provisioning or config.
The messages may map one to one onto CBOR later.
