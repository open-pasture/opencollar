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
| Release key | The OpenCollar project, offline | Images and release manifests | Every OpenCollar bootloader, from manufacture (`image_keys` in the factory record) |
| Image key (optional) | A DIY builder or an owner | Their own images and manifests | Bootloaders it was enrolled in |
| Server key | The farm's software | The update command (when to install) | The collar's application |

Two signatures meet on every update: the **release or image key** says what the image is;
the **server key** says this herd should install it now. A server can't make a collar run an
image nobody trusted signed, and a release can't install itself on a farm whose software
didn't send it.

**Enrolling an image key** is physical, like a factory reset: magnet on the collar, then the
key over the USB console or BLE with the claim code. The bootloader keeps up to four trusted
key hashes in a region only it can write. An owner MAY remove the release key and trust only
their own (then OpenCollar releases no longer install); MAY NOT do it remotely.

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
| 22 | `min_battery` | uint | Least battery to start, % |
| 23 | `revoke` | [kid] | Firmware keys to stop trusting ([§Revocation](#revocation)) |

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
   running one (`downgrade`). These are permanent refusals.
3. The collar acks the command `received` and fetches the image ([§Delivery](#delivery)),
   reporting progress in firmware records. A wrong size or digest is `bad_image`, and the
   image is fetched again (three tries, then refused).
4. **It waits for a safe moment.** It installs only when all of these hold, checking again
   right before it reboots:
   - battery at or above both the manifest's `min_battery` and its own floor of **40 %**;
   - **no move**: no staged boundary takes effect within the next hour, and no fast window
     is running;
   - **no escape**: the animal isn't outside its fence or in a warning episode, and the
     collar holds no collar-scoped boundary (a pen);
   - it is inside its window (`effective_at` + its own random offset within `window_s`).
   While it waits, its firmware record says `staged` with `not_now`. It never gives up on
   its own.
5. It reboots into the new image in **test mode**. The active boundary is in flash and is
   enforced from the first instant of boot, as after any reboot.
6. The new image **confirms itself** only after, within 30 minutes: a GNSS fix, the active
   boundary loaded and enforcing, and its link working (a beacon heard, or a batch posted).
   Then it marks the image confirmed and acks the command `applied`.
7. If it doesn't confirm (it crashes, the watchdog fires, 30 minutes pass), it reboots and
   MCUboot puts the previous image back. The collar reports `rolled_back` and refuses that
   digest from then on.

Steps 4–7 are the collar's own rules, the same for every server: no server can make a collar
update during a move or on a low battery.

## Delivery

- **Anchors, stations, direct collars**: HTTP GET over LTE ([http.md §6](http.md#6-firmware-images)),
  with Range to resume. The image goes to external flash (the secondary slot).
- **Nodes, over LoRa**: the active anchor sends the image to the herd as a broadcast message
  of type 128 whose id is the first 4 bytes of the digest, in fragments of 209 bytes, a few
  dozen per minute in the downlink windows ([lora.md §7](lora.md#7-delivering-a-message-to-the-herd)).
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

A manifest's `revoke` lists firmware key ids to stop trusting. A collar that has installed
such a manifest's image refuses manifests signed by those keys from then on, and the
bootloader drops their hashes where the hardware supports revoking keys (nRF54 and nRF91 key
management units). A revocation is signed by another trusted key, so the release key needs a
standby: the OpenCollar project keeps two release keys, one offline in reserve.

## What can't be updated over the air

The bootloader and its first trusted key hashes are written at manufacture and are the root
of everything above. Updating the bootloader itself in the field is [open question 5](README.md#open-questions).
