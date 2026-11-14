"""Post-export STL clean (Blender bmesh): merge float32-duplicate verts, collapse zero-area slivers, re-triangulate.
Run after d4pod.py; rewrites ../stl/action_pod_*.stl in place and prints bad-edge / zero-area counts before/after."""
import os,sys,glob,bpy,bmesh
H=os.path.dirname(os.path.abspath(__file__))
def stats(bm):
  return sum(1 for e in bm.edges if len(e.link_faces)!=2),sum(1 for f in bm.faces if f.calc_area()<1e-8)
def clean(path):
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.wm.stl_import(filepath=path);o=bpy.context.selected_objects[0]
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=bm.faces);before=stats(bm)
  for d in (1e-5,1e-4,5e-4,1e-3,5e-3,1e-2):
    bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=d)
    bmesh.ops.dissolve_degenerate(bm,dist=d,edges=bm.edges)
    bmesh.ops.triangulate(bm,faces=bm.faces)
    loose=[v for v in bm.verts if not v.link_edges];bmesh.ops.delete(bm,geom=loose,context='VERTS')
    after=stats(bm)
    if after==(0,0):break
  if after[0]:
    # remaining defect = a dangling sliver fin (tiny triangle hinged on an edge shared by 3 faces): delete fins < 0.1 mm2, drop loose edges, fill any hole
    fins=[f for f in bm.faces if f.calc_area()<0.1 and any(len(e.link_faces)!=2 for e in f.edges)]
    bmesh.ops.delete(bm,geom=fins,context='FACES_ONLY')
    bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces],context='EDGES')
    bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if len(e.link_faces)==1],sides=8);bmesh.ops.triangulate(bm,faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces);after=stats(bm)+(f'fins removed {len(fins)}',)
  bm.normal_update();bm.to_mesh(o.data);bm.free()
  bpy.ops.wm.stl_export(filepath=path,export_selected_objects=True,ascii_format=False,apply_modifiers=False)
  return before,after,d
if __name__=='__main__':
  for p in sorted(glob.glob(os.path.join(H,'..','stl','*.stl'))):
    print(os.path.basename(p),*clean(p))
