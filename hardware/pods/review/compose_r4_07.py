"""Annotate r4_07 shock-bay keep-out renders (PIL). Run after build_r4_07_shockbay.py. Repo-relative."""
import json,os
from PIL import Image,ImageDraw,ImageFont
R=os.path.dirname(os.path.abspath(__file__))+'/';P=os.path.abspath(R+'..')+'/'
J=json.load(open(P+'checks/shockbay_keepout.json'));pr=json.load(open(R+'_r4_07_proj.json'))
N=J['configs']['nominal 3.8 strap, stack 1.0+0.5'];T=J['configs']['thin 3.0 strap, stack 0.5'];K=J['configs']['thick 7.5 strap, stack 4.5']
m=N['per_keepout']['module'];d=N['per_keepout']['driver']
def F(s,b=False):
  f='/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'%('-Bold' if b else '')
  return ImageFont.truetype(f,s) if os.path.exists(f) else ImageFont.load_default()
RED=(190,20,20);INK=(25,25,25);GRY=(70,70,70)
def frame(raw,title,sub,foot,top=120):
  im0=Image.open(R+raw).convert('RGB');W,H=im0.size;im=Image.new('RGB',(W,H+top+40*len(foot)+30),(245,243,236));im.paste(im0,(0,top))
  dr=ImageDraw.Draw(im);dr.text((20,14),title,font=F(30,True),fill=INK)
  for i,s in enumerate(sub):dr.text((20,56+i*30),s,font=F(21),fill=GRY)
  return im,dr,top
def wrap(dr,s,font,w):
  out=[];cur=''
  for wd in s.split(' '):
    t=(cur+' '+wd).strip()
    if dr.textlength(t,font=font)>w and cur:out.append(cur);cur=wd
    else:cur=t
  return out+[cur]
def frame(raw,title,sub,foot,top=None):
  im0=Image.open(R+raw).convert('RGB');W,H=im0.size;tmp=ImageDraw.Draw(Image.new('RGB',(10,10)))
  sl=[l for s in sub for l in wrap(tmp,s,F(21),W-40)];fl=[(l,c) for s,c in foot for l in wrap(tmp,s,F(23,c==RED),W-40)]
  top=60+30*len(sl)+10
  im=Image.new('RGB',(W,H+top+34*len(fl)+30),(245,243,236));im.paste(im0,(0,top));dr=ImageDraw.Draw(im)
  dr.text((20,14),title,font=F(28,True),fill=INK)
  for i,s in enumerate(sl):dr.text((20,56+i*30),s,font=F(21),fill=GRY)
  for i,(s,c) in enumerate(fl):dr.text((20,H+top+14+i*34),s,font=F(23,c==RED),fill=c)
  return im,dr,top
def P_(img,k,top):x,y=pr[img][k];return x,y+top
def vdim(dr,x,y0,y1,label,col=RED,side=1):
  dr.line([(x,y0),(x,y1)],fill=col,width=3)
  for y in(y0,y1):dr.line([(x-10,y),(x+10,y)],fill=col,width=3)
  dr.text((x+14*side if side>0 else x-14-dr.textlength(label,font=F(22,True)),(y0+y1)/2-12),label,font=F(22,True),fill=col)
def hdim(dr,y,x0,x1,label,col=RED):
  dr.line([(x0,y),(x1,y)],fill=col,width=3)
  for x in(x0,x1):dr.line([(x,y-10),(x,y+10)],fill=col,width=3)
  dr.text(((x0+x1)/2-dr.textlength(label,font=F(21,True))/2,y+12),label,font=F(21,True),fill=col)
def hline(dr,y,x0,x1,label,col=GRY):
  for x in range(int(x0),int(x1),18):dr.line([(x,y),(x+9,y)],fill=col,width=2)
  dr.text((x1+8,y-12),label,font=F(19),fill=col)
LEG='Legend: tan = A3 action pod L | orange = U clamp bars (y = -27.5 / +22.5) | yellow = C-clip spacers | grey = M3x12 | blue translucent = strap 44.45 x 3.8 | RED = shock bay keep-outs (module 31x46x10, driver 28x41x8) | pale red = reserved saddle 52x97x13.7 | magenta = wire pass-through d8 @ (0,-28) + saddle M3 @ (+-18,+-32)'
verdict=f"FAIL: strap intrudes {m['strap_intrusion_depth_z']} mm into the keep-out (thin strap {T['per_keepout']['module']['strap_intrusion_depth_z']}, 7.5 strap {K['per_keepout']['module']['strap_intrusion_depth_z']}); clamp bar base sits fully inside it (z {m['clampbar_z_in_keepout_footprint'][0]}..{m['clampbar_z_in_keepout_footprint'][1]}, {m['clampbar_overlap_thickness_z']} mm thick; {m['clampbar_intrusion_mm3']:.0f} mm3 module, {d['clampbar_intrusion_mm3']:.0f} mm3 driver)"
# ---- iso
im,dr,top=frame('_r4_07_iso.png','r4_07  Shock/electrode bay keep-out vs A3 action pod + U clamp + strap (iso from the neck side)',
  ['Keep-out = PR #28 @ 352e734 pod_saddle.py Option A neck saddle (PLACEHOLDER sizes, not a spec), mapped 1:1 in pod XY, saddle face on the A3 underside (z = 0).',
   'Nominal clamp: 3.8 mm strap, stack 1.0 + 0.5 (lip gap 4.0), M3x12.  ' ],
  [(LEG,GRY),(verdict,RED),
   ("The A3 pod has NO defined shock bay: the pr28 wire pass-through d8 (0,-28) and saddle M3 holes (+-18,+-32) are blind from below (1.75 mm skin), and both sit under a clamp bar.",RED),
   (f"Clear: M3 heads to module/driver keep-out {m['screw_head_lateral_clear']} / {d['screw_head_lateral_clear']} mm (to the 52 mm saddle envelope {N['saddle_envelope']['screw_head_lateral_clear']} mm); spacers {m['spacer_lateral_clear']} mm; width shims {m['width_shim_lateral_clear']} mm.",INK)])
for k,lab in [('mod_c','module keep-out 31x46x10'),('drv_c','driver keep-out 28x41x8'),('strap_c','strap (44.45 x 3.8)')]:
  x,y=P_('_r4_07_iso.png',k,top);dr.ellipse([x-6,y-6,x+6,y+6],fill=RED);dr.text((x+10,y-30),lab,font=F(22,True),fill=RED)
im.save(R+'r4_07_shockbay_keepout_iso.png')
# ---- secX (long section at x = 0)
img='_r4_07_secX.png'
im,dr,top=frame(img,'r4_07  Section x = 0 (long axis), looking +X. Mount face +Y at LEFT, strap end at RIGHT.',
  ['Z levels (pod underside = 0, neck = down): strap -4.0..-0.2 | keep-out top -2.5 (saddle 2.5 face wall) / bottom -12.5 module, -10.5 driver | clamp bar -8.0..-1.5',
   'Bar at y -27.5 sits inside the module keep-out; bar at y +22.5 inside the driver keep-out. Wire pass-through (0,-28) is directly above bar 1 and is closed by a 1.75 mm skin.'],
  [(verdict,RED),(f"strap-to-keep-out gap = {m['strap_to_keepout_z_gap']} mm (negative = overlap) | clamp bar-to-keep-out gap = {m['clampbar_to_keepout_z_gap']} mm | bars cover y -37.5..-17.5 and 12.5..32.5; the 30 mm gap between them is shorter than the 46 mm module.",INK)])
x0=pr[img]['ko_top'][0]
yz={k:P_(img,k,top)[1] for k in['pod_under','strap_bot','ko_top','ko_bot','bar_bot']}
W=im.width
for k,lab in [('pod_under','z 0 pod underside'),('ko_top','z -2.5 keep-out top'),('strap_bot','z -4.0 strap bottom'),('bar_bot','z -8.0 bar bottom'),('ko_bot','z -12.5 keep-out bottom')]:
  hline(dr,yz[k],60,W-330,lab)
vdim(dr,W-360,yz['ko_top'],yz['strap_bot'],f"strap in keep-out {m['strap_intrusion_depth_z']}",side=-1)
vdim(dr,90,yz['ko_top'],yz['bar_bot'],f"bar bottom {-m['clampbar_to_keepout_z_gap']} below keep-out top")
im.save(R+'r4_07_shockbay_keepout_section_long.png')
# ---- secY (cross-section at y = -27.5: bar 1 + module keep-out)
img='_r4_07_secY.png'
im,dr,top=frame(img,'r4_07  Section y = -27.5 (through clamp bar 1 + module keep-out), looking -Y',
  ['Lateral: module keep-out |x| <= 15.5, saddle envelope |x| <= 26, strap |x| <= 22.2, M3 at x = +-33.6 (head r 2.75), spacers OD 7, shims at |x| 22.7..25',
   'Screws, spacers and inserts clear the keep-out sideways; the strap and the bar base between the lips do not.'],
  [(verdict,RED),(f"M3 head to module keep-out {m['screw_head_lateral_clear']} mm | to saddle envelope {N['saddle_envelope']['screw_head_lateral_clear']} mm | spacer {m['spacer_lateral_clear']} mm | width shim {m['width_shim_lateral_clear']} mm | screw shank {m['screw_shank_lateral_clear']} mm",INK)])
yk=P_(img,'ko_x',top)[1]+70
xk=P_(img,'ko_x',top)[0];xh=P_(img,'head_x',top)[0];xs=P_(img,'sad_x',top)[0]
hdim(dr,yk,xk,xh,f"{m['screw_head_lateral_clear']} head-to-keep-out")
hdim(dr,yk+60,xs,xh,f"{N['saddle_envelope']['screw_head_lateral_clear']} to saddle")
yz={k:P_(img,k,top)[1] for k in['pod_under','strap_bot','ko_top','ko_bot','bar_bot']}
vdim(dr,im.width-60,yz['ko_top'],yz['bar_bot'],f"bar bottom {-m['clampbar_to_keepout_z_gap']} below keep-out top",side=-1)
vdim(dr,120,yz['ko_top'],yz['strap_bot'],f"{m['strap_intrusion_depth_z']} strap")
im.save(R+'r4_07_shockbay_keepout_section_cross.png')
print('ok')
