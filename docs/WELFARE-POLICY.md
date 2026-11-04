# Collar welfare policy

How OpenCollar limits cues so virtual fencing is kinder than tangled wire.
Informed by public commentary on Nofence's N3 collar (Alexander Crawley,
Nuffield Farming Scholar). Firmware lives in `firmware/src/cue.c`.

**Status:** audio-first (V0). The same counters will gate a future pulse
module. Thresholds below are **conservative defaults that need review by
someone with animal-welfare expertise** before pulse hardware ships, and
should be re-checked after field data from the pilot farm.

**Shock / pulse hardware:** interfaces only are reserved in
[`SHOCK-MODULE-INTERFACE.md`](SHOCK-MODULE-INTERFACE.md) (op-architect
record O; Cody standing rule 2026-11-04 — one production design, module may
be unfitted at first). **Placement decided (Cody):** side pods, not the top
unit; [`BOTTOM-BAY.md`](BOTTOM-BAY.md) pulse text is superseded. Reserving
connectors, states, and report field names **changes no cue behaviour**. If
nothing is fitted, no firmware path may drive it; default is OFF. **No
welfare reviewer is named yet** — the module stays **OFF in all builds**
until one is named **and** Cody approves. Owner opt-in, an audit log, and a
ready module are also required; the server offers no pulse settings
otherwise. Dual enable / `pulse_grant` / `GATE_LATCH` are **proposed,
awaiting Cody**. Hardware current limit stays TBD. Module faults clear when
a person **re-enables** the module — not via welfare `rearm`
(`welfare.enforcement` / record L).

## Principles

1. **A cue only teaches when the animal can escape it** by moving away from
   the edge. Already true: only a crossing is cued; walking back in is silent;
   a new boundary that leaves an animal outside is silent until clear inside.
2. **Bounded stimuli per crossing.** After a short outside/pulse budget, stop.
   Restart the warning–pulse system only once the animal is clear inside the
   geofence (not merely in the warning zone).
3. **Auto shut-off beats endless punishment.** If an animal repeatedly escapes
   and returns, turn enforcement off for that animal. Physical fencing offers
   no reprieve when an animal is tangled; virtual fencing must.
4. **Battery savings never override welfare.** Duty-cycling GNSS, LoRa, or
   reports must not weaken cutoffs, shut-off, or the logging of welfare
   events. Prefer smarter herd communication over a bigger pack, but not at
   the expense of these behaviours.
5. **Welfare is observable.** Cutoffs, returns, and shut-offs are first-class
   events (serial today; report uplink when the network path lands), so the
   collar can also serve as a monitoring platform.

## Behaviour

| Rule | Default | Config field |
| --- | --- | --- |
| Outside/pulse cues per boundary crossing | **3** | `max_outside_cues` |
| Then suspend until clear inside (`GEOFENCE_INSIDE`) | always | (state: `pulse_cutoff`) |
| Escape→return cycles before auto shut-off | **3** | `escape_cycle_limit` |
| Fixed window for those cycles (starts at first escape; resets after 24 h) | **24 hours** | `escape_cycle_window_ms` |
| Clear shut-off | explicit caretaker re-arm only (`cue_clear_shutoff` / serial `rearm`); a new boundary never clears it | — |

Existing caps still apply: warning cues at most 20 s continuous then 30 s
rest; outside cues also stop after `outside_max_ms` (10 s) if the count
budget has not already been spent.

While auto shut-off is active, the fence still evaluates (state and margin)
but no warn or outside cue plays. `status` reports `enforcement off`. Only an
explicit caretaker re-arm (per collar) clears shut-off, resets the escape-cycle
counters, and emits `enforcement_resumed`. A new boundary / fence update
disarms cueing for the usual "animal left outside stays silent" reasons, but
leaves shut-off and the cycle counters alone.

**Decision (Cody, Nov 3):** a fence move must not clear auto shut-off. Once
shut-off trips, enforcement stays off until a person re-arms that collar.

## Welfare events

Queued like episodes; drained by `cue_take_welfare`, logged as
`welfare: …` on the serial console:

| Kind | When |
| --- | --- |
| `pulse_cutoff` | Outside cue budget (count or time) spent for this crossing |
| `returned` | Clear inside after a counted crossing (one escape cycle) |
| `auto_shutoff` | Escape-cycle limit hit; enforcement off |
| `enforcement_resumed` | Shut-off cleared by explicit caretaker re-arm |

## Open questions for welfare review

- Are **3** outside/pulse cues per crossing and **3** cycles per 24 h the
  right defaults for cattle (and later sheep/goats)? See *Basis for the
  defaults*; they still need sign-off from an animal-welfare expert, and no
  collar goes on an animal before that review. **No welfare reviewer is
  named yet**; the shock module stays OFF in all builds until one is named
  and Cody approves — see
  [`SHOCK-MODULE-INTERFACE.md`](SHOCK-MODULE-INTERFACE.md).
- When the pulse module ships, should warning **audio** share the same count
  budget as the pulse, or stay on the existing time/rest caps only?
- Should welfare events be a separate report array, or folded into episodes /
  a `welfare` cap in the protocol registry?
- Hardware current-limit value for the reserved shock module (see
  [`SHOCK-MODULE-INTERFACE.md`](SHOCK-MODULE-INTERFACE.md))?

## Basis for the defaults

No vendor publishes a full threshold set; these are the published anchors.

- **3 cues per crossing (strong, published).** Nofence's user guide: an
  escaping animal gets at most three audio zones / three electric pulses,
  then the fence function switches off, the farmer is alerted, and it
  re-activates when the animal returns
  (https://www.manula.com/manuals/nofence-as/master-user-guide/1/en/topic/the-nofence-boundary).
  Nofence's submission to the Norwegian government gives the welfare reason:
  if three aversive stimuli fail, more will not work
  (https://regjeringen.no/contentassets/5bccb513f5cf47c78995247bce67b672/nofence-as.pdf).
  V0 is audio only, so the cue is not aversive; matching the published
  pulse cap keeps the counter ready to gate the pulse module unchanged.
- **3 escape cycles per 24 h, then off until caretaker re-arm (moderate; daily
  window inferred).** Halter states it has time-bound limits and daily
  maximums on pulses, after which the collar is disabled and the farmer
  alerted, but does not publish the numbers
  (https://www.halterhq.com/animal-welfare-charter/system-overview). The
  2012 Nofence sheep trial: **4 pulses a day, audio continued**
  (http://hdl.handle.net/11250/2447492). Counting escapes (rather than
  pulses) for shut-off is **our own design choice**, not taken from that
  trial. A fixed 24 h window is stricter than the old 1 h placeholder:
  three escapes spread across a day now also trigger shut-off.
- **Re-arm only by an explicit caretaker command (conservative).** Decided
  Nov 3 (Cody): a fence move alone must never resume enforcement. Halter
  reactivates only once the animal shows it responds to cues; we have no
  such test yet, so a person decides, per collar.
- **Learning context.** Campbell et al. 2019 (eShepherd): cattle needed on
  average 2.5 audio+pulse pairings (range 1-6) before responding to audio
  alone; 71.5% of cues were audio-only over 4 weeks
  (https://www.frontiersin.org/journals/veterinary-science/articles/10.3389/fvets.2019.00445/full).
  Verdon/TIA (Halter): most learning within 1 day; about 2.6 pulses per 100
  audio cues once trained
  (https://www.utas.edu.au/__data/assets/pdf_file/0007/1675699/Factsheet-Managing-dairy-cows-with-Halter-virtual-fencing-technology-2023.pdf).
- Vence, eShepherd (Gallagher) and Smart Paddock thresholds were not found
  in public sources.
