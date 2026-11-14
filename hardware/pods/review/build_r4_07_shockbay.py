"""r4_07: shock/electrode bay keep-out vs A3 action pod L + U clamp + strap (nominal 3.8 strap, stack 1.0+0.5).
Keep-outs from ../checks/shockbay_keepout.json (run checks/shockbay_keepout.py first). Cycles CPU, headless.
Run: python3 build_r4_07_shockbay.py  (bpy module). Writes _r4_07_*.png raw renders + _r4_07_proj.json; compose_r4_07.py annotates."""
import bpy,bmesh,json,math,os,numpy as np
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view as w2c
R=os.path.dirname(os.path.abspath(__file__))+'/';P=os.path.abspath(R+'..')+'/';S=P+'stl/'
J=json.load(open(P+'checks/shockbay_keepout.json'));cfg=J['configs']['nominal 3.8 strap, stack 1.0+0.5']
s=cfg['stack'];HX=33.6;BAR_Y=J['bar_y']
bpy.ops.wm.read_factory_settings(use_empty=True);sc=bpy.context.scene
us=sc.unit_settings;us.system='METRIC';us.scale_length=0.001
def mat(name,rgb,alpha=1.0,emit=0.0):
  m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;b=nt.nodes['Principled BSDF']
  b.inputs['Base Color'].default_value=(*rgb,1);b.inputs['Roughness'].default_value=0.55;b.inputs['Alpha'].default_value=alpha
  if emit:b.inputs['Emission Color'].default_value=(*rgb,1);b.inputs['Emission Strength'].default_value=emit
  return m
M=dict(base=mat('base',(0.62,0.55,0.42)),lid=(mat('lid',(0.55,0.62,0.75))),bar=mat('bar',(0.95,0.38,0.10)),spacer=mat('spacer',(0.98,0.80,0.20)),
  screw=mat('screw',(0.30,0.31,0.34)),shim=mat('shim',(0.20,0.45,0.85)),strap=mat('strap',(0.20,0.55,0.95),0.30),
  ko=mat('ko',(0.95,0.05,0.05),0.38,0.4),sad=mat('sad',(1.0,0.45,0.45),0.12),wire=mat('wire',(0.6,0.0,0.6),0.6,0.3),cutf=mat('cutf',(0.25,0.25,0.25)))
def stl(path):
  bpy.ops.wm.stl_import(filepath=path);o=bpy.context.selected_objects[0];me=o.data;bpy.data.objects.remove(o);return me
def obj(name,me,m,loc=(0,0,0),coll=None):
  o=bpy.data.objects.new(name,me);(coll or sc.collection).objects.link(o);o.location=loc
  me.materials.clear();me.materials.append(m);return o
def boxme(name,x,y,z):
  bm=bmesh.new();bmesh.ops.create_cube(bm,size=1.0);bmesh.ops.scale(bm,vec=(x[1]-x[0],y[1]-y[0],z[1]-z[0]),verts=bm.verts)
  bmesh.ops.translate(bm,vec=((x[0]+x[1])/2,(y[0]+y[1])/2,(z[0]+z[1])/2),verts=bm.verts);me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();return me
def cylme(name,r,z0,z1,seg=32):
  bm=bmesh.new();bmesh.ops.create_cone(bm,cap_ends=True,segments=seg,radius1=r,radius2=r,depth=z1-z0);bmesh.ops.translate(bm,vec=(0,0,(z0+z1)/2),verts=bm.verts)
  me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();return me
def cut(me,co,no):
  bm=bmesh.new();bm.from_mesh(me);g=bm.verts[:]+bm.edges[:]+bm.faces[:]
  r=bmesh.ops.bisect_plane(bm,geom=g,plane_co=co,plane_no=no,clear_outer=True)
  bmesh.ops.edgeloop_fill(bm,edges=[e for e in r['geom_cut'] if isinstance(e,bmesh.types.BMEdge)])
  m2=bpy.data.meshes.new(me.name+'_cut');bm.to_mesh(m2);bm.free();return m2
SRC=dict(base=stl(S+'action_pod_L_base.stl'),lid=stl(S+'_asm_action_pod_L_lid.stl'),bar=stl(S+'clamp_bar.stl'),sp1=stl(S+'spacer_1p0.stl'),sp05=stl(S+'spacer_0p5.stl'),shim=stl(S+'width_shim.stl'))
CLIP=None   # (axis, value, sign) for translucent boxes in section views
def cbox(name,x,y,z):
  e=[list(x),list(y),list(z)]
  if CLIP:
    ax,v,sg=CLIP
    if sg>0:e[ax][0]=max(e[ax][0],v-0.3)
    else:e[ax][1]=min(e[ax][1],v+0.3)
  return boxme(name,*e)
def scene_parts():
  """list of (name, mesh, material, location)"""
  L=[('pod L base',SRC['base'],M['base'],(0,0,0)),('pod L lid',SRC['lid'],M['lid'],(0,0,0))]
  for y in BAR_Y:
    L.append((f'clamp bar y{y}',SRC['bar'],M['bar'],(0,y,-(s+6.5))))
    for sx in(-1,1):
      L.append((f'spacer1 {sx} {y}',SRC['sp1'],M['spacer'],(sx*HX,y,-s)));L.append((f'spacer05 {sx} {y}',SRC['sp05'],M['spacer'],(sx*HX,y,-s+1.0)))
      zs=-(s+6.5)+1.5;L.append((f'M3x12 {sx} {y}',cylme('scr',1.5,0,12),M['screw'],(sx*HX,y,zs)));L.append((f'head {sx} {y}',cylme('hd',2.75,-1.6,0),M['screw'],(sx*HX,y,zs)))
  sz=cfg['strap_z'];L.append(('strap 44.45 x 3.8',cbox('strap',(-44.45/2,44.45/2),(-75,75),tuple(sz)),M['strap'],(0,0,0)))
  for kn,k in J['keepouts'].items():L.append((f'KEEP-OUT {kn}',cbox(kn,k['x'],k['y'],k['z']),M['ko'],(0,0,0)))
  sd=J['saddle_envelope'];L.append(('saddle envelope 52x97x13.7',cbox('sad',sd['x'],sd['y'],sd['z']),M['sad'],(0,0,0)))
  w=J['wire_pass_through'];L.append(('wire pass-through d8',cylme('wire',w['d']/2,-2.5,1.75),M['wire'],(w['xy'][0],w['xy'][1],0)))
  for i,(mx,my) in enumerate(J['saddle_mounts']):L.append((f'saddle M3 {i}',cylme('mnt',1.7,-8,1.75,16),M['wire'],(mx,my,0)))
  return L
cols={}
def build(tag,section=None):
  """section=(axis, value, keep_sign): sign +1 removes the side below value, -1 removes the side above via an EXACT boolean (real cut faces)"""
  global CLIP
  CLIP=section
  c=bpy.data.collections.new(tag);sc.collection.children.link(c);cols[tag]=c;cutter=None
  if section:
    ax,v,sg=section;lo=[-500,-500,-500];hi=[500,500,500]
    if sg>0:hi[ax]=v
    else:lo[ax]=v
    cutter=bpy.data.objects.new(tag+'_cutter',boxme('cutter',(lo[0],hi[0]),(lo[1],hi[1]),(lo[2],hi[2])));c.objects.link(cutter);cutter.hide_render=True;cutter.display_type='WIRE'
    lo2,hi2=list(lo),list(hi)   # translucent parts: cut 0.3 mm in front of the opaque cut face (no coplanar z-fighting)
    if sg>0:hi2[ax]=v-0.3
    else:lo2[ax]=v+0.3
    cutter2=bpy.data.objects.new(tag+'_cutter2',boxme('cutter2',(lo2[0],hi2[0]),(lo2[1],hi2[1]),(lo2[2],hi2[2])));c.objects.link(cutter2);cutter2.hide_render=True;cutter2.display_type='WIRE'
  for n,me,m,loc in scene_parts():
    o=obj(tag+':'+n,me.copy(),m,loc,c)
    if cutter:
      md=o.modifiers.new('sec','BOOLEAN');md.operation='DIFFERENCE';md.solver='EXACT';md.object=cutter2 if m is M['wire'] else cutter
      if m in (M['ko'],M['sad'],M['strap']):o.modifiers.remove(md)
build('iso');build('secX',(0,0.0,1));build('secY',(1,-27.5,-1))
sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=48;sc.cycles.use_denoising=True
sc.view_settings.view_transform='Standard'
w=bpy.data.worlds.new('w');sc.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(0.93,0.92,0.89,1);w.node_tree.nodes['Background'].inputs[1].default_value=0.7
sun=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN'));sun.data.energy=2.0;sc.collection.objects.link(sun);sun.rotation_euler=(math.radians(50),math.radians(-20),math.radians(30))
sun2=bpy.data.objects.new('sun2',bpy.data.lights.new('sun2','SUN'));sun2.data.energy=0.8;sc.collection.objects.link(sun2);sun2.rotation_euler=(math.radians(140),math.radians(20),math.radians(-60))
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));sc.collection.objects.link(cam);sc.camera=cam;cam.data.type='ORTHO';cam.data.clip_end=5000
PTS={'strap_bot':(0,-60,cfg['strap_z'][0]),'strap_top':(0,-60,cfg['strap_z'][1]),'ko_top':(0,-10,-2.5),'ko_bot':(0,-10,-12.5),'pod_under':(0,-10,0),
  'bar_bot':(0,-27.5,-(s+6.5)),'bar_top':(0,-27.5,-s),'ko_x':(15.5,-27.5,-7.5),'screw':(33.6,-27.5,-5),'head_x':(33.6-2.75,-27.5,-7.5),'sad_x':(26,-27.5,-7.5),
  'mod_c':(0,-21.5,-7.5),'drv_c':(0,24,-6.5),'bar1':(0,-27.5,-8),'bar2':(0,22.5,-8),'wire':(0,-28,0),'mnt':(18,32,0),'strap_c':(0,-62,-2)}
proj={}
def shot(out,tag,camp,tgt,scale,res,up='Y'):
  for n,c in cols.items():c.hide_render=(n!=tag)
  cam.location=camp;d=Vector(tgt)-Vector(camp);cam.rotation_euler=d.to_track_quat('-Z',up).to_euler();cam.data.ortho_scale=scale
  sc.render.resolution_x,sc.render.resolution_y=res;sc.render.filepath=R+out;bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
  proj[out]={k:[(p:=w2c(sc,cam,Vector(v))).x*res[0],(1-p.y)*res[1]] for k,v in PTS.items()}
shot('_r4_07_iso.png','iso',(170,-200,-150),(0,0,-3),175,(1600,1150))
shot('_r4_07_secX.png','secX',(-400,0,-2),(0,0,-2),125,(1800,700))
shot('_r4_07_secY.png','secY',(0,400,-2),(0,-27.5,-2),95,(1700,800))
json.dump(proj,open(R+'_r4_07_proj.json','w'),indent=1)
for c in cols.values():c.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=R+'r4_07_shockbay_keepout.blend')
print('done')
