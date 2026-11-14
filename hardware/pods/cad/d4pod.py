"""D4-style action pods (Cody 12:22 AM CT Sat Nov 14 2026, option b): D4_contoured_v3 look around the LOCKED
pr28_352e734 internals (two-cell cavity 58 x 82, floor 1.4, internal height floor->lid 20.7, lid-screw columns with
inserts, buzzer/mount-face recess, floor glyphs, lid key: all copied from the printed source, never re-modelled).
 - base = old pod base between its floor underside (old z 14.1) and its wall top (old z 36.2), dropped to z=0
   -> flat underside = the floor underside (no skirt, tunnel or plinth; nothing under the cavity floor)
 - outer form = D4 plan measured flat (ref_d4/d4_pod_plan_flat.json, x-symmetrised) U cavity+4.5 (convex),
   1 mm 45° bed bevel, vertical side, R10.24 shoulder arc (vertical->45°) on the base ending at the seam,
   45° x 2.6 chamfer on the lid (support-free, lid prints top-down) -> flat top plateau
 - old tongue/groove dropped (it alone set 3.7 mm of height): lid = 2.6 mm plate seated on the wall top + old lid key
   + 4x M3 90° countersinks (ISO 10642) into the existing column inserts
 - clamp inserts moved to side EARS at x=±33.6 (outside the cavity), M3 heat-set Ø4.0 x 6.5
Paths are relative to this file (repo: hardware/pods/cad/)."""
import os,json,math,numpy as np,manifold3d as m3,trimesh,shapely.geometry as sg,shapely.geometry.polygon as sgp
H=os.path.dirname(os.path.abspath(__file__));P=os.path.join(H,'..')
SRC=os.path.join(P,'src_pr28_352e734')+'/';OUT=os.path.join(P,'stl')+'/';CHK=os.path.join(P,'checks')+'/'
BIG=1000.
def box(x0,x1,y0,y1,z0,z1):return m3.Manifold.cube([x1-x0,y1-y0,z1-z0]).translate([x0,y0,z0])
def cyl(r,z0,z1,x,y,n=48):return m3.Manifold.cylinder(z1-z0,r,r,n).translate([x,y,z0])
def cone(r0,r1,z0,z1,x,y,n=48):return m3.Manifold.cylinder(z1-z0,r0,r1,n).translate([x,y,z0])
def load(f):
  t=trimesh.load(SRC+f);t.merge_vertices()
  M=m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices,np.float32),tri_verts=np.asarray(t.faces,np.uint32)))
  parts=sorted(M.decompose(),key=lambda p:-p.volume())
  if len(parts)>1:
    fixed=[parts[0]]
    for p in parts[1:]:
      if (p^parts[0]).volume()<0.5*p.volume():p=m3.Manifold.batch_boolean([p]+[p.translate(v) for v in ([.15,0,0],[-.15,0,0],[0,.15,0],[0,-.15,0],[0,0,.15],[0,0,-.15])],m3.OpType.Add)
      fixed.append(p)
    M=m3.Manifold.batch_boolean(fixed,m3.OpType.Add)
  return M
def tm(M):me=M.to_mesh();return trimesh.Trimesh(np.asarray(me.vert_properties)[:,:3],np.asarray(me.tri_verts),process=False)
def save(M,name,keep_min=0.5):
  sh=sorted(M.decompose(),key=lambda p:-p.volume());dropped=[round(p.volume(),2) for p in sh if p.volume()<=keep_min]
  sh=[p for p in sh if p.volume()>keep_min];M0=m3.Manifold.batch_boolean(sh,m3.OpType.Add) if len(sh)>1 else sh[0]
  # STL stores float32: raise the sliver-collapse tolerance until the exported file itself is watertight with no zero-area faces
  for tol in (0.0005,):   # zero-area float32 slivers are removed afterwards by stlclean.py
    M=M0.simplify(tol);t=tm(M);t.export(OUT+name+'.stl')
    r=trimesh.load(OUT+name+'.stl');rr=trimesh.load(OUT+name+'.stl',process=False)
    if r.is_watertight and (rr.area_faces<1e-6).sum()==0:break
  print(name,'simplify tol',tol,'stl watertight',r.is_watertight,'zero-area',int((rr.area_faces<1e-6).sum()))
  return M,t,[round(p.volume(),2) for p in sh],dropped
Z_FLOOR_UNDER=14.1; Z_WALL_TOP=36.2; LID_T=2.6; FLOOR_ADD=1.1   # old floor 1.4 -> 2.5 (added below; cavity untouched)
SEAM=Z_WALL_TOP-Z_FLOOR_UNDER+FLOOR_ADD; HT=SEAM+LID_T
WALL_SIDE=4.5; BEVEL=1.0; ARC_R=10.24; LAND=1.2; CH=LID_T-LAND   # lid edge: 1.2 vertical land (seam reveal) + 45° chamfer
I_SEAM=ARC_R*(1-1/math.sqrt(2)); Z_ARC0=SEAM-ARC_R/math.sqrt(2); I_TOP=I_SEAM+CH
INS_D=4.0; INS_DEPTH=6.5; INS_X=33.6; EAR_H=9.4; EAR_R=5.0; BAR_DY=25.0
def profile():
  pr=[(0.0,-BEVEL),(BEVEL,0.0),(Z_ARC0,0.0)]
  for a in np.linspace(0,math.pi/4,10)[1:]:pr.append((Z_ARC0+ARC_R*math.sin(a),-ARC_R*(1-math.cos(a))))
  pr.append((SEAM+LAND,-I_SEAM));pr.append((HT,-I_TOP));return pr
def outer(plan):
  pts=[]
  for z,o in profile():
    q=plan.buffer(o,resolution=32) if o else plan;pts+=[[x,y,z] for x,y in np.asarray(q.exterior.coords)[:-1]]
  return m3.Manifold.hull_points(np.asarray(pts,np.float64))
def cavity_outline(old):
  ps=[sg.Polygon(p) for p in old.slice(30.0).to_polygons()];ps=[p for p in ps if 3000<abs(p.area)<5500]
  return sg.Polygon(max(ps,key=lambda p:abs(p.area)).exterior).buffer(0)
def mp(sl):
  ps=[sg.Polygon(p).buffer(0) for p in sl.to_polygons()]
  return sg.MultiPolygon([q for p in ps for q in getattr(p,'geoms',[p]) if q.area>0]).buffer(0) if ps else sg.Polygon()
def slab_area(M,z):
  # signed (even-odd correct) area of a slice
  return M.slice(z).area()
d=np.asarray(json.load(open(os.path.join(P,'ref_d4','d4_pod_plan_flat.json'))))
D4s=sg.MultiPoint(np.r_[d,np.c_[-d[:,0],d[:,1]]]).convex_hull   # x-symmetrised (the wide side both ways)
report={}
def build(side):
  ob=load(f'pod_{side}_base.stl');ol=load(f'pod_{side}_lid.stl')
  _s=[sg.Polygon(p) for p in ob.slice(15.0).to_polygons()];y0=min(p.bounds[1] for p in _s);y1=max(p.bounds[3] for p in _s)
  cav=cavity_outline(ob)
  dd=np.asarray(D4s.exterior.coords);dy0,dy1=dd[:,1].min(),dd[:,1].max()
  d4p=sg.Polygon(np.c_[dd[:,0],y0+(dd[:,1]-dy0)*(y1-y0)/(dy1-dy0)])
  plan=d4p.union(cav.buffer(WALL_SIDE,resolution=32)).convex_hull.intersection(sg.box(-BIG,y0,BIG,y1))
  O=outer(plan)
  body=ob^box(-BIG,BIG,-BIG,BIG,Z_FLOOR_UNDER,Z_WALL_TOP)
  # old rim had a 0.02 mm step (ledge top 36.18 vs wall top 36.20) -> knife edge at the new seam; square off the top 0.25 mm band
  rim=m3.Manifold.extrude((ob^box(-BIG,BIG,-BIG,BIG,Z_WALL_TOP-0.25,Z_WALL_TOP)).project(),0.25).translate([0,0,Z_WALL_TOP-0.25])
  body=(body+rim).translate([0,0,FLOOR_ADD-Z_FLOOR_UNDER])
  fill=(O^box(-BIG,BIG,-BIG,BIG,-1,FLOOR_ADD+0.6))
  # do not close openings that the old floor underside had (only fill where the old part is solid at z=0.65)
  solid65=mp(body.slice(FLOOR_ADD+0.65)).intersection(plan)   # old floor-underside solid (keeps any opening the old floor had)
  def ext(poly,h):
    gs=[g for g in getattr(poly,'geoms',[poly]) if g.area>0.01]
    return m3.Manifold.batch_boolean([m3.Manifold.extrude(m3.CrossSection([np.asarray(sgp.orient(g).exterior.coords)[:-1]]+[np.asarray(sgp.orient(sg.Polygon(r)).exterior.coords)[:-1][::-1] for r in g.interiors]),h).translate([0,0,-1]) for g in gs],m3.OpType.Add)
  fillmask=ext(solid65.union(plan.difference(cav.buffer(-0.5))).buffer(0),FLOOR_ADD+2.6)
  base=(body+(fill^fillmask))^(O^box(-BIG,BIG,-BIG,BIG,-1,SEAM))
  yc=(y0+y1)/2;ys=[yc-BAR_DY,yc+BAR_DY];ins=[(sx*INS_X,round(y,3)) for sx in(-1,1) for y in ys]
  ears=None
  for x,y in ins:
    sx=np.sign(x);fp=sg.Point(x,y).buffer(EAR_R,resolution=32).union(sg.box(min(x,sx*31),y-EAR_R,max(x,sx*31),y+EAR_R))
    pts=[]
    for z,o in [(0,-0.5),(0.5,0),(EAR_H-0.5,0),(EAR_H,-0.5)]:
      q=fp.buffer(o,resolution=32);pts+=[[a,b,z] for a,b in np.asarray(q.exterior.coords)[:-1]]
    e=m3.Manifold.hull_points(np.asarray(pts));ears=e if ears is None else ears+e
  base=base+ears
  for x,y in ins:base=base-cyl(INS_D/2,-1,INS_DEPTH,x,y)
  plate=O^box(-BIG,BIG,-BIG,BIG,SEAM,HT+1)
  olA=ol.rotate([180,0,0]);olA=olA.translate([0,0,-olA.bounding_box()[2]]);top=ob.bounding_box()[5]
  for dz in np.arange(top-9,top,0.05):
    if (ob^olA.translate([0,0,dz])).volume()<0.5:break
  olA=olA.translate([0,0,dz])
  key=None
  for k in [sg.Polygon(p) for p in olA.slice(35.0).to_polygons() if abs(sg.Polygon(p).area)>2]:
    x0,k0,x1,k1=k.bounds;kk=olA^box(x0-0.3,x1+0.3,k0-0.3,k1+0.3,30,Z_WALL_TOP+0.05);key=kk if key is None else key+kk
  lid=plate if key is None else plate+key.translate([0,0,FLOOR_ADD-Z_FLOOR_UNDER])
  holes=[]
  for p in [sg.Polygon(q) for q in ob.slice(35.3).to_polygons()]:
    if 8<abs(p.area)<20:c=p.centroid;holes.append((round(c.x,2),round(c.y,2)))
  CSK=1.45   # ISO 10642 M3: Ø6.3 x 90° -> 1.45 deep from Ø3.4
  for x,y in holes:lid=lid-cyl(1.7,SEAM-3,HT+1,x,y)-cone(1.7,1.7+CSK+0.01,HT-CSK,HT+0.01,x,y)
  Mb,tb,shb,drb=save(base,f'action_pod_{side}_base',keep_min=100.0)
  lidp=lid.rotate([180,0,0]);lidp=lidp.translate([0,0,-lidp.bounding_box()[2]])
  Ml,tl,shl,drl=save(lidp,f'action_pod_{side}_lid')
  tm(lid).export(OUT+f'_asm_action_pod_{side}_lid.stl')
  def ring_miss(x,y):
    big=cyl(INS_D/2+2.4,0,INS_DEPTH+2.4,x,y)-cyl(INS_D/2,-1,INS_DEPTH,x,y);return round((big-Mb).volume(),3)
  cp=m3.Manifold.extrude(m3.CrossSection([np.asarray(sgp.orient(cav.buffer(-0.3)).exterior.coords)[:-1]]),SEAM-FLOOR_ADD-1.45).translate([0,0,FLOOR_ADD+1.45])  # cavity air zone: above old floor top
  oldin=(body^cp);newin=(Mb^cp)
  diffs=[]
  for z in np.arange(FLOOR_ADD+1.5,SEAM,0.5):
    a=mp(oldin.slice(z));b=mp(newin.slice(z));dd_=a.symmetric_difference(b)
    if dd_.area>0.5:diffs.append((round(float(z),2),round(dd_.area,1),[round(v,1) for v in dd_.bounds]))
  # lid seat: lid underside vs locked internal height
  report[side]=dict(plan_bounds=[round(v,2) for v in plan.bounds],plan_area=round(plan.area,1),cavity_bounds=[round(v,2) for v in cav.bounds],
    seam=round(SEAM,2),assembled_height=round(HT,2),internal_height_floor_to_lid=round(SEAM-(15.5-Z_FLOOR_UNDER+FLOOR_ADD),2),floor_thickness=round(15.5-Z_FLOOR_UNDER+FLOOR_ADD,2),
    shoulder=dict(arc_R=ARC_R,arc_z=[round(Z_ARC0,2),round(SEAM,2)],inset_at_seam=round(I_SEAM,2),lid_land=LAND,lid_chamfer_45=round(CH,2),inset_at_top=round(I_TOP,2),drop=round(HT-Z_ARC0,2)),
    inserts=ins,insert_ring_miss_mm3={f'{x},{y}':ring_miss(x,y) for x,y in ins},lid_screws=holes,old_lid_dz=round(float(dz),2),
    cavity_prism_material_old_vs_new_mm3=[round(oldin.volume(),2),round(newin.volume(),2)],cavity_prism_diff_slices=diffs,
    base=dict(bounds=tb.bounds.round(2).tolist(),watertight=bool(tb.is_watertight),volume=round(tb.volume),genus=Mb.genus(),shells=shb,dropped_shells=drb),
    lid=dict(bounds=tl.bounds.round(2).tolist(),watertight=bool(tl.is_watertight),volume=round(tl.volume),genus=Ml.genus(),shells=shl,dropped_shells=drl))
  print(side,json.dumps(report[side]))
if __name__=='__main__':
  for s in('L','R'):build(s)
  json.dump(report,open(CHK+'d4pod_report.json','w'),indent=1)
