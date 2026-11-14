# AMS mapping: overnight_petg_A3_d4 (Sat Nov 14 2026, ~1:10 AM CT)

Live AMS (parent relay, 11:44 PM CT Nov 13): A1 = PLA (Cody is out of PLA, so never use it). A2 = PETG grey #7F7E83 (tray index 1). A3 = ASA. A4 = empty.

## What the 3MF stores (read back from the file)
- Metadata/slice_info.config: `<filament id="1" tray_info_idx="GFG99" type="PETG" color="#7F7E83" used_g="150.00" used_for_support="false">`, `filament_maps="1"`, `support_used="false"`, `printer_model_id="N7"`, no `<warning>`.
- Metadata/project_settings.config: filament_type ["PETG"], filament_colour ["#7F7E83"], filament_settings_id "OpenCollar filament (Generic PETG @BBL P2S) bed65", filament_map ["1"], curr_bed_type "Textured PEI Plate", textured_plate_temp ["65"].
- **The Bambu 3MF has no AMS-tray field.** `filament_maps=1` is the extruder (single nozzle), not a tray. The tray is chosen at send time.

## Required at send
- Map filament 1 (PETG grey) to **A2 / PETG** only. Nothing on A1, A3 or A4.
- **AMS auto-refill/backup OFF** (on #10 the backup switched A1 to A4); it must not fall back to A1 PLA.
- LAN/MQTT equivalent (reference only): `ams_mapping [1,-1,-1,-1,-1]` (filament 1 → tray index 1 = A2), `use_ams true`.
- sha256 at send must be **5dec437a8c36697ca29997d16ea8a7fedda2c6c90499c2fd2f2d974d48e0ac0c**.
