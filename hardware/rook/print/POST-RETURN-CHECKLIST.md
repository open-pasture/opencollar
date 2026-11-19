# Post-return printer checklist (printing paused since Nov 17, 2026)

Printing is paused per Cody (7:08 AM CT Nov 17). Nothing below runs until he is back and lifts the pause himself.

1. **Bed clean-up.** Pull the two infinity cubes (#12) and whatever is left of turtles try 2 (#14). Scrape off any stuck PLA and wipe the Textured PEI plate with IPA. Photograph the failed turtles first, if any are left, to find the cause.
2. **Re-enable checks.** The kid plates had foreign-object detection (M972) removed and ABL off, as one-off files only. Before the next print:
   - Use stock `lan_p2s.py`, not the keep-out variant. The stock one sends bed leveling, flow, vibration and layer inspect True.
   - Confirm the printer's AI/foreign-object detection settings are on.
   - Never reuse `*_aroundcubes*` or `*_noFOD*` files.
3. **Bars #11 dry-fit.** Fit the 4 PETG clamp bars, spacers and shims on the 44.45–49 mm strap: removable, tightens and loosens, no cracking. Log the result in PRINT-HISTORY.
4. **Route check.** Mac online, `ssh garage` works, and `lan_p2s.py check` passes with Developer Mode on. Optional: a bot route to garage over Tailscale.
5. **AMS.** Confirm A2 PETG and A4 PLA levels. A1 PLA is unknown; don't use it.
6. **Next print** needs Cody's Blender + in-person review and a typed go naming plate and sha.
