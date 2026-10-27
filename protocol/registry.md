# Registry

Every name and number with a fixed meaning on the wire, for v1 (JSON, by name) and v2
(CBOR, by number; the JSON view uses the name). `v` is the protocol version that introduced
it. This file is the source; op-protocol's `v2::registry` module follows it.

## Extensibility

These rules are what let collars and servers of different ages and makers work together:

1. **Unknown fields are ignored**: JSON keys, CBOR map keys, and elements past the end of a
   v2 record.
2. **Unknown values are kept, never refused.** A value from any table below that the
   receiver doesn't know is stored as sent (v1) or kept as its number (v2; the JSON view shows
   the number, not a name). One unknown value never makes a whole report, ack, record, frame
   or batch invalid. A known field with the wrong type or out of range is not an unknown
   value: it makes its record or message `bad_cbor`.
   A collar receiving an unknown value in a command does refuse that command (`bad_cbor`,
   `unsupported`): a collar must not guess how to cue.
3. **Capabilities gate meaning.** A server never sends a field, command type or value whose
   meaning matters for the animal to a collar that hasn't listed the cap for it.
4. **Numbers and names are never reused.** A retired entry stays here, marked retired.
5. A change that would make a conforming receiver misread a message is a new protocol
   version, with a new `external_aad` (`opencollar/3`).

### Adding to a registry

Open a pull request against `opencollar/protocol/` that adds the entry here with its
number, name, the version it appears in and its meaning, adds it to the spec text and to
`v2/opencollar.cddl`, and adds a test vector. Anyone may; the protocol is meant for other
collar makers and other farm equipment too. For experiments before that, use the private
ranges: caps starting `x-`, message types 48–63 and 112–127, record types 96–127, reject
codes 200–255. Private values never appear in shipped products.

## <a id="caps"></a>Caps

What a collar can do, in `device.caps` (v1) or the device record's `caps` (v2).

| Cap | v | Means the collar |
|---|---|---|
| `holes` | 1 | holds boundaries with holes |
| `slots` | 1 | holds staged boundaries and reports them |
| `collar_id` | 1 | takes boundaries for itself alone (v1 `collar_id`, v2 `device`) |
| `cue_mode` | 1 | takes `cue_mode` (track mode) |
| `episodes` | 1 | reports episodes |
| `config` | 1 | takes signed config commands |
| `sim` | 1 | **is simulated**, not a collar on an animal. A server shows everything from it as simulated and keeps it out of anything that describes real animals. A simulated collar MUST list it |
| `v2` | 2 | speaks v2 messages (a v1 collar that has been updated) |
| `fixes` | 2 | sends fix history blocks (`track_s`) |
| `firmware` | 2 | takes firmware update commands |
| `handover` | 2 | takes handover and confirm commands |
| `owner` | 2 | takes an owner key |
| `imu` | 2 | reports motion (`still_s`, `tilt_deg`) |
| `zones` | 2 | holds permanent no-go zones, checks boundaries against them and takes staged ones only under a lease ([messages.md §4.7](v2/messages.md#47-zones-and-leases-what-the-collar-enforces-itself)) |

**What a v2.0 collar on an animal must list:** `v2`, `holes`, `slots`, `collar_id`,
`cue_mode`, `episodes`, `config`, `firmware`, `handover`, `owner`, `zones`. Optional:
`fixes`, `imu`. A server may refuse to claim a collar for an animal without the required set,
and MUST NOT rely on a cap it doesn't list.

## <a id="message-types"></a>Message types (v2, payload key 0)

| Code | Name | Kind | Signed by | Spec |
|---|---|---|---|---|
| 1 | `boundary` | command | server | [messages.md](v2/messages.md#42-the-types) |
| 2 | `config` | command | server | " |
| 3 | `membership` | command | server | " |
| 4 | `roster` | command | server | " |
| 5 | `bind` | command | the new server key | [identity.md](v2/identity.md#4-claim) |
| 6 | `handover` | command | server or owner; a transfer: owner, or the server while no owner key is enrolled | [identity.md](v2/identity.md#6-handover-rotating-the-server-key-or-moving-to-other-software) |
| 7 | `confirm` | command | the pending key | " |
| 8 | `owner` | command | owner (server while none) | " |
| 9 | `firmware` | command | server | [firmware.md](v2/firmware.md#the-update-command) |
| 10 | `resend` | command | server | [messages.md](v2/messages.md#42-the-types) |
| 11 | `release` | command | owner, or the server while no owner key is enrolled | [identity.md](v2/identity.md#7-release-and-factory-reset) |
| 12 | `zones` | command | server | [messages.md §4.7](v2/messages.md#47-zones-and-leases-what-the-collar-enforces-itself) |
| 13 | `lease` | command | server | " |
| 14 | `trust` | command | server (the update inside: a firmware key) | [firmware.md](v2/firmware.md#trust-updates) |
| 48–63 | | command | | private use |
| 64 | `factory` | document | maker | [identity.md](v2/identity.md#factory-record) |
| 65 | `manifest` | document | release or image key | [firmware.md](v2/firmware.md#the-release-manifest) |
| 66 | `batch` | document | the sender's device key | [http.md](v2/http.md#2-the-batch) |
| 67 | `hello` | document | the collar's device key | [lora.md](v2/lora.md#6-join) |
| 68 | `trust_update` | document | a firmware key the bootloader trusts | [firmware.md](v2/firmware.md#trust-updates) |
| 112–127 | | document | | private use |
| 128 | `image` | – | – | A firmware image in a LoRa announcement ([lora.md](v2/lora.md#7-delivering-a-message-to-the-herd)); never a payload type |

## <a id="record-types"></a>Record types (v2, record element 0)

| Code | Name | | Code | Name |
|---|---|---|---|---|
| 1 | `status` | | 6 | `health` |
| 2 | `fixes` | | 7 | `device` |
| 3 | `cue` | | 8 | `slots` |
| 4 | `episode` | | 9 | `anchor` |
| 5 | `ack` | | 10 | `firmware` |

96–127: private use. Fields: [messages.md §6](v2/messages.md#6-records-up).

## <a id="device-classes"></a>Device classes

| Code | Name | | v |
|---|---|---|---|
| 1 | `node` | LoRa only (BLE for setup); most collars | 2 |
| 2 | `anchor` | LoRa and LTE-M, on an animal; takes turns as the herd's link | 2 |
| 3 | `station` | An anchor on a post or a building: no animal, no fence | 2 |
| 4 | `direct` | LTE (or another IP link) straight to its server, no LoRa; every v1 collar | 2 |

## Roles (membership)

| Code | Name |
|---|---|
| 1 | `node` |
| 2 | `anchor` |
| 3 | `station` |

## Fence states

| Code | Name | |
|---|---|---|
| 0 | `unknown` | no usable fix yet |
| 1 | `inside` | clear of the warning zone |
| 2 | `warning` | inside, within `warn_m` of an edge |
| 3 | `outside` | |

## Cue kinds, cue modes, episode outcomes

| Code | Cue kind | v | | Code | Cue mode | v | | Code | Episode outcome | v |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `warn` | 1 | | 0 | `audio` | 1 | | 1 | `turned_back` | 1 |
| 2 | `outside` | 1 | | 1 | `track` | 1 | | 2 | `crossed` | 1 |
| | | | | | | | | 3 | `rest` | 1 |
| | | | | | | | | 4 | `boundary_changed` | 1 |

A new kind of cue (a vibration, another tone) is a new cue kind and a cap; a collar never
plays one a server didn't know it could.

## Ack and slot statuses

| Code | Name | |
|---|---|---|
| 1 | `received` | stored; waiting for its time (or, for a handover, its confirm) |
| 2 | `applied` | in effect |
| 3 | `rejected` | with a code (acks only) |

## Firmware states

| Code | Name | | Code | Name |
|---|---|---|---|---|
| 0 | `idle` | | 4 | `confirmed` |
| 1 | `downloading` | | 5 | `rolled_back` |
| 2 | `staged` | | 6 | `refused` |
| 3 | `testing` | | | |

## <a id="reject-codes"></a>Reject codes

Permanent unless marked: the server doesn't offer that version to that collar again
([server.md §5](v2/server.md#5-refusals) for the exceptions).

| Code | Name | v | |
|---|---|---|---|
| 1 | `bad_sig` | 1 | signature missing, malformed or not verifying |
| 2 | `wrong_herd` | 1 | another herd's |
| 3 | `wrong_collar` | 1 | another collar's |
| 4 | `bad_json` | 1 | not a valid v1 command |
| 5 | `too_large` | 1 | over 12 288 bytes |
| 6 | `stale` | 1 | a version at or below one held |
| 7 | `out_of_range` | 1 | a coordinate past ±180 / ±90 |
| 8 | `too_few_vertices` | 1 | |
| 9 | `too_many_vertices` | 1 | per ring or in total |
| 10 | `too_many_holes` | 1 | |
| 11 | `self_intersecting` | 1 | |
| 12 | `rings_cross` | 1 | touching counts |
| 13 | `hole_outside` | 1 | |
| 14 | `holes_overlap` | 1 | |
| 15 | `zero_area` | 1 | outer ring under 1 m² |
| 16 | `hole_too_small` | 1 | under 100 m² |
| 17 | `hole_too_close` | 1 | rings closer than 2·warn_m + 2 m |
| 18 | `bad_margins` | 1 | warn or hysteresis not finite or outside 0–1000 m |
| 19 | `slots_full` | 1 | **temporary**: no room now |
| 20 | `bad_config` | 1 | a config or membership out of range |
| 21 | `bad_cbor` | 2 | not deterministic CBOR, or not the message it claims to be |
| 22 | `expired` | 2 | `expires_at` reached; a handover whose deadline passed |
| 23 | `unknown_kid` | 2 | signed by a key the collar doesn't trust for that command |
| 24 | `unsupported` | 2 | a command type the collar doesn't implement |
| 25 | `claimed` | 2 | a bind for a claimed collar |
| 26 | `bad_claim` | 2 | a bind with the wrong nonce or proof |
| 27 | `rate_limited` | 2 | **temporary**: too many bad claims this hour |
| 28 | `not_now` | 2 | **temporary**: valid, waiting for a safe moment (firmware), or for GNSS time (a command with `expires_at`) |
| 29 | `bad_image` | 2 | a firmware image with the wrong digest, size or signature |
| 30 | `incompatible` | 2 | firmware for other hardware |
| 31 | `downgrade` | 2 | firmware older than the running image's security counter |
| 32 | `in_exclusion` | 2 | a boundary whose fenced area overlaps a permanent no-go zone the collar holds |
| 200–255 | | | private use |

## Channel plans

| Id | Name | |
|---|---|---|
| 1 | `US915_500` | [lora.md §2](v2/lora.md#2-radio) |

## Device record keys (v2)

1 `class`, 2 `fw`, 3 `caps`, 4 `limits`, 5 `hw_rev`, 6 `server_kid`, 7 `pending_kid`, 8
`owner_kid`, 9 `versions`, 10 `herd`, 11 `short`, 12 `claim_nonce`, 13 `boot`, 14
`security_counter`, 15 `image_keys`, 16 `part` (v2 draft 2), 17 `device_key` (draft 2), 18
`plans` (draft 2), 19 `zone_limits` (draft 2). [messages.md §6](v2/messages.md#6-records-up).
