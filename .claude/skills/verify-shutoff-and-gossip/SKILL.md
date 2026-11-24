---
name: verify-shutoff-and-gossip
description: >-
  Formal check of the collar's welfare auto shut-off / caretaker re-arm (cue.c) and the
  fence-gossip rule that a beacon hint never outranks a signed manifest. Use before
  merging any change to firmware/src/cue.c, cue.h, app.c, main.c's boot, the serial
  `rearm` command, shut-off persistence or remote rearm (#25), firmware/lora (#6), or
  docs/firmware/pilot-firmware-spec.md section 4.
---

# Verify shut-off and fence gossip

Two promises, each with the harm if it breaks:

- **Shut-off holds until a person re-arms.** Once 3 escape→return cycles in 24 h trip auto shut-off, the collar makes no sound until the caretaker re-arms it. Not a fence move, not a mode change, not a reboot. If it breaks, an animal that keeps escaping gets cued again with nobody checking on it.
- **A beacon hint never outranks a signed manifest.** Beacons are unauthenticated. If a beacon-made pending slot can make a node refuse the server's newer signed fence, anyone with a radio can freeze a herd on an old fence.

## Run

```sh
firmware/formal/check.sh
```

About 5 s. Needs Java 11+ and TLC 1.7.4; the script's header has the install lines and the jar's sha256. `make -C firmware/tests/host` (CI) also runs the code-level half, `test_cue_explore`.

Expected output on main:

```
ok    Shutoff_main: pass
ok    Shutoff: ShutoffSurvivesReboot
ok    Shutoff_pr25: pass
ok    Shutoff_pre22: BoundaryKeepsShutoff
ok    FenceGossip: pass
ok    FenceGossip_broken: HintNeverOutranksManifest
cue explore: ... all tests passed
```

Read every TLC result, pass or fail, with the pstack `/statechart` skill. The views are `firmware/formal/Shutoff.view.ts` and `FenceGossip.view.ts`. It turns a counterexample into the shortest path in plain words and redraws `Shutoff.mmd` / `FenceGossip.mmd`.

## What each piece checks

| File | Checks | How |
| --- | --- | --- |
| `firmware/formal/Shutoff.tla` | `NoCueWhileShutOff`, `BoundaryKeepsShutoff`, `ShutoffSurvivesReboot`, `TypeOK` (≤ 3 outside cues per crossing) | TLC, every order of: fix inside / warning / outside (time budget left or spent), new boundary, caretaker re-arm, 24 h window ends, reboot |
| `firmware/tests/host/test_cue_explore.c` | R1 no cue while shut off, R2 only the caretaker clears shut-off, R3 ≤ 3 outside cues per crossing | The real `cue.c`, every sequence of 7 events to depth 9 (47 M steps, about 1 s). No reboot: see F1 |
| `firmware/formal/FenceGossip.tla` | `HintNeverOutranksManifest`, `ActiveIsSigned`, `NoRollback` | TLC over one node: beacons for seq 1..4 (forged above 2), signed manifests 1..2, activation |

The `_pre22` and `_broken` configs are the broken variants. They must keep failing; if one passes, the model no longer sees that bug.

## Findings

- **F1 (open on main, fixed by #25):** a reboot clears shut-off. `cue` state lives only in RAM; `main()` → `app_init()` → `cue_init()` zeroes it, and nothing reloads it. Path: inside, then 3× (outside, inside) → shut off → power cycle → armed again on the next inside fix. Replayed on the real `app_init`/`app_boot` with `store_ram`: enforcement `off` before reboot, `on` after.

## Real bug or modeling error

1. Read the counterexample with `/statechart`.
2. Replay it on the real code. For shut-off, add the steps to `test_cue_explore.c` or a `test_cue.c` case (one `cue_update` / `cue_rearm_at` / `cue_clear_shutoff_at` / `app_init`+`app_boot` per TLA+ step). If the code doesn't break, assume the model is wrong until you show otherwise.
3. Never weaken an invariant to make it pass. A property the code breaks is a finding: report it with the path in the code's words.

## Coverage

Synced at `3c010f8` (origin/main). Move this forward only after you confirm the model still matches the code at the new commit.

| Model action / rule | Code (on main) |
| --- | --- |
| `FixInside` | `cue.c` `decide()` `GEOFENCE_INSIDE`, `note_return()`, `clear_escape_state()` |
| `FixWarning` | `decide()` `GEOFENCE_WARNING` |
| `FixOutside(budgetOk)` | `decide()` `GEOFENCE_OUTSIDE`, the outside budget, `engage_pulse_cutoff()` |
| `NewBoundary` | `cue_rearm_at()`, called from `app.c` `apply_boundary()`, `app_boot()`, `app_bench()` |
| `CaretakerRearm` | `cue_clear_shutoff_at()`, serial `rearm` in `app.c` `app_line()` |
| `DayPasses` | `note_return()`'s `escape_cycle_window_ms` reset |
| `Reboot` | `main.c` `main()` → `app_init()` → `cue_init()`, then `app_boot()` |
| `FenceGossip.tla` | Design only: `docs/firmware/pilot-firmware-spec.md` §4. No gossip code on main |

Left out of `Shutoff.tla`: rest and `max_active_ms` timers (they only silence cues), episodes, the welfare event queue, warning volume, track mode (`cue_enforcement_active()` is false there; the explorer does toggle it). Left out of `FenceGossip.tla`: fragments and their hashes (one `FragmentsArrive` step), Trickle timing, serving neighbours, same seq with a different hash, flash persistence, liveness.

## When the code changes

- **#25 lands** (persisted shut-off, signed remote rearm): flip `Shutoff.cfg`'s expected result in `check.sh` to `pass` and delete `Shutoff_pr25.cfg`. Add a `RemoteRearm(seq)` action with a persisted `rearmSeq`: a rearm with seq ≤ the last accepted one is refused, and `rearmSeq` survives `Reboot`. Add the rules "a stale rearm never clears shut-off" and "reboot keeps `rearmSeq`". In `test_cue_explore.c`, add reboot (reload from `store_ram`) and a stale remote rearm as events, then delete the F1 note.
- **#6 lands** (`firmware/lora`): map `HearBeacon` / `ReceiveManifest` / `FragmentsArrive` to `fence_node.c`, mainly `begin_pending_from_manifest()` and `activate_pending()`, and add those rows to Coverage. Its 3-way rule (a real manifest replaces a hint whatever the seq; a sealed one preempts a local one; otherwise the higher seq wins) needs a `local` kind in `pending`. Add a bounded explorer over `fence_node.c` like `test_cue_explore.c`.
- **Any other change to a covered function:** re-read it against its action, update the model in the same PR, rerun `check.sh`, and move the sync commit.
