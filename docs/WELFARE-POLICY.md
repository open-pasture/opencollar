# Collar welfare policy

How OpenCollar limits cues so virtual fencing is kinder than tangled wire.
Informed by public commentary on Nofence's N3 collar (Alexander Crawley,
Nuffield Farming Scholar). Firmware lives in `firmware/src/cue.c`.

**Status:** audio-first (V0). The same counters will gate a future pulse
module. Thresholds below are **conservative defaults that need review by
someone with animal-welfare expertise** before pulse hardware ships, and
should be re-checked after field data from the pilot farm.

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
| Outside/pulse cues per boundary crossing | **2** | `max_outside_cues` |
| Then suspend until clear inside (`GEOFENCE_INSIDE`) | always | (state: `pulse_cutoff`) |
| Escape→return cycles before auto shut-off | **3** | `escape_cycle_limit` |
| Rolling window for those cycles | **1 hour** | `escape_cycle_window_ms` |
| Clear shut-off | new boundary / `cue_rearm` | — |

Existing caps still apply: warning cues at most 20 s continuous then 30 s
rest; outside cues also stop after `outside_max_ms` (10 s) if the count
budget has not already been spent.

While auto shut-off is active, the fence still evaluates (state and margin)
but no warn or outside cue plays. `status` reports `enforcement off`. A new
boundary (or `cue_rearm`) resumes enforcement and emits
`enforcement_resumed`.

## Welfare events

Queued like episodes; drained by `cue_take_welfare`, logged as
`welfare: …` on the serial console:

| Kind | When |
| --- | --- |
| `pulse_cutoff` | Outside cue budget (count or time) spent for this crossing |
| `returned` | Clear inside after a counted crossing (one escape cycle) |
| `auto_shutoff` | Escape-cycle limit hit; enforcement off |
| `enforcement_resumed` | Shut-off cleared by rearm / new boundary |

## Open questions for welfare review

- Are **2** outside/pulse cues per crossing and **3** cycles per hour the
  right defaults for cattle (and later sheep/goats)?
- Should shut-off clear only on a new boundary, or also after a long quiet
  period / explicit caretaker command?
- When the pulse board ships, should warning **audio** share the same count
  budget as the pulse, or stay on the existing time/rest caps only?
- Should welfare events be a separate report array, or folded into episodes /
  a `welfare` cap in the protocol registry?
