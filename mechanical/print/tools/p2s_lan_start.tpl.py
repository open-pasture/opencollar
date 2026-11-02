# Transient P2S start-print script. __CODE__ is substituted on the box; never store the substituted copy.
import socket, ssl, struct, json, time, os, sys, hashlib, subprocess
IP="192.168.1.248"; SER="22E8AJ673000665"; USER="bblp"; CODE="__CODE__"
F=os.path.expanduser("~/Documents/openpasture/opencollar/mechanical/print/sliced/p2s_pla/F2_cap.gcode.3mf")
NAME="F2_cap.gcode.3mf"
def scrub(s): return str(s).replace(CODE,"***")
ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
def vl(n):
    b=b""
    while True:
        d=n%128; n//=128
        if n: d|=128
        b+=bytes([d])
        if not n: return b
def s16(x): x=x.encode(); return struct.pack(">H",len(x))+x
def rd(s,n):
    b=b""
    while len(b)<n:
        c=s.recv(n-len(b))
        if not c: raise EOFError
        b+=c
    return b
def rpkt(s):
    h=rd(s,1)[0]; m=0; mul=1
    while True:
        d=rd(s,1)[0]; m+=(d&127)*mul; mul*=128
        if not d&128: break
    return h,rd(s,m)
def mqtt():
    s=ctx.wrap_socket(socket.create_connection((IP,8883),timeout=15)); s.settimeout(15)
    vh=s16("MQTT")+bytes([4,0xC2])+struct.pack(">H",60)
    pl=s16("opmaker%d"%os.getpid())+s16(USER)+s16(CODE)
    s.sendall(b"\x10"+vl(len(vh+pl))+vh+pl); h,b=rpkt(s)
    if b[1]!=0: raise Exception("mqtt connack %d"%b[1])
    t=s16("device/%s/report"%SER)+b"\x00"
    s.sendall(b"\x82"+vl(2+len(t))+struct.pack(">H",1)+t); rpkt(s)
    return s
def pub(s,obj):
    t=s16("device/%s/request"%SER); p=json.dumps(obj).encode()
    s.sendall(b"\x30"+vl(len(t)+len(p))+t+p)
def status(s,wait=12):
    pub(s,{"pushing":{"sequence_id":"1","command":"pushall","version":1,"push_target":1}})
    end=time.time()+wait; best=None
    while time.time()<end:
        try: h,b=rpkt(s)
        except socket.timeout: break
        if h>>4!=3: continue
        tl=struct.unpack(">H",b[:2])[0]
        try: j=json.loads(b[2+tl:])
        except Exception: continue
        p=j.get("print")
        if p and "gcode_state" in p: best=p
    return best
def show(p):
    keys=["gcode_state","subtask_name","gcode_file","mc_percent","layer_num","total_layer_num","mc_remaining_time","print_error","nozzle_temper","bed_temper","sdcard"]
    print(scrub(json.dumps({k:p.get(k) for k in keys},indent=1)))
m=mqtt(); p=status(m)
if not p: print("NO STATUS"); sys.exit(2)
print("PRE:"); show(p)
if p.get("gcode_state") not in ("FINISH","IDLE") or p.get("print_error",0)!=0:
    print("NOT READY - aborting, nothing sent"); sys.exit(3)
cfg='url = "ftps://%s:990/%s"\nuser = "%s:%s"\ninsecure\nftp-pasv\nupload-file = "%s"\nssl-reqd\nsilent\nshow-error\nconnect-timeout = 15\nmax-time = 240\n'%(IP,NAME,USER,CODE,F)
r=subprocess.run(["curl","-K","-"],input=cfg.encode(),capture_output=True)
print("curl exit",r.returncode,scrub(r.stderr.decode()[:300]))
if r.returncode!=0: sys.exit(5)
md5=hashlib.md5(open(F,"rb").read()).hexdigest()
pub(m,{"print":{"sequence_id":"20","command":"project_file","param":"Metadata/plate_1.gcode","project_id":"0","profile_id":"0","task_id":"0","subtask_id":"0","subtask_name":"F2_cap","file":"","url":"ftp:///"+NAME,"md5":md5,"timelapse":False,"bed_type":"auto","bed_levelling":True,"flow_cali":True,"vibration_cali":True,"layer_inspect":True,"use_ams":True,"ams_mapping":[0],"skip_objects":None}})
print("print command sent; waiting")
time.sleep(25)
p=status(m,15); print("POST:"); show(p) if p else print("no status")
