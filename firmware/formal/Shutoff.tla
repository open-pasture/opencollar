---------------------------- MODULE Shutoff ----------------------------
(* Welfare auto shut-off and the caretaker re-arm, as firmware/src/cue.c does them
   on main (synced at 3c010f8). One variable per cue.c field that the rules need;
   each action names the cue.c function it stands for.

   Rules (INVARIANTS):
     NoCueWhileShutOff      cue.c decide(): no cue while enforcement_off
     BoundaryKeepsShutoff   cue_rearm_at() (a new boundary, #22) never clears shut-off
     ShutoffSurvivesReboot  a reboot never clears shut-off; only the caretaker does
     TypeOK                 pulse cutoff: outside_cues <= max_outside_cues

   Left out: rest / max_active timers (they only silence cues), episodes, welfare
   event queue, warning volume, track mode (cue_enforcement_active is false there).
   Time is abstract: DayPasses stands for the 24 h escape window running out. *)
EXTENDS Naturals

CONSTANTS
  MaxOutsideCues,        \* cfg.max_outside_cues (default 3)
  EscapeCycleLimit,      \* cfg.escape_cycle_limit (default 3)
  BoundaryClearsShutoff, \* TRUE: cue_rearm_at as at 6098e2d, before #22
  RebootKeepsShutoff     \* FALSE: main (RAM only). TRUE: #25 persists shut-off

VARIABLES
  armed, seenOutside, escaping, crossedOut, pulseCutoff, outsideCues,
  escapeCycles, windowOpen, enforcementOff,
  cue,        \* what this step sounded: "none", "warn", "outside"
  prevOff,    \* enforcementOff before this step
  lastStep    \* the step just taken, for the rules and the chart

vars == <<armed, seenOutside, escaping, crossedOut, pulseCutoff, outsideCues,
          escapeCycles, windowOpen, enforcementOff, cue, prevOff, lastStep>>

TypeOK ==
  /\ outsideCues \in 0..MaxOutsideCues
  /\ escapeCycles \in 0..EscapeCycleLimit
  /\ cue \in {"none", "warn", "outside"}

\* cue_init: everything zero
Fresh(name) ==
  /\ armed' = FALSE /\ seenOutside' = FALSE /\ escaping' = FALSE
  /\ crossedOut' = FALSE /\ pulseCutoff' = FALSE /\ outsideCues' = 0
  /\ cue' = "none" /\ lastStep' = name

Init ==
  /\ armed = FALSE /\ seenOutside = FALSE /\ escaping = FALSE
  /\ crossedOut = FALSE /\ pulseCutoff = FALSE /\ outsideCues = 0
  /\ escapeCycles = 0 /\ windowOpen = FALSE /\ enforcementOff = FALSE
  /\ cue = "none" /\ prevOff = FALSE /\ lastStep = "boot"

\* decide(), GEOFENCE_INSIDE, with note_return() and clear_escape_state()
FixInside ==
  /\ prevOff' = enforcementOff
  /\ IF crossedOut
       THEN LET n == IF windowOpen THEN escapeCycles + 1 ELSE 1
                off == enforcementOff \/ n >= EscapeCycleLimit
            IN /\ escapeCycles' = n
               /\ windowOpen' = TRUE
               /\ enforcementOff' = off
               /\ armed' = ~off
       ELSE /\ UNCHANGED <<escapeCycles, windowOpen, enforcementOff>>
            /\ armed' = (armed \/ ~enforcementOff)
  /\ escaping' = FALSE /\ pulseCutoff' = FALSE /\ outsideCues' = 0 /\ crossedOut' = FALSE
  /\ UNCHANGED seenOutside
  /\ cue' = "none" /\ lastStep' = "inside"

\* decide(), GEOFENCE_WARNING
FixWarning ==
  /\ prevOff' = enforcementOff
  /\ LET a == armed \/ (~seenOutside /\ ~enforcementOff)
     IN /\ armed' = a
        /\ cue' = IF a /\ ~enforcementOff THEN "warn" ELSE "none"
  /\ escaping' = FALSE
  /\ UNCHANGED <<seenOutside, crossedOut, pulseCutoff, outsideCues,
                 escapeCycles, windowOpen, enforcementOff>>
  /\ lastStep' = "warning"

\* decide(), GEOFENCE_OUTSIDE. budgetOk: outside_max_ms not yet spent (time is abstract)
FixOutside(budgetOk) ==
  /\ prevOff' = enforcementOff
  /\ LET cross == armed /\ ~enforcementOff
         esc   == IF cross THEN TRUE ELSE escaping
         cut   == IF cross THEN FALSE ELSE pulseCutoff
         n     == IF cross THEN 0 ELSE outsideCues
         sound == ~enforcementOff /\ esc /\ ~cut /\ budgetOk /\ n < MaxOutsideCues
         n2    == IF sound THEN n + 1 ELSE n
         last  == sound /\ n2 >= MaxOutsideCues
     IN /\ armed' = IF cross THEN FALSE ELSE armed
        /\ crossedOut' = (crossedOut \/ cross)
        /\ outsideCues' = n2
        /\ cue' = IF sound THEN "outside" ELSE "none"
        /\ escaping' = IF ~enforcementOff /\ esc /\ ~cut /\ (~sound \/ last) THEN FALSE ELSE esc
        /\ pulseCutoff' = IF ~enforcementOff /\ esc /\ ~cut /\ (~sound \/ last) THEN TRUE ELSE cut
  /\ seenOutside' = TRUE
  /\ UNCHANGED <<escapeCycles, windowOpen, enforcementOff>>
  /\ lastStep' = "outside"

\* cue_rearm_at(): a new boundary
NewBoundary ==
  /\ prevOff' = enforcementOff
  /\ Fresh("boundary")
  /\ IF BoundaryClearsShutoff
       THEN /\ escapeCycles' = 0 /\ windowOpen' = FALSE /\ enforcementOff' = FALSE
       ELSE UNCHANGED <<escapeCycles, windowOpen, enforcementOff>>

\* cue_clear_shutoff_at(): the caretaker re-arm (serial `rearm`)
CaretakerRearm ==
  /\ prevOff' = enforcementOff
  /\ escaping' = FALSE /\ pulseCutoff' = FALSE /\ outsideCues' = 0 /\ crossedOut' = FALSE
  /\ escapeCycles' = 0 /\ windowOpen' = FALSE /\ enforcementOff' = FALSE
  /\ UNCHANGED <<armed, seenOutside>>
  /\ cue' = "none" /\ lastStep' = "caretaker"

\* The 24 h escape window runs out (note_return starts a new one at the next return)
DayPasses ==
  /\ windowOpen
  /\ prevOff' = enforcementOff
  /\ windowOpen' = FALSE
  /\ UNCHANGED <<armed, seenOutside, escaping, crossedOut, pulseCutoff, outsideCues,
                 escapeCycles, enforcementOff>>
  /\ cue' = "none" /\ lastStep' = "day"

\* Power cycle: main() -> cue_init() -> app_boot() -> cue_rearm_at()
Reboot ==
  /\ prevOff' = enforcementOff
  /\ Fresh("reboot")
  /\ IF RebootKeepsShutoff
       THEN UNCHANGED <<escapeCycles, windowOpen, enforcementOff>>
       ELSE /\ escapeCycles' = 0 /\ windowOpen' = FALSE /\ enforcementOff' = FALSE

Next ==
  \/ FixInside \/ FixWarning \/ FixOutside(TRUE) \/ FixOutside(FALSE)
  \/ NewBoundary \/ CaretakerRearm \/ DayPasses \/ Reboot

Spec == Init /\ [][Next]_vars

NoCueWhileShutOff == enforcementOff => cue = "none"
BoundaryKeepsShutoff == (prevOff /\ lastStep = "boundary") => enforcementOff
ShutoffSurvivesReboot == (prevOff /\ lastStep = "reboot") => enforcementOff
=============================================================================
