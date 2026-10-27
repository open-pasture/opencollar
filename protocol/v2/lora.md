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
| Largest uplink frame | 128 bytes (≈ 95 ms on air) |
| Largest beacon or fragment frame | 222 bytes |

A plan on 125 kHz channels would have to hop (15.247(a)(1): at least 50 channels, at most
400 ms on any one per 20 s); its `max_dwell_ms` and slot length change, nothing else does.
Time on air is computed as in Semtech AN1200.13 (`Plan::airtime_us` in op-protocol; vectors
in `link.json`).

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
```

- Normally a collar sends once per cycle, in the minutes where `minute mod C = (k + g) mod C`.
  That spreads a herd evenly across the cycle and keeps collars that share a slot index
  (one group apart) in different minutes.
- In a fast window (config `fast_until`) a collar of group 0 sends every minute.
- So a channel holds `300 × C` collars (1 500 at the default cycle), and 300 of them can be
  fast at once. A server MUST NOT give out short addresses beyond that ([server.md §9](server.md#9-herds-on-lora)).
- A collar starts sending 20 ms into its slot. The slot leaves 20 ms of guard each side of a
  full 128-byte frame for clock error.

**Clocks.** A collar times its slots from its GNSS time, kept between fixes by its RTC and
corrected by every beacon's arrival. The beacon's `minute` is never a clock for anything
that matters: activation (`effective_at`), expiry, fast windows and acks use GNSS time only,
as in v1.

## 4. Frames

The first byte is `0x2k`: protocol 2, frame kind k. Integers are big-endian. A receiver
drops frames of another protocol, another kind or another `net`.

| Kind | Layout | |
|---|---|---|
| `20` beacon | `20 \| net u16 \| anchor u16 \| minute u32 \| CBOR map` | Unsigned (§9) |
| `21` uplink | `21 \| net u16 \| src u16 \| fcnt u32 \| link_len u8 \| link \| sealed records \| tag` | [messages.md §7](messages.md#7-frames-sealing-records) |
| `22` fragment | `22 \| net u16 \| dst u16 \| msg u32 \| idx u16 \| count u16 \| data` | 13-byte header |
| `23` hello | `23 \| net u16 \| COSE_Sign1 hello` | net 0 when the collar has none |

**Beacon map:** 1 `bver` (the highest herd boundary version the anchor holds), 2 `pending`
[short] (collars with a message waiting), 3 `msgs` [[msg, count, dst, type]] (what this
minute's downlink window carries: message id, fragment count, addressee, message type; 128
for a firmware image), 4 `heard` [first byte, bitmap] (bit k, LSB first from byte 0, set =
slot k's frame was heard last minute), 5 `state` [battery %, LTE quality 0–4, rank], 6
`next` (the short address taking over at the next hand-on). Every key is optional; a quiet
minute's beacon is 10 bytes.

**Link section** of an uplink frame, read by the anchor: 1 `got` [msg] (messages this collar
now holds whole), 2 `need` [[msg, from, bitmap]] (bit i set = fragment `from + i` missing), 3
`anchor` [battery %, LTE quality 0–4] (standby anchors only).

`dst` 65 535 means every collar in the herd. A message id is the first 4 bytes of SHA-256 of
the whole message, so a collar knows a reassembled message is the one announced before it
checks the signature.

## 5. Anchors

**Hand-on.** An anchor holds the herd's link for `anchor_hold_s` (config key 24, default
3 600 s), then hands it on at a minute boundary:

1. The server names the next anchor in its batch reply (`next_anchor`), from what every
   anchor reports (battery, signal, how many collars it hears). With no word from the server,
   the active anchor picks among the standby anchors it heard in the last hour: battery
   ≥ 30 % and LTE quality ≥ 2 first, then the most battery, then the lowest rank.
2. For the last 5 minutes of its hold the active anchor names it in `next`.
3. At the hand-on minute the named anchor beacons and posts its first batch; the old one
   goes quiet and becomes a standby (a node with a slot).

**Failover.** A standby anchor of rank r that hears no beacon for 2 minutes in a row starts
beaconing at minute `2 + r` after the last one it heard, unless it has heard a beacon by
then. The first to beacon wins; with ranks from 0 the herd's link is back within 2–3
minutes. An anchor that hears another anchor's beacon on its net with a lower rank, or the
one the server named, stops beaconing.

**Split herds.** Two active anchors on one net (a herd split across paddocks, a failover race)
do no harm: collars follow the beacon they hear, both anchors post what they hear, and the
server keeps one copy of each record by (device, seq).

**What an active anchor does each minute:** beacon; send the announced fragments; listen to
the uplink slots and the join window; keep every frame it hears in flash until the server
acknowledges the batch that carried it ([http.md](http.md)); post batches at its report
interval (sooner in a fast window or with a full queue).

## 6. Join

- **A claimed collar new to the herd** (its membership arrived by phone, by USB or in its
  old herd) listens for its net's beacon on the plan's channel, then uses its slot.
- **A collar that lost the herd** (out of range, beacons stopped) keeps its fence and its
  records. It listens at each minute boundary with a wider window for 10 minutes, then scans
  the plan's channels for its net once every 5 minutes. Once it hears a beacon it sends its
  backlog ([§8](#8-getting-reports-up)).
- **An unclaimed collar** sends a hello ([identity.md §4](identity.md#how-the-bind-reaches-the-collar))
  in the join window of any beacon it hears, at most once every 10 minutes. A hello is
  signed by the device key, so the server checks it against the card. The anchor relays it;
  when the farmer has scanned that card, the server answers with a bind and a membership
  addressed to the device id, and the anchor delivers them in the downlink window to a
  `pending` entry of 0 (the collar listens after each hello).

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
a record that goes to the server.

**One collar's message** (a pen, a config, a membership): the same, with `dst` its short
address and the short in the beacon's `pending`. **Firmware images** go the same way with
type 128 and the message id from the image digest, over many minutes; collars report `need`
windows of up to 64 fragments ([firmware.md](firmware.md#delivery)).

## 8. Getting reports up

- A collar puts its records, oldest first, into one frame in its slot. What doesn't fit
  waits for its next slot; a collar with a backlog MAY also send one frame per minute in the
  join window, at a random time in it.
- The next beacon's `heard` says whether the frame arrived. If not, the same records go
  again in a new frame (a new `fcnt`). Records stay in the collar's flash until heard.
- An anchor keeps what it heard until the server acknowledges it. Records an anchor loses
  (it died before posting) show as a gap in the collar's seq, and the server asks for them
  with a resend command.

## 9. Security on the air

- Commands are signed by the server ([messages.md §3](messages.md#3-signed-messages-cose_sign1));
  frames are sealed per collar ([§7 there](messages.md#7-frames-sealing-records)). An
  attacker on the radio can't move a fence, impersonate a collar, or read its reports.
- **Beacons are not authenticated.** Nothing in a beacon changes a fence, a key or a clock:
  it only says when to listen and what is being sent. A forged beacon can waste a collar's
  battery or delay its reports, as jamming can. Herd keys to authenticate beacons are
  [open question 6](README.md#open-questions).
- Link sections are authenticated (they are associated data) but only the server can check
  them. A forged `need` makes the anchor resend fragments; a forged `got` can delay one
  collar's copy until the next re-announcement.

## 10. Off the network

Out of range of any anchor, nothing breaks: the collar enforces the boundary it holds, takes
its staged boundaries on time by GNSS, cues as always, and keeps its records until it hears
a beacon again.
