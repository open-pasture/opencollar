# Conformance

How a collar, a server or a tool shows it speaks the OpenCollar protocol. There is no
certification body and no fee: conformance is passing the published vectors for your role,
and the scripted exchange once it exists, and saying which commit of the vectors you ran.

## Roles

| Role | Means | v1 | v2 |
|---|---|---|---|
| **Collar** | Anything that holds a fence and reports: a node, an anchor, a direct collar, a simulator | ✓ | ✓ |
| **Server** | Anything that commands collars: a farm app, a research server, an integration | ✓ | ✓ |
| **Relay** | Carries messages without reading them: an anchor's gateway side, a phone app, a bridge | – | ✓ |
| **Reader** | Only reads reports: analytics, a dashboard, a logger | ✓ | ✓ |

## Level 1: the vectors

Every file is in [`../vectors/`](../vectors/README.md), which says exactly how to run each
case. Which ones each role must pass:

| File | Collar | Server | Relay | Reader |
|---|---|---|---|---|
| `shapes.json` | all cases | all (with its own slack, never refusing what a collar accepts) | | |
| `geofence.json` | all | if it keeps its own fence per collar | | |
| `slots.json` | all | the activation rule, for what it serves | | |
| `cue.json` | all | | | |
| `commands.json`, `config.json` (v1) | all | it signs what passes | | |
| `v2/messages.json` | `commands`, in the listed order of checks, with and without a clock | it produces the same bytes for the same inputs; `documents` | | |
| `v2/records.json` | it encodes the `ok` cases byte for byte, each within `max_record` | it decodes every case, keeping what it doesn't know and refusing what is malformed | | every case |
| `v2/link.json` | frame key, uplinks, beacons (tag), fragments (bounds), slots, airtime, hellos, joins | frame key, uplinks (a malformed record among valid), batches, joins, replay | fragments, beacons, batches | uplinks (with a key) |
| `v2/identity.json` | claim, install rules, test boot, trust updates, counters, overlaps, activation | claim codes, claim, card, zones digest, v1 herd ids | | |

### Running the reference implementations

```sh
# openpasture's Rust (Apache-2.0 crate, in the openpasture repo)
cargo test -p op-protocol --test vectors --test vectors_v2

# the firmware's C, on a computer (opencollar repo)
make -C firmware/tests/host

# an independent Python reader of v2 records (standard library only)
python3 protocol/reference/opencollar_decode.py --test protocol/vectors/v2/records.json

# the same Python reader: beacons (their HMAC tags) and the slot schedule, with a collision sweep
python3 protocol/reference/opencollar_decode.py --test-link protocol/vectors/v2/link.json

# every v2 vector against the CDDL schema, with the reference CDDL tool
gem install cddl
python3 protocol/conformance/check_cddl.py

# hostile input for every decoder (openpasture repo; OP_FUZZ_ROUNDS runs longer)
cargo test -p op-protocol --test fuzz_v2
```

### What each check proves

Three kinds of conformance, kept apart because each catches what the others can't:

- **Schema shape** (`check_cddl.py`): the CDDL is the *sender's* schema. Every vector says
  what the schema must make of it (`schema`: `accept`, `reject`, or `skip` when the question
  isn't the schema's). A command a collar refuses for its state (a key, a version, a zone) is
  shape-valid and the schema accepts it; a record with an element a later version added is
  one a reader takes and the schema rejects.
- **Canonical bytes and the profile** (the decoders): deterministic CBOR, integer map keys,
  no tags, lengths and counts within bounds. The schema can't see these; the Rust reference
  and the Python reader refuse them, and the fuzz test checks nothing panics on them.
- **State** (the `expect` of commands, `install`, `activation`, `trust_updates`, `counters`,
  `joins`, `replay`): what a collar or server does given what it holds. Vectors pin single
  steps; the Level 2 exchange below pins sequences.

opencollar's CI runs the last three, and fails when the firmware's copy of a vector file
differs from `protocol/vectors/`; openpasture's runs the first, and fails when its copy
differs.

A different implementation runs the same files its own way. Test keys and the procedure for
each file are in the vectors README; nothing in the vectors depends on openpasture.

## Level 2: the scripted exchange

Vectors check one message at a time. Most real failures are in sequences: a herd change, a
lost slot, a handover. The exchange below is the conformance script for servers. A **device
emulator** (a simulated collar that speaks only the protocol: claim, frames or v1 JSON,
nothing of any server's own API) drives it against the server under test, and checks each
reply against the spec clause named.

| Step | The emulator | The server must | Clause |
|---|---|---|---|
| 1 | Sends a hello (v2) or first report (v1) as an unclaimed or freshly provisioned collar | Accept it; claim it once a person scans the card | identity §4 |
| 2 | Reports holding nothing | Serve the herd's boundary in effect | README Endpoints; lora §7 |
| 3 | Acks it `applied`; reports again | Store each record once, the resend too | server §7 |
| 4 | Reports a slot list missing the version in effect | Hand it per-collar copies above what it holds | server §4 |
| 5 | Is moved to another herd whose versions are lower | Send the move, then copies of the new herd's boundaries above what it holds | server §3 |
| 6 | Refuses a boundary `wrong_herd` before the move arrives | Offer it again once the move is confirmed | server §5 |
| 7 | Refuses one `slots_full` | Offer it again when there is room | server §5 |
| 8 | Reports a cue kind and an ack status from the future | Store both as sent; refuse nothing | registry, server §7 |
| 9 | (v2) Leaves a gap in its seq | Ask for it with a resend | server §7 |
| 10 | (v2) Receives a handover; the new server confirms, naming its digest | Allocate versions above what the collar reports | identity §6, server §2 |
| 11 | (v2) Misses the handover; its frames go to both endpoints | The old server keeps reading it and re-sends the handover | identity §6, server §10 |
| 12 | (v2) Sends the same frame twice, and a record with a seq it used before | Drop the replay; flag the conflict | messages §7.1, server §7 |
| 13 | (v2) Holds zones; a no-go is added over a staged strip | Send zones before boundaries; leases for the current epoch only; restage | messages §4.7, server §11 |
| 14 | (v2) Is reset and reports unclaimed | Reclaim it from its card, checked against the kept `claim_check` | identity §4, server §12 |

**Status:** this script is specified, not yet runnable. The `joins` vector in `link.json`
(two collars claimed over LoRa at once, to their first sealed status) is the first piece of
it in vector form. openpasture's `simulation/collar-sim`
exercises steps 1–8 against openpasture's own server today but also uses openpasture's app
API to set things up; splitting it into a protocol-only device emulator, so it can run
against any server, is the next piece of work here. A collar-side script (a fake server
sending every command and fault in turn) will follow the same pattern.

## Saying you conform

State the protocol version and role, the commit of `protocol/vectors/` you ran, and which
files (and, once runnable, which exchange steps) pass. A collar that is simulated says so
with the `sim` cap.
