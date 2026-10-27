# Firmware updates

Protocol v2, **draft**. Part of the [v2 spec](README.md). The key words MUST, SHOULD and MAY
are used as in RFC 2119. Vectors: [`../vectors/v2/identity.json`](../vectors/README.md#v2identityjson)
(manifest and install rules).

What most farmers want is updates that just happen and never cost an animal its fence. So by
default updates are **automatic and invisible**: images are signed by the OpenCollar release
key, checked by the bootloader, rolled out in stages, never installed during a move or an
escape or on a low battery, and rolled back by themselves if the new image doesn't prove it
works. A DIY builder or an owner who wants to run their own firmware enrols their own image
key.

## Keys and what checks them

| Key | Who holds it | Signs | Trusted by |
|---|---|---|---|
| Release keys (two) | The OpenCollar project, offline; the second in reserve | Images, release manifests, trust updates | Every OpenCollar bootloader, from manufacture: both are built in (`image_keys` in the factory record lists both) |
| Image key (optional) | A DIY builder or an owner | Their own images and manifests | Bootloaders it was enrolled in |
| Server key | The farm's software | The update command (when to install), the trust command (when to apply) | The collar's application |

Two signatures meet on every update: the **release or image key** says what the image is;
the **server key** says this herd should install it now. A server can't make a collar run an
image nobody trusted signed, and a release can't install itself on a farm whose software
didn't send it.

**Enrolling an image key** is physical, like a factory reset: hold a magnet on the collar for
10 s, then within 2 minutes send `enrol <claim code> <public key, 64 hex>` over the USB
console or BLE. The application checks the claim code and leaves the request for the
bootloader, then reboots; the bootloader applies it only if the magnet is **still there when
it starts** (it reads the hall sensor itself), so neither a remote command nor a compromised
application can enrol a key. An owner MAY remove the release keys the same way and trust
only their own (then OpenCollar releases no longer install); MAY NOT do it remotely.

## <a id="boot-profile"></a>Boot profile: nRF52840 (`nrf52840-mcuboot-1`)

What the node and anchor boards ship with, fixed at manufacture:

- **MCUboot**, built with Ed25519 image signatures and SHA-256, hardware anti-rollback on.
  Primary slot in internal flash; secondary slot and scratch in the external 16 MB flash.
  The bootloader's own pages are write-protected (BPROT/ACL) and APPROTECT is on. The
  bootloader is never updated in the field ([open question 5](README.md#open-questions)).
- **Built-in roots**: the hashes of both OpenCollar release keys, compiled in.
- **Trust page**: one internal flash page, made writable only by the bootloader (it sets the
  ACL to read-only before it starts the application), two copies with generations and a CRC
  like the counter journal ([messages.md §7.1](messages.md#71-counters-that-never-repeat)).
  It holds keys added by trust updates or enrolment (at most **four trusted keys in all**,
  built-in ones included), the revoked kids, the trust counter, and the **security counter**
  MCUboot's anti-rollback compares with (MCUboot leaves this storage to the platform; this
  page is ours).
- **Lifetime counters and identity** live in their own pages that no image erases.

**Commit order, safe at every power cut.** (1) A new image boots in test mode. (2) It passes
its self-test and marks itself confirmed (MCUboot's image-ok flag). (3) At the next boot the
bootloader writes the trust page once: the security counter raised to the confirmed image's,
and any pending trust update applied. Each step is one atomic write; a cut before (2) rolls
back; a cut between (2) and (3) just does (3) at the following boot. Nothing that would stop
the previous image from booting happens before the new one is confirmed.

## <a id="trust-updates"></a>Trust updates

A **trust update** (document type 68) changes which firmware keys the bootloader trusts. It
is signed by a firmware key the bootloader trusts now, and carried to a collar inside a
server's **trust** command (type 14, key 16), herd-wide or for one collar. The server says
when; a trusted firmware key says what.

| Key | Name | Type | |
|---|---|---|---|
| 16 | `counter` | uint ≥ 1 | Above every trust update this collar applied (`stale` otherwise) |
| 17 | `revoke` | [kid] | Keys to stop trusting |
| 18 | `add` | [bstr 32] | Public keys to trust from now on, as OpenCollar release keys |

The collar's application checks the trust command as any command, then the update's
signature against its trusted firmware keys (`unknown_kid`, `bad_sig`), acks `received`, and
leaves it for the bootloader, which checks it again and applies it at the next boot after the
running image is confirmed (never in a move: it waits for the install conditions below). The
bootloader refuses (`bad_config`) an update that would leave more than four keys trusted, or
no OpenCollar release key and no enrolled owner key: no update can leave a collar unable to
take a release. `firmware::TrustStore::apply` is the reference; `identity.json` has the
sequence.

**When a release key leaks:** the project signs, with the reserve, a trust update revoking
the leaked key and adding a new reserve, and ships it to every farm; servers send it with the
next update. The collars never need a visit, and still hold two release keys afterwards.
**When the reserve is lost too**, before an update with a new one went out: only physical
enrolment (above) adds a key; that is the recall case, and why both keys are kept offline
apart.

## The image

An MCUboot image: header, application, and trailing TLVs with the image's SHA-256, its
Ed25519 signature by a trusted key, and a **security counter**. MCUboot checks the signature
before every first boot of a new image and refuses a lower security counter than the one
running (anti-rollback). The **image digest** this spec uses is SHA-256 of the whole image
file as distributed.

## The release manifest

Message type 65, a COSE_Sign1 by the release or image key, published next to the image:

| Key | Name | Type | |
|---|---|---|---|
| 16 | `version` | tstr ≤ 32 | Semver |
| 17 | `digest` | bstr 32 | SHA-256 of the image file |
| 18 | `size` | uint | Bytes |
| 19 | `classes` | [uint] | Device classes it runs on |
| 20 | `hw_revs` | [tstr] | Board revisions it runs on, exactly |
| 21 | `security_counter` | uint | The image's, as in its TLV |
| 22 | `min_battery` | uint 0–100 | Least battery to start, %. Present and not that: the manifest is `bad_cbor` |
| 23 | `revoke` | [kid] | Firmware keys whose manifests the application refuses from now on ([§Revocation](#revocation)) |

Every field present must have its type and range, or the manifest is refused (`bad_cbor`);
nothing malformed is read as absent.

## The update command

Message type 9, signed by the server key, herd-wide or for one collar:

| Key | Name | Type | |
|---|---|---|---|
| 7 | `effective_at` | uint | Not before this GNSS time |
| 16 | `manifest` | bstr | The release manifest, as published |
| 17 | `window_s` | uint | Spread installs over this long after `effective_at`: each collar picks its own moment, so a herd never reboots at once |
| 18 | `url` | tstr | Where anchors fetch the image. Absent: `<endpoint>/fw/<digest hex>` |

## On the collar, in order

1. The command is checked as any command ([messages.md §4.3](messages.md#43-what-a-collar-checks-in-order)).
2. The manifest: its signature by a trusted, unrevoked firmware key (`unknown_kid`,
   `bad_sig`); its class and board (`incompatible`); its security counter not below the
   running one (`downgrade`); a digest it refused before (`bad_image`). These are permanent
   refusals.
3. The collar acks the command `received` and fetches the image ([§Delivery](#delivery)),
   reporting progress in firmware records. A wrong size or digest is `bad_image`, and the
   image is fetched again (three tries, then refused).
4. **It picks its moment.** Once per command it draws a random offset in `0..window_s` and
   keeps it in flash; it may install from `effective_at` + that offset on, never before. From
   then it checks every 10 minutes, and **never gives up** on its own (only a newer release
   or the server replaces it). It installs only when all of these hold, **all read from its
   own state**, and checks them all again in the last second before it reboots:
   - it has GNSS time;
   - battery at or above both the manifest's `min_battery` and its own floor of **40 %**;
   - a fix in the last 10 minutes, and its fence says **inside** (not warning, not outside,
     not unknown);
   - **no escape**: no episode open, no collar-scoped boundary (a pen) held;
   - **no move**: no fast window running (`fast_until` after now), and no staged boundary
     due in the next hour or overdue and waiting for zones or a lease.
   While it waits, its firmware record says `staged` with `not_now`. A server can't make a
   collar update during a move or an escape: the collar doesn't ask the server.
5. It reboots into the new image in **test mode**. The active boundary and the held zones are
   in flash and enforced from the first instant of boot, as after any reboot.
6. The new image **confirms itself** on local evidence only, within 30 minutes: the active
   boundary and zones loaded and enforcing, flash and counters readable and advancing, the
   watchdog fed, the GNSS receiver answering and a fix taken. Then it marks itself
   confirmed and acks the command `applied`. **The link is not a condition**: a herd out of
   range of its anchor, or a beacon that never came, never condemns an image.
7. If it doesn't confirm, it reboots and MCUboot puts the previous image back:
   - it crashed, the watchdog fired, or the self-test failed: the collar reports
     `rolled_back` and refuses that digest from then on;
   - everything passed but no fix came in 30 minutes (a barn, a gully): it reports `staged`
     with `not_now` and tries again at its next safe moment; after **three** such tries it
     refuses that digest.

`firmware::check_install`, `InstallWindow` and `after_test` are the reference;
`identity.json` has a vector for every condition.

**Persistent data across versions.** An image in test mode MUST NOT change the format of
anything in flash the previous image reads (boundaries, zones, versions, keys, counters,
records). A format change happens only after it is confirmed, and every release reads the
formats of the release before it. The counter, identity and trust pages never change format.

## Delivery

- **Anchors, stations, direct collars**: HTTP GET over LTE ([http.md §6](http.md#6-firmware-images)),
  with Range to resume. The image goes to external flash (the secondary slot).
- **Nodes, over LoRa**: the active anchor sends the image to the herd as a broadcast message
  of type 128 whose id is the first 4 bytes of the digest, in fragments of 209 bytes, a few
  dozen per minute in the downlink windows ([lora.md §7](lora.md#7-delivering-a-message-to-the-herd)).
  A node takes image fragments only for a firmware command it accepted, only with the count
  that the manifest's `size` gives, and streams them to the secondary slot
  ([lora.md §7.1](lora.md#71-what-a-receiver-holds)).
  Each node reports `need` windows of up to 64 fragments until it holds the whole image. A
  200 KB image is about 1 000 fragments: a few hours of downlink windows, during which the
  herd's other traffic goes first.
- **From a phone over BLE**, for a collar that missed it or a farm without anchors.
- **Over the USB console**, on the bench.

## Rollout

Rollout is the server's choice ([server.md §8](server.md#8-firmware)), within the collar's
rules. The default a server SHOULD use: one collar per herd first; the rest of that herd
after 24 h if it confirmed; then every herd after 72 h. It stops sending an update as soon as
any collar reports `rolled_back` or goes silent after installing it, and tells a person.
Owners MAY turn automatic updates off or hold a herd at a version; security fixes are
labelled so the software can say so.

## Revocation

Two levels:

- A manifest's `revoke` makes the **application** refuse manifests signed by those keys once
  it runs that manifest's image.
- A **trust update** (above) makes the **bootloader** stop trusting them, on the
  nRF52840 through its trust page; on parts with a key management unit (nRF54, nRF91) the
  bootloader also revokes them there. This is what turns a leaked release key into a
  software update instead of a recall.

## What can't be updated over the air

The bootloader and its built-in key hashes are written at manufacture and are the root of
everything above. Trust updates change which keys it trusts; nothing changes the bootloader.
Updating the bootloader itself in the field is [open question 5](README.md#open-questions);
the recommendation for the pilot is never.
