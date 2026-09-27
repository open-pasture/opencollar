"""Write the carrier's test-pad and hole positions to tp.json, for the fixture pictures
(and later, the probe plate's drill file).

    kicad-python docs/images/test-fixture/export_pads.py \
        hardware/carrier/build/carrier.kicad_pcb docs/images/test-fixture/tp.json

Positions are board-local mm: origin top-left, x right, y down (layout.py's frame).
"""
import json
import sys

import pcbnew

src, dst = sys.argv[1:3]
board = pcbnew.LoadBoard(src)
ORIGIN = 100.0                      # layout.py puts the board's corner at (100, 100) mm
out = {"board": [65.0, 58.5], "tps": [], "holes": []}
for f in board.GetFootprints():
    ref, pos = f.GetReference(), f.GetPosition()
    x, y = round(pcbnew.ToMM(pos.x) - ORIGIN, 2), round(pcbnew.ToMM(pos.y) - ORIGIN, 2)
    if ref.startswith("TP"):
        out["tps"].append({"ref": ref, "net": f.GetValue(), "x": x, "y": y})
    elif ref.startswith("H"):
        drills = [pcbnew.ToMM(p.GetDrillSize().x) for p in f.Pads()]
        out["holes"].append({"ref": ref, "x": x, "y": y, "d": drills[0] if drills else 0})
json.dump(out, open(dst, "w"), indent=1)
print(f"{len(out['tps'])} test pads, {len(out['holes'])} holes -> {dst}")
