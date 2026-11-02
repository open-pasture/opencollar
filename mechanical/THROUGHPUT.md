# Node V1 print throughput (Bambu P2S) — op-maker, 2026-11-02

All times below are **measured**: real Orca 2.4.2 CLI slice estimates (gcode header "total estimated time")
from the repo profiles (`print/p2s_pla`, `print/p2s_asa`), unless marked **(est.)**. Slicer estimates leave out
real-world start overhead (heat, level, purge) and usually run a few % low. The baseline re-slice matched print #2
(3h32m vs 3h31m56s, 103 layers, 93.15 g). Scratch slices are in the box's /workspace/tp/runs (not in the repo).

**Correction:** the PLA fit profile is **3 walls, 15 % crosshatch, 5 top / 3 bottom, tree supports**, not 6/40 %.
6 walls / 40 % gyroid / 6+6 shells is the **ASA** profile (the real-parts spec in parts/node_v1.py).

## Where the time goes (cap plate = base + lid + 2 bars, PLA 0.4 mm, 0.20 mm)
| Part | Bbox mm | Vol cm³ | PLA alone | ASA alone |
|---|---|---|---|---|
| cap base | 62x142x20.5 | 66.5 | 2h33m / 59.6 g | 3h11m |
| cap lid | 62x142x7 | 53.3 | 0h60m / 29.2 g | 1h44m |
| clamp bar (all 3 types the same) | 10x70x4 | 2.5 | 0h17m / 2.2 g | 0h19m |
| cw tub | 88x74x30 | 82.3 | 1h32m / 49.1 g | 2h22m |
| cw lid | 88x74x6 | 23.8 | 0h43m | 0h54m |
| pod base (x2 per node) | 92x68x24.5 | 48.4 | 1h26m | 1h38m |
| pod lid (x2) | 92x68x6 | 21.9 | 0h42m | 0h51m |
Two limits stand out: **max volumetric flow** (the filament profile is Generic PLA at 12 mm³/s, so faster speed
settings change nothing) and **tree supports** under the cap base's spine relief (~48 min).

## Levers, measured on the cap plate (PLA baseline 3h32m, ASA baseline 4h58m)
| # | Change | PLA time (Δ) | ASA time (Δ) | Strength / quality tradeoff | Risk |
|---|---|---|---|---|---|
| 1 | Supports off (design change below) | 2h44m (−48m, −22 %) | — | none if the relief is redesigned to self-support | low |
| 1b | Tree → normal supports | 2h59m (−33m) | — | harder to clean up; more scarring | low |
| 2 | Real PLA flow limit 21 mm³/s (Bambu PLA Basic preset) | 3h16m (−16m) | n/a (18 already) | none; use the matching filament | low |
| 3 | 0.28 mm layers | 3h21m (−12m); 2h56m with #2 | 4h08m (−50m, −17 %) | coarser steps on the lid edges; layer bond about the same | low |
| 4 | 0.6 mm nozzle, 0.30 mm layers, 0.62 lines | 2h59m (−34m); **2h19m with #2** | **3h07m (−1h51m, −37 %)** | thicker walls = stronger; loses fine detail (O-ring groove and insert holes need a fit check); +25 g | med |
| 5 | Infill 15 → 10 % gyroid (PLA) | 3h27m (−5m) | — | negligible for fit prints | low |
| 5b | ASA infill 40 → 25 % | — | 4h27m (−31m) | lower crush strength; keep 100 % around bosses | med |
| 6 | Walls 3 → 2 (PLA) / 6 → 4 (ASA) | 3h21m (−10m) | 5h00m (+2m, no gain) | ASA: no time saved; keep 6 walls | — |
| 7 | Top/bottom 5/3 → 4/2 (PLA) | 3h27m (−5m) | — | thinner floor, possible pillowing | low |
| 8 | Accel 10k → 5k (check only) | 3h58m (+26m) | — | keep 10k; accel is not the limit | — |
| 9 | Combined PLA: 21 flow + 0.28 + no supports + 10 % gyroid | **2h15m (−1h17m, −36 %)** | — | fine for fit checks | low |
| 9b | Combined ASA: 0.28 + 4 walls + 25 % | — | 3h45m (−1h13m) | weaker; prefer #4 | med |
ASA prints slower even at higher flow (12 s minimum layer time, closed chamber, less fan to avoid warping), so its
gains come from **layer height and nozzle size**, not speed. Keep the door closed and the bed at ~90-100 °C, and do
not raise ASA speeds (est.: warping risk on the 142 mm cap base).

## Batching (256x256x256 mm plate)
- The cap plate already batches 4 parts: **3h32m vs 4h06m printed one by one** (−34m, measured).
- **Full node** (cap set + cw set + 2 pods with 4 bars; Orca auto-arranged it onto 3 plates):
  PLA 3h26m + 3h02m + 3h17m = **9h45m** vs **12h16m** for each part printed separately (sum of single-part slices);
  ASA 4h51m + 4h23m + 3h51m = **13h05m**. Each plate you avoid also saves the start routine (~5-8 min per plate (est.)).
- Footprint check: four cap bases (62 mm wide) fit side by side across 256 mm. Two cap sets went to 2 plates
  (5h43m + 1h22m = 7h05m vs 7h04m for two single cap plates). So batching pays when parts **fill the plate
  height-matched** (group tall parts together, flat lids and bars together); otherwise the tallest part sets the time.
- Single filament, no AMS colour changes, so no purge or prime tower. Keep it that way (est.: each colour swap costs
  roughly 1-2 min and a few grams).

## Part design changes (parts/node_v1.py), none weakens the clamp or the field repair path
1. **Cap spine relief (28x5 mm underside): add a 45° chamfer or a teardrop roof** so the base prints with no
   supports. Saves −48m per cap (measured with supports off), stops the support scarring seen on print #1, and cuts cleanup.
2. **Cap lid is 7 mm solid (53 cm³, nearly the base's volume).** Make it 3 mm with perimeter and cross ribs (keep
   the 1.2 mm panel pockets and the 4 mm wire holes). (est.) −30-40 % lid time (about −20m PLA, −35m ASA) and ~−25 g.
   Check stiffness by hand on the screw line.
3. **CAP_FLOOR_Z 7.5 mm solid under the cavity:** core it out between the strap channel and the insert bosses (keep
   ≥2.5 mm around each M3 insert, ≥1.6 mm under the channel). (est.) −10-15 % base material.
4. **Walls 5.0 mm (CAP_WALL, POD_WALL):** fine with 0.6 nozzle (8 lines); don't thin them (sealing, drop impact).
5. **Clamp bars:** all three types are the same 10x70x4 bar. Make one shared part and print 8 at a time on one
   flat plate (≈ 8 x 17m single ≈ 2h16m serial; batched (est.) ~1h20m). Fewer SKUs for farmers.
6. **Don't combine lid and base into one print:** a separate lid is what makes the part field-repairable.

## Workflow overhead between prints (est., not slicer data)
| Item | Now | Faster | Saves |
|---|---|---|---|
| File transfer / start | Bambu Connect on Cody's Mac; no SD card means no LAN upload | microSD in printer + LAN FTPS/MQTT start from a script; or keep Bambu Connect and import the file | ~5-30 min of fiddling per job |
| op-maker start routine | ~2 min once the route works | keep the runbook (PRINTING.md) | — |
| Bed level + flow cal | Auto both | bed level Auto (keep); turn flow cal off for known PLA (est. −2-4 min) | ~3 min |
| Cool-down / plate swap | the plate has to cool before the PEI releases parts | 2 PEI plates, swap hot, flex off later | ~10-15 min |
| Queueing | one job, wait for Cody | slice whole-node plate sets ahead; Cody swaps the plate, I start the next | hours idle |

## Ranked top changes
1. **Batch a whole node onto 3 height-matched plates:** −2h31m PLA per node (12h16m → 9h45m), measured.
2. **Remove the cap supports (chamfer the spine relief):** −48m per cap, measured with supports off; better surfaces.
3. **0.6 mm nozzle at 0.30 mm for ASA production:** −37 % (4h58m → 3h07m per cap plate), measured; keeps 6 walls.
4. **Correct the PLA flow (21 mm³/s Bambu PLA) + 0.28 mm for fit prints:** −36m (3h32m → 2h56m); with #2 and
   10 % gyroid 2h15m (−36 %).
5. **Workflow:** microSD + a second PEI plate + pre-sliced queue (est. 15-45 min per job saved, more in idle time).
Skip: higher accel (not the limit), fewer ASA walls (no time saved), merging lid and base (hurts repairability).

## Test plan (PLA first, then ASA)
1. **T1 (PLA, ~2h15m):** cap plate with flow 21 + 0.28 + 10 % gyroid, supports off **after** the relief chamfer CAD
   change. Check: relief face quality, O-ring groove depth, insert hole diameter (calipers vs nominal), lid seat.
2. **T2 (PLA, ~2h20m):** the same on a 0.6 nozzle (needs a $10-20 nozzle, Cody's purchase). Same fit checks + heat-set
   one M3 insert in each boss type.
3. **T3 (ASA, ~3h07m):** 0.6 / 0.30 / 6 walls / 40 % cap set, enclosure closed. Check warp (corners flat on glass
   ≤0.3 mm), then the strength tests against a 0.4 mm / 0.20 mm ASA control:
   - clamp-bar screw torque to strip/crack (M3 into insert, small torque driver, record N·m; target ≥ control);
   - insert pull-out (hang weight or luggage scale from an M3 eyebolt; record kg at failure);
   - drop test: assembled cap with ~120 g dummy mass, 1.5 m onto concrete, 5 drops on each face; inspect
     the bosses and lid seal;
   - strap clamp hold: pull the strap by hand/scale with the bars torqued; no slip at the target load.
4. **T4:** full-node 3-plate batch at the winning settings; log the real wall-clock time per plate vs these estimates in PRINT-HISTORY.md.
Pass = fits, matches or beats the control on torque/pull-out, no drop cracks. Then make it the default profile.
