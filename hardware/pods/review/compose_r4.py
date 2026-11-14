"""Annotate the r4 renders (PIL) and draw the G-code layer plot. Run after build_r4.py. Repo-relative."""
import json,os,re,numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
R=os.path.dirname(os.path.abspath(__file__))+'/';P=os.path.abspath(R+'..')+'/'
rep=json.load(open(P+'checks/d4pod_report.json'));sl=json.load(open(P+'plates/overnight_petg_A3_d4/overnight_petg_A3_d4_slice.json'))
sha=open(P+'plates/overnight_petg_A3_d4/SHA256.txt').read().split()[0]
def F(s):
  for f in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/dejavu/DejaVuSans.ttf']:
    if os.path.exists(f):return ImageFont.truetype(f,s)
  return ImageFont.load_default()
def B(s):
  for f in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
    if os.path.exists(f):return ImageFont.truetype(f,s)
  return F(s)
# ---- r4_01 comparison
a,b,c=[Image.open(R+f) for f in ['_r4_01a_iso.png','_r4_01b_side.png','_r4_01c_end.png']]
W=a.width;rows=[('PR #21 (old)','69.8 x 92 x 26.2','R~7 plan, square top edge, crown 0'),
 ('A2 = pr28 shell (plate A2)','68 x 97 x 37.2','R9 plan, top roll ~2.4, crown 0'),
 ('A3 = NEW D4-style (this plate)',f"{rep['L']['plan_bounds'][2]*2:.0f} (77.2 at ears) x 97 x {rep['L']['assembled_height']}",f"D4 plan R10/19, shoulder R{rep['L']['shoulder']['arc_R']} + 45 chamfer: inset {rep['L']['shoulder']['inset_at_top']} over {rep['L']['shoulder']['drop']} drop"),
 ('D4_contoured_v3 (target)','67 x 97.2 x 21.3','R10/19 plan, shoulder ~9 drop over 7.4, crown ~0.4')]
H=a.height+b.height+180+60*len(rows)
im=Image.new('RGB',(W,H),(245,243,236));d=ImageDraw.Draw(im)
d.text((20,15),'r4_01  Action pod L: old PR #21 | A2 (pr28) | A3 new D4-style | D4_contoured_v3   (all flat, mount face +Y, same scale)',font=B(30),fill=(20,20,20))
im.paste(a,(0,70));im.paste(b,(0,70+a.height));y=70+a.height+b.height+10
xs=[W*0.5-W*0.36*1.5/1.0*0.0+(-180+i*120)*W/480 for i in range(4)]
for i,(n,dm,sh) in enumerate(rows):
  d.text((20,y+i*55),n,font=B(26),fill=(140,40,20) if i==2 else (30,30,30));d.text((560,y+i*55),dm,font=F(26),fill=(30,30,30));d.text((1060,y+i*55),sh,font=F(24),fill=(60,60,60))
d.text((20,H-45),'Underside flat on all four. A3 height = floor 2.5 + locked internal 20.7 + lid 2.6 (D4 21.3 is not reachable with the locked 19.5 cavity and 2.4 walls).',font=F(22),fill=(90,30,30))
im.save(R+'r4_01_old_vs_A2_vs_A3_vs_D4.png')
# ---- r4_03 section
s=Image.open(R+'_r4_03_section.png');im=Image.new('RGB',(s.width,s.height+230),(245,243,236));im.paste(s,(0,90));d=ImageDraw.Draw(im)
L=rep['L'];d.text((20,15),'r4_03  Cavity sections, action pod L (A3). Green = locked electronics envelope 58 x 82 x 19.5 sitting on the floor.',font=B(30),fill=(20,20,20))
d.text((20,52),'left: section at y = -2 (cell axis), looking +Y      right: section at x = 0 (long axis, turned 90°), mount face +Y at LEFT',font=F(24),fill=(60,60,60))
t=[f"cavity {L['cavity_bounds'][2]-L['cavity_bounds'][0]:.1f} x {L['cavity_bounds'][3]-L['cavity_bounds'][1]:.2f} (spec 58 x 82; the extra 0.25 is the pr28 source) | floor {L['floor_thickness']} | floor-to-lid {L['internal_height_floor_to_lid']} (envelope 19.5 -> 1.2 headroom) | lid 2.6 | assembled {L['assembled_height']}",
   f"cavity air volume old vs new (prism above old floor): {L['cavity_prism_material_old_vs_new_mm3'][0]} vs {L['cavity_prism_material_old_vs_new_mm3'][1]} mm3 of internal features: unchanged (columns, buzzer seat, glyphs, lid key copied from pr28)",
   "inserts moved OUT of the cavity to side ears at x = +/-33.6: nothing under the floor; underside flat for the clamp"]
for i,x in enumerate(t):d.text((20,s.height+100+i*40),x,font=F(23),fill=(30,30,30))
im.save(R+'r4_03_cavity_section_envelope.png')
# ---- r4_04 / r4_05 plate with labels
lab=json.load(open(R+'_r4_labels.json'));p=sl['plates'][0]
hdr=f"overnight_petg_A3_d4 | sha256 {sha[:16]}... | {p['time']} | {p['grams']} g | {p['layers']} layers | margin {p['margin_min_mm']} mm | supports 0 | brims on 4 shims only | PETG A2 only"
def short(n):
  return n.replace('action_pod_','').replace('clamp_bar_','bar').replace('spacer_','s').replace('width_shim_','shim').replace('_0','.0').replace('p','.')
for src,dst,k,fs in [('_r4_04_plate_top.png','r4_04_plate_A3_top.png','top',20),('_r4_05_plate_34.png','r4_05_plate_A3_34.png','34',18)]:
  s=Image.open(src if os.path.isabs(src) else R+src);im=Image.new('RGB',(s.width,s.height+70),(245,243,236));im.paste(s,(0,70));d=ImageDraw.Draw(im)
  d.text((15,12),hdr,font=B(18 if s.width>1450 else 15),fill=(20,20,20))
  for n,(u,v) in lab[k].items():
    if n.startswith('spacer') and not n.endswith('01'):continue
    txt=short(n) if not n.startswith('spacer') else 'spacer '+n.split('_')[1].replace('p','.')+' x4'
    x,y=u*s.width,v*s.height+70;w_=d.textlength(txt,font=F(fs))
    d.rectangle([x-w_/2-3,y-fs/2-3,x+w_/2+3,y+fs/2+3],fill=(255,255,240));d.text((x-w_/2,y-fs/2-1),txt,font=F(fs),fill=(150,30,10))
  im.save(R+dst)
# ---- r4_06 G-code layer plot
g=P+'plates/overnight_petg_A3_d4/out_overnight_petg_A3_d4/plate_1.gcode'
x=y=z=0.;t='';segs={};prev=None
for l in open(g):
  if l.startswith('; FEATURE:'):t=l[10:].strip()
  elif l.startswith('G1') or l.startswith('G0'):
    mx=re.search(r'X([-\d.]+)',l);my=re.search(r'Y([-\d.]+)',l);mz=re.search(r'Z([-\d.]+)',l);px,py=x,y
    if mx:x=float(mx.group(1))
    if my:y=float(my.group(1))
    if mz:z=round(float(mz.group(1)),2)
    if l.startswith('G1') and (mx or my) and re.search(r' E[\d.]+',l):segs.setdefault(z,[]).append((px,py,x,y,t))
Z=sorted(k for k in segs if k<=24 and len(segs[k])>20)
pick=[Z[0]]+[min(Z,key=lambda q:abs(q-v)) for v in (1.0,3.0,6.6,12.0,16.4,19.4,21.6,23.2)]
col={'Outer wall':'#c0392b','Inner wall':'#e67e22','Sparse infill':'#7f8c8d','Internal solid infill':'#2980b9','Top surface':'#27ae60','Bottom surface':'#8e44ad','Bridge':'#f1c40f','Skirt':'#bbbbbb','Brim':'#16a085','Overhang wall':'#ff00ff','Gap infill':'#34495e'}
fig,axs=plt.subplots(3,3,figsize=(18,18))
for ax,zz in zip(axs.flat,pick):
  for (x0,y0,x1,y1,tt) in segs[zz]:ax.plot([x0,x1],[y0,y1],color=col.get(tt,'k'),lw=0.5)
  ax.set_xlim(0,256);ax.set_ylim(0,256);ax.set_aspect('equal');ax.set_title(f'layer z={zz} mm ({len(segs[zz])} moves)',fontsize=13)
  ax.add_patch(plt.Rectangle((4,4),248,248,fill=False,ls='--',color='r',lw=0.8))
from matplotlib.lines import Line2D
fig.legend([Line2D([0],[0],color=v,lw=3) for v in col.values()],list(col.keys()),loc='lower center',ncol=6,fontsize=12)
fig.suptitle(f"r4_06  overnight_petg_A3_d4 G-code layers (OrcaSlicer 2.4.2, N7) | {p['time']} | {p['grams']} g | {p['layers']} layers | support extrusions {p['support_moves_total']} | red dashed = 4 mm margin",fontsize=15)
plt.tight_layout(rect=(0,0.04,1,0.97));plt.savefig(R+'r4_06_plate_A3_gcode_layers.png',dpi=70)
print('ok')
