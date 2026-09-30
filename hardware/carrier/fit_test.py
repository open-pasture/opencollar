"""A 1:1 paper fit test of the carrier, to print before ordering.

    kicad-python fit_test.py pcb/carrier.kicad_pcb build/carrier-fit-test.pdf

Print at 100 % ("actual size", no fit-to-page) and check the 50 mm bar with a ruler.
Then lay the real Connect Kit, MAX-M10S and ISM330 boards, header pins down, on the
drawn outlines: every pin should land in a circle. The circles are the socket contacts
(the middle of each socket, where the plugged board's pin goes in), not the solder pads,
which alternate either side.
"""
import math
import os
import subprocess
import sys
import tempfile

import pcbnew

mm, nm = pcbnew.ToMM, pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(nm(x), nm(y))
LAYER = pcbnew.Dwgs_User
ORIGIN = (100.0, 100.0)
# Plugged boards (board mm), from layout.py's PLUGGED table
KIT_X, KIT_TOP = 3.5, 0.5
PLUGGED = [   # name, outline, where the name goes (clear board)
    ("Connect Kit", (KIT_X - 1.27, KIT_TOP, KIT_X - 1.27 + 20.32, KIT_TOP + 55.88), (12.4, 28.5)),
    ("MAX-M10S", (26.5, 2.5, 26.5 + 38.10, 2.5 + 30.48), (38.0, 10.5)),
    ("ISM330", (26.5, 33.5, 26.5 + 25.40, 33.5 + 17.78), (39.0, 40.5)),
]
SOCKETS = ("J1", "J2", "J3", "J4", "J8", "J9", "J10")


def seg(b, a, c, w=0.25):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*c)); s.SetLayer(LAYER); s.SetWidth(nm(w))
    b.Add(s)


def circle(b, c, r, w=0.15):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(V(*c)); s.SetEnd(V(c[0] + r, c[1])); s.SetLayer(LAYER); s.SetWidth(nm(w))
    b.Add(s)


def text(b, s, x, y, h=1.2):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(s); t.SetPosition(V(x, y)); t.SetLayer(LAYER)
    t.SetTextSize(V(h, h)); t.SetTextThickness(nm(h * 0.15))
    b.Add(t)


def main(src, out):
    b = pcbnew.LoadBoard(src)
    ox, oy = ORIGIN
    for name, (x0, y0, x1, y1), (lx, ly) in PLUGGED:
        x0, y0, x1, y1 = x0 + ox, y0 + oy, x1 + ox, y1 + oy
        for a, c in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
            seg(b, a, c, 0.3)
        text(b, name, lx + ox, ly + oy, 1.3)
    for ref in SOCKETS:
        f = b.FindFootprintByReference(ref)
        o = f.GetPosition()
        a = math.radians(f.GetOrientationDegrees())
        for p in f.Pads():
            # the contact is on the socket's centre line (local x = 0), level with its pad
            ly = mm(p.GetFPRelativePosition().y)
            cx = mm(o.x) + ly * math.sin(a)
            cy = mm(o.y) + ly * math.cos(a)
            circle(b, (cx, cy), 0.55)
            seg(b, (cx - 0.3, cy), (cx + 0.3, cy), 0.1)
            seg(b, (cx, cy - 0.3), (cx, cy + 0.3), 0.1)
    # scale check below the board
    y = oy + 58.5 + 5.0
    seg(b, (ox, y), (ox + 50, y), 0.3)
    for k in range(0, 51, 10):
        seg(b, (ox + k, y - 1.2), (ox + k, y + 1.2), 0.2)
    text(b, "50 mm: measure this; if it isn't 50 mm, reprint at 100 %", ox + 25, y + 3.0, 1.4)
    text(b, "OpenCollar carrier 1:1 fit test. Plugged-board pins go in the circles.", ox + 32.5, oy - 3.5, 1.6)
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, "fit.kicad_pcb")
        b.Save(tmp)
        subprocess.run(["kicad-cli", "pcb", "export", "pdf", "--mode-single", "--black-and-white",
                        "--layers", "Edge.Cuts,F.Mask,F.Silkscreen,Dwgs.User", "--scale", "1",
                        "--drill-shape-opt", "2", "--exclude-value", "-o", out, tmp],
                       check=True, stdout=subprocess.DEVNULL)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
