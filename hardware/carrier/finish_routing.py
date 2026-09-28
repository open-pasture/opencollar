"""Finish the carrier's routing: Inky's HeyPCB board brought up to the current schematic.

    uv run python schematic.py      # build/carrier.net, read below
    kicad-python finish_routing.py pcb/heypcb/opencollar-carrier.kicad_pcb pcb/carrier.kicad_pcb

Needs Freerouting 2.4 and a Java 25 runtime in build/tools (gitignored), from
github.com/freerouting/freerouting/releases and api.adoptium.net (see DESIGN-PHASE.md).

HeyPCB's agent (Inky) routed rev A2. Since then the board has changed under it, so this
brings Inky's board up to the schematic and routes what changed:
  1. new parts, values, nets and footprints from build/carrier.net (rev A3: fuel gauge,
     flash, reverse protection, basic-value charger resistors, Pin1Right sockets), new
     parts placed per A3_PARTS;
  2. the charger's passives re-placed beside the U1 pins they serve (CHARGER): packed by
     block, the IN cap and TMR resistor had sat under the chip with their pins on top;
  3. copper cleared wherever it no longer fits (changed nets, re-footprinted sockets, the
     charger block, the new parts); fixed copper at the fine-pitch parts (U1 0.5 mm,
     U6 0.4 mm), so no router has to find its way out of their pins; a GND via at every
     small part's GND pad, so no decoupling cap depends on the pour reaching it;
  4. Freerouting routes what's open around the copper that stayed; a two-layer grid
     router (0.05 mm grid, 45-degree moves, rip-up and reroute) finishes what it can't;
  5. GND stitching, joining any pour piece the routing cut off, stub cleanup, each
     checked with KiCad's own DRC.
It also pulls J1-J4's courtyards and silk back where the sockets butt end to end.
Result: kicad-cli DRC with every severity reports nothing.
"""
import heapq
import math
import os
import sys

import numpy as np
import pcbnew

G = 0.05                      # grid, mm
CLR = 0.15                    # copper clearance
EPS = 0.03                    # grid slack: tracks run between grid points
EDGE_CLR = 0.3
TP_CLR = 0.5                  # vias to bottom test pads: a probe that misses mustn't land on bare copper
TP_TRACK_CLR = 0.25           # tracks to test pads (they're under soldermask)
HOLE_CLR = 0.25               # hole to hole, copper to NPTH
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = 2.5                # mm-equivalent
TURN_COST = 0.3
NECK_W, NECK_R = 0.25, 1.0    # power tracks may narrow to 0.25 mm within 1 mm of U1's pins
NECK = {"U1": 0.25, "U6": 0.2}  # fine-pitch parts and the width tracks may narrow to at their pins
                                # (U6 is 0.4 mm pitch: 0.2 mm leaves 0.2 mm to the next pin)
WIDTH = {"BAT": 0.5, "BAT_PACK": 0.5, "BAT_CELL": 0.5, "CHG_IN": 0.5, "CHG_OUT": 0.5, "SOLAR_A": 0.5, "SOLAR_B": 0.5,
         "3V3": 0.4, "EXT_3V3": 0.4}
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)

mm, nm = pcbnew.ToMM, pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(nm(float(x)), nm(float(y)))


# ---------------------------------------------------------------- geometry

def seg_dist(px, py, ax, ay, bx, by):
    """Distance from points (arrays) to segment a-b."""
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = np.zeros_like(px) if L2 == 0 else np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rect_dist(px, py, cx, cy, w, h, rot):
    a = math.radians(rot)
    c, s = math.cos(a), math.sin(a)
    lx = (px - cx) * c - (py - cy) * s
    ly = (px - cx) * s + (py - cy) * c
    qx, qy = np.abs(lx) - w / 2, np.abs(ly) - h / 2
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)


class Shape:
    """One piece of copper on one or both layers: 'seg' (with width), 'rect' or 'circle'."""

    def __init__(self, item, net, layers, kind, **g):
        self.item, self.net, self.layers, self.kind, self.g = item, net, layers, kind, g

    def bbox(self):
        g = self.g
        if self.kind == "seg":
            r = g["w"] / 2
            return min(g["ax"], g["bx"]) - r, min(g["ay"], g["by"]) - r, max(g["ax"], g["bx"]) + r, max(g["ay"], g["by"]) + r
        if self.kind == "circle":
            return g["x"] - g["r"], g["y"] - g["r"], g["x"] + g["r"], g["y"] + g["r"]
        r = math.hypot(g["w"], g["h"]) / 2
        return g["x"] - r, g["y"] - r, g["x"] + r, g["y"] + r

    def dist(self, px, py):
        """Distance from points to this copper's edge (negative inside)."""
        g = self.g
        if self.kind == "seg":
            return seg_dist(px, py, g["ax"], g["ay"], g["bx"], g["by"]) - g["w"] / 2
        if self.kind == "circle":
            return np.hypot(px - g["x"], py - g["y"]) - g["r"]
        return rect_dist(px, py, g["x"], g["y"], g["w"], g["h"], g["rot"])


def pad_shape(p):
    q, s = p.GetPosition(), p.GetSize()
    layers = tuple(L for L in LAYERS if p.IsOnLayer(L))
    x, y, w, h = mm(q.x), mm(q.y), mm(s.x), mm(s.y)
    if p.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
        return Shape(p, p.GetNetname(), layers, "circle", x=x, y=y, r=w / 2)
    return Shape(p, p.GetNetname(), layers, "rect", x=x, y=y, w=w, h=h, rot=p.GetOrientationDegrees())


def track_shapes(t):
    if t.GetClass() == "PCB_VIA":
        q = t.GetPosition()
        return [Shape(t, t.GetNetname(), LAYERS, "circle", x=mm(q.x), y=mm(q.y), r=mm(t.GetWidth(pcbnew.F_Cu)) / 2)]
    pts = [t.GetStart(), t.GetEnd()]
    if t.GetClass() == "PCB_ARC":
        pts = [t.GetStart(), t.GetMid(), t.GetEnd()]
    w = mm(t.GetWidth())
    return [Shape(t, t.GetNetname(), (t.GetLayer(),), "seg", ax=mm(a.x), ay=mm(a.y), bx=mm(b.x), by=mm(b.y), w=w)
            for a, b in zip(pts, pts[1:])]


def is_tp(p):
    return p.GetParentFootprint().GetReference().startswith("TP")


# ---------------------------------------------------------------- the board model

EDGES = {}


class Board:
    def __init__(self, b):
        self.b = b
        if id(b) not in EDGES:               # read once: SWIG loses the box type after edits
            bb = b.GetBoardEdgesBoundingBox()
            EDGES[id(b)] = (mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetWidth()), mm(bb.GetHeight()))
        x, y, w, h = EDGES[id(b)]
        self.x0, self.y0, self.x1, self.y1 = x, y, x + w, y + h
        self.nx = int((self.x1 - self.x0) / G) + 1
        self.ny = int((self.y1 - self.y0) / G) + 1
        self.X = self.x0 + np.arange(self.nx) * G
        self.Y = self.y0 + np.arange(self.ny) * G
        self.refresh()

    def refresh(self):
        self.shapes = []
        for f in self.b.GetFootprints():
            for p in f.Pads():
                self.shapes.append(pad_shape(p))
        for t in self.b.GetTracks():
            self.shapes.extend(track_shapes(t))
        self.holes = []          # (x, y, r) of every drill
        for f in self.b.GetFootprints():
            for p in f.Pads():
                d = p.GetDrillSize()
                if d.x > 0:
                    q = p.GetPosition()
                    self.holes.append((mm(q.x), mm(q.y), mm(max(d.x, d.y)) / 2, p))
        for t in self.b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                q = t.GetPosition()
                self.holes.append((mm(q.x), mm(q.y), mm(t.GetDrillValue()) / 2, t))

    def cell(self, x, y):
        return int(round((x - self.x0) / G)), int(round((y - self.y0) / G))

    def window(self, box, pad):
        i0 = max(0, int((box[0] - pad - self.x0) / G))
        i1 = min(self.nx, int((box[2] + pad - self.x0) / G) + 2)
        j0 = max(0, int((box[1] - pad - self.y0) / G))
        j1 = min(self.ny, int((box[3] + pad - self.y0) / G) + 2)
        return i0, i1, j0, j1

    def clearance_field(self, net, reach=1.2, ignore=None):
        """Per layer: distance from each grid point to the nearest copper that isn't `net`,
        shrunk by the extra clearance that copper asks for (test pads, NPTH, the edge).
        `ignore(shape)` leaves copper out (for rip-up: tracks that may be moved)."""
        D = {L: np.full((self.ny, self.nx), 9.0, np.float32) for L in LAYERS}
        T = np.full((self.ny, self.nx), 9.0, np.float32)      # distance to test pads
        for s in self.shapes:
            if ignore is not None and ignore(s):
                continue
            if s.net == net and net != "":
                continue
            extra = 0.0
            if isinstance(s.item, pcbnew.PAD):
                if s.item.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    extra = HOLE_CLR - CLR
                    s = Shape(s.item, s.net, LAYERS, s.kind, **s.g)   # a hole blocks both layers
                elif is_tp(s.item):
                    extra = TP_TRACK_CLR - CLR
                    i0, i1, j0, j1 = self.window(s.bbox(), reach + TP_CLR)
                    px, py = np.meshgrid(self.X[i0:i1], self.Y[j0:j1])
                    sub = T[j0:j1, i0:i1]
                    np.minimum(sub, s.dist(px, py), out=sub)
            i0, i1, j0, j1 = self.window(s.bbox(), reach + extra)
            if i0 >= i1 or j0 >= j1:
                continue
            px, py = np.meshgrid(self.X[i0:i1], self.Y[j0:j1])
            d = s.dist(px, py) - extra
            for L in s.layers:
                sub = D[L][j0:j1, i0:i1]
                np.minimum(sub, d, out=sub)
        # board edge
        px, py = np.meshgrid(self.X, self.Y)
        de = np.minimum.reduce([px - self.x0, self.x1 - px, py - self.y0, self.y1 - py]) - (EDGE_CLR - CLR)
        for L in LAYERS:
            np.minimum(D[L], de, out=D[L])
        # drills, for vias
        H = np.full((self.ny, self.nx), 9.0, np.float32)
        for x, y, r, _ in self.holes:
            i0, i1, j0, j1 = self.window((x - r, y - r, x + r, y + r), 1.0)
            px, py = np.meshgrid(self.X[i0:i1], self.Y[j0:j1])
            sub = H[j0:j1, i0:i1]
            np.minimum(sub, np.hypot(px - x, py - y) - r, out=sub)
        # vias keep the full test-pad clearance: fold it into the drill field they check
        np.minimum(H, T - (TP_CLR + VIA_D / 2) + (VIA_DRILL / 2 + HOLE_CLR + EPS) + 0.001, out=H)
        return D, H

    def cells_in(self, s, shrink=0.0):
        """Grid cells inside a copper shape, per layer. On a track, only its two ends: a new
        track then joins it end to end, the way KiCad connects tracks."""
        i0, i1, j0, j1 = self.window(s.bbox(), 0.0)
        px, py = np.meshgrid(self.X[i0:i1], self.Y[j0:j1])
        inside = s.dist(px, py) < -shrink
        if s.kind == "seg":
            g = s.g
            r = g["w"] / 2
            inside &= (np.hypot(px - g["ax"], py - g["ay"]) < r) | (np.hypot(px - g["bx"], py - g["by"]) < r)
        js, is_ = np.nonzero(inside)
        return [(L, j0 + j, i0 + i) for L in s.layers for j, i in zip(js, is_)]


# ---------------------------------------------------------------- connectivity

def islands(bm, net):
    """Groups of copper on `net` that touch each other (pads, tracks, vias)."""
    sh = [s for s in bm.shapes if s.net == net]
    parent = list(range(len(sh)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def anchors(s):
        g = s.g
        if s.kind == "seg":
            return [(g["ax"], g["ay"]), (g["bx"], g["by"])]
        return [(g["x"], g["y"])]

    for i, a in enumerate(sh):
        for j in range(i + 1, len(sh)):
            b = sh[j]
            if not set(a.layers) & set(b.layers):
                continue
            # touching if an anchor of one lies inside the other
            if any(b.dist(np.array([x]), np.array([y]))[0] <= 0.001 for x, y in anchors(a)) or \
               any(a.dist(np.array([x]), np.array([y]))[0] <= 0.001 for x, y in anchors(b)):
                parent[find(i)] = find(j)
    groups = {}
    for i, s in enumerate(sh):
        groups.setdefault(find(i), []).append(s)
    return list(groups.values())


# ---------------------------------------------------------------- router

B_KEEPOUT = None      # box kept free of signals on the bottom layer (solid GND under U1's thermal vias)
B_PENALTY = None      # (box, factor): bottom-layer steps inside `box` cost more, keeping the GND pour whole


DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def route(bm, net, src, dst, w, neck_pts=(), goal_cells=None, start_cells=None, neck_w=NECK_W, ignore=None):
    D, H = bm.clearance_field(net, ignore=ignore)
    need = w / 2 + CLR + EPS
    need_n = neck_w / 2 + CLR + EPS
    ok = {L: D[L] > need for L in LAYERS}
    if B_KEEPOUT and net != "GND":
        i0, i1, j0, j1 = bm.window(B_KEEPOUT, 0.0)
        ok[pcbnew.B_Cu][j0:j1, i0:i1] = False
    narrow = {L: np.zeros_like(ok[L]) for L in LAYERS}
    if neck_pts:
        px, py = np.meshgrid(bm.X, bm.Y)
        near = np.zeros(ok[LAYERS[0]].shape, bool)
        for x, y in neck_pts:
            near |= np.hypot(px - x, py - y) < NECK_R
        for L in LAYERS:
            narrow[L] = near & ~ok[L] & (D[L] > need_n)
    via_ok = (D[pcbnew.F_Cu] > VIA_D / 2 + CLR + EPS) & (D[pcbnew.B_Cu] > VIA_D / 2 + CLR + EPS) & \
             (H > VIA_DRILL / 2 + HOLE_CLR + EPS)
    def passable(L, j, i):
        return ok[L][j, i] or narrow[L][j, i]

    starts = set(c for s in src for c in bm.cells_in(s) if passable(*c))
    if start_cells:
        starts |= {c for c in start_cells if passable(*c)}
    goals = set(c for s in dst for c in bm.cells_in(s) if passable(*c))
    if goal_cells:
        goals |= {c for c in goal_cells if passable(*c)}
    # a new track may start or end on its net's copper, but not run along on top of it
    for sh in bm.shapes:
        if sh.net == net and net != "":
            i0, i1, j0, j1 = bm.window(sh.bbox(), 0.0)
            px, py = np.meshgrid(bm.X[i0:i1], bm.Y[j0:j1])
            inside = sh.dist(px, py) < 0
            for L in sh.layers:
                ok[L][j0:j1, i0:i1] &= ~inside
                narrow[L][j0:j1, i0:i1] &= ~inside
    for L, j, i in starts | goals:
        ok[L][j, i] = True
    if not starts or not goals:
        return None
    gx = np.array([c[2] for c in goals]); gy = np.array([c[1] for c in goals])
    gb = (gx.min(), gy.min(), gx.max(), gy.max())

    def h(j, i):
        dx = max(gb[0] - i, 0, i - gb[2]); dy = max(gb[1] - j, 0, j - gb[3])
        return G * (max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy))

    pen = {L: None for L in LAYERS}
    if B_PENALTY and net != "GND":
        (bx0, by0, bx1, by1), factor = B_PENALTY
        p = np.ones((bm.ny, bm.nx), np.float32)
        i0, i1, j0, j1 = bm.window((bx0, by0, bx1, by1), 0.0)
        p[j0:j1, i0:i1] = factor
        pen[pcbnew.B_Cu] = p
    # state: (layer, j, i); the direction we arrived from sets the turn cost
    openq, best, came, dirs = [], {}, {}, {}
    for st in starts:
        best[st] = 0.0
        dirs[st] = -1
        heapq.heappush(openq, (h(st[1], st[2]), 0.0, st))
    end = None
    n = 0
    while openq:
        f, g, st = heapq.heappop(openq)
        if g > best.get(st, 1e9):
            continue
        if st in goals:
            end = st
            break
        n += 1
        if n > 4_000_000:
            print(f"    gave up after {n} steps")
            break
        L, j, i = st
        d = dirs[st]
        for k, (di, dj) in enumerate(DIRS):
            i2, j2 = i + di, j + dj
            if not (0 <= i2 < bm.nx and 0 <= j2 < bm.ny) or not passable(L, j2, i2):
                continue
            st2 = (L, j2, i2)
            step = G * (1.4142 if di and dj else 1.0)
            if pen[L] is not None:
                step *= pen[L][j2, i2]
            g2 = g + step + (TURN_COST if d not in (-1, k) else 0.0)
            if g2 < best.get(st2, 1e9):
                best[st2] = g2; came[st2] = st; dirs[st2] = k
                heapq.heappush(openq, (g2 + h(j2, i2), g2, st2))
        if via_ok[j, i]:
            for L2 in LAYERS:
                st2 = (L2, j, i)
                if L2 != L and passable(L2, j, i):
                    g2 = g + VIA_COST
                    if g2 < best.get(st2, 1e9):
                        best[st2] = g2; came[st2] = st; dirs[st2] = -1
                        heapq.heappush(openq, (g2 + h(j, i), g2, st2))
    if end is None:
        return None
    path = [end]
    while path[-1] in came:
        path.append(came[path[-1]])
    path.reverse()
    return [(L, j, i, bool(narrow[L][j, i] and not ok[L][j, i])) for (L, j, i) in path]


def commit(bm, net, path, w, neck_w=NECK_W):
    """Turn a grid path into tracks and vias: one segment per straight run."""
    b = bm.b
    ni = b.FindNet(net)
    xy = lambda j, i: (bm.x0 + i * G, bm.y0 + j * G)

    def add_track(p0, p1, L, width):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*p0)); t.SetEnd(V(*p1)); t.SetWidth(nm(width)); t.SetLayer(L); t.SetNet(ni)
        b.Add(t)

    def add_via(p):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(V(*p)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetWidth(nm(VIA_D)); v.SetDrill(nm(VIA_DRILL)); v.SetNet(ni)
        b.Add(v)

    run = [path[0]]
    for prev, cur in zip(path, path[1:]):
        if cur[0] != prev[0]:                   # layer change
            if len(run) > 1:
                emit(run, add_track, xy, w, neck_w)
            add_via(xy(cur[1], cur[2]))
            run = [cur]
            continue
        run.append(cur)
    if len(run) > 1:
        emit(run, add_track, xy, w, neck_w)


def emit(run, add_track, xy, w, neck_w=NECK_W):
    """Split a same-layer run into straight pieces. A piece is narrow if any of its cells
    is; the boundary cell at a width change goes to the narrow piece, so wide pieces
    only cover cells cleared for the full width."""
    L, n = run[0][0], len(run)
    cuts = {0, n - 1}
    for k in range(1, n - 1):
        d0 = (run[k][1] - run[k - 1][1], run[k][2] - run[k - 1][2])
        d1 = (run[k + 1][1] - run[k][1], run[k + 1][2] - run[k][2])
        if d0 != d1:
            cuts.add(k)
    for k in range(n - 1):
        if run[k][3] and not run[k + 1][3]:
            cuts.add(k + 1)
        elif not run[k][3] and run[k + 1][3]:
            cuts.add(k)
    cuts = sorted(cuts)
    for a, c in zip(cuts, cuts[1:]):
        width = neck_w if any(run[k][3] for k in range(a, c + 1)) else w
        add_track(xy(run[a][1], run[a][2]), xy(run[c][1], run[c][2]), L, width)


# ---------------------------------------------------------------- edits

def u1_fingers(b):
    """Fixed copper at U1 (0.5 mm pitch QFN) that the router then connects to:
    - BAT (pins 2, 3) and CHG_OUT (10, 11): 0.25 mm fingers to a 0.4 mm bar just past the
      pin tips, so the 0.5 mm tracks never come near the neighbouring pins;
    - CHG_IN (13): a 0.25 mm finger out past the pin tip;
    - GND (5, 8): straight onto the exposed pad."""
    u1 = b.FindFootprintByReference("U1")
    pads = {p.GetNumber(): p for p in u1.Pads()}
    at = lambda n: (mm(pads[n].GetPosition().x), mm(pads[n].GetPosition().y))

    def add(p0, p1, w, net):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*p0)); t.SetEnd(V(*p1)); t.SetWidth(nm(w)); t.SetLayer(pcbnew.F_Cu)
        t.SetNet(b.FindNet(net)); t.SetLocked(True)
        b.Add(t)

    for net, pins, dx in (("BAT", ("2", "3"), -1), ("CHG_OUT", ("10", "11"), +1)):
        (px, y0), (_, y1) = at(pins[0]), at(pins[1])
        bar = px + dx * 0.6375
        for y in (y0, y1):
            add((px, y), (bar, y), NECK_W, net)
        add((bar, y0), (bar, y1), 0.4, net)
    x, y = at("13")
    add((x, y), (x, y - 0.7), NECK_W, "CHG_IN")
    ep = pads["17"]
    ey = mm(ep.GetPosition().y) + mm(ep.GetSize().y) / 2 - 0.05
    for n in ("5", "8"):
        x, y = at(n)
        add((x, y), (x, ey), NECK_W, "GND")


def add_like(b, t, p0, p1):
    n = pcbnew.PCB_TRACK(b)
    n.SetStart(p0); n.SetEnd(p1); n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer()); n.SetNet(t.GetNet())
    b.Add(n)


def split_tees(b):
    """Where a track ends on the middle of another track of its net, split that track there,
    so every joint is an end-to-end one (as KiCad draws them) and stubs past a joint can be
    seen and dropped."""
    for _ in range(20):
        tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
        ends = [(t, q) for t in tracks for q in (t.GetStart(), t.GetEnd())]
        done = False
        for t in tracks:
            a, c = t.GetStart(), t.GetEnd()
            ax, ay, cx, cy = mm(a.x), mm(a.y), mm(c.x), mm(c.y)
            L2 = (cx - ax) ** 2 + (cy - ay) ** 2
            if L2 < 1e-6:
                continue
            for u, q in ends:
                if u is t or u.GetNetname() != t.GetNetname() or u.GetLayer() != t.GetLayer():
                    continue
                px, py = mm(q.x), mm(q.y)
                k = ((px - ax) * (cx - ax) + (py - ay) * (cy - ay)) / L2
                if not 0.0 < k < 1.0:
                    continue
                jx, jy = ax + k * (cx - ax), ay + k * (cy - ay)
                if math.hypot(px - jx, py - jy) > mm(t.GetWidth()) / 2:
                    continue
                if min(math.hypot(px - ax, py - ay), math.hypot(px - cx, py - cy)) < 0.01:
                    continue
                end = t.GetEnd()
                t.SetEnd(V(jx, jy))
                add_like(b, t, V(jx, jy), end)          # fresh tracks: Duplicate() keeps the UUID
                if math.hypot(px - jx, py - jy) > 0.001:
                    add_like(b, u, q, V(jx, jy))
                done = True
                break
            if done:
                break
        if not done:
            return


def drop_dangling(b):
    """Remove tracks with an end that touches nothing, and vias with copper on only one
    layer (left over from rip-ups). GND vias stay: the pours hold them."""
    for t in list(b.GetTracks()):                    # zero-length leftovers
        if t.GetClass() == "PCB_TRACK" and t.GetStart() == t.GetEnd():
            b.Delete(t)
    split_tees(b)
    uid = lambda o: o.m_Uuid.AsString()      # SWIG hands out a new wrapper each time: `is` won't do
    while True:
        bm = Board(b)
        for sh in bm.shapes:
            sh.uid = uid(sh.item)
        dead = []
        for t in b.GetTracks():
            net, me = t.GetNetname(), uid(t)
            if t.GetClass() == "PCB_VIA":
                if net == "GND":
                    continue
                q = t.GetPosition()
                x, y = np.array([mm(q.x)]), np.array([mm(q.y)])
                r = mm(t.GetWidth(pcbnew.F_Cu)) / 2
                layers = [L for L in LAYERS if any(s.uid != me and s.net == net and L in s.layers
                                                   and s.dist(x, y)[0] <= r for s in bm.shapes)]
                if len(layers) < 2:
                    dead.append(t)
                continue
            if t.GetClass() != "PCB_TRACK":
                continue
            for q in (t.GetStart(), t.GetEnd()):
                x, y = np.array([mm(q.x)]), np.array([mm(q.y)])
                touch = [s for s in bm.shapes if s.uid != me and s.net == net
                         and t.GetLayer() in s.layers and s.dist(x, y)[0] <= 0.001]
                if not touch:
                    dead.append(t)
                    break
        if not dead:
            return
        for t in dead:
            b.Delete(t)


def connect_all(b, nets):
    failed = []
    for net in nets:
        w = WIDTH.get(net, 0.25)
        for attempt in range(40):
            bm = Board(b)
            isl = islands(bm, net)
            if len(isl) < 2:
                print(f"  {net}: connected")
                break
            # join the island holding the most pads to its nearest neighbour
            isl.sort(key=lambda g: -sum(isinstance(s.item, pcbnew.PAD) for s in g))
            main, rest = isl[0], isl[1:]
            fine = [(s.g["x"], s.g["y"], NECK[r]) for g in isl for s in g if isinstance(s.item, pcbnew.PAD)
                    for r in [s.item.GetParentFootprint().GetReference()] if r in NECK]
            neck = [(x, y) for x, y, _ in fine]
            neck_w = min([n for _, _, n in fine], default=NECK_W)
            path = None
            for width in ([w] + [x for x in (0.4, 0.3, 0.25) if x < w]):
                path = route(bm, net, main, [s for g in rest for s in g], width, neck, neck_w=neck_w)
                if path:
                    break
            if not path:
                print(f"  {net}: NO PATH for {len(rest)} island(s)")
                failed.append(net)
                break
            commit(bm, net, path, width, neck_w)
            vias = sum(1 for a, c in zip(path, path[1:]) if a[0] != c[0])
            print(f"  {net}: routed {len(path)} steps at {width} mm, {vias} via(s)")
    return failed


def movable(net):
    """Copper a rip-up may move for `net`: other signals' tracks and vias, never GND, pads,
    or the fixed fan-outs."""
    return lambda s: (s.item.GetClass() in ("PCB_TRACK", "PCB_VIA", "PCB_ARC") and s.net not in (net, "GND", "")
                      and not s.item.IsLocked())


def rip_for(b, bm, net, path, w):
    """Delete the movable copper within clearance of `path`; return the nets it belonged to."""
    need = w / 2 + CLR + EPS
    by_layer = {}
    for L, j, i, _ in path:
        by_layer.setdefault(L, []).append((bm.x0 + i * G, bm.y0 + j * G))
    hit, uids = set(), set()
    mov = movable(net)
    for sh in bm.shapes:
        if not mov(sh):
            continue
        for L in sh.layers:
            pts = by_layer.get(L)
            if not pts:
                continue
            px = np.array([p[0] for p in pts]); py = np.array([p[1] for p in pts])
            if float(sh.dist(px, py).min()) < need:
                hit.add(sh.net)
                uids.add(sh.item.m_Uuid.AsString())
                break
    for t in list(b.GetTracks()):
        if t.m_Uuid.AsString() in uids:
            b.Delete(t)
    return hit


def rip_reroute(b, nets, depth=2):
    """Route nets the plain router couldn't: find each one's path as if other signals'
    tracks weren't there, rip up what's in the way, route it, then route the ripped nets
    again (rip-up allowed `depth` levels down). Returns the nets still open."""
    left = []
    for net in nets:
        w = WIDTH.get(net, 0.25)
        for _ in range(10):
            bm = Board(b)
            isl = islands(bm, net)
            if len(isl) < 2:
                break
            isl.sort(key=lambda g: -sum(isinstance(s.item, pcbnew.PAD) for s in g))
            main, rest = isl[0], [s for g in isl[1:] for s in g]
            fine = [(s.g["x"], s.g["y"], NECK[r]) for g in isl for s in g if isinstance(s.item, pcbnew.PAD)
                    for r in [s.item.GetParentFootprint().GetReference()] if r in NECK]
            neck, neck_w = [(x, y) for x, y, _ in fine], min([n for _, _, n in fine], default=NECK_W)
            path = None
            for width in ([w] + [x for x in (0.4, 0.3, 0.25) if x < w]):
                path = route(bm, net, main, rest, width, neck, neck_w=neck_w, ignore=movable(net))
                if path:
                    break
            if not path:
                break
            ripped = rip_for(b, bm, net, path, width)
            bm = Board(b)
            path = route(bm, net, main, rest, width, neck, neck_w=neck_w)
            if not path:
                break
            commit(bm, net, path, width, neck_w)
            print(f"  {net}: routed by ripping up {sorted(ripped)}")
            if ripped:
                again = connect_all(b, sorted(ripped))
                if again and depth > 0:
                    again = rip_reroute(b, again, depth - 1)
                left += again
        else:
            pass
        if len(islands(Board(b), net)) > 1:
            left.append(net)
    return sorted(set(left))


def refill(b):
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def gnd_via(b, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetWidth(nm(VIA_D)); v.SetDrill(nm(VIA_DRILL)); v.SetNet(b.FindNet("GND"))
    b.Add(v)


class Spots:
    """Where a GND via can go: clear of other copper, holes, test pads and parts, with
    both pours around it."""

    def __init__(self, b):
        self.b = b
        self.bm = Board(b)
        self.D, self.H = self.bm.clearance_field("GND")
        self.fills = {L: [z.GetFilledPolysList(L) for z in b.Zones() if z.GetNetname() == "GND" and z.IsOnLayer(L)]
                      for L in LAYERS}
        self.yards = [f.GetCourtyard(L) for f in b.GetFootprints() for L in LAYERS
                      if not f.GetReference().startswith(("TP", "H")) and f.GetCourtyard(L).OutlineCount()]

    def ok(self, x, y):
        bm = self.bm
        i, j = bm.cell(x, y)
        if not (0 <= i < bm.nx and 0 <= j < bm.ny):
            return False
        need = VIA_D / 2 + CLR + 0.05
        if not (self.D[pcbnew.F_Cu][j, i] > need and self.D[pcbnew.B_Cu][j, i] > need
                and self.H[j, i] > VIA_DRILL / 2 + HOLE_CLR + 0.05):
            return False
        r = VIA_D / 2 + 0.05
        ring = [V(x + r * math.cos(a), y + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
        if not all(any(f.Contains(p) for f in self.fills[L]) for L in LAYERS for p in ring):
            return False
        return not any(yd.Contains(V(x, y)) for yd in self.yards)


def gnd_islands(b):
    """GND as the fill sees it: pour pieces on each layer, joined wherever a group of GND
    copper (pads, tracks, vias that touch) reaches into them. Returns (groups of piece
    indices, pieces)."""
    pieces = []
    for z in b.Zones():
        if z.GetNetname() != "GND":
            continue
        for L in LAYERS:
            if z.IsOnLayer(L):
                f = z.GetFilledPolysList(L)
                pieces += [(L, f, k) for k in range(f.OutlineCount())]
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def samples(sh):
        g = sh.g
        if sh.kind == "seg":
            n = max(2, int(math.hypot(g["bx"] - g["ax"], g["by"] - g["ay"]) / 0.2))
            return [(g["ax"] + (g["bx"] - g["ax"]) * t, g["ay"] + (g["by"] - g["ay"]) * t) for t in np.linspace(0, 1, n)]
        r = g["r"] if sh.kind == "circle" else max(g["w"], g["h"]) / 2
        return [(g["x"], g["y"])] + [(g["x"] + (r + 0.12) * math.cos(a), g["y"] + (r + 0.12) * math.sin(a))
                                     for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]

    for grp in islands(Board(b), "GND"):
        hit = set()
        for sh in grp:
            for x, y in samples(sh):
                p = V(x, y)
                for k, (L, f, idx) in enumerate(pieces):
                    if L in sh.layers and k not in hit and f.Contains(p, idx):
                        hit.add(k)
        hit = sorted(hit)
        for k in hit[1:]:
            parent[find(k)] = find(hit[0])
    groups = {}
    for k in range(len(pieces)):
        groups.setdefault(find(k), []).append(k)
    return list(groups.values()), pieces


def join_gnd(b, step=0.25, rounds=200):
    """Add GND vias until every pour piece is joined to the rest."""
    added = 0
    for _ in range(rounds):
        refill(b)
        groups, pieces = gnd_islands(b)
        area = lambda g: sum(pieces[k][1].Outline(pieces[k][2]).Area() for k in g) / 1e12
        groups.sort(key=area, reverse=True)
        # slivers the fill kept are attached to a pad; the sampling above can miss them
        groups = groups[:1] + [g for g in groups[1:] if area(g) >= 1.0]
        if len(groups) == 1:
            return added
        sp = Spots(b)
        placed = False
        for g in groups[1:]:
            for k in g:
                L, f, idx = pieces[k]
                bb = f.Outline(idx).BBox()
                for y in np.arange(mm(bb.GetY()), mm(bb.GetY() + bb.GetHeight()), step):
                    for x in np.arange(mm(bb.GetX()), mm(bb.GetX() + bb.GetWidth()), step):
                        if f.Contains(V(x, y), idx) and sp.ok(x, y):
                            gnd_via(b, x, y)
                            added += 1
                            placed = True
                            break
                    if placed:
                        break
                if placed:
                    break
            if placed:
                break
        if not placed:
            # no room for a via: route the stranded pads to a via on the main pour instead
            if not route_stranded_gnd(b, groups, pieces):
                for g in groups[1:]:
                    for k in g:
                        L, f, idx = pieces[k]
                        bb = f.Outline(idx).BBox()
                        print(f"  GND: unjoined {b.GetLayerName(L)} piece {f.Outline(idx).Area() / 1e12:.1f} mm2 at "
                              f"({mm(bb.GetX()):.1f}, {mm(bb.GetY()):.1f}) size {mm(bb.GetWidth()):.1f} x {mm(bb.GetHeight()):.1f}")
                return added
    return added


def route_stranded_gnd(b, groups, pieces):
    bm = Board(b)
    main = groups[0]
    in_group = lambda x, y, g: any(pieces[k][1].Contains(V(x, y), pieces[k][2]) for k in g)
    gnd = [s for s in bm.shapes if s.net == "GND"]
    vias = [s for s in gnd if s.item.GetClass() == "PCB_VIA" and
            any(in_group(s.g["x"] + dx, s.g["y"] + dy, main) for dx, dy in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)))]
    def lattice(ks):
        """Grid cells well inside these pour pieces, on a 0.5 mm lattice."""
        cells = set()
        for k in ks:
            L, f, idx = pieces[k]
            bb = f.Outline(idx).BBox()
            for y in np.arange(mm(bb.GetY()), mm(bb.GetY() + bb.GetHeight()), 0.5):
                for x in np.arange(mm(bb.GetX()), mm(bb.GetX() + bb.GetWidth()), 0.5):
                    if all(f.Contains(V(x + dx, y + dy), idx) for dx, dy in ((0, 0), (0.3, 0), (-0.3, 0), (0, 0.3), (0, -0.3))):
                        i, j = bm.cell(x, y)
                        cells.add((L, j, i))
        return cells

    main_cells = lattice(main)
    for g in groups[1:]:
        # from inside the stranded piece to anywhere well inside the main pour
        starts = lattice(g)
        if not starts:
            continue
        size = sum(pieces[k][1].Outline(pieces[k][2]).Area() for k in g) / 1e12
        for width in (0.4, 0.25):
            path = route(bm, "GND", [], [], width, goal_cells=main_cells, start_cells=starts)
            if path:
                commit(bm, "GND", path, width)
                print(f"  GND: joined a {size:.1f} mm2 piece at {width} mm")
                return True
        # walled in: rip up the signals in the way, join it, route them again
        path = route(bm, "GND", [], [], 0.25, goal_cells=main_cells, start_cells=starts, ignore=movable("GND"))
        if path:
            ripped = rip_for(b, bm, "GND", path, 0.25)
            bm2 = Board(b)
            path = route(bm2, "GND", [], [], 0.25, goal_cells=main_cells, start_cells=starts)
            if path:
                commit(bm2, "GND", path, 0.25)
                again = connect_all(b, sorted(ripped))
                if again:
                    again = rip_reroute(b, again)
                print(f"  GND: joined a {size:.1f} mm2 piece by ripping up {sorted(ripped)}; still open: {again or 'none'}")
                return True
    return False


def stitch(b, pitch=2.5):
    """GND vias on a grid wherever both pours have room."""
    sp = Spots(b)
    placed = 0
    for y in np.arange(sp.bm.y0 + 1.25, sp.bm.y1 - 1.0, pitch):
        for x in np.arange(sp.bm.x0 + 1.25, sp.bm.x1 - 1.0, pitch):
            if sp.ok(x, y):
                gnd_via(b, x, y)
                placed += 1
    return placed


def u6_fingers(b):
    """Fixed copper at the fuel gauge's 0.4 mm-pitch top row (0.2 mm tracks leave 0.2 mm to
    the next pin), so no router has to find its way out of it: REG straight up into C10;
    the CSPH Kelvin line up, over the two GND pins, down the channel along the board edge
    and into R24's system-side pad; ALRT up and into R25; SDA and SCL out to the left."""
    u6 = b.FindFootprintByReference("U6")
    pads = {p.GetNumber(): p for p in u6.Pads()}
    at = lambda p: (mm(p.GetPosition().x), mm(p.GetPosition().y))
    c10 = {p.GetNumber(): p for p in b.FindFootprintByReference("C10").Pads()}
    r24 = {p.GetNumber(): p for p in b.FindFootprintByReference("R24").Pads()}

    def run(pts, net):
        for p0, p1 in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(V(*p0)); t.SetEnd(V(*p1)); t.SetWidth(nm(0.2)); t.SetLayer(pcbnew.F_Cu)
            t.SetNet(b.FindNet(net)); t.SetLocked(True)
            b.Add(t)

    (rx, ry), (cx, cy) = at(pads["11"]), at(c10["1"])
    run([(rx, ry), (rx, cy)], "FG_REG")
    (sx, sy), (kx, ky) = at(pads["10"]), at(r24["2"])
    tip = ry - mm(pads["10"].GetBoundingBox().GetHeight()) / 2      # top edge of the pin row
    c10_bottom = cy + mm(c10["1"].GetBoundingBox().GetHeight()) / 2
    y = (tip + c10_bottom) / 2                                        # midway: clear of both
    edge_x = at(pads["8"])[0] + 0.6
    run([(sx, sy), (sx, y), (edge_x, y), (edge_x, ky - 0.4), (kx + 0.3, ky)], "BAT")
    # ALRT up between SDA and REG, then left into R25; SDA and SCL left under R25
    r25 = {p.GetNumber(): p for p in b.FindFootprintByReference("R25").Pads()}
    (ax, ay), (px, py) = at(pads["12"]), at(r25["1"])
    run([(ax, ay), (ax, py + 0.35), (px + 0.2, py + 0.35)], "FG_ALRT")
    (dx, dy), (qx, qy) = at(pads["13"]), at(pads["14"])
    r25_bottom = py + mm(r25["1"].GetBoundingBox().GetHeight()) / 2
    run([(dx, dy), (dx, r25_bottom + 0.45), (158.9, r25_bottom + 0.45)], "I2C_SDA")
    run([(qx, qy), (qx, r25_bottom + 0.85), (159.4, r25_bottom + 0.85)], "I2C_SCL")


def u6_ground(b):
    """The fuel gauge's GND and CSPL pins go straight onto its exposed pad, which gets two
    vias to the bottom pour, so no GND via has to sit in the channel along the board edge
    that the CSPH sense line uses."""
    u6 = b.FindFootprintByReference("U6")
    pads = {p.GetNumber(): p for p in u6.Pads()}
    ep = pads["15"]
    ec = ep.GetPosition()
    ex, ey = mm(ec.x), mm(ec.y)
    a = math.radians(u6.GetOrientationDegrees())
    bb = ep.GetBoundingBox()
    x0, y0 = mm(bb.GetX()), mm(bb.GetY())
    x1, y1 = x0 + mm(bb.GetWidth()), y0 + mm(bb.GetHeight())
    for n in ("8", "9"):
        q = pads[n].GetPosition()
        qx, qy = mm(q.x), mm(q.y)
        # straight across onto the pad, square to the pin row, clear of the next pin
        tx = qx if x0 - 0.15 <= qx <= x1 + 0.15 else min(max(qx, x0 + 0.25), x1 - 0.25)
        ty = qy if y0 - 0.15 <= qy <= y1 + 0.15 else min(max(qy, y0 + 0.25), y1 - 0.25)
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(q)
        t.SetEnd(V(tx, ty))
        t.SetWidth(nm(0.2)); t.SetLayer(pcbnew.F_Cu); t.SetNet(ep.GetNet()); t.SetLocked(True)
        b.Add(t)
    for d in (-0.5, 0.5):                       # along the pad's long side
        x, y = ex + d * math.sin(a), ey + d * math.cos(a)
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(V(x, y)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetWidth(nm(VIA_D)); v.SetDrill(nm(VIA_DRILL))
        v.SetNet(ep.GetNet()); v.SetLocked(True)
        b.Add(v)


def rip_box(b, box, keep=("GND",)):
    """Remove every track and via with an end inside `box` (x0, y0, x1, y1), except on `keep`.
    The stubs left outside become islands for the router to reconnect; the unused ones
    are dropped once routing is done. Returns the nets touched."""
    x0, y0, x1, y1 = box
    inside = lambda q: x0 <= mm(q.x) <= x1 and y0 <= mm(q.y) <= y1
    nets = set()
    for t in list(b.GetTracks()):
        if t.GetNetname() in keep:
            continue
        ends = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        if any(inside(q) for q in ends):
            nets.add(t.GetNetname())
            b.Delete(t)
    return nets


def drop_gnd_vias(b, box, keep_near=(152.0, 119.0, 0.8)):
    """Old GND vias in the block sat beside parts that have since moved; the thermal vias
    in U1's pad stay."""
    x0, y0, x1, y1 = box
    kx, ky, kr = keep_near
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND":
            x, y = mm(t.GetPosition().x), mm(t.GetPosition().y)
            if x0 <= x <= x1 and y0 <= y <= y1 and math.hypot(x - kx, y - ky) > kr:
                b.Delete(t)


def drop_gnd_tracks(b, box):
    """GND tracks near U1 duplicate the pours on both layers and wall pins in; the pours
    (and the vias, which stay) make those connections instead."""
    x0, y0, x1, y1 = box
    inside = lambda q: x0 <= mm(q.x) <= x1 and y0 <= mm(q.y) <= y1
    for t in list(b.GetTracks()):
        if t.GetNetname() == "GND" and t.GetClass() == "PCB_TRACK" and (inside(t.GetStart()) or inside(t.GetEnd())):
            b.Delete(t)


def reserve_gnd_vias(b, box=None, near=1.5):
    """GND pads of passives and ICs get a via at the pad, placed before signals are routed
    so they route around it instead of walling the pad in. In `box`: every GND pad left
    with nothing attached. Board-wide (box None): every such pad with no GND via within
    `near` mm, so no decoupling cap depends on the pour reaching it."""
    bm = Board(b)
    D, H = bm.clearance_field("GND")
    need = VIA_D / 2 + CLR + 0.05
    vias = [(s.g["x"], s.g["y"]) for s in bm.shapes if s.net == "GND" and s.item.GetClass() == "PCB_VIA"]
    if box is None:
        cands = [s for s in bm.shapes if s.net == "GND" and isinstance(s.item, pcbnew.PAD) and s.kind != "seg"
                 and s.item.GetParentFootprint().GetReference()[0] in "RCUQD"
                 and all(math.hypot(s.g["x"] - x, s.g["y"] - y) > near for x, y in vias)]
    else:
        x0, y0, x1, y1 = box
        cands = [grp[0] for grp in islands(bm, "GND") if len(grp) == 1 and isinstance(grp[0].item, pcbnew.PAD)
                 and x0 <= grp[0].g["x"] <= x1 and y0 <= grp[0].g["y"] <= y1]
    for sh in cands:
        p = sh.item
        if p.GetParentFootprint().GetReference() in ("U1", "U6") or p.GetDrillSize().x > 0 or \
                p.GetParentFootprint().IsDNP() and box is None:
            continue
        g = sh.g
        if sh.kind == "circle":
            g = dict(g, w=2 * g["r"], h=2 * g["r"], rot=0)
        hw, hh = (g["w"] / 2, g["h"] / 2) if int(round(g["rot"])) % 180 == 0 else (g["h"] / 2, g["w"] / 2)
        for dx, dy in ((0, hh + 0.25), (0, -hh - 0.25), (hw + 0.25, 0), (-hw - 0.25, 0),
                       (hw, hh + 0.2), (-hw, hh + 0.2), (hw, -hh - 0.2), (-hw, -hh - 0.2)):
            i, j = bm.cell(g["x"] + dx, g["y"] + dy)
            if D[pcbnew.F_Cu][j, i] > need and D[pcbnew.B_Cu][j, i] > need and H[j, i] > VIA_DRILL / 2 + HOLE_CLR + 0.05:
                x, y = bm.x0 + i * G, bm.y0 + j * G
                gnd_via(b, x, y)
                t = pcbnew.PCB_TRACK(b)             # tie it to the pad centre
                t.SetStart(p.GetPosition()); t.SetEnd(V(x, y)); t.SetWidth(nm(0.4)); t.SetLayer(pcbnew.F_Cu)
                t.SetNet(b.FindNet("GND"))
                b.Add(t)
                print(f"  GND via for {p.GetParentFootprint().GetReference()}.{p.GetNumber()}")
                bm = Board(b)
                D, H = bm.clearance_field("GND")
                break


POWER = ["CHG_IN", "BAT_PACK", "BAT_CELL", "BAT", "CHG_OUT", "SOLAR_A", "SOLAR_B", "3V3", "EXT_3V3"]


# The charger's passives, each beside the U1 pin it serves (board mm, degrees). U1's pins:
# left TS, BAT, BAT, CE; bottom GND, EN1, PGOOD, GND; right STAT, OUT, OUT, ILIM;
# top IN, TMR, -, ISET.
CHARGER = {
    "R5": (147.9, 115.9, 180),   # TS 10 k (not fitted), beside C1: shares its TS and GND
    "C2": (153.8, 115.1, 90),    # IN 10 uF, above pin 13
    "R4": (152.0, 115.3, 90),    # TMR, above pin 14
    "R2": (150.4, 115.3, 90),    # ISET, above pin 16
    "C1": (147.9, 117.6, 180),   # TS filter, left of pin 1
    "C4": (148.1, 119.6, 180),   # BAT 10 uF, left of pins 2-3
    "R6": (150.2, 123.0, 270),   # CE pull-down, below pin 4
    "R1": (151.9, 123.0, 90),    # EN1 pull-up, below pin 6
    "R8": (153.6, 123.0, 270),   # PGOOD pull-up, below pin 7
    "R3": (156.3, 117.1, 0),     # ILIM, right of pin 12
    "C3": (155.9, 119.0, 0),     # OUT 10 uF, right of pins 10-11
    "R7": (155.9, 120.9, 0),     # STAT pull-up, right of pin 9
}
CHARGER_BOX = (145.0, 111.0, 158.6, 126.0)


# Rev A3 additions (fuel gauge, flash, reverse protection; schematic.py battery_path, flash).
# Board mm, degrees. The flash sits in the free board under the MAX-M10S; the battery
# path goes in the edge column between H3 and H4, on the way from the harness to the
# charger and beside the M10S's I2C socket.
A3_PARTS = {
    "U7": (136.0, 125.0, 0),     # W25Q128 flash
    "C12": (141.5, 123.3, 90),   # its 0.1 uF
    "R26": (141.5, 126.6, 90),   # /CS pull-up
    "R25": (160.0, 110.9, 90),   # ALRT pull-up, left: ALRT, SDA, SCL all leave U6 to the left
    "C10": (162.25, 111.25, 90),  # REG 0.47 uF, straight above REG
    "U6": (161.8, 115.05, 90),    # MAX17260: I2C, REG, ALRT up; CSN, BATT down to R24; CSPH by the edge
    "C11": (159.75, 121.3, 90),   # BATT 0.1 uF, beside R24
    "R24": (161.8, 121.3, 90),   # 10 mOhm sense
    "Q1": (161.8, 124.95, 0),    # AO3401A
}
A3_BOXES = [(131.0, 121.3, 143.0, 128.5), (158.9, 108.9, 164.7, 127.5)]
FP_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"


def read_netlist(path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from netlist_to_pcb import child, sexp, val
    root = sexp(open(path).read())
    comps = {}
    for c in child(root, "components")[1:]:
        if isinstance(c, list) and c[0] == "comp":
            fields = {}
            fl = child(c, "fields")
            for f in (fl[1:] if fl else []):
                if isinstance(f, list) and f[0] == "field":
                    fields[val(f, "name")] = f[-1] if isinstance(f[-1], str) else ""
            comps[val(c, "ref")] = dict(value=val(c, "value"), fp=val(c, "footprint"), fields=fields)
    nets = []
    for n in child(root, "nets")[1:]:
        if isinstance(n, list) and n[0] == "net":
            nets.append((val(n, "name"), [(val(x, "ref"), val(x, "pin")) for x in n[1:]
                                          if isinstance(x, list) and x[0] == "node"]))
    return comps, nets


def apply_netlist(b, path):
    """Bring the board up to the schematic: add parts it lacks (placed per A3_PARTS),
    update values and BOM fields, and give every pad its net. Returns the nets whose
    pads changed."""
    comps, nets = read_netlist(path)
    have = {f.GetReference(): f for f in b.GetFootprints()}
    swapped = []
    for ref, c in comps.items():
        f = have.get(ref)
        if f is not None and str(f.GetFPID().GetLibItemName()) != c["fp"].split(":")[1]:
            # footprint changed in the schematic (the sockets' Pin1Left -> Pin1Right): same
            # place, same reference, new pads; its copper gets routed again
            lib, name = c["fp"].split(":")
            g = pcbnew.FootprintLoad(os.path.join(FP_DIR, lib + ".pretty"), name)
            g.SetReference(ref)
            g.SetPosition(f.GetPosition())
            g.SetOrientationDegrees(f.GetOrientationDegrees())
            g.Reference().SetVisible(f.Reference().IsVisible())
            g.Reference().SetTextSize(f.Reference().GetTextSize())
            g.Reference().SetTextThickness(f.Reference().GetTextThickness())
            g.Reference().SetPosition(f.Reference().GetPosition())
            b.Delete(f)
            b.Add(g)
            have[ref] = f = g
            swapped.append(ref)
        if f is None:
            lib, name = c["fp"].split(":")
            f = pcbnew.FootprintLoad(os.path.join(FP_DIR, lib + ".pretty"), name)
            f.SetReference(ref)
            b.Add(f)
            x, y, rot = A3_PARTS[ref]
            f.SetOrientationDegrees(rot)
            f.SetPosition(V(x, y))
            f.Reference().SetVisible(ref == "U7")   # the edge column has no room for labels
            f.Reference().SetTextSize(pcbnew.VECTOR2I(nm(0.8), nm(0.8)))
            f.Reference().SetTextThickness(nm(0.12))
            have[ref] = f
        f.SetValue(c["value"])
        for k in ("LCSC", "MPN"):
            if k in c["fields"]:
                f.SetField(k, c["fields"][k])
                f.GetField(k).SetVisible(False)
    pin_net = {(r, p): n for n, nodes in nets for r, p in nodes}
    netinfo = {}
    changed = set()
    for name in {n for n, _ in nets}:
        ni = b.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(b, name)
            b.Add(ni)
        netinfo[name] = ni
    for ref, f in have.items():
        for pad in f.Pads():
            if not pad.GetNumber():
                continue
            want = pin_net.get((ref, pad.GetNumber()), "")
            if pad.GetNetname() != want:
                changed |= {pad.GetNetname(), want}
                if want:
                    pad.SetNet(netinfo[want])
                else:
                    pad.SetNetCode(0)
    changed.discard("")
    return changed, swapped


def retitle(b, old="rev A2", new="rev A3"):
    for d in b.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and old in d.GetText():
            d.SetText(d.GetText().replace(old, new))



def place_charger(b):
    for ref, (x, y, rot) in CHARGER.items():
        f = b.FindFootprintByReference(ref)
        f.SetOrientationDegrees(rot)
        f.SetPosition(V(x, y))


def butted_sockets(b, pairs=(("J1", "J2"), ("J3", "J4"))):
    """J1+J2 and J3+J4 are 1x10 sockets butted end to end into the Kit's two 1x20 rows, so
    their bodies touch by design. Pull each courtyard back to the joint and drop the silk
    within 1 mm of it (end lines, and J2/J4's pin-1 marks, which would sit mid-row)."""
    work = []                     # read everything before editing: SWIG loses its types after edits
    for a, c in pairs:
        fa, fc = b.FindFootprintByReference(a), b.FindFootprintByReference(c)
        ya, yc = mm(fa.GetPosition().y), mm(fc.GetPosition().y)
        (up, lo) = (fa, fc) if ya < yc else (fc, fa)
        butt = (ya + yc) / 2
        for f, edge in ((up, butt - 0.01), (lo, butt + 0.01)):
            work.append((f, f is up, butt, edge, [g for g in f.GraphicalItems() if g.GetClass() == "PCB_SHAPE"]))
    drop = []
    for f, is_up, butt, edge, shapes in work:
        for g in shapes:
            L = g.GetLayer()
            if L in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                for get, put in ((g.GetStart, g.SetStart), (g.GetEnd, g.SetEnd)):
                    q = get()
                    if (mm(q.y) > edge) if is_up else (mm(q.y) < edge):
                        put(pcbnew.VECTOR2I(q.x, nm(edge)))
            elif L in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                if all(abs(mm(q.y) - butt) < 1.0 for q in (g.GetStart(), g.GetEnd())):
                    drop.append((f, g))
    for f, g in drop:
        f.Delete(g)
    for f, *_ in work:
        f.BuildCourtyardCaches()


def drc(path):
    import json
    import os
    import subprocess
    rep = path + ".drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all", "--refill-zones",
                    "-o", rep, path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = json.load(open(rep))
    os.remove(rep)
    return d


def clear_dangling(b, out):
    """Delete what KiCad's DRC calls dangling (stubs the rip-ups left), one at a time,
    keeping anything whose removal would leave a connection open."""
    split_tees(b)
    kept = set()
    for _ in range(60):
        pcbnew.SaveBoard(out, b)
        d = drc(out)
        base = len(d["unconnected_items"])
        hits = [(v["type"], v["items"][0]["pos"]["x"], v["items"][0]["pos"]["y"]) for v in d["violations"]
                if v["type"] in ("track_dangling", "via_dangling")]
        hits = [h for h in hits if (h[1], h[2]) not in kept]
        if not hits:
            return
        kind, x, y = hits[0]
        for t in list(b.GetTracks()):
            if kind == "via_dangling" and t.GetClass() == "PCB_VIA":
                q = t.GetPosition()
                hit = abs(mm(q.x) - x) < 0.01 and abs(mm(q.y) - y) < 0.01
            elif kind == "track_dangling" and t.GetClass() == "PCB_TRACK":
                hit = any(abs(mm(q.x) - x) < 0.01 and abs(mm(q.y) - y) < 0.01 for q in (t.GetStart(), t.GetEnd()))
            else:
                hit = False
            if hit:
                dup = t.Duplicate()
                b.Delete(t)
                pcbnew.SaveBoard(out, b)
                if len(drc(out)["unconnected_items"]) > base:
                    # other copper joins it part-way along: keep it, cut back to that joint
                    b.Add(dup)
                    kept.add((x, y))
                break
        else:
            kept.add((x, y))


NETLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "carrier.net")


def prepare(src):
    """Inky's board brought up to the current schematic, with the charger block re-placed,
    and everything that has to be routed again cleared."""
    b = pcbnew.LoadBoard(src)
    EDGES.clear()
    ds = b.GetDesignSettings()
    ds.m_TentViasFront = ds.m_TentViasBack = True    # a probe that misses a test pad lands on mask
    retitle(b)
    changed, swapped = apply_netlist(b, NETLIST)
    for p in b.FindFootprintByReference("J5").Pads():   # the Kit-feed pigtail's GND hole:
        if p.GetNetname() == "GND":                      # solid to the pour, so routing can't starve it
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    butted_sockets(b)
    place_charger(b)
    nets = rip_box(b, CHARGER_BOX)
    for ref in swapped:                              # re-footprinted parts: clear their column
        bb = b.FindFootprintByReference(ref).GetCourtyard(pcbnew.F_CrtYd).BBox()
        box = (mm(bb.GetX()) - 0.8, mm(bb.GetY()) - 0.8,
               mm(bb.GetX() + bb.GetWidth()) + 0.8, mm(bb.GetY() + bb.GetHeight()) + 0.8)
        nets |= rip_box(b, box)
        drop_gnd_tracks(b, box)
    for t in list(b.GetTracks()):                    # copper of nets whose pads changed
        if t.GetNetname() in changed:
            nets.add(t.GetNetname())
            b.Delete(t)
    for box in A3_BOXES:
        nets |= rip_box(b, box)
        drop_gnd_tracks(b, box)
        drop_gnd_vias(b, box, keep_near=(0, 0, 0))
    nets |= changed
    nets |= {p.GetNetname() for r in A3_PARTS for p in b.FindFootprintByReference(r).Pads()}
    nets.discard("GND")
    nets.discard("")
    drop_gnd_tracks(b, CHARGER_BOX)
    drop_gnd_vias(b, CHARGER_BOX)
    u1_fingers(b)
    u6_ground(b)
    u6_fingers(b)
    reserve_gnd_vias(b, CHARGER_BOX)
    for box in A3_BOXES:
        reserve_gnd_vias(b, box)
    reserve_gnd_vias(b)                              # and every other GND pad without a via nearby
    return b, nets


JAVA = "build/tools/jdk-25.0.4.1+1-jre/Contents/Home/bin/java"
FREEROUTING = "build/tools/freerouting.jar"


def freeroute(b, work, passes=100):
    """Freerouting routes what's open, around the copper that stays (Specctra DSN out,
    session back in). Single-threaded: its multi-threaded optimiser is known to leave
    clearance errors, and single-threaded it gives the same result every run."""
    import subprocess
    dsn, ses = f"{work}.dsn", f"{work}.ses"
    for f in (dsn, ses):
        if os.path.exists(f):
            os.remove(f)
    pcbnew.ExportSpecctraDSN(b, dsn)
    with open(f"{work}.freerouting.log", "w") as log:
        subprocess.run([JAVA, "-Djava.awt.headless=true", "-jar", FREEROUTING, "-de", dsn, "-do", ses,
                        "-mp", str(passes), "-mt", "1"], check=True, stdout=log, stderr=subprocess.STDOUT)
    if not os.path.getsize(ses):
        sys.exit(f"freerouting wrote nothing; see {work}.freerouting.log")
    pcbnew.ImportSpecctraSES(b, ses)


def main(src, out):
    import shutil
    global B_PENALTY, B_KEEPOUT
    B_PENALTY = (CHARGER_BOX, 4.0)
    B_KEEPOUT = (149.6, 117.3, 154.4, 119.75)    # clear of TP23 and TP31
    shutil.copy(src.replace(".kicad_pcb", ".kicad_pro"), out.replace(".kicad_pcb", ".kicad_pro"))   # rules for DRC
    print("bring the board up to the schematic, re-place the charger, clear what changed")
    b, nets = prepare(src)
    print("freerouting")
    freeroute(b, os.path.join(os.path.dirname(os.path.abspath(out)), "..", "build",
                              os.path.basename(out).replace(".kicad_pcb", "")))
    drop_dangling(b)
    print("grid router: whatever is still open")
    signals = sorted({p.GetNetname() for f in b.GetFootprints() for p in f.Pads()} - {"", "GND"})
    failed = connect_all(b, signals)
    if failed:
        failed = rip_reroute(b, failed)
    if failed:
        print(f"UNROUTED: {failed}")
    drop_dangling(b)
    refill(b)
    print(f"stitching vias: {stitch(b)}")
    print(f"vias joining GND pour pieces: {join_gnd(b)}")
    refill(b)
    drop_dangling(b)
    clear_dangling(b, out)
    refill(b)
    pcbnew.SaveBoard(out, b)


if __name__ == "__main__":
    main(*sys.argv[1:3])
