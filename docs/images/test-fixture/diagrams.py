"""Draw the SVG diagrams for docs/TEST-FIXTURE.md.

    python3 docs/images/test-fixture/diagrams.py        # writes *.svg next to this file

tp.json (test-pad and hole positions) comes from the carrier's .kicad_pcb via
export_pads.py, so the pad map always matches the real board.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BG, INK, MUTED = "#f6f4ef", "#1e2622", "#6b726d"
GREEN, PALE = "#2f6f4a", "#e3ece5"
PCB, PAD, METAL, SPRING = "#2d6a45", "#d3a13f", "#b9bcbf", "#7d8387"
GREY, DARK = "#d9d6ce", "#3a3f3c"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"


class SVG:
    def __init__(self, w, h):
        self.w, self.h, self.items = w, h, []

    def add(self, s):
        self.items.append(s)

    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=2, rx=0, extra=""):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}" {extra}/>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=2, dash=None, arrow=False):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        a = ' marker-end="url(#arrow)"' if arrow else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                 f'stroke-width="{sw}"{d}{a}/>')

    def path(self, d, fill="none", stroke=INK, sw=2, extra=""):
        self.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

    def circle(self, x, y, r, fill="none", stroke=INK, sw=2):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def text(self, x, y, s, size=22, fill=INK, weight=400, anchor="start", italic=False):
        st = ' font-style="italic"' if italic else ""
        for i, part in enumerate(s.split("\n")):
            self.add(f'<text x="{x}" y="{y + i * size * 1.3}" font-family="{FONT}" font-size="{size}" '
                     f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{st}>{esc(part)}</text>')

    def callout(self, x, y, tx, ty, label, size=22, anchor="start"):
        """A thin leader line from a point on the drawing to a label."""
        self.circle(x, y, 4, fill=INK, stroke="none")
        self.line(x, y, tx, ty, stroke=INK, sw=1.5)
        dx = 8 if anchor == "start" else -8
        self.text(tx + dx, ty + size * 0.35, label, size=size, anchor=anchor)

    def save(self, name):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" '
                f'refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>'
                f'<rect width="100%" height="100%" fill="{BG}"/>')
        open(os.path.join(HERE, name), "w").write(head + "\n".join(self.items) + "</svg>")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def spring(s, x, y0, y1, w=10, turns=7, stroke=SPRING, sw=2):
    """A zig-zag spring from y0 down to y1 centred on x."""
    pts = [(x, y0)]
    step = (y1 - y0) / (turns * 2)
    for i in range(1, turns * 2):
        pts.append((x + (w if i % 2 else -w), y0 + i * step))
    pts.append((x, y1))
    s.path("M" + " L".join(f"{a},{b}" for a, b in pts), stroke=stroke, sw=sw)


# ------------------------------------------------------------------ 1. how a board gets made

def pipeline():
    s = SVG(1600, 560)
    s.text(60, 70, "How a circuit board gets made", 34, weight=600)
    s.text(60, 108, "Six steps from a design file to a collar. We own the ones in green.", 22, MUTED)
    steps = [
        ("Design", "Us", "KiCad, SKiDL, agents", "days", True),
        ("Bare board", "JLCPCB", "copper, drilling, mask", "2–5 days", False),
        ("Assembly", "JLCPCB, later\nour own small line", "machines place and\nsolder every part", "1–2 weeks", False),
        ("Test", "Us: the fixture", "every board, pass or fail", "30–60 s a board", True),
        ("Final assembly", "Us", "shell, seals, battery,\nstrap", "minutes", True),
        ("On the cow", "The farm", "", "", False),
    ]
    x0, dx, top = 60, 252, 170
    for i, (name, who, what, time, ours) in enumerate(steps):
        x = x0 + i * dx
        cx = x + 100
        col = GREEN if ours else DARK
        s.rect(x, top, 200, 150, fill=PALE if ours else "#ecebe6", stroke=col, sw=2, rx=10)
        icon(s, i, cx, top + 75)
        s.text(cx, top + 190, name, 26, weight=600, anchor="middle", fill=col)
        s.text(cx, top + 225, who, 20, anchor="middle")
        if what:
            s.text(cx, top + 285, what, 18, MUTED, anchor="middle")
        if time:
            s.text(cx, top + 355, time, 18, MUTED, anchor="middle", italic=True)
        if i < len(steps) - 1:
            s.line(x + 206, top + 75, x + dx - 8, top + 75, sw=2, arrow=True)
    s.save("01-how-a-board-gets-made.svg")


def icon(s, i, cx, cy):
    if i == 0:      # a screen with a schematic
        s.rect(cx - 55, cy - 40, 110, 70, fill="white", sw=2, rx=4)
        s.line(cx - 20, cy + 30, cx - 30, cy + 45); s.line(cx + 20, cy + 30, cx + 30, cy + 45)
        s.path(f"M{cx-40},{cy-10} h20 l5,-10 l10,20 l10,-20 l10,20 l5,-10 h20", stroke=GREEN)
        s.rect(cx - 12, cy + 5, 24, 14, sw=1.5)
    elif i == 1:    # bare board
        s.rect(cx - 60, cy - 38, 120, 76, fill=PCB, stroke=DARK, rx=4)
        for px, py in [(-40, -20), (-40, 18), (40, -20), (40, 18)]:
            s.circle(cx + px, cy + py, 5, fill=BG, stroke="none")
        s.path(f"M{cx-25},{cy} h20 v-15 h30", stroke=PAD, sw=3)
    elif i == 2:    # board with parts and a placement nozzle
        s.rect(cx - 60, cy - 10, 120, 42, fill=PCB, stroke=DARK, rx=4)
        for px in (-40, -12, 18):
            s.rect(cx + px, cy - 2, 18, 12, fill=DARK, stroke="none")
        s.rect(cx + 36, cy - 45, 12, 30, fill=METAL, stroke=DARK, sw=1.5)
        s.rect(cx + 34, cy - 18, 16, 8, fill=DARK, stroke="none")
    elif i == 3:    # board on pins
        s.rect(cx - 60, cy - 25, 120, 12, fill=PCB, stroke=DARK)
        for px in range(-45, 50, 18):
            s.line(cx + px, cy - 13, cx + px, cy + 20, stroke=PAD, sw=4)
        s.rect(cx - 70, cy + 20, 140, 14, fill=GREY, stroke=DARK)
    elif i == 4:    # crest unit on a strap
        s.path(f"M{cx-60},{cy+25} Q{cx},{cy-45} {cx+60},{cy+25}", stroke=DARK, sw=6)
        s.rect(cx - 28, cy - 30, 56, 18, fill=GREY, stroke=DARK, rx=6)
    else:           # a collar on a neck
        s.path(f"M{cx-35},{cy-40} Q{cx-55},{cy+10} {cx-30},{cy+40} L{cx+30},{cy+40} "
               f"Q{cx+55},{cy+10} {cx+35},{cy-40}", stroke=MUTED, sw=2, fill="#eae6dc")
        s.path(f"M{cx-44},{cy-10} Q{cx},{cy-30} {cx+44},{cy-10}", stroke=DARK, sw=5)
        s.rect(cx - 16, cy - 32, 32, 10, fill=GREY, stroke=DARK, rx=3)
        s.rect(cx - 14, cy + 30, 28, 14, fill=DARK, stroke="none", rx=3)


# ------------------------------------------------------------------ 2. fixture cross-section

def section():
    s = SVG(1800, 980)
    s.text(60, 70, "A bed-of-nails test fixture, cut in half", 34, weight=600)
    s.text(60, 108, "The board drops onto spring pins; the lid closes; the pins press on test pads under the board.", 22, MUTED)
    L, R = 540, 1300           # fixture extent
    LX, RX = 480, 1370          # label columns
    # base box
    s.rect(L - 30, 720, R - L + 60, 190, fill=DARK, stroke=INK, rx=12)
    # probe plate
    plate_y, plate_h = 640, 80
    s.rect(L - 10, plate_y, R - L + 20, plate_h, fill=GREY, stroke=INK)
    # board, with a tooling hole near its right end
    by, bh = 520, 26
    bl, br = L + 40, R - 40
    ax = R - 110
    s.rect(bl, by, br - bl, bh, fill=PCB, stroke=INK)
    s.rect(ax - 20, by - 1, 40, bh + 2, fill=BG, stroke="none")
    s.line(ax - 20, by, ax - 20, by + bh, sw=1.5); s.line(ax + 20, by, ax + 20, by + bh, sw=1.5)
    parts = [(bl + 40, 60, 22), (bl + 170, 36, 14), (bl + 270, 90, 30), (bl + 450, 40, 16), (bl + 560, 70, 26)]
    for px, pw, ph in parts:
        s.rect(px, by - ph, pw, ph, fill=INK, stroke="none", rx=2)
    pins = [bl + 90, bl + 230, bl + 370, bl + 510]
    for px in pins:
        s.rect(px - 16, by + bh, 32, 6, fill=PAD, stroke="none")                        # test pad
        s.rect(px - 13, plate_y - 4, 26, plate_h + 40, fill=METAL, stroke=INK, sw=1.5)   # receptacle
        s.rect(px - 9, plate_y - 60, 18, 64, fill="#cfd2d4", stroke=INK, sw=1.5)         # barrel
        spring(s, px, plate_y - 50, plate_y + 30, w=6, turns=8)
        s.rect(px - 5, by + bh + 6, 10, plate_y - 60 - (by + bh + 6), fill=PAD, stroke=INK, sw=1.2)  # plunger
        s.path(f"M{px},{plate_y + plate_h + 36} C{px},{plate_y + plate_h + 90} {px + 40},{plate_y + plate_h + 110} {px + 40},{plate_y + plate_h + 150}",
               stroke="#a33", sw=3)
    # alignment pin through the tooling hole
    s.rect(ax - 12, by - 60, 24, plate_y - by + 60 + plate_h, fill="#9ea3a7", stroke=INK)
    s.path(f"M{ax-12},{by-60} L{ax},{by-78} L{ax+12},{by-60} z", fill="#9ea3a7", stroke=INK)
    # lid, hinge and push fingers (on bare board, clear of parts)
    s.rect(L - 10, 330, R - L + 20, 40, fill="#dfe8ee", stroke=INK)
    for fx in (bl + 20, bl + 400, bl + 660):
        s.rect(fx - 10, 370, 20, by - 370, fill="#f0ede4", stroke=INK)
    s.circle(R + 10, 350, 14, fill=METAL, stroke=INK)
    # labels, left
    s.callout(L + 60, 345, LX, 300, "Lid, closed by hand or a toggle clamp", anchor="end")
    s.callout(bl + 400, 440, LX, 440, "Push fingers press on bare board", anchor="end")
    s.callout(bl + 330, by + 14, LX, 560, "Board under test (the “DUT”)", anchor="end")
    s.callout(pins[0], by + bh + 3, LX, 620, "Test pad, 1 mm, on the underside", anchor="end")
    s.callout(pins[1], plate_y + 20, LX, 700, "Pogo pin: a spring-loaded probe", anchor="end")
    s.callout(L, plate_y + 60, LX, 780, "Probe plate, drilled to the pad map", anchor="end")
    # labels, right
    s.callout(ax + 12, by - 40, RX, 470, "Alignment pin through a tooling hole:")
    s.text(RX + 8, 505, "puts the board in the same place\nto a tenth of a millimetre", 20, MUTED)
    s.callout(R + 10, 350, RX, 350, "Hinge")
    s.callout(R - 60, 800, RX, 800, "Base: wiring and electronics")
    s.callout(pins[3] + 40, plate_y + plate_h + 150, RX, 880, "One wire per pin, to the test station")
    s.save("02-fixture-section.svg")


# ------------------------------------------------------------------ 3. pogo pin up close

def pogo():
    s = SVG(1600, 1110)
    s.text(60, 70, "A pogo pin, up close", 34, weight=600)
    s.text(60, 108, "About 1 mm wide. A spring inside keeps the tip pressed onto the pad, even if the board sits slightly crooked.", 22, MUTED)
    s.add('<g transform="translate(0,90)">')
    cx = 420
    # receptacle
    s.rect(cx - 34, 470, 68, 330, fill=METAL, stroke=INK)
    s.rect(cx - 6, 800, 12, 50, fill=METAL, stroke=INK)
    # plate section
    s.rect(cx - 200, 560, 400, 110, fill=GREY, stroke=INK, extra='opacity="0.6"')
    # barrel
    s.rect(cx - 24, 300, 48, 260, fill="#d5d8da", stroke=INK)
    spring(s, cx, 330, 540, w=14, turns=10)
    # plunger
    s.rect(cx - 12, 170, 24, 170, fill=PAD, stroke=INK)
    s.path(f"M{cx-12},170 L{cx},130 L{cx+12},170 z", fill=PAD, stroke=INK)
    # pad above
    s.rect(cx - 70, 110, 140, 14, fill=PAD, stroke=INK)
    s.rect(cx - 200, 70 + 20, 400, 20, fill=PCB, stroke=INK)
    s.callout(cx + 70, 110, 760, 150, "Test pad on the board")
    s.callout(cx + 8, 150, 760, 215, "Tip: shaped to bite through flux and oxide")
    s.callout(cx + 12, 250, 760, 280, "Plunger: gold-plated, slides in and out")
    s.callout(cx + 14, 430, 760, 400, "Spring: gives ~1–2 N of force at working travel")
    s.callout(cx + 24, 330, 760, 340, "Barrel: holds the plunger and spring")
    s.callout(cx + 34, 620, 760, 520, "Receptacle: pressed into the plate, so a worn")
    s.text(768, 555, "pin swaps out without rewiring", 22)
    s.callout(cx + 6, 830, 760, 640, "Tail: the wire is soldered or wrapped here")
    s.text(760, 720, "Typical size for our boards: “100 mil” probes (2.54 mm spacing),", 20, MUTED)
    s.text(760, 748, "~1 mm barrel, rated for tens of thousands of presses.", 20, MUTED)
    # tip styles
    s.text(760, 820, "Tip shapes", 22, weight=600)
    tips = [("Spear", "flat pads (ours)"), ("Crown", "pins and vias"), ("Flat", "gold pads"), ("Cup", "wire ends, pins")]
    for i, (name, use) in enumerate(tips):
        x = 800 + i * 200
        s.rect(x - 10, 880, 20, 70, fill=PAD, stroke=INK, sw=1.5)
        if name == "Spear":
            s.path(f"M{x-10},880 L{x},850 L{x+10},880 z", fill=PAD, stroke=INK, sw=1.5)
        elif name == "Crown":
            s.path(f"M{x-10},880 L{x-10},860 L{x-5},872 L{x},858 L{x+5},872 L{x+10},860 L{x+10},880 z", fill=PAD, stroke=INK, sw=1.5)
        elif name == "Flat":
            s.rect(x - 14, 872, 28, 8, fill=PAD, stroke=INK, sw=1.5)
        else:
            s.path(f"M{x-12},880 L{x-12},862 Q{x},878 {x+12},862 L{x+12},880 z", fill=PAD, stroke=INK, sw=1.5)
        s.text(x + 22, 890, name, 20, weight=600)
        s.text(x + 22, 918, use, 17, MUTED)
    s.add("</g>")
    s.save("03-pogo-pin.svg")


# ------------------------------------------------------------------ 4. the test station

def station():
    s = SVG(1600, 1060)
    s.text(60, 70, "The test station: what the fixture plugs into", 34, weight=600)
    s.text(60, 108, "Example parts and rough prices. Every box talks to the Raspberry Pi, which runs the test script.", 22, MUTED)
    fx, fy, fw, fh = 620, 420, 360, 220
    s.rect(fx, fy, fw, fh, fill=PALE, stroke=GREEN, sw=3, rx=12)
    s.text(fx + fw / 2, fy + 90, "Fixture", 30, weight=600, anchor="middle", fill=GREEN)
    s.text(fx + fw / 2, fy + 130, "board on the pins", 20, MUTED, anchor="middle")
    s.text(fx + fw / 2, fy + 160, "~33 wires out", 20, MUTED, anchor="middle")
    boxes = [
        # (x, y, title, example with price, what it does on the board, side)
        (60, 170, "Test computer", "Raspberry Pi 5 · ~$60–80", "runs the script; USB to every box here", "pi"),
        (60, 420, "Programmer", "Raspberry Pi Debug Probe · $12\nor SEGGER J-Link · ~$500", "SWD pads: flashes firmware", "l"),
        (60, 680, "Serial console", "FTDI TTL-232R-3V3 cable · ~$20", "UART pads: reads test output", "l"),
        (1100, 170, "Battery stand-in and meter", "Nordic Power Profiler Kit II · ~$100", "BAT pads: supplies 3.3 V, measures\nfrom under 1 µA to 1 A", "r"),
        (1100, 420, "Solar stand-in", "USB bench supply, e.g. Riden RD6006 · ~$90", "SOLAR pads: fakes a 6 V panel", "r"),
        (1100, 680, "Voltage checks", "2 × ADS1115 ADC boards · ~$10 each", "rail pads: 3V3, charger, TS, ISET", "r"),
        (620, 170, "Switching", "8-channel USB relay board · ~$20", "connects each supply in turn", "t"),
        (620, 790, "Radios", "test SIM on the real network;\na GNSS re-radiator later · $200–600", "LTE attach, satellites seen", "b"),
        (60, 900, "Label printer", "Brother QL-800 · ~$100", "serial number + QR code", "pl"),
    ]
    for x, y, title, ex, role, side in boxes:
        w = 360 if side in ("t", "b") else 440
        h = {"pl": 130, "t": 170}.get(side, 190)
        s.rect(x, y, w, h, fill="white", stroke=INK, sw=1.5, rx=10)
        s.text(x + 20, y + 40, title, 23, weight=600)
        s.text(x + 20, y + 74, ex, 19)
        s.text(x + 20, y + (130 if "\n" in ex else 110), role, 18, MUTED)
        if side == "l":
            s.line(x + w, y + 95, fx - 6, fy + (60 if y < 500 else 160), arrow=True)
        elif side == "r":
            s.line(x, y + 95, fx + fw + 6, fy + (40 if y < 300 else 110 if y < 500 else 180), arrow=True)
        elif side == "t":
            s.line(x + w / 2, y + h, fx + fw / 2, fy - 6, arrow=True)
        elif side == "b":
            s.line(x + w / 2, y, fx + fw / 2, fy + fh + 6, arrow=True)
    s.text(1100, 935, "Do-it-yourself station: roughly $600–1,500", 22, weight=600)
    s.text(1100, 968, "in parts. A fixture maker builds one for", 20, MUTED)
    s.text(1100, 996, "about $3–10k (MANUFACTURING.md).", 20, MUTED)
    s.save("04-test-station.svg")


# ------------------------------------------------------------------ 5. the test sequence

def sequence():
    s = SVG(1600, 1180)
    s.text(60, 70, "One board through the fixture", 34, weight=600)
    s.text(60, 108, "The script runs top to bottom. Any failed check stops it and prints why. About a minute a board.", 22, MUTED)
    rows = [
        ("Load and close", "Operator drops the board on the pins, shuts the lid", "—", "5 s"),
        ("Power on", "Power Profiler supplies 3.3 V through the BAT pads, current-limited", "draws a few mA, not a short", "1 s"),
        ("Check the rails", "ADC reads every rail pad", "3V3 within ±3 %; charger pins at rest", "2 s"),
        ("Flash test firmware", "Programmer writes it through the SWD pads", "verify reads back correctly", "10–20 s"),
        ("Self-test", "Firmware talks to every chip, drives each piezo", "IMU, GNSS, fuel gauge, flash answer;\npiezo current seen", "5 s"),
        ("Charger", "Relay applies the 6 V solar stand-in", "“power good” low; charge current flows", "5 s"),
        ("Radios", "Modem registers on LTE; GNSS reads the re-radiated sky", "attached; enough satellites seen", "10–30 s"),
        ("Sleep current", "Board goes to its deepest sleep; Power Profiler measures", "under the budget, e.g. < 10 µA", "5 s"),
        ("Finish", "Flash the real firmware, write the serial number,\nprint the label, save the results", "all steps passed", "5–10 s"),
    ]
    y = 170
    s.text(150, y, "Step", 20, MUTED, weight=600)
    s.text(470, y, "What happens", 20, MUTED, weight=600)
    s.text(1080, y, "Pass if", 20, MUTED, weight=600)
    s.text(1540, y, "Time", 20, MUTED, weight=600, anchor="end")
    for i, (name, what, ok, t) in enumerate(rows):
        yy = y + 40 + i * 105
        s.circle(95, yy + 30, 26, fill=PALE, stroke=GREEN, sw=2)
        s.text(95, yy + 38, str(i + 1), 24, GREEN, weight=600, anchor="middle")
        if i < len(rows) - 1:
            s.line(95, yy + 56, 95, yy + 109, stroke=GREEN, sw=2)
        s.text(150, yy + 38, name, 24, weight=600)
        s.text(470, yy + 38, what, 19)
        s.text(1080, yy + 38, ok, 19, MUTED)
        s.text(1540, yy + 38, t, 19, anchor="end")
    s.save("05-test-sequence.svg")


# ------------------------------------------------------------------ 6. our carrier's pads

GROUPS = [
    ("Battery stand-in + current meter", "#c0392b", {"BAT", "GND"}),
    ("Solar stand-in", "#d68910", {"SOLAR_A", "SOLAR_B"}),
    ("Voltage checks (ADC)", "#2e86c1", {"CHG_OUT", "CHG_IN", "3V3", "EXT_3V3", "KIT_VSYS", "KIT_VBUS", "TS", "ISET"}),
    ("Programmer (SWD)", "#7d3c98", {"SWDIO", "SWCLK", "RESET"}),
    ("Serial console", "#148f77", {"UART_TX", "UART_RX"}),
    ("Buses and status (Pi GPIO/I2C)", "#566573", None),
]


def group(net):
    for name, col, nets in GROUPS:
        if nets is None or net in nets:
            return name, col


def padmap():
    tp = json.load(open(os.path.join(HERE, "tp.json")))
    W, H = tp["board"]
    k = 14.0                       # px per mm
    ox, oy = 90, 170
    s = SVG(1600, 1110)
    s.text(60, 70, "Our carrier board, seen from below (the fixture’s view)", 34, weight=600)
    s.text(60, 108, "Its 33 test pads, coloured by which instrument each one goes to. Positions from the real board file.", 22, MUTED)

    def P(x, y):   # mirrored left-right: we look at the underside
        return ox + (W - x) * k, oy + y * k

    s.rect(ox, oy, W * k, H * k, fill=PCB, stroke=INK, sw=2, rx=2 * k)
    for h in tp["holes"]:
        x, y = P(h["x"], h["y"])
        s.circle(x, y, h["d"] / 2 * k, fill=BG, stroke=INK, sw=1.5)
    for t in tp["tps"]:
        x, y = P(t["x"], t["y"])
        _, col = group(t["net"])
        s.circle(x, y, 0.55 * k, fill=col, stroke="white", sw=2)
    for ref in ("H1", "H4"):
        h = next(h for h in tp["holes"] if h["ref"] == ref)
        x, y = P(h["x"], h["y"])
        s.circle(x, y, h["d"] / 2 * k + 6, stroke="#1a5276", sw=3)
    hx, hy = P(62.06, 30.44)
    s.callout(hx, hy + 30, 90 + W * k + 60, 640, "Mounting holes, used as alignment holes")
    s.text(90 + W * k + 68, 675, "(the integrated board gets its own tooling holes)", 20, MUTED)
    lx, ly = 90 + W * k + 60, 200
    s.text(lx, ly, "Goes to", 22, MUTED, weight=600)
    for i, (name, col, _) in enumerate(GROUPS):
        yy = ly + 45 + i * 50
        s.circle(lx + 12, yy - 7, 11, fill=col, stroke="white", sw=2)
        s.text(lx + 36, yy, name, 22)
    s.text(90, oy + H * k + 60, "On this carrier, the processor lives on the plugged-in Connect Kit, so a carrier test is mostly power, charger", 20, MUTED)
    s.text(90, oy + H * k + 88, "and bus checks. The full sequence (flash, self-test, radios, sleep current) is for the integrated board.", 20, MUTED)
    s.save("06-carrier-pads.svg")


# ------------------------------------------------------------------ 7. what the integrated board needs

def dft():
    s = SVG(1600, 860)
    s.text(60, 70, "What the integrated board has to include, so it can be tested", 34, weight=600)
    s.text(60, 108, "Decided before layout. Adding any of these after the boards are made means a new board. Underside shown.", 22, MUTED)
    k = 6.4
    W, H = 125, 55
    ox, oy = 70, 230
    X = lambda x: ox + x * k
    Y = lambda y: oy + y * k
    s.rect(ox, oy, W * k, H * k, fill=PCB, stroke=INK, rx=20)
    # tooling holes, opposite corners
    for (x, y) in [(5, 5), (W - 5, H - 5)]:
        s.circle(X(x), Y(y), 1.5 * k, fill=BG, stroke=INK)
    # fiducials
    for (x, y) in [(12, 4.5), (W - 12, H - 4.5)]:
        s.circle(X(x), Y(y), 0.7 * k, fill=PAD, stroke="none")
    # test pad grid
    for i in range(10):
        for j in range(3):
            s.circle(X(52 + i * 5.08), Y(14 + j * 5.08), 0.55 * k, fill=PAD, stroke="white", sw=1.5)
    # SWD + serial pads
    for i in range(5):
        s.rect(X(52 + i * 2.54) - 0.5 * k, Y(38) - 0.5 * k, k, k, fill=PAD, stroke="none")
    # battery pads and the current-measure point
    s.rect(X(104), Y(36), 3 * k, 5 * k, fill=PAD, stroke="none")
    s.rect(X(110), Y(36), 3 * k, 5 * k, fill=PAD, stroke="none")
    s.rect(X(104), Y(44), 9 * k, 2 * k, fill="none", stroke=PAD, sw=2)
    # GNSS patch keep-out and RF test connectors
    s.rect(X(4), Y(14), 28 * k, 28 * k, fill="none", stroke=PAD, sw=2, extra='stroke-dasharray="8,6"')
    s.text(X(18), Y(29), "GNSS patch", 18, "white", anchor="middle")
    for (x, y) in [(35, 26), (118, 12)]:
        s.rect(X(x), Y(y), 2 * k, 2 * k, fill="#e8e3d6", stroke=INK, sw=1.5)
    # labels
    RX = ox + W * k + 50
    s.callout(X(W - 5), Y(H - 5), RX, 690, "Two tooling holes, far apart, not plated")
    s.callout(X(W - 12), Y(H - 4.5), RX, 610, "Fiducials: dots the machines find the board by")
    s.callout(X(97.7), Y(14), RX, 250, "Test pads: 1 mm, 2.54 mm grid, one side only")
    s.callout(X(119), Y(13), RX, 330, "RF test connectors on the LTE and GNSS feeds")
    s.text(RX + 8, 362, "e.g. Murata MM8130: the antenna is cut off", 18, MUTED)
    s.text(RX + 8, 386, "while a test cable is plugged in", 18, MUTED)
    s.callout(X(113), Y(38), RX, 450, "Battery pads the fixture supplies")
    s.callout(X(108.5), Y(45), RX, 530, "One point all the board current flows through,")
    s.text(RX + 8, 562, "so the fixture can measure sleep current", 18, MUTED)
    s.callout(X(57), Y(38), ox + 380, 670, "Programming (SWD) and serial pads", anchor="end")
    s.text(ox, 760, "Not drawn: a test mode in the firmware, and pads for every power rail. Outline: the crest-unit board, ~55 × 125 mm", 18, MUTED)
    s.text(ox, 786, "(COLLAR-FIRST-PRINCIPLES.md). Positions here are illustrative; the real ones come with the layout.", 18, MUTED)
    s.save("07-integrated-board-dft.svg")


if __name__ == "__main__":
    pipeline()
    section()
    pogo()
    station()
    sequence()
    padmap()
    dft()
    print("ok")
