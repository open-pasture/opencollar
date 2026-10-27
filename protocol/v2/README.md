# Collar protocol, v2 (draft)

**Draft, 2026-10-26.** Open for change until the first field firmware ships; after that,
what [§ Frozen at manufacture](#frozen-at-manufacture) lists is permanent. Nothing runs it
on a collar yet. openpasture's `crates/op-protocol` (`v2` module, Apache-2.0) is the
reference codec, and [`../vectors/v2/`](../vectors/README.md#v2) holds its test vectors.
openpasture's server doesn't serve v2 endpoints yet.

v1 is one collar on LTE talking HTTP + JSON to its server. v2 is the same fence, carried by
a herd: most collars are LoRa-only **nodes**, a few **anchor** collars with LTE take turns
as the herd's link to the server, and boundaries go out once to the whole herd. It is meant
to be adopted: by other collar makers, by other farm equipment, by any server. openpasture
is one client of many.

## Layers

| Layer | File | |
|---|---|---|
| Messages | [messages.md](messages.md) | The stable contract: deterministic CBOR, COSE-signed commands carried as opaque bytes, uplink records with a sequence number, sealed frames. Any transport carries them unchanged |
| LoRa binding | [lora.md](lora.md) | One herd on one channel: GNSS-timed minute, beacon, slots, broadcast with selective repeat, anchor hand-on and failover, join |
| HTTP binding | [http.md](http.md) | Anchors, stations and direct collars to the server: signed batches up, downlinks in the reply, retry rules; CoAP-ready; v1's status rules; BLE and USB |
| Identity | [identity.md](identity.md) | Device keys made on the collar, factory records, claim codes, server key handover, owner recovery key, release, revocation, TLS trust |
| Firmware | [firmware.md](firmware.md) | Signed releases, the collar's install rules (never during a move or an escape, never on a low battery), test boot and rollback |
| Server obligations | [server.md](server.md) | What any server must do: versions, herd changes, out-of-step recovery, refusals, deduplication |
| Schema | [opencollar.cddl](opencollar.cddl) | Every message in CDDL (RFC 8610) |

Names and numbers are in [../registry.md](../registry.md); conformance is
[../conformance/](../conformance/README.md).

**The fence itself is v1's.** Boundaries mean what they mean in v1: the limits, the shape
rules and their order, the geofence, the cue rule ("only cue a crossing"), episodes, slots and
activation, and the herd-change rule ([../README.md](../README.md)), with the same vectors
(`shapes.json`, `geofence.json`, `slots.json`, `cue.json`). v2 changes how they travel, not
what they are.

## Principles

v1's, plus:

- **Every collar runs its own fence on its own GNSS.** Anchors share a link, never a
  position or a decision.
- **Signed bytes are opaque.** A command is signed once and carried as is by LoRa, LTE,
  BLE or a USB cable. Nothing re-encodes, so nothing breaks a signature.
- **Nothing unsigned changes a fence, a key or a clock.** Beacons and replies only say when
  to listen and what is coming.
- **Nothing is lost silently.** Every record has the collar's sequence number; gaps are
  asked for again; duplicates are dropped.
- **Nothing new breaks anything old.** Unknown keys, record fields and registry values are
  ignored or kept, never refused ([messages.md §8](messages.md#8-extensibility)).
- **The farm owns the collars.** Moving to other software, rotating a key or recovering from
  a stolen one never needs a visit to the herd ([identity.md](identity.md)).

## <a id="data-budget"></a>Data budget

A typical day: status every 5 minutes, health every 6 hours, device record daily, a few cues
and acks; sizes are whole frames from op-protocol (`tests/vectors_v2.rs`, `data_budget`).
Airtime at plan 1 (SF8, 500 kHz). Anchor numbers are for a herd of 250, batches every 5
minutes, about 2 KB of TLS, TCP and HTTP per exchange.

| Per day | Node (LoRa only) | Anchor (when active, shared by rotation) | Direct collar (LTE) | v1 collar (measured) |
|---|---|---|---|---|
| Status frame | 46 B, 41 ms on air | | 46 B | ~125 B per fix in JSON |
| LoRa sent | 13.7 KB, 12 s on air | | – | – |
| LoRa listening | 55 s (beacons) | the herd's slots | – | – |
| Radio energy | ≈ 4.5 J (0.05 mW) | | | |
| LTE | **0** | 4.7 MB for the herd; **0.6–0.9 MB per anchor** with 8–5 anchors | **0.6 MB** | **7.9 MB** |
| LTE per collar, herd average | **19 KB** | | | |
| With fix history every 10 min (`track_s` 600) | 29 KB, 24 s on air | 1.1–1.8 MB per anchor | 0.6 MB | |

Against the 1 MB per collar per day target: every collar is far under it; an anchor is near
it only while it carries the herd, and the hand-on spreads that. Downlink is small: a
typical strip boundary is one 150-byte broadcast for the whole herd, where v1 sent each
collar its own copy.

## <a id="frozen-at-manufacture"></a>Frozen at manufacture

Firmware updates ([firmware.md](firmware.md)) can change almost everything a collar does.
These can't change without new hardware or a bootloader update, so they get settled before
the first field build:

- the bootloader, its image signature scheme (MCUboot, Ed25519, SHA-256) and its first
  trusted key hashes;
- the device key and how it is stored; the claim code;
- the factory record format and the card text format.

What a firmware update can change but every collar in a herd must agree on, and so changes
only with care: the frame format and frame key derivation, the COSE envelope and
`external_aad`, the minute layout (by new plan ids), the record layouts (by appending).

## Status of the parts

| Part | Spec | Reference (op-protocol `v2`) | Vectors | Firmware | openpasture server |
|---|---|---|---|---|---|
| CBOR, COSE, commands | ✓ | ✓ | `messages.json` | – | – |
| Records, frames | ✓ | ✓ | `records.json`, `link.json` | – | – |
| LoRa minute, fragments | ✓ | slots, airtime, fragments | `link.json` | – | – |
| HTTP batch and reply | ✓ | ✓ | `link.json` | – | – |
| Identity, claim, card | ✓ | ✓ | `identity.json` | – | fleet records |
| Firmware manifest, install rules | ✓ | ✓ | `identity.json` | – | – |
| Anchor election, broadcast scheduling | ✓ | – | – | – | – |

## <a id="open-questions"></a>Open questions for the owner

1. **Herd size per channel.** A net holds 300 collars that can all report every minute in a
   fast window, 1 500 at the default 5-minute cycle. Bigger herds get a second net on
   another channel. Is 300 fast collars per channel enough for the herds you're selling to?
2. **Radio plan.** Plan 1 is SF8 on 500 kHz channels (no hopping under FCC 15.247(a)(2)).
   125 kHz with hopping gives ~5 dB more range and halves capacity. Settle with the
   RAK4630's FCC grant in hand and a range test in a real pasture.
3. **HTTP or CoAP for anchors.** HTTP + TLS is specified; CoAP + DTLS with connection IDs
   would cut the per-exchange overhead (most of an anchor's bytes). Decide after measuring
   LTE-M power and data on an anchor.
4. **Proof for third parties.** Frames are authenticated to the server only. Should collars
   also sign an hourly digest of their records (64 bytes an hour) so a researcher or an
   auditor can show the server didn't change them?
5. **Bootloader updates in the field.** Never (safest, the root stays fixed), or with a
   signed and power-safe bootloader swap?
6. **Beacon authentication.** Beacons are unsigned (they can only waste battery). A herd key
   would authenticate them for 8 bytes a beacon, at the cost of distributing and rotating
   that key.
7. **BLE.** The GATT layout, and whether the farm app or a generic OpenCollar app does
   setup.
8. **Lost cards.** The claim code is the only way to factory-reset a collar. Does the maker
   keep claim codes so support can recover them, or does only the card hold it?
9. **Owner key by default.** Offer an offline owner key at claim (printed QR, or the phone's
   secure storage) by default, or leave it advanced?
10. **Release keys.** Who holds the OpenCollar release key and its offline reserve, and
    whether automatic updates are on by default for every farm (recommended) or opt-in.
11. **Install thresholds.** 40 % battery floor, no staged boundary within an hour, 30 minutes
    to confirm a new image: right for your batteries and moves?
12. **Fix history.** Status only by default (where the animal is every 5 minutes), with fix
    history opt-in per herd (`track_s`), which doubles airtime. Is the 5-minute picture
    enough for grazing analytics?
