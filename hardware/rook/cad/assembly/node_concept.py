"""Concept render of the V1 node collar from docs/TOP-UNIT-BRIEF.md: one
crest unit with a two-panel roof, ear pods on a perforated strap, and an
encased counterweight, on a neck form. Not a print file: shapes are lofted
for looks, but the crest unit is a real hollow shell, so its printed volume
and the fit of the bought parts inside are measured.

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --factory-startup --python assembly/node_concept.py

Renders go to renders/node_concept/.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "common", "cad", "lib")))
import bmesh
import bpy
from mathutils import Vector

import oc

OUT = os.path.join(oc.ROOT, "renders", "node_concept" + ("_pouch" if "--pouch" in sys.argv else ""))

# Neck just behind the head: ~25 cm wide, ~42 cm tall (~107 cm around).
NECK_A, NECK_B = 125.0, 210.0
STRAP_T, STRAP_W = 3.0, 50.0

# Crest unit, from the brief.
CU_W = 70.0          # across the neck
CU_L = 140.0         # along the spine
ROOF_DEG = 16.0      # each roof face
WALL = 2.5
CU_FLAT = 52.0       # half-length of the straight middle; the ends round off over CU_L/2 - CU_FLAT

# Bought parts inside.
CELL_D, CELL_L = 18.4, 65.0      # 18650 LiFePO4
BOARD = (52.0, 112.0, 1.6)
BOARD_PARTS = 2.0                # tallest component on the board's top side
PATCH = (25.0, 25.0, 4.0)        # GNSS patch
POUCH = (40.0, 112.0, 8.0)       # alternative: ~10 Wh LiFePO4 pouch pack
VARIANT = "pouch" if "--pouch" in sys.argv else "18650"

COL = {
    "shell": ((0.16, 0.16, 0.17), 0.55, 0.0),
    "pod": ((0.16, 0.16, 0.17), 0.55, 0.0),
    "solar": ((0.02, 0.035, 0.07), 0.12, 0.0),
    "window": ((0.30, 0.30, 0.31), 0.35, 0.0),
    "accent": ((1.0, 0.24, 0.05), 0.45, 0.0),
    "strap": ((0.07, 0.07, 0.075), 0.8, 0.0),
    "weight": ((0.13, 0.13, 0.14), 0.6, 0.0),
    "neck": ((0.62, 0.55, 0.47), 0.95, 0.0),
    "pcb": ((0.05, 0.30, 0.12), 0.45, 0.0),
    "cell": ((0.10, 0.25, 0.55), 0.4, 0.0),
    "gnss": ((0.80, 0.74, 0.60), 0.4, 0.0),
    "antenna": ((0.75, 0.55, 0.15), 0.4, 0.3),
    "cut": ((0.85, 0.30, 0.22), 0.6, 0.0),
}


def mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    rgb, rough, metal = COL[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if name == "solar":
        b.inputs["Coat Weight"].default_value = 1.0
    m.diffuse_color = (*rgb, 1)
    return m


def dress(obj, name, smooth=True):
    obj.data.materials.clear()
    obj.data.materials.append(mat(name))
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
        try:
            obj.data.set_sharp_from_angle(angle=math.radians(40))
        except AttributeError:
            pass
    return obj


# ---------------------------------------------------------------- geometry helpers

def neck_top(x):
    return NECK_B * math.sqrt(max(0.0, 1 - (x / NECK_A) ** 2))


def chaikin(pts, n):
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            (x0, z0), (x1, z1) = pts[i], pts[(i + 1) % len(pts)]
            out += [(0.75 * x0 + 0.25 * x1, 0.75 * z0 + 0.25 * z1),
                    (0.25 * x0 + 0.75 * x1, 0.25 * z0 + 0.75 * z1)]
        pts = out
    return pts


def loft(name, profile, half_len, flat, stations=48, ends=True, power=2):
    """Extrude an XZ profile along Y, scaling it about its centroid toward
    zero over the last (half_len - flat) mm at each end: rounded ends in
    plan and elevation."""
    cx = sum(p[0] for p in profile) / len(profile)
    cz = sum(p[1] for p in profile) / len(profile)
    r = half_len - flat
    ys = []
    for i in range(stations + 1):
        a = -math.pi / 2 + math.pi * i / stations
        ys.append(math.sin(a))  # dense near the ends
    bm = bmesh.new()
    rings = []
    for u in ys:
        y = u * half_len
        d = abs(y) - flat
        s = 1.0 if d <= 0 else max(0.0, 1 - (d / r) ** power) ** (1 / power)
        s = max(s, 0.02)
        rings.append([bm.verts.new((cx + s * (x - cx), y, cz + s * (z - cz))) for x, z in profile])
    n = len(profile)
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    if ends:
        for ring, y in ((rings[0], -half_len), (rings[-1], half_len)):
            c = bm.verts.new((cx, y, cz))
            for k in range(n):
                bm.faces.new((ring[k], ring[(k + 1) % n], c) if y > 0 else (ring[(k + 1) % n], ring[k], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj, (cx, cz)


def band(name, pts, y0, y1, thickness, closed=True):
    """A band of rectangular section along an XZ polyline, between y0 and y1."""
    bm = bmesh.new()
    n = len(pts)
    rings = []
    for i in range(n):
        p0 = pts[i - 1] if (closed or i > 0) else pts[i]
        p2 = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        tx, tz = p2[0] - p0[0], p2[1] - p0[1]
        L = math.hypot(tx, tz) or 1
        nx, nz = -tz / L, tx / L
        x, z = pts[i]
        rings.append([bm.verts.new((x + nx * o * thickness / 2, y, z + nz * o * thickness / 2))
                      for o, y in ((-1, y0), (1, y0), (1, y1), (-1, y1))])
    m = n if closed else n - 1
    for i in range(m):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    if not closed:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def strap_points(step_deg=1.0):
    """Centreline of the strap: the neck ellipse, offset by half the strap."""
    pts = []
    k = int(360 / step_deg)
    for i in range(k):
        a = math.radians(90 - i * step_deg)  # start at the top, run clockwise (to +X)
        pts.append(((NECK_A + STRAP_T / 2) * math.cos(a), (NECK_B + STRAP_T / 2) * math.sin(a)))
    return pts


def arc_index(pts, length):
    """Index of the point `length` mm along the strap from the top."""
    s = 0.0
    for i in range(1, len(pts)):
        s += math.dist(pts[i - 1], pts[i])
        if s >= length:
            return i
    return len(pts) - 1


def frame_at(pts, i):
    """Point, tangent and outward normal (in XZ) at strap index i."""
    (x0, z0), (x1, z1), (x2, z2) = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
    tx, tz = x2 - x0, z2 - z0
    L = math.hypot(tx, tz)
    tx, tz = tx / L, tz / L
    nx, nz = tz, -tx  # clockwise path, so this points outward
    return (x1, z1), (tx, tz), (nx, nz)


# ---------------------------------------------------------------- crest unit

def crest_profile(inset=0.0):
    """Coarse XZ section of the crest unit, then rounded."""
    h = CU_W / 2 - inset
    t = math.tan(math.radians(ROOF_DEG))
    under = [(x, neck_top(x) + STRAP_T + inset) for x in
             [h * (-1 + 2 * i / 12) for i in range(13)]]
    side_top = RIDGE - inset / math.cos(math.radians(ROOF_DEG)) - h * t
    coarse = under[:-1] + densify([under[-1], (h, side_top), (0.0, side_top + h * t), (-h, side_top), under[0]], 6.0)[:-1]
    return chaikin(coarse, 4)


def densify(pts, seg):
    out = []
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        n = max(1, int(math.dist((x0, z0), (x1, z1)) / seg))
        out += [(x0 + (x1 - x0) * k / n, z0 + (z1 - z0) * k / n) for k in range(n)]
    out.append(pts[-1])
    return out


def roof_z(x):
    """Outer roof surface in the straight middle, away from the rounded edges."""
    return RIDGE - abs(x) * math.tan(math.radians(ROOF_DEG))


def crest_unit():
    outer, _ = loft("crest_unit", crest_profile(), CU_L / 2, CU_FLAT, power=4)
    inner, _ = loft("crest_cavity", crest_profile(WALL), CU_L / 2 - WALL, CU_FLAT - WALL, power=4)
    oc.cut(outer, inner)
    return outer


def surface(unit):
    """z of the crest unit's outer top surface at (x, y), by ray cast."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromObject(unit, bpy.context.evaluated_depsgraph_get())

    def z(x, y):
        loc, _, _, _ = tree.ray_cast(Vector((x, y, 1000.0)), Vector((0, 0, -1)))
        return loc.z
    return z


def sheet(name, grid, z_of, top=0.6, bottom=-0.4, wrap=False):
    """A thin solid that follows the surface: grid is rows of (x, y) points."""
    bm = bmesh.new()
    T = [[bm.verts.new((x, y, z_of(x, y) + top)) for x, y in row] for row in grid]
    B = [[bm.verts.new((x, y, z_of(x, y) + bottom)) for x, y in row] for row in grid]
    nr, nc = len(grid), len(grid[0])
    cols = nc if wrap else nc - 1
    area = 0.0
    for i in range(nr - 1):
        for j in range(cols):
            k = (j + 1) % nc
            f = bm.faces.new((T[i][j], T[i][k], T[i + 1][k], T[i + 1][j]))
            area += f.calc_area()
            bm.faces.new((B[i + 1][j], B[i + 1][k], B[i][k], B[i][j]))
    edges = []
    for j in range(cols):  # first and last rows
        k = (j + 1) % nc
        edges += [(0, j, 0, k), (nr - 1, k, nr - 1, j)]
    if not wrap:
        for i in range(nr - 1):
            edges += [(i + 1, 0, i, 0), (i, nc - 1, i + 1, nc - 1)]
    for i0, j0, i1, j1 in edges:
        bm.faces.new((T[i0][j0], T[i1][j1], B[i1][j1], B[i0][j0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o, area


def panels(z_of):
    """Two solar laminates on the roof faces, either side of the ridge."""
    out, total = [], 0.0
    y0, y1 = -24.0, 56.0
    xa, xb = 3.0, CU_W / 2 - 6.5
    for sx in (-1, 1):
        grid = [[(sx * (xa + (xb - xa) * j / 16), y0 + (y1 - y0) * i / 20) for j in range(17)] for i in range(21)]
        o, a = sheet(f"solar_{'L' if sx < 0 else 'R'}", grid, z_of, top=0.5, bottom=-0.5)
        out.append(o)
        total += a
    return out, total / 100


def gnss_window(z_of):
    """A matte window over the GNSS patch at the head end, and a thin accent seam
    between it and the panels: the one accent colour."""
    def rrect(x0, x1, y0, y1, r, n=10):
        pts = []
        for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
            pts += [(cx + r * math.cos(math.radians(a0 + 90 * k / n)), cy + r * math.sin(math.radians(a0 + 90 * k / n)))
                    for k in range(n + 1)]
        return pts
    objs = []
    edge = rrect(-CU_W / 2 + 6.5, CU_W / 2 - 6.5, -CU_L / 2 + 9, -30.0, 5.0)
    cx, cy = 0.0, (-CU_L / 2 + 9 - 30.0) / 2
    grid = [[(cx + (x - cx) * f, cy + (y - cy) * f) for x, y in edge] for f in [0.02 + 0.98 * i / 8 for i in range(9)]]
    o, _ = sheet("gnss_window", grid, z_of, top=0.3, bottom=-0.5, wrap=True)
    objs.append((o, "window"))
    seam = [[(-CU_W / 2 + 6.5 + (CU_W - 13) * j / 40, y) for j in range(41)] for y in (-27.6, -26.2)]
    o, _ = sheet("gnss_seam", seam, z_of, top=0.45, bottom=-0.5)
    objs.append((o, "accent"))
    return objs


def insides():
    """Board on the floor's crown, cells on top, patch at the head end, antenna at the tail."""
    floor = neck_top(0) + STRAP_T + WALL + 0.8
    parts = []
    board = oc.box("board", BOARD, at=(0, 0, floor), anchor="bottom")
    parts.append((board, "pcb"))
    if VARIANT == "pouch":
        pack = oc.box("pouch", POUCH, at=(0, 4.0, floor + BOARD[2] + BOARD_PARTS), anchor="bottom")
        parts.append((pack, "cell"))
    else:
        cz = floor + BOARD[2] + BOARD_PARTS + CELL_D / 2
        for sx in (-1, 1):
            cell = oc.cylinder(f"cell_{sx}", CELL_D, CELL_L, at=(sx * (CELL_D / 2 + 0.6), 14.0, cz), axis="Y")
            parts.append((cell, "cell"))
    patch = oc.box("gnss_patch", PATCH, at=(0, -45.0, floor + BOARD[2]), anchor="bottom")
    parts.append((patch, "gnss"))
    ant = oc.box("lora_antenna", (32.0, 0.3, 6.0), at=(0, CU_L / 2 - WALL - 7.0, floor + BOARD[2] + 1.0), anchor="bottom")
    parts.append((ant, "antenna"))
    return parts


# ---------------------------------------------------------------- the rest of the collar

def strap(pts, skip):
    """Ladder strap: two edge rails plus rungs, so it reads as perforated."""
    rail = 9.0
    objs = [band("strap_rail_a", pts, -STRAP_W / 2, -STRAP_W / 2 + rail, STRAP_T),
            band("strap_rail_b", pts, STRAP_W / 2 - rail, STRAP_W / 2, STRAP_T)]
    s, last = 0.0, -1e9
    pitch, rung = 17.0, 6.0
    for i in range(1, len(pts)):
        s += math.dist(pts[i - 1], pts[i])
        if s - last < pitch or skip(pts[i]):
            continue
        last = s
        j = arc_index(pts, s + rung)
        seg = pts[i:j + 1] if j > i else [pts[i], pts[(i + 1) % len(pts)]]
        if len(seg) < 2:
            continue
        objs.append(band(f"rung_{i}", seg, -STRAP_W / 2 + rail - 0.5, STRAP_W / 2 - rail + 0.5,
                         STRAP_T * 0.9, closed=False))
    return objs


def ear_pod(pts, idx, sx):
    (x, z), (tx, tz), (nx, nz) = frame_at(pts, idx)
    prof = chaikin([(-22.0, 0.0), (22.0, 0.0), (20.0, 11.0), (-20.0, 11.0)], 4)
    pod, _ = loft("ear_pod", prof, 18.0, 6.0, stations=24)
    # Profile x runs along the strap, profile z points away from the neck.
    ang = math.atan2(tz, tx)
    pod.rotation_euler = (0, -ang, 0)
    pod.location = (x + nx * STRAP_T / 2, 0, z + nz * STRAP_T / 2)
    oc.bake(pod)
    return pod, []


def pod_cable(pts, i0, i1):
    """The pod's lead, in a sleeve along the strap edge, into the crest unit's end."""
    cd = bpy.data.curves.new("cable", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = 2.2
    cd.bevel_resolution = 4
    sp = cd.splines.new("POLY")
    seq = range(i0, i1 + 1) if i1 >= i0 else range(i0, i1 - 1, -1)
    seq = list(seq)
    sp.points.add(len(seq) - 1)
    for p, i in zip(sp.points, seq):
        (x, z), _, (nx, nz) = frame_at(pts, i % len(pts))
        p.co = (x + nx * (STRAP_T / 2 + 2.2), STRAP_W / 2 - 4.0, z + nz * (STRAP_T / 2 + 2.2), 1)
    o = bpy.data.objects.new("pod_cable", cd)
    bpy.context.scene.collection.objects.link(o)
    return o


def counterweight():
    """A steel plate inside a rounded casing, its top following the throat."""
    h = 62.0
    under = [(x, -neck_top(x) - STRAP_T) for x in [h * (1 - 2 * i / 12) for i in range(13)]]
    coarse = under + [(-h, -neck_top(h) - STRAP_T - 22), (0, -NECK_B - STRAP_T - 26), (h, -neck_top(h) - STRAP_T - 22)]
    w, _ = loft("counterweight", chaikin(coarse, 4), 34.0, 20.0)
    clips = []
    for sx in (-1, 1):
        x = sx * (h + 9)
        z = -neck_top(x) - STRAP_T / 2
        a = math.atan2(-x / NECK_A ** 2, z / NECK_B ** 2)  # normal angle of the ellipse
        c = oc.rounded_box(f"clip_{sx}", (18.0, STRAP_W + 6, 9.0), 3.0)
        c.rotation_euler = (0, -(a - math.pi / 2) * 1.0, 0)
        c.location = (x * 1.01, 0, z - 2.5)
        oc.bake(c)
        tab = oc.rounded_box(f"tab_{sx}", (10.0, 14.0, 3.0), 1.2)
        tab.rotation_euler = c.rotation_euler
        tab.location = (x * 1.01 + sx * 2, 0, z - 8.5)
        oc.bake(tab)
        clips.append((c, tab))
    return w, clips


def neck():
    prof = [(NECK_A * math.cos(2 * math.pi * k / 96), NECK_B * math.sin(2 * math.pi * k / 96)) for k in range(96)]
    n, _ = loft("neck", prof, 330.0, 230.0, stations=64)
    return n


# ---------------------------------------------------------------- scene and renders

def scene():
    s = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            s.render.engine = engine
            break
        except TypeError:
            continue
    s.render.resolution_x, s.render.resolution_y = 1800, 1200
    s.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("studio")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.93, 0.93, 0.91, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
    s.world = w
    if hasattr(s, "eevee"):
        for attr, val in (("use_gtao", True), ("use_shadows", True), ("taa_render_samples", 96)):
            if hasattr(s.eevee, attr):
                setattr(s.eevee, attr, val)

    def sun(name, e, d, ang):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy, ld.angle = e, math.radians(ang)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = (-Vector(d)).to_track_quat("-Z", "Y").to_euler()
        s.collection.objects.link(lo)
    sun("key", 3.4, (0.55, -0.75, 0.95), 10)
    sun("fill", 0.9, (-0.9, -0.4, 0.35), 40)
    sun("rim", 1.6, (-0.2, 0.95, 0.5), 20)
    bpy.ops.mesh.primitive_plane_add(size=8000, location=(0, 0, -NECK_B - 220))
    g = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.58, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1
    g.data.materials.append(gm)


def camera(loc, target, lens=50, ortho=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start, cd.clip_end = 5, 30000
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", ortho
    cam = bpy.data.objects.new("cam", cd)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    return cam


def shoot(cam, name):
    os.makedirs(OUT, exist_ok=True)
    s = bpy.context.scene
    s.camera = cam
    s.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)


def cutaway(objs, y):
    """Cut everything at plane y (keep y > plane) and paint the cut faces."""
    for o in objs:
        if o.type != "MESH":
            continue
        tool = oc.box("cutter", (2000, 1000, 2000), at=(0, y - 500, 0))
        oc.cut(o, tool)


if __name__ == "__main__":
    oc.reset()
    RIDGE = 0.0  # set below

    # Ridge height: the lowest roof that clears the cells with 0.5 mm to spare.
    floor = neck_top(0) + STRAP_T + WALL + 0.8
    t = math.tan(math.radians(ROOF_DEG))
    if VARIANT == "pouch":
        cell_top = floor + BOARD[2] + BOARD_PARTS + POUCH[2]
        x_cell = POUCH[0] / 2  # the pack's outer top edge sits under roof_z(x_cell)
    else:
        cell_top = floor + BOARD[2] + BOARD_PARTS + CELL_D
        x_cell = CELL_D / 2 + 0.6  # cell centre; its top point sits under roof_z(x_cell)
    RIDGE = cell_top + 0.5 + WALL / math.cos(math.radians(ROOF_DEG)) + x_cell * t + 0.8  # +0.8 for ridge rounding
    globals()["RIDGE"] = RIDGE

    unit = crest_unit()
    shell_cm3 = oc.volume_mm3(unit) / 1000
    inside = insides()
    clash = [o.name for o, _ in inside if oc.overlaps(unit, o)]
    bounds = oc.bounds(unit)
    height_above_crest = bounds[1][2] - NECK_B
    z_of = surface(unit)
    sols, panel_cm2 = panels(z_of)
    win = gnss_window(z_of)

    pts = strap_points()
    pod_len = 125.0
    i_r = arc_index(pts, pod_len)
    i_l = len(pts) - i_r
    pods = [ear_pod(pts, i_r, 1), ear_pod(pts, i_l, -1)]
    cables = [pod_cable(pts, i_r - 14, 18), pod_cable(pts, i_l + 14, len(pts) - 18)]

    def hidden(p):
        x, z = p
        return (z > 0 and abs(x) < CU_W / 2 + 2) or (z < 0 and abs(x) < 66)
    straps = strap(pts, hidden)
    weight, clips = counterweight()
    n = neck()

    dress(unit, "shell")
    for o in sols:
        dress(o, "solar", smooth=False)
    for o, m in win:
        dress(o, m, smooth=True)
    for pod, grille in pods:
        dress(pod, "pod")
        for g in grille:
            dress(g, "solar", smooth=False)
    for c in cables:
        c.data.materials.append(mat("strap"))
    for o in straps:
        dress(o, "strap", smooth=False)
    dress(weight, "weight")
    for c, tab in clips:
        dress(c, "weight")
        dress(tab, "accent")
    dress(n, "neck")
    for o, m in inside:
        dress(o, m, smooth=False)
        o.hide_render = True

    report = {
        "crest_unit_mm": [round(bounds[1][i] - bounds[0][i], 1) for i in range(3)],
        "height_above_crest_mm": round(height_above_crest, 1),
        "crest_shell_cm3_one_piece": round(shell_cm3, 1),
        "crest_shell_g_PA12": round(shell_cm3 * oc.DENSITY["PA12"], 0),
        "panel_cm2": round(panel_cm2, 1),
        "inside_clashes": clash,
        "battery": VARIANT,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))

    if "--no-render" in sys.argv:
        sys.exit(0)

    scene()
    top = NECK_B + 15
    shoot(camera((300, -380, 400), (0, 0, 150), lens=36), "collar_hero")
    shoot(camera((230, -300, top + 190), (0, 5, top), lens=58), "crest_unit")
    shoot(camera((0, -2400, 0), (0, 0, 0), ortho=860), "collar_front")
    # Collar alone, no neck.
    n.hide_render = True
    shoot(camera((560, -820, 330), (0, 0, 0), lens=42), "collar_product")
    # Section through the cells, looking from the head end.
    for o, _ in inside:
        o.hide_render = False
    for o in [x for x in bpy.data.objects if x.name.startswith(("rung_", "strap_rail", "ear_pod", "grille", "pod_cable",
                                                                   "counterweight", "clip_", "tab_"))]:
        o.hide_render = True
    keep = [unit] + sols + [o for o, _ in inside] + [o for o, _ in win]
    cutaway(keep, 14.0)
    n.hide_render = False
    cutaway([n], 14.0)
    shoot(camera((0, -900, top), (0, 0, top), ortho=120), "crest_section")
    print("renders in", OUT)
