# How to start a print fast (Bambu P2S "Openpasture-1")

Last verified: 2026-11-02 (print #2, the Node V1 cap). Total hands-on time once the route is known: about 2 minutes.

## The working route (use this first)

Bambu Connect on the owner's Mac, which is already signed in and shows the printer. Needs the Mac on and awake.

1. Find the sliced file in the repo (see "Where files live"). It must be a `.gcode.3mf` that already contains `Metadata/plate_1.gcode`. Do not re-slice just to print again.
2. Open it in Bambu Connect with the deep link (URL-encode the full path):
   `open "bambu-connect://import-file?path=<url-encoded path>&name=<job name>&version=1.0.0"`
3. In Bambu Connect click **Import Gcode 3MF**, then **Print** (top right), then **Send** in the "Send to print" box. Check the printer name and that the filament maps to the right AMS slot (PLA to the PLA slot).
4. The printer shows "Downloading", then "Homing toolhead, 0/N layers". That is the confirmation it started.
5. Log it in `mechanical/PRINT-HISTORY.md` (file, material, layers, estimated time, route).

Driving the Mac from an assistant needs macOS Accessibility permission for the assistant app (System Settings > Privacy & Security > Accessibility). Menu-style scripting clicks do not work in this app; use a real mouse click (a tiny Swift `CGEvent` helper compiled on the Mac), and activate the app first. Screen coordinates are global points; the Mac has a very wide screen, so take a full-width screenshot and scale coordinates.

## What failed and why (do not retry these)

- **Local upload to the printer (FTPS 990)**: login works, but every upload fails with `553` and `/cache` is refused, because the P2S reports no storage (`sdcard: false`). Local LAN printing needs a microSD card in the printer. (Python's `ssl` also hits "522 session reuse required" on the data connection; `curl --ssl-reqd` handles that, so it was not the real blocker.)
- **Cloud print from the assistant's own computer**: blocked. Outbound port 8883 (Bambu MQTT) is blocked by the sandbox network, so Orca on that computer shows "Failed to connect to the server". Not fixable there.
- **Printing from OrcaSlicer on the Mac**: Orca's printer was a custom "OpenCollar machine" preset (not a bound Bambu device), so there is no Print button, only Export. Also Orca 2.4.2 on macOS refuses to slice that preset with "Relative extruder addressing requires resetting the extruder position... add G92 E0" until `before_layer_change_gcode` contains `G92 E0`. Use the already-sliced 3mf with Bambu Connect instead.
- **Bambu Handy / Bambu Studio**: Handy is phone-only, and neither is installed on the Mac. Only OrcaSlicer and Bambu Connect are. "Print again" in Handy history works but needs the owner's phone.
- **Looking for the file by name on the Mac**: the repo's `mechanical/print/gcode/` folder is gitignored, so sliced files were not on GitHub. They are now tracked (see below).
- **macOS dialogs**: Orca shows a "Customized Preset" confirmation (click OK) and a "New version" popup (Cancel) when it opens a project.

## First-check order next time

1. Is the Mac on and connected (Bambu Connect running, printer shows Online)?
2. Printer state: finished or idle, no error, right filament loaded in the AMS. (Status can also be read over the LAN with MQTT from the Mac: `device/<serial>/report`, user `bblp`, password is the printer access code; never write the code in chat or logs.)
3. Is the file already sliced and in the repo? If yes, use the route above. If not, slice with Orca CLI or the repo scripts, commit the 3mf, then print.
4. If Bambu Connect is signed out, the owner has to sign in (Google sign-in with a phone prompt); that is the only step an assistant cannot do.

## Where files live (GitHub is the source of truth)

Repo: open-pasture/opencollar, under `mechanical/`.
- STLs: `exports/node_v1_cap`, `exports/node_v1_pod`, `exports/node_v1_cw`
- Sliced P2S PLA projects (F1 to F5, e.g. `F2_cap.gcode.3mf`): `print/sliced/p2s_pla/` (see also `print/README-print-files.md`)
- Orca profiles: `print/p2s_pla`, `print/p2s_asa`
- Scripts: `print/slice_p2s_pla.sh`, `print/fix_bbl_3mf.py`, `print/flatten_profiles.py`
- Print log: `PRINT-HISTORY.md`
- How to print: `PRINTING.md` (this file); throughput notes: `THROUGHPUT.md`

## One-time setup that makes it faster

1. **Put a microSD card in the P2S.** Then an assistant can upload and start prints over the LAN with no Mac and no app clicks, and the Mac can be off (if it still has a LAN path, i.e. a small always-on home bridge).
2. **Leave Accessibility on** for the assistant app on the Mac, and keep Bambu Connect signed in and running.
3. **Bind the P2S in Orca on the Mac** (sign in to Bambu, pick the real Bambu Lab P2S preset) so Orca has a Print button, and add `G92 E0` to the OpenCollar preset's `before_layer_change_gcode`.
4. **Allow outbound port 8883** for the assistant's computer so it can cloud-print itself.
5. **Always-on home bridge** (small Pi or mini PC on the home network) for control when the Mac is off.
