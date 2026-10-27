#!/usr/bin/env python3
"""Check every v2 test vector against v2/opencollar.cddl with the reference
CDDL tool (the `cddl` Ruby gem: `gem install cddl`).

    python3 conformance/check_cddl.py            # from opencollar/protocol

The CDDL is the sender's schema (shape and ranges). Every vector says what
the schema must make of it in its `schema` field:

- `accept`: the envelope matches `signed` and the payload its type's rule (or
  the record its rule). Cases a collar refuses for state (keys, versions,
  scope, zones) are shape-valid and accepted here;
- `reject`: the schema refuses it (a missing or mistyped field, a value out
  of range, a field a v2.0 sender never sends);
- `skip`: not the schema's question: canonical bytes, a size limit, a tag
  under an extension key. The decoders check those (vectors/README.md).

Documents, batch replies and beacon bodies must all match. Exits non-zero on
any mismatch, and prints how many cases of each verdict ran.
"""

import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "reference"))
from opencollar_decode import BadCbor, Tag, decode  # noqa: E402

COMMANDS = {1: "boundary", 2: "config", 3: "membership", 4: "roster", 5: "bind", 6: "handover", 7: "confirm", 8: "owner",
            9: "firmware-update", 10: "resend", 11: "release", 12: "zones", 13: "lease", 14: "trust"}
DOCUMENTS = {"factory": "factory-record", "manifest": "manifest", "hello": "hello", "trust_update": "trust-update"}
RECORDS = {1: "status", 2: "fixes", 3: "cue", 4: "episode", 5: "ack", 6: "health", 7: "device", 8: "slots",
           9: "anchor-state", 10: "firmware-status"}


def vectors(name):
    with open(os.path.join(ROOT, "vectors", "v2", name)) as f:
        return json.load(f)


def jobs():
    """(group, [(rule, bytes)…], name, want): a group matches when every
    (rule, bytes) in it validates."""
    out = []
    m = vectors("messages.json")
    for c in m["commands"]:
        if c["schema"] == "skip":
            out.append(("skip", [], c["name"], None))
            continue
        b = bytes.fromhex(c["hex"])
        checks = [("signed", b)]
        try:
            env = decode(b, strict=False)
            payload = env.value[2] if isinstance(env, Tag) and isinstance(env.value, list) and len(env.value) == 4 else None
            t = decode(payload, strict=False).get(0) if isinstance(payload, bytes) else None
            checks.append((COMMANDS.get(t, "other-command") if isinstance(t, int) else "command", payload))
        except (BadCbor, AttributeError, TypeError):
            pass
        out.append(("command", checks, c["name"], c["schema"] == "accept"))
    for d in m["documents"]:
        b = bytes.fromhex(d["hex"])
        out.append(("document", [("signed", b), (DOCUMENTS[d["json"]["type"]], decode(b, strict=False).value[2])], d["name"], True))
    for r in vectors("records.json")["records"]:
        if r["schema"] == "skip":
            out.append(("skip", [], r["name"], None))
            continue
        b = bytes.fromhex(r["hex"])
        try:
            t = decode(b, strict=False)[0]
        except (BadCbor, TypeError, IndexError, KeyError):
            t = None
        rule = RECORDS.get(t, "other-record") if isinstance(t, int) else "record"
        out.append(("record", [(rule, b), ("record", b)], r["name"], r["schema"] == "accept"))
    link = vectors("link.json")
    for b in link["batches"]:
        raw = bytes.fromhex(b["hex"])
        out.append(("batch", [("signed", raw), ("batch", decode(raw, strict=False).value[2])], b["name"], True))
        out.append(("reply", [("reply", bytes.fromhex(b["reply"]))], b["name"], True))
    for j in link["joins"]:
        out.append(("reply", [("reply", bytes.fromhex(j["reply"]))], j["name"], True))
        for c in j["collars"]:
            for k in ("bind", "membership"):
                raw = bytes.fromhex(c[k])
                out.append(("command", [("signed", raw), (k, decode(raw, strict=False).value[2])], f"{j['name']} {k}", True))
    for b in link["beacons"]:
        if b["expect"] == "ok":
            out.append(("beacon", [("beacon-body", bytes.fromhex(b["hex"])[9:-8])], b["name"], True))
    # Made up, must fail: a float, a report interval out of range.
    out.append(("record", [("status", bytes.fromhex("8801051a6ab90540" "3a37cd5c3a" "1a190d5d90" "f93e00" "01" "1839"))], "float accuracy", False))
    out.append(("command", [("config", bytes.fromhex("a600020148" + "4845524430303031" + "0248" + "0102030405060708" + "0301" + "0401" + "1005"))], "report_s 5", False))
    return out


def main():
    schema = open(os.path.join(ROOT, "v2", "opencollar.cddl")).read()
    work = tempfile.mkdtemp(prefix="cddl-")
    todo = jobs()
    rules = {rule for _, checks, _, _ in todo for rule, _ in checks}
    for rule in rules:
        with open(os.path.join(work, rule + ".cddl"), "w") as f:
            f.write(f"top = {rule}\n" + schema)
    flat = [(i, rule, data) for i, (_, checks, _, _) in enumerate(todo) for rule, data in checks]

    def run(job):
        i, rule, data = job
        if not isinstance(data, bytes):
            return i, False
        path = os.path.join(work, f"{i}-{rule}.cbor")
        with open(path, "wb") as f:
            f.write(data)
        p = subprocess.run(["cddl", os.path.join(work, rule + ".cddl"), "validate", path], capture_output=True, text=True)
        return i, p.returncode == 0

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(run, flat))
    ok = {}
    for i, passed in results:
        ok[i] = ok.get(i, True) and passed
    bad, kinds = [], Counter()
    for i, (group, checks, name, want) in enumerate(todo):
        if want is None:
            kinds["skipped"] += 1
            continue
        kinds[f"{group} {'accept' if want else 'reject'}"] += 1
        got = ok.get(i, False) and bool(checks)
        if got != want:
            bad.append((group, name, want))
    for group, name, want in bad:
        print(f"FAIL {group} {name}: the schema should {'accept' if want else 'reject'} it")
    print(", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
    print(f"{len(todo)} cases, {len(bad)} failures")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
