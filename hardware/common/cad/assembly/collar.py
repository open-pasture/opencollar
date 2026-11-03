"""The whole V1-alpha collar, assembled: top unit, strap, bay and the bought
parts inside, with display materials. Saves assembly/collar_v1_alpha.blend
and renders presentation images to renders/collar/.

    ./build.sh --assembly
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import bmesh
import bpy
from mathutils import Vector

import collar as c
import oc

# Neck: a cow's neck just behind the head, roughly 25 cm wide and 42 cm tall
# (about 107 cm around, which suits the 48" strap).
NECK_A, NECK_B = 125.0, 210.0

OUT_BLEND = os.path.join(HERE, "collar_v1_alpha.blend")
OUT_RENDERS = os.path.join(oc.ROOT, "renders", "collar")

MATERIALS = {
    "shell": ((0.80, 0.79, 0.75), 0.55, 0.0),
    "clamp": ((0.62, 0.61, 0.58), 0.6, 0.0),
    "solar": ((0.03, 0.05, 0.10), 0.18, 0.0),
    "strap": ((0.05, 0.17, 0.55), 0.8, 0.0),
    "pcb": ((0.05, 0.30, 0.12), 0.45, 0.0),
    "battery": ((0.10, 0.10, 0.11), 0.5, 0.0),
    "gnss": ((0.78, 0.74, 0.62), 0.4, 0.0),
    "metal": ((0.55, 0.55, 0.57), 0.3, 1.0),
    "antenna": ((0.75, 0.55, 0.15), 0.4, 0.3),
}


def material(name):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    rgb, rough, metal = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    mat.diffuse_color = (*rgb, 1.0)
    return mat


def dress(obj, mat, collection, smooth=False):
    obj.data.materials.clear()
    obj.data.materials.append(material(mat))
    for col in obj.users_collection:
        col.objects.unlink(obj)
    collection.objects.link(obj)
    if smooth:
        # Smooth curved faces but keep hard edges crisp.
        for p in obj.data.polygons:
            p.use_smooth = True
        obj.modifiers.new("edges", "WEIGHTED_NORMAL").keep_sharp = True
        try:
            obj.data.set_sharp_from_angle(angle=math.radians(35))
        except AttributeError:
            pass
    return obj


def collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


# ---------------------------------------------------------------- strap

def strap_path(unit_z, cradle_top_z):
    """Closed centreline of the strap in the XZ plane, as (x, z) points."""
    t = c.STRAP_T
    pts, pinned = [], []

    # Under the top unit, in the channel (strap's top face on the channel ceiling).
    for i in range(61):
        x = -c.W / 2 - 4 + (c.W + 8) * i / 60
        ceiling = c.arch_z(x) + c.CHANNEL_D if abs(x) <= c.ARCH_HALF else c.CHANNEL_D
        pts.append((x, unit_z + ceiling - t / 2))
        pinned.append(True)

    # Right side, down around the neck.
    def side(sign, down):
        out = []
        angles = [math.radians(a) for a in range(62, -63, -4)]
        if not down:
            angles = list(reversed(angles))
        for a in angles:
            x = sign * (NECK_A + t / 2 + 1) * math.cos(a)
            z = (NECK_B + t / 2 + 1) * math.sin(a)
            out.append((x, z))
        return out

    right = side(1, True)
    pts += right
    pinned += [False] * len(right)

    # Through the bay cradle's tunnel.
    tunnel_z = cradle_top_z - c.CRADLE_T + c.TUNNEL_Z + c.TUNNEL[1] / 2
    for i in range(41):
        x = c.BAY[0] / 2 + 4 - (c.BAY[0] + 8) * i / 40
        pts.append((x, tunnel_z))
        pinned.append(True)

    left = side(-1, False)
    pts += left
    pinned += [False] * len(left)

    # Relax the free points so the strap runs smoothly between the pinned spans.
    for _ in range(60):
        new = list(pts)
        n = len(pts)
        for i in range(n):
            if pinned[i]:
                continue
            (x0, z0), (x2, z2) = pts[i - 1], pts[(i + 1) % n]
            new[i] = ((x0 + x2) / 2 * 0.6 + pts[i][0] * 0.4, (z0 + z2) / 2 * 0.6 + pts[i][1] * 0.4)
        pts = new
    return pts


def strap_mesh(pts, width, thickness):
    """A closed band of rectangular section along an XZ polyline."""
    bm = bmesh.new()
    n = len(pts)
    rings = []
    for i in range(n):
        (x0, z0), (x1, z1), (x2, z2) = pts[i - 1], pts[i], pts[(i + 1) % n]
        tx, tz = x2 - x0, z2 - z0
        L = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / L, tx / L
        ring = []
        for (ox, oy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            ring.append(bm.verts.new((x1 + nx * ox * thickness / 2, oy * width / 2, z1 + nz * ox * thickness / 2)))
        rings.append(ring)
    for i in range(n):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("strap")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("strap", me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------- build

def build(explode=0.0):
    oc.reset()
    root = bpy.context.scene.collection
    col_top = collection("Top unit")
    col_bay = collection("Bay")
    col_strap = collection("Strap")
    col_parts = collection("Bought parts")

    unit_z = NECK_B - c.ARCH_SAG + 1.0
    cradle_top = -NECK_B - 1.0

    base = c.top_base()
    lid = c.top_lid()
    oc.move(lid, dz=c.BASE_H + explode)
    for o in (base, lid):
        oc.move(o, dz=unit_z)
        oc.bake(o)
    dress(base, "shell", col_top, smooth=True).name = "top_unit_base"
    dress(lid, "shell", col_top, smooth=True).name = "top_unit_lid"

    for sx in (-1, 1):
        bar = c.clamp_bar()
        oc.rotate(bar, 180, "X")  # strap face up, screw heads down
        oc.move(bar, sx * c.BAR_X, 0, unit_z - explode * 0.5)
        oc.bake(bar)
        dress(bar, "clamp", col_top).name = f"clamp_bar_{'L' if sx < 0 else 'R'}"

    for r in c.top_refs(z_lid=c.BASE_H + explode):
        oc.move(r, dz=unit_z)
        oc.bake(r)
        name = r.name
        mat = ("battery" if name == "battery" else "gnss" if name == "gps_patch"
               else "metal" if name == "ground_plane" else "antenna" if name == "lte_antenna" else "pcb")
        dress(r, mat, col_parts)
    for p in c.panels(z_lid=c.BASE_H + explode * 1.6):
        oc.move(p, dz=unit_z)
        oc.bake(p)
        dress(p, "solar", col_top)

    cradle = c.bay_cradle()
    oc.move(cradle, dz=cradle_top - c.CRADLE_T)
    oc.bake(cradle)
    dress(cradle, "shell", col_bay, smooth=True).name = "bay_cradle"
    module = c.ballast_module()
    slab = c.steel_slab()
    for o in (module, slab):
        oc.move(o, dz=cradle_top - c.CRADLE_T - explode * 0.6)
        oc.bake(o)
    dress(module, "shell", col_bay, smooth=True).name = "ballast_module"
    dress(slab, "metal", col_parts)

    strap = strap_mesh(strap_path(unit_z, cradle_top), c.STRAP_W, c.STRAP_T)
    dress(strap, "strap", col_strap, smooth=True)
    return {"base": base, "lid": lid, "cradle": cradle, "module": module}


def setup_scene():
    s = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            s.render.engine = engine
            break
        except TypeError:
            continue
    s.render.resolution_x, s.render.resolution_y = 1800, 1350
    s.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.93, 0.93, 0.91, 1.0)
    bg.inputs["Strength"].default_value = 0.35
    s.world = world
    if hasattr(s, "eevee"):
        for attr, val in (("use_gtao", True), ("use_shadows", True), ("taa_render_samples", 64)):
            if hasattr(s.eevee, attr):
                setattr(s.eevee, attr, val)

    def sun(name, strength, direction, angle=12):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = strength
        ld.angle = math.radians(angle)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = (-Vector(direction)).to_track_quat("-Z", "Y").to_euler()
        s.collection.objects.link(lo)
    sun("key", 3.2, (0.5, -0.7, 0.9))
    sun("fill", 0.8, (-0.9, -0.3, 0.3), angle=40)
    sun("rim", 1.2, (0.0, 0.9, 0.6), angle=25)

    # Soft ground so the collar isn't floating in a void.
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -NECK_B - 140))
    ground = bpy.context.active_object
    ground.name = "ground"
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.55, 0.53, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    ground.data.materials.append(gm)
    if hasattr(ground, "is_shadow_catcher"):
        ground.is_shadow_catcher = False


def camera(name, loc, target, lens=50, ortho_scale=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start, cd.clip_end = 10, 20000
    if ortho_scale:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho_scale
    cam = bpy.data.objects.new(name, cd)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    return cam


def render(cam, name):
    s = bpy.context.scene
    s.camera = cam
    os.makedirs(OUT_RENDERS, exist_ok=True)
    s.render.filepath = os.path.join(OUT_RENDERS, name + ".png")
    bpy.ops.render.render(write_still=True)


def shots(unit_z):
    top = (0, 0, unit_z + 25)
    return {
        "collar_front": camera("cam_collar_front", (700, -1050, 380), (0, 0, 10), lens=50),
        "collar_side": camera("cam_collar_side", (0, -2000, 0), (0, 0, 0), ortho_scale=720),
        "top_unit": camera("cam_top_unit", (320, -420, unit_z + 330), top, lens=60),
        "top_unit_underside": camera("cam_top_under", (260, -380, unit_z - 260), (0, 0, unit_z), lens=60),
        "bay": camera("cam_bay", (260, -380, -NECK_B + 160), (0, 0, -NECK_B - 20), lens=60),
    }


if __name__ == "__main__":
    unit_z = NECK_B - c.ARCH_SAG + 1.0
    render_only = "--no-render" not in sys.argv

    # Exploded top unit first (renders only), then the assembled collar (saved).
    build(explode=70.0)
    setup_scene()
    cam = camera("cam_exploded", (380, -520, unit_z + 360), (0, 0, unit_z + 60), lens=50)
    if render_only:
        render(cam, "top_unit_exploded")

    parts = build()
    setup_scene()
    cams = shots(unit_z)
    # Hide the lid for one shot so the layout inside is visible.
    if render_only:
        for name, cam in cams.items():
            render(cam, name)
        hidden = [o for o in bpy.data.objects if o.name.startswith(("top_unit_lid", "solar_panel"))]
        for o in hidden:
            o.hide_render = True
        render(cams["top_unit"], "top_unit_inside")
        for o in hidden:
            o.hide_render = False
    bpy.context.scene.camera = cams["collar_front"]
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print("saved", OUT_BLEND)
