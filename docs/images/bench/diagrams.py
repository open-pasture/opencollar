"""Draw the SVG diagrams for docs/BENCH-TESTS.md.

    python3 docs/images/bench/diagrams.py        # writes *.svg (and *.png with Chrome) here

Kit pin positions follow hardware/carrier/SPEC.md section 2: top view with USB up,
pins 1-20 run down the left row, 21-40 run up the right row, 2.54 mm pitch.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test-fixture"))
import diagrams as base  # noqa: E402
from diagrams import SVG, INK, MUTED, PCB, PAD, GREY, DARK  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
base.HERE = HERE
RED, BLACK, BLUE, YELLOW = "#c0392b", "#1e2622", "#2e6fd6", "#e0b000"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

K = 9  # px per mm for the Kit drawing


def kit(s, ox, oy, label_pins=()):
    """Connect Kit, top view, USB up. Returns a function pin -> (x, y)."""
    w, h = 20.32 * K, 55.88 * K
    s.rect(ox, oy, w, h, fill=PCB, stroke=INK, rx=8)
    s.rect(ox + w / 2 - 40, oy - 14, 80, 30, fill="#c9ccce", stroke=INK, rx=5)   # USB-C
    s.text(ox + w / 2, oy - 24, "USB", 18, MUTED, anchor="middle")
    s.text(ox + w / 2, oy + h * 0.55, "nRF9151\nConnect Kit", 18, "#e8efe9", 600, "middle")

    def pin(n):
        if n <= 20:
            return ox + 1.27 * K, oy + (3.81 + (n - 1) * 2.54) * K
        return ox + 19.05 * K, oy + (3.81 + (40 - n) * 2.54) * K

    for n in range(1, 41):
        x, y = pin(n)
        s.rect(x - 7, y - 7, 14, 14, fill=PAD if n in label_pins else "#9aa49d", stroke=INK, sw=1)
    return pin


def wire(s, x1, y1, x2, y2, col, bend=0.5):
    mx = x1 + (x2 - x1) * bend
    s.path(f"M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}", stroke=INK, sw=8, extra='stroke-linecap="round"')
    s.path(f"M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}", stroke=col, sw=5, extra='stroke-linecap="round"')


def qwiic_board(s, x, y, w, h, name, ports=2, extra=None):
    s.rect(x, y, w, h, fill="#d04040" if name.startswith("Qwiic Buzzer") else "#1f3a68", stroke=INK, rx=8)
    s.text(x + w / 2, y + h + 30, name, 20, INK, 600, "middle")
    pts = []
    for i in range(ports):
        cy = y + h * (i + 1) / (ports + 1)
        s.rect(x - 10, cy - 14, 24, 28, fill="#f2f2f2", stroke=INK, sw=1.5, rx=2)
        pts.append((x - 10, cy))
    if extra:
        extra(s)
    return pts


def png(name):
    if not os.path.exists(CHROME):
        return
    svg = os.path.join(HERE, name)
    with open(svg) as f:
        head = f.read(300)
    w = int(head.split('width="')[1].split('"')[0])
    h = int(head.split('height="')[1].split('"')[0])
    html = os.path.join(HERE, "_render.html")
    open(html, "w").write(f'<html><body style="margin:0"><img src="{name}" width="{w}" height="{h}"></body></html>')
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size={w},{h}", f"--screenshot={svg[:-4]}.png", "file://" + html],
                   check=True, capture_output=True)
    os.remove(html)


def save(s, name):
    s.save(name)
    png(name)


# ------------------------------------------------------------------ 1. buzzer

def buzzer():
    s = SVG(1200, 760)
    s.text(40, 50, "Test 1: buzzer onto the Kit (no soldering)", 30, INK, 700)
    s.text(40, 84, "Qwiic-to-female-socket cable (Adafruit 4397): plug the white plug into the buzzer, push the four sockets onto the Kit's pins", 18, MUTED)
    ox, oy = 470, 150
    pin = kit(s, ox, oy, label_pins=(15, 16, 39, 40))
    bx, by = 900, 300
    ports = qwiic_board(s, bx, by, 170, 150, "Qwiic Buzzer", ports=2,
                        extra=lambda s: (s.circle(bx + 95, by + 75, 40, fill="#222", stroke=INK),
                                         s.circle(bx + 95, by + 75, 8, fill="#555", stroke="none")))
    px, py = ports[0]
    # cable bundle: four wires fan out from a point left of the buzzer port
    fx = 790
    for i, (n, col, lab) in enumerate([(39, BLACK, "GND"), (40, RED, "3V3"), (16, BLUE, "SDA"), (15, YELLOW, "SCL")]):
        x, y = pin(n)
        wire(s, x, y, fx, py - 15 + i * 10, col, bend=0.6 if n > 20 else 0.75)
    s.rect(fx - 4, py - 20, px - fx + 4, 40, fill="#2a2a2a", stroke=INK, rx=6)
    # pin labels
    x, y = pin(40)
    s.text(x + 30, 136, "pin 40  3V3  (red)", 18, RED, 700)
    s.text(x + 30, 162, "pin 39  GND  (black)", 18, INK, 700)
    for n, txt, col in [(16, "pin 16  P0.30 / SDA  (blue)", BLUE), (15, "pin 15  P0.31 / SCL  (yellow)", "#a07c00")]:
        x, y = pin(n)
        s.line(x - 10, y, ox - 40, y, stroke=col, sw=1.5)
        s.text(ox - 48, y + 6, txt, 18, col, 700, "end")
    x, y = pin(1)
    s.text(ox - 48, y + 6, "pin 1 (VBUS)", 16, MUTED, anchor="end")
    s.line(x - 10, y, ox - 40, y, stroke=MUTED, sw=1)
    s.text(40, 690, "Top view, USB end up. Pins 1–20 run down the left row, 21–40 up the right row.", 18, MUTED)
    s.text(40, 716, "Check each pin against the name printed beside it on the Kit before plugging in USB.", 18, INK, 600)
    s.text(900, 520, "Pass: a short beep\nevery time the Kit\nstarts or is reset", 20, INK, 600)
    save(s, "01-buzzer.svg")


# ------------------------------------------------------------------ 2. polarity check

def meter(s, x, y, reading, ok=True):
    s.rect(x, y, 230, 330, fill="#f08a1c", stroke=INK, rx=22)
    s.rect(x + 25, y + 25, 180, 80, fill="#c8d6c0", stroke=INK, rx=6)
    s.text(x + 115, y + 82, reading, 40, INK if ok else RED, 700, "middle")
    s.circle(x + 115, y + 180, 48, fill="#2b2b2b", stroke=INK)
    s.line(x + 115, y + 180, x + 115, y + 140, stroke="#fff", sw=5)
    s.text(x + 115, y + 120, "V ⎓", 20, INK, 700, "middle")
    for i, (lab, col) in enumerate([("COM", BLACK), ("VΩ", RED)]):
        cx = x + 70 + i * 90
        s.circle(cx, y + 280, 14, fill=col, stroke=INK)
        s.text(cx, y + 318, lab, 16, INK, 700, "middle")
    return (x + 70, y + 280), (x + 160, y + 280)


def jst_plug(s, x, y):
    """JST-PH plug seen from its open face, two contacts; red wire left, black right."""
    s.rect(x, y, 110, 60, fill="#f4f1ea", stroke=INK, rx=4)
    s.rect(x + 18, y + 18, 26, 26, fill="#c9a24a", stroke=INK, sw=1.5)
    s.rect(x + 66, y + 18, 26, 26, fill="#c9a24a", stroke=INK, sw=1.5)
    return (x + 31, y + 31), (x + 79, y + 31)


def polarity():
    s = SVG(1200, 720)
    s.text(40, 50, "Test 2: which wire is + (multimeter, nothing plugged in)", 30, INK, 700)
    s.text(40, 84, "Do this for the battery pack's plug, then for one 1.25 mm lead plugged into the Kit's J2 socket", 18, MUTED)
    for col, (ox, reading, ok, verdict) in enumerate([(40, "+3.9", True, "Plus sign: red wire is +. Good."),
                                                      (620, "–3.9", False, "Minus sign: wires are swapped. Stop.")]):
        com, vo = meter(s, ox, 150, reading, ok)
        # pack
        s.rect(ox + 330, 420, 200, 150, fill="#3d6fd6", stroke=INK, rx=10)
        s.text(ox + 430, 505, "6600 mAh\npack", 18, "#fff", 600, "middle")
        r, b = jst_plug(s, ox + 360, 200)
        rw, bw = (RED, BLACK) if ok else (BLACK, RED)
        s.path(f"M{r[0]},{r[1] + 29} C{r[0]},330 {ox + 400},380 {ox + 400},420", stroke=rw, sw=6)
        s.path(f"M{b[0]},{b[1] + 29} C{b[0]},330 {ox + 460},380 {ox + 460},420", stroke=bw, sw=6)
        # probes: red probe always on the red wire's contact
        red_target = r if ok else b
        blk_target = b if ok else r
        rx_, bx_ = ox + 290, ox + 252
        s.path(f"M{vo[0]},{vo[1]} L{rx_},{vo[1]} L{rx_},180 L{red_target[0]},180 L{red_target[0]},{red_target[1] - 40}",
               stroke=RED, sw=5, extra='stroke-linejoin="round"')
        s.path(f"M{com[0]},{com[1]} L{com[0]},{com[1] + 80} L{bx_},{com[1] + 80} L{bx_},140 L{blk_target[0]},140 "
               f"L{blk_target[0]},{blk_target[1] - 40}", stroke=BLACK, sw=5, extra='stroke-linejoin="round"')
        for tg, c in [(red_target, RED), (blk_target, BLACK)]:
            s.line(tg[0], tg[1] - 40, tg[0], tg[1] - 4, stroke=c, sw=3)
            s.circle(tg[0], tg[1] - 4, 4, fill=c, stroke="none")
        s.text(ox, 620, verdict, 22, INK if ok else RED, 700)
    s.text(40, 662, "Dial on DC volts (V with the straight line). Red probe to the red wire's contact, black probe to the black wire's.", 18, MUTED)
    s.text(40, 688, "Keep the two probe tips apart: touching them across the pack shorts it. Expect between 3.7 and 4.2 V.", 18, INK, 600)
    save(s, "02-polarity.svg")


# ------------------------------------------------------------------ 3. charger alone

def charger_board(s, x, y, w=300, h=260):
    s.rect(x, y, w, h, fill="#1f3a68", stroke=INK, rx=10)
    s.text(x + w / 2, y + h / 2 + 8, "bq24074\ncharger", 22, "#e6ecf7", 600, "middle")
    s.rect(x - 14, y + 40, 40, 60, fill="#c9ccce", stroke=INK, rx=6)          # USB-C
    s.text(x + 12, y + 128, "USB-C in", 16, "#e6ecf7", 600)
    s.rect(x + w - 30, y + h - 90, 44, 56, fill="#f4f1ea", stroke=INK, rx=3)   # BATT JST
    s.text(x + w + 22, y + h - 98, "BATT socket", 18, INK, 600)
    s.circle(x + 60, y + h - 40, 10, fill="#ffb000", stroke=INK)
    s.text(x + 80, y + h - 34, "CHG light", 16, "#e6ecf7")
    return (x + w + 14, y + h - 62)


def charger():
    s = SVG(1200, 700)
    s.text(40, 50, "Test 3: charger and pack on their own (no soldering)", 30, INK, 700)
    s.text(40, 84, "Nothing connects to the Kit yet. Leave the thermistor off.", 18, MUTED)
    batt = charger_board(s, 360, 170)
    s.rect(60, 170, 150, 110, fill="#f2f2f2", stroke=INK, rx=12)
    s.text(135, 232, "USB charger\n(phone brick)", 18, INK, 600, "middle")
    s.path(f"M210,225 C280,225 280,240 346,240", stroke="#555", sw=8)
    s.rect(820, 380, 240, 170, fill="#3d6fd6", stroke=INK, rx=10)
    s.text(940, 470, "6600 mAh pack", 20, "#fff", 600, "middle")
    s.path(f"M{batt[0]},{batt[1] - 10} C780,{batt[1] - 10} 760,400 880,380", stroke=RED, sw=6)
    s.path(f"M{batt[0]},{batt[1] + 10} C760,{batt[1] + 10} 740,420 900,380", stroke=BLACK, sw=6)
    s.text(40, 560, "1. Plug the pack's plug into the BATT socket (it only fits one way).", 20)
    s.text(40, 592, "2. Plug USB into the charger. The CHG light comes on while it charges.", 20)
    s.text(40, 624, "3. Measure the pack again after 15–30 minutes: it should read a little higher.", 20)
    s.text(40, 670, "Layout is approximate; go by the names printed on the board.", 18, MUTED)
    save(s, "03-charger.svg")


# ------------------------------------------------------------------ 4. charger to Kit

def charger_kit():
    s = SVG(1200, 830)
    s.text(40, 50, "Test 4: the charger powers the Kit (one soldering job)", 30, INK, 700)
    s.text(40, 84, "A 1.25 mm lead goes from the charger's OUT and GND to the Kit's J2. This is the wiring the carrier board will use.", 18, MUTED)
    batt = charger_board(s, 120, 200, 300, 260)
    s.rect(560, 470, 200, 130, fill="#3d6fd6", stroke=INK, rx=10)
    s.text(660, 542, "pack", 20, "#fff", 600, "middle")
    s.path(f"M{batt[0]},{batt[1] - 8} C520,{batt[1] - 8} 520,470 620,470", stroke=RED, sw=6)
    s.path(f"M{batt[0]},{batt[1] + 8} C500,{batt[1] + 8} 500,490 660,470", stroke=BLACK, sw=6)
    # OUT / GND pads
    for i, lab in enumerate(["OUT", "GND"]):
        s.circle(220 + i * 50, 230, 12, fill=PAD, stroke=INK)
        s.text(220 + i * 50, 262, lab, 16, "#fff", 700, "middle")
    # Kit, underside view, with J2
    kx, ky = 880, 170
    s.rect(kx, ky, 20.32 * K, 55.88 * K, fill=PCB, stroke=INK, rx=8)
    s.text(kx + 91, ky - 20, "Kit, turned over (underside)", 18, MUTED, anchor="middle")
    s.rect(kx + 40, ky + 300, 100, 40, fill="#f4f1ea", stroke=INK, rx=3)
    s.text(kx + 90, ky + 326, "J2", 18, INK, 700, "middle")
    s.text(kx + 20, ky + 380, "+ and – marks\nbeside J2", 16, "#e8efe9", 600)
    s.path(f"M220,218 C220,120 700,120 {kx + 70},{ky + 300}", stroke=RED, sw=5)
    s.path(f"M270,218 C270,140 680,150 {kx + 110},{ky + 300}", stroke=BLACK, sw=5)
    s.text(470, 140, "1.25 mm lead: red to OUT, black to GND", 18, INK, 700)
    s.text(40, 726, "Before soldering: send a photo of the charger's pads and of J2 with the lead plugged in.", 20, RED, 700)
    s.text(40, 760, "Pass: with USB only on the charger, the Kit starts and beeps. Unplug USB: it keeps running from the pack.", 20)
    s.text(40, 796, "J2 position on the underside is approximate; the pad names on both boards are what count.", 18, MUTED)
    save(s, "04-charger-kit.svg")


# ------------------------------------------------------------------ 5. IMU

def imu():
    s = SVG(1200, 520)
    s.text(40, 50, "Test 5: motion sensor (IMU) chained off the buzzer", 30, INK, 700)
    s.text(40, 84, "Qwiic boards pass the bus through: the buzzer's second port feeds the IMU", 18, MUTED)
    s.rect(60, 180, 160, 230, fill=PCB, stroke=INK, rx=10)
    s.text(140, 300, "Kit", 22, "#e8efe9", 700, "middle")
    s.text(140, 440, "pins 15, 16, 39, 40", 16, MUTED, anchor="middle")
    bp = qwiic_board(s, 480, 200, 170, 150, "Qwiic Buzzer", ports=2)
    ip = qwiic_board(s, 880, 200, 200, 150, "ISM330DHCX IMU", ports=2)
    for i, col in enumerate([BLACK, RED, BLUE, YELLOW]):
        wire(s, 220, 250 + i * 18, 380, bp[0][1] - 12 + i * 8, col)
    s.rect(380, bp[0][1] - 20, bp[0][0] - 380, 40, fill="#2a2a2a", stroke=INK, rx=6)
    s.text(300, 180, "socket cable (4397)", 16, MUTED, anchor="middle")
    s.path(f"M{bp[1][0]},{bp[1][1]} C700,{bp[1][1] + 120} 800,{ip[0][1]} {ip[0][0]},{ip[0][1]}", stroke="#2a2a2a", sw=12)
    s.text(780, 420, "100 mm Qwiic cable (4210)", 16, MUTED, anchor="middle")
    s.text(40, 490, "Firmware doesn't read the IMU yet. A console command to scan the bus and print IMU readings is the next firmware job.", 18, INK, 600)
    save(s, "05-imu.svg")


if __name__ == "__main__":
    buzzer()
    polarity()
    charger()
    charger_kit()
    imu()
    print("ok")
