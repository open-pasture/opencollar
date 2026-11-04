import bpy,math,bmesh
from mathutils import Vector,Matrix
bpy.ops.wm.open_mainfile(filepath='/workspace/conceptD3/D3b_full_review_v2.blend')
R=232.0;FZ=-604
CH=bpy.data.materials["Charcoal_26282B"]
P={"cap_stack":(80,0.15,0.35,1),"cap_anchor":(35,0.0,0.0,1),"pod_L_anchor":(34,0.08,0.25,0),"pod_R_anchor":(34,0.08,0.25,0),"cw_anchor":(32,0.10,0.25,0)}
SOFT=("cap_base","cap_lid","pod_L_base","pod_L_lid","pod_R_base","pod_R_lid","cw_tub","cw_lid","saddle")
def soften(o,vox=0.6,it=10):
    m=o.modifiers.new("rm","REMESH");m.mode='VOXEL';m.voxel_size=vox
    s=o.modifiers.new("sm","SMOOTH");s.factor=0.9;s.iterations=it
    bpy.context.view_layer.objects.active=o
    for md in list(o.modifiers):
        with bpy.context.temp_override(object=o):bpy.ops.object.modifier_apply(modifier=md.name)
    for p in o.data.polygons:p.use_smooth=True
def warp_bend(o,Ra,halfL,a,zt,rot):
    me=o.data.copy();o.data=me
    M=o.matrix_basis.copy();me.transform(M);o.matrix_basis=Matrix.Identity(4)
    for v in me.vertices:
        x,y,z=v.co
        if rot:
            x,y=-y,x;t=min(abs(x)/halfL,1.0);y*=1-a*t**4;z*=1-zt*t**3
        else:
            t=min(abs(y)/halfL,1.0);x*=1-a*t**4;z*=1-zt*t**3
        phi=y/Ra;r=Ra+z
        v.co=(x,r*math.sin(phi),r*math.cos(phi)-Ra)
    me.update()
def sink(o,e,yoff,off):
    cen=e.matrix_world.inverted()@Vector((0,yoff,-R))
    for v in o.data.vertices:v.co-=(v.co-cen).normalized()*off
def place_pods(prefix,yoff):
    for n,sg in(("pod_L_anchor",-1),("pod_R_anchor",1)):
        e=bpy.data.objects[prefix+n];th=sg*80/R
        e.location=(0,yoff+(R+1.75)*math.sin(th),-R+(R+1.75)*math.cos(th));e.rotation_euler=(-th,0,0)
    bpy.context.view_layer.update()
def process(prefix,yoff):
    place_pods(prefix,yoff)
    center=Vector((0,yoff,-R))
    for an,(hl,a,zt,rot) in P.items():
        e=bpy.data.objects[prefix+an];Ra=(e.location-center).length
        for ch in list(e.children):
            if ch.type!='MESH':continue
            base=ch.name[len(prefix):]
            # subdivide lightly for smooth bend
            warp_bend(ch,Ra,hl,a,zt,rot)
            if 'plug' in base or base=='latch':sink(ch,e,yoff,1.3 if 'plug' in base else 0.8)
            if base in SOFT:soften(ch)
    # fairings
    col=bpy.data.collections["D3_assembled" if not prefix else "D3_exploded"]
    def fair(name,s0,s1,w0,w1,h0,h1):
        bm=bmesh.new();loops=[];N=28;K=24
        for i in range(K+1):
            u=i/K;s=s0+(s1-s0)*u;th=s/R
            ease=u*u*(3-2*u);w=w0+(w1-w0)*ease;h=h0+(h1-h0)*ease
            lo,hi=R-1.3,R+3.5+h;rc=(lo+hi)/2;hh=(hi-lo)/2
            ring=[]
            for j in range(N):
                ang=2*math.pi*j/N;c,sn=math.cos(ang),math.sin(ang)
                X=w/2*math.copysign(abs(c)**0.45,c);Rr=rc+hh*math.copysign(abs(sn)**0.45,sn)
                ring.append(bm.verts.new((X,yoff+Rr*math.sin(th),-R+Rr*math.cos(th))))
            loops.append(ring)
        for i in range(K):
            for j in range(N):bm.faces.new([loops[i][j],loops[i][(j+1)%N],loops[i+1][(j+1)%N],loops[i+1][j]])
        bm.faces.new(loops[0][::-1]);bm.faces.new(loops[-1])
        me=bpy.data.meshes.new(prefix+name);bm.to_mesh(me);bm.free()
        o=bpy.data.objects.new(prefix+name,me);col.objects.link(o);me.materials.append(CH);soften(o,0.8,6);return o
    for sg in(-1,1):
        tag="L" if sg<0 else "R"
        fair(f"fairing_cap_pod_{tag}",sg*34,sg*48,120,84,10,12)
        fair(f"fairing_pod_{tag}_strap",sg*110,sg*145,80,46,15,0.8)
        fair(f"fairing_cw_{tag}",math.pi*R+sg*28,math.pi*R+sg*60,66,46,15,0.8)
process("",0);process("D3__",700)
# lineup: reuse bent meshes
groups={}
for o in bpy.data.collections["D3_lineup"].objects:
    if o.type!='MESH' or not o.name.startswith("LU_") or o.name.startswith("LU_loose") or o.name=="LU_strap_loop":continue
    src=bpy.data.objects.get(o.name[3:])
    if not src:continue
    o.data=src.data;o.rotation_euler=(0,0,0);o.scale=(1,1,1)
    groups.setdefault(round(o.location.x),[]).append(o)
for gx,objs in groups.items():
    zmin=min(min(v.co.z for v in o.data.vertices) for o in objs)
    for o in objs:o.location.z=FZ-zmin
bpy.context.view_layer.update()
# export STLs (anchor-local shapes)
for o in bpy.data.collections["D3_assembled"].objects:
    if o.type=='MESH' and o.name!="strap_loop" and "plug" not in o.name:
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
        bpy.ops.wm.stl_export(filepath=f"/workspace/conceptD3/d5/{o.name}.stl",export_selected_objects=True,apply_modifiers=True)
# hero cam
st=bpy.data.collections["Studio"]
d=bpy.data.cameras.new("cam_hero");d.lens=55;d.clip_end=20000;h=bpy.data.objects.new("cam_hero",d);st.objects.link(h)
h.location=(-620,-470,-170);h.rotation_euler=(Vector((0,0,-40))-h.location).to_track_quat('-Z','Y').to_euler()
c=bpy.data.objects["cam_cap"];c.location=(-300,-380,170);c.rotation_euler=(Vector((0,0,-5))-c.location).to_track_quat('-Z','Y').to_euler()
sc=bpy.context.scene;sc.camera=bpy.data.objects["cam_lineup"]
bpy.ops.wm.save_as_mainfile(filepath='/workspace/conceptD3/D5_cap_lengthwise.blend')
sc.cycles.samples=40
for cam,res in [("cam_lineup",(1280,960)),("cam_cap",(1280,960)),("cam_hero",(1600,1200))]:
    sc.camera=bpy.data.objects[cam];sc.render.resolution_x,sc.render.resolution_y=res
    sc.render.filepath=f'/workspace/conceptD3/v5_{cam[4:]}.png';bpy.ops.render.render(write_still=True)
