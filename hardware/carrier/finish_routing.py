"""Finish the carrier's routing after HeyPCB (rev A2).

    kicad-python finish_routing.py pcb/heypcb/opencollar-carrier.kicad_pcb pcb/carrier.kicad_pcb

HeyPCB's agent (Inky) routed 163 of the board's 166 connections. The three it left, and
the six clearance errors it made, were all at U1, the bq24074 charger: layout.py packed
the charger's passives by block rather than by pin, so the IN capacitor and the TMR
resistor sat below the chip with their pins on top, and nothing could get out of pin 13.

This script keeps Inky's routing everywhere else and redoes the charger block:
  1. each charger passive goes beside the U1 pin it serves (CHARGER below);
  2. everything but GND is cleared from the block; fixed copper goes on U1's 0.5 mm-pitch
     pins (0.25 mm fingers, so 0.5 mm power tracks never pass near a neighbouring pin);
  3. each GND pad in the block gets its own via, then a two-layer grid router (0.05 mm
     grid, 45-degree moves) reconnects every net, keeping the board's clearances, 0.3 mm
     to the edge, and signals mostly off the bottom layer so its GND pour stays whole;
     route orders are retried until every net routes;
  4. GND stitching vias, pour refill, and removal of the stubs the rip-up left behind,
     each checked with KiCad's own DRC.
It also pulls J1-J4's courtyards and silk back where the sockets butt end to end.
Result: kicad-cli DRC with every severity reports nothing.
"""
import heapq
import math
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
WIDTH = {"BAT": 0.5, "CHG_IN": 0.5, "CHG_OUT": 0.5, "SOLAR_A": 0.5, "SOLAR_B": 0.5,
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

    def clearance_field(self, net, reach=1.2):
        """Per layer: distance from each grid point to the nearest copper that isn't `net`,
        shrunk by the extra clearance that copper asks for (test pads, NPTH, the edge)."""
        D = {L: np.full((self.ny, self.nx), 9.0, np.float32) for L in LAYERS}
        T = np.full((self.ny, self.nx), 9.0, np.float32)      # distance to test pads
        for s in self.shapes:
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


def route(bm, net, src, dst, w, neck_pts=()):
    D, H = bm.clearance_field(net)
    need = w / 2 + CLR + EPS
    need_n = NECK_W / 2 + CLR + EPS
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
    goals = set(c for s in dst for c in bm.cells_in(s) if passable(*c))
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


def commit(bm, net, path, w):
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
                emit(run, add_track, xy, w)
            add_via(xy(cur[1], cur[2]))
            run = [cur]
            continue
        run.append(cur)
    if len(run) > 1:
        emit(run, add_track, xy, w)


def emit(run, add_track, xy, w):
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
        width = NECK_W if any(run[k][3] for k in range(a, c + 1)) else w
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
            neck = [(s.g["x"], s.g["y"]) for g in isl for s in g
                    if isinstance(s.item, pcbnew.PAD) and s.item.GetParentFootprint().GetReference() == "U1"]
            path = None
            for width in ([w] + [x for x in (0.4, 0.3, 0.25) if x < w]):
                path = route(bm, net, main, [s for g in rest for s in g], width, neck)
                if path:
                    break
            if not path:
                print(f"  {net}: NO PATH for {len(rest)} island(s)")
                failed.append(net)
                break
            commit(bm, net, path, width)
            vias = sum(1 for a, c in zip(path, path[1:]) if a[0] != c[0])
            print(f"  {net}: routed {len(path)} steps at {width} mm, {vias} via(s)")
    return failed


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


def join_gnd(b, step=0.25):
    """Add GND vias until every pour piece is joined to the rest."""
    added = 0
    for _ in range(40):
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
    for g in groups[1:]:
        near = lambda s: any(in_group(s.g["x"] + dx, s.g["y"] + dy, g) for dx, dy in
                             ((0, 0), (0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6)))
        pads = [s for s in gnd if isinstance(s.item, pcbnew.PAD) and near(s)]
        if not pads:        # a piece held only by vias: route from those
            pads = [s for s in gnd if s.item.GetClass() == "PCB_VIA" and near(s) and s not in vias]
        if not pads:
            continue
        for width in (0.4, 0.25):
            path = route(bm, "GND", pads, vias, width)
            if path:
                commit(bm, "GND", path, width)
                print(f"  GND: rejoined {[p.item.GetParentFootprint().GetReference() for p in pads]} at {width} mm")
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


def reserve_gnd_vias(b, box):
    """Each GND pad in `box` left with nothing attached gets a via at its edge now, before
    signals are routed, so they route around it instead of walling the pad in."""
    x0, y0, x1, y1 = box
    bm = Board(b)
    D, H = bm.clearance_field("GND")
    need = VIA_D / 2 + CLR + 0.05
    for grp in islands(bm, "GND"):
        if len(grp) != 1 or not isinstance(grp[0].item, pcbnew.PAD):
            continue
        p = grp[0].item
        if p.GetParentFootprint().GetReference() == "U1" or p.GetDrillSize().x > 0:
            continue
        g = grp[0].g
        if not (x0 <= g["x"] <= x1 and y0 <= g["y"] <= y1):
            continue
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


POWER = ["CHG_IN", "BAT", "CHG_OUT", "SOLAR_A", "SOLAR_B", "3V3", "EXT_3V3"]


# The charger's passives, each beside the U1 pin it serves (board mm, degrees). U1's pins:
# left TS, BAT, BAT, CE; bottom GND, EN1, PGOOD, GND; right STAT, OUT, OUT, ILIM;
# top IN, TMR, -, ISET.
CHARGER = {
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


def prepare(src):
    """Inky's board with the charger block re-placed and cleared for routing."""
    b = pcbnew.LoadBoard(src)
    EDGES.clear()
    ds = b.GetDesignSettings()
    ds.m_TentViasFront = ds.m_TentViasBack = True    # a probe that misses a test pad lands on mask
    butted_sockets(b)
    place_charger(b)
    nets = rip_box(b, CHARGER_BOX)
    drop_gnd_tracks(b, CHARGER_BOX)
    drop_gnd_vias(b, CHARGER_BOX)
    u1_fingers(b)
    reserve_gnd_vias(b, CHARGER_BOX)
    return b, nets


def main(src, out):
    import shutil
    global B_PENALTY, B_KEEPOUT
    B_PENALTY = (CHARGER_BOX, 4.0)
    B_KEEPOUT = (149.6, 117.3, 154.4, 119.75)    # clear of TP23 and TP31
    shutil.copy(src.replace(".kicad_pcb", ".kicad_pro"), out.replace(".kicad_pcb", ".kicad_pro"))   # rules for DRC
    print("re-place the charger passives by pin, clear the block, fix U1's fan-out; route")
    hint, best = [], None
    for k in range(10):
        b, nets = prepare(src)
        order = hint + [n for n in POWER if n in nets and n not in hint]
        order += sorted(n for n in nets if n not in order)
        failed = connect_all(b, order)
        print(f"attempt {k + 1}: failed {failed}")
        if best is None or len(failed) < len(best[1]):
            best = (b, failed)
        if not failed:
            break
        hint = failed + [n for n in hint if n not in failed]
    b, failed = best
    if failed:
        print(f"UNROUTED: {failed}")
    drop_dangling(b)
    refill(b)
    print(f"stitching vias: {stitch(b)}")
    print(f"vias joining GND pour pieces: {join_gnd(b)}")
    refill(b)
    clear_dangling(b, out)
    refill(b)
    pcbnew.SaveBoard(out, b)


if __name__ == "__main__":
    main(*sys.argv[1:3])
