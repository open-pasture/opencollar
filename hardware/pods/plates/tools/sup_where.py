import re,sys,collections,json,trimesh,numpy as np
g,stldir=sys.argv[1],sys.argv[2]
x=y=z=0;t='';obj=None;S=collections.defaultdict(list);P=collections.defaultdict(lambda:[1e9,-1e9,1e9,-1e9])
for l in open(g):
  if l.startswith('; printing object '):obj=l[18:].split(' id:')[0].strip()
  elif l.startswith('; stop printing object '):obj=None
  elif l.startswith('; FEATURE:'):t=l[10:].strip()
  elif l.startswith('G1') or l.startswith('G0'):
    mx=re.search(r'X([-\d.]+)',l);my=re.search(r'Y([-\d.]+)',l);mz=re.search(r'Z([-\d.]+)',l)
    if mx:x=float(mx.group(1))
    if my:y=float(my.group(1))
    if mz:z=float(mz.group(1))
    if l.startswith('G1') and (mx or my) and ' E' in l and obj:
      if 'upport' in t:S[obj].append((x,y,z))
      elif 'rim' not in t:
        b=P[obj];b[0]=min(b[0],x);b[1]=max(b[1],x);b[2]=min(b[2],y);b[3]=max(b[3],y)
out={}
for o,pts in S.items():
  m=trimesh.load(stldir+'/'+o);bb=m.bounds;c_stl=(bb[0][:2]+bb[1][:2])/2;b=P[o];c_g=np.array([(b[0]+b[1])/2,(b[2]+b[3])/2])
  a=np.array(pts);a[:,:2]=a[:,:2]-c_g+c_stl
  # classify vs part: support point inside the part's XY footprint at that z? (i.e. under an internal overhang)
  grid=collections.Counter((int(round(p[0]/5))*5,int(round(p[1]/5))*5) for p in a)
  top=collections.defaultdict(float)
  for p in a: k=(int(round(p[0]/5))*5,int(round(p[1]/5))*5);top[k]=max(top[k],p[2])
  out[o]=sorted([(k,v,round(top[k],1)) for k,v in grid.items()],key=lambda q:-q[1])[:25]
  print(o,len(pts));print('   (x,y)5mm cell, moves, max z:',out[o])
