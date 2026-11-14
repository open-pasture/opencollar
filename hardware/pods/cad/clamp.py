"""Adjustable clamp parts (approved concept A-adj, Cody 11:18 PM CT Nov 13 2026): U-bar, C-clip spacers, width shims.
Bar 78 x 20 x 6.5: base 4.0, lips 2.5 at |x| 25..39 (50.0 clear), 2x M3 clearance Ø3.4 at x=±33.6 + Ø6.0x1.5 head c'bore
on the NECK face; neck-face edges rolled R2 (support-free: 45° start, arc to vertical); 3 grip ribs across the strap
(45° flanks, 0.6 high) on the channel floor. Prints channel-UP, neck face on bed. 8 per collar (2 per pod).
Spacers: C-clip washers OD7 / ID3.4 / clip slot 2.6 (snap over the M3 shank so they can be added/removed with the screw
only loosened) in 0.5/1/2 mm; per hole 1x2 + 2x1 + 1x0.5 = 4.5 mm max stack -> gap 2.5..7.0 mm.
Shims: 2.3 x 20 x 2.5 width shims, one each side inside the channel -> 50.0 to 45.4 clear (44.45 strap)."""
import numpy as np,manifold3d as m3,trimesh,math,os,json,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','stl'))+'/'
import shapely.geometry as sg
def box(x0,x1,y0,y1,z0,z1):return m3.Manifold.cube([x1-x0,y1-y0,z1-z0]).translate([x0,y0,z0])
def cyl(r,z0,z1,x,y,n=48):return m3.Manifold.cylinder(z1-z0,r,r,n).translate([x,y,z0])
def save(M,name):
  M=M.simplify(0.0005)
  me=M.to_mesh();t=trimesh.Trimesh(np.asarray(me.vert_properties)[:,:3],np.asarray(me.tri_verts),process=False);t.export(OUT+name+'.stl');return t
BAR_L,BAR_W,BASE,LIP,INNER,HX=78.0,20.0,4.0,2.5,50.0,33.6  # Nov 14: holes re-fitted to the D4-pod side-ear inserts at x=±33.6 (web to channel 6.9 mm)
def rr(hx,hy,R,off):
  p=sg.box(-hx+R,-hy+R,hx-R,hy-R).buffer(R,resolution=16).buffer(off,resolution=16);return np.asarray(p.exterior.coords)[:-1]
def bar():
  r=2.0;z45=r*(1-1/math.sqrt(2));o45=-(r-r/math.sqrt(2))
  prof=[(0,o45-z45)]+[(z,-(r-math.sqrt(max(r*r-(r-z)**2,0)))) for z in np.linspace(z45,r,9)]+[(BASE+LIP,0)]
  pts=[[x,y,z] for z,o in prof for x,y in rr(BAR_L/2,BAR_W/2,3.0,o)]
  b=m3.Manifold.hull_points(np.asarray(pts))
  b=b-box(-INNER/2,INNER/2,-50,50,BASE,50)           # open channel (no roof)
  for y in (-6.0,0.0,6.0):                           # 45° grip ribs across the strap, 0.6 high
    cs=m3.CrossSection([[(y-0.6,0),(y+0.6,0),(y,0.6)]])
    rib=m3.Manifold.extrude(cs,INNER-1.0).rotate([90,0,90]).translate([-(INNER-1.0)/2,0,BASE])
    b=b+rib
  for sx in(-1,1):
    b=b-cyl(1.7,-1,20,sx*HX,0)-cyl(3.0,-1,1.5,sx*HX,0)
  return b
def spacer(t):
  w=cyl(3.5,0,t,0,0)-cyl(1.7,-1,t+1,0,0)-box(-1.3,1.3,0,10,-1,t+1)
  return w
def shim():
  return box(0,BAR_W,0,LIP,0,2.3)   # printed lying: 20 (len) x 2.5 (height in use) on bed, 2.3 tall
if __name__=='__main__':
  rep={}
  for n,M in [('clamp_bar',bar()),('spacer_0p5',spacer(0.5)),('spacer_1p0',spacer(1.0)),('spacer_2p0',spacer(2.0)),('width_shim',shim())]:
    t=save(M,n);rep[n]=dict(bounds=t.bounds.round(3).tolist(),watertight=bool(t.is_watertight),volume=round(t.volume,2),genus=M.genus())
    print(n,rep[n])
  json.dump(rep,open(OUT+'../checks/clamp_report.json','w'),indent=1)
