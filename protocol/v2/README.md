# Collar protocol, v2 (draft)

**Draft 2, 2026-10-27.** Open for change until the first field firmware ships; after that,
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
- **Nothing unsigned changes a fence, a key or a clock.** Replies only say what is coming;
  beacons are authenticated with the herd's key and still can't change a fence, a key or a
  clock, or make a collar forget a record.
- **The collar enforces the farm's permanent no-go zones itself**, under every boundary, and
  takes a staged boundary only under a current lease, so a change on the map reaches a
  boundary that was signed before it.
- **Nothing is lost silently.** Every record has the collar's lifetime sequence number;
  collars keep records after the radio has them; gaps are asked for again; duplicates are
  dropped and conflicts flagged.
- **Nothing new breaks anything old.** Unknown keys, record fields and registry values are
  ignored or kept, never refused ([messages.md §8](messages.md#8-extensibility)).
- **The farm owns the collars.** Moving to other software, rotating a key or recovering from
  a stolen one never needs a visit to the herd ([identity.md](identity.md)).

## <a id="data-budget"></a>Data budget

Computed by op-protocol's `data_budget` test (`tests/vectors_v2.rs`) from the real encoders:
whole sealed frames, all the traffic named, nothing measured on a collar yet.

**A node's day:** status every 5 minutes, health every 6 hours, its device snapshot daily (in
3 parts), 4 cues, 6 acks, 2 % of frames sent again; it listens to every minute's beacon
(acknowledging about 50 of a 250-node herd's frames, 71 bytes) with a 20 ms guard, a lease
every 15 minutes and a strip boundary a day.

| Per day | Node (LoRa only) | Anchor (when active, shared by rotation) | v1 collar (measured) |
|---|---|---|---|
| Frames | status 46 B (41 ms on air), fix block 107 B, health 76 B, device 80–119 B, all ≤ 128 B | | ~125 B per fix in JSON |
| LoRa sent | 311 frames, 14.6 KB, **13.0 s** on air | | – |
| LoRa listening | **125 s** (beacons 114 s, leases and a boundary 12 s) | the herd's slots | – |
| Radio energy | **≈ 7.2 J (0.08 mW)**: 5.1 J sending, 2.2 J listening | | |
| LTE | **0** | **5.1 MB for a herd of 250** (status batches 4.8 MB, the rest 0.3 MB); **0.64–1.0 MB per anchor** with 8–5 anchors | **7.9 MB** |
| LTE per collar, herd average | **20 KB** | | |
| With fix history every 10 min (`track_s` 600) | +144 frames, +11.8 s on air; 11.8 J in all | +4.2 MB for the herd; 1.2–1.9 MB per anchor | |

The energy assumes SX1262 datasheet figures, **not measurements**: 118 mA sending (the +22 dBm
PA setting +20 dBm conducted needs), 5.3 mA receiving at 500 kHz, 3.3 V, 20 ms of guard per
beacon, no ramp or MCU time. The anchor's LTE assumes a signed batch every 5 minutes with
radio fields, 2 KB of TLS/TCP/HTTP and 200 B of reply per exchange; a direct LTE collar sends
its own frames the same way (about 0.6 MB a day, not recomputed here). Listening, not
sending, is a third of a node's radio energy: [open question 6](#open-questions). Downlink is
small: a typical strip boundary is one 150-byte broadcast for the whole herd, where v1 sent
each collar its own copy.

**Capacity on one channel** ([lora.md §3](lora.md#3-the-minute)): 300 collars that can all
be fast at once (every minute in a move), or up to 1 500 at the 5-minute rate with fast
windows shrinking to nothing as the net fills. The pilot's 20–50 collars, and a 1 000-head
ranch in herds of up to 300, are one net per herd. These are slot arithmetic and a collision
test, not a range or RF test.

## <a id="frozen-at-manufacture"></a>Frozen at manufacture

Firmware updates ([firmware.md](firmware.md)) can change almost everything a collar does.
These can't change without new hardware or a bootloader update, so they get settled before
the first field build:

- the bootloader and its boot profile ([firmware.md](firmware.md#boot-profile)): MCUboot,
  Ed25519 and SHA-256, the trust page and its format, the security counter's storage, and
  **both** OpenCollar release key hashes built in;
- the device key and how it is stored; the claim code and the physical reset, recode and
  enrol operations;
- the lifetime counters' flash format and reservation rule ([messages.md §7.1](messages.md#71-counters-that-never-repeat));
- the factory record format and the card text format.

What a firmware update can change but every collar in a herd must agree on, and so changes
only with care: the frame format and frame key derivation, the COSE envelope and
`external_aad`, the minute layout (by new plan ids, switched with the recoverable plan change
in [lora.md §2](lora.md#2-radio)), the beacon tag and key wrap, the record layouts (by
appending).

## Status of the parts

"Reference" is op-protocol's `v2` module; "state" means the reference models the collar's or
server's state machine for it, with tests, not only the bytes.

| Part | Spec | Reference | Vectors | Firmware | openpasture server |
|---|---|---|---|---|---|
| CBOR, COSE, commands, scope, who signs | ✓ | ✓ + versions store | `messages.json` | – | – |
| Zones and leases | ✓ | ✓ state (`policy`) | `messages.json`, `identity.json` | – | – |
| Records, parts, frames | ✓ | ✓ | `records.json`, `link.json` | – | – |
| Lifetime counters, replay window | ✓ | ✓ state (`counter`, power-cut test) | `identity.json`, `link.json` | – | – |
| LoRa minute, schedule, fragments, join | ✓ | ✓ slots, airtime, bounded reassembly, net filter | `link.json` | – | – |
| Beacons: tag, key wrap, election order | ✓ | ✓ codec and order; election timing not | `link.json` | – | – |
| HTTP batch and reply | ✓ | ✓ | `link.json` | – | – |
| Identity, claim, card, handover binding | ✓ | ✓ | `identity.json`, `messages.json` | – | fleet records |
| Firmware: manifest, install rules, test boot, trust updates | ✓ | ✓ state (`check_install`, `after_test`, `TrustStore`) | `identity.json` | – | rollout (fleet) |
| Anchor election and broadcast scheduling in time | ✓ | – | – | – | – |
| Stateful exchange (claim to first status, two anchors, handover with a missed member) | ✓ | join only | `link.json` `joins` | – | – |

Every decoder runs under a mutation fuzzer in op-protocol's tests (`fuzz_v2`); the Python
reader checks records, beacons and the slot schedule independently; the CDDL checker labels
what the schema decides and what it doesn't ([../conformance/](../conformance/README.md)).

## <a id="open-questions"></a>Open questions for the owner

1. **Herd size per net, and the two-anchor test.** One net gives a full fast window to 300
   collars and holds up to 1 500 at the 5-minute rate (fast windows shrink as it fills);
   bigger herds that move as one take a second net on another channel. Enough for the
   ranches you're selling to? Before plan 1 is frozen, two real anchors should be run
   against each other (failover race, a split herd rejoining) to set how often an active
   anchor stays silent to listen (now one minute in eight).
2. **Radio plan.** Plan 1 is SF8 on 500 kHz channels (no hopping under FCC 15.247(a)(2), which
   needs a *measured* 6 dB bandwidth of 500 kHz or more). 125 kHz with hopping gives ~5 dB
   more range and halves capacity. Settle with the RAK4630's FCC grant in hand, a bandwidth
   and PSD measurement, and a range test in a Montana pasture.
3. **HTTP or CoAP for anchors.** HTTP + TLS is specified; CoAP + DTLS with connection IDs
   would cut the per-exchange overhead (most of an anchor's bytes). Decide after measuring
   LTE-M power and data on an anchor.
4. **Proof for third parties.** Frames are authenticated to the server only. Should collars
   also sign an hourly digest of their records (64 bytes an hour) so a researcher or an
   auditor can show the server didn't change them?
5. **Bootloader updates in the field.** Recommended: never, for the pilot and the first
   1 000 (trust updates replace a leaked key without one). Or later, with a signed and
   power-safe bootloader swap?
6. **Node listening.** Beacons are now authenticated (an 8-byte tag under a herd key, decided
   in this draft). Listening to every minute's beacon is 2.2 J a day, a third of a node's
   radio energy. Listening only after its own slot and every fifth minute would cut that
   by about four fifths, at the cost of a move reaching a node in up to 5 minutes instead of
   1. Which?
7. **BLE.** The GATT layout, and whether the farm app or a generic OpenCollar app does
   setup.
8. **Lost cards.** The claim code is the only way to factory-reset or recode a collar. Does
   the maker keep claim codes so support can recover them, or does only the card hold it?
9. **Owner key by default.** Offer an offline owner key at claim (printed QR, or the phone's
   secure storage) by default, or leave it advanced? Without one, recovering from a stolen
   server key means a factory reset of every collar, in person.
10. **Release keys.** Who holds the two OpenCollar release keys (they must be made, and their
    hashes built in, before the first unit), kept apart offline; and whether automatic
    updates are on by default for every farm (recommended) or opt-in.
11. **Install thresholds.** 40 % battery floor, no staged boundary within an hour, a fix in the
    last 10 minutes, 30 minutes to confirm a new image, three no-fix tries before an image is
    refused: right for your batteries and moves?
12. **Fix history.** Status only by default (where the animal is every 5 minutes), with fix
    history opt-in per herd (`track_s`), which nearly doubles airtime. Is the 5-minute
    picture enough for grazing analytics?
13. **Lease window.** A staged strip needs a lease from the last 2 hours to take effect. Longer
    lets an out-of-range herd keep advancing its schedule longer; shorter makes a new no-go
    zone bind an out-of-range collar sooner. 2 hours, or something else per farm?
14. **Selling collars.** A sale is a transfer signed by the seller's owner key, and the card
    goes with the collar. Should the buyer be told to recode the claim code in person
    (magnet and phone), or is handing over the card enough?
15. **Record retention.** Collars keep records at least 7 days after the radio has them (years
    in practice with 16 MB of flash). Is 7 days the right floor for gaps to be recovered?
