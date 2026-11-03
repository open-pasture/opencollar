# SPDX-License-Identifier: Apache-2.0
"""Smoke test for the mock server: python3 test_server.py"""
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import server
import sign

srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
AUTH = {"Authorization": "Bearer " + server.TOKEN}


def req(m, p, body=None, h=AUTH):
    c = http.client.HTTPConnection("127.0.0.1", port)
    c.request(m, p, body=json.dumps(body) if body is not None else None, headers=h)
    r = c.getresponse()
    return r.status, r.read()


assert req("GET", "/collar/v1/boundary?have=0", h={})[0] == 401
s, b = req("GET", "/collar/v1/boundary?have=0")
assert s == 200 and json.loads(b)["version"] == 1
assert req("GET", "/collar/v1/boundary?have=1")[0] == 204
s, b = req("POST", "/collar/v1/report", {"boundary_version": 1, "fixes": []})
assert s == 200 and json.loads(b) == {"latest_version": 1}
req("POST", "/mock/boundary", {})
assert json.loads(req("GET", "/collar/v1/boundary?have=1")[1])["version"] == 2
req("POST", "/mock/fail", {"status": 503, "count": 1, "retry_after": 7})
assert req("POST", "/collar/v1/report", {})[0] == 503
assert req("POST", "/collar/v1/ack", {"command_id": "x", "version": 2, "status": "applied"})[0] == 204
assert sign.public_key_b64() == "A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg="
print("mock server: all tests passed")
