"""usage: run_slice.py PLATE_DIR NAME PROCESS stl... ; slices, patches N7, parses every plate_N.gcode."""
import sys,os,subprocess,re,glob,json,shutil
H=os.path.dirname(os.path.abspath(__file__))   # repo: hardware/pods/plates/tools
ORCA=os.environ.get('ORCA','/home/box/tools/orca/squashfs-root/AppRun')            # OrcaSlicer 2.4.2 AppImage (extracted)
ORCA_LIBS=os.environ.get('ORCA_LIBS','/home/box/tools/orca/extralibs/root/usr/lib/x86_64-linux-gnu')
pd,name,proc=sys.argv[1:4];stls=[os.path.abspath(s) for s in sys.argv[4:]]

os.makedirs(pd,exist_ok=True);od=os.path.join(pd,'out_'+name);shutil.rmtree(od,ignore_errors=True);os.makedirs(od)
env=dict(os.environ,LD_LIBRARY_PATH=ORCA_LIBS)
tm=os.path.join(pd,name+'.gcode.3mf')
cmd=['timeout','1500',ORCA,'--arrange',os.environ.get('ARRANGE','1'),'--orient','0','--slice','0',
 '--load-settings',os.environ['PROFDIR']+'/machine.json;'+os.environ['PROFDIR']+'/'+proc,'--load-filaments',os.environ['PROFDIR']+'/'+os.environ['FIL'],'--export-3mf',name+'.gcode.3mf','--outputdir',os.path.abspath(od)]+stls
r=subprocess.run(cmd,env=env,capture_output=True,text=True,cwd=pd);open(os.path.join(od,'orca.log'),'w').write(r.stdout+r.stderr)
res={'name':name,'process':proc,'rc':r.returncode,'parts':[os.path.basename(s) for s in stls],'plates':[]}
try: res['result_json']=json.load(open(os.path.join(od,'result.json')))['error_string']
except Exception as e: res['result_json']=str(e)
for g in sorted(glob.glob(os.path.join(od,'plate_*.gcode'))):
    txt=open(g).read().splitlines();p={'gcode':os.path.relpath(g,pd)}
    for l in txt[:400]+txt[-400:]:
        m=re.search(r'total estimated time: (.+)$',l)
        if m:p['time']=m.group(1).strip()
        m=re.match(r'; (?:total )?filament used \[g\] = ([\d.]+)',l)
        if m:p['grams']=float(m.group(1))
        m=re.match(r'; total layer number: (\d+)',l) or re.match(r'; total layers count = (\d+)',l)
        if m:p['layers']=int(m.group(1))
        m=re.match(r'; max_z_height: ([\d.]+)',l)
        if m:p['max_z']=float(m.group(1))
    x=y=z=0.;xs=[];ys=[];feat={};t='';zmax=0
    for l in txt:
        if l.startswith('; FEATURE:'):t=l[10:].strip()
        elif l.startswith('G1') or l.startswith('G0'):
            mx=re.search(r'X([-\d.]+)',l);my=re.search(r'Y([-\d.]+)',l);mz=re.search(r'Z([-\d.]+)',l)
            if mx:x=float(mx.group(1))
            if my:y=float(my.group(1))
            if mz:z=float(mz.group(1))
            if (mx or my) and re.search(r' E[\d.]+',l) and l.startswith('G1'):
                xs.append(x);ys.append(y);zmax=max(zmax,z);feat[t]=feat.get(t,0)+1
    if xs:
        p['extrusion_X']=[min(xs),max(xs)];p['extrusion_Y']=[min(ys),max(ys)];p['extrusion_zmax']=zmax
        p['margin_min_mm']=round(min(min(xs),min(ys),256-max(xs),256-max(ys)),3)
        p['within_4mm_margin']=p['margin_min_mm']>=4.0
        p['support_moves']=sum(v for k,v in feat.items() if 'upport' in k);p['brim_moves']=sum(v for k,v in feat.items() if 'rim' in k)
    lay=os.path.join(pd,f'{name}_{os.path.basename(g)[:-6]}_layout.png')
    subprocess.run(['python3',f'{H}/layout.py',g,lay,f'{name} {os.path.basename(g)}'],capture_output=True)
    p['layout_png']=os.path.relpath(lay,pd);res['plates'].append(p)
res['plate_count']=len(res['plates'])
if os.path.exists(os.path.join(od,name+'.gcode.3mf')): shutil.move(os.path.join(od,name+'.gcode.3mf'),tm)
if os.path.exists(tm):
    f=subprocess.run(['python3',f'{H}/fix_bbl_3mf.py',tm,'N7']+stls,capture_output=True,text=True)
    res['fix_bbl']=('ok ' if f.returncode==0 else 'FAIL ')+(f.stdout+f.stderr).strip()[-300:]
json.dump(res,open(os.path.join(pd,name+'_slice.json'),'w'),indent=1)
print(json.dumps({k:v for k,v in res.items() if k!='parts'},indent=1))
