"""Localise thin (<2.4 mm ray thickness) faces by region (trimesh ray, inward normal)."""
import trimesh,numpy as np,sys,json,collections
def thin(path,minw=2.4):
  m=trimesh.load(path);c=m.triangles_center;n=m.face_normals;a=m.area_faces
  o=c-n*1e-3;d=np.full(len(c),np.inf)
  for s in range(0,len(c),2000):
    sl=slice(s,s+2000);loc,ir,it=m.ray.intersects_location(o[sl],-n[sl],multiple_hits=False)
    d[s+ir]=np.linalg.norm(loc-o[sl][ir],axis=1)
  t=d<minw-0.02
  return m,c,n,a,d,t
if __name__=='__main__':
  for p in sys.argv[1:]:
    m,c,n,a,d,t=thin(p);H=m.bounds[1][2]
    cl=collections.defaultdict(float)
    for ci,ni,ai,ti in zip(c,n,a,t):
      if not ti:continue
      z=ci[2];r=('bottom z<0.1' if z<0.1 else 'floor top' if abs(ni[2])>0.9 and z<4 else 'top/seam z>H-0.3' if z>H-0.3 else 'outer>31' if max(abs(ci[0]),0)>31 else 'interior')
      cl[(r,int(z//2)*2)]+=ai
    print(p,'thin total',round(a[t].sum(),1),'min',round(d[t].min(),3) if t.any() else None)
    for k,v in sorted(cl.items(),key=lambda kv:-kv[1])[:12]:print('   ',k,round(v,1))
