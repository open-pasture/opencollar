"""Review package r4 (D4-style action pods, plate overnight_petg_A3_d4). Run: python3 build_r4.py  (bpy module; repo-relative paths).
Writes r4_01..r4_05 PNGs (+ _r4_labels.json for the plate labels) and overnight_review_r4.blend next to this file."""
import bpy,bmesh,json,math,os,numpy as np
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view as w2c
R=os.path.dirname(os.path.abspath(__file__))+'/';P=os.path.abspath(R+'..')+'/'
S=P+'stl/';REF=P+'ref_d4/';lay=json.load(open(P+'plates/layout_A3_d4.json'))
rep=json.load(open(P+'checks/d4pod_report.json'))
bpy.ops.wm.read_factory_settings(use_empty=False);sc=bpy.context.scene
for o in list(bpy.data.objects):bpy.data.objects.remove(o)
us=sc.unit_settings;us.system='METRIC';us.scale_length=0.001;us.length_unit='MILLIMETERS'
C=dict(base=(0.93,0.88,0.76,1),lid=(0.72,0.78,0.88,1),old=(0.80,0.74,0.66,1),d4=(0.70,0.84,0.72,1),bar=(0.95,0.42,0.17,1),spacer=(0.98,0.80,0.20,1),
       shim=(0.20,0.50,0.85,1),screw=(0.40,0.41,0.45,1),strap=(0.28,0.24,0.19,1),bed=(0.15,0.15,0.16,1),petg=(0.50,0.49,0.51,1),env=(0.25,0.75,0.35,1),cut=(0.85,0.25,0.25,1))
cache={}
def coll(n):c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
def mesh(path):
  if path not in cache:
    bpy.ops.wm.stl_import(filepath=path);o=bpy.context.selected_objects[0];me=o.data;me.name=os.path.basename(path)[:-4];bpy.data.objects.remove(o);cache[path]=me
  return cache[path]
def put(c,path,M,col,label):
  o=bpy.data.objects.new(label,mesh(path) if isinstance(path,str) else path);c.objects.link(o);o.matrix_world=Matrix(np.asarray(M).tolist());o.color=col;return o
def T(x=0,y=0,z=0):M=np.eye(4);M[:3,3]=[x,y,z];return M
def Rz(d):r=math.radians(d);M=np.eye(4);M[:2,:2]=[[math.cos(r),-math.sin(r)],[math.sin(r),math.cos(r)]];return M
def boxme(name,x0,x1,y0,y1,z0,z1):
  bm=bmesh.new();bmesh.ops.create_cube(bm,size=1.0);bmesh.ops.scale(bm,vec=(x1-x0,y1-y0,z1-z0),verts=bm.verts);bmesh.ops.translate(bm,vec=((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),verts=bm.verts)
  me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();return me
def cylme(name,r,z0,z1):
  bm=bmesh.new();bmesh.ops.create_cone(bm,cap_ends=True,segments=24,radius1=r,radius2=r,depth=z1-z0);bmesh.ops.translate(bm,vec=(0,0,(z0+z1)/2),verts=bm.verts)
  me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();return me
def cut(me,co,no,name):
  """copy of mesh with the half-space (p-co).no>0 removed and the cut face filled"""
  bm=bmesh.new();bm.from_mesh(me);g=bm.verts[:]+bm.edges[:]+bm.faces[:]
  r=bmesh.ops.bisect_plane(bm,geom=g,plane_co=co,plane_no=no,clear_outer=True)
  bmesh.ops.edgeloop_fill(bm,edges=[e for e in r['geom_cut'] if isinstance(e,bmesh.types.BMEdge)])
  m2=bpy.data.meshes.new(name);bm.to_mesh(m2);bm.free();return m2
# ---------- 1. old vs A2 vs A3 vs D4 (aligned flat, mount end +Y)
cc=coll('Compare_old_A2_A3_D4')
CMP=[('PR #21 (old)',REF+'pr21_pod_L_base.stl',REF+'pr21_pod_L_lid_stacked.stl',90,C['old']),
     ('A2 = pr28 shell',REF+'a2_pod_L_base_pr28.stl',REF+'a2_pod_L_lid_stacked_pr28.stl',0,C['old']),
     ('A3 = new D4-style',S+'action_pod_L_base.stl',S+'_asm_action_pod_L_lid.stl',0,C['base']),
     ('D4_contoured_v3',REF+'d4_pod_L_base_flat.stl',REF+'d4_pod_L_lid_flat.stl',0,C['d4'])]
CX=[-180,-60,60,180]
for (nm,b,l,rz,col),x in zip(CMP,CX):
  put(cc,b,T(x)@Rz(rz),col,nm+' base');put(cc,l,T(x)@Rz(rz),C['lid'],nm+' lid')
# ---------- 2. pod + adjustable clamp (L, stack 1.0+0.5)
ca=coll('Pod_clamp_assembled');AX=0;AY=300
yc=(rep['L']['plan_bounds'][1]+rep['L']['plan_bounds'][3])/2;HX=33.6;STACK=[1.0,0.5];s=sum(STACK)
put(ca,S+'action_pod_L_base.stl',T(AX,AY),C['base'],'L base');put(ca,S+'_asm_action_pod_L_lid.stl',T(AX,AY),C['lid'],'L lid')
screw=cylme('M3x12',1.5,0,12);head=cylme('M3_head',2.75,-1.6,0)
for dy in(-25,25):
  y=AY+yc+dy;put(ca,S+'clamp_bar.stl',T(AX,y,-(s+6.5)),C['bar'],f'bar y{dy:+d}')
  for sx in(-1,1):
    z=-s
    for t in STACK:
      put(ca,S+{1.0:'spacer_1p0',0.5:'spacer_0p5',2.0:'spacer_2p0'}[t]+'.stl',T(AX+sx*HX,y,z),C['spacer'],f'spacer {t} {sx:+d} {dy:+d}');z+=t
    zs=-(s+6.5)+1.5;put(ca,screw,T(AX+sx*HX,y,zs),C['screw'],f'M3x12 {sx:+d} {dy:+d}');put(ca,head,T(AX+sx*HX,y,zs),C['screw'],f'head {sx:+d} {dy:+d}')
    Ms=np.array([[0,0,1,0],[1,0,0,0],[0,1,0,0],[0,0,0,1]],float);x0=sx*25-(2.3 if sx>0 else 0)
    put(ca,S+'width_shim.stl',T(AX+x0,y-10,-(s+2.5))@Ms,C['shim'],f'shim {sx:+d} {dy:+d}')
put(ca,boxme('strap',-44.45/2,44.45/2,-110,110,0,3.8),T(AX,AY+yc,-(s+2.5)),C['strap'],'strap 44.45x3.8 (ref)')
# ---------- 3. cavity section with electronics envelope (locked 58 x 82 x 19.5 on the floor)
cs=coll('Section_cavity_envelope');SX=0;SY=-300
fl=rep['L']['floor_thickness'];cav=rep['L']['cavity_bounds']
env=boxme('envelope',cav[0],cav[2],cav[1],cav[3],fl,fl+19.5)
for tag,co,no,dx in [('X',(0,-2,0),(0,-1,0),-78),('Y',(0,0,0),(-1,0,0),62)]:
  b=cut(mesh(S+'action_pod_L_base.stl'),co,no,'cut_base_'+tag);l=cut(mesh(S+'_asm_action_pod_L_lid.stl'),co,no,'cut_lid_'+tag);e=cut(env,co,no,'cut_env_'+tag)
  M=T(SX+dx,SY)@(Rz(90) if tag=='Y' else np.eye(4))
  put(cs,b,M,C['base'],f'section {tag} base');put(cs,l,M,C['lid'],f'section {tag} lid');put(cs,e,M,C['env'],f'section {tag} envelope 58x82x19.5')
# ---------- 4. plate A3
cp=coll('Plate_A3_overnight_petg_A3_d4');PX=500
put(cp,boxme('bed',0,256,0,256,-1,0),T(PX),C['bed'],'bed 256')
lab={}
for nm,(x,y) in lay.items():
  s_='clamp_bar' if nm.startswith('clamp_bar') else 'width_shim' if nm.startswith('width_shim') else nm[:10] if nm.startswith('spacer') else nm
  me=mesh(S+s_+'.stl');v=np.array([q.co[:] for q in me.vertices]);c=(v.min(0)+v.max(0))/2
  put(cp,S+s_+'.stl',T(PX+x-c[0],y-c[1]),C['petg'],'A3:'+nm);lab[nm]=(PX+x,y,float(v[:,2].max()))
# ---------- viewports
allv=np.array([(o.matrix_world@v.co)[:] for o in bpy.data.objects if o.type=='MESH' for v in list(o.data.vertices)[::9]])
lo,hi=allv.min(0),allv.max(0);ctr=(lo+hi)/2;rad=float(np.linalg.norm(hi-lo))/2
for scr in bpy.data.screens:
  for ar in scr.areas:
    if ar.type=='VIEW_3D':
      for sp in ar.spaces:
        if sp.type=='VIEW_3D':
          sp.clip_start=0.1;sp.clip_end=10000;sp.shading.type='SOLID';sp.shading.color_type='OBJECT';sp.shading.show_cavity=True
          r3=sp.region_3d;r3.view_location=Vector(ctr.tolist());r3.view_distance=max(rad*2.6,900);r3.view_perspective='PERSP'
sc.render.engine='BLENDER_WORKBENCH';sh=sc.display.shading;sh.light='STUDIO';sh.color_type='OBJECT';sh.show_cavity=True;sh.cavity_type='BOTH'
w=bpy.data.worlds.new('w');sc.world=w;w.color=(0.95,0.94,0.91)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=10000
def shot(out,camp,tgt,scale,res,only,up='Y'):
  for c in bpy.data.collections:c.hide_render=c.name not in only
  cam.location=camp;d=Vector(tgt)-Vector(camp);cam.rotation_euler=d.to_track_quat('-Z',up).to_euler();cam.data.ortho_scale=scale
  sc.render.resolution_x,sc.render.resolution_y=res;sc.render.filepath=R+out;bpy.ops.render.render(write_still=True);bpy.context.view_layer.update()
  return {k:[(p:=w2c(sc,cam,Vector(v))).x,1-p.y] for k,v in lab.items()}
shot('_r4_01a_iso.png',(260,-330,260),(0,0,10),480,(2000,900),['Compare_old_A2_A3_D4'])
shot('_r4_01b_side.png',(0,-800,14),(0,0,14),480,(2000,330),['Compare_old_A2_A3_D4'])
shot('_r4_01c_end.png',(-180-60,800,14),(-180-60,0,14),480,(2000,330),['Compare_old_A2_A3_D4'])
shot('r4_02a_pod_clamp_underside.png',(AX+150,AY-170,-130),(AX,AY,4),190,(1500,1100),['Pod_clamp_assembled'])
shot('r4_02b_pod_clamp_end.png',(AX,AY+600,8),(AX,AY,8),110,(1500,900),['Pod_clamp_assembled'])
shot('_r4_03_section.png',(SX,SY-600,12),(SX,SY,12),250,(2400,560),['Section_cavity_envelope'])
L1=shot('_r4_04_plate_top.png',(PX+128,128,500),(PX+128,128,0),275,(1400,1400),['Plate_A3_overnight_petg_A3_d4'])
L2=shot('_r4_05_plate_34.png',(PX+128+260,128-330,260),(PX+128,118,0),330,(1600,1100),['Plate_A3_overnight_petg_A3_d4'])
json.dump({'top':L1,'34':L2},open(R+'_r4_labels.json','w'))
for c in bpy.data.collections:c.hide_render=False
cam.location=(AX+150,AY-170,-130);cam.rotation_euler=(Vector((AX,AY,4))-Vector(cam.location)).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=190
bpy.ops.wm.save_as_mainfile(filepath=R+'overnight_review_r4.blend')
print('OBJS',len(bpy.data.objects))
