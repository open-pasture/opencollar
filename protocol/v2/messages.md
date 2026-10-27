# Messages

Protocol v2, **draft**. Part of the [v2 spec](README.md). The key words MUST, SHOULD and MAY
are used as in RFC 2119. The schema of everything here is [opencollar.cddl](opencollar.cddl);
every message has test vectors in [`../vectors/v2/`](../vectors/README.md#v2).

This is the transport-neutral layer, the part meant to outlast any radio: the same bytes
travel over LoRa ([lora.md](lora.md)), over LTE ([http.md](http.md)), over BLE from a phone,
and over a USB console. A transport may split them, batch them and retry them. It never
changes them.

## 1. Encoding

Every message is **deterministic CBOR** (RFC 8949 §4.2.1):

- integers, lengths and tags in their shortest form; definite lengths only;
- map keys sorted by their encoded bytes, never repeated;
- no floating point, no `undefined`, no tags except 18 (COSE_Sign1) where this spec says so;
  no payload, record, link section or beacon map holds a tag anywhere;
- every map's keys are unsigned integers (a reader that merges `0` and `false`, or drops a
  key it can't read, would read a different message);
- text is UTF-8;
- nesting at most 16 deep.

A receiver MUST refuse anything else (`bad_cbor`): decoding and encoding again gives back
exactly the bytes received, so a message has one encoding and a signature or tag covers one
thing. A sender MUST NOT build what has no deterministic encoding (a repeated key); the
reference encoder refuses to.

**Known fields are strict.** A field this version knows that is present with the wrong type
or outside its range (a battery of 255, a cue level of 0, a manifest `min_battery` of
`"90"`) makes its message or record `bad_cbor`. It is never read as if it were absent: a
default would silently replace what the sender meant. Unknown keys and unknown registry
values are a different thing (§8): they are kept or ignored.

Maps have small unsigned integer keys. **Quantities are integers in fixed units**, named in
each field:

| Quantity | Unit |
|---|---|
| Time | Unix seconds, UTC, from GNSS (leap seconds folded as GNSS-to-UTC does) |
| Coordinates | `[lon, lat]`, WGS 84, integers of 10⁻⁷ degree (`e7`). The same rounding v1 uses |
| Distances in a boundary | centimetres |
| Margins in reports | centimetres, signed: + inside, − outside |
| Accuracy | decimetres |
| Battery | percent, 0–100 |

Byte strings in the **JSON view** (logs, tools, vectors, schemas) are lowercase hex, names
come from the [registry](../registry.md), and a registry value the viewer doesn't know shows
as its number, so a consumer that keeps only JSON keeps the code.

## 2. Identifiers

`device_id`, `kid`, `herd_id` and `short` are defined in [identity.md](identity.md#2-identifiers).
A command names itself by its type and version; servers MAY add a `ref` (their own id, up to
16 bytes). An acknowledgement names a command by type and version, and by its **digest**: the
first 8 bytes of SHA-256 of the signed bytes as received.

## 3. Signed messages: COSE_Sign1

Every command and every signed document is a tagged COSE_Sign1 (RFC 9052) with EdDSA
(Ed25519, RFC 8032):

```
18([
  protected:   bstr .cbor { 1: -8, 4: kid },    ; alg EdDSA, the signer's 8-byte kid
  unprotected: {},                              ; always empty
  payload:     bstr .cbor payload-map,
  signature:   bstr .size 64
])

Sig_structure = [ "Signature1", protected, external_aad = "opencollar/2", payload ]
```

- The signature covers the payload **bytes as sent**. Nothing canonicalizes, nothing
  re-encodes. A relay carries the whole COSE_Sign1 as an opaque byte string.
- `external_aad` is the 12 ASCII bytes `opencollar/2`: a signature made for anything else
  with the same key, or for another version of this protocol, never verifies here.
- Key 0 of every payload is the **message type** ([registry](../registry.md#message-types)),
  inside the signature, so one type can never be taken for another.
- Receivers MUST refuse another `alg` and a `crit` header (`bad_sig`), and MUST ignore other
  protected header labels.
- The unprotected header MUST be an empty map (`bad_cbor`). Anything there would change the
  message's bytes, and so its digest and its LoRa message id, without touching the signature.

**Why COSE and not a custom envelope.** The envelope costs 22 bytes beyond the 64-byte
signature (tag, array, a 13-byte protected header and its length, payload length). A minimal custom one
(type, kid, signature) would save about 15 of them: under 10 % of a typical strip command,
and never a whole LoRa fragment. Commands are rare (a few a day), so the bytes don't matter;
interoperability does. COSE has libraries in C, Rust, Python, Go and JavaScript, a defined
key id and a defined way to bind context. A collar needs none of them: it reads four CBOR
items and streams `["Signature1", protected, "opencollar/2", payload]` into Ed25519, exactly
as firmware 0.2 streams v1's canonical JSON into SHA-512 today.

## 4. Commands (types 1–63)

What a collar obeys. Signed by the server key (a few types by the owner key or a new server
key, [§4.4](#44-who-may-sign-what)).

### 4.1 Common keys

| Key | Name | Type | |
|---|---|---|---|
| 0 | `type` | uint | Required. 1–63 |
| 1 | `herd` | bstr 1–16 | **Required.** The herd it is for. A membership or bind names the herd it moves the collar to |
| 2 | `device` | bstr 8 | Present: for this collar only. Absent: for every collar in `herd`. **Required** for config, membership, bind, resend and release (`bad_cbor` without it): they only ever concern one collar, and a herd-wide one would re-address or release a whole herd |
| 3 | `version` | uint 1–2³²−1 | Required ([§4.6](#46-versions)) |
| 4 | `issued_at` | uint | Required. When the server signed it |
| 5 | `expires_at` | uint | Optional. Refused (`expired`) when the collar's GNSS time has reached it; a staged boundary that expires before it takes effect is dropped. A collar with no GNSS time yet holds the command unapplied (`not_now`) until it has, then checks again: no clock never means "not expired" |
| 6 | `ref` | bstr ≤ 16 | Optional. The server's own id for it, echoed nowhere; for logs |
| 7 | `effective_at` | uint | Optional. When it takes effect, on the collar's GNSS clock. Absent: at once |
| 8–15 | | | Reserved for common keys |
| 16– | | | The type's own keys |

Unknown keys MUST be ignored. A server MUST NOT rely on a collar understanding a key or a
type the collar hasn't listed support for in its `caps` ([registry](../registry.md#caps)).

### 4.2 The types

**1 boundary**: the fence. Herd-wide, or one collar's own (`device`: an escape pen, a
per-collar copy). Same meaning as v1's boundary command: slots, activation, shape rules and
the cue rule are [v1's](../README.md#slots) unchanged.

| Key | Name | Type | |
|---|---|---|---|
| 16 | `outer` | ring | Required |
| 17 | `holes` | [ring] | Absent when none |
| 18 | `cue_mode` | uint | 1 `track` (evaluate, report, no sound). Absent: `audio`. 0 is never sent |
| 19 | `warn_cm` | uint ≤ 100 000 | Absent: the collar's default (500) |
| 20 | `hyst_cm` | uint ≤ 100 000 | Absent: the collar's default (100) |
| 21 | `policy` | uint ≥ 1 | The policy epoch the server checked it against ([§4.7](#47-zones-and-leases-what-the-collar-enforces-itself)) |

A **ring** is one flat integer array: the first vertex's `lon, lat` in e7, then for each
next vertex its difference from the one before. Unclosed; 3 or more vertices; winding
ignored. A 4-vertex strip is about 30 bytes, and the largest v1 shape (384 vertices) under
3 KB.

**2 config**: one collar's settings (`device` required).

| Key | Name | Type | |
|---|---|---|---|
| 16 | `report_s` | uint 10–3600 | Required. How often it reports |
| 17 | `fix_s` | uint 1–3600 | How often it takes a GNSS fix |
| 18 | `fast_report_s` | uint 10–3600 | During a fast window (a move, an escape) |
| 19 | `fast_fix_s` | uint 1–3600 | |
| 20 | `fast_until` | uint | The fast window ends at this GNSS time, with no further command. Needs `fast_report_s` |
| 21 | `endpoint` | tstr ≤ 256 | Anchors, stations, direct collars: where batches go. `https://` (bench builds also `http://`). Switched to as v1's endpoint is: after a first success, with a 24 h fallback |
| 22 | `endpoint_pin` | bstr 32 | SHA-256 of the server's TLS SubjectPublicKeyInfo ([identity.md §9](identity.md#9-frame-keys-and-transport-security)) |
| 23 | `track_s` | uint 0 or 60–86 400 | Send fix history every this many seconds; 0 or absent: never |
| 24 | `anchor_hold_s` | uint 600–86 400 | Anchors: how long one holds the herd's link ([lora.md §5](lora.md#5-anchors)) |

Anything out of range is `bad_config`.

**3 membership**: which herd the collar is in and its place there (`device` required).
Moving a collar to another herd is a membership naming that herd, with the same effect as
v1's herd change: staged boundaries of every other herd are dropped with no ack, and the
active boundary stays in force until one of the new herd applies.

| Key | Name | Type | |
|---|---|---|---|
| 16 | `short` | uint 1–65 534 | Required. Its address on the herd's LoRa link ([lora.md §3](lora.md#3-the-minute)) |
| 17 | `role` | uint | Required. 1 node, 2 anchor, 3 station |
| 18 | `net` | uint 0–65 535 | Required. The herd's LoRa network id |
| 19 | `plan` | uint | Channel plan ([lora.md §2](lora.md#2-radio)). Absent: 1 |
| 20 | `cycle_s` | uint | Report cycle on LoRa, a whole number of minutes, 60–3600. Absent: 300 |
| 21 | `rank` | uint | Anchors: takeover order, lowest first |
| 22 | `groups` | uint | How many groups of 300 short addresses the net uses, 1 to `cycle_s`/60. Absent: 1 ([lora.md §3](lora.md#3-the-minute)) |
| 23 | `beacon_key` | bstr 24 | The herd's beacon key, wrapped for this collar ([lora.md §9](lora.md#9-security-on-the-air)) |

`unsupported` for a channel plan the collar doesn't list in its device record. `bad_config`
for a short address of 0 or 65 535, an unknown role, a bad cycle, `groups` outside 1 to
`cycle_s`/60, or a short address whose group is not below `groups` (it would never send).
Every collar of a net MUST get the same plan, cycle and groups ([server.md §9](server.md#9-herds-on-lora)).

**4 roster**: the herd's collars, for its anchors (herd-wide).

| Key | Name | Type | |
|---|---|---|---|
| 16 | `members` | [[short, device_id, role]] | Required |
| 17 | `revoked` | [device_id] | Collars whose frames anchors drop |

**5 bind**, **6 handover**, **7 confirm**, **8 owner**, **11 release**: claiming a collar and
moving it between keys and software. [identity.md](identity.md).

**9 firmware**: install a release. [firmware.md](firmware.md#the-update-command).

**10 resend**: send records `from`..`to` (key 16, 17: seq, inclusive) again, if still held
(`device` required).

**12 zones**, **13 lease**: permanent no-go zones and the lease that lets staged boundaries
take effect ([§4.7](#47-zones-and-leases-what-the-collar-enforces-itself)).

**14 trust**: key 16 is a trust update (type 68), signed by a firmware key, for the
bootloader ([firmware.md](firmware.md#trust-updates)).

A type the collar doesn't implement is acked `rejected`, `unsupported`.

### 4.3 What a collar checks, in order

The first failure is the reject code:

1. More than 12 288 bytes: `too_large`.
2. The envelope ([§3](#3-signed-messages-cose_sign1)): `bad_cbor` (an unprotected header
   that isn't empty too), or `bad_sig` for another algorithm or a `crit` header.
3. The key: a trusted key with that kid (a bind is checked against the key it carries),
   else `unknown_kid`; the signature, else `bad_sig`.
4. The payload: deterministic CBOR in the profile of §1, a command type, `herd`, `version`,
   `issued_at`, `device` where required, and every known field present with its type and
   range: `bad_cbor`.
5. Who may sign it ([§4.4](#44-who-may-sign-what)).
6. A bind's claim: `bad_claim` ([identity.md §4](identity.md#4-claim)).
7. Scope: `device` another collar's (`wrong_collar`); `herd` another herd's, except a
   membership or bind (`wrong_herd`); `expires_at` reached (`expired`), or present with no
   GNSS time yet (`not_now`, held and checked again).
8. Versions ([§4.6](#46-versions)): issued before the collar's claim, or at or below the
   version held and not the very command held (`stale`).
9. The type's own rules: a boundary's shape ([v1's codes and order](../README.md#validation)),
   `bad_config` (a config, membership or handover out of range), `unsupported`.
10. For boundaries: the slot store (`slots_full`), then zones and lease when it would take
    effect ([§4.7](#47-zones-and-leases-what-the-collar-enforces-itself)): `in_exclusion`, or
    it waits.

### 4.4 Who may sign what

| Command | Signed by |
|---|---|
| bind | The new server key it carries, and only while unclaimed (`claimed`) |
| confirm | The pending handover key, naming the current key in `replaces` and the digest of the handover that staged it in `handover` (`bad_sig`) |
| handover, reason rotate | The current server key or the owner key |
| handover, reason transfer; release; owner | The owner key when one is enrolled; the server key only while none is (`unknown_kid`). A stolen server key can't erase the owner's recovery or sell the collar |
| everything else | The current server key alone (`unknown_kid`) |

### 4.5 Acknowledgements

A collar acknowledges every command it receives with an [ack record](#ack):

| | `received` | `applied` | `rejected` |
|---|---|---|---|
| boundary | staged for a later time | in effect (time = when it took effect, possibly while offline) | with the code |
| handover | staged, waiting for its confirm | confirmed: the new key is current | `expired` when the deadline passed |
| firmware | accepted, downloading | running and confirmed | with the code |
| anything else | – | done | with the code |

An ack carries the command's type, version and digest. When a command is refused before its
type and version can be read (`too_large`, `bad_cbor`, `bad_sig`), the ack has type 0 and
version 0 and the server matches it by digest. A repeated command (the same digest as the one
held for its type) is acked again with its current status, as in v1, and nothing is done
twice; another command at or below the held version is `stale`.

### 4.6 Versions

- Each collar keeps the highest version it holds **of each command type**, with the digest
  of the command that carried it, and reports them in its [device record](#device). A
  command whose version is at or below the one held for its type is `stale`, unless it is
  that very command (same digest), which is acked again; a boundary follows v1's slot rules
  (a version equal to one held is acked again with its current status).
- Herd-wide and per-collar commands of one type share the collar's version space, so a
  server MUST allocate versions that increase for every collar they reach. One counter per
  server for all herds is the simple way ([server.md §2](server.md#2-versions)).
- A claim (bind) starts every version over; a handover doesn't. The collar keeps the bind's
  `issued_at` as its **claim time** and refuses (`stale`) every later command issued before
  it, so the commands of an earlier claim can't be replayed after a reclaim, even by the
  same server key. A server's `issued_at` MUST NOT go backwards for a collar.

### 4.7 Zones and leases: what the collar enforces itself

A server checks every boundary against the farm's permanent no-go zones before it signs it
([server.md §11](server.md#11-farm-policy-zones-and-leases)). The collar does too, so a
change on the map reaches even a boundary that was signed and staged before it.

**Zones (type 12)**, herd-wide or for one collar: key 16 `zones`, an array of rings (the
boundary's ring encoding, 0–16 rings), and key 17 `epoch`, the farm's **policy epoch**, a
number the server raises with every change to its zones or the rules they encode. A zones
command is the whole set: it replaces what the collar held, and an empty list clears it.
Each zone follows v1's ring rules (`too_few_vertices`, `self_intersecting`, `zero_area`,
`out_of_range`); more zones or vertices than the collar's `zone_limits` is `too_many_holes`
or `too_many_vertices`, and the zones it held stay.

- The collar enforces every held zone as **a hole of whatever boundary is active**, always,
  with v1's cue rule (only a crossing is cued). A zone over the active strip takes effect at
  once.
- **A boundary may take effect** (on receipt if immediate, at `effective_at` if staged) only
  when, in order:
  1. its `policy` is not above the held zones' epoch. Otherwise it **waits**, staged: the
     collar lacks the newer zones;
  2. its fenced area (inside the outer ring, outside every hole) doesn't overlap a held zone:
     some point strictly inside both. Touching edges don't count, nor a zone carved out
     exactly as a hole. Otherwise it is acked `rejected`, `in_exclusion`, and the boundary in
     force stays;
  3. if it is **staged** (`effective_at` more than 600 s after `issued_at`) and names a
     `policy`, the collar holds a **lease** for the zones it holds that runs past now.
     Otherwise it waits, and never takes effect late without one; if its `expires_at` passes
     first it is dropped.

**Lease (type 13)**, herd-wide: key 16 `epoch`, key 17 `until` (GNSS time), key 18 `digest`
(the first 8 bytes of SHA-256 of the zones' key-16 value as encoded). It says: as of
`issued_at`, the farm's policy is still that epoch with those zones, until `until`. The
collar keeps the newest. A server sends one every 15 minutes or so, valid for the farm's
lease window (owner question 13).

So a no-go added now protects a collar in range at once, and a collar out of range from the
moment its lease runs out: it stops advancing its schedule and stays on the boundary it
holds. A boundary with no `policy` skips steps 1 and 3; step 2 always applies. Immediate
boundaries (an escape pen) need no lease. Collars that can do this list the cap `zones`; a
server MUST NOT rely on it for one that doesn't.

## 5. Signed documents (types 64–127)

Signed like commands, never obeyed:

| Type | Name | Signed by | Spec |
|---|---|---|---|
| 64 | factory record | maker key | [identity.md §3](identity.md#factory-record) |
| 65 | manifest | release or image key | [firmware.md](firmware.md#the-release-manifest) |
| 66 | batch | the sender's device key | [http.md](http.md#2-the-batch) |
| 67 | hello | the collar's device key | [lora.md §6](lora.md#6-join), [identity.md §4](identity.md#how-the-bind-reaches-the-collar) |
| 68 | trust update | a firmware key the bootloader trusts | [firmware.md](firmware.md#trust-updates) |

## 6. Records (up)

What a collar reports. Each record is a CBOR array:

```
[ type, seq, t, field, field, … ]
```

- `type` from the [registry](../registry.md#record-types).
- `seq`: the collar's sequence number, uint32. It counts every record the collar makes,
  of every type, starting at 0, for the life of the device, and never goes back or repeats:
  not on a reboot or a power cut, a release, a factory reset, a new claim, a handover, or a
  firmware update or rollback ([§7.1](#71-counters-that-never-repeat)). A server
  deduplicates on **(device, seq)** and asks for a gap again with a resend command.
- `t`: GNSS time, Unix seconds: of the fix, the cue, the start of an episode, or when the
  record was made.
- Fields by position. Optional fields at the end are left off; one in the middle is `null`.
- A reader MUST ignore elements past those it knows, MUST keep a record of a type it doesn't
  know (or skip it), and MUST keep an unknown registry value as its number. A known field
  present with the wrong type or out of range makes the record `bad_cbor` (§1).
- **One malformed record costs only itself**, never the frame or batch it came in. A
  reader finds each record of a frame by its extent (a well-formed CBOR item, RFC 8949
  §5.3.1) and decodes each on its own against this profile, so a record that breaks it (a
  float, a tag, a long head, a bad field) is dropped and counted while its neighbours are
  read. Only an item whose extent can't be found (truncated, indefinite length) loses the
  records after it in that frame.
- **Every record fits one frame.** A record is at most 109 bytes (plan 1's 128-byte uplink
  frame, less its 18 bytes and the records array's head). Fix histories hold as many fixes
  as fit. A **device** record or a **slots** list that would be longer goes in **parts**:
  each carries `part = [index, count]` (device key 16; slots element 4), all made at the
  same `t`, together one snapshot. A device snapshot's list keys (caps, versions, image
  keys, plans) may be cut across parts and are joined; every other key is in one part. A
  reader takes the snapshot once it has every part of a `t`. Texts in records are at most
  32 bytes.

| Type | Record | Fields after `type, seq, t` |
|---|---|---|
| 1 | <a id="status"></a>**status** | `lon, lat` (e7), `acc_dm`, `state` (fence state or null), `bver` (boundary version enforced, 0 for none), `battery` (% or null), `flags`? |
| 2 | **fixes** | `lon, lat, acc_dm` of the first fix (at `t`), then one flat array of `dt, dlon, dlat, acc_dm` for each next fix, differences from the one before (accuracy is not a difference) |
| 3 | **cue** | `kind`, `level` (1–4), `margin_cm`, `ring` (0 outer, 1.. holes), `bver`, `dur_ms`? |
| 4 | **episode** | `dur_s`, `bver`, `ring`, `cues`, `max_level`, `min_margin_cm`, `outcome` (`t` is its start) |
| 5 | <a id="ack"></a>**ack** | `type`, `version`, `status`, `code`?, `digest`? (8 bytes) |
| 6 | **health** | one map ([below](#health)) |
| 7 | <a id="device"></a>**device** | one map ([below](#device-1)) |
| 8 | **slots** | `[[version, status, effective_at?], …], part?`: every boundary held, `applied` (in effect) or `received` (staged, or due and waiting for zones or a lease) |
| 9 | **anchor** | one map: 1 `active` (bool), 2 `battery` (%), 3 `rsrp_dbm`, 4 `heard` (collars heard in the last hour), 5 `rank`, 6 `queue` (frames waiting to go up) |
| 10 | **firmware** | `state`, `version` (semver text), `digest`? (first 8 bytes of the image's), `code`? |

**Status flags** (bits): 1 armed, 2 escaping (the outside tone window), 4 charging, 8 in a
fast window, 16 stale (no fix this period; the position is the last known), 32 track mode.

A status record is about 30 bytes and one is sent every report period: it is what most of
the herd's airtime carries ([README](README.md#data-budget)).

<a id="health"></a>**Health** keys: 1 `fix_attempts`, 2 `fix_ok`, 3 `sats`, 4 `cn0_dbhz`,
5 `ttf_ds` (time to fix, tenths of a second), 6 `hdop_x10`, 7 `battery_mv`, 8 `charging`
(bool), 9 `temp_dc` (tenths of a °C), 10 `uptime_s`, 11 `reset` (text, e.g. `power_on`,
`watchdog`), 12 `still_s`, 13 `tilt_deg`, 14 `cell` {1 `rsrp_dbm`, 2 `rsrq_db`, 3 `snr_db`,
4 `mode` (`ltem`/`nbiot`), 5 `band`, 6 `cell_id`, 7 `tac`}, 15 `lora` {1 `rssi_dbm`, 2
`snr_db`, 3 `beacons` heard, 4 `missed`, 5 `frames` sent}, 16 `solar_mv`. Each only when
measured.

<a id="device-1"></a>**Device** keys (sent at boot, whenever any of it changes, and daily):
1 `class`, 2 `fw` (semver), 3 `caps` [text], 4 `limits` {1 `outer`, 2 `holes`, 3
`hole_vertices`, 4 `total`, 5 `slots`, 6 `slot_bytes`}, 5 `hw_rev`, 6 `server_kid`, 7
`pending_kid`, 8 `owner_kid`, 9 `versions` {type: highest version held}, 10 `herd`, 11
`short`, 12 `claim_nonce` (only while unclaimed), 13 `boot` (bootloader version), 14
`security_counter`, 15 `image_keys` [kid], 16 `part` [index, count], 17 `device_key` (bstr 32,
only while moving from v1, [identity.md §10](identity.md#10-from-v1)), 18 `plans` [channel
plan ids it can use], 19 `zone_limits` [zones, vertices in all zones]. `limits` are v1's
([../README.md](../README.md#limits)); a server fits shapes to them.

## 7. Frames: sealing records

Records travel in **frames**, the unit a transport carries end to end. An uplink frame is
the same bytes over LoRa, inside an anchor's batch over LTE, over BLE through a phone and
from a direct collar.

```
21 | net u16 | src u16 | fcnt u32 | link_len u8 | link | AES-128-CCM(records) | tag (8)
```

(Integers big-endian. The other frame kinds, `20` beacon, `22` fragment, `23` hello, belong
to the LoRa link: [lora.md](lora.md#4-frames).)

- `net`, `src`: the herd's network id and the sender's short address; both 0 for a
  direct collar with no LoRa link.
- `fcnt`: the frame counter. It counts every frame the collar ever seals, under every frame
  key, for the life of the device key, and never repeats ([§7.1](#71-counters-that-never-repeat)),
  so `(device_id, fcnt)` and the nonce below never repeat under any key.
- `link`: a CBOR map the anchor reads ([lora.md §7](lora.md#7-delivering-a-message-to-the-herd)):
  1 `got` [message id], 2 `need` [[message id, from, bitmap]]. Empty (`link_len` 0) when
  there is nothing to say.
- The rest is a CBOR array of records, encrypted and authenticated with **AES-128-CCM**
  (RFC 3610: 8-byte tag, 13-byte nonce, L = 2) under the collar's **frame key**
  ([identity.md §9](identity.md#9-frame-keys-and-transport-security)). Nonce: `device_id ‖
  fcnt ‖ 0x01`. Associated data: every byte before the ciphertext.

A frame that doesn't authenticate is dropped whole (the server counts it). Records inside
one that does are read one by one ([§6](#6-records-up)). No v2 frame of any kind is longer
than 255 bytes (a LoRa payload's limit), on any transport: a receiver refuses a longer one
(`too_large`) before it reads it.

### 7.1 Counters that never repeat

A collar keeps three **lifetime counters**: `seq` (records), `fcnt` (frames) and the batch
counter (anchors, stations and direct collars, [http.md §2](http.md#2-the-batch)). Each counts
from 0 for the life of the device key. They survive everything a collar goes through: reboots
and power cuts, release and factory reset, a new claim, a handover, firmware updates and
rollbacks. They live in a flash region no firmware image erases, in a layout every image
reads (it is frozen at manufacture, [README](README.md#frozen-at-manufacture)).

- **Write-ahead reservation.** A counter only hands out values below a reservation that is
  already durable in flash. When it reaches the reservation it first writes a new one (the
  reference uses 64 higher) and only then continues. After a reboot it resumes at the
  durable reservation, skipping whatever of the last block went unused. A power cut at any
  instant can skip values, never repeat one.
- **Atomic writes.** Each counter's reservation is two copies, each `[generation, value,
  CRC-32]`; a write goes to the copy with the older generation, a read takes the valid copy
  with the newer one, so a torn write leaves the previous reservation in force.
- **Never wrap.** A counter that would pass 2³² − 1 stops: the collar seals no more frames
  (or makes no more records) under that device key and reports it on its console. At a
  frame a minute that is 8 000 years away; it is a rule for broken counters.
- A **server** keeps, per device, the highest `fcnt` it accepted and which of the 128 below
  it it has seen, and drops a frame outside that or seen before (a replay); it keeps it for
  as long as it keeps the device ([server.md §7](server.md#7-acknowledgements-and-reports)).
  `seq` is the record's identity: a record with a `(device, seq)` already stored is a
  duplicate when its bytes are the same and a **conflict** when they aren't (kept aside and
  flagged, never silently dropped).

`op_protocol::v2::counter` is the reference (`Counter`, `Journal`, `ReplayWindow`), with a
test that cuts the power at every byte of every reservation write.

**Why a symmetric tag and not a signature.** An Ed25519 signature is 64 bytes. On a
30-byte status record it would nearly double each frame's time on air (46 bytes, 41 ms at
SF8/500 kHz, becomes about 100 bytes, 77 ms), and time on air is what sets how many collars
a channel holds; it would also put an Ed25519 signing on every report. The 8-byte CCM tag
costs an eighth of the bytes, and the frame key is per collar and shared only
with its server (static X25519 between the device key and the server key), so an anchor,
a phone or a neighbour on the radio can't forge or read another collar's reports. The 13
bytes of overhead (counter and tag) also buy confidentiality: livestock positions aren't
broadcast in clear to anyone with a receiver. What a tag doesn't give is proof to a third
party (the server could forge its own collars' reports); the device key's signatures on
hellos and batches, and [open question 4](README.md#open-questions), cover what needs that.

## 8. Extensibility

- **Unknown keys** in any map are ignored. **Unknown elements** at the end of a record are
  ignored. Senders never put a field whose meaning matters for safety in front of a
  receiver that hasn't listed it in its `caps`.
- **Unknown registry values** are kept as received, by number. A whole message is never
  refused for one: a record with an unknown cue kind is stored with that kind, an ack with an
  unknown status is taken and set aside.
- **Unknown command types** are acked `unsupported`; **unknown record types** are kept or
  skipped; **unknown frame kinds** are dropped.
- New keys, record fields, types and registry values are added by the rules in
  [registry.md](../registry.md#adding-to-a-registry). A change that would make a conforming
  receiver misread a message gets a new protocol version and a new `external_aad`.
