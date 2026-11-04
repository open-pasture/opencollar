"""Build review/d6_assembly.blend + 4 renders from assembly_check.py world STLs.
python3 build_assembly_blend.py <world_dir> <d4_stl_dir> <out_dir>   (bpy pip or Blender --python)"""
import bpy, os, sys, math, glob
from mathutils import Vector
a = [x for x in sys.argv if not x.endswith(".py")][-3:]
WORLD, D4, OUT = a
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.unit_settings.scale_length = 0.001; sc.unit_settings.length_unit = "MILLIMETERS"
def col(n):
    c = bpy.data.collections.new(n); sc.collection.children.link(c); return c
def mat(n, rgba, alpha=1.0):
    m = bpy.data.materials.new(n); m.diffuse_color = (*rgba[:3], alpha); return m
COL = {"cap": (0.15, 0.16, 0.17), "pod": (0.22, 0.24, 0.26), "cw": (0.30, 0.30, 0.28),
       "fairing": (0.85, 0.45, 0.15), "saddle": (0.55, 0.50, 0.40), "clamp": (0.75, 0.70, 0.20)}
def imp(path, c):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    for cc in o.users_collection: cc.objects.unlink(o)
    c.objects.link(o); return o
d6 = col("D6_assembly"); ghost = col("D4_contoured_v3_ghost")
for f in sorted(glob.glob(os.path.join(WORLD, "*.stl"))):
    o = imp(f, d6); k = next((k for k in COL if o.name.startswith(k)), "cap")
    o.data.materials.append(mat("m_" + o.name, COL[k]))
gm = mat("d4_ghost", (0.2, 0.6, 1.0), 0.25)
for f in sorted(glob.glob(os.path.join(D4, "*.stl"))):
    if os.path.basename(f).startswith("._"): continue
    o = imp(f, ghost); o.name = "D4_" + o.name; o.data.materials.append(gm)
    o.display_type = "WIRE"; o.show_in_front = True
    if o.name.startswith("D4_pod_L"):  # D4 R pod = mirror of L across y
        r = o.copy(); r.data = o.data.copy(); r.name = o.name.replace("_L_", "_R_mirror_")
        r.scale.y = -1; ghost.objects.link(r)
for n in ("pod_L", "pod_R"):
    e = bpy.data.objects.new(n + "_anchor", None); e.empty_display_type = "ARROWS"; e.empty_display_size = 15
    s = -1 if n == "pod_L" else 1
    # D6 outboard anchors (assembly.POD_ANCHOR_Y=124); L=+tilt R=-tilt
    e.location = (0, s * 124.0, -27.839); e.rotation_euler = (math.radians(-s * 29.1418), 0, 0); d6.objects.link(e)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "d6_assembly.blend"))
# renders: workbench, D4 ghost as wire overlay
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_xray = False; sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.render.film_transparent = False
w = bpy.data.worlds.new("w"); sc.world = w; w.color = (0.94, 0.92, 0.86)
# ghost wire for render: wireframe modifier so it renders
for o in ghost.objects:
    m = o.modifiers.new("wf", "WIREFRAME"); m.thickness = 0.35; o.display_type = "TEXTURED"
    o.data.materials.clear(); o.data.materials.append(mat("ghostR", (0.1, 0.45, 0.95), 1.0))
objs = [o for o in d6.objects if o.type == "MESH"]
lo = Vector([min((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
hi = Vector([max((o.matrix_world @ Vector(c))[i] for o in objs for c in o.bound_box) for i in range(3)])
ctr = (lo + hi) / 2; ext = (hi - lo).length
cam_d = bpy.data.cameras.new("cam"); cam_d.type = "ORTHO"; cam_d.ortho_scale = ext * 1.05; cam_d.clip_end = 1e5
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
for name, d in {"iso": (1, -1, 0.8), "front": (0, -1, 0.0001), "side": (1, 0, 0.0001), "top": (0.0001, 0, 1)}.items():
    d = Vector(d).normalized(); cam.location = ctr + d * ext * 2
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, f"d6_assembly_{name}.png"); bpy.ops.render.render(write_still=True)
print("OK")
