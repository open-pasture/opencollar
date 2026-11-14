"""Mesh overhang audit in print orientation: faces steeper than 45 deg from vertical (n_z < -sin(46 deg)), not on the bed.
Horizontal down-facing faces are bridges: report each connected bridge patch with its shortest span (min bbox side)."""
import trimesh,numpy as np,sys,json,os
H=os.path.dirname(os.path.abspath(__file__))
def audit(p):
  m=trimesh.load(p);n=m.face_normals;c=m.triangles_center;a=m.area_faces;z0=m.bounds[0][2]
  onbed=np.all(np.abs(m.vertices[m.faces][:,:,2]-z0)<0.05,axis=1)
  ov=(n[:,2]< -np.sin(np.radians(46)))&~onbed
  flat=ov&(n[:,2]<-0.999)
  slope=ov&~flat
  out={'overhang_area_mm2':round(a[ov].sum(),1),'sloped_overhang_area_mm2':round(a[slope].sum(),1),'bridges':[]}
  if flat.any():
    sub=m.submesh([np.where(flat)[0]],append=True)
    for comp in sub.split(only_watertight=False):
      e=comp.extents;out['bridges'].append({'z':round(comp.bounds[0][2],2),'xy_bbox':comp.bounds[:, :2].round(1).tolist(),'area':round(comp.area,1),'span_mm':round(min(e[0],e[1]),1)})
    out['bridges'].sort(key=lambda b:-b['span_mm'])
  if slope.any():
    sub=m.submesh([np.where(slope)[0]],append=True)
    out['sloped']=sorted([{'z':comp.bounds[:,2].round(2).tolist(),'xy_bbox':comp.bounds[:, :2].round(1).tolist(),'area':round(comp.area,2),'min_angle_from_horizontal':round(float(np.degrees(np.arcsin(-comp.face_normals[:,2].min()))) and float(90-np.degrees(np.arccos(-comp.face_normals[:,2].min()))),1)} for comp in sub.split(only_watertight=False)],key=lambda d:-d['area'])
  return out
if __name__=='__main__':
  R={os.path.basename(p):audit(p) for p in sys.argv[1:]}
  for k,v in R.items():
    print(k,'overhang',v['overhang_area_mm2'],'sloped',v['sloped_overhang_area_mm2'],'bridges',len(v['bridges']))
    for b in v['bridges'][:6]:print('   bridge',b)
    for s in v.get('sloped',[])[:6]:print('   slope',s)
  json.dump(R,open(os.path.join(H,'..','checks','overhang_audit.json'),'w'),indent=1)
