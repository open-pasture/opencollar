"""10-point check of overnight_review_r4.blend. Run: python3 check_blend_r4.py  -> blend_check_r4.json"""
import bpy,os,json
R=os.path.dirname(os.path.abspath(__file__));f=os.path.join(R,'overnight_review_r4.blend')
bpy.ops.wm.open_mainfile(filepath=f);sc=bpy.context.scene
v3=[(a,s) for scr in bpy.data.screens for a in scr.areas if a.type=='VIEW_3D' for s in a.spaces if s.type=='VIEW_3D']
meshes=[o for o in bpy.data.objects if o.type=='MESH'];cols=[c.name for c in bpy.data.collections]
PNG=['r4_01_old_vs_A2_vs_A3_vs_D4.png','r4_02a_pod_clamp_underside.png','r4_02b_pod_clamp_end.png','r4_03_cavity_section_envelope.png','r4_04_plate_A3_top.png','r4_05_plate_A3_34.png','r4_06_plate_A3_gcode_layers.png']
ck={'1_opens':True,'2_has_VIEW_3D':len(v3)>0,
 '3_clip_end_ge_10000':all(s.clip_end>=10000 for a,s in v3),'4_clip_start_le_0p1':all(s.clip_start<=0.1001 for a,s in v3),
 '5_solid_object_colour':all(s.shading.type=='SOLID' and s.shading.color_type=='OBJECT' for a,s in v3),
 '6_view_frames_all':all(s.region_3d.view_distance>800 for a,s in v3),'7_all_meshes_nonempty':all(len(o.data.polygons)>0 for o in meshes),
 '8_units_mm':sc.unit_settings.length_unit=='MILLIMETERS' and abs(sc.unit_settings.scale_length-0.001)<1e-9,
 '9_collections':all(any(c.startswith(p) for c in cols) for p in ['Compare_','Pod_clamp_assembled','Section_cavity','Plate_A3']),
 '10_camera_and_pngs':sc.camera is not None and all(os.path.exists(os.path.join(R,p)) for p in PNG)}
out=dict(checks=ck,score=f"{sum(ck.values())}/10",n_view3d=len(v3),n_mesh=len(meshes),plate_objects=len([o for o in meshes if o.name.startswith('A3:')]),collections=cols)
print('RESULT',json.dumps(out));json.dump(out,open(os.path.join(R,'blend_check_r4.json'),'w'),indent=1)
