"""Shared helpers for OpenCollar part scripts.

Every part is a script in `parts/` that builds its geometry with these helpers,
then calls `finish()` to export, render, measure and check it. Units are
millimetres throughout: 1 Blender unit = 1 mm, and STL files come out in mm.

Run a part headless with `./build.sh <part>` (see README.md).
"""

import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# g/cm³. Solid-part mass; real prints weigh less with sparse infill.
DENSITY = {"ASA": 1.07, "PA12": 1.01, "TPU": 1.21, "PETG": 1.27}

# Colours for renders only (printed parts are light grey/white, see MATERIALS-AND-STRAP.md).
PART_COLOUR = (0.86, 0.85, 0.82, 1.0)
REF_COLOUR = (0.25, 0.55, 0.85, 1.0)
CUT_COLOUR = (0.85, 0.30, 0.22, 1.0)  # section faces


# ---------------------------------------------------------------- scene

def reset():
    """Empty scene in millimetres."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 0.001
    s.unit_settings.length_unit = "MILLIMETERS"


def _link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _from_bmesh(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return _link(bpy.data.objects.new(name, me))


# ---------------------------------------------------------------- primitives

def box(name, size, at=(0, 0, 0), anchor="center"):
    """Axis-aligned box. `anchor="bottom"` puts its base on `at` z."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    z = at[2] + (sz / 2 if anchor == "bottom" else 0)
    bmesh.ops.translate(bm, vec=(at[0], at[1], z), verts=bm.verts)
    return _from_bmesh(name, bm)


def cylinder(name, d, h, at=(0, 0, 0), axis="Z", segments=64, anchor="center"):
    """Cylinder of diameter `d`, height `h` along `axis`."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments,
                          radius1=d / 2, radius2=d / 2, depth=h)
    if anchor == "bottom":
        bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
    if axis == "X":
        bmesh.ops.rotate(bm, cent=(0, 0, 0), verts=bm.verts,
                         matrix=_rot(math.radians(90), "Y"))
    elif axis == "Y":
        bmesh.ops.rotate(bm, cent=(0, 0, 0), verts=bm.verts,
                         matrix=_rot(math.radians(-90), "X"))
    bmesh.ops.translate(bm, vec=at, verts=bm.verts)
    return _from_bmesh(name, bm)


def cone(name, d1, d2, h, at=(0, 0, 0), segments=64):
    """Truncated cone along Z: diameter `d1` at the bottom (`at` z), `d2` at the top."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments,
                          radius1=d1 / 2, radius2=d2 / 2, depth=h)
    bmesh.ops.translate(bm, vec=(at[0], at[1], at[2] + h / 2), verts=bm.verts)
    return _from_bmesh(name, bm)


def prism_y(name, profile_xz, length, at_y=0.0):
    """Extrude a closed XZ polygon (counter-clockwise seen from -Y) along Y,
    centred on `at_y`."""
    bm = bmesh.new()
    front = [bm.verts.new((x, at_y - length / 2, z)) for x, z in profile_xz]
    back = [bm.verts.new((x, at_y + length / 2, z)) for x, z in profile_xz]
    n = len(profile_xz)
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _from_bmesh(name, bm)


def prism_z(name, outline_xy, z0, h):
    """Extrude a closed XY polygon upward from z0 by h."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in outline_xy]
    hi = [bm.verts.new((x, y, z0 + h)) for x, y in outline_xy]
    n = len(outline_xy)
    bm.faces.new(lo)
    bm.faces.new(list(reversed(hi)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _from_bmesh(name, bm)


def rotate(obj, deg, axis, about=(0, 0, 0)):
    """Rotate mesh data about a world point."""
    from mathutils import Matrix
    bake(obj)
    t = Matrix.Translation(Vector(about))
    obj.data.transform(t @ Matrix.Rotation(math.radians(deg), 4, axis) @ t.inverted())
    return obj


def rounded_box(name, size, r, at=(0, 0, 0), anchor="center", segments=6):
    """Box with every edge rounded to radius `r`."""
    obj = box(name, size, at, anchor)
    bevel(obj, r, segments)
    return obj


def rounded_rect(name, size, r, at=(0, 0, 0), anchor="center", segments=12):
    """Box with only the four vertical edges rounded (a stadium-cornered plate)."""
    obj = box(name, size, at, anchor)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    vertical = [e for e in bm.edges
                if abs((e.verts[0].co - e.verts[1].co).normalized().z) > 0.99]
    bmesh.ops.bevel(bm, geom=vertical, offset=r, segments=segments,
                    affect="EDGES", profile=0.5)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def text(name, body, size, depth, at=(0, 0, 0), align="CENTER"):
    """Extruded text as a mesh (for engraving or embossing labels)."""
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = depth / 2
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_character = 1.25   # default spacing lets glyphs nearly touch (slivers)
    obj = _link(bpy.data.objects.new(name, cu))
    obj.location = (at[0], at[1], at[2] + depth / 2)
    return to_mesh(obj)


def to_mesh(obj):
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.view_layer.objects.active


def _rot(angle, axis):
    from mathutils import Matrix
    return Matrix.Rotation(angle, 4, axis)


# ---------------------------------------------------------------- operations

def bevel(obj, r, segments=6):
    m = obj.modifiers.new("bevel", "BEVEL")
    m.width = r
    m.segments = segments
    m.limit_method = "NONE"
    apply_modifiers(obj)


def apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    old = obj.data
    obj.data = me
    bpy.data.meshes.remove(old)


def _boolean(target, tools, op):
    for tool in tools if isinstance(tools, (list, tuple)) else [tools]:
        m = target.modifiers.new(op, "BOOLEAN")
        m.operation = op
        m.solver = "EXACT"
        m.object = tool
        apply_modifiers(target)
        bpy.data.objects.remove(tool)
    return target


def cut(target, *tools):
    """Subtract each tool from target. Tools are consumed."""
    return _boolean(target, list(tools), "DIFFERENCE")


def union(target, *tools):
    """Merge each tool into target. Tools are consumed."""
    return _boolean(target, list(tools), "UNION")


def intersect(target, tool):
    return _boolean(target, [tool], "INTERSECT")


def move(obj, dx=0, dy=0, dz=0):
    obj.location += Vector((dx, dy, dz))
    return obj


def mirror_copy(obj, axis="X", name=None):
    """A mirrored duplicate across the world origin plane."""
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.name = name or obj.name + "_mirror"
    _link(dup)
    i = "XYZ".index(axis)
    s = [1, 1, 1]
    s[i] = -1
    dup.data.transform(_scale(s))
    dup.data.flip_normals()
    loc = list(dup.location)
    loc[i] = -loc[i]
    dup.location = loc
    return dup


def _scale(s):
    from mathutils import Matrix
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][i] = s[i]
    return m


def reference(obj):
    """Mark an object as a reference body (a bought part). Rendered blue,
    used for clearance checks, never exported."""
    obj["oc_reference"] = True
    return obj


# ---------------------------------------------------------------- measuring

def bake(obj):
    """Apply location/rotation/scale so vertex coordinates are world coordinates."""
    # matrix_basis is built straight from location/rotation/scale, so it's
    # right even before the depsgraph has updated matrix_world.
    from mathutils import Matrix
    obj.data.transform(obj.matrix_basis)
    obj.matrix_basis = Matrix.Identity(4)


def bounds(obj):
    bake(obj)
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def size(obj):
    lo, hi = bounds(obj)
    return tuple(round(hi[i] - lo[i], 3) for i in range(3))


def _bm(obj):
    bake(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    return bm


def volume_mm3(obj):
    bm = _bm(obj)
    v = bm.calc_volume(signed=True)
    bm.free()
    return v


def overlaps(a, b):
    """True if two closed meshes intersect (a clearance failure)."""
    bake(a)
    bake(b)
    ta, tb = BVHTree.FromObject(a, bpy.context.evaluated_depsgraph_get()), \
        BVHTree.FromObject(b, bpy.context.evaluated_depsgraph_get())
    if ta.overlap(tb):
        return True
    # Fully contained: one mesh's vertex is inside the other.
    probe = b.matrix_world @ b.data.vertices[0].co
    return _inside(a, probe)


def _inside(obj, point):
    tree = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    hits, origin, ray = 0, Vector(point), Vector((0.0123, 0.0071, 1.0)).normalized()
    while True:
        loc, _, _, _ = tree.ray_cast(origin, ray)
        if loc is None:
            return hits % 2 == 1
        hits += 1
        origin = loc + ray * 1e-4


# ---------------------------------------------------------------- printability

def check_printable(obj, min_wall=1.2, overhang_deg=45.0):
    """Manifold, consistent normals, minimum wall thickness, overhang area.

    Thickness is measured like Blender's 3D Print Toolbox: from each face
    centre, cast a ray inward along -normal and measure the distance to the
    opposite wall.
    """
    bm = _bm(obj)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose = sum(1 for v in bm.verts if not v.link_edges)
    signed_volume = bm.calc_volume(signed=True)

    bmesh.ops.triangulate(bm, faces=bm.faces)
    tree = BVHTree.FromBMesh(bm)
    thin_faces, thin_area, thinnest, thinnest_at = 0, 0.0, math.inf, None
    zmin = min(v.co.z for v in bm.verts)
    cos_limit = math.cos(math.radians(90 - overhang_deg))
    overhang_area = 0.0
    for f in bm.faces:
        c, n = f.calc_center_median(), f.normal
        loc, _, idx, dist = tree.ray_cast(c - n * 1e-4, -n)
        if loc is not None and idx != f.index:
            if dist < thinnest:
                thinnest, thinnest_at = dist, tuple(round(x, 1) for x in c)
            if dist < min_wall:
                thin_faces += 1
                thin_area += f.calc_area()
        on_bed = all(abs(v.co.z - zmin) < 0.05 for v in f.verts)
        if n.z < -cos_limit and not on_bed:
            overhang_area += f.calc_area()
    bm.free()
    return {
        "manifold": non_manifold == 0 and loose == 0,
        "non_manifold_edges": non_manifold,
        "normals_outward": signed_volume > 0,
        "min_wall_mm": min_wall,
        "thinnest_mm": round(thinnest, 2) if thinnest != math.inf else None,
        "thinnest_at": thinnest_at,
        "thin_area_mm2": round(thin_area, 1),
        "overhang_area_mm2": round(overhang_area, 1),
    }


# ---------------------------------------------------------------- export

def export_stl(obj, path):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                          global_scale=1.0, apply_modifiers=True, ascii_format=False)


# ---------------------------------------------------------------- rendering

def _material(name, rgba):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def _setup_render(res=(1400, 1050)):
    s = bpy.context.scene
    s.render.engine = "BLENDER_WORKBENCH"
    s.render.resolution_x, s.render.resolution_y = res
    s.render.film_transparent = False
    sh = s.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = True
    sh.show_specular_highlight = False
    world = bpy.data.worlds.new("w")
    world.color = (0.96, 0.96, 0.95)
    s.world = world
    s.view_settings.view_transform = "Standard"


def _camera(target_lo, target_hi, direction):
    """Orthographic camera looking at the bounding box centre from `direction`."""
    centre = (Vector(target_lo) + Vector(target_hi)) / 2
    extent = (Vector(target_hi) - Vector(target_lo)).length
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = extent * 1.05
    cam_data.clip_end = extent * 20
    cam = _link(bpy.data.objects.new("cam", cam_data))
    d = Vector(direction).normalized()
    cam.location = centre + d * extent * 3
    if abs(d.z) > 0.99:
        # Straight down or up: keep +Y pointing up the image.
        cam.rotation_euler = (0, 0, 0) if d.z > 0 else (math.pi, 0, 0)
    else:
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


VIEWS = {
    "front": (0, -1, 0),
    "side": (1, 0, 0),
    "top": (0, 0, 1),
    "bottom": (0, 0, -1),
    "iso": (1, -1.2, 0.9),
}


def render_views(objs, out_dir, section_axis="Y"):
    """Front, side, top, bottom, iso and a section cut through the middle."""
    os.makedirs(out_dir, exist_ok=True)
    _setup_render()
    for o in objs:
        o.data.materials.clear()
        colour = REF_COLOUR if o.get("oc_reference") else PART_COLOUR
        o.data.materials.append(_material("ref" if o.get("oc_reference") else "part", colour))
    lo = [min(bounds(o)[0][i] for o in objs) for i in range(3)]
    hi = [max(bounds(o)[1][i] for o in objs) for i in range(3)]
    paths = []
    for view, d in VIEWS.items():
        cam = _camera(lo, hi, d)
        path = os.path.join(out_dir, f"{view}.png")
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)
        paths.append(path)
    paths.append(_render_section(objs, lo, hi, out_dir, section_axis))
    return paths


def _render_section(objs, lo, hi, out_dir, axis):
    """Cut every object in half along `axis` and look at the cut face."""
    i = "XYZ".index(axis)
    mid = (lo[i] + hi[i]) / 2
    big = max(hi[j] - lo[j] for j in range(3)) * 4
    halves = []
    for o in objs:
        dup = o.copy()
        dup.data = o.data.copy()
        _link(dup)
        at = [(lo[j] + hi[j]) / 2 for j in range(3)]
        at[i] = mid - big / 2
        keeper = box("keep", (big, big, big), at)
        keeper.data.materials.append(_material("cut", CUT_COLOUR))
        m = dup.modifiers.new("section", "BOOLEAN")
        m.operation, m.solver, m.object = "INTERSECT", "EXACT", keeper
        m.material_mode = "TRANSFER"
        apply_modifiers(dup)
        bpy.data.objects.remove(keeper)
        halves.append(dup)
        o.hide_render = True
    d = [0, 0, 0]
    d[i] = 1
    cam = _camera(lo, hi, d)
    path = os.path.join(out_dir, f"section_{axis.lower()}.png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    for h in halves:
        bpy.data.objects.remove(h)
    for o in objs:
        o.hide_render = False
    return path


# ---------------------------------------------------------------- finish

def finish(name, parts, spec=None, refs=(), material="ASA", min_wall=1.2,
           thin_area_allowed=0.0, section_axis="Y", notes=""):
    """Export, render, measure and check a part. Exits non-zero on any failure.

    parts:  {file_stem: obj} printed bodies, each exported as its own STL.
    spec:   {file_stem: {"size": (x, y, z), "tol": 0.5}} expected outer size.
    refs:   reference bodies (bought parts) for renders and clearance checks.
    thin_area_allowed: mm² of wall thinner than min_wall to tolerate. Only for
            cosmetic detail such as engraved labels, whose glyphs have
            knife-edge corners; say why in the part script.
    """
    spec = spec or {}
    exports = os.path.join(ROOT, "exports", name)
    renders = os.path.join(ROOT, "renders", name)
    os.makedirs(exports, exist_ok=True)
    report = {"part": name, "material": material, "bodies": {}, "clearance": [], "pass": True}

    for stem, obj in parts.items():
        dims = size(obj)
        vol = volume_mm3(obj)
        checks = check_printable(obj, min_wall=min_wall)
        body = {
            "size_mm": dims,
            "volume_cm3": round(vol / 1000, 2),
            "solid_mass_g": round(vol / 1000 * DENSITY[material], 1),
            "print": checks,
            "stl": os.path.relpath(os.path.join(exports, f"{stem}.stl"), ROOT),
        }
        ok = checks["manifold"] and checks["normals_outward"] and checks["thin_area_mm2"] <= thin_area_allowed
        if stem in spec:
            want, tol = spec[stem]["size"], spec[stem].get("tol", 0.5)
            body["spec_size_mm"] = want
            ok = ok and all(abs(dims[i] - want[i]) <= tol for i in range(3))
        body["pass"] = ok
        report["bodies"][stem] = body
        report["pass"] &= ok
        export_stl(obj, os.path.join(exports, f"{stem}.stl"))

    for ref in refs:
        for stem, obj in parts.items():
            hit = overlaps(obj, ref)
            report["clearance"].append({"body": stem, "ref": ref.name, "overlap": hit})
            report["pass"] &= not hit

    render_views(list(parts.values()) + list(refs), renders, section_axis)
    report["renders"] = os.path.relpath(renders, ROOT)
    if notes:
        report["notes"] = notes
    with open(os.path.join(renders, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    _print_report(report)
    if not report["pass"]:
        sys.exit(1)


def _print_report(r):
    print(f"\n=== {r['part']} ({r['material']}) ===")
    for stem, b in r["bodies"].items():
        p = b["print"]
        print(f"{'PASS' if b['pass'] else 'FAIL'}  {stem}: {b['size_mm']} mm, "
              f"{b['volume_cm3']} cm3, ~{b['solid_mass_g']} g solid")
        if "spec_size_mm" in b:
            print(f"      spec size {b['spec_size_mm']}")
        print(f"      manifold={p['manifold']} normals_out={p['normals_outward']} "
              f"thinnest={p['thinnest_mm']} mm at {p['thinnest_at']} (min {p['min_wall_mm']}), "
              f"thin area={p['thin_area_mm2']} mm2, overhang={p['overhang_area_mm2']} mm2")
    for c in r["clearance"]:
        print(f"{'FAIL' if c['overlap'] else 'PASS'}  clearance {c['body']} vs {c['ref']}")
    print(f"renders: {r['renders']}")
    print("RESULT:", "PASS" if r["pass"] else "FAIL")
