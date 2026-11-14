# /// script
# dependencies = ["matplotlib"]
# ///
import sys,re,matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
g,out,title=sys.argv[1:4];xs=[];ys=[];cs=[];x=y=0;t='';z=0
col={'Support':'orange','Brim':'red'}
for l in open(g):
    if l.startswith('; FEATURE:'):t=l[10:].strip()
    elif l.startswith('G1'):
        m=re.search(r'X([-\d.]+)',l);n=re.search(r'Y([-\d.]+)',l)
        if m:x=float(m.group(1))
        if n:y=float(n.group(1))
        e=re.search(r' E([\d.]+)',l)
        if e and (m or n):xs.append(x);ys.append(y);cs.append('orange' if 'Support' in t else 'red' if 'Brim' in t else 'steelblue')
k=max(1,len(xs)//400000)
f,a=plt.subplots(figsize=(7,7));a.scatter(xs[::k],ys[::k],s=0.05,c=cs[::k])
a.add_patch(plt.Rectangle((0,0),256,256,fill=False));a.add_patch(plt.Rectangle((4,4),248,248,fill=False,ls='--',ec='gray'))
a.set_xlim(-5,261);a.set_ylim(-5,261);a.set_aspect('equal');a.set_title(title+' (blue part, orange support, red brim; dashed=4mm margin)',fontsize=8)
f.savefig(out,dpi=110)
