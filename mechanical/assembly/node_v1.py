"""Node V1 option 1, assembled on a neck with a spine ridge: cap on the
crest, a pod low on each side (inside the strap, electrodes on the skin),
the encased counterweight under the throat, cables from the cap to the pods.

Saves assembly/node_v1.blend, renders to renders/node_v1/, and writes
renders/node_v1/report.json with the mass budget and the balance check.

    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --factory-startup --python assembly/node_v1.py [-- --no-render]
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, HERE)
import bmesh
import bpy
from mathutils import Matrix, Vector

import dims as d
import node_concept as nc
import node_v1 as n
import oc

OUT = os.path.join(oc.ROOT, "renders", "node_v1")
OUT_BLEND = os.path.join(HERE, "node_v1.blend")

A, B = 125.0, 210.0          # neck semi-axes (~107 cm around)
RIDGE, RIDGE_W = 9.0, 15.0   # spine ridge on top of the neck
POD_T = 1.0                  # pod position, radians from the top

COL = {
    "pa12": ((0.50, 0.50, 0.49), 0.6, 0.0),
    "bar": ((0.42, 0.42, 0.41), 0.6, 0.0),
    "solar": ((0.02, 0.035, 0.07), 0.12, 0.0),
    "strap": ((0.05, 0.17, 0.55), 0.8, 0.0),
    "steel": ((0.55, 0.55, 0.57), 0.35, 1.0),
    "cell": ((0.10, 0.25, 0.55), 0.4, 0.0),
    "pcb": ((0.05, 0.30, 0.12), 0.45, 0.0),
    "gnss": ((0.80, 0.74, 0.60), 0.4, 0.0),
    "antenna": ((0.75, 0.55, 0.15), 0.4, 0.3),
    "cable": ((0.06, 0.06, 0.06), 0.7, 0.0),
    "neck": ((0.62, 0.55, 0.47), 0.95, 0.0),
}
nc.COL.update(COL)


def ridge(x, w=RIDGE_W):
    return RIDGE * math.exp(-((x / w) ** 2))


def neck_pt(t, out=0.0):
    """Point on the neck outline t radians clockwise from the top, pushed `out` along the normal."""
    x, z = A * math.sin(t), B * math.cos(t)
    if math.cos(t) > 0:
        z += ridge(x)  # the ridge is on top of the neck only
    nx, nz = math.sin(t) / A, math.cos(t) / B
    L = math.hypot(nx, nz)
    nx, nz = nx / L, nz / L
    return x + nx * out, z + nz * out, (nx, nz)


def neck():
    prof = []
    for k in range(160):
        t = 2 * math.pi * k / 160
        x, z, _ = neck_pt(t)
        prof.append((x, z))
    prof.reverse()  # counter-clockwise for the loft
    obj, _ = nc.loft("neck", prof, 330.0, 230.0, stations=64)
    return obj


def place(obj, M):
    oc.bake(obj)  # keep any oc.move() offsets before transforming
    obj.data.transform(M)
    obj.matrix_basis = Matrix.Identity(4)
    return obj


def mirror_x(obj):
    obj.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    obj.data.flip_normals()
    return obj


def pod_matrix(side):
    """Pod local frame to world: local z = 0 on the skin, local +X toward the crest (left pod)."""
    t = side * POD_T
    x, z, (nx, nz) = neck_pt(t, 0.3)
    th = math.atan2(nx, nz)
    return Matrix.Translation((x, 0, z)) @ Matrix.Rotation(th, 4, "Y")


def strap_points():
    lift = n.POD_BASE_H + n.POD_LID_T - n.CHANNEL_D
    half = (n.POD_L / 2 + 6) / 170.0  # half the pod length as an angle on the side of the neck
    pts = []
    for k in range(720):
        t = 2 * math.pi * k / 720
        tt = math.atan2(math.sin(t), math.cos(t))
        bump = 0.0
        for c in (POD_T, -POD_T):
            dd = abs(tt - c)
            if dd < half:
                bump = 1.0
            elif dd < half + 0.12:
                bump = max(bump, 0.5 * (1 + math.cos(math.pi * (dd - half) / 0.12)))
        x, z, (nx, nz) = neck_pt(t, n.STRAP_T / 2 + bump * lift)
        x = x if abs(x) > 1e-9 else 0.0
        # The strap tents over the spine ridge rather than following its sharp peak.
        if abs(x) < 40 and z > 0:
            z = max(z, B + RIDGE * math.exp(-((x / 40) ** 2)) * 0.95 + n.STRAP_T / 2 - (B - B * math.sqrt(max(0, 1 - (x / A) ** 2))))
        pts.append((x, z))
    return pts


def cable(name, p0, p1, c0, c1):
    cd = bpy.data.curves.new(name, "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = 2.7
    cd.bevel_resolution = 4
    sp = cd.splines.new("BEZIER")
    sp.bezier_points.add(1)
    a, b = sp.bezier_points
    a.co, a.handle_right, a.handle_left = Vector(p0), Vector(c0), Vector(p0)
    b.co, b.handle_left, b.handle_right = Vector(p1), Vector(c1), Vector(p1)
    o = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(nc.mat("cable"))
    return o


def build():
    oc.reset()
    parts, refs, masses = {}, [], {}

    # ---- cap
    z0 = B + RIDGE + n.STRAP_T - n.CHANNEL_D
    Mcap = Matrix.Translation((0, 0, z0))
    base, lid = n.cap_base(), n.cap_lid()
    oc.move(lid, dz=n.CAP_BASE_H)
    for o in (base, lid):
        place(o, Mcap)
    parts["cap_base"], parts["cap_lid"] = base, lid
    for sx in (-1, 1):
        bar = n.cap_bar()
        place(bar, Matrix.Translation((sx * 20.0, 0, z0 - n.CAP_BAR[2])))
        parts[f"cap_bar_{sx}"] = bar
    for r in n.cap_refs():
        refs.append(place(r, Mcap))

    # ---- pods: build the left one, then mirror it across the neck's midplane for the right.
    M = pod_matrix(-1)
    pb, pl = n.pod_base(), n.pod_lid()
    oc.move(pl, dz=n.POD_BASE_H)
    left = {"pod_base": pb, "pod_lid": pl}
    for sx in (-1, 1):
        bar = n.pod_bar()
        oc.move(bar, dx=sx * 32.0, dz=n.POD_BASE_H + n.POD_LID_T)
        left[f"pod_bar_{sx}"] = bar
    for o in left.values():
        place(o, M)
    for k, o in left.items():
        parts[k + "_L"] = o
        r = oc.mirror_copy(o, "X", name=o.name + "_R")
        oc.bake(r)
        parts[k + "_R"] = r
    for r in n.pod_refs():
        place(r, M)
        refs.append(r)
        m = oc.mirror_copy(r, "X", name=r.name + "_R")
        oc.bake(m)
        m["oc_reference"] = True
        refs.append(m)
    cable_in = M @ Vector((n.POD_L / 2 + 1.0, -2.0, 12.0))

    # ---- counterweight (no rotation: tub to the ground, lid and strap toward the throat)
    c = -(B + n.STRAP_T) - (n.CW_TUB_H + n.CW_LID_T - n.CHANNEL_D)
    Mcw = Matrix.Translation((0, 0, c))
    tub, cl = n.cw_tub(), n.cw_lid()
    oc.move(cl, dz=n.CW_TUB_H)
    for o in (tub, cl):
        place(o, Mcw)
    parts["cw_tub"], parts["cw_lid"] = tub, cl
    for r in n.cw_refs():
        refs.append(place(r, Mcw))

    # ---- strap, cables, neck
    strap = nc.band("strap", strap_points(), -n.STRAP_W / 2, n.STRAP_W / 2, n.STRAP_T)
    cables = []
    cable_z = n.CAP_FLOOR_Z + (n.CAP_BASE_H - n.CAP_FLOOR_Z) / 2
    for side in (-1, 1):
        p0 = (side * (n.CAP_W / 2 + 1.0), 0.0, z0 + cable_z)
        p1 = (-side * -cable_in.x if side > 0 else cable_in.x, cable_in.y, cable_in.z)
        x, z, _ = neck_pt(side * 0.55, 12.0)
        cables.append(cable(f"cable_{side}", p0, p1, (side * (n.CAP_W / 2 + 24.0), 0, z0 + cable_z - 4), (x, 0, z)))
    nk = neck()
    return parts, refs, strap, cables, nk


def mass_budget(parts):
    rho = oc.DENSITY["PA12"]
    g = {k: oc.volume_mm3(o) / 1000 * rho for k, o in parts.items()}
    cap_print = g["cap_base"] + g["cap_lid"] + g["cap_bar_-1"] + g["cap_bar_1"]
    pod_print = sum(v for k, v in g.items() if k.startswith("pod_") and k.endswith("_L"))
    cw_print = g["cw_tub"] + g["cw_lid"]
    kit = d.NRF9151_KIT["mass_g"]
    cap = cap_print + kit + 8 + 2 + 10 + 2 + n.P124["mass_g"] + 15     # kit, bq24074, IMU, patch, LTE flex, P124, screws/inserts/O-ring
    pod = pod_print + n.CELL["mass_g"] + d.QWIIC_BUZZER["mass_g"] + 8 + 12 + 10   # cell, buzzer, electrodes, screws, half the cable
    cw = cw_print + n.steel_mass_g() + 10 + 2 * 2.5                       # steel, screws/foam, bars
    return {"cap_g": round(cap), "pod_g_each": round(pod), "counterweight_g": round(cw),
            "cap_print_g": round(cap_print), "pod_print_g_each": round(pod_print), "cw_print_g": round(cw_print),
            "steel_g": round(n.steel_mass_g()), "strap_g": 130}


def balance(m):
    """Centre of mass below the neck centre, against Halter's published split."""
    z_cap = B + RIDGE + n.STRAP_T + 12.0
    _, z_pod, _ = neck_pt(POD_T, 14.0)
    z_cw = -(B + n.STRAP_T + 15.0)
    top = m["cap_g"] * z_cap + 2 * m["pod_g_each"] * z_pod
    total = m["cap_g"] + 2 * m["pod_g_each"] + m["counterweight_g"] + m["strap_g"]
    com = (top + m["counterweight_g"] * z_cw) / total
    halter = (488 * 215 - 912 * 225) / 1400   # 488 g top, 912 g counterweight (Verdon et al. 2026)
    m0 = total - m["counterweight_g"]
    need = (halter * m0 - top) / (z_cw - halter)  # counterweight whose COM matches Halter's
    return {"collar_g": round(total), "com_mm": round(com, 1), "halter_com_mm": round(halter, 1),
            "counterweight_needed_g": round(need), "z_pod_mm": round(z_pod, 1)}


if __name__ == "__main__":
    parts, refs, strap, cables, nk = build()
    m = mass_budget(parts)
    bal = balance(m)
    report = {"mass": m, "balance": bal,
              "note": "PA12 solid masses; FDM ASA at 40 % infill prints ~30 % lighter. Electronics masses: pub where known, est otherwise."}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))

    for k, o in parts.items():
        nc.dress(o, "bar" if "bar" in k else "pa12")
    for r in refs:
        nm = r.name
        mat = ("solar" if "p124" in nm or "p122" in nm else "cell" if "cell" in nm
               else "steel" if "steel" in nm or "electrode" in nm
               else "gnss" if "gps" in nm else "antenna" if "lte" in nm else "pcb")
        nc.dress(r, mat, smooth=False)
    nc.dress(strap, "strap", smooth=False)
    nc.dress(nk, "neck")
    if "--no-render" not in sys.argv:
        nc.scene()
        top = B + 25
        def shot(cam, name):
            os.makedirs(OUT, exist_ok=True)
            s = bpy.context.scene
            s.camera = cam
            s.render.filepath = os.path.join(OUT, name + ".png")
            bpy.ops.render.render(write_still=True)
        shot(nc.camera((420, -560, 430), (0, 0, 120), lens=38), "collar_hero")
        shot(nc.camera((0, -2400, 0), (0, 0, -10), ortho=900), "collar_front")
        shot(nc.camera((200, -260, top + 150), (0, 0, top - 5), lens=55), "cap")
        x, z, _ = neck_pt(POD_T, 20)
        shot(nc.camera((x + 260, -230, z + 40), (x, 0, z), lens=55), "pod_right")
        nk.hide_render = True
        shot(nc.camera((520, -760, 260), (0, 0, 0), lens=40), "collar_product")
        # Inside: lids off.
        for k in ("cap_lid", "pod_lid_L", "pod_lid_R", "cw_lid"):
            parts[k].hide_render = True
        for o in bpy.data.objects:
            if o.name.startswith("ref_p12"):
                o.hide_render = True
        strap.hide_render = True
        shot(nc.camera((260, -330, top + 220), (0, 0, top - 10), lens=50), "cap_inside")
        shot(nc.camera((x + 300, -200, z + 120), (x, 0, z), lens=50), "pod_inside")
        for k in ("cap_lid", "pod_lid_L", "pod_lid_R", "cw_lid"):
            parts[k].hide_render = False
        for o in bpy.data.objects:
            o.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print("saved", OUT_BLEND)
