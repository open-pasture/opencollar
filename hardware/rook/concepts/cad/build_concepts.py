"""Rook enclosure design concepts — three visual languages, same hardware envelope.

Keeps Node V1 fit points so electronics still drop in:
  cap   footprint 76×160; columns CAP_COLS; clamp CAP_CLAMP; cavity ≥13 mm
  pod   cavity 82×58×21.5; columns POD_COLS; outer ~92×68
  cw    outer ~88×74×30; screws CW_SCREWS; clamp CW_CLAMP

Print: flat on bed, no supports (flanks ≥45° or self-supporting radii).
Run:  blender --background --factory-startup --python build_concepts.py
"""

import os
import sys
import json
import struct
import shutil
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONCEPTS = os.path.abspath(os.path.join(_HERE, ".."))
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
import bmesh
import oc

# ---------------------------------------------------------------- envelope (match node_v1)

CAP_W, CAP_L = 76.0, 160.0
CAP_WALL = 5.0
CAP_FLOOR = 6.0
CAP_CAVITY_H = 13.0
CAP_H = CAP_FLOOR + CAP_CAVITY_H  # 19
CAP_COLS = [(sx * 29.5, y) for sx in (-1, 1) for y in (-68.0, -42.0, 42.0, 68.0)]
CAP_CLAMP = [(sx * 20.0, sy * 28.5) for sx in (-1, 1) for sy in (-1, 1)]
CLEAR = 3.4
INSERT_D = 4.0

POD_L, POD_W = 92.0, 68.0
POD_WALL = 5.0
POD_FLOOR = 3.0
POD_CAVITY = (82.0, 58.0, 21.5)
POD_BASE_H = POD_FLOOR + POD_CAVITY[2]  # 24.5
POD_COLS = [(sx * 37.0, sy * 27.0) for sx in (-1, 1) for sy in (-1, 1)]

CW_L, CW_W = 88.0, 74.0
CW_WALL = 5.0
CW_FLOOR = 3.0
CW_TUB_H = 30.0
CW_SCREWS = [(sx * 22.0, sy * 31.5) for sx in (-1, 1) for sy in (-1, 1)]
CW_CLAMP = [(sx * 36.0, sy * 29.5) for sx in (-1, 1) for sy in (-1, 1)]


# ---------------------------------------------------------------- watertight helpers

def prepare(obj, merge=1e-4):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=merge, edges=list(bm.edges))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge)
    tiny = [f for f in bm.faces if f.calc_area() < 1e-8]
    if tiny:
        bmesh.ops.delete(bm, geom=tiny, context="FACES")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def check_watertight(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    loose = sum(1 for v in bm.verts if not v.link_edges)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return {
        "watertight": bad == 0 and zero == 0 and loose == 0,
        "bad_edges": bad,
        "zero_area_faces": zero,
        "normals_outward": vol > 0,
    }


def check_stl(path, q=1e-4):
    data = open(path, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0]
    edges = Counter()
    off = 84
    for _ in range(n):
        vals = struct.unpack_from("<12fH", data, off)
        off += 50
        vs = [vals[3:6], vals[6:9], vals[9:12]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ka = tuple(round(vs[a][i] / q) * q for i in range(3))
            kb = tuple(round(vs[b][i] / q) * q for i in range(3))
            key = (ka, kb) if ka < kb else (kb, ka)
            edges[key] += 1
    bad = sum(1 for c in edges.values() if c != 2)
    return {"watertight": bad == 0, "bad_edges": bad, "faces": n}


def add_columns(body, cols, floor_z, top_z):
    bosses = [oc.cylinder(f"col{i}", 8.0, top_z - floor_z + 0.4,
                          at=(x, y, floor_z - 0.2), anchor="bottom")
              for i, (x, y) in enumerate(cols)]
    oc.union(body, *bosses)
    for i, (x, y) in enumerate(cols):
        oc.cut(body, oc.cylinder(f"h{i}", CLEAR, top_z + 2, at=(x, y, -1), anchor="bottom"))
    return body


def cut_cavity(body, size_xy_h, floor_z, r=4.0):
    sx, sy, h = size_xy_h
    oc.cut(body, oc.rounded_rect("cav", (sx, sy, h + 1), r,
                                 at=(0, 0, floor_z), anchor="bottom"))
    return body


def wall_seam(body, w, l, z, depth=1.2, inset=1.6):
    """Accent groove cut into the four outer walls (not a through-frame boolean)."""
    # ±X walls
    oc.cut(body, oc.box("sx+", (depth + 0.5, l - 8, 1.2),
                        at=(w / 2 - depth / 2, 0, z), anchor="bottom"))
    oc.cut(body, oc.box("sx-", (depth + 0.5, l - 8, 1.2),
                        at=(-(w / 2 - depth / 2), 0, z), anchor="bottom"))
    # ±Y walls
    oc.cut(body, oc.box("sy+", (w - 8, depth + 0.5, 1.2),
                        at=(0, l / 2 - depth / 2, z), anchor="bottom"))
    oc.cut(body, oc.box("sy-", (w - 8, depth + 0.5, 1.2),
                        at=(0, -(l / 2 - depth / 2), z), anchor="bottom"))
    return body


def top_chamfer_cut(body, w, l, h, ch=3.0):
    """45° top chamfer by cutting four prism wedges (reliable vs bevel)."""
    # +X wedge: triangle in XZ extruded in Y
    oc.cut(body, oc.prism_y("chx+", [
        (w / 2 + 0.2, h + 0.2),
        (w / 2 - ch, h + 0.2),
        (w / 2 + 0.2, h - ch),
    ], l + 2))
    oc.cut(body, oc.prism_y("chx-", [
        (-w / 2 - 0.2, h + 0.2),
        (-w / 2 - 0.2, h - ch),
        (-w / 2 + ch, h + 0.2),
    ], l + 2))
    oc.cut(body, oc.prism_x("chy+", [
        (l / 2 + 0.2, h + 0.2),
        (l / 2 + 0.2, h - ch),
        (l / 2 - ch, h + 0.2),
    ], w + 2))
    oc.cut(body, oc.prism_x("chy-", [
        (-l / 2 - 0.2, h + 0.2),
        (-l / 2 + ch, h + 0.2),
        (-l / 2 - 0.2, h - ch),
    ], w + 2))
    return body


# ---------------------------------------------------------------- Concept A — organic

def a_cap():
    """Soft pill: large corner radii, no sharp edges."""
    b = oc.rounded_box("a_cap", (CAP_W, CAP_L, CAP_H), 10.0, anchor="bottom", segments=8)
    cut_cavity(b, (CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, CAP_CAVITY_H + 2),
               CAP_FLOOR, r=8.0)
    add_columns(b, CAP_COLS, CAP_FLOOR, CAP_H)
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ci{i}", INSERT_D, 4.5, at=(x, y, -0.2), anchor="bottom"))
    return prepare(b)


def a_pod():
    b = oc.rounded_box("a_pod", (POD_L, POD_W, POD_BASE_H), 11.0, anchor="bottom", segments=8)
    cut_cavity(b, POD_CAVITY, POD_FLOOR, r=6.0)
    add_columns(b, POD_COLS, POD_FLOOR, POD_BASE_H)
    oc.cut(b, oc.cylinder("port", 8.0, POD_WALL + 4,
                          at=(20.0, POD_W / 2 - POD_WALL / 2, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("cable", 6.0, POD_WALL + 4,
                          at=(POD_L / 2 - POD_WALL / 2, -2.0, 12.0), axis="X"))
    return prepare(b)


def a_cw():
    b = oc.rounded_box("a_cw", (CW_L, CW_W, CW_TUB_H), 10.0, anchor="bottom", segments=8)
    cut_cavity(b, (CW_L - 2 * CW_WALL - 2, CW_W - 2 * CW_WALL - 2, CW_TUB_H),
               CW_FLOOR, r=4.0)
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.cut(b, oc.cylinder(f"cwi{i}", INSERT_D, 5.0,
                              at=(x, y, CW_TUB_H - 5.0), anchor="bottom"))
    return prepare(b)


# ---------------------------------------------------------------- Concept B — technical

def b_cap():
    """Crisp slab, 45° crown chamfer, single waist seam."""
    b = oc.rounded_rect("b_cap", (CAP_W, CAP_L, CAP_H), 2.0, anchor="bottom", segments=4)
    top_chamfer_cut(b, CAP_W, CAP_L, CAP_H, ch=3.5)
    wall_seam(b, CAP_W, CAP_L, CAP_H * 0.42, depth=1.2)
    cut_cavity(b, (CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, CAP_CAVITY_H + 2),
               CAP_FLOOR, r=3.0)
    add_columns(b, CAP_COLS, CAP_FLOOR, CAP_H)
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ci{i}", INSERT_D, 4.5, at=(x, y, -0.2), anchor="bottom"))
    return prepare(b)


def b_pod():
    b = oc.rounded_rect("b_pod", (POD_L, POD_W, POD_BASE_H), 2.0, anchor="bottom", segments=4)
    top_chamfer_cut(b, POD_L, POD_W, POD_BASE_H, ch=3.0)
    wall_seam(b, POD_L, POD_W, POD_BASE_H * 0.4, depth=1.2)
    cut_cavity(b, POD_CAVITY, POD_FLOOR, r=3.0)
    add_columns(b, POD_COLS, POD_FLOOR, POD_BASE_H)
    oc.cut(b, oc.cylinder("port", 8.0, POD_WALL + 4,
                          at=(20.0, POD_W / 2 - POD_WALL / 2, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("cable", 6.0, POD_WALL + 4,
                          at=(POD_L / 2 - POD_WALL / 2, -2.0, 12.0), axis="X"))
    return prepare(b)


def b_cw():
    b = oc.rounded_rect("b_cw", (CW_L, CW_W, CW_TUB_H), 2.0, anchor="bottom", segments=4)
    top_chamfer_cut(b, CW_L, CW_W, CW_TUB_H, ch=3.0)
    wall_seam(b, CW_L, CW_W, CW_TUB_H * 0.4, depth=1.2)
    cut_cavity(b, (CW_L - 2 * CW_WALL - 2, CW_W - 2 * CW_WALL - 2, CW_TUB_H),
               CW_FLOOR, r=2.0)
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.cut(b, oc.cylinder(f"cwi{i}", INSERT_D, 5.0,
                              at=(x, y, CW_TUB_H - 5.0), anchor="bottom"))
    return prepare(b)


# ---------------------------------------------------------------- Concept C — minimal

def c_cap():
    """Lowest flush silhouette; recessed fastener seats; no decoration."""
    h = 18.0
    floor = 5.0
    b = oc.rounded_rect("c_cap", (CAP_W, CAP_L, h), 3.0, anchor="bottom", segments=6)
    cut_cavity(b, (CAP_W - 2 * CAP_WALL, CAP_L - 2 * CAP_WALL, h), floor, r=3.0)
    add_columns(b, CAP_COLS, floor, h)
    # Ø7.6 (not Ø8) so the cbore is not coplanar with the column boss wall.
    for i, (x, y) in enumerate(CAP_COLS):
        oc.cut(b, oc.cylinder(f"cb{i}", 7.6, 2.8, at=(x, y, 0.0), anchor="bottom"))
    for i, (x, y) in enumerate(CAP_CLAMP):
        oc.cut(b, oc.cylinder(f"ci{i}", INSERT_D, 4.5, at=(x, y, -0.2), anchor="bottom"))
    return prepare(b)


def c_pod():
    b = oc.rounded_rect("c_pod", (POD_L, POD_W, POD_BASE_H), 3.0, anchor="bottom", segments=6)
    cut_cavity(b, POD_CAVITY, POD_FLOOR, r=3.0)
    add_columns(b, POD_COLS, POD_FLOOR, POD_BASE_H)
    for i, (x, y) in enumerate(POD_COLS):
        oc.cut(b, oc.cylinder(f"cb{i}", 7.6, 2.8, at=(x, y, 0.0), anchor="bottom"))
    oc.cut(b, oc.cylinder("port", 8.0, POD_WALL + 4,
                          at=(20.0, POD_W / 2 - POD_WALL / 2, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("cable", 6.0, POD_WALL + 4,
                          at=(POD_L / 2 - POD_WALL / 2, -2.0, 12.0), axis="X"))
    return prepare(b)


def c_cw():
    h = 28.0
    b = oc.rounded_rect("c_cw", (CW_L, CW_W, h), 3.0, anchor="bottom", segments=6)
    cut_cavity(b, (CW_L - 2 * CW_WALL - 2, CW_W - 2 * CW_WALL - 2, h), CW_FLOOR, r=2.0)
    for i, (x, y) in enumerate(CW_SCREWS):
        oc.cut(b, oc.cylinder(f"cwi{i}", INSERT_D, 5.0, at=(x, y, h - 5.0), anchor="bottom"))
        oc.cut(b, oc.cylinder(f"cb{i}", 8.0, 2.5, at=(x, y, h - 2.5), anchor="bottom"))
    return prepare(b)


# ---------------------------------------------------------------- build / export / render

CONCEPTS = {
    "A_organic": {
        "title": "A — Soft organic",
        "builders": {"cap": a_cap, "pod": a_pod, "cw": a_cw},
    },
    "B_technical": {
        "title": "B — Clean technical",
        "builders": {"cap": b_cap, "pod": b_pod, "cw": b_cw},
    },
    "C_minimal": {
        "title": "C — Minimal low-profile",
        "builders": {"cap": c_cap, "pod": c_pod, "cw": c_cw},
    },
}


def layout(parts):
    oc.move(parts["pod"], dx=CAP_W / 2 + POD_L / 2 + 25)
    oc.move(parts["cw"], dx=-(CAP_W / 2 + CW_L / 2 + 25))
    return [parts["cw"], parts["cap"], parts["pod"]]


def build_one(key, meta):
    stl_dir = os.path.join(_CONCEPTS, "stl", key)
    rend_dir = os.path.join(_CONCEPTS, "renders", key)
    os.makedirs(stl_dir, exist_ok=True)
    os.makedirs(rend_dir, exist_ok=True)
    oc.reset()
    parts = {name: fn() for name, fn in meta["builders"].items()}
    report = {"concept": key, "title": meta["title"], "bodies": {}, "pass": True}

    for name, obj in parts.items():
        prepare(obj)
        dims = oc.size(obj)
        vol = oc.volume_mm3(obj)
        wt = check_watertight(obj)
        path = os.path.join(stl_dir, f"{name}.stl")
        oc.export_stl(obj, path)
        stl = check_stl(path)
        # Footprint sanity: must not shrink the locked envelope by more than 1 mm.
        expect = {
            "cap": (CAP_W, CAP_L),
            "pod": (POD_L, POD_W),
            "cw": (CW_L, CW_W),
        }[name]
        size_ok = abs(dims[0] - expect[0]) <= 1.0 and abs(dims[1] - expect[1]) <= 1.0 and dims[2] > 5.0
        ok = wt["watertight"] and stl["watertight"] and wt["normals_outward"] and size_ok
        body = {
            "size_mm": dims,
            "volume_cm3": round(vol / 1000, 2),
            "watertight": wt,
            "stl": stl,
            "size_ok": size_ok,
            "pass": ok,
        }
        report["bodies"][name] = body
        report["pass"] &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {key}/{name}: {dims} mm  "
              f"bad_edges={wt['bad_edges']} stl_bad={stl['bad_edges']} size_ok={size_ok}")

    objs = layout(parts)
    oc.render_views(objs, rend_dir, section_axis="Y")
    hero_src = os.path.join(rend_dir, "iso.png")
    # Tracked hero copy (hardware/**/renders/ is gitignored).
    img_dir = os.path.join(_CONCEPTS, "images")
    os.makedirs(img_dir, exist_ok=True)
    if os.path.isfile(hero_src):
        shutil.copy2(hero_src, os.path.join(_CONCEPTS, "renders", f"{key}.png"))
        shutil.copy2(hero_src, os.path.join(img_dir, f"{key}.png"))

    with open(os.path.join(rend_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    return report


def main():
    reports = []
    overall = True
    for key, meta in CONCEPTS.items():
        print(f"\n=== {meta['title']} ===")
        r = build_one(key, meta)
        reports.append(r)
        overall &= r["pass"]
    summary = {"pass": overall, "concepts": reports}
    with open(os.path.join(_CONCEPTS, "renders", "report.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nRESULT:", "PASS" if overall else "FAIL")
    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
