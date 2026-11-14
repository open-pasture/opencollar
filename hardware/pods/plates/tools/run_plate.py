"""usage: run_perobj_954f80a.py PLATE_DIR NAME PROCESS ARRANGE OVERRIDES_JSON stl...
pass1: run_slice.py (ARRANGE) -> 3MF; inject per-object metadata overrides {substr:{key:val}}; reslice with --arrange 0;
fix_bbl N7; layout; parse G-code incl. per-object support/brim move counts."""
import sys,os,subprocess,re,json,zipfile,shutil,glob
H=os.path.dirname(os.path.abspath(__file__))   # repo: hardware/pods/plates/tools
ORCA=os.environ.get('ORCA','/home/box/tools/orca/squashfs-root/AppRun')            # OrcaSlicer 2.4.2 AppImage (extracted)
ORCA_LIBS=os.environ.get('ORCA_LIBS','/home/box/tools/orca/extralibs/root/usr/lib/x86_64-linux-gnu')
pd,name,proc,arr,ovj=sys.argv[1:6];stls=[os.path.abspath(s) for s in sys.argv[6:]]
pd=os.path.abspath(pd);os.makedirs(pd,exist_ok=True)
PR=os.environ['PROFDIR'];FIL=os.environ['FIL']
ov=json.loads(ovj)
env=dict(os.environ,ARRANGE=arr)
p1=name+'_pass1'
r=subprocess.run(['python3',os.path.join(H,'run_slice1.py'),pd,p1,proc]+stls,env=env,capture_output=True,text=True)
src=os.path.join(pd,p1+'.gcode.3mf');assert os.path.exists(src),r.stdout+r.stderr
inp=os.path.join(pd,name+'_perobj_input.3mf')
zi=zipfile.ZipFile(src);zo=zipfile.ZipFile(inp,'w',zipfile.ZIP_DEFLATED);applied=[]
for it in zi.infolist():
    d=zi.read(it.filename)
    if it.filename.endswith('.gcode') or it.filename.endswith('.md5'): continue
    if it.filename=='Metadata/model_settings.config':
        c=d.decode()
        def fix(m):
            blk=m.group(0);nm=re.search(r'<metadata key="name" value="([^"]+)"',blk).group(1)
            for sub,kv in ov.items():
                if sub in nm:
                    for k,v in kv.items():
                        hd,rest=blk.split('\n',1)
                        # drop object-level existing key (first occurrence before <part)
                        pre,sep,post=rest.partition('<part')
                        pre=re.sub(rf'\s*<metadata key="{k}" value="[^"]*"/>','',pre)
                        blk=hd+f'\n    <metadata key="{k}" value="{v}"/>'+pre+sep+post
                        applied.append((nm,k,v))
            return blk
        c=re.sub(r'<object id="\d+">.*?</object>',fix,c,flags=re.S);d=c.encode()
    if it.filename=='3D/3dmodel.model' and os.environ.get('POS'):
        pos=json.loads(os.environ['POS']);c=d.decode()
        names=dict(re.findall(r'<object id="(\d+)">\s*<metadata key="name" value="([^"]+)"',zi.read('Metadata/model_settings.config').decode()))
        def mv(m):
            oid=m.group(1);nm=names.get(oid,'');t=m.group(2).split()
            for sub,(px,py) in pos.items():
                if nm.replace('.stl','')==sub: t[:9]='1 0 0 0 1 0 0 0 1'.split();t[9],t[10]=str(px),str(py);applied.append((nm,'pos',(px,py)))
            return m.group(0).replace(m.group(2),' '.join(t))
        c=re.sub(r'<item objectid="(\d+)"[^>]*?transform="([^"]+)"',mv,c);d=c.encode()
    zo.writestr(it,d)
zo.close()
od=os.path.join(pd,'out_'+name);shutil.rmtree(od,ignore_errors=True);os.makedirs(od)
e2=dict(os.environ,LD_LIBRARY_PATH=ORCA_LIBS)
cmd=['timeout','1500',ORCA,'--arrange','0','--orient','0','--slice','0','--load-settings',f'{PR}/machine.json;{PR}/{proc}','--load-filaments',f'{PR}/{FIL}','--export-3mf',name+'.gcode.3mf','--outputdir',od,inp]
r=subprocess.run(cmd,env=e2,capture_output=True,text=True,cwd=pd);open(os.path.join(od,'orca.log'),'w').write(r.stdout+r.stderr)
tm=os.path.join(pd,name+'.gcode.3mf');shutil.move(os.path.join(od,name+'.gcode.3mf'),tm)
f=subprocess.run(['python3',f'{H}/fix_bbl_3mf.py',tm,'N7']+stls,capture_output=True,text=True)
res={'name':name,'process':proc,'arrange_pass1':arr,'orca_rc':r.returncode,'overrides_applied':applied,'parts':[os.path.basename(s) for s in stls],
     'fix_bbl_rc':f.returncode,'fix_bbl':(f.stdout+f.stderr).strip()[-300:],'plates':[]}
with zipfile.ZipFile(tm) as z:
    names=z.namelist();res['gcode_in_3mf']=[n for n in names if n.endswith('.gcode')]
    sl=[n for n in names if 'slice_info' in n]
    res['printer_model_id']=re.findall(r'printer_model_id" value="([^"]*)"',z.read(sl[0]).decode()) if sl else None
for g in sorted(glob.glob(os.path.join(od,'plate_*.gcode'))):
    txt=open(g).read().splitlines();p={'gcode':os.path.relpath(g,pd)}
    for l in txt:
        if not l.startswith(';'):continue
        m=re.search(r'total estimated time: (.+)$',l);  p.update(time=m.group(1).strip()) if m else None
        m=re.match(r'; filament used \[g\] = ([\d.]+)',l); p.update(grams=float(m.group(1))) if m else None
        m=re.match(r'; total layer number: (\d+)',l); p.update(layers=int(m.group(1))) if m else None
        m=re.match(r'; max_z_height: ([\d.]+)',l); p.update(max_z=float(m.group(1))) if m else None
    x=y=z=0.;xs=[];ys=[];t='';obj=None;per={};zmax=0
    for l in txt:
        if l.startswith('; printing object '):obj=l[18:].split(' id:')[0]
        elif l.startswith('; stop printing object '):obj=None
        elif l.startswith('; FEATURE:'):t=l[10:].strip()
        elif l.startswith('G1') or l.startswith('G0'):
            mx=re.search(r'X([-\d.]+)',l);my=re.search(r'Y([-\d.]+)',l);mz=re.search(r'Z([-\d.]+)',l)
            if mx:x=float(mx.group(1))
            if my:y=float(my.group(1))
            if mz:z=float(mz.group(1))
            if l.startswith('G1') and (mx or my) and re.search(r' E[\d.]+',l):
                xs.append(x);ys.append(y);zmax=max(zmax,z)
                d=per.setdefault(obj or '_none',{'support':0,'brim':0,'moves':0});d['moves']+=1
                if 'upport' in t:d['support']+=1
                if 'rim' in t:d['brim']+=1
    p['extrusion_X']=[min(xs),max(xs)];p['extrusion_Y']=[min(ys),max(ys)];p['extrusion_zmax']=zmax
    p['margin_min_mm']=round(min(min(xs),min(ys),256-max(xs),256-max(ys)),3);p['within_4mm_margin']=p['margin_min_mm']>=4.0
    p['support_moves_total']=sum(v['support'] for v in per.values());p['per_object']=per
    lay=os.path.join(pd,f'{name}_{os.path.basename(g)[:-6]}_layout.png')
    subprocess.run(['python3',f'{H}/layout.py',g,lay,f'{name} {os.path.basename(g)} @'+os.environ.get('COMMIT','')],capture_output=True);p['layout_png']=os.path.basename(lay)
    res['plates'].append(p)
json.dump(res,open(os.path.join(pd,name+'_slice.json'),'w'),indent=1)
print(json.dumps({k:v for k,v in res.items() if k not in('parts',)},indent=1)[:3000])
