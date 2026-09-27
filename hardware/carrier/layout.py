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
W, H = 65.0, 58.5
ORIGIN = (100.0, 100.0)      # where the board sits on the KiCad page
CORNER_R = 2.0

# The board is the three plugged boards tiled edge to edge, with every carrier
# part underneath them (they sit ~11 mm up on 8.5 mm sockets):
#   Kit down the left edge, MAX-M10S top right, ISM330 below it.

# Connect Kit: USB end at the top edge. Pins 1/40 are 3.81 mm in from that end,
# rows 17.78 mm apart [MD dimension drawing]. The left row sits just far enough
# in for its SMD socket pads.
KIT_X, KIT_TOP = 3.5, 0.5
KIT_ROW = 17.78
KIT_PIN1_Y = KIT_TOP + 3.81
KIT_MID = KIT_X + KIT_ROW / 2          # centre line between the rows, under the Kit

# Breakouts, from their board files [SF]. Eagle coordinates run from the board's
# bottom-left corner with y up.
M10S_TL = (26.5, 2.5)                   # 38.10 x 30.48; its 8-pin row can't sit closer to the Kit's socket
IMU_TL = (26.5, 33.5)                   # 25.40 x 17.78, turned 180 deg: pin row on top


def m10s(ex, ey):
    return M10S_TL[0] + ex, M10S_TL[1] + 30.48 - ey


def imu(ex, ey):
    """ISM330 board point after the 180 deg turn."""
    return IMU_TL[0] + 25.40 - ex, IMU_TL[1] + ey


FIXED = {
    # ref: (x, y, rotation deg, side). Sockets' origin is the middle of the row.
    "J1": (KIT_X, KIT_PIN1_Y + 11.43, 0, "F"),                   # Kit 1-10
    "J2": (KIT_X, KIT_PIN1_Y + 25.4 + 11.43, 0, "F"),            # Kit 11-20
    "J3": (KIT_X + KIT_ROW, KIT_PIN1_Y + 11.43, 0, "F"),         # Kit 40-31
    "J4": (KIT_X + KIT_ROW, KIT_PIN1_Y + 25.4 + 11.43, 0, "F"),  # Kit 30-21
    "J5": (KIT_MID - 1.27, 8.0, 90, "F"),                        # under the Kit's own J2 socket
    "J8": (m10s(1.27, 0)[0], m10s(0, 24.13)[1] + 8.89, 0, "F"),  # M10S 8-pin row
    "J9": (M10S_TL[0] + (22.86 + 15.24) / 2, m10s(0, 29.21)[1], -90, "F"),   # M10S 4-pin row
    "J10": (IMU_TL[0] + 25.40 - (2.54 + 22.86) / 2, imu(0, 2.54)[1], -90, "F"),  # IMU 9-pin row
    "J7": (35.5, 3.3, 180, "F"),                                 # spare Qwiic, top edge, under the M10S
    "J11": (29.6, H - 3.4, 0, "F"),                              # cue L, bottom edge
    "J12": (38.0, H - 3.4, 0, "F"),                              # cue R
    "J6": (46.0, H - 3.4, 0, "F"),                               # panels, bottom edge
    "J13": (W - 5.2, 46.2, 90, "F"),                             # harness M8 8-pin, right edge beside the IMU
    "U1": (52.0, 19.0, 0, "F"),                                  # bq24074, under the M10S
    "D1": (48.0, 29.0, 0, "F"),
    "D2": (54.0, 29.0, 0, "F"),
    "U2": (KIT_MID, 16.0, 0, "F"),                               # TCA4307, under the Kit
    "U3": (KIT_MID, 33.0, 0, "F"),                               # TPS2553, under the Kit
    "U4": (33.5, 45.0, 0, "F"),                                  # ESD, cue ports, under the IMU
    "U5": (44.0, 45.0, 0, "F"),                                  # ESD, harness TS/INT
    "H1": (KIT_MID, 24.5, 0, "F"),                               # board mounts under the Kit
    "H2": (KIT_MID, 47.0, 0, "F"),
    "H3": m10s(35.56, 27.94) + (0, "F"),                         # M10S standoffs, also board mounts
    "H4": m10s(35.56, 2.54) + (0, "F"),
    "H5": imu(2.54, 15.24) + (0, "F"),                           # IMU standoffs (M2)
    "H6": imu(22.86, 15.24) + (0, "F"),
}

# Where each block's loose parts (passives) go: an anchor they cluster around,
# and the rectangle they stay inside.
UNDER_KIT = (7.0, 2.5, 17.8, H - 1.0)
SPILL = (31.5, 7.0, 46.0, 30.5)          # free board under the M10S's left half, for overflow
REGIONS = {
    "charger": ((52.0, 19.0), (32.0, 7.0, 58.0, 30.5)),
    "solar_inputs": ((51.0, 29.0), (32.0, 7.0, 58.0, 30.5)),
    "sensing": ((KIT_MID, 53.0), UNDER_KIT),
    "main_i2c": ((KIT_MID, 20.0), UNDER_KIT),
    "external_bus": ((KIT_MID, 24.0), UNDER_KIT),
    "harness_port": ((44.0, 42.0), (30.5, 40.0, 51.5, 51.0)),
    "esd": ((38.0, 45.0), (30.5, 40.0, 51.5, 51.0)),
}

# Top silkscreen labels: (text, x, y). Connectors listed in LABELLED have their
# own reference hidden, because the label carries it.
LABELS = [
    ("KIT USB", KIT_MID, 2.0),
    ("J5 KIT BAT", KIT_MID, 10.9),
    ("J7 QWIIC", 35.5, 7.6),
    ("J11 CUE L", 29.6, H - 7.9),
    ("J12 CUE R", 38.0, H - 7.9),
    ("J6 A+ G B+", 46.6, H - 7.9),
    ("J13 HARNESS", W - 5.6, 34.8),
]
LABELLED = {"J5", "J6", "J7", "J11", "J12", "J13"}
FAB_REF = {"U2"}   # reference on the fab layer only: it sits under the Kit, next to C-parts

# Test pads: bottom side, 5 x 3.6 mm grid, grouped as in SPEC.md section 7.
TP_GRID = (21.0, 9.5, 5.0, 3.6, 8)     # x0, y0, dx, dy, columns
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


PLUGGED = [   # outlines of the boards that plug in, for the assembled preview only
    ("Connect Kit", (KIT_X - 1.27, KIT_TOP, KIT_X - 1.27 + 20.32, KIT_TOP + 55.88)),
    ("MAX-M10S", (M10S_TL[0], M10S_TL[1], M10S_TL[0] + 38.10, M10S_TL[1] + 30.48)),
    ("ISM330", (IMU_TL[0], IMU_TL[1], IMU_TL[0] + 25.40, IMU_TL[1] + 17.78)),
]


def assembled_preview(board, path):
    """A copy of the board with the plugged boards' outlines on the silkscreen, so a
    render shows what the carrier looks like with them fitted. Not for manufacture."""
    for name, (x0, y0, x1, y1) in PLUGGED:
        for (a, b), (c, d) in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                               ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
            seg = pcbnew.PCB_SHAPE(board)
            seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
            seg.SetStart(at(a, b)); seg.SetEnd(at(c, d))
            seg.SetLayer(pcbnew.F_SilkS); seg.SetWidth(mm(0.5))
            board.Add(seg)
        text(board, name, (x0 + x1) / 2, (y0 + y1) / 2, 1.4)
    board.Save(path)


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
        if c["ref"][0] in "RCH" or c["ref"].startswith("TP") or c["ref"] in LABELLED | FAB_REF:
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
        if not pack(fps[ref][0], anchor, region, taken) and \
                not pack(fps[ref][0], (38.0, 18.0), SPILL, taken):
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
    for s_, x, y in LABELS:
        text(board, s_, x, y, 0.8)
    # Polarity marks from the real pad positions, so they can't drift from the pads.
    for ref, marks, (dx, dy) in (("J5", {"1": "+", "2": "-"}, (0, -1.9)),):
        for pad in fps[ref][0].Pads():
            if pad.GetNumber() in marks:
                px = pcbnew.ToMM(pad.GetPosition().x) - ORIGIN[0]
                py = pcbnew.ToMM(pad.GetPosition().y) - ORIGIN[1]
                text(board, marks[pad.GetNumber()], px + dx, py + dy, 0.8)
    # Bottom: title, test-pad heading, harness pinout (the top is all under boards).
    text(board, "OpenCollar carrier rev A2", 38.0, 33.5, 1.0, pcbnew.B_SilkS, mirror=True)
    text(board, "CERN-OHL-P  2026-09-27", 38.0, 35.3, 0.8, pcbnew.B_SilkS, mirror=True)
    text(board, "TEST PADS", 38.5, 7.3, 0.8, pcbnew.B_SilkS, mirror=True)
    text(board, "HARNESS M8: 1 SDA 2 BAT+ 3 GND 4 SCL", 38.0, 53.0, 0.8, pcbnew.B_SilkS, mirror=True)
    text(board, "5 NTC 6 INT 7 GND 8 BAT+  (bench: PH8 pigtail)", 38.0, 54.3, 0.8, pcbnew.B_SilkS, mirror=True)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(dst)
    assembled_preview(board, dst.replace(".kicad_pcb", "_assembled.kicad_pcb"))
    print(f"{len(fps)} footprints, {len(nets)} nets -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
