# Server obligations

Protocol v2, **draft**; sections 1–7 apply to v1 as well. Part of the [v2 spec](README.md).
The key words MUST, SHOULD and MAY are used as in RFC 2119.

What any server has to do for collars to work, beyond speaking the formats. These rules come
from openpasture's server (`crates/op-ingest`), where each was learned the hard way; a
different server that skips one will strand a collar sooner or later. The last section is
openpasture's own policies, for information.

## 1. Clocks

Collars run on GNSS time; nothing unsigned from a server sets their clock. The server's clock
is used to decide what is in effect now (which boundary to serve, what has expired) and never
to judge a collar's data. A server SHOULD keep records whose times are ahead of its clock and
mark them, rather than refuse them. (openpasture today refuses a v1 report with any time more
than 10 minutes ahead of its clock, 400, "Check the collar clock"; this is to be relaxed.)

## 2. Versions

- A collar takes only versions above every one it holds (boundaries), or above the one it
  holds of that type (other commands). So versions MUST increase **per collar**, across
  herd-wide and per-collar commands and across herds. A per-herd counter breaks the first
  time a collar changes herd.
- The simple way, and openpasture's: **one counter per server** for boundaries
  (`MAX(version) + 1` over every boundary of every herd), one per collar for configs.
- After a **handover**, a restore from backup, or a claim by new software, the server reads
  what the collar holds (v1: `have` on downloads, `device.config_version`; v2: the device
  record's `versions` and `slots`) and allocates above it. A config version the collar holds
  above the server's (a restored database) is overtaken by a new one.
- `issued_at` MUST NOT go backwards for a collar: a v2 collar refuses (`stale`) any command
  issued before its claim time. A server whose clock was wrong when it claimed a collar
  re-claims it rather than sign "older" commands.

## 3. Herd changes

When a collar moves herd (v1: a config naming the new herd; v2: a membership), the collar
drops the old herd's staged boundaries and keeps enforcing its active one until one of the
new herd applies.

- The new herd's boundaries may sit at or below what the collar holds. The server MUST then
  hand the collar **per-collar copies** of the new herd's boundary in effect and of each
  staged one that is still alive, with versions above everything it holds and the same
  `effective_at` (v1: `collar_id` plus openpasture's `copy_of`; v2: `device`). The one in
  effect drops the rest.
- It does the same when it doesn't know what the collar holds (heard from, but no slots yet).
- A boundary of the new herd can reach the collar before the command that moves it and be
  refused `wrong_herd`; see §5.

## 4. Out of step

When a collar's reported slots show it can't get some version of its boundary set the usual
way (a version it doesn't hold, hasn't refused, at or below the highest it holds: it lost a
slot record, or it holds another herd's versions), the server MUST hand it copies of its
herd's boundary in effect and each alive staged one above what it holds, as in §3, and name
them in the next reply.

## 5. Refusals

- A version a collar refused is not offered to it again, **except**:
  - `slots_full`, `not_now`, `rate_limited`: temporary; offer again later (v1: when `free`
    and `free_bytes` allow it).
  - `wrong_herd` and `bad_sig` refused before the collar's current config (v1) or membership
    (v2) went out: offered again once the collar reports holding it. A boundary of the new
    herd can arrive before the move, and a collar set up with another server's key refuses
    every signature until its config arrives.
  - `unsupported`: offered again only when the collar's firmware or caps change.
- A rejection without a code (v1, firmware 0.1) counts as permanent.
- A server MUST NOT send a field or command type a collar hasn't listed support for in its
  caps when its meaning matters for the animal (holes, track mode, collar-scoped boundaries).

## 6. Escapes and per-collar boundaries

An immediate per-collar boundary (an escape pen) drops every lower staged boundary on that
collar. When the escape ends, the server MUST restage that collar's copies of the herd's
boundary in effect and of each alive staged one (§3), so the herd's schedule still reaches it.
Only that collar downloads anything.

## 7. Acknowledgements and reports

- **Correlate acks** by (collar, version) and, in v1, `command_id`: one herd boundary is
  fitted and signed separately per collar, so the id is shared and the bytes differ. In v2 by
  (device, type, version), and by `digest` when type and version are 0.
- **Store every report once.** v1: one fix per (collar, fix time), one cue per (collar, time,
  kind), one episode per (collar, start); a report resent after a lost reply changes nothing.
  v2: one record per (device, seq). A server MUST answer a duplicate exactly as the original.
- **v2 identity and replay** ([messages.md §7.1](messages.md#71-counters-that-never-repeat)):
  `seq` and `fcnt` are lifetime counters of the device, never reset by a claim, release or
  reset, so a server keeps them per device id across claims.
  - Per device it keeps the highest `fcnt` accepted and which of the 128 below it it has
    seen, and drops (and counts) an authenticated frame outside that window or seen before.
  - A record whose `(device, seq)` is stored with **different** bytes is a conflict: kept
    aside and flagged to a person, never silently dropped or overwritten.
  - A collar whose `seq` goes backwards (records below its known high-water mark with new
    content) has broken its counter store: flag it, keep its records as conflicts, and treat
    it as needing service.
  - After a **restore from backup**, the window and records are as old as the backup: frames
    from after it may be accepted again, which is correct (they are the collar's own) and
    deduplicated by `(device, seq)` from then on.
- **Never refuse a whole report or batch for one entry.** Store what is valid; drop and count
  what isn't. A value the server doesn't know (a cue kind, an outcome, a status) is stored as
  sent ([registry.md](../registry.md#extensibility)). openpasture does this for v1 cue kinds,
  episode outcomes, ack and slot statuses and reject codes; it still refuses a v1 report for
  a malformed number or a future time (§1).
- **Gaps** (v2): a gap in a collar's seq that stays open for a whole report cycle after the
  collar was last heard is asked for with a resend command, again after 6 hours if still
  open; collars keep records at least 7 days, so a gap is let go only after that.
- **Simulated collars**: data from a collar whose caps include `sim` MUST be shown as
  simulated wherever it appears, and kept out of anything that describes real animals.

## 8. Firmware

A server that sends firmware updates ([firmware.md](firmware.md)) MUST roll out in stages
(one collar per herd, then the herd, then every herd), MUST stop on any `rolled_back` or a
collar that goes silent after installing, and MUST let the owner turn automatic updates off.

## 9. Herds on LoRa

- **Short addresses** are unique per `net`, from 1, filling group 0 (1–300) first. A net
  holds at most 300 × `groups` collars, `groups` ≤ cycle; only a net of one group gives every
  collar a full fast window ([lora.md §3](lora.md#3-the-minute)). Put a herd that moves fast
  as one, and is bigger than 300, on more than one net. Reuse a short only after the collar
  that had it has acknowledged leaving.
- **One schedule per net**: every member gets the same plan, `cycle_s` and `groups`. Raise
  `groups` (to every member) before handing out the first short of the new group, and hand it
  out only once every member has acked the raise. Change the cycle or plan only by a
  membership with `effective_at` to every member, and only to a plan every member lists.
- **The beacon key** is the server's, one per herd: 16 random bytes, wrapped for each member
  in its membership ([lora.md §9](lora.md#9-security-on-the-air)). Rotate it when a member is
  revoked, and yearly.
- **Net ids** are unique among the herds of a farm whose collars can hear each other.
- **Anchors**: at least three per herd, ranked; name the next one in each reply from their
  anchor records (battery, signal, collars heard).
- **The herd's downlink queue** holds the herd boundary in effect and each alive staged one,
  plus per-collar commands. Superseded versions are dropped (`drop`) as soon as a higher one
  takes effect at or before them, as the collars' slot rule does.
- **Roster**: send a new one whenever membership changes; revoked collars go in `revoked`.

## 10. Keys

- The server key is the farm's: keep it out of logs and backups that leave the farm. Rotate
  it with a handover ([identity.md §6](identity.md#6-handover-rotating-the-server-key-or-moving-to-other-software)),
  never by copying it to new software.
- **During a handover**, as the old server: keep the key, the frame keys, the queue and the
  endpoint for the herd until every member has acked it `applied` or its deadline has passed
  for every member; re-send it to members that haven't acked it; and keep the key for as long
  as any member still holds it as current (it fell back). As the new server: re-send the
  confirm (naming the handover's digest) to members that acked `received`; hold other commands
  for a member until it has confirmed; ask for record gaps with a resend.
- Store claim codes only as long as a claim takes; store the owner key's public half only.
- Before a release, ask a person: a released collar on an animal has no fence. A release or
  transfer of a collar with an owner key needs the owner's signature; the server can only
  prepare it.

## 11. Farm policy: zones and leases

A server that sends boundaries to collars listing the cap `zones` ([messages.md §4.7](messages.md#47-zones-and-leases-what-the-collar-enforces-itself)):

1. Keeps one **policy epoch** per farm and raises it with every change to the permanent no-go
   zones (or farm rules they encode). Sends the new zones herd-wide **before** any boundary
   checked against them.
2. Stamps every boundary with `policy`: the epoch it passed the server's own checks against.
3. Sends a **lease** for the current epoch herd-wide every 15 minutes, `until` = now + the
   farm's lease window (default 2 hours, [open question 13](README.md#open-questions)). Never
   a lease for an older epoch.
4. On an epoch change, re-checks every outstanding staged boundary and per-collar copy against
   the new zones, drops the ones that now overlap (`drop`) and restages a corrected schedule;
   collars that already hold one refuse it `in_exclusion` when it comes due.
5. Treats `in_exclusion` as permanent for that version, and a staged slot still `received`
   after its `effective_at` as waiting for zones or a lease, not as an error.

## 12. Claims

- When the card's factory record has a `claim_check`, check a typed or scanned code against
  it before storing it or using airtime, and refuse a mismatch ([identity.md §4](identity.md#4-claim)).
- A collar is **claim pending** until it acks the bind `applied`; the software MUST NOT show
  it as claimed before. `bad_claim` means the code was wrong.
- After the claim, forget the code and keep the `claim_check`. A collar that is unclaimed
  again (its hello carries a claim nonce) is reclaimed by scanning its card again, checked
  against the kept `claim_check`.
- A factory server (one that only makes collars) forgets claim codes when the unit ships,
  unless the maker's support policy says it keeps them; either way the box says which.

## Informative: openpasture's policies

Not required for conformance, but without the first most real drawings come back refused:

- **Fitting.** Each herd boundary is fitted to the strictest limits among the herd's collars
  (outer rings only shrink, holes only grow) with a 0.5 m slack on the gap rule, so rounding
  on a collar never refuses what the server accepted; per-collar fitting for collars with
  smaller limits (firmware 0.1: one ring of 64 vertices, no holes).
- **Fast windows.** A move or an escape gives the herd or the collar a fast window
  (`fast_until` = the estimated end at 4 m/min of what is left, kept between 5 and 30 min,
  plus 10 min), extended while the move runs.
- **Selection** (v1 `GET /boundary`): the boundary in effect when newer than `have`, else the
  lowest alive staged one above `have` that fits `free` and `free_bytes`.
