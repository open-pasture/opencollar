"""oc.check_printable (ray thickness, as 3D-Print Toolbox) at min_wall 2.4 on the new parts; printed pr28 source for comparison."""
import sys,json,os
H=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,H)
import bpy,oc
NEW=os.path.join(H,'..','stl')+'/';OLD=os.path.join(H,'..','src_pr28_352e734')+'/'
pairs=[('action_pod_L_base','pod_L_base'),('action_pod_R_base','pod_R_base'),('action_pod_L_lid','pod_L_lid'),('action_pod_R_lid','pod_R_lid'),
 ('clamp_bar',None),('spacer_0p5',None),('spacer_1p0',None),('spacer_2p0',None),('width_shim',None)]
def chk(path):
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.wm.stl_import(filepath=path);o=bpy.context.selected_objects[0]
  return oc.check_printable(o,min_wall=2.4,overhang_deg=45.0)
res={}
for n,o in pairs:
  r={'new':chk(NEW+n+'.stl')}
  if o:r['printed_source']=chk(OLD+o+'.stl')
  res[n]=r;print(n,json.dumps(r))
json.dump(res,open(os.path.join(H,'..','checks','wallcheck_oc_2p4.json'),'w'),indent=1)
