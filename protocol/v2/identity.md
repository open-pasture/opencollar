# Identity and ownership

Protocol v2, **draft**. Part of the [v2 spec](README.md). The key words MUST, SHOULD and MAY
are used as in RFC 2119.

Who a collar is, who may command it, and how that changes hands without opening the collar.
The wire formats referred to here (COSE_Sign1 commands, frames, records) are in
[messages.md](messages.md); the schema is [opencollar.cddl](opencollar.cddl).

## 1. Keys

| Key | Algorithm | Held by | Made when | Signs or protects | Changed by |
|---|---|---|---|---|---|
| **Device key** | Ed25519 | The collar, never exported | At manufacture, on the collar | Hello frames, anchor batches, and (through key agreement) every frame the collar sends | Never. A unit whose key leaks is retired |
| **Server key** | Ed25519 | The farm's software | When the software is installed | Every command (boundaries, config, membership, firmware approvals, handover) | Handover (section 6) |
| **Owner key** (optional) | Ed25519 | The farmer, offline (paper, phone) | At claim or later | A handover of the server key, a new owner key, a release | Only itself |
| **Maker key** | Ed25519 | Whoever built the collar | Once per maker | Factory records (section 3) | The maker |
| **Release key** | Ed25519 | The OpenCollar project | Once | Firmware images and release manifests ([firmware.md](firmware.md)) | Revocation list in a signed manifest |
| **Image key** (optional) | Ed25519 | A DIY builder or owner | When they choose | Their own firmware images | Physical enrolment ([firmware.md](firmware.md)) |

No secret is printed on anything except the **claim code** (section 4), which is only good
for claiming an unclaimed collar or resetting it with the collar in hand.

Ed25519 is RFC 8032 (pure EdDSA, no prehash). Everything else uses SHA-256 (FIPS 180-4),
HMAC-SHA-256 (RFC 2104), HKDF-SHA-256 (RFC 5869), X25519 (RFC 7748) and AES-128-CCM
(RFC 3610).

## 2. Identifiers

| Name | Form | Where it comes from |
|---|---|---|
| `serial` | 1–32 characters of `A–Z 0–9 -` | The maker. Printed on the collar and its card. OpenCollar's form is `OC` + class letter + `-` + year and week + `-` + a 5-digit counter, e.g. `OCN-2611-00123` |
| `device_id` | 8 bytes | The first 8 bytes of SHA-256 of the 32-byte device public key. Never assigned, never changes, works across every server. Shown as 16 lowercase hex digits |
| `kid` | 8 bytes | The same function on any Ed25519 public key: the first 8 bytes of SHA-256 of the key. Names server, owner, maker, release and image keys in signed messages |
| `herd_id` | 1–16 bytes, opaque | The server. Stable for the life of the herd on that server. Servers SHOULD use 8 random bytes or a 16-byte ULID |
| `short` | 1–65 534 | The server, per herd (membership command). The collar's address on the herd's LoRa link and the basis of its airtime slot ([lora.md](lora.md)). 0 and 65 535 are reserved |

A server's own ids (openpasture's `col_…`, `herd_…`) never travel in v2. The server keeps the
mapping. `device_id` is how a server recognises a collar it has never seen.

## 3. Manufacture

On the test fixture, after the functional test passes:

1. The firmware generates the device key from the hardware random number generator and
   stores the private half where the application can't read it back out (on the nRF52840 a
   flash page locked by ACL, with APPROTECT on; on parts with a key store, there).
2. The fixture reads the public key, the hardware facts and the firmware version over the
   test UART, and draws a random 80-bit **claim code** (section 4), which it writes to the
   collar.
3. The fixture builds the **factory record**, signs it with the maker key and prints the
   card and label.

A collar that has no device key (a v1 collar updated to v2 firmware, a DIY board) generates
one on its first boot of v2 firmware and prints its public key on the console.

### Factory record

A signed document: a COSE_Sign1 by the maker key, whose payload is a deterministic CBOR map
with message type 64 ([registry](../registry.md)). The JSON view is what servers and tools
exchange; byte strings are lowercase hex.

| Key | Name | Type | Required | Meaning |
|---|---|---|---|---|
| 0 | `type` | uint | yes | 64 |
| 1 | `serial` | tstr | yes | See section 2 |
| 2 | `class` | uint | yes | Device class ([registry](../registry.md#device-classes)): 1 `node`, 2 `anchor`, 3 `station`, 4 `direct` |
| 3 | `hw_rev` | tstr ≤ 16 | yes | Board revision, e.g. `N1.0` |
| 4 | `device_key` | bstr 32 | yes | Ed25519 public key |
| 5 | `fw` | tstr ≤ 32 | yes | Firmware version flashed at manufacture (semver) |
| 6 | `made_at` | uint | yes | Unix seconds |
| 7 | `maker` | tstr ≤ 64 | yes | Who built it, e.g. `OpenCollar` or a DIY builder's name |
| 8 | `claim_check` | bstr 16 | no | First 16 bytes of HMAC-SHA-256(K_claim, `"check"`): lets software tell a mistyped claim code from a right one before using airtime |
| 9 | `radio` | map | no | 1 `lora_region` tstr (`US915`), 2 `ble_addr` bstr 6, 3 `imei` tstr, 4 `iccid` tstr |
| 10 | `image_keys` | [bstr 8] | yes | kids of the firmware keys the bootloader trusts ([firmware.md](firmware.md)) |
| 11 | `test` | map | no | 1 `fixture` tstr, 2 `passed` bool, 3 `report` bstr 32 (SHA-256 of the fixture's full report), 4 `at` uint |
| 12 | `caps` | [tstr] | no | Capabilities fixed by the hardware ([registry](../registry.md#caps)). A simulated collar MUST list `sim` |

`device_id` isn't stored: anyone computes it from `device_key`. Unknown keys MUST be ignored.

The fixture keeps the record and its full test report; the record also goes to the buyer
(in the box, by download, or straight into their software). A record signed by an unknown
maker key is still usable: the software shows it as unverified. A DIY builder signs with
their own maker key.

**For the fleet stream (server side):** store `serial`, `class`, `hw_rev`, `device_key`,
derived `device_id`, `fw`, `made_at`, `maker`, the maker `kid`, whether the signature
verified, `image_keys`, `caps`, and the record bytes as received.

### The card

Each collar ships with a card whose QR code holds one line of text:

```
OC2:<serial>:<device key, base64url without padding>:<claim code>
```

for example `OC2:OCN-2611-00123:F0VTtFbd38aQjsqxwQH-arIeK6oGF3lbfUOmNIKZP9U:7Q4K9M2XH8D3TV5W` (the test collar in the [vectors](../vectors/README.md#test-keys)).
Scanning it gives the farm's software everything it needs to claim the collar and to read
its frames from the first one. Parsers MUST ignore any further `:`-separated fields.

## 4. Claim

An unclaimed collar obeys nothing but a **bind** command proving knowledge of its claim
code.

- **Claim code**: 16 characters of Crockford base32 (`0–9 A–Z` without `I L O U`), 80 bits,
  printed in four groups of four. Software MUST accept lower case, `-` and spaces, and map
  `I L` to `1` and `O` to `0` before use.
- **K_claim** = HKDF-SHA-256(salt = `"opencollar/2"`, IKM = the 16 normalized ASCII
  characters, info = `"claim"` ‖ device_id, length 32).
- **Claim nonce**: 8 random bytes the collar draws whenever it becomes unclaimed (first boot,
  release, factory reset) and announces in its hello (LoRa), its BLE advertisement and its
  console `status` line. A recorded bind is useless after the next reset.

### Bind (message type 5)

A COSE_Sign1 signed by the **new server key**, whose own public key is inside it (proof of
possession). Payload keys beyond the common ones ([messages.md](messages.md#4-commands-types-163)):

| Key | Name | Type | Required |
|---|---|---|---|
| 16 | `server_key` | bstr 32 | yes; the COSE `kid` MUST be its kid |
| 17 | `proof` | bstr 16 | yes |
| 18 | `nonce` | bstr 8 | yes; the collar's current claim nonce |
| 19 | `endpoint` | tstr ≤ 256 | anchors, stations and direct collars |
| 20 | `owner_key` | bstr 32 | no; enrols the owner key at the same time |
| 21 | `endpoint_pin` | bstr 32 | no; SHA-256 of the server's TLS SubjectPublicKeyInfo (section 9) |

`proof` = the first 16 bytes of HMAC-SHA-256(K_claim, `"bind"` ‖ device_id ‖ nonce ‖
server_key ‖ len(herd_id) as one byte ‖ herd_id). `dev` (key 2) is required and `herd`
(key 1) is the herd the collar joins.

The collar checks it as any command ([messages.md §4.3](messages.md#43-what-a-collar-checks-in-order)),
in order: the envelope (`bad_cbor`), the signature against `server_key` (`bad_sig`), the
payload (`bad_cbor`), that it is unclaimed (`claimed`), `nonce` and `proof` (`bad_claim`),
then `dev` (`wrong_collar`) and `expires_at` (`expired`). After five `bad_claim` in an hour
it refuses binds for an hour (`rate_limited`), which keeps guessing an 80-bit code over the
air hopeless.

On success the collar stores the server key as **current**, the herd, the endpoint and pin
if given, and the owner key if given; it is **claimed**. It acks the bind `applied`
([messages.md](messages.md#ack)). A membership command (short address, role) normally
follows in the same delivery.

### How the bind reaches the collar

- **Over LoRa, with no phone.** An unclaimed collar sends a **hello** in the join window of
  any herd beacon it hears ([lora.md](lora.md#6-join)). A hello is signed by the device key
  (the server checks it against the card) and carries the device id, class, firmware and
  claim nonce. Anchors relay hellos from collars they don't know to their server. When the
  farmer has scanned that card, the server answers with a bind and a membership, addressed
  to the device id.
- **Over BLE from a phone.** The farm's app scans the card, connects to the collar it
  advertises (device id in the advertisement), reads the hello, asks the server for a bind
  and writes it to the collar.
- **Over the USB console** (bench, DIY): `bind <hex of the COSE bytes>`.

## 5. What a claimed collar holds

| Item | Set by | Notes |
|---|---|---|
| Current server key | Bind, handover confirm | Verifies every command except owner-signed ones |
| Pending server key, endpoint, pin, deadline | Handover | At most one pending handover |
| Owner key | Bind, owner command | Optional |
| Herd, short address, role | Bind, membership | |
| Endpoint and pin | Bind, config, handover | Anchors, stations and direct collars only |
| Highest version per message type and scope | Each command | Anti-replay ([messages.md](messages.md#46-versions)) |

All of it survives reboots and power cuts. None of it can be changed over the USB console
without the reset in section 7.

## 6. Handover: rotating the server key or moving to other software

The same two-phase exchange covers a routine key rotation, a move to different software,
and selling one collar to a neighbour. Nobody shares a private key and nobody touches the
collar.

1. **Propose.** The current server signs a **handover** (type 6) naming the new key. The
   owner key MAY sign it instead; that is how a farmer recovers from a lost or stolen
   server key.
2. **Stage.** The collar stores the new key as **pending**, keeps obeying the current key,
   and acks the handover `received`. Anchors and direct collars start sending to the new
   endpoint as well as the old one.
3. **Confirm.** The new software signs a **confirm** (type 7) with the new key, naming the
   kid it replaces. On a valid confirm the new key becomes current, the old one is
   forgotten, the new endpoint becomes the endpoint, and the collar acks the handover
   `applied`. From then on only the new key commands it.
4. **Fall back.** If no confirm arrives by the handover's `deadline` (GNSS time), the pending
   key is dropped and the collar acks the handover `rejected` with `expired`. A dead or
   mistyped new server never strands a collar.

Handover payload (type 6):

| Key | Name | Type | Required |
|---|---|---|---|
| 16 | `new_key` | bstr 32 | yes |
| 17 | `deadline` | uint | yes; Unix seconds, at most 30 days after `issued_at` |
| 18 | `endpoint` | tstr ≤ 256 | for anchors, stations and direct collars when the server moves |
| 19 | `endpoint_pin` | bstr 32 | no |
| 20 | `reason` | uint | no; 1 `rotate`, 2 `transfer` (for people; no behaviour depends on it) |

Confirm payload (type 7): key 16 `replaces` (bstr 8, the kid of the key being replaced).
The confirm's COSE `kid` MUST be the pending key's kid. A confirm with nothing pending, or
naming another kid, is rejected `bad_sig`.

Rules:
- A handover can be herd-scoped (no `dev`: every collar in the herd, delivered by
  broadcast) or for one collar (`dev`).
- A newer handover replaces a pending one. An owner-signed handover replaces a pending
  server-signed one, and a server-signed handover can't replace a pending owner-signed one
  (`stale`).
- The new software allocates versions above everything the collar reports holding
  ([server.md](server.md#2-versions)), so its first boundary is accepted.
- Boundaries and config signed by the old key that the collar already holds stay in force.
  A handover never changes the fence.

### Owner key (type 8)

Key 16 `owner_key` (bstr 32). Signed by the current owner key to replace it. When no owner
key is enrolled, the current server key MAY enrol the first one. The server key can never
replace or remove an enrolled owner key, so a stolen server key can be recovered from with
the owner key, without visiting the herd.

## 7. Release and factory reset

- **Release** (type 11), signed by the server key or the owner key: the collar forgets its
  server keys, owner key, herd, membership, config and staged boundaries, draws a new claim
  nonce and is unclaimed again. Its device key and claim code stay. Releasing a collar that
  is on an animal leaves that animal without a fence, so the server MUST refuse to send a
  release to a collar that holds an active boundary unless a person confirms it.
- **Factory reset** is the owner's hard override for a collar whose software is gone:
  hold a magnet on the collar's reed or hall sensor for 10 s, then within 2 minutes send
  `reset <claim code>` over the USB console or BLE. The collar does what release does.
  Physical access plus the card is ownership. The claim code requirement stops a passer-by
  with a magnet from removing a cow's fence.

## 8. Revocation

- **A collar** (lost, stolen, or its key leaked): the server marks its device id revoked,
  drops its frames, and leaves it out of the herd roster, so anchors stop relaying it. The
  device key is never replaced; the unit is retired.
- **A server key** (backup leaked, host breached): a handover to a fresh key, signed by the
  owner key if the server key can't be trusted. Without an owner key, a factory reset of
  each collar.
- **A release or image key**: [firmware.md](firmware.md#revocation).

## 9. Frame keys and transport security

**Frame key.** Every frame a claimed collar sends is encrypted and authenticated with
AES-128-CCM ([messages.md](messages.md#7-frames-sealing-records)) under

```
shared    = X25519(device private key, server public key)   (both keys in their X25519 form)
frame key = HKDF-SHA-256(salt = "opencollar/2", IKM = shared,
                         info = "frame" ‖ device_id ‖ server kid, length 16)
```

The X25519 form of an Ed25519 key is the standard birational map (libsodium's
`crypto_sign_ed25519_pk_to_curve25519` and `…_sk_to_curve25519`; Monocypher's
`crypto_eddsa_to_x25519`; for the private half, the first 32 bytes of SHA-512 of the seed).
Only the collar and the server it is bound to can compute it. Anchors, phones and anyone
listening on the radio can't read or forge a collar's reports, and a handover changes the key
with the server key, with nothing extra to send.

**Anchors, stations and direct collars over LTE.** Commands are signed end to end, frames
are protected end to end, and batches are signed by the anchor's device key with their own
sequence number ([http.md](http.md)). TLS adds privacy of metadata and authenticates the
server to the anchor. The anchor trusts:

- the server's TLS key named by `endpoint_pin` (SHA-256 of its SubjectPublicKeyInfo) when
  bind, config or handover set one: this is how a self-hosted server with a self-signed
  certificate works, with no tunnel and no certificate authority;
- otherwise a public certificate chaining to a small built-in root set (ISRG Root X1 and X2,
  plus the roots listed with the firmware release), which a firmware update can change.

`http://` endpoints are accepted only by bench builds of the firmware, never by field
builds. There are no client certificates and no bearer keys: the batch signature
authenticates the anchor.

## 10. From v1

v1 collars keep v1 provisioning ([../README.md](../README.md)). When a v1 collar first boots
v2 firmware it keeps the v1 server key as its current server key and its v1 herd, generates
its device key, and sends a device record (with the public key) over the v1 HTTP binding,
whose bearer key vouches for it once. From then on it is a claimed v2 collar; the printed v1
card's bearer key stops working when the server has the device key.
