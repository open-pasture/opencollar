"""First placement of the carrier board from the netlist (rev A2, SPEC.md section 8).

    kicad-python layout.py build/carrier.net build/carrier.kicad_pcb

Board-local coordinates in mm: origin at the top-left corner, x right, y down.
Fixed parts (sockets, connectors, ICs, holes) go at the positions below, taken
from the Makerdiary drawing and the breakout board files. Passives are packed
near their block's anchor without overlapping anything. Test pads go on the
bottom. Ground pours on both layers. Routing comes later (Freerouting).
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist_to_pcb import child, sexp, val  # noqa: E402

FP_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
W, H = 95.0, 75.0
ORIGIN = (100.0, 100.0)      # where the board sits on the KiCad page
CORNER_R = 2.0
HOLE_INSET = 3.5

# Connect Kit: top edge of the Kit (USB end) at y = 6. Pins 1/40 are 3.81 mm in
# from that end, rows 17.78 mm apart [MD dimension drawing].
KIT_X, KIT_TOP = 5.5, 6.0
KIT_ROW = 17.78
KIT_PIN1_Y = KIT_TOP + 3.81

# Breakouts: (left x, bottom y) of the board outline, Eagle coordinates are
# measured from the bottom-left corner with y up [SF board files].
M10S = (54.5, 38.48)          # 38.10 x 30.48
IMU = (27.0, 38.0)            # 25.40 x 17.78


def eagle(origin, ex, ey):
    return origin[0] + ex, origin[1] - ey


FIXED = {
    # ref: (x, y, rotation deg, side). Sockets' origin is the middle of the row.
    "J1": (KIT_X, KIT_PIN1_Y + 11.43, 0, "F"),                 # Kit 1-10
    "J2": (KIT_X, KIT_PIN1_Y + 25.4 + 11.43, 0, "F"),          # Kit 11-20
    "J3": (KIT_X + KIT_ROW, KIT_PIN1_Y + 11.43, 0, "F"),       # Kit 40-31
    "J4": (KIT_X + KIT_ROW, KIT_PIN1_Y + 25.4 + 11.43, 0, "F"),  # Kit 30-21
    "J5": (KIT_X + KIT_ROW / 2 + 1.27, KIT_TOP + 6.0, 90, "F"),  # under the Kit's J2 socket
    "J10": (eagle(M10S, 1.27, 24.13)[0], eagle(M10S, 1.27, 24.13)[1] + 8.89, 0, "F"),
    "J11": ((eagle(M10S, 22.86, 29.21)[0] + eagle(M10S, 15.24, 29.21)[0]) / 2,
            eagle(M10S, 0, 29.21)[1], -90, "F"),
    "J12": ((eagle(IMU, 2.54, 2.54)[0] + eagle(IMU, 22.86, 2.54)[0]) / 2,
            eagle(IMU, 0, 2.54)[1], 90, "F"),
    "J9": (62.0, 3.8, 180, "F"),                                # spare Qwiic, top edge
    "J16": (30.0, 3.5, 90, "F"),                                # EXP header, top edge
    "J13": (34.0, 71.4, 0, "F"),                                # cue L, bottom edge
    "J14": (43.0, 71.4, 0, "F"),                                # cue R
    "J15": (61.5, 71.0, 0, "F"),                                # harness M8 8-pin
    "J7": (79.5, 69.6, 0, "F"),                                 # bench battery
    "J6": (89.6, 46.0, 90, "F"),                                # panels A/GND/B, right edge
    "J8": (89.6, 58.0, 90, "F"),                                # bench NTC
    "U1": (78.0, 53.0, 0, "F"),                                 # bq24074
    "D1": (82.0, 43.0, 0, "F"),
    "D2": (82.0, 48.5, 0, "F"),
    "U2": (36.0, 50.0, 0, "F"),                                 # TCA4307
    "U3": (46.0, 50.0, 0, "F"),                                 # TPS2553
    "U4": (38.5, 63.5, 0, "F"),                                 # ESD, EXT bus
    "U5": (61.5, 63.5, 0, "F"),                                 # ESD, harness TS/INT
    "H1": (HOLE_INSET, HOLE_INSET, 0, "F"),
    "H2": (W - HOLE_INSET, HOLE_INSET, 0, "F"),
    "H3": (HOLE_INSET, H - HOLE_INSET, 0, "F"),
    "H4": (W - HOLE_INSET, H - HOLE_INSET, 0, "F"),
}
for i, (ex, ey) in enumerate([(35.56, 2.54), (35.56, 27.94)]):   # away from the 8-pin row
    x, y = eagle(M10S, ex, ey)
    FIXED[f"H{5 + i}"] = (x, y, 0, "F")
for i, (ex, ey) in enumerate([(2.54, 15.24), (22.86, 15.24)]):
    x, y = eagle(IMU, ex, ey)
    FIXED[f"H{7 + i}"] = (x, y, 0, "F")

# Where each block's loose parts (passives) go: anchor point they cluster
# around, and the rectangle they must stay inside.
REGIONS = {
    "charger": ((78.0, 52.0), (64.0, 40.0, 87.0, 66.0)),
    "solar_inputs": ((83.0, 50.0), (64.0, 40.0, 87.0, 66.0)),
    "sensing": ((30.0, 55.0), (26.5, 40.0, 34.0, 67.0)),
    "main_i2c": ((36.0, 45.0), (30.0, 40.5, 56.0, 60.0)),
    "external_bus": ((41.0, 50.0), (30.0, 40.5, 56.0, 60.0)),
    "harness_port": ((56.0, 63.0), (50.0, 56.0, 72.0, 66.0)),
    "esd": ((50.0, 63.0), (30.0, 60.0, 72.0, 66.5)),
}

# Top silkscreen labels: (text, x, y).
LABELS = [   # connectors labelled here have their own reference hidden
    ("KIT USB", 14.4, 7.6),
    ("J5 KIT BAT", 16.9, 15.0),
    ("J16 EXP 3V3 GND P0-P4 A3-A5", 41.5, 6.2),
    ("J9 QWIIC", 69.5, 4.0),
    ("M10S", 58.9, 13.2),
    ("IMU ISM330", 39.7, 31.2),
    ("J13 CUE L", 34.0, 67.0),
    ("J14 CUE R", 43.0, 67.0),
    ("J15 HARNESS", 55.0, 65.6),
    ("J7 BAT bench, pin 1 = +", 79.5, 63.6),
    ("J6 PANELS A+ GND B+", 84.0, 39.0),
    ("J8 NTC bench", 86.0, 52.3),
]
LABELLED = {"J5", "J6", "J7", "J8", "J9", "J13", "J14", "J15", "J16"}

# Test pads: bottom side, 3 mm grid, grouped as in SPEC.md section 7.
TP_GRID = (31.0, 43.0, 5.0, 3.6, 8)    # x0, y0, dx, dy, columns
TP_LABEL = {   # bottom silkscreen, <= 5 characters; legend in SPEC.md section 7
    "CHG_OUT": "COUT", "CHG_IN": "CIN", "SOLAR_A": "SOLA", "SOLAR_B": "SOLB", "EXT_3V3": "X3V3",
    "KIT_VBUS": "VBUS", "KIT_VSYS": "VSYS", "RESET": "RST", "UART_TX": "TX", "UART_RX": "RX",
    "KIT_EN": "KEN", "I2C_SDA": "SDA", "I2C_SCL": "SCL", "EXT_SDA": "XSDA", "EXT_SCL": "XSCL",
    "EXT_EN": "XEN", "EXT_INT": "XINT", "CHG_STAT": "CHG", "CHG_PGOOD": "PG", "CHG_CE": "CE",
    "GNSS_SAFEBOOT": "SAFE", "GNSS_RESET_N": "GRST", "GNSS_PPS": "PPS"}


def mm(v):
    return pcbnew.FromMM(v)


def at(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))


def parse_netlist(path):
    root = sexp(open(path).read())
    comps = []
    for c in child(root, "components")[1:]:
        if not (isinstance(c, list) and c[0] == "comp"):
            continue
        fields = {}
        fl = child(c, "fields")
        if fl:
            for f in fl[1:]:
                if isinstance(f, list) and f[0] == "field":
                    fields[val(f, "name")] = f[-1] if isinstance(f[-1], str) else ""
        comps.append(dict(ref=val(c, "ref"), value=val(c, "value"), fp=val(c, "footprint"), fields=fields))
    nets = []
    for n in child(root, "nets")[1:]:
        if isinstance(n, list) and n[0] == "net":
            nodes = [(val(x, "ref"), val(x, "pin")) for x in n[1:] if isinstance(x, list) and x[0] == "node"]
            nets.append((val(n, "name"), nodes))
    return comps, nets


def bbox_mm(fp, margin=0.25):
    """Courtyard bounding box in board-local mm, with a margin."""
    try:
        b = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd).BBox()
        if b.GetWidth() == 0:
            raise ValueError
    except Exception:
        b = fp.GetBoundingBox(False)
    x0 = pcbnew.ToMM(b.GetX()) - ORIGIN[0] - margin
    y0 = pcbnew.ToMM(b.GetY()) - ORIGIN[1] - margin
    return (x0, y0, x0 + pcbnew.ToMM(b.GetWidth()) + 2 * margin, y0 + pcbnew.ToMM(b.GetHeight()) + 2 * margin)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def place(fp, x, y, rot=0, side="F"):
    fp.SetPosition(at(x, y))
    fp.SetOrientationDegrees(rot)
    if side == "B" and not fp.IsFlipped():
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)


def pack(fp, anchor, region, taken):
    """Put fp at the free spot nearest the anchor inside region."""
    rx0, ry0, rx1, ry1 = region
    spots = []
    step = 0.5
    y = ry0
    while y <= ry1:
        x = rx0
        while x <= rx1:
            spots.append((math.hypot(x - anchor[0], y - anchor[1]), x, y))
            x += step
        y += step
    spots.sort()
    for rot in (0, 90):
        for _, x, y in spots:
            place(fp, x, y, rot)
            bb = bbox_mm(fp, margin=0.45)   # room for silkscreen between passives
            if bb[0] < rx0 or bb[1] < ry0 or bb[2] > rx1 or bb[3] > ry1:
                continue
            if not any(overlaps(bb, t) for t in taken):
                taken.append(bb)
                return True
    return False


def outline(board):
    pts = [(CORNER_R, 0), (W - CORNER_R, 0), (W, CORNER_R), (W, H - CORNER_R),
           (W - CORNER_R, H), (CORNER_R, H), (0, H - CORNER_R), (0, CORNER_R)]
    for (x0, y0), (x1, y1) in [(pts[0], pts[1]), (pts[2], pts[3]), (pts[4], pts[5]), (pts[6], pts[7])]:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(at(x0, y0)); s.SetEnd(at(x1, y1))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    c = CORNER_R * (1 - 1 / math.sqrt(2))
    for (sx, sy), (mx, my), (ex, ey) in [
        ((0, CORNER_R), (c, c), (CORNER_R, 0)),
        ((W - CORNER_R, 0), (W - c, c), (W, CORNER_R)),
        ((W, H - CORNER_R), (W - c, H - c), (W - CORNER_R, H)),
        ((CORNER_R, H), (c, H - c), (0, H - CORNER_R))]:
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetArcGeometry(at(sx, sy), at(mx, my), at(ex, ey))
        a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(mm(0.1))
        board.Add(a)


def gnd_pour(board, net, layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # solid to SMD pads, reliefs on hand-soldered holes
    o = z.Outline()
    o.NewOutline()
    for x, y in [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]:
        o.Append(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))
    board.Add(z)


def text(board, s, x, y, size=1.0, layer=pcbnew.F_SilkS, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(at(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    if mirror:
        t.SetMirrored(True)
    board.Add(t)


def rules(board):
    """JLCPCB 2-layer standard process, with margin: 0.15 mm clearance and track,
    0.3 mm via drill / 0.6 mm via, 0.3 mm min hole."""
    ds = board.GetDesignSettings()
    ds.m_MinClearance = mm(0.15)
    ds.m_TrackMinWidth = mm(0.15)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.3)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(mm(0.15))
    nc.SetTrackWidth(mm(0.25))
    nc.SetViaDiameter(mm(0.6))
    nc.SetViaDrill(mm(0.3))


def thermal_vias(board, fp, net, pitch=0.9):
    """Four 0.3/0.6 mm vias in an exposed pad, to the bottom ground pour [BQ] 12.1."""
    c = fp.GetPosition()
    for dx in (-pitch / 2, pitch / 2):
        for dy in (-pitch / 2, pitch / 2):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(c.x + mm(dx), c.y + mm(dy)))
            v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
            v.SetNet(net)
            board.Add(v)


def main(src, dst):
    comps, nets = parse_netlist(src)
    board = pcbnew.BOARD()
    rules(board)
    fps, taken, loose = {}, [], []
    for c in comps:
        lib, name = c["fp"].split(":")
        f = pcbnew.FootprintLoad(os.path.join(FP_DIR, lib + ".pretty"), name)
        f.SetReference(c["ref"])
        f.SetValue(c["value"])
        for k in ("LCSC", "MPN"):
            if k in c["fields"]:
                f.SetField(k, c["fields"][k])
                f.GetField(k).SetVisible(False)   # BOM data, not silkscreen
        if c["fields"].get("DNP") == "1":
            f.SetDNP(True)
            f.SetAttributes(f.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        if c["ref"][0] in "RCH" or c["ref"].startswith("TP") or c["ref"] in LABELLED:
            f.Reference().SetVisible(False)
        else:
            f.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
            f.Reference().SetTextThickness(mm(0.12))
        board.Add(f)
        fps[c["ref"]] = (f, c)

    # Fixed parts first.
    for ref, (x, y, rot, side) in FIXED.items():
        f = fps[ref][0]
        place(f, x, y, rot, side)
        taken.append(bbox_mm(f))

    # Test pads on the bottom, in the order they were declared.
    tps = [r for r, (f, c) in fps.items() if c["fields"].get("block") == "test_pads"]
    tps.sort(key=lambda r: int(r[2:]))
    x0, y0, dx, dy, cols = TP_GRID
    for i, ref in enumerate(tps):
        f, c = fps[ref]
        x, y = x0 + dx * (i % cols), y0 + dy * (i // cols)
        place(f, x, y, 0, "B")
        f.Reference().SetVisible(False)
        text(board, TP_LABEL.get(c["value"], c["value"]), x, y + 1.6,
             size=0.8, layer=pcbnew.B_SilkS, mirror=True)

    # Loose parts: pack near their block anchor.
    for ref, (f, c) in fps.items():
        if ref in FIXED or c["fields"].get("block") == "test_pads":
            continue
        loose.append((c["fields"].get("block", ""), ref))
    failed = []
    for blk, ref in sorted(loose, key=lambda t: (t[0], len(t[1]), t[1])):
        anchor, region = REGIONS.get(blk, ((47.5, 37.5), (0, 0, W, H)))
        if not pack(fps[ref][0], anchor, region, taken):
            failed.append(ref)
    if failed:
        print("could not place:", failed)

    # Nets.
    netinfo = {}
    for name, nodes in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
        for ref, pin in nodes:
            for pad in fps[ref][0].Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(ni)

    thermal_vias(board, fps["U1"][0], netinfo["GND"])
    outline(board)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        gnd_pour(board, netinfo["GND"], layer)
    # Top: title in the clear area under the MAX-M10S, and a label at every connector.
    text(board, "OpenCollar carrier rev A2", 74.0, 20.0, 1.2)
    text(board, "CERN-OHL-P  2026-09-26", 74.0, 22.2, 0.8)
    for s_, x, y in LABELS:
        text(board, s_, x, y, 0.8)
    # Polarity marks from the real pad positions, so they can't drift from the pads.
    for ref, marks in (("J5", {"1": "+", "2": "-"}),):
        for pad in fps[ref][0].Pads():
            if pad.GetNumber() in marks:
                px = pcbnew.ToMM(pad.GetPosition().x) - ORIGIN[0]
                py = pcbnew.ToMM(pad.GetPosition().y) - ORIGIN[1]
                text(board, marks[pad.GetNumber()], px, py - 1.9, 1.0)
    # Bottom: test-pad title, harness pinout, bench warning.
    text(board, "OpenCollar carrier rev A2 - test pads", 47.5, 39.5, 0.8, pcbnew.B_SilkS, mirror=True)
    text(board, "HARNESS M8: 1 SDA 2 BAT+ 3 GND 4 SCL", 61.5, 64.0, 0.8, pcbnew.B_SilkS, mirror=True)
    text(board, "5 NTC 6 INT 7 GND 8 BAT+", 61.5, 65.3, 0.8, pcbnew.B_SilkS, mirror=True)
    text(board, "J7 BENCH BATTERY: NEVER WITH A HARNESS PACK", 47.5, 68.5, 0.8, pcbnew.B_SilkS, mirror=True)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(dst)
    print(f"{len(fps)} footprints, {len(nets)} nets -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
