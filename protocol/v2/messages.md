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
- text is UTF-8;
- nesting at most 16 deep.

A receiver MUST refuse anything else (`bad_cbor`): decoding and encoding again gives back
exactly the bytes received, so a message has one encoding and a signature or tag covers one
thing.

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
come from the [registry](../registry.md), and an unknown registry value shows as `"other"`.

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
  unprotected: {},
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
  header labels.

**Why COSE and not a custom envelope.** The envelope costs 22 bytes beyond the 64-byte
signature (tag, array, a 14-byte protected header, payload length). A minimal custom one
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
| 2 | `device` | bstr 8 | Present: for this collar only. Absent: for every collar in `herd` |
| 3 | `version` | uint 1–2³²−1 | Required ([§4.6](#46-versions)) |
| 4 | `issued_at` | uint | Required. When the server signed it |
| 5 | `expires_at` | uint | Optional. Refused (`expired`) when the collar's GNSS time has reached it; a staged boundary that expires before it takes effect is dropped |
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

`bad_config` for a short address of 0 or 65 535, an unknown role or a bad cycle.

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

A type the collar doesn't implement is acked `rejected`, `unsupported`.

### 4.3 What a collar checks, in order

The first failure is the reject code:

1. More than 12 288 bytes: `too_large`.
2. The envelope ([§3](#3-signed-messages-cose_sign1)): `bad_cbor`, or `bad_sig` for another
   algorithm.
3. The key: a trusted key with that kid (a bind is checked against the key it carries),
   else `unknown_kid`; the signature, else `bad_sig`.
4. The payload: deterministic CBOR, a command type, `herd`, `version`, `issued_at` and the
   type's required fields with the right types: `bad_cbor`.
5. Who may sign it ([§4.4](#44-who-may-sign-what)).
6. A bind's claim: `bad_claim` ([identity.md §4](identity.md#4-claim)).
7. Scope: `device` another collar's (`wrong_collar`); `herd` another herd's, except a
   membership or bind (`wrong_herd`); `expires_at` reached (`expired`).
8. The type's own rules: a boundary's shape ([v1's codes and order](../README.md#validation)),
   `bad_config`, `unsupported`.
9. Versions ([§4.6](#46-versions)): `stale`; then, for boundaries, the slot store
   (`slots_full`).

### 4.4 Who may sign what

| Command | Signed by |
|---|---|
| bind | The new server key it carries, and only while unclaimed (`claimed`) |
| confirm | The pending handover key, naming the current key in `replaces` (`bad_sig`) |
| handover, release | The current server key or the owner key |
| owner | The owner key; the server key only while no owner key is enrolled |
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
version 0 and the server matches it by digest. A repeated command is acked again with its
current status, as in v1.

### 4.6 Versions

- Each collar keeps the highest version it holds **of each command type** and reports them
  in its [device record](#device). A command whose version is at or below the one held for
  its type is `stale`, except a boundary, which follows v1's slot rules (a version equal to
  one held is acked again with its current status).
- Herd-wide and per-collar commands of one type share the collar's version space, so a
  server MUST allocate versions that increase for every collar they reach. One counter per
  server for all herds is the simple way ([server.md §2](server.md#2-versions)).
- A claim (bind) starts every version over; a handover doesn't.

## 5. Signed documents (types 64–127)

Signed like commands, never obeyed:

| Type | Name | Signed by | Spec |
|---|---|---|---|
| 64 | factory record | maker key | [identity.md §3](identity.md#factory-record) |
| 65 | manifest | release or image key | [firmware.md](firmware.md#the-release-manifest) |
| 66 | batch | the sender's device key | [http.md](http.md#2-the-batch) |
| 67 | hello | the collar's device key | [lora.md §6](lora.md#6-join), [identity.md §4](identity.md#how-the-bind-reaches-the-collar) |

## 6. Records (up)

What a collar reports. Each record is a CBOR array:

```
[ type, seq, t, field, field, … ]
```

- `type` from the [registry](../registry.md#record-types).
- `seq`: the collar's sequence number, uint32. It counts every record the collar makes,
  of every type, starting at 0, and never goes back or repeats: a collar writes each record
  to flash before sending it and continues from the last one written after a reboot. A
  server deduplicates on **(device, seq)** and asks for a gap again with a resend command.
- `t`: GNSS time, Unix seconds: of the fix, the cue, the start of an episode, or when the
  record was made.
- Fields by position. Optional fields at the end are left off; one in the middle is `null`.
- A reader MUST ignore elements past those it knows, MUST keep a record of a type it doesn't
  know (or skip it), and MUST read an unknown registry value as "other". One malformed
  record costs only itself, never the frame or batch it came in.

| Type | Record | Fields after `type, seq, t` |
|---|---|---|
| 1 | <a id="status"></a>**status** | `lon, lat` (e7), `acc_dm`, `state` (fence state or null), `bver` (boundary version enforced, 0 for none), `battery` (% or null), `flags`? |
| 2 | **fixes** | `lon, lat, acc_dm` of the first fix (at `t`), then one flat array of `dt, dlon, dlat, acc_dm` for each next fix, differences from the one before (accuracy is not a difference) |
| 3 | **cue** | `kind`, `level` (1–4), `margin_cm`, `ring` (0 outer, 1.. holes), `bver`, `dur_ms`? |
| 4 | **episode** | `dur_s`, `bver`, `ring`, `cues`, `max_level`, `min_margin_cm`, `outcome` (`t` is its start) |
| 5 | <a id="ack"></a>**ack** | `type`, `version`, `status`, `code`?, `digest`? (8 bytes) |
| 6 | **health** | one map ([below](#health)) |
| 7 | <a id="device"></a>**device** | one map ([below](#device-1)) |
| 8 | **slots** | `[[version, status, effective_at?], …]`: every boundary held, `applied` (in effect) or `received` (staged) |
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
`security_counter`, 15 `image_keys` [kid]. `limits` are v1's ([../README.md](../README.md#limits));
a server fits shapes to them.

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
- `fcnt`: the frame counter. It MUST never repeat under one frame key: a collar persists a
  high-water mark at least every 64 frames and resumes 64 above it after a reboot.
- `link`: a CBOR map the anchor reads ([lora.md §7](lora.md#7-delivering-a-message-to-the-herd)):
  1 `got` [message id], 2 `need` [[message id, from, bitmap]]. Empty (`link_len` 0) when
  there is nothing to say.
- The rest is a CBOR array of records, encrypted and authenticated with **AES-128-CCM**
  (RFC 3610: 8-byte tag, 13-byte nonce, L = 2) under the collar's **frame key**
  ([identity.md §9](identity.md#9-frame-keys-and-transport-security)). Nonce: `device_id ‖
  fcnt ‖ 0x01`. Associated data: every byte before the ciphertext.

A frame that doesn't authenticate is dropped whole (the server counts it). Records inside
one that does are read one by one ([§6](#6-records-up)).

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
- **Unknown registry values** read as "other" and are kept as received. A whole message is
  never refused for one: a record with an unknown cue kind is stored with that kind, an ack
  with an unknown status is taken and set aside.
- **Unknown command types** are acked `unsupported`; **unknown record types** are kept or
  skipped; **unknown frame kinds** are dropped.
- New keys, record fields, types and registry values are added by the rules in
  [registry.md](../registry.md#adding-to-a-registry). A change that would make a conforming
  receiver misread a message gets a new protocol version and a new `external_aad`.
