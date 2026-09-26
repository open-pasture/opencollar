# Collar protocol

How software talks to an OpenCollar: boundaries go down, positions and cues
come up. Any software that speaks this can run the collars. Openpasture is the
first. Its side of the same formats is in
`openpasture-agent-kit/docs/contracts.md`.

Status: draft. V0 firmware compiles its boundary in (`firmware/src/boundary.h`).
Nothing here is sent over the air yet.

## Principles

- **Fence logic runs on the collar.** The collar holds its boundary and cues the
  animal without the network. The server only changes what the boundary is.
- **The collar keeps the last good boundary.** A lost connection, a bad message,
  or a reboot never leaves an animal without a fence.
- **Versions only go up.** Each boundary carries a version per herd. A collar
  ignores any boundary older than or equal to the one it holds.
- **Everything is acknowledged.** A boundary counts as active only once the
  collar reports it applied.
- **Only a crossing is cued.** See below.

## Collar rule: only cue a crossing

The collar cues "outside" only when the animal goes from inside (or the warning
zone) to outside under the boundary it holds.

- At boot and whenever a new boundary is applied, the fence is **unarmed**. The
  first fix inside the polygon arms it. If that fix is in the warning zone, the
  warning cue plays at once, which is how a moved boundary pushes an animal.
- While unarmed and outside, the collar is silent and reports state `outside`.
  A boundary that leaves an animal outside never cues it.
- A crossing cues the outside tone for up to 10 s, then disarms. An animal
  walking back in is not cued in the warning zone on its way; a fix clear of
  the warning zone arms the fence again.
- Warning-zone cues are otherwise unchanged: louder toward the edge, at most
  20 s of continuous cueing, then 30 s of rest.

Why: an audio cue only teaches when the animal can escape it by moving away
from the edge. A fence drawn on top of an animal, or behind it, gives no
direction, only noise. In the firmware this is `cue.c`; `main.c` calls
`cue_rearm()` whenever it applies a boundary.

## Boundary (down)

```json
{
  "command_id": "bc_01J8...",
  "herd_id": "herd_01J7...",
  "version": 42,
  "effective_at": "2026-09-25T12:30:00Z",
  "boundary": [[-92.4100, 38.1200], [-92.4000, 38.1200], [-92.4000, 38.1300], [-92.4100, 38.1300]],
  "warn_m": 10,
  "hysteresis_m": 3
}
```

- `boundary` is one ring of `[longitude, latitude]` pairs, WGS 84, not closed
  (the collar closes it). 3 to 64 vertices, the firmware's
  `GEOFENCE_MAX_VERTICES`.
- `effective_at` lets a boundary be staged ahead of time. Absent means now.
- `warn_m` and `hysteresis_m` are optional and override the collar's defaults.
- `herd_id` is the herd the boundary is for. Openpasture signs it with the rest
  of the command (Ed25519 over the canonical JSON, sent as `sig`). A collar
  rejects a command for a herd other than its own. Commands without `herd_id`
  (older servers) are accepted.

The collar validates before applying: vertex count, coordinate ranges, a ring
that does not cross itself, and a version newer than the current one. A failure
is reported as `rejected` and the old boundary stays.

### What the collar does not need to know

The engine's boundary command has exclusion areas and transitions. V0 collars
handle neither directly:

- **Transitions** are two boundaries. The engine sends the combined old paddock,
  corridor, and new paddock as version N, then the new paddock alone as version
  N+1 with a later `effective_at`.
- **Exclusions** are cut out of the ring by the engine before sending, where the
  shape allows it. Holes inside a polygon are future work in the firmware.

### Moves

To move a herd, openpasture sets a target and **sweeps** the active boundary
toward it: a series of ordinary boundaries, each one containing every animal,
with its back edge just behind the rearmost animal so only the animals at the
back hear the warning cue and walk forward. The next step goes out once the
herd has moved up. The last step is the target. The collar needs nothing new
for this beyond the rule above: each step is just a newer boundary.

## Acknowledgement (up)

```json
{ "command_id": "bc_01J8...", "version": 42, "status": "applied", "at": "2026-09-25T12:30:04Z" }
```

`status` is `received` (stored, waiting for `effective_at`), `applied`, or
`rejected` with a `reason`.

## Position report (up)

Sent on a schedule and on events. Fixes are batched to save power.

```json
{
  "collar_id": "oc_0012",
  "boundary_version": 42,
  "fixes": [{ "at": "2026-09-25T10:40:00Z", "point": [-92.4051, 38.1244], "accuracy_m": 1.8, "sats": 9 }],
  "cues": [{ "at": "2026-09-25T10:12:00Z", "level": 2, "margin_m": -1.4 }],
  "battery": 0.81
}
```

- `boundary_version` tells the server which fence the collar is enforcing.
- `cues` are every sound or stimulus the collar gave, with how far past or short
  of the line the animal was. The engine uses these to see how the herd is
  taking a boundary.

## Transport

Not decided. The nRF9151 gives LTE-M and NB-IoT, so the likely path is CoAP or
MQTT over LTE-M with messages encoded in CBOR. The JSON above is the logical
shape. The wire encoding will map it one to one.

## Open questions

- How often to report, and how that changes with distance to the line (see
  `docs/V1-REQUIREMENTS.md`, adaptive fix rate).
- Authentication of boundaries so a collar only accepts its own server.
- Holes (exclusions) in the firmware geofence.
- What a collar does when it has no boundary at all on first boot.
