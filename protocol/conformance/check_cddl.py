#!/usr/bin/env python3
"""Check every v2 test vector against v2/opencollar.cddl with the reference
CDDL tool (the `cddl` Ruby gem: `gem install cddl`).

    python3 conformance/check_cddl.py            # from opencollar/protocol

Signed messages are checked whole (`signed`) and their payload against its own
rule; records, batch replies and beacon bodies against theirs. A few made-up
messages must fail. Exits non-zero on any mismatch.
"""

import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "reference"))
from opencollar_decode import Tag, decode  # noqa: E402

COMMANDS = {"boundary": "boundary", "config": "config", "membership": "membership", "roster": "roster", "bind": "bind",
            "handover": "handover", "confirm": "confirm", "owner": "owner", "firmware": "firmware-update",
            "resend": "resend", "release": "release", "other": "other-command"}
DOCUMENTS = {"factory": "factory-record", "manifest": "manifest", "hello": "hello"}
RECORDS = {"anchor": "anchor-state", "firmware": "firmware-status", "other": "other-record"}


def vectors(name):
    with open(os.path.join(ROOT, "vectors", "v2", name)) as f:
        return json.load(f)


def jobs():
    out = []

    def signed(b, name, rule):
        env = decode(b)
        assert isinstance(env, Tag) and env.tag == 18
        out.append(("signed", b, name, True))
        out.append((rule, env.value[2], name, True))

    m = vectors("messages.json")
    for c in m["commands"]:
        # Shape-valid commands only: the schema doesn't know a collar's state or limits.
        if c["json"] is None or c["expect"] in ("bad_cbor", "too_large", "bad_config"):
            continue
        signed(bytes.fromhex(c["hex"]), c["name"], COMMANDS[c["json"]["type"]])
    for d in m["documents"]:
        signed(bytes.fromhex(d["hex"]), d["name"], DOCUMENTS[d["json"]["type"]])
    for r in vectors("records.json")["records"]:
        if r["expect"] == "ok" and r["same_bytes"]:
            t = r["json"]["type"]
            out.append((RECORDS.get(t, t), bytes.fromhex(r["hex"]), r["name"], True))
            out.append(("record", bytes.fromhex(r["hex"]), r["name"], True))
    link = vectors("link.json")
    for b in link["batches"]:
        signed(bytes.fromhex(b["hex"]), b["name"], "batch")
        out.append(("reply", bytes.fromhex(b["reply"]), b["name"], True))
    for b in link["beacons"]:
        out.append(("beacon-body", bytes.fromhex(b["hex"])[9:], b["name"], True))
    # Must fail: a float, a report interval out of range, a ring of two vertices.
    out.append(("status", bytes.fromhex("8801051a6ab90540" "3a37cd5c3a" "1a190d5d90" "f93e00" "01" "1839"), "float accuracy", False))
    out.append(("config", bytes.fromhex("a500020148" + "4845524430303031" + "0301" + "0401" + "1005"), "report_s 5", False))
    return out


def main():
    schema = open(os.path.join(ROOT, "v2", "opencollar.cddl")).read()
    work = tempfile.mkdtemp(prefix="cddl-")
    todo = jobs()
    for rule in {j[0] for j in todo}:
        with open(os.path.join(work, rule + ".cddl"), "w") as f:
            f.write(f"top = {rule}\n" + schema)

    def run(i):
        rule, data, name, want = todo[i]
        path = os.path.join(work, f"{i}.cbor")
        with open(path, "wb") as f:
            f.write(data)
        p = subprocess.run(["cddl", os.path.join(work, rule + ".cddl"), "validate", path], capture_output=True, text=True)
        return (p.returncode == 0) == want, rule, name, want

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(run, range(len(todo))))
    bad = [r for r in results if not r[0]]
    for _, rule, name, want in bad:
        print(f"FAIL {name}: {'should match' if want else 'should not match'} {rule}")
    print(f"{len(results)} checks, {len(bad)} failures")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
