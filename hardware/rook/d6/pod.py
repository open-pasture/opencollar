"""D7r2 pod CAD — cavity rotated for D4-narrow outline.

Scope: pod_L/R base+lid, fairings (cap↔pod, pod↔strap), pod_floor_layout.
Frame: origin at cap centre; X across strap, Y along spine, Z up (mm).

Mount (locked from d6-integrate / assembly.py — do not move):
  L: loc (0, -126.0, -21.9), rot_x +29.142°
  R: loc (0, +126.0, -21.9), rot_x -29.142°
  Face at local Y = +POD_MOUNT_FACE_Y (=46); 36×4×14 recess + 4× M3 clear.

Envelope (D7r2 — cavity 90° vs D7r1):
  Cavity 82×58×19.5 kept; 82 runs along Y (long), 58 across X.
  Outer ~68 wide × ~97 long (D4 ≈67×97); narrower than cap 76.
  Mount face Y locked at 46 (strap-end grows to make length 97).
  Wall ≥3.5 at cells (here 5.0 → 68 outer). Smooth G1 lid crown.

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

# ---------------------------------------------------------------- D7r2 pod envelope (cavity rotated)

# Locked cavity size (82×58×19.5); ORIENTED in pod frame as X=58, Y=82, Z=19.5.
POD_CAVITY = D.POD_CAVITY                    # (82, 58, 19.5) — size locked
CAV_X = POD_CAVITY[1]                        # 58 — across strap
CAV_Y = POD_CAVITY[0]                        # 82 — along spine
CAV_Z = POD_CAVITY[2]                        # 19.5
POD_WALL = 5.0                               # ≥3.5 at cells → outer X = 68
POD_X_MAX = CAV_X + 2 * POD_WALL             # 68 — swell (narrower than cap 76)
POD_X_END = 66.0                             # slight tip taper (≤70)
POD_L = POD_X_MAX                            # max X extent
POD_LEN = A.POD_W                            # 97 — total Y length
POD_MOUNT_FACE_Y = A.POD_MOUNT_FACE_Y        # 46 — LOCKED recess face
POD_Y0 = POD_MOUNT_FACE_Y - POD_LEN / 2.0    # -2.5 — body centre (asymmetric)
POD_W = POD_LEN                              # alias: length along Y
POD_FLOOR = A.POD_FLOOR                      # 1.5
POD_BASE_H = A.POD_BASE_H                    # 22.2 mating plane
POD_LID_T = 4.0                              # locked durability
POD_STACK_H = POD_BASE_H + POD_LID_T         # ~26.2
POD_LID_CROWN = 1.8                          # convex dome sagitta (1.5–2.0)
PLAN_R = 8.0
PLAN_R_SWELL = 10.0
POD_TOP_EDGE_R = 6.0                         # R6 along top perimeter (D7r3)
# Full-width band covers most of the long cavity; soft tip taper only
POD_Y_SWELL = 38.0                           # half-length of full-width band
POD_SHOULDER_RUN = 8.0                       # 68→66 shoulder run
# Groove / lip follow oriented cavity + wall
POD_GROOVE_X = CAV_X + 2 * POD_WALL          # 68
POD_GROOVE_Y = CAV_Y + 2 * POD_WALL          # 92
# Screw bosses inset from oriented cavity corners
POD_COLS = [(sx * 22.0, sy * 36.0) for sx in (-1, 1) for sy in (-1, 1)]
POD_TAPER_LEN = 20.0                         # D7r3: slightly longer tip run
POD_TAPER_DROP = 6.0                         # D7r3: roof tip drop ~6 mm to fairing
# D7r6: deep skirt recesses clamps; width ≤ pod outline (no side overhang).
# Stack: channel 3.4 + clamp 8 + ≤1 mm proud + roof 1.6 ≈ 14
POD_SKIRT_H = 14.0
POD_SKIRT_FLARE = 0.0                        # no outward flange past pod width
POD_SKIRT_PLAN_R = 12.0                      # large rounded ends (D4)
# D7r7: long concave tangent flare into strap (not a vertical cliff)
POD_SKIRT_SHOULDER_R = 14.0
POD_PUBLIC_ID = "001"                        # recessed mono on lid outer
POD_ID_H = 9.0                               # D7r7: match D4 orange-dot ~8–10 mm
POD_ID_DEPTH = 0.55                          # low-contrast deboss

# Cap↔pod M3 joint (matches cap.py pad) — recess on +Y mount face
POD_MOUNT_SIZE = A.POD_MOUNT_SIZE            # 36×4×14
POD_MOUNT_SCREWS = list(A.POD_MOUNT_SCREWS)

# Cell bay / buzzer re-placed for Y-long cavity (cell axis along Y)
CELL_AT = (0.0, -2.0)                        # cradle centre
BUZZ_AT = (0.0, 28.0)                         # toward +Y mount, clear cells

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


def contoured_slab(name, x_max, x_end, length, height, y_swell, r_end=PLAN_R,
                   r_swell=PLAN_R_SWELL, shoulder_run=POD_SHOULDER_RUN,
                   y0=0.0):
    """Tapered plan: ~68 wide × length long; soft tip taper; optional Y shift.

    y0 is the body centre so the +Y face sits on POD_MOUNT_FACE_Y while length
    grows toward the strap end (asymmetric about local origin). Mesh is built
    in-place (no obj.location offset) so later cavity cuts stay aligned.
    """
    body = oc.rounded_rect(name, (x_end, length, height), r_end,
                           at=(0.0, y0, 0.0), anchor="bottom", segments=12)
    swell_len = min(length - 2.0, 2.0 * y_swell + shoulder_run)
    swell = oc.rounded_rect(f"{name}_swell", (x_max, swell_len, height), r_swell,
                            at=(0.0, y0, 0.0), anchor="bottom", segments=12)
    oc.union(body, swell)
    chamfer_plan_shoulder(body, x_max, x_end, y_swell, length / 2.0, height,
                          shoulder_run, y0=y0)
    return body


def chamfer_plan_shoulder(body, x_max, x_end, y_swell, y_half, h, run, y0=0.0):
    """Low chamfered shoulder: cut the step from swell width down to tip width."""
    run = min(run, max(2.0, y_half - y_swell - 1.0))
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            ya = y0 + sy * y_swell
            yb = y0 + sy * (y_swell + run)
            xs = sx * (x_max / 2.0)
            xe = sx * (x_end / 2.0)
            outline = [
                (sx * (x_max / 2.0 + 4.0), ya - sy * 1.0),
                (sx * (x_max / 2.0 + 4.0), y0 + sy * (y_half + 4.0)),
                (sx * (x_end / 2.0 - 1.0), y0 + sy * (y_half + 4.0)),
                (xe, yb),
                (xs, ya),
            ]
            oc.cut(body, oc.prism_z(f"sh_{int(sx)}_{int(sy)}", outline, -1.0, h + 3.0))
    return body


def cut_cav(body, w, l, floor, h, r=5.0):
    oc.cut(body, oc.rounded_rect("cav", (w, l, h + 1), r,
                                 at=(0, 0, floor), anchor="bottom"))
    return body


def end_taper_skin(body, w, l, h, taper_len, drop, y0=0.0):
    """D4-look outer tip chamfer on ±Y. Keeps central cavity full (cut above floor+cav)."""
    for sy in (-1, 1):
        tip = y0 + sy * (l / 2)
        oc.cut(body, oc.prism_x(f"taper{sy}", [
            (tip + sy * 0.5, h + 0.5),
            (tip - sy * taper_len, h + 0.5),
            (tip + sy * 0.5, h - drop),
        ], w + 4))
    return body


def top_perimeter_chamfer(body, w, l, h, r=POD_TOP_EDGE_R, y0=0.0):
    """R6-ish soft top perimeter: cut a 45° chamfer band around the roof edge."""
    r = min(float(r), h * 0.35, w * 0.12)
    if r < 1.0:
        return body
    # Four side wedges: drop the outer roof edge by `r` over run `r`
    for sx in (-1.0, 1.0):
        oc.cut(body, oc.prism_y(f"topch_x{int(sx+2)}", [
            (sx * (w / 2.0 + 1.0), h + 0.5),
            (sx * (w / 2.0 - r), h + 0.5),
            (sx * (w / 2.0 + 1.0), h - r),
        ], l + 6.0))
    for sy in (-1.0, 1.0):
        tip = y0 + sy * (l / 2.0)
        oc.cut(body, oc.prism_x(f"topch_y{int(sy+2)}", [
            (tip + sy * 1.0, h + 0.5),
            (tip - sy * r, h + 0.5),
            (tip + sy * 1.0, h - r),
        ], w + 6.0))
    return body


def strap_flare_skirt(body, w, l, y0=0.0, h=POD_SKIRT_H, flare=POD_SKIRT_FLARE):
    """Deep skirt: long R12+ tangent flare into strap (no vertical cliff).

    Extends below z=0 by `h`. Plan width never exceeds the pod body (`w`) so
    top/side views show no flange overhang. Multi-step concave cut eases the
    outer face into the strap. Channel 46.45×3.4 kept.
    """
    del flare  # D7r6: no outward overhang; kept in signature for call-site compat
    ch_w = float(A.SADDLE_CHANNEL_W)
    ch_d = float(A.SADDLE_CHANNEL_D)
    bar_w, bar_l, bar_h = A.CLAMP_BAR  # 10×70×8 — after 90°Z, long axis = X
    # ≤ pod width; clamp length 70 ≈ pod swell 68–70 so bars stay in footprint
    skirt_w = min(w, max(bar_l, ch_w + 4.0))
    skirt_l = min(l * 0.82, 82.0)
    plan_r = min(POD_SKIRT_PLAN_R, skirt_w / 2.0 - 1.0, skirt_l / 2.0 - 1.0)
    sk = oc.rounded_rect(
        "strap_skirt", (skirt_w, skirt_l, h), plan_r,
        at=(0.0, y0, -h), anchor="bottom", segments=12,
    )
    # D7r7: long concave flare (R≈POD_SKIRT_SHOULDER_R) — not a short cliff
    shoulder = min(float(POD_SKIRT_SHOULDER_R), h * 0.85, skirt_w * 0.22)
    # Two-step prism approximates a concave quarter-curve into the strap
    mid = shoulder * 0.45
    for sx in (-1.0, 1.0):
        oc.cut(sk, oc.prism_y(f"skirt_sh_x{int(sx + 2)}", [
            (sx * (skirt_w / 2.0 + 1.5), -h - 0.5),
            (sx * (skirt_w / 2.0 + 1.5), -h + shoulder),
            (sx * (skirt_w / 2.0 - mid * 0.35), -h + mid),
            (sx * (skirt_w / 2.0 - shoulder), -h - 0.5),
        ], skirt_l + 6.0))
    for sy in (-1.0, 1.0):
        tip = y0 + sy * (skirt_l / 2.0)
        oc.cut(sk, oc.prism_x(f"skirt_sh_y{int(sy + 2)}", [
            (tip + sy * 1.5, -h - 0.5),
            (tip + sy * 1.5, -h + shoulder),
            (tip - sy * mid * 0.35, -h + mid),
            (tip - sy * shoulder, -h - 0.5),
        ], skirt_w + 6.0))

    pocket_h = bar_h + 0.2
    for i, dy in enumerate((-25.0, 25.0)):
        oc.cut(sk, oc.box(
            f"clamp_pocket{i}",
            (min(bar_l + 1.0, skirt_w - 1.0), bar_w + 1.6, pocket_h + 0.4),
            at=(0.0, y0 + dy, -h), anchor="bottom",
        ))
    oc.cut(sk, oc.box(
        "skirt_ch", (ch_w, skirt_l + 4.0, ch_d + 0.4),
        at=(0.0, y0, -h + pocket_h), anchor="bottom",
    ))
    oc.union(body, sk)
    return body


def soft_crown_edges(body, w, l, h, edge_r=2.0):
    """Skipped on bases — boolean stack + bevel leaves non-manifold edges."""
    return body


def smooth_lid_crown(lid, w, l, h, sagitta=POD_LID_CROWN, y0=0.0):
    """Closed convex dome across the full outline — no dish, no X-facet.

    D7r6: low ellipsoid union (not a clipped UV-sphere) so studio lighting
    does not read an arrow/X. Flat rim (~6 mm) left for corner screws on top.
    """
    sagitta = max(1.5, min(float(sagitta), 2.2))
    rim = 6.0
    cw = max(w - 2.0 * rim, 20.0)
    cl = max(l - 2.0 * rim, 24.0)
    # UV sphere scaled into a wide shallow ellipsoid covering the inner field
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.0, location=(0.0, y0, h), segments=48, ring_count=24)
    sph = bpy.context.active_object
    sph.name = "crown_ellip"
    sph.scale = (cw / 2.0, cl / 2.0, sagitta)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # Keep only the upper half above the lid deck
    blank = oc.box(
        "crown_keep", (cw + 2.0, cl + 2.0, sagitta + 0.4),
        at=(0.0, y0, h + sagitta / 2.0), anchor="center",
    )
    oc.intersect(blank, sph)
    try:
        bpy.data.objects.remove(sph, do_unlink=True)
    except ReferenceError:
        pass
    if oc.volume_mm3(blank) > 40.0:
        oc.union(lid, blank)
    return lid


def mirror_x(obj):
    """True geometric mirror about YZ; fix winding once (outward normals)."""
    oc.bake(obj)
    obj.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    obj.data.flip_normals()
    return prepare(obj)


def mirror_for_R(obj):
    """R pod: mirror X, then flip Y so the mount face (−Y) points at the cap.

    L keeps mount at +Y (toward world origin). R at +126 needs mount at local −Y;
    without the Y flip the long strap-end would dig into the cap.
    Two mirrors = proper rotation (winding preserved) — do not flip_normals.
    """
    oc.bake(obj)
    obj.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    obj.data.transform(Matrix.Scale(-1, 4, (0, 1, 0)))
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
    """Print: cavity UP. Oriented cavity (58 across X, 82 along Y) in ~68×97 shell.

    Mount face / recess / hole pattern locked at Y=+POD_MOUNT_FACE_Y.
    Cell bay axis along Y; buzzer toward +Y; cable + countersink on mount end.
    """
    b = contoured_slab(f"pod_{side}_base", POD_X_MAX, POD_X_END, POD_LEN, POD_BASE_H,
                       POD_Y_SWELL, r_end=PLAN_R, r_swell=PLAN_R_SWELL,
                       shoulder_run=POD_SHOULDER_RUN, y0=POD_Y0)
    # Oriented cavity centred on origin (Y from -41..+41); body +Y face at +46
    cut_cav(b, CAV_X, CAV_Y, POD_FLOOR, CAV_Z + 1, r=5.0)
    d5.columns(b, POD_COLS, POD_FLOOR, POD_BASE_H)
    d5.groove(b, POD_GROOVE_X, POD_GROOVE_Y, PLAN_R, POD_BASE_H, POD_WALL)
    d5.reg_lip(b, POD_GROOVE_X, POD_GROOVE_Y, PLAN_R, POD_BASE_H, POD_WALL)

    # Floor ribs along cell axis (Y)
    for sx in (-1, 1):
        oc.union(b, oc.box(f"frib{sx}", (1.6, CAV_Y - 16.0, 1.8),
                           at=(sx * 12.0, CELL_AT[1], POD_FLOOR),
                           anchor="bottom"))

    # 18650 bay — long axis along Y (rotated with cavity)
    cell_d = D.CELL_POCKET_D + D.CELL_BAY_ADJUST
    cell_l = D.CELL_BAY_L
    cx, cy = CELL_AT
    oc.cut(b, oc.cylinder("cell", cell_d, cell_l,
                          at=(cx, cy, POD_FLOOR + cell_d / 2), axis="Y"))

    # Buzzer toward +Y mount end; sound port through +Y outer wall
    d5.pocket_box(b, "buzz", D.BUZZ_POCKET, BUZZ_AT, POD_FLOOR)
    port_y = POD_MOUNT_FACE_Y
    oc.union(b, oc.cylinder("sboss", D.BUZZ_PORT_D + 4.0, 1.8,
                            at=(BUZZ_AT[0], port_y + 0.9, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("sport", D.BUZZ_PORT_D, POD_WALL + 8,
                          at=(BUZZ_AT[0], port_y, 11.0), axis="Y"))
    oc.cut(b, oc.cylinder("meshseat", D.BUZZ_PORT_D + 1.6, 0.8,
                          at=(BUZZ_AT[0], port_y + 1.2, 11.0), axis="Y"))

    # Cap-facing cable (+Y mount face)
    cable_y = POD_MOUNT_FACE_Y - POD_WALL / 2
    cable_z = POD_FLOOR + 6.0
    oc.cut(b, oc.cylinder("pcable", CABLE_D, POD_WALL + 6,
                          at=(0.0, cable_y, cable_z), axis="Y", segments=32))
    oc.cut(b, oc.cylinder("pcablesink", CABLE_SINK_D, CABLE_SINK_H,
                          at=(0.0, POD_MOUNT_FACE_Y - CABLE_SINK_H / 2, cable_z),
                          axis="Y", segments=32))

    # Cap↔pod M3 joint on locked mount face
    pw, pt, ph = POD_MOUNT_SIZE
    mz = POD_BASE_H / 2.0
    # Side wall beside recess: (POD_X_MAX - pw) / 2 ≥ 3 mm
    recess = oc.box("pmount_rec", (pw + 0.4, pt + 0.3, ph + 0.4),
                    at=(0.0, POD_MOUNT_FACE_Y - pt / 2, mz), anchor="center")
    oc.cut(b, recess)
    for i, (lx, lz) in enumerate(POD_MOUNT_SCREWS):
        oc.cut(b, oc.cylinder(f"pmount_h{i}", D.CLEAR, POD_WALL + 8,
                              at=(lx, POD_MOUNT_FACE_Y - pt / 2, mz + (lz - ph / 2)),
                              axis="Y", segments=24))

    fz = POD_FLOOR
    d5.emboss_label(b, "BATT", (0.0, CELL_AT[1] - 22.0, fz))
    d5.emboss_label(b, "PLUS", (-18.0, CELL_AT[1] + 22.0, fz))
    d5.emboss_label(b, "MINUS", (18.0, CELL_AT[1] + 22.0, fz))
    d5.emboss_label(b, "BUZZ", (0.0, BUZZ_AT[1] - 14.0, fz))
    d5.emboss_label(b, "PIN1", (0.0, POD_MOUNT_FACE_Y - 14.0, fz), rot_z=0.0)
    for key, (sx, sy) in (("SCR1", POD_COLS[0]), ("SCR2", POD_COLS[1]),
                          ("SCR3", POD_COLS[2]), ("SCR4", POD_COLS[3])):
        d5.emboss_label(b, key, (sx * 0.70, sy * 0.70, fz))

    end_taper_skin(b, POD_L, POD_LEN, POD_BASE_H, POD_TAPER_LEN, POD_TAPER_DROP,
                   y0=POD_Y0)
    # Heal the boolean-heavy shell BEFORE attaching the skirt so the union
    # doesn't inherit open edges that collapse under remesh.
    prepare(b, merge=0.012)
    heal(b, merge=0.03)
    # D7r6: skirt ≤ pod width, tangent into strap, clamp pockets
    strap_flare_skirt(b, POD_L, POD_LEN, y0=POD_Y0)

    if side == "R":
        mirror_for_R(b)
    return prepare(b, merge=0.01)


def pod_lid(side="L"):
    """Print: OUTER face DOWN. Closed convex dome; screws on flat rim; ID 001."""
    reveal = D.REVEAL
    # D7r6: nearly full outline so end-on view is a closed lid, not an open box
    lx_max = POD_X_MAX - 2 * reveal
    lx_end = POD_X_END - 2 * reveal
    ll = POD_LEN - 2 * reveal
    y_swell = max(8.0, POD_Y_SWELL - reveal)
    lid = contoured_slab(f"pod_{side}_lid", lx_max, lx_end, ll, POD_LID_T, y_swell,
                         r_end=max(PLAN_R - 0.5, 8.0), r_swell=max(PLAN_R_SWELL - 0.5, 8.0),
                         shoulder_run=max(POD_SHOULDER_RUN - 1.0, 6.0),
                         y0=POD_Y0)
    d5.lid_fasteners(lid, POD_COLS, POD_LID_T)

    # Landing ring on mating face only (z≈0) — outer stays closed
    ring_w = 1.5
    ring_out_w = POD_GROOVE_X - 2 * reveal - 5.0
    ring_out_l = POD_GROOVE_Y - 2 * reveal - 5.0
    r_o = 3.5
    r_i = r_o - ring_w
    groove_depth = min(1.3, POD_LID_T - 2.5)
    outer = oc.rounded_rect("plring_o", (ring_out_w, ring_out_l, groove_depth), r_o,
                            at=(0, 0, -0.1), anchor="bottom")
    inner = oc.rounded_rect("plring_i",
                            (ring_out_w - 2 * ring_w, ring_out_l - 2 * ring_w, groove_depth + 0.5),
                            r_i, at=(0, 0, -0.2), anchor="bottom")
    oc.cut(lid, oc.cut(outer, inner))

    rib_len = min(CAV_Y - 20.0, ll - 24.0)
    for i, sx in enumerate((-1.0, 1.0)):
        rib = oc.box(f"prib{i}", (2.0, rib_len, 1.5), at=(sx * 10.0, CELL_AT[1], 0.6))
        oc.union(lid, rib)

    for i, (px, py) in enumerate([(0.0, 28.0), (0.0, -28.0)]):
        post = oc.cylinder(f"lpost{i}", 6.0, 1.8, at=(px, py, 0.0),
                           anchor="bottom", segments=16)
        oc.union(lid, post)

    # Closed convex dome across full outline; light tip ease only (no open end)
    smooth_lid_crown(lid, lx_max, ll, POD_LID_T, sagitta=POD_LID_CROWN, y0=POD_Y0)
    end_taper_skin(lid, lx_max, ll, POD_LID_T + POD_LID_CROWN,
                   POD_TAPER_LEN * 0.55, min(POD_TAPER_DROP * 0.25, 1.5), y0=POD_Y0)
    top_perimeter_chamfer(lid, lx_max, ll, POD_LID_T + POD_LID_CROWN,
                          r=min(2.0, POD_TOP_EDGE_R * 0.35), y0=POD_Y0)

    # Screw heads ON the flat rim (proud of outer deck) — D4 closed-lid read
    z_rim = POD_LID_T
    for i, (sx, sy) in enumerate(POD_COLS):
        head = oc.cylinder(
            f"pscrew_head{i}", 5.2, 1.2,
            at=(sx, sy, z_rim), anchor="bottom", segments=20,
        )
        oc.union(lid, head)

    # D7r7: debossed "001" — 9 mm (≈D4 orange-dot H), low-contrast, strap end.
    # +90°Z so reading runs local +Y (strap→cap): readable in side AND top cams
    # when the collar hangs. Letter block sits toward the strap (base toward strap).
    try:
        z_outer = POD_LID_T + POD_LID_CROWN
        font_size = POD_ID_H * 2.0  # DejaVu size≈2× capital H
        glyph = d5._text_mesh(POD_PUBLIC_ID, font_size, POD_ID_DEPTH + 0.15)
        oc.bake(glyph)
        glyph.data.transform(Matrix.Rotation(math.radians(90.0), 4, "Z"))
        lo, hi = oc.bounds(glyph)
        id_y = POD_Y0 - (ll * 0.30)  # toward strap end (−Y for L)
        oc.move(
            glyph,
            dx=0.0 - (lo[0] + hi[0]) / 2.0,
            dy=id_y - (lo[1] + hi[1]) / 2.0,
            dz=(z_outer - POD_ID_DEPTH) - lo[2],
        )
        oc.cut(lid, glyph)
    except Exception as exc:
        print(f"  public ID emboss skipped: {exc}")

    if side == "R":
        mirror_for_R(lid)
    return prepare(lid)


def pod_floor_layout(side="L"):
    """PLA coupon: oriented cavity (58×82), cell rails along Y, glyphs readable."""
    w, l = CAV_X - 2, CAV_Y - 2
    floor = oc.rounded_rect(f"pod_{side}_floor", (w, l, 2.0), 3.0, anchor="bottom", segments=6)
    fz = 2.0
    for sx in (-1, 1):
        oc.union(floor, oc.box(f"cellrail{sx}", (1.4, 50.0, d5.FLOOR_RIB_H),
                               at=(sx * 11.0, 0.0, fz), anchor="bottom"))
    for sy, key in ((-1, "PLUS"), (1, "MINUS")):
        oc.union(floor, oc.box(f"cellend{sy}", (18.0, 1.6, d5.FLOOR_RIB_H),
                               at=(0.0, sy * 28.0, fz), anchor="bottom"))
        d5.emboss_label(floor, key, (18.0, sy * 22.0, fz))
    d5.emboss_label(floor, "BATT", (0.0, -8.0, fz))
    d5.locate_rib_rect(floor, "buzz", (20.0, 20.0), (0.0, 28.0), fz, wall=1.2)
    d5.emboss_label(floor, "BUZZ", (0.0, 18.0, fz))
    d5.emboss_label(floor, "PIN1", (0.0, 34.0, fz), rot_z=0.0)
    for key, (sx, sy) in (("SCR1", (-1, -1)), ("SCR2", (1, -1)),
                          ("SCR3", (-1, 1)), ("SCR4", (1, 1))):
        d5.emboss_label(floor, key, (sx * 20.0, sy * 32.0, fz))
    if side == "R":
        mirror_for_R(floor)
    return normalize_z0(prepare(floor))


# ---------------------------------------------------------------- fairings (D7 continuous loft via fairing.py)

import fairing as fairing_lib  # noqa: E402


def fairing_cap_pod(side="L"):
    """Cap↔pod: continuous wedge kissing pod outer (~68)."""
    f = prepare(fairing_lib.fairing_cap_pod(side))
    if side == "R":
        mirror_x(f)
    return normalize_z0(f)


def fairing_pod_strap(side="L"):
    """Pod↔strap: continuous wedge from pod outer into strap path."""
    f = prepare(fairing_lib.fairing_pod_strap(side))
    if side == "R":
        mirror_x(f)
    return normalize_z0(f)


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
        # 0.32 balances taper retention vs manifold; retry coarser if still open
        for vx in (0.32, 0.42, 0.55):
            remesh_manifold(obj, voxel=vx)
            heal(obj, merge=max(0.03, vx * 0.08))
            normalize_z0(obj)
            wt = check_wt(obj)
            print(f"  remesh@{vx}: bad_edges={wt['bad_edges']} wt={wt['watertight']}")
            if wt["watertight"]:
                break
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
        "revision": "D7_pod_tapered_swell_d5_internals",
        "d5_head": "6b1f882",
        "d6_integrate_head": "96f3b30",
        "mount": {"L": MOUNT_L, "R": MOUNT_R, "source": "assembly.py d6-integrate locked"},
        "envelope": {
            "outer_base_mm": [POD_X_MAX, POD_LEN, POD_BASE_H],
            "outer_tip_width_mm": POD_X_END,
            "mount_face_y": POD_MOUNT_FACE_Y,
            "swell_half_y_mm": POD_Y_SWELL,
            "shoulder_run_mm": POD_SHOULDER_RUN,
            "plan_r_mm": PLAN_R,
            "outer_lid_mm": [POD_X_MAX - 2 * D.REVEAL, POD_LEN - 2 * D.REVEAL, POD_LID_T],
            "lid_crown_sagitta_mm": POD_LID_CROWN,
            "cavity_mm": list(POD_CAVITY),
            "cavity_oriented_xyz": [CAV_X, CAV_Y, CAV_Z],
            "stack_mm": POD_STACK_H,
            "d4_ref_base": [67.02, 96.99, 19.38],
            "d5_ref_base": [D.POD_L, D.POD_W, D.POD_BASE_H],
            "d7r1_ref_base": [92.0, 92.0, 22.2],
            "note": (
                "D7r2: cavity rotated — 58 across X / 82 along Y; outer ~68×97; "
                f"mount face Y={POD_MOUNT_FACE_Y} locked; smooth lid crown "
                f"sagitta {POD_LID_CROWN}; cavity size 82×58×19.5 locked"
            ),
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
        "buzzer_at": list(BUZZ_AT),
        "cell_at": list(CELL_AT),
        "cell_axis": "Y",
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

    # Renders: iso / top / side for L and R (shaded charcoal — not black) + L section
    for side in ("L", "R"):
        oc.reset()
        b = pod_base(side)
        lid = pod_lid(side)
        oc.move(lid, dz=POD_BASE_H + 6)
        colors = [(b, CHARCOAL, "base"), (lid, OAT, "lid")]
        tag = f"pod_{side}"
        render_objs(colors, os.path.join(img_dir, f"{tag}_iso.png"), (1.3, -1.4, 0.9))
        render_objs(colors, os.path.join(img_dir, f"{tag}_top.png"), (0.01, 0.01, 1.0), pad=1.15)
        render_objs(colors, os.path.join(img_dir, f"{tag}_side.png"), (1.0, 0.0, 0.05), pad=1.2)
        # Back-compat aliases for L (prior D6 names)
        if side == "L":
            shutil.copyfile(os.path.join(img_dir, f"{tag}_iso.png"),
                            os.path.join(img_dir, "pod_iso.png"))
            shutil.copyfile(os.path.join(img_dir, f"{tag}_top.png"),
                            os.path.join(img_dir, "pod_top.png"))
            shutil.copyfile(os.path.join(img_dir, f"{tag}_side.png"),
                            os.path.join(img_dir, "pod_side.png"))

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
    print("\n=== D7 POD SUMMARY ===")
    print("swell/tip/length/h:", POD_X_MAX, POD_X_END, POD_W, POD_BASE_H)
    print("cavity:", POD_CAVITY)
    print("mount L:", MOUNT_L)
    print("mount R:", MOUNT_R)
    print("lid supports:", json.dumps(lid_support_notes, indent=2))
    print("PASS" if report["pass"] else "LOOK — check report.json")
    return report


if __name__ == "__main__":
    main()
