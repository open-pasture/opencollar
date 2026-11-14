"""Shock/electrode bay keep-out vs the A3 action pod + adjustable U clamp + strap (Sat Nov 14 2026).
Keep-out source: PR #28 @ 352e734 hardware/rook/d6/pod_saddle.py (Option A neck saddle; PLACEHOLDER sizes, not a spec)
and pod.py (POD_WIRE_GLAND_Y=-28, POD_SADDLE_MOUNT=(+-18,+-32)). The A3 base keeps the pr28 pod-local XY frame
(mount face +Y=46), so the saddle keep-outs map 1:1 in XY. Z: the saddle's flat face sits on the pod underside (z=0)
exactly as it sat on the pr28 pod bed; bay toward the neck (-z). Writes checks/shockbay_keepout.json.
Run from hardware/pods/checks: python3 shockbay_keepout.py"""
import os,json,numpy as np,manifold3d as m3,trimesh,shapely.geometry as sg
H=os.path.dirname(os.path.abspath(__file__));S=os.path.join(H,'..','stl')+'/'
def box(x0,x1,y0,y1,z0,z1):return m3.Manifold.cube([x1-x0,y1-y0,z1-z0]).translate([x0,y0,z0])
def load(f):
  t=trimesh.load(S+f);return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices,np.float32),tri_verts=np.asarray(t.faces,np.uint32)))
# ---- keep-outs (pr28 352e734 pod_saddle.py: MODULE 40x25x8 +3 XY/+2 Z, DRIVER 35x22x6 +3/+2, BAY_WALL 2, SADDLE 52x97x13.7)
FACE_WALL=2.5   # bay_z0 = max(SADDLE_FLAT_T+0.5, ...) = 2.5 below the saddle flat face
KO=dict(
  module=dict(x=(-15.5,15.5),y=(-44.5,1.5),z=(-FACE_WALL-10.0,-FACE_WALL)),     # 31 x 46 x 10 at module_y=-21.5
  driver=dict(x=(-14.0,14.0),y=(3.5,44.5),z=(-FACE_WALL-8.0,-FACE_WALL)),       # 28 x 41 x 8 at driver_y=+24
)
SADDLE=dict(x=(-26,26),y=(-48.5,48.5),z=(-13.7,0.0))
WIRE=dict(xy=(0.0,-28.0),d=8.0,gland_d=12.0); MOUNTS=[(sx*18.0,sy*32.0) for sx in(-1,1) for sy in(-1,1)]
ELEC=[(0.0,-21.5-12.5),(0.0,-21.5+12.5)]   # electrode lands (blank) at module_y +-12.5, on the neck face
base=load('action_pod_L_base.stl');bar=load('clamp_bar.stl')
bb=base.bounding_box();yc=(-51.0+46.0)/2   # plan bounds centre (d4pod_report L plan_bounds) = -2.5
BAR_Y=[yc-25,yc+25];HX=33.6
CFG={'thin 3.0 strap, stack 0.5':(3.0,0.5),'nominal 3.8 strap, stack 1.0+0.5':(3.8,1.5),'thick 7.5 strap, stack 4.5':(7.5,4.5)}
out=dict(source='PR #28 352e734 pod_saddle.py / pod.py (placeholders, not a spec)',keepouts=KO,saddle_envelope=SADDLE,wire_pass_through=WIRE,saddle_mounts=MOUNTS,electrode_lands=ELEC,bar_y=BAR_Y,configs={})
def kobox(k):return box(*k['x'],*k['y'],*k['z'])
def gap1(a,b):return max(b[0]-a[1],a[0]-b[1])   # signed 1D gap (negative = overlap)
for name,(t,s) in CFG.items():
  gap=s+2.5;strap_z=(-gap,min(-gap+t,0.0));W=44.45
  r=dict(strap_t=t,stack=s,lip_gap=gap,strap_z=strap_z,bar_z=(-(s+6.5),-s),per_keepout={})
  for kn,k in KO.items():
    K=kobox(k);kv=K.volume()
    strap=box(-W/2,W/2,-120,120,*strap_z)
    bars=m3.Manifold.batch_boolean([bar.translate([0,y,-(s+6.5)]) for y in BAR_Y],m3.OpType.Add)
    sv=(strap^K).volume();bv=(bars^K).volume()
    r['per_keepout'][kn]=dict(
      keepout_mm3=round(kv),
      strap_intrusion_mm3=round(sv,1),strap_intrusion_depth_z=round(-gap1(strap_z,k['z']),2) if sv>0 else 0.0,
      strap_to_keepout_z_gap=round(gap1(strap_z,k['z']),2),
      clampbar_intrusion_mm3=round(bv,1),
      clampbar_to_keepout_z_gap=round(gap1((-(s+6.5),-s),k['z']),2),
      clampbar_z_in_keepout_footprint=(-(s+6.5),round(-(s+2.5)+0.6,2)),   # bar base 4.0 + 0.6 grip ribs (lips are at |x|>=25, outside the keep-out)
      clampbar_overlap_thickness_z=round(min(-(s+2.5)+0.6,k['z'][1])-max(-(s+6.5),k['z'][0]),2),
      bars_over_keepout_y=[y for y in BAR_Y if gap1((y-10,y+10),k['y'])<0],
      screw_shank_lateral_clear=round(HX-1.5-k['x'][1],2),screw_head_lateral_clear=round(HX-2.75-k['x'][1],2),
      spacer_lateral_clear=round(HX-3.5-k['x'][1],2),width_shim_lateral_clear=round((25.0-2.3)-k['x'][1],2))
  # whole saddle envelope (the reserved part zone between pod underside and neck)
  Sd=box(*SADDLE['x'],*SADDLE['y'],*SADDLE['z'])
  strap=box(-W/2,W/2,-120,120,*strap_z);bars=m3.Manifold.batch_boolean([bar.translate([0,y,-(s+6.5)]) for y in BAR_Y],m3.OpType.Add)
  r['saddle_envelope']=dict(strap_intrusion_mm3=round((strap^Sd).volume()),clampbar_intrusion_mm3=round((bars^Sd).volume()),screw_head_lateral_clear=round(HX-2.75-26.0,2))
  r['mounts_under_bar']=[m for m in MOUNTS if any(abs(m[1]-y)<=10 for y in BAR_Y)]
  r['wire_under_bar']=any(abs(WIRE['xy'][1]-y)<=10 for y in BAR_Y)
  r['relocate_below_bars']=dict(keepout_top_z=-(s+6.5)-FACE_WALL,extra_standoff_vs_saddle_on_pod=round(s+6.5,2))
  out['configs'][name]=r
# pod-side interface in the A3 base (blind holes from the pr28 floor)
def holes_at(z):
  ps=[sg.Polygon(p) for p in base.slice(z).to_polygons()];return sorted([(round(p.centroid.x,1),round(p.centroid.y,1),round(abs(p.area),1)) for p in ps if 5<abs(p.area)<80])
zopen=None
for z in np.arange(0.1,2.5,0.05):
  if any(abs(h[0])<1 and abs(h[1]+28)<1.5 for h in holes_at(z)):zopen=round(float(z),2);break
out['a3_interface']=dict(wire_hole_and_saddle_mounts_open_from_z=zopen,below_that='solid skin (no through-hole from the underside)',
  holes_z2=holes_at(2.0),bars_gap_between_y=[BAR_Y[0]+10,BAR_Y[1]-10],bar_gap_len=round(BAR_Y[1]-BAR_Y[0]-20,1))
json.dump(out,open(os.path.join(H,'shockbay_keepout.json'),'w'),indent=1)
print(json.dumps(out,indent=1))
