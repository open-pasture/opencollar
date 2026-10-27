# The LoRa binding

Protocol v2, **draft**. Part of the [v2 spec](README.md). The key words MUST, SHOULD and MAY
are used as in RFC 2119. Vectors: [`../vectors/v2/link.json`](../vectors/README.md#v2linkjson).

How a herd's collars share one LoRa channel: when each one talks, how the herd's link to the
server moves between anchor collars, and how a boundary reaches every collar at once. The
messages themselves are [messages.md](messages.md); this file only carries them.

## 1. Topology

```
   server ── LTE ── active anchor ─┐
                    standby anchor  │  LoRa, one hop, GNSS-timed slots
                    standby anchor  │
           node node node node node ┘
```

- **Star, one hop.** Every collar talks to the active anchor directly. Nodes never relay:
  relaying means listening, and listening costs more than talking.
- **Anchors** (role 2) are collars with LTE as well as LoRa. One at a time is **active**: it
  beacons, carries the herd's frames up and its messages down. The others are **standby**
  and behave as nodes on the LoRa link until it is their turn.
- **Stations** (role 3) are anchors on a post or a building, with no animal and no fence.
  Optional. When a herd has one, servers SHOULD rank it first.
- **Every collar keeps its own GNSS and runs its own fence.** Nothing on this link is needed
  to keep an animal fenced; it only changes what the fence is and reports what happened.

## 2. Radio

A **channel plan** fixes the radio and the shape of the minute. A herd's plan is in its
membership (key 19); its channel is `channels[net mod len]`. Plans are parameters, to be
confirmed against the radio module's FCC grant ([open question 2](README.md#open-questions)).

**Plan 1, `US915_500`:**

| Parameter | Value |
|---|---|
| Band | US 902–928 MHz, FCC Part 15.247 |
| Channels | 903.0 + 1.6 n MHz, n = 0–7 |
| Modulation | LoRa, 500 kHz, SF8, coding rate 4/5, 8-symbol preamble, explicit header, CRC on |
| Rule it relies on | 15.247(a)(2) digital modulation (6 dB bandwidth ≥ 500 kHz): no hopping, power spectral density ≤ 8 dBm in any 3 kHz |
| Power | +20 dBm conducted |
| Sync word | Private (0x12), not LoRaWAN's or Meshtastic's |
| Largest uplink frame | 128 bytes (≈ 95 ms on air); so the largest record is 109 bytes ([messages.md §6](messages.md#6-records-up)) |
| Largest beacon or fragment frame | 222 bytes |
| Largest hello frame | 222 bytes, sent only in the join window |

A plan on 125 kHz channels would have to hop (15.247(a)(1): at least 50 channels, at most
400 ms on any one per 20 s); its `max_dwell_ms` and slot length change, nothing else does.
Time on air is computed as in Semtech AN1200.13 (`Plan::airtime_us` in op-protocol; vectors
in `link.json`).

**What plan 1 relies on and nobody has measured yet.** 15.247(a)(2) needs the *measured* 6 dB
bandwidth of the transmission to be at least 500 kHz and the power spectral density at most
8 dBm in any 3 kHz; setting the LoRa bandwidth register to 500 kHz doesn't establish either.
The module's grant (RAK4630), the antenna and the conducted power must be checked on the real
collar before plan 1 ships ([open question 2](README.md#open-questions)). That rule has no
duty-cycle limit; the 400 ms / 20 s rule above belongs to the hopping route only. A downlink
window fully used is about 13 % of each minute.

A collar lists the plans it can use in its device record (key 18); a membership naming
another is `unsupported`. **Changing a net's plan** is a membership with `effective_at` to
every member, sent only when every member lists the new plan. A collar that hears no beacon
for 10 minutes after switching goes back to its previous plan for 24 hours and listens there,
so a member that missed the change, or a plan that doesn't work in that pasture, recovers
without a visit.

## 3. The minute

Everything runs on **GNSS time**. Each UTC minute (Unix time / 60) on the herd's channel is:

| From (ms after the minute) | To | What |
|---|---|---|
| 0 | 250 | **Beacon** from the active anchor (it starts sending at +10 ms) |
| 250 | 8 000 | **Downlink window**: fragments of the messages the beacon announced |
| 8 000 | 56 000 | **Uplink slots**: 300 slots of 160 ms |
| 56 000 | 59 800 | **Join window**: hellos and backlog, random access |
| 59 800 | 60 000 | Guard |

**Slots.** A collar's slot comes from its short address `s` (membership key 16), never sent:

```
k = (s − 1) mod 300        slot index; the slot starts at 8 000 + 160 k ms
g = (s − 1) div 300        group
C = cycle_s / 60           report cycle in minutes (membership key 20, default 5)
G = groups                 groups the net uses, 1..C (membership key 22, default 1)
p = (minute − k) mod C     the phase of slot k in this minute
```

Every slot of every minute has exactly one owner, whoever is fast:

- **Phase `p < G`** belongs to group `p`. Every collar sends once a cycle, in its own phase,
  which spreads a herd across the cycle and keeps collars sharing a slot index apart.
- **Phase `p ≥ G` is spare.** Spare phase `j = p − G` belongs to group `j mod G`. A collar
  in a fast window (config `fast_until`) also sends in its group's spare phases.
- A short address with `g ≥ G` never sends: a membership giving one is `bad_config`.
- Every collar of a net MUST hold the same plan, `cycle_s` and `groups`. A server changes
  them only by a new membership to every member, raising `groups` before it hands out the
  first short of a new group and only once every member has acked the raise; a collar that
  missed it then uses fewer minutes, never someone else's.

What a net holds, honestly:

| Collars on the net | Groups | Normal rate | Fast rate (default 5-minute cycle) |
|---|---|---|---|
| up to 300 | 1 | once in 5 min | **every minute**, all at once |
| up to 600 | 2 | once in 5 min | 2–3 times in 5 min |
| up to 900 | 3 | once in 5 min | 1–2 times in 5 min |
| up to 1 200 | 4 | once in 5 min | 1–2 times in 5 min (group 0 only) |
| up to 1 500 | 5 | once in 5 min | no faster: no spare minutes |

So a net gives a **full fast window to 300 collars**. A herd that must all be fast at once
during a move, larger than that, is split across nets on other channels (plan 1 has eight).
The pilot's 20–50 collars and a 1 000-head ranch in herds of up to 300 are one net per herd.
`Plan::sends` in op-protocol is the reference; its test runs full nets of every shape with
every collar fast, none, and mixes, and finds no collision; `link.json` has the vectors.

- A collar starts sending 20 ms into its slot. The slot leaves 20 ms of guard each side of a
  full 128-byte frame for clock error.

**Clocks.** A collar times its slots from its GNSS time, kept between fixes by its RTC. A
beacon that authenticates may correct the slot timing by at most ±50 ms from the RTC's
expectation, and only when its `minute` is the collar's own GNSS minute; anything further off
is not the herd's beacon and is ignored. The beacon's `minute` is never a clock for anything
that matters: activation (`effective_at`), expiry, fast windows, leases and acks use GNSS
time only, as in v1.

## 4. Frames

The first byte is `0x2k`: protocol 2, frame kind k. Integers are big-endian. No frame is
longer than 255 bytes. A receiver drops frames of another protocol, another kind or another
`net`, except at the join (`frame::accepts` is the reference):

- an active anchor also takes **hellos with net 0** (collars with no herd);
- a collar with no net yet takes any beacon (only to find the join window) and fragments
  addressed to **dst 0** (its bind may be in them).

| Kind | Layout | |
|---|---|---|
| `20` beacon | `20 \| net u16 \| anchor u16 \| minute u32 \| CBOR map \| tag 8` | Tag: the herd's beacon key (§9) |
| `21` uplink | `21 \| net u16 \| src u16 \| fcnt u32 \| link_len u8 \| link \| sealed records \| tag` | [messages.md §7](messages.md#7-frames-sealing-records) |
| `22` fragment | `22 \| net u16 \| dst u16 \| msg u32 \| idx u16 \| count u16 \| data` | 13-byte header; `1 ≤ count`, `idx < count`, 1–242 data bytes |
| `23` hello | `23 \| net u16 \| COSE_Sign1 hello` | net 0 when the collar has none |

**Beacon map:** 1 `bver` (the highest herd boundary version the anchor holds), 2 `pending`
[short] (collars with a message waiting; 0 for collars with no short yet), 3 `msgs` [[msg,
count, dst, type]] (what this minute's downlink window carries: message id, fragment count,
addressee, message type; 128 for a firmware image), 4 `heard` [first byte, bitmap] (bit k,
LSB first from byte 0, set = slot k's frame was heard last minute: a radio receipt, never a
reason to forget a record, §8), 5 `state` [battery %, LTE quality 0–4, rank], 6 `handon`
[short, minute] (the anchor taking over and the GNSS minute it beacons first), 7 `term` (the
anchor's election term, §5). Every key is optional; a quiet minute's beacon is 20 bytes with
its term and tag.

**Beacon tag:** the first 8 bytes of HMAC-SHA-256 under the herd's 16-byte beacon key, over
every byte of the frame before the tag. A collar that holds a beacon key ignores a beacon
that doesn't verify under it (or under the next key during a change, §9).

**Link section** of an uplink frame, read by the anchor: 1 `got` [msg] (messages this collar
now holds whole), 2 `need` [[msg, from, bitmap]] (bit i set = fragment `from + i` missing), 3
`anchor` [battery %, LTE quality 0–4] (standby anchors only).

`dst` 65 535 means every collar in the herd; `dst` 0 means collars with no short address yet
(joining): the message inside names its device. A message id is the first 4 bytes of SHA-256
of the whole message, so a collar knows a reassembled message is the one announced before it
checks the signature. It is not authentication; the signature is.

## 5. Anchors

One anchor at a time is active on a net. Who it is converges by an **election term**:
every active anchor beacons its term (key 7), and wherever two meet, the higher term wins,
then the lower rank, then the lower short address (`Beacon::outranks`). Anchors keep the
highest term they have heard in flash.

**Hand-on.** An anchor holds the herd's link for `anchor_hold_s` (config key 24, default
3 600 s), then hands it on:

1. The server names the next anchor in its batch reply (`next_anchor`), from what every
   anchor reports (battery, signal, how many collars it hears). With no word from the server,
   the active anchor picks among the standby anchors it heard in the last hour: battery
   ≥ 30 % and LTE quality ≥ 2 first, then the most battery, then the lowest rank.
2. It chooses the hand-on minute H, and for the 5 minutes before H names it in every beacon:
   `handon` [next, H].
3. At minute H the named anchor beacons with term + 1 and posts its first batch. The old one
   listens in minute H instead of beaconing: if it hears the new term it becomes a standby
   (a node with a slot); if not, it beacons again from H + 1 with its own term and hands on
   later, to the same or another anchor. A standby that missed the announcement never takes
   over: it doesn't know H. A standby that heard it acts at H even if the anchors' own
   `anchor_hold_s` differ, because H is absolute.

**Failover.** A standby anchor of rank r that hears no beacon for 2 minutes in a row starts
beaconing, with the last term it heard + 1, at minute `2 + r` after the last one it heard,
unless it has heard a beacon by then. With ranks from 0 the herd's link is back within 2–3
minutes.

**Two active anchors.** A failover race, or two herd groups that drifted apart and back, can
leave two anchors active on one net; transmitting at the same instant they can't hear each
other. So **every active anchor stays silent in about one minute in eight**, chosen from a
hash of its net, short address and the minute (`frame::listen_minute`), and listens for a
beacon instead. Within minutes one hears the other; the one that is outranked becomes a
standby at once. In the minutes when both beacon, collars in reach of both hear one (capture)
or neither; a collar that hears two different anchors follows the one that outranks. Each
anchor posts what it hears and the server keeps one copy of each record by (device, seq).
Records a collar sent while two anchors were active are never lost: `heard` is only a radio
receipt (§8). This rule has a trace in op-protocol's tests; it still needs an RF test with two
real anchors ([open question 1](README.md#open-questions)).

**What an active anchor does each minute:** beacon (except its listen minutes); send the
announced fragments; listen to the uplink slots and the join window; keep every frame it
hears in flash until the server acknowledges the batch that carried it ([http.md](http.md));
post batches at its report interval (sooner in a fast window or with a full queue).

## 6. Join

- **A claimed collar new to the herd** (its membership arrived by phone, by USB or in its
  old herd) listens for its net's beacon on the plan's channel, then uses its slot.
- **A collar that lost the herd** (out of range, beacons stopped) keeps its fence and its
  records. It listens at each minute boundary with a wider window for 10 minutes, then scans
  the plan's channels for its net once every 5 minutes. Once it hears a beacon it sends its
  backlog ([§8](#8-getting-reports-up)).
- **An unclaimed collar** has no net, no short address and no beacon key:
  1. It listens for any beacon, only to find a join window; it can't check one.
  2. It sends a **hello** frame with **net 0** ([identity.md §4](identity.md#how-the-bind-reaches-the-collar))
     at a random time in that join window, then listens to the next minute's downlink.
     With no answer it waits 10 minutes, doubling up to an hour, ± 25 % jitter, before the
     next hello. A hello is at most 222 bytes: caps that don't fit wait for the device record.
  3. The active anchor takes net-0 hellos and relays them to its server in its next batch.
     When the farmer has scanned that card, the server answers with a **bind** and a
     **membership** addressed to the device id (`to` in the reply), and the anchor sends
     them as fragments with **dst 0**, announced with `pending` 0.
  4. A joining collar assembles the dst-0 messages (at most four at once, §7), opens each:
     it keeps a bind that names its device and proves its claim, then a membership from the
     key that bind gave it that names its device, and drops everything else. Two collars
     joining at once each keep only their own. A lost fragment is asked for again with
     `need` from its first frame after the bind, or the whole exchange repeats on its next
     hello.
  5. The membership gives it its short address and the herd's beacon key; it sends its first
     sealed status in its slot with `seq` and `fcnt` continuing its lifetime counters (0 for a
     new collar).

  `link.json` has this whole exchange for two collars joining at once (`joins`).

## 7. Delivering a message to the herd

A boundary goes out **once to the whole herd**: it is herd-scoped and signed once, so every
collar gets the same bytes. This is the reason for this binding: a fence move is mostly
downlink, and per-device downlink is LoRaWAN's weak spot.

1. The anchor splits the message into fragment frames of at most 209 data bytes (a typical
   strip, about 150 bytes, is one fragment; the largest v1 shape about 15).
2. It announces the message in the beacon (`msgs`) and sends every fragment in that minute's
   downlink window. Collars that hold the herd's newest boundary (`bver`) or the message
   already skip the window.
3. Each collar that listened reports in its next uplink frame: `got`, or `need` with the
   fragments it is missing.
4. In the next minutes the anchor sends only the fragments still needed (the union of the
   bitmaps), re-announced, until every collar in the roster has said `got`. A collar not yet
   heard from gets the whole message again when it next talks.
5. After 30 minutes the anchor re-announces it every 10 minutes while anyone lacks it, until
   the server drops it ([http.md](http.md)).

The collar reassembles, checks the message id, then checks the message as any command
([messages.md §4.3](messages.md#43-what-a-collar-checks-in-order)), and acknowledges it in
a record that goes to the server. A boundary takes effect only whole and only after its
signature checks; until then the one in force stays, whatever fragments came.

### 7.1 What a receiver holds

Fragment headers are unauthenticated, so a receiver bounds everything before it allocates
(`fragment::Assemblies` is the reference):

- A command or document is at most **64 fragments** and **12 288 bytes**; a fragment
  claiming a larger count is dropped unseen, and an assembly whose fragments add up to more
  is dropped and starts again.
- A collar assembles at most **4 messages at once**; a new one when all are in use takes the
  place of the one that has waited longest. An assembly with no new fragment for **30
  minutes** is dropped.
- A fragment repeating an index replaces it; if the whole message then fails its id, the
  assembly starts again.
- **Firmware images** (type 128) are never assembled in memory: a collar takes image
  fragments only for a firmware command it has accepted, checks the count against the size
  in its signed manifest, and streams them to the secondary slot.

**One collar's message** (a pen, a config, a membership): the same, with `dst` its short
address and the short in the beacon's `pending`. **Firmware images** go the same way with
type 128 and the message id from the image digest, over many minutes; collars report `need`
windows of up to 64 fragments ([firmware.md](firmware.md#delivery)).

## 8. Getting reports up

- A collar puts its records, oldest first, into one frame in its slot. What doesn't fit
  waits for its next slot (no record is bigger than a frame, [messages.md §6](messages.md#6-records-up));
  a collar with a backlog MAY also send one frame per minute in the join window, at a random
  time in it.
- The next beacon's `heard` says whether the frame arrived: a **radio receipt**. If not, the
  same records go again in a new frame (a new `fcnt`). If so, the collar stops resending
  them, and **keeps them**: in flash for at least 7 days after they were heard, and after
  that until the space is needed (oldest first). A node's 16 MB of flash holds years of a
  collar's records, so in practice nothing is dropped.
- The server's **durable** acknowledgement is its reply to the anchor's batch; records an
  anchor loses before it posts (it died, a forged or mistaken `heard`) show as a gap in the
  collar's seq, and the server asks for them with a resend command, which the collar answers
  from flash.

## 9. Security on the air

- Commands are signed by the server ([messages.md §3](messages.md#3-signed-messages-cose_sign1));
  frames are sealed per collar ([§7 there](messages.md#7-frames-sealing-records)). An
  attacker on the radio can't move a fence, impersonate a collar, or read its reports.
- **Beacons are authenticated** with the herd's **beacon key** (16 bytes, one per herd).
  The server makes it and gives it to every claimed member in its membership (key 23),
  wrapped for that collar: AES-128-CCM under the collar's **wrap key** (HKDF of the same
  X25519 secret as its frame key, label `"wrap"`, [identity.md §9](identity.md#9-frame-keys-and-transport-security)),
  nonce `device_id ‖ membership version ‖ 0x02`, associated data `"beacon" ‖ len(herd) ‖
  herd ‖ net`. So only that collar can unwrap it, and it can't be moved to another herd or
  net. Anchors tag beacons with it; collars ignore a beacon that doesn't verify.
- **Changing the beacon key** (a member revoked or lost, or yearly): the server sends every
  member a membership with the next key; a collar holds its current and next keys and takes
  a beacon under either; anchors switch to the next key once every member has acked it, and
  collars drop the old key when they first hear the new one.
- **What a beacon can and can't do.** It can't change a fence, a key, a version or a clock
  that matters. Even authenticated, its `heard` never makes a collar forget a record (§8);
  its timing can move slots by at most ±50 ms (§3); its `term` decides only which anchor is
  active. Every collar of the herd holds the beacon key, so a captured collar could forge
  beacons: the worst it can do is what jamming does (delay reports, waste battery) and make
  itself the active anchor until the server revokes it and rotates the key. A new firmware
  image never needs a beacon to prove itself ([firmware.md](firmware.md#on-the-collar-in-order)).
- An unclaimed collar can't check beacons; it uses one only to find the join window.
- Link sections are authenticated (they are associated data) but only the server can check
  them. A forged `need` makes the anchor resend fragments; a forged `got` can delay one
  collar's copy until the next re-announcement.

## 10. Off the network

Out of range of any anchor, nothing breaks: the collar enforces the boundary it holds, takes
its staged boundaries on time by GNSS, cues as always, and keeps its records until it hears
a beacon again.
