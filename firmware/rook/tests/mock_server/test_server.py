# SPDX-License-Identifier: Apache-2.0
"""Tests for the mock server against the ingest spec: python3 test_server.py"""
import http.client
import json
import threading
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.server import ThreadingHTTPServer

import server
import sign

srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
AUTH = {"Authorization": "Bearer " + server.TOKEN}
assert len(server.TOKEN) == 64


def req(m, p, body=None, h=AUTH):
    c = http.client.HTTPConnection("127.0.0.1", port)
    c.request(m, p, body=json.dumps(body) if body is not None else None, headers=h)
    r = c.getresponse()
    return r.status, r.read(), r


def t(delta=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


fix = {"at": t(), "point": [-92.405, 38.124], "accuracy_m": 1.8, "sats": 9}
dev = {"fw": "0.2.0", "caps": ["holes", "slots", "collar_id", "cue_mode", "config"]}

# Auth
assert req("GET", "/collar/v1/boundary?have=0", h={})[0] == 401
assert req("GET", "/collar/v1/boundary?have=0", h={"Authorization": "Bearer " + "f" * 64})[0] == 401
assert req("POST", "/collar/v1/report", {"collar_id": "col_other"})[0] == 403
assert req("POST", "/collar/v1/ack", {"collar_id": "col_other", "command_id": "x", "version": 1,
                                      "status": "applied", "at": t()})[0] == 403

# Boundary: 200, 204, query recorded, 409 from the gate
s, b, r = req("GET", "/collar/v1/boundary?have=0&free=16&free_bytes=24576")
assert s == 200 and json.loads(b)["version"] == 1
assert parsedate_to_datetime(r.headers["Date"]).tzinfo is not None
assert req("GET", "/collar/v1/boundary?have=1")[0] == 204
req("POST", "/mock/boundary", {})
req("POST", "/mock/gate", {"refuse": True})
assert req("GET", "/collar/v1/boundary?have=1")[0] == 409
req("POST", "/mock/gate", {"refuse": False})
assert json.loads(req("GET", "/collar/v1/boundary?have=1")[1])["version"] == 2

# Report
s, b, _ = req("POST", "/collar/v1/report", {"collar_id": server.COLLAR_ID, "fixes": [fix],
                                            "battery": 0.81, "device": dev,
                                            "slots": [{"version": 1, "status": "applied"}]})
assert s == 200 and json.loads(b) == {"latest_version": 2}, b
st = json.loads(req("GET", "/mock/state")[1])
assert st["legacy"] is False and st["slots"] == [{"version": 1, "status": "applied"}]
assert st["queries"][0] == {"have": 0, "free": 16, "free_bytes": 24576}
assert req("POST", "/collar/v1/report", {"fixes": [{"at": t(), "point": [0, 0]}]})[0] == 400
assert req("POST", "/collar/v1/report", {"fixes": [dict(fix, point=[200, 0])]})[0] == 400
assert req("POST", "/collar/v1/report", {"battery": 3.7})[0] == 400  # volts, not a fraction
assert req("POST", "/collar/v1/report", {"fixes": [dict(fix, at=t(11 * 60))]})[0] == 400
assert req("POST", "/collar/v1/report", {"fixes": [dict(fix, at=t(9 * 60))]})[0] == 200
assert req("POST", "/collar/v1/report", {"fixes": [dict(fix, at="2026-11-02 18:00:00")]})[0] == 400
assert req("POST", "/collar/v1/report", {"device": {"fw": "0.1.0"}})[0] == 200
assert json.loads(req("GET", "/mock/state")[1])["legacy"] is True

# Config rides in the report reply, for a collar with the config cap below its version
req("POST", "/mock/config", {"version": 3, "report_s": 30})
s, b, _ = req("POST", "/collar/v1/report", {"device": dev})
cfg = json.loads(b)["config"]
assert cfg["version"] == 3 and cfg["report_s"] == 30 and "sig" in cfg
assert "config" not in json.loads(req("POST", "/collar/v1/report",
                                      {"device": dict(dev, config_version=3)})[1])
assert "config" not in json.loads(req("POST", "/collar/v1/report",
                                      {"device": {"fw": "0.2.0", "caps": ["slots"]}})[1])

# Ack: 204, and at is required
assert req("POST", "/collar/v1/ack", {"command_id": "x", "version": 2, "status": "applied",
                                      "at": t()})[0] == 204
assert req("POST", "/collar/v1/ack", {"command_id": "x", "version": 2, "status": "applied"})[0] == 400
assert req("POST", "/collar/v1/ack", {"command_id": "x", "version": 2, "status": "done",
                                      "at": t()})[0] == 400

# Failure injection
req("POST", "/mock/fail", {"status": 503, "count": 1, "retry_after": 7})
s, _, r = req("POST", "/collar/v1/report", {})
assert s == 503 and r.headers["Retry-After"] == "7"
assert sign.public_key_b64() == "A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg="
print("mock server: all tests passed")
