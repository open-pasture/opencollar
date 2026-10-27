# The HTTP binding

Protocol v2, **draft**. Part of the [v2 spec](README.md). The key words MUST, SHOULD and MAY
are used as in RFC 2119.

How an anchor, a station or a direct collar talks to its server over LTE (or any IP link):
one request carries everything heard up, and its reply carries everything waiting to go
down. Nothing polls. The last sections cover v1's HTTP binding, BLE and the USB console.

## 1. One exchange

```
POST <endpoint>/batch                         <endpoint> from bind, config or handover,
Content-Type: application/cose; cose-type="cose-sign1"    e.g. https://farm.example.com/collar/v2
<a batch: COSE_Sign1 by the sender's device key>

200 OK
Content-Type: application/cbor
<a reply>
```

There are no bearer keys and no cookies: the batch's signature says who sent it, and its
sequence number makes a retry harmless. TLS is as in
[identity.md §9](identity.md#9-frame-keys-and-transport-security) (an `endpoint_pin` or the
built-in roots).

## 2. The batch

Message type 66, a COSE_Sign1 whose kid is the sender's device id:

| Key | Name | Type | |
|---|---|---|---|
| 0 | `type` | uint | 66 |
| 16 | `seq` | uint | The sender's batch counter: a lifetime counter like `fcnt` ([messages.md §7.1](messages.md#71-counters-that-never-repeat)), never reset. A retry sends the same batch, same seq |
| 17 | `sent_at` | uint | GNSS time it was made |
| 18 | `herd` | bstr | The herd it serves; absent for a direct collar |
| 19 | `have` | uint | The highest downlink id it holds (0 for none) |
| 20 | `frames` | [[frame] / [frame, at, rssi_dbm, snr_db]] | Uplink and hello frames as heard, with when and how well; its own frames without the radio fields |

A direct collar's own frames have `net` and `src` 0; the server knows whose they are from the
batch's signer. Every frame is at most 255 bytes; a longer one is counted and dropped without
being read. Batches SHOULD stay under 64 KB; a server MUST accept at least 1 MB.

**During a handover** ([identity.md §6](identity.md#6-handover-rotating-the-server-key-or-moving-to-other-software))
an anchor posts every batch to both endpoints until the handover's deadline, even after its
own confirm, and keeps each endpoint's `have` and downlink queue apart, relaying both. It
keeps a frame until both have acknowledged a batch carrying it, or the deadline has passed.

## 3. What the server does with it

1. Check the signature against the sender's device key. Unknown, unclaimed or revoked sender:
   401.
2. A batch seq it has already stored: answer again, storing nothing twice.
3. Each frame on its own ([server.md §7](server.md#7-acknowledgements-and-reports)): find the collar from `net`
   and `src` (or the signer), open it with that collar's frame key, keep each record once by
   (device, seq). A frame that is malformed or doesn't open is counted and dropped; it never
   fails the batch.
4. Hellos go to the claim flow ([identity.md §4](identity.md#4-claim)).
5. Reply.

## 4. The reply

A CBOR map, unsigned (every command in it is signed):

| Key | Name | Type | |
|---|---|---|---|
| 1 | `ack` | uint | The batch seq stored. The sender may now drop those frames |
| 2 | `down` | [[id, to, message]] | Downlinks with an id above the batch's `have`: `to` is a device id, or `null` for the whole herd; `message` a signed command, as is |
| 3 | `next_s` | uint | Post again within this many seconds (a fast window, a queue waiting) |
| 4 | `time` | uint | The server's clock, for logs. Never used for a fence |
| 5 | `drop` | [id] | Downlinks to stop delivering: delivered to everyone, or superseded |
| 6 | `next_anchor` | uint | The short address to hand the herd's link to next ([lora.md §5](lora.md#5-anchors)) |

Downlink ids increase per herd and never repeat. Standby anchors don't post for the herd;
the anchor taking over posts at once with the `have` it last held and gets what it missed.

## 5. Status codes and retries

What a sender does with each answer. "Keep" means the frames stay in flash for a later batch.

| Answer | Meaning | The sender |
|---|---|---|
| 200 | Stored | Drops those frames; delivers `down`; honours `drop`, `next_s`, `next_anchor` |
| 400 | The batch itself is malformed | Doesn't send it again as is. Sends its frames one per batch; drops (and logs) a frame refused alone |
| 401 | The server doesn't know this sender, or it isn't claimed there | Keeps. Stops posting there; during an endpoint change or a handover, goes back to the previous endpoint; else retries hourly |
| 413 | Too large | Splits it in two and retries both |
| 429, 503 | Busy | Keeps; retries after `Retry-After` (at most 1 h), else as for 5xx |
| other 5xx, a network or TLS error, no answer in 60 s | | Keeps; retries the same batch after 30 s, doubling to 30 min, ± 25 % jitter; new frames go in the next batch |

A server answers 4xx only for the reasons above. It never refuses a batch for a record's
content, a clock or a value it doesn't know.

## 6. Firmware images

```
GET <endpoint>/fw/<hex SHA-256 of the image>      (or the firmware command's url)
200 application/octet-stream, Range supported
```

Images are signed releases, not secrets: no authorization. The anchor checks the digest
before it offers the image to anyone ([firmware.md](firmware.md#delivery)).

## 7. CoAP, later

The exchange maps one to one onto CoAP when power measurements favour it ([open question 3](README.md#open-questions)):
`POST /collar/v2/batch` with Content-Format 18 (`application/cose; cose-type="cose-sign1"`),
answered 2.04 Changed with Content-Format 60 (`application/cbor`); block-wise transfer
(RFC 7959) for large batches and images; DTLS 1.2 with Connection ID (RFC 9146) or OSCORE in
place of TLS. Batch, reply, frames and commands are unchanged.

## <a id="v1-binding"></a>8. v1's HTTP binding

Direct collars speaking v1 ([../README.md](../README.md#endpoints)) keep its endpoints and
JSON. These rules, which v1 left unwritten, apply to them:

| Answer | The collar |
|---|---|
| 2xx | Done: drops what it sent |
| 400 | Drops that report or ack and logs it; never resends it unchanged |
| 401 | Its key is unknown: keeps its data, stops, retries hourly until re-provisioned |
| 403 | Drops it (it named another collar) |
| 404 on an ack | Drops that ack (a command from before a herd change) |
| 413 | Splits the report |
| 429, 5xx, network | Keeps; retries with backoff as in §5 |

Acks go oldest first; a failed one doesn't block those after it once it has been dropped.
The server stores each fix once per (collar, time) and each cue once per (collar, time,
kind), so a report resent after a lost reply changes nothing.

## 9. BLE and the USB console

**BLE** (phone, nodes and anchors): the collar advertises its device id. A phone running the
farm's app relays in both directions without reading anything: signed commands and fragments
down, sealed frames and signed hellos up, which the app forwards to its server through the
server's own API. The GATT service layout is [open question 7](README.md#open-questions).

**USB console** (bench, fixture, DIY), one line each:

| Line | Reply |
|---|---|
| `status` | the device record's JSON view |
| `hello` | hex of a signed hello |
| `cmd <hex>` | a signed command, by the same path as over the air: `applied …`, `received …`, `rejected … <code>` |
| `bind <hex>` | the same, for a bind |
| `reset <claim code>` | within 2 minutes of holding a magnet to the collar ([identity.md §7](identity.md#7-release-and-factory-reset)) |
