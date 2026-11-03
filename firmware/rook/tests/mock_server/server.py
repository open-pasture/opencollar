# SPDX-License-Identifier: Apache-2.0
"""Mock OpenPasture v1 collar server for the Rook LTE-M reporter.

Implements protocol/README.md "Endpoints":
  POST /collar/v1/report    -> 200 {"latest_version": N}
  GET  /collar/v1/boundary?have=H[&free=F&free_bytes=B] -> 200 command | 204
  POST /collar/v1/ack       -> 204
plus GET /mock/state (what it received) and POST /mock/boundary {"version":N}
to stage a newer signed boundary, POST /mock/fail {"status":503,"count":2,
"retry_after":5} to inject failures.

Auth: Authorization: Bearer <token>, default the vectors' collar key
"0123456789abcdef0123456789abcdef" (--token). Wrong token -> 401.

  python3 server.py --port 8080                    # plain HTTP
  python3 server.py --port 8443 --tls cert.pem key.pem   # HTTPS
"""
import argparse
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import sign

STATE = {"reports": [], "acks": [], "boundaries": [sign.boundary(1)], "fail": None}
LOCK = threading.Lock()
TOKEN = "0123456789abcdef0123456789abcdef"
PREFIX = "/collar/v1"


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, obj=None, headers=None):
        body = b"" if obj is None else json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
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
        if self.headers.get("Authorization") != "Bearer " + TOKEN:
            self._send(401, {"error": "unauthorized"})
            return False
        with LOCK:
            f = STATE["fail"]
            if f and f["count"] > 0:
                f["count"] -= 1
                hdr = {"Retry-After": str(f["retry_after"])} if f.get("retry_after") else {}
                self._send(f["status"], {"error": "injected"}, hdr)
                return False
        return True

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/mock/state":
            with LOCK:
                return self._send(200, {k: STATE[k] for k in ("reports", "acks")} |
                                  {"latest_version": STATE["boundaries"][-1]["version"]})
        if not self._gate(u.path):
            return
        if u.path == PREFIX + "/boundary":
            q = parse_qs(u.query)
            have = int(q.get("have", ["0"])[0])
            with LOCK:
                newer = [b for b in STATE["boundaries"] if b["version"] > have]
            if newer:
                return self._send(200, newer[-1])  # the active (latest) one
            return self._send(204)
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        u = urlparse(self.path)
        raw = self._body()
        if u.path == "/mock/boundary":
            v = json.loads(raw or b"{}").get("version")
            with LOCK:
                v = v or STATE["boundaries"][-1]["version"] + 1
                STATE["boundaries"].append(sign.boundary(v))
            return self._send(200, {"staged": v})
        if u.path == "/mock/fail":
            with LOCK:
                STATE["fail"] = json.loads(raw)
            return self._send(200, STATE["fail"])
        if not self._gate(u.path):
            return
        try:
            obj = json.loads(raw)
        except ValueError:
            return self._send(400, {"error": "bad_json"})
        if u.path == PREFIX + "/report":
            with LOCK:
                STATE["reports"].append(obj)
                latest = STATE["boundaries"][-1]["version"]
            return self._send(200, {"latest_version": latest})
        if u.path == PREFIX + "/ack":
            with LOCK:
                STATE["acks"].append(obj)
            return self._send(204)
        self._send(404, {"error": "not_found"})

    def log_message(self, fmt, *a):
        print("mock:", fmt % a, flush=True)


def main():
    global TOKEN
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--token", default=TOKEN)
    ap.add_argument("--tls", nargs=2, metavar=("CERT", "KEY"))
    a = ap.parse_args()
    TOKEN = a.token
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
