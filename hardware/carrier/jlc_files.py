"""JLCPCB assembly files for the carrier: BOM and placement (CPL), plus Gerbers and drill.

    kicad-python jlc_files.py pcb/carrier.kicad_pcb build/fab

JLCPCB places parts with its own footprints (the EasyEDA library behind each LCSC
number), whose zero rotation and origin often differ from KiCad's. Instead of a
rotation table, this fetches JLCPCB's footprint for every part, finds the rotation and
offset that land its pads on ours, and writes the placement from that. Each part's pad
fit is reported: a large error means the two footprints disagree, which is a design
problem to fix before ordering, not a rotation to tweak.

Writes build/fab/carrier-BOM.csv, carrier-CPL.csv, carrier-gerbers.zip and
footprint-check.txt. Network access: easyeda.com (JLCPCB's public footprint API).
"""
import csv
import json
import math
import os
import subprocess
import sys
import zipfile

import pcbnew

mm = pcbnew.ToMM
FP_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
EE_UNIT = 0.254          # EasyEDA footprint units are 10 mil
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "easyeda")


def easyeda_pads(lcsc):
    """JLCPCB's footprint for an LCSC part: {pad number: (x, y)} in mm, y down, relative
    to the footprint origin JLCPCB places by, plus the footprint's title."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{lcsc}.json")
    if not os.path.exists(path):
        url = f"https://easyeda.com/api/products/{lcsc}/components?version=6.4.19.5"
        # curl, not urllib: KiCad's bundled Python has no certificate store
        subprocess.run(["curl", "-sSfL", "--max-time", "30", "-o", path, url], check=True)
    d = json.load(open(path))["result"]["packageDetail"]
    ds = d["dataStr"]
    ox, oy = float(ds["head"]["x"]), float(ds["head"]["y"])
    pads = {}
    for s in ds["shape"]:
        if s.startswith("PAD~"):
            f = s.split("~")
            pads.setdefault(f[8], []).append(((float(f[2]) - ox) * EE_UNIT, (float(f[3]) - oy) * EE_UNIT))
    # a pad number used twice (split exposed pads, mounting tabs): use their middle
    return {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in pads.items()}, d["title"]


def kicad_pads(f):
    """Our footprint's pads at zero rotation, relative to its origin, same format."""
    lib = str(f.GetFPID().GetLibNickname()) or ""
    name = str(f.GetFPID().GetLibItemName())
    g = None
    if lib:
        try:
            g = pcbnew.FootprintLoad(os.path.join(FP_DIR, lib + ".pretty"), name)
        except Exception:
            g = None
    if g is None:              # fall back to the placed copy, un-rotated
        g = f
    pads = {}
    for p in g.Pads():
        q = p.GetFPRelativePosition() if g is not f else None
        if q is None:
            v = p.GetPosition() - f.GetPosition()
            a = -math.radians(f.GetOrientationDegrees())
            x, y = mm(v.x), mm(v.y)
            q = (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))
        else:
            q = (mm(q.x), mm(q.y))
        if p.GetNumber():
            pads.setdefault(p.GetNumber(), []).append(q)
    return {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in pads.items()}


def rot(p, deg):
    """Rotate counter-clockwise as seen on screen (y down), like KiCad's orientation."""
    a = math.radians(deg)
    return (p[0] * math.cos(a) + p[1] * math.sin(a), -p[0] * math.sin(a) + p[1] * math.cos(a))


def fit(k, e):
    """Rotation t (0/90/180/270) and offset d with e ~= rot(k, t) + d; returns (t, d, rms, n)."""
    common = sorted(set(k) & set(e))
    best = None
    for t in (0, 90, 180, 270):
        rk = [rot(k[n], t) for n in common]
        dx = sum(e[n][0] - r[0] for n, r in zip(common, rk)) / len(common)
        dy = sum(e[n][1] - r[1] for n, r in zip(common, rk)) / len(common)
        err = math.sqrt(sum((e[n][0] - r[0] - dx) ** 2 + (e[n][1] - r[1] - dy) ** 2
                            for n, r in zip(common, rk)) / len(common))
        if best is None or err < best[2]:
            best = (t, (dx, dy), err, len(common))
    return best


def main(board_path, out):
    os.makedirs(out, exist_ok=True)
    b = pcbnew.LoadBoard(board_path)
    bom, cpl, report = {}, [], []
    for f in sorted(b.GetFootprints(), key=lambda f: (f.GetReference()[0], int("0" + "".join(c for c in f.GetReference() if c.isdigit())))):
        ref = f.GetReference()
        attrs = f.GetAttributes()
        if f.IsDNP() or attrs & pcbnew.FP_EXCLUDE_FROM_BOM or ref.startswith(("TP", "H")):
            continue
        lcsc = f.GetFieldText("LCSC") if f.HasField("LCSC") else ""
        if not lcsc:
            report.append(f"{ref}: NO LCSC NUMBER")
            continue
        key = (f.GetValue(), str(f.GetFPID().GetLibItemName()), lcsc)
        bom.setdefault(key, []).append(ref)
        e, title = easyeda_pads(lcsc)
        k = kicad_pads(f)
        t, (dx, dy), err, n = fit(k, e)
        # JLCPCB puts its footprint's origin at (Mid X, Mid Y), turned by Rotation:
        # e = rot(k, t) + d, so its rotation is ours minus t, and its origin sits -d from ours
        r_k = f.GetOrientationDegrees()
        r_j = (r_k - t) % 360
        ox, oy = rot((-dx, -dy), r_j)
        px, py = mm(f.GetPosition().x) + ox, mm(f.GetPosition().y) + oy
        side = "Top" if f.GetLayer() == pcbnew.F_Cu else "Bottom"
        cpl.append((ref, f"{px:.4f}mm", f"{-py:.4f}mm", side, f"{r_j:.0f}"))
        signal = sum(1 for p in k if p.isdigit())        # mounting tabs ("MP") are numbered differently
        flag = "" if err < 0.25 and n >= signal else "   <-- CHECK"
        report.append(f"{ref:5s} {lcsc:10s} {title[:44]:44s} pads {n}/{len(k)}/{len(e)}  "
                      f"turn {t:3d}  offset ({dx:+.2f},{dy:+.2f})  fit {err:.3f} mm{flag}")
    with open(os.path.join(out, "carrier-BOM.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in sorted(bom.items(), key=lambda kv: kv[1][0]):
            w.writerow([value, ",".join(refs), fp, lcsc])
    with open(os.path.join(out, "carrier-CPL.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(cpl)
    open(os.path.join(out, "footprint-check.txt"), "w").write("\n".join(report) + "\n")
    print("\n".join(report))

    g = os.path.join(out, "gerbers")
    os.makedirs(g, exist_ok=True)
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers",
                    "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts",
                    "--subtract-soldermask", "-o", g + "/", board_path], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
                    "-o", g + "/", board_path], check=True, stdout=subprocess.DEVNULL)
    with zipfile.ZipFile(os.path.join(out, "carrier-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(g)):
            z.write(os.path.join(g, name), name)
    print(f"BOM lines {len(bom)}, placed parts {len(cpl)}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
