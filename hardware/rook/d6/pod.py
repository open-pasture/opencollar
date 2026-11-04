"""D6 pod CAD — D4 contoured skin around D5 (6b1f882) two-cell internals.

Scope: pod_L/R base+lid, fairings (cap↔pod, pod↔strap), pod_floor_layout.
Frame: origin at cap centre; X across strap, Y along spine, Z up (mm).

Mount (from D4_contoured_v3 / d4.json, confirmed):
  pod_L_anchor: loc (0, -113.830, -27.839), rot_x +29.142°
  pod_R_anchor: loc (0, +113.830, -27.839), rot_x -29.142°

Envelope: grow D4's ~67×97×19.4 to hold D5 cavity 82×58×19.5
  → outer 92 × 97 × 22 (base) + lid 4.0; soft Y-end taper for D4 look.

Print orientation (bed = z=0):
  bases cavity UP; lids OUTER face DOWN via 180° about X + recalc normals
  (never flip_normals for orientation — that inverts volume).
  R side = true mirror (Scale -X) with flip_normals once to fix winding.

Reuses D5 FLOOR_LABEL_TABLE / emboss glyphs (DejaVu Bold, ≥5/0.8/0.6).

Run:
  cd hardware/rook/d6
  blender --background --factory-startup --python pod.py
"""

from __future__ import annotations

import json
import math
import os
import shutil
import struct
import sys
from collections import Counter

import bpy
from mathutils import Matrix, Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_D6 = _HERE
_D5_CAD = os.path.abspath(os.path.join(_HERE, "..", "d5", "cad"))
_COMMON = os.path.abspath(os.path.join(_HERE, "..", "..", "common", "cad", "lib"))
sys.path.insert(0, _COMMON)
sys.path.insert(0, _D5_CAD)
sys.path.insert(0, _D6)

import oc  # noqa: E402
import d5_dims as D  # noqa: E402
import build_d5 as d5  # noqa: E402 — glyph table, emboss, groove, flip_outer_down
import assembly as A  # noqa: E402

CHARCOAL = (0x26 / 255, 0x28 / 255, 0x2B / 255, 1.0)
ORANGE = (0xFF / 255, 0x6A / 255, 0x2B / 255, 1.0)
OAT = (0xEF / 255, 0xE8 / 255, 0xD8 / 255, 1.0)
WORLD = (0.94, 0.93, 0.90)

# ---------------------------------------------------------------- D6 pod envelope (D4 look + D5 cavity)

# D5 cavity kept; outer X forced to 92 (82+2×5). Slimmer Y/Z toward D4 67×97×19.4.
POD_CAVITY = D.POD_CAVITY                    # (82, 58, 19.5) — locked
POD_WALL = D.POD_WALL                        # 5.0
POD_L = A.POD_L                              # 92 — min across strap for cavity
POD_W = A.POD_W                              # 92 — along strap (was 97; still > D5 68)
POD_FLOOR = A.POD_FLOOR                      # 1.5 (slim vs D5 2.5)
POD_BASE_H = A.POD_BASE_H                    # 21.0
POD_LID_T = A.POD_LID_T                      # 4.0
POD_STACK_H = POD_BASE_H + POD_LID_T         # 25.0
PLAN_R = D.PLAN_R                            # 7.0
# Screw bosses stay inside cavity envelope (same as D5 relative to cavity)
POD_COLS = list(D.POD_COLS)                  # (±37, ±27)
# Soft end taper (D4 hard taper ≈4→15→19 over last ~20 mm of height look)
POD_TAPER_LEN = 18.0
POD_TAPER_DROP = 3.5                         # outer tip height drop (keeps cavity full)

# Cap↔pod M3 joint (matches cap.py pad)
POD_MOUNT_SIZE = A.POD_MOUNT_SIZE            # 36×4×14 recess on +Y end
POD_MOUNT_SCREWS = list(A.POD_MOUNT_SCREWS)

# D6 mount — D4 tilt; anchors shifted outboard (see assembly.py / DECISIONS.md)
MOUNT_Y = A.POD_ANCHOR_Y                     # ±124 (was D4 113.8)
MOUNT_Z = A.POD_ANCHOR_Z
MOUNT_ROT_X_DEG = A.TILT_DEG                 # L = +; R = −
MOUNT_L = {"loc": (0.0, -MOUNT_Y, MOUNT_Z), "rot_x_deg": +MOUNT_ROT_X_DEG}
MOUNT_R = {"loc": (0.0, +MOUNT_Y, MOUNT_Z), "rot_x_deg": -MOUNT_ROT_X_DEG}

# Cable toward cap-facing +Y local end (pods straddle cap on ±Y)
CABLE_D = 6.0
CABLE_SINK_D = 8.0
CABLE_SINK_H = 1.2

FLIP_OUTER_DOWN = {"pod_L_lid", "pod_R_lid"}
GLYPH_EXPORT_WELD = {
    "pod_L_base", "pod_R_base", "pod_floor_layout",
}

# Fairings — widened to span 92 mm pods (see assembly.py)
FAIRING_RUN = A.FAIRING_RUN
FAIRING_W0 = A.FAIRING_W0                    # 88 wide end
FAIRING_W1 = A.FAIRING_W1                    # 66 narrow end
FAIRING_H = A.FAIRING_H
FAIRING_R = D.FAIRING_R
FAIRING_EDGE_R = D.FAIRING_EDGE_R
# Assembly agree (owned by CW agent; pods do not re-export these):
#   clamp_bar 10×70×8, flange down, holes ±28.5, qty 8
#   saddle W=76; strap channel 46.45×3.4 along Y


# ---------------------------------------------------------------- helpers (thin wrappers)

def prepare(obj, merge=1e-4):
    """Weld + hole-fill; looser merge for glyph/boolean stacks."""
    return d5.prepare(obj, merge=merge)


def heal(obj, merge=0.02):
    """Aggressive manifold heal for export (bases with glyphs + taper)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=merge)
    bmesh.ops.dissolve_degenerate(bm, dist=merge, edges=list(bm.edges))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    for _ in range(3):
        boundary = [e for e in bm.edges if len(e.link_faces) < 2]
        if not boundary:
            break
        bmesh.ops.holes_fill(bm, edges=boundary, sides=12)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def remesh_manifold(obj, voxel=0.35):
    """Last-resort manifold: voxel remesh preserves volume, kills micro cracks."""
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    vox = obj.modifiers.new("heal_vox", "REMESH")
    vox.mode = "VOXEL"
    vox.voxel_size = voxel
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.view_layer.objects.active
    return prepare(obj, merge=voxel * 0.5)


def normalize_z0(obj):
    return d5.normalize_z0(obj)


def flip_outer_down(obj):
    """Rotate 180° about X; recalc normals — never flip_normals() for orientation."""
    return d5.flip_outer_down(obj)


def check_wt(obj):
    return d5.check_wt(obj)


def check_stl(path, q=1e-4):
    return d5.check_stl(path, q=q)


def slab(name, w, l, h, r=PLAN_R):
    return oc.rounded_rect(name, (w, l, h), r, anchor="bottom", segments=10)


def cut_cav(body, w, l, floor, h, r=5.0):
    oc.cut(body, oc.rounded_rect("cav", (w, l, h + 1), r,
                                 at=(0, 0, floor), anchor="bottom"))
    return body


def end_taper_skin(body, w, l, h, taper_len, drop):
    """D4-look outer tip chamfer on ±Y. Keeps central cavity full (cut above floor+cav)."""
    # Only shave the outer roof near tips — prism from top face down `drop` over `taper_len`.
    for sy in (-1, 1):
        tip = sy * (l / 2)
        oc.cut(body, oc.prism_x(f"taper{sy}", [
            (tip + sy * 0.5, h + 0.5),
            (tip - sy * taper_len, h + 0.5),
            (tip + sy * 0.5, h - drop),
        ], w + 4))
    return body


def soft_crown_edges(body, w, l, h, edge_r=2.0):
    """Skipped: bevel after boolean stack leaves non-manifold edges on bases.

    D4 crown cue is carried by end_taper_skin instead (printable, manifold).
    """
    return body


def mirror_x(obj):
    """True geometric mirror about YZ; fix winding once (outward normals)."""
    oc.bake(obj)
    obj.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    obj.data.flip_normals()
    return prepare(obj)


def bed_face_area_xy(obj):
    """Approx bed contact: sum face areas with normal ≈ −Z and z≈0."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    area = 0.0
    lo, _ = oc.bounds(obj)
    z0 = lo[2]
    for f in bm.faces:
        n = f.normal
        if n.z > -0.85:
            continue
        zc = sum((v.co.z for v in f.verts)) / 3.0
        if abs(zc - z0) > 0.35:
            continue
        area += f.calc_area()
    bm.free()
    return area


# ---------------------------------------------------------------- parts — POD BASE / LID

def pod_base(side="L"):
    """Print: cavity UP. Two-cell D5 internals in D4-length envelope.

    Cell swap: M3 driver only. Buzzer at (18,15). Cable + D8×1.2 countersink
    on cap-facing +Y end. Floor glyphs from D5 FLOOR_LABEL_TABLE.
    """
    b = slab(f"pod_{side}_base", POD_L, POD_W, POD_BASE_H, PLAN_R)
    cut_cav(b, POD_CAVITY[0], POD_CAVITY[1], POD_FLOOR, POD_CAVITY[2] + 1, r=5.0)
    d5.columns(b, POD_COLS, POD_FLOOR, POD_BASE_H)
    d5.groove(b, POD_L, POD_W, PLAN_R, POD_BASE_H, POD_WALL)
    d5.reg_lip(b, POD_L, POD_W, PLAN_R, POD_BASE_H, POD_WALL)

    # Floor ribs under cell cradle (assembly / stiffness)
    for sy in (-1, 1):
        oc.union(b, oc.box(f"frib{sy}", (POD_CAVITY[0] - 12, 1.6, 1.8),
                           at=(0.0, D.CELL_AT[1] + sy * 12.0, POD_FLOOR),
                           anchor="bottom"))

    # 18650 bay (D5)
    cell_d = D.CELL_POCKET_D + D.CELL_BAY_ADJUST
    cell_l = D.CELL_BAY_L
    cx, cy = D.CELL_AT
    oc.cut(b, oc.cylinder("cell", cell_d, cell_l,
                          at=(cx, cy, POD_FLOOR + cell_d / 2), axis="X"))

    # Buzzer pocket + sound port (+Y wall of cavity → toward +Y outer)
    buzz_at = D.BUZZ_AT  # (18, 15)
    d5.pocket_box(b, "buzz", D.BUZZ_POCKET, buzz_at, POD_FLOOR)
    # Port through +Y outer wall at buzzer X
    port_y = POD_W / 2
    oc.union(b, oc.cylinder("sboss", D.BUZZ_PORT_D + 4.0, 1.8,
                            at=(buzz_at[0], port_y + 0.9, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("sport", D.BUZZ_PORT_D, POD_WALL + 8,
                          at=(buzz_at[0], port_y, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("meshseat", D.BUZZ_PORT_D + 1.6, 0.8,
                          at=(buzz_at[0], port_y + 1.2, 11.0), axis="Y"))

    # Cap-facing cable (+Y local): through-hole + D8×1.2 countersink (D5 durable sub)
    cable_y = POD_W / 2 - POD_WALL / 2
    cable_z = POD_FLOOR + 6.0
    oc.cut(b, oc.cylinder("pcable", CABLE_D, POD_WALL + 6,
                          at=(0.0, cable_y, cable_z), axis="Y", segments=32))
    oc.cut(b, oc.cylinder("pcablesink", CABLE_SINK_D, CABLE_SINK_H,
                          at=(0.0, POD_W / 2 - CABLE_SINK_H / 2, cable_z),
                          axis="Y", segments=32))

    # Cap↔pod M3 joint: 36×4×14 recess + 4× clear holes matching cap.py pad
    pw, pt, ph = POD_MOUNT_SIZE
    recess = oc.box("pmount_rec", (pw + 0.4, pt + 0.3, ph + 0.4),
                    at=(0.0, POD_W / 2 - pt / 2, POD_FLOOR + 5.0), anchor="center")
    oc.cut(b, recess)
    for i, (lx, lz) in enumerate(POD_MOUNT_SCREWS):
        oc.cut(b, oc.cylinder(f"pmount_h{i}", D.CLEAR, POD_WALL + 8,
                              at=(lx, POD_W / 2 - pt / 2, POD_FLOOR + lz),
                              axis="Y", segments=24))

    # Floor glyphs — one table (d5.FLOOR_LABEL_TABLE)
    # (D4 tip taper applied AFTER glyphs — see end of function — so emboss stays
    # on a flat floor; taper only shaves outer roof near ±Y tips.)

    fz = POD_FLOOR
    d5.emboss_label(b, "BATT", (0.0, D.CELL_AT[1] - 18.0, fz))
    d5.emboss_label(b, "PLUS", (-28.0, 14.0, fz))
    d5.emboss_label(b, "MINUS", (28.0, 14.0, fz))
    d5.emboss_label(b, "BUZZ", (D.BUZZ_AT[0], D.BUZZ_AT[1] - 16.0, fz))
    d5.emboss_label(b, "PIN1", (0.0, POD_W / 2 - 16.0, fz), rot_z=0.0)  # arrow → +Y cable/cap
    # Screw order near bosses (inset toward centre so glyphs clear inserts)
    order = [("SCR1", POD_COLS[0]), ("SCR2", POD_COLS[1]),
             ("SCR3", POD_COLS[2]), ("SCR4", POD_COLS[3])]
    for key, (sx, sy) in order:
        d5.emboss_label(b, key, (sx * 0.72, sy * 0.72, fz))

    # D4-look outer tip taper last (cavity already full; roof-only shave)
    end_taper_skin(b, POD_L, POD_W, POD_BASE_H, POD_TAPER_LEN, POD_TAPER_DROP)

    if side == "R":
        mirror_x(b)
    return prepare(b, merge=0.01)


def pod_lid(side="L"):
    """Print: OUTER face DOWN (flip on export). ≥4.0 mm; ribs clear of cell; landing ring."""
    lw, ll = POD_L - 2 * D.REVEAL, POD_W - 2 * D.REVEAL
    lid = slab(f"pod_{side}_lid", lw, ll, POD_LID_T, PLAN_R - 0.5)
    d5.lid_fasteners(lid, POD_COLS, POD_LID_T)

    ring_w = 1.5
    ring_out_w, ring_out_l = lw - 5.0, ll - 5.0
    r_o = 3.5
    r_i = r_o - ring_w
    groove_depth = min(1.3, POD_LID_T - 2.5)
    outer = oc.rounded_rect("plring_o", (ring_out_w, ring_out_l, groove_depth), r_o,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("plring_i",
                            (ring_out_w - 2 * ring_w, ring_out_l - 2 * ring_w, groove_depth + 0.5),
                            r_i, at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))

    # Cross-ribs on mating face; clear cell Y envelope
    cell_y = D.CELL_AT[1]
    cell_r = (D.CELL_POCKET_D + D.CELL_BAY_ADJUST) / 2 + 1.0
    for i, dy in enumerate((-1.0, 1.0)):
        ry = cell_y + dy * (cell_r + 3.0)
        if abs(ry) > ll / 2 - 8:
            continue
        rib = oc.box(f"prib{i}", (lw - 16, 2.0, 1.5), at=(0, ry, 0.6))
        oc.union(lid, rib)

    # Lid posts (short standoffs on mating face near centre — clear cell)
    for i, (px, py) in enumerate([(0.0, 22.0), (0.0, -22.0)]):
        post = oc.cylinder(f"lpost{i}", 6.0, 1.8, at=(px, py, 0.0), anchor="bottom", segments=16)
        oc.union(lid, post)

    # Soft outer tip taper matching base silhouette (outer face = +Z before flip)
    end_taper_skin(lid, lw, ll, POD_LID_T, POD_TAPER_LEN * 0.7, 1.2)

    if side == "R":
        mirror_x(lid)
    return prepare(lid)


def pod_floor_layout(side="L"):
    """PLA coupon: cell rails, buzz fence, polarity + screw glyphs. Bed underside."""
    w, l = POD_CAVITY[0] - 2, POD_CAVITY[1]
    floor = oc.rounded_rect(f"pod_{side}_floor", (w, l, 2.0), 3.0, anchor="bottom", segments=6)
    fz = 2.0
    for sy in (-1, 1):
        oc.union(floor, oc.box(f"cellrail{sy}", (50.0, 1.4, d5.FLOOR_RIB_H),
                               at=(0.0, sy * 11.0, fz), anchor="bottom"))
    for sx, key in ((-1, "PLUS"), (1, "MINUS")):
        oc.union(floor, oc.box(f"cellend{sx}", (1.6, 18.0, d5.FLOOR_RIB_H),
                               at=(sx * 28.0, 0.0, fz), anchor="bottom"))
        d5.emboss_label(floor, key, (sx * 22.0, 18.0, fz))
    d5.emboss_label(floor, "BATT", (0.0, -20.0, fz))
    d5.locate_rib_rect(floor, "buzz", (20.0, 20.0), (22.0, 12.0), fz, wall=1.2)
    d5.emboss_label(floor, "BUZZ", (-18.0, 18.0, fz))
    d5.emboss_label(floor, "PIN1", (30.0, -18.0, fz), rot_z=-90.0)
    for key, (sx, sy) in (("SCR1", (-1, -1)), ("SCR2", (1, -1)),
                          ("SCR3", (-1, 1)), ("SCR4", (1, 1))):
        d5.emboss_label(floor, key, (sx * 32.0, sy * 22.0, fz))
    if side == "R":
        mirror_x(floor)
    return normalize_z0(prepare(floor))


# ---------------------------------------------------------------- fairings

def _fairing_body(name, run, w0, w1, h):
    f = oc.prism_y(name, [
        (0.0, 0.0),
        (w0 / 2, 0.0),
        (w1 / 2, h),
        (-w1 / 2, h),
        (-w0 / 2, 0.0),
    ], run)
    bound = oc.rounded_rect(f"{name}_bnd", (max(w0, w1) + 2, run + 2, h + 2),
                            FAIRING_R, at=(0, 0, -1), anchor="bottom", segments=10)
    oc.intersect(f, bound)
    try:
        oc.bevel(f, FAIRING_EDGE_R, segments=3)
        oc.apply_modifiers(f)
    except Exception:
        pass
    return f


def fairing_cap_pod(side="L"):
    """Bridge cap end → pod mount. W0=88→W1=66 × run 28 × H 14 (spans 92 mm pod)."""
    f = prepare(_fairing_body(f"fairing_cap_pod_{side}", FAIRING_RUN,
                              FAIRING_W0, FAIRING_W1, FAIRING_H))
    if side == "R":
        mirror_x(f)
    return f


def fairing_pod_strap(side="L"):
    """Blend pod into strap. W0=88→W1=66 × run 28 × H 14."""
    f = prepare(_fairing_body(f"fairing_pod_strap_{side}", FAIRING_RUN,
                              FAIRING_W0, FAIRING_W1, FAIRING_H))
    if side == "R":
        mirror_x(f)
    return f


# ---------------------------------------------------------------- export / render

PART_META = {
    "pod_L_base": ("PRINT: cavity UP; bed=underside z=0", "lid screws; cell cradle"),
    "pod_L_lid": ("PRINT: OUTER face DOWN z=0 (180° about X on export)", "lid screws; ribs"),
    "pod_R_base": ("PRINT: cavity UP; bed=underside z=0", "true mirror of L"),
    "pod_R_lid": ("PRINT: OUTER face DOWN z=0 (180° about X on export)", "true mirror of L"),
    "fairing_cap_pod_L": ("PRINT: long axis on bed; slope=WALL", "cap→pod blend"),
    "fairing_cap_pod_R": ("PRINT: long axis on bed; slope=WALL", "mirror"),
    "fairing_pod_strap_L": ("PRINT: long axis on bed; slope=WALL", "pod→strap blend"),
    "fairing_pod_strap_R": ("PRINT: long axis on bed; slope=WALL", "mirror"),
    "pod_floor_layout": ("PRINT: floor underside z=0; ribs/glyphs UP", "PLA coupon"),
}


def export_part(obj, path, meta_key=None):
    weld = 0.012 if meta_key in GLYPH_EXPORT_WELD else 1e-4
    prepare(obj, merge=weld)
    if meta_key in GLYPH_EXPORT_WELD or (meta_key and "base" in meta_key):
        heal(obj, merge=0.025)
    flipped = False
    if meta_key in FLIP_OUTER_DOWN:
        flip_outer_down(obj)
        flipped = True
    else:
        normalize_z0(obj)
    wt = check_wt(obj)
    # Bases/glyphs: remesh if still open so STLs slice cleanly
    if (meta_key in GLYPH_EXPORT_WELD or (meta_key and "base" in meta_key)) and not wt["watertight"]:
        print(f"  remesh {meta_key}: bad_edges={wt['bad_edges']}")
        remesh_manifold(obj, voxel=0.40)
        normalize_z0(obj)
        wt = check_wt(obj)
    dims = list(oc.size(obj))
    bed_area = bed_face_area_xy(obj) if flipped or (meta_key and "lid" in meta_key) else None
    oc.export_stl(obj, path)
    stl = check_stl(path)
    ok = bool(stl["watertight"] and wt["normals_outward"])
    tag = "OK" if ok else "LOOK"
    print(f"{tag}  {os.path.basename(path)}: {[round(x, 1) for x in dims]}  "
          f"bad_mesh={wt['bad_edges']} bad_stl={stl['bad_edges']}  out={wt['normals_outward']}  "
          f"bed={'OUTER' if flipped else 'as-built'}"
          + (f"  bed_area≈{bed_area:.0f}mm²" if bed_area is not None else ""))
    body = {
        "size_mm": dims,
        "watertight": wt,
        "stl": stl,
        "pass": ok,
        "stl_path": os.path.relpath(path, _D6),
        "export_flipped_outer_down": flipped,
        "normals_outward": wt["normals_outward"],
        "bed_face_at_z0": True,
        "bed_face_area_mm2": round(bed_area, 1) if bed_area is not None else None,
    }
    if meta_key and meta_key in PART_META:
        o, load = PART_META[meta_key]
        body.update({"orientation": o, "load_path": load})
    return body


def _mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


def _setup(res=(1400, 1050)):
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.render.resolution_x, s.render.resolution_y = res
    sh = s.display.shading
    sh.light, sh.color_type = "STUDIO", "MATERIAL"
    sh.show_cavity, sh.cavity_type = True, "BOTH"
    sh.show_object_outline = True
    w = bpy.data.worlds.new("w")
    w.color = WORLD
    s.world = w
    s.view_settings.view_transform = "Standard"


def render_objs(objs_colors, path, direction, pad=1.1):
    _setup()
    live = []
    for o, rgba, n in objs_colors:
        o.data.materials.clear()
        o.data.materials.append(_mat(n, rgba))
        live.append(o)
    lo = [min(oc.bounds(o)[0][i] for o in live) for i in range(3)]
    hi = [max(oc.bounds(o)[1][i] for o in live) for i in range(3)]
    centre = (Vector(lo) + Vector(hi)) / 2
    extent = (Vector(hi) - Vector(lo)).length
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(extent * pad, 1)
    cam = oc._link(bpy.data.objects.new("cam", cam_data))
    d = Vector(direction).normalized()
    cam.location = centre + d * extent * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def _section_cut(obj, axis="X"):
    """Keep +axis half for a section view (destructive)."""
    lo, hi = oc.bounds(obj)
    size = [hi[i] - lo[i] + 4 for i in range(3)]
    if axis == "X":
        cutter = oc.box("sec", (size[0], size[1] + 2, size[2] + 2),
                        at=(lo[0] - 1, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
    else:
        cutter = oc.box("sec", (size[0] + 2, size[1], size[2] + 2),
                        at=((lo[0] + hi[0]) / 2, lo[1] - 1, (lo[2] + hi[2]) / 2))
    oc.cut(obj, cutter)
    return prepare(obj)


def save_review_blend(path):
    """World-space L/R pods at D4 mounts + fairing stand-ins + empties."""
    oc.reset()
    # Build in local, then place at mounts
    lb = pod_base("L")
    ll = pod_lid("L")
    rb = pod_base("R")
    rl = pod_lid("R")
    # lids currently mating-at-z=0; raise to base top for assembly view
    oc.move(ll, dz=POD_BASE_H)
    oc.move(rl, dz=POD_BASE_H)

    def place(obj, mount):
        oc.bake(obj)
        rx = math.radians(mount["rot_x_deg"])
        obj.data.transform(Matrix.Rotation(rx, 4, "X"))
        lx, ly, lz = mount["loc"]
        oc.move(obj, dx=lx, dy=ly, dz=lz)

    place(lb, MOUNT_L)
    place(ll, MOUNT_L)
    place(rb, MOUNT_R)
    place(rl, MOUNT_R)

    # Empties for mount confirmation
    for name, m in (("pod_L_anchor", MOUNT_L), ("pod_R_anchor", MOUNT_R)):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 20
        e.location = m["loc"]
        e.rotation_euler = (math.radians(m["rot_x_deg"]), 0, 0)
        oc._link(e)

    fcl = fairing_cap_pod("L")
    fcr = fairing_cap_pod("R")
    fsl = fairing_pod_strap("L")
    fsr = fairing_pod_strap("R")
    # Rough world placement near D4 fairing bboxes
    oc.move(fcl, dy=-82, dz=-8)
    oc.move(fcr, dy=+82, dz=-8)
    oc.move(fsl, dy=-150, dz=-45)
    oc.move(fsr, dy=+150, dz=-45)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("saved", path)


def main():
    stl_dir = os.path.join(_D6, "stl")
    img_dir = os.path.join(_D6, "renders")
    rev_dir = os.path.join(_D6, "review")
    for d in (stl_dir, img_dir, rev_dir):
        os.makedirs(d, exist_ok=True)

    builders = [
        ("pod_L_base", lambda: pod_base("L"), "pod_L_base"),
        ("pod_L_lid", lambda: pod_lid("L"), "pod_L_lid"),
        ("pod_R_base", lambda: pod_base("R"), "pod_R_base"),
        ("pod_R_lid", lambda: pod_lid("R"), "pod_R_lid"),
        ("fairing_cap_pod_L", lambda: fairing_cap_pod("L"), "fairing_cap_pod_L"),
        ("fairing_cap_pod_R", lambda: fairing_cap_pod("R"), "fairing_cap_pod_R"),
        ("fairing_pod_strap_L", lambda: fairing_pod_strap("L"), "fairing_pod_strap_L"),
        ("fairing_pod_strap_R", lambda: fairing_pod_strap("R"), "fairing_pod_strap_R"),
        ("pod_floor_layout", lambda: pod_floor_layout("L"), "pod_floor_layout"),
    ]

    report = {
        "revision": "D6_pod_d4_skin_d5_internals",
        "d5_head": "6b1f882",
        "mount": {"L": MOUNT_L, "R": MOUNT_R, "source": "d4.json pod_*_anchor"},
        "envelope": {
            "outer_base_mm": [POD_L, POD_W, POD_BASE_H],
            "outer_lid_mm": [POD_L - 2 * D.REVEAL, POD_W - 2 * D.REVEAL, POD_LID_T],
            "cavity_mm": list(POD_CAVITY),
            "stack_mm": POD_STACK_H,
            "d4_ref_base": [67.02, 96.99, 19.38],
            "d5_ref_base": [D.POD_L, D.POD_W, D.POD_BASE_H],
            "note": "X grown 67→92 for 82 cavity; Y kept ~97 D4 length; H 22 for 19.5 cav",
        },
        "gasket": {
            "groove_w": D.GROOVE_W,
            "groove_d": D.GROOVE_D,
            "inner_land": D.GROOVE_INNER_LAND,
            "outer_land": D.GROOVE_OUTER_LAND,
        },
        "floor_glyphs": {
            "table": {k: v[0] for k, v in d5.FLOOR_LABEL_TABLE.items()},
            "char_h_mm": d5.GLYPH_CHAR_H,
            "stroke_mm": d5.GLYPH_STROKE,
            "relief_mm": round(d5.GLYPH_DEPTH - d5.GLYPH_EMBED, 2),
            "font": d5.GLYPH_FONT,
        },
        "cable": {"through_d": CABLE_D, "countersink": [CABLE_SINK_D, CABLE_SINK_H],
                  "axis": "+Y cap-facing"},
        "buzzer_at": list(D.BUZZ_AT),
        "print_orientation": (
            "bases cavity UP; lids rotated 180° about X on export (recalc normals, "
            "no flip_normals); R = Scale(-X) + flip_normals once for winding"
        ),
        "bodies": {},
        "pass": True,
    }

    lid_support_notes = {}

    for name, fn, meta in builders:
        oc.reset()
        obj = fn()
        path = os.path.join(stl_dir, f"{name}.stl")
        body = export_part(obj, path, meta)
        report["bodies"][name] = body
        if not body["pass"]:
            report["pass"] = False
        if "lid" in name and body.get("bed_face_area_mm2") is not None:
            # Flat-ish lid with soft taper: large bed face, no large supports expected
            area = body["bed_face_area_mm2"]
            lid_support_notes[name] = {
                "bed_face_area_mm2": area,
                "supports": (
                    "NONE expected for outer shell (flat outer on bed); "
                    "optional tiny supports under mating-face ribs/posts if they bridge"
                ),
                "note": "Outer-down; soft tip taper only — not a deep crown",
            }

    report["lid_print"] = lid_support_notes

    # Renders: iso / top / side / section of L base+lid
    oc.reset()
    lb = pod_base("L")
    ll = pod_lid("L")
    oc.move(ll, dz=POD_BASE_H + 6)
    colors = [(lb, CHARCOAL, "base"), (ll, CHARCOAL, "lid")]
    render_objs(colors, os.path.join(img_dir, "pod_iso.png"), (1.3, -1.4, 0.9))
    render_objs(colors, os.path.join(img_dir, "pod_top.png"), (0.01, 0.01, 1.0), pad=1.15)
    render_objs(colors, os.path.join(img_dir, "pod_side.png"), (1.0, 0.0, 0.05), pad=1.2)

    oc.reset()
    sec = pod_base("L")
    _section_cut(sec, "X")
    render_objs([(sec, CHARCOAL, "sec")], os.path.join(img_dir, "pod_section.png"),
                (0.2, -1.0, 0.3), pad=1.15)

    # Fairing lineup
    oc.reset()
    parts = [
        (fairing_cap_pod("L"), CHARCOAL, "f1"),
        (fairing_pod_strap("L"), ORANGE, "f2"),
    ]
    oc.move(parts[1][0], dx=90)
    render_objs(parts, os.path.join(img_dir, "pod_fairings.png"), (1.2, -1.2, 0.8))

    # review.blend
    blend_path = os.path.join(rev_dir, "pod_review.blend")
    try:
        save_review_blend(blend_path)
        report["review_blend"] = os.path.relpath(blend_path, _D6)
    except Exception as e:
        report["review_blend_error"] = str(e)
        print("review.blend save failed:", e)

    with open(os.path.join(stl_dir, "pod_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    # Verification markdown snippet written beside POD.md by post-step; dump key lines
    print("\n=== D6 POD SUMMARY ===")
    print("outer base:", POD_L, POD_W, POD_BASE_H)
    print("cavity:", POD_CAVITY)
    print("mount L:", MOUNT_L)
    print("mount R:", MOUNT_R)
    print("lid supports:", json.dumps(lid_support_notes, indent=2))
    print("PASS" if report["pass"] else "LOOK — check report.json")
    return report


if __name__ == "__main__":
    main()
