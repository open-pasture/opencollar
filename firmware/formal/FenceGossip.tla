------------------------- MODULE FenceGossip -------------------------
(* One node's fence exchange, as docs/firmware/pilot-firmware-spec.md section 4
   describes it on main (synced at 3c010f8). There is no gossip code on main; the
   draft code is firmware/lora on PR #6 (fence_node.c begin_pending_from_manifest).

   A beacon is an unauthenticated hint: anyone can send any fence_seq. Hearing a newer
   seq makes the node want that fence, so it holds a "pending" slot for it. A manifest
   is signed by the server, and only the server's seqs 1..ServerSeq exist as manifests.
   A fence activates only from a complete, verified pending manifest.

   Rules (INVARIANTS):
     HintNeverOutranksManifest  a pending slot made by a beacon never makes the node
                                refuse a newer signed manifest
     ActiveIsSigned             the fence in force always has a real server seq
     NoRollback                 the fence in force never goes back to an older seq

   Left out: fragments and their hashes (FragmentsArrive stands for the whole
   reassembly passing its checks), Trickle timing, serving neighbours, the hash
   mismatch case (same seq, different hash), flash persistence. *)
EXTENDS Naturals

CONSTANTS
  ServerSeq,       \* the newest fence_seq the server has signed
  MaxSeq,          \* the largest seq a (forged) beacon may claim; > ServerSeq
  HigherSeqAlwaysWins \* TRUE: broken variant, pending slot ranked by seq alone

VARIABLES
  active,      \* fence_seq in force (0: the factory/boot fence)
  pending,     \* [kind |-> "none" | "hint" | "real", seq |-> n]
  refused,     \* TRUE once a newer signed manifest was refused for a hint
  prevActive,  \* active before this step
  lastStep

vars == <<active, pending, refused, prevActive, lastStep>>

None == [kind |-> "none", seq |-> 0]

TypeOK ==
  /\ active \in 0..MaxSeq
  /\ pending \in [kind : {"none", "hint", "real"}, seq : 0..MaxSeq]

Init ==
  /\ active = 0 /\ pending = None /\ refused = FALSE
  /\ prevActive = 0 /\ lastStep = "boot"

\* Hear a beacon naming seq s (real or forged): newer than ours -> want it
HearBeacon(s) ==
  /\ s > active
  /\ \/ pending.kind = "none"
     \/ pending.kind = "hint" /\ pending.seq < s
  /\ pending' = [kind |-> "hint", seq |-> s]
  /\ UNCHANGED <<active, refused>>
  /\ prevActive' = active /\ lastStep' = "beacon"

\* Receive the server's signed manifest for seq s
ReceiveManifest(s) ==
  /\ s > active                           \* "a manifest with fence_seq <= current is refused"
  /\ LET keep == \/ pending.kind = "real" /\ pending.seq >= s
                 \/ HigherSeqAlwaysWins /\ pending.kind = "hint" /\ pending.seq >= s
     IN /\ pending' = IF keep THEN pending ELSE [kind |-> "real", seq |-> s]
        /\ refused' = (refused \/ (keep /\ pending.kind = "hint"))
  /\ UNCHANGED active
  /\ prevActive' = active /\ lastStep' = "manifest"

\* Every fragment arrived and matched the signed manifest's hashes: activate
FragmentsArrive ==
  /\ pending.kind = "real"
  /\ active' = pending.seq
  /\ pending' = None
  /\ UNCHANGED refused
  /\ prevActive' = active /\ lastStep' = "activate"

Done ==
  /\ active = ServerSeq /\ pending.kind # "real"
  /\ UNCHANGED vars

Next ==
  \/ \E s \in 1..MaxSeq : HearBeacon(s)
  \/ \E s \in 1..ServerSeq : ReceiveManifest(s)
  \/ FragmentsArrive
  \/ Done

Spec == Init /\ [][Next]_vars

HintNeverOutranksManifest == ~refused
ActiveIsSigned == active <= ServerSeq
NoRollback == active >= prevActive
=============================================================================
