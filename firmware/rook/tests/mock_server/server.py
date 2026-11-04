# SPDX-License-Identifier: Apache-2.0
"""Mock OpenPasture v1 collar server for the Rook LTE-M reporter.

Mirrors the real ingest (openpasture crates/op-ingest/src/device.rs) as far
as the Rook touches it:
  POST /collar/v1/report   -> 200 {"latest_version": N|null[, "config": {...}]}
  GET  /collar/v1/boundary?have=H[&free=F&free_bytes=B]
                           -> 200 signed command | 204 nothing new | 409 gate refuses
  POST /collar/v1/ack      -> 204
Auth: `Authorization: Bearer <key>` (64 hex chars, default the dev key below).
Missing or unknown key -> 401; a body collar_id other than the key's -> 403.
Report checks (-> 400): fix point in range, accuracy_m present and >= 0,
battery a fraction 0..1, every fix/cue time RFC 3339 and at most 10 min ahead
of this server's clock. Without device.caps the collar is marked LEGACY.
Ack checks (-> 400): command_id, version, status received|applied|rejected, at.
Every response carries Date (the Rook uses it as its server clock).

Test hooks (no auth): GET /mock/state; POST /mock/boundary {"version":N};
POST /mock/fail {"status":503,"count":2,"retry_after":5};
POST /mock/gate {"refuse":true}; POST /mock/config {"version":N,"report_s":S}.

  python3 server.py --port 7878                    # plain HTTP, as behind the tunnel
  python3 server.py --port 8443 --tls cert.pem key.pem   # HTTPS
"""
import argparse
import json
import re
import ssl
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import sign

TOKEN = "0123456789abcdef" * 4
COLLAR_ID = "col_01J9SIMCOLLAR"
PREFIX = "/collar/v1"
MAX_AHEAD = timedelta(minutes=10)
ACK_STATUS = {"received", "applied", "rejected"}
RFC3339 = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:\d\d)$")


def fresh_state():
    return {"reports": [], "acks": [], "queries": [], "boundaries": [sign.boundary(1)],
            "fail": None, "gate_refuses": False, "config": None, "legacy": None,
            "devices": [], "slots": None}


STATE = fresh_state()
LOCK = threading.Lock()


def parse_time(s):
    if not isinstance(s, str) or not RFC3339.match(s):
        raise ValueError("time")
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def check_report(rep, now):
    """The 400s of PositionReport::validate and the clock check."""
    if not isinstance(rep, dict):
        return "bad_json"
    times = []
    for f in rep.get("fixes", []):
        p = f.get("point")
        if not (isinstance(p, list) and len(p) == 2 and all(isinstance(x, (int, float)) for x in p)
                and abs(p[0]) <= 180 and abs(p[1]) <= 90):
            return "Invalid fix point."
        a = f.get("accuracy_m", f.get("accuracy_meters"))
        if not isinstance(a, (int, float)) or a < 0:
            return "Invalid fix accuracy_m."
        try:
            times.append(parse_time(f.get("at")))
        except ValueError:
            return "Invalid fix at."
    for c in rep.get("cues", []):
        try:
            times.append(parse_time(c.get("at")))
        except ValueError:
            return "Invalid cue at."
    b = rep.get("battery")
    if b is not None and not (isinstance(b, (int, float)) and 0.0 <= b <= 1.0):
        return "Invalid battery."
    for s in rep.get("slots") or []:
        if s.get("status") == "rejected":
            return "Invalid slots."
    if times and max(times) > now + MAX_AHEAD:
        return "A fix or cue is timestamped in the future. Check the collar clock."
    return None


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, obj=None, headers=None):
        body = b"" if obj is None else json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)  # adds Date
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        if body:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _gate(self, path):
        if not path.startswith(PREFIX + "/"):
            return True
        auth = self.headers.get("Authorization") or ""
        key = auth[7:].strip() if auth[:7] in ("Bearer ", "bearer ") else ""
        if not key:
            self._send(401, {"error": "Missing collar key."})
            return False
        if key != TOKEN:
            self._send(401, {"error": "Unknown collar key."})
            return False
        with LOCK:
            f = STATE["fail"]
            if f and f["count"] > 0:
                f["count"] -= 1
                hdr = {"Retry-After": str(f["retry_after"])} if f.get("retry_after") else {}
                self._send(f["status"], {"error": "injected"}, hdr)
                return False
        return True

    def _collar_ok(self, obj):
        c = obj.get("collar_id")
        if c and c != COLLAR_ID:
            self._send(403, {"error": "This key belongs to collar %s, not %s." % (COLLAR_ID, c)})
            return False
        return True

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/mock/state":
            with LOCK:
                return self._send(200, {k: STATE[k] for k in
                                        ("reports", "acks", "queries", "legacy", "slots")} |
                                  {"latest_version": STATE["boundaries"][-1]["version"]})
        if not self._gate(u.path):
            return
        if u.path == PREFIX + "/boundary":
            q = parse_qs(u.query)
            try:
                have = int(q.get("have", ["0"])[0])
                free = int(q["free"][0]) if "free" in q else None
                free_bytes = int(q["free_bytes"][0]) if "free_bytes" in q else None
            except ValueError:
                return self._send(400, {"error": "Invalid query."})
            with LOCK:
                STATE["queries"].append({"have": have, "free": free, "free_bytes": free_bytes})
                newer = [b for b in STATE["boundaries"] if b["version"] > have]
                refuse = STATE["gate_refuses"]
            if newer:
                if refuse:
                    return self._send(409, {"error": "The safety gate refuses this boundary."})
                return self._send(200, newer[-1])  # the active (latest) one
            return self._send(204)
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        u = urlparse(self.path)
        raw = self._body()
        if u.path.startswith("/mock/"):
            obj = json.loads(raw or b"{}")
            with LOCK:
                if u.path == "/mock/boundary":
                    v = obj.get("version") or STATE["boundaries"][-1]["version"] + 1
                    STATE["boundaries"].append(sign.boundary(v))
                    return self._send(200, {"staged": v})
                if u.path == "/mock/fail":
                    STATE["fail"] = obj
                    return self._send(200, obj)
                if u.path == "/mock/gate":
                    STATE["gate_refuses"] = bool(obj.get("refuse"))
                    return self._send(200, obj)
                if u.path == "/mock/config":
                    STATE["config"] = sign.config(obj.get("version", 1),
                                                  report_s=obj.get("report_s", 60),
                                                  poll_s=obj.get("poll_s", 60))
                    return self._send(200, STATE["config"])
                if u.path == "/mock/reset":
                    STATE.clear()
                    STATE.update(fresh_state())
                    return self._send(200, {})
            return self._send(404, {"error": "not_found"})
        if not self._gate(u.path):
            return
        try:
            obj = json.loads(raw)
        except ValueError:
            return self._send(400, {"error": "Invalid JSON."})
        if not isinstance(obj, dict):
            return self._send(400, {"error": "Invalid JSON."})
        if u.path == PREFIX + "/report":
            if not self._collar_ok(obj):
                return
            err = check_report(obj, datetime.now(timezone.utc))
            if err:
                return self._send(400, {"error": err})
            dev = obj.get("device") or {}
            with LOCK:
                STATE["reports"].append(obj)
                if "device" in obj:
                    STATE["legacy"] = not dev.get("caps")
                elif STATE["legacy"] is None:
                    STATE["legacy"] = True
                if "slots" in obj:
                    STATE["slots"] = obj["slots"]
                latest = STATE["boundaries"][-1]["version"]
                resp = {"latest_version": latest}
                cfg = STATE["config"]
                if (cfg and "config" in dev.get("caps", []) and
                        (dev.get("config_version") or 0) < cfg["version"]):
                    resp["config"] = cfg
            return self._send(200, resp)
        if u.path == PREFIX + "/ack":
            if not self._collar_ok(obj):
                return
            ok = (isinstance(obj.get("command_id"), str) and isinstance(obj.get("version"), int)
                  and obj.get("status") in ACK_STATUS)
            try:
                parse_time(obj.get("at", obj.get("received_at")))
            except ValueError:
                ok = False
            if not ok:
                return self._send(400, {"error": "Invalid ack."})
            with LOCK:
                STATE["acks"].append(obj)
            return self._send(204)
        self._send(404, {"error": "not_found"})

    def log_message(self, fmt, *a):
        print("mock:", fmt % a, flush=True)


def main():
    global TOKEN, COLLAR_ID
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7878)
    ap.add_argument("--token", default=TOKEN)
    ap.add_argument("--collar", default=COLLAR_ID)
    ap.add_argument("--tls", nargs=2, metavar=("CERT", "KEY"))
    a = ap.parse_args()
    TOKEN, COLLAR_ID = a.token, a.collar
    srv = ThreadingHTTPServer((a.host, a.port), H)
    if a.tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(*a.tls)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    print("mock collar server on %s:%d%s, server public key %s" %
          (a.host, a.port, " (TLS)" if a.tls else "", sign.public_key_b64()), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
