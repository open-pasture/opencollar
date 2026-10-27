#!/usr/bin/env python3
"""Reference reader for OpenCollar protocol v2 (draft): records, beacons and
LoRa slots.

Python standard library only. Written from the spec, not from op-protocol's
Rust, so the vectors aren't checked by their own author alone. It is as
strict as a conforming receiver must be (protocol/v2/messages.md §1, §6):

- deterministic CBOR only; protocol maps have unsigned integer keys and
  payloads carry no tags;
- a known field that is present must have its type and range, or the record
  is refused (`bad_cbor`); it is never read as absent;
- a value from an open registry that this reader doesn't know is kept as its
  number in the JSON view;
- a frame's records are found by their extents and read one by one, so one
  malformed record costs only itself.

    python3 opencollar_decode.py 8901...              # one record, or a frame's array of them
    python3 opencollar_decode.py --test ../vectors/v2/records.json
    python3 opencollar_decode.py --test-link ../vectors/v2/link.json

Apache-2.0.
"""

import hashlib
import hmac
import json
import sys

# ---------------------------------------------------------------- deterministic CBOR


class BadCbor(Exception):
    pass


class Tag:
    def __init__(self, tag, value):
        self.tag, self.value = tag, value


def decode(data, strict=True):
    """One item in deterministic form (RFC 8949 §4.2.1), nothing after it.

    strict: the protocol profile on top (unsigned integer map keys, no tags).
    """
    value, end = _item(data, 0, 0, strict)
    if end != len(data):
        raise BadCbor("bytes after the item")
    return value


def _head(data, i):
    if i >= len(data):
        raise BadCbor("ends early")
    major, info = data[i] >> 5, data[i] & 0x1F
    i += 1
    if major == 7 and info >= 24:
        raise BadCbor("floats are not used")
    if info < 24:
        return major, info, info, i
    sizes = {24: 1, 25: 2, 26: 4, 27: 8}
    if info not in sizes:
        raise BadCbor("indefinite or reserved length")
    n = sizes[info]
    if i + n > len(data):
        raise BadCbor("ends early")
    arg = int.from_bytes(data[i : i + n], "big")
    if arg < (24 if n == 1 else 1 << (8 * n // 2)):
        raise BadCbor("not the shortest form")
    return major, info, arg, i + n


def _is_uint(v):
    return type(v) is int and v >= 0


def _item(data, i, depth, strict):
    if depth > 16:
        raise BadCbor("nested too deep")
    major, info, arg, i = _head(data, i)
    if major == 0:
        return arg, i
    if major == 1:
        return -1 - arg, i
    if major in (2, 3):
        if i + arg > len(data):
            raise BadCbor("ends early")
        raw = data[i : i + arg]
        if major == 2:
            return bytes(raw), i + arg
        try:
            return raw.decode("utf-8"), i + arg
        except UnicodeDecodeError:
            raise BadCbor("invalid UTF-8")
    if major == 4:
        items = []
        for _ in range(arg):
            v, i = _item(data, i, depth + 1, strict)
            items.append(v)
        return items, i
    if major == 5:
        out, last = {}, None
        for _ in range(arg):
            start = i
            k, i = _item(data, i, depth + 1, strict)
            key_bytes = bytes(data[start:i])
            if last is not None and key_bytes <= last:
                raise BadCbor("map keys out of order or repeated")
            last = key_bytes
            # Python would merge 0 and False, 1 and True: refuse what isn't
            # an unsigned integer key before it can overwrite one.
            if strict and not _is_uint(k):
                raise BadCbor("a map key that isn't an unsigned integer")
            if not strict and (type(k) is bool or not isinstance(k, (int, str, bytes))):
                k = ("key", key_bytes)
            v, i = _item(data, i, depth + 1, strict)
            out[k] = v
        return out, i
    if major == 6:
        if strict:
            raise BadCbor("a tag")
        v, i = _item(data, i, depth + 1, strict)
        return Tag(arg, v), i
    if info in (20, 21, 22):
        return {20: False, 21: True, 22: None}[info], i
    raise BadCbor("simple value")


def item_len(data, i=0, depth=0):
    """Where the well-formed CBOR item at i ends (RFC 8949 §5.3.1), whatever
    profile it breaks. Indefinite lengths and truncation are errors."""
    if depth > 16:
        raise BadCbor("nested too deep")
    if i >= len(data):
        raise BadCbor("ends early")
    major, info = data[i] >> 5, data[i] & 0x1F
    i += 1
    if info < 24:
        n = info
    elif info <= 27:
        w = 1 << (info - 24)
        if i + w > len(data):
            raise BadCbor("ends early")
        n = int.from_bytes(data[i : i + w], "big")
        i += w
    else:
        raise BadCbor("indefinite or reserved")
    if major in (0, 1, 7):
        return i
    if major in (2, 3):
        if i + n > len(data):
            raise BadCbor("ends early")
        return i + n
    if major in (4, 5):
        count = n * (2 if major == 5 else 1)
        if count > len(data) - i:
            raise BadCbor("ends early")
        for _ in range(count):
            i = item_len(data, i, depth + 1)
        return i
    return item_len(data, i, depth + 1)


def split_array(data):
    """The byte ranges of a frame's records: a definite array head, then each
    item by its extent. An item whose extent can't be found ends the list
    with None."""
    if not data or data[0] >> 5 != 4 or data[0] & 0x1F > 27:
        raise BadCbor("not an array")
    info = data[0] & 0x1F
    w = 0 if info < 24 else 1 << (info - 24)
    count = info if info < 24 else int.from_bytes(data[1 : 1 + w], "big")
    i, out = 1 + w, []
    for _ in range(count):
        try:
            end = item_len(data, i)
        except BadCbor:
            out.append(None)
            return out
        out.append(data[i:end])
        i = end
    if i != len(data):
        out.append(None)
    return out


# ---------------------------------------------------------------- registries (protocol/registry.md)

RECORD_TYPES = {1: "status", 2: "fixes", 3: "cue", 4: "episode", 5: "ack", 6: "health", 7: "device", 8: "slots", 9: "anchor", 10: "firmware"}
MESSAGE_TYPES = {1: "boundary", 2: "config", 3: "membership", 4: "roster", 5: "bind", 6: "handover", 7: "confirm", 8: "owner",
                 9: "firmware", 10: "resend", 11: "release", 12: "zones", 13: "lease", 14: "trust",
                 64: "factory", 65: "manifest", 66: "batch", 67: "hello", 68: "trust_update"}
FENCE_STATES = {0: "unknown", 1: "inside", 2: "warning", 3: "outside"}
CUE_KINDS = {1: "warn", 2: "outside"}
OUTCOMES = {1: "turned_back", 2: "crossed", 3: "rest", 4: "boundary_changed"}
ACK_STATUSES = {1: "received", 2: "applied", 3: "rejected"}
FIRMWARE_STATES = {0: "idle", 1: "downloading", 2: "staged", 3: "testing", 4: "confirmed", 5: "rolled_back", 6: "refused"}
DEVICE_CLASSES = {1: "node", 2: "anchor", 3: "station", 4: "direct"}
REJECT_CODES = dict(enumerate(
    "bad_sig wrong_herd wrong_collar bad_json too_large stale out_of_range too_few_vertices too_many_vertices too_many_holes "
    "self_intersecting rings_cross hole_outside holes_overlap zero_area hole_too_small hole_too_close bad_margins slots_full "
    "bad_config bad_cbor expired unknown_kid unsupported claimed bad_claim rate_limited not_now bad_image incompatible downgrade "
    "in_exclusion".split(), 1))

U, I, B, T, P, M = "uint", "int", "bool", "text", "percent", "map"
CELL = {1: ("rsrp_dbm", I), 2: ("rsrq_db", I), 3: ("snr_db", I), 4: ("mode", T), 5: ("band", U), 6: ("cell_id", U), 7: ("tac", U)}
LORA = {1: ("rssi_dbm", I), 2: ("snr_db", I), 3: ("beacons", U), 4: ("missed", U), 5: ("frames", U)}
HEALTH = {1: ("fix_attempts", U), 2: ("fix_ok", U), 3: ("sats", U), 4: ("cn0_dbhz", U), 5: ("ttf_ds", U), 6: ("hdop_x10", U),
          7: ("battery_mv", U), 8: ("charging", B), 9: ("temp_dc", I), 10: ("uptime_s", U), 11: ("reset", T), 12: ("still_s", U),
          13: ("tilt_deg", U), 14: ("cell", CELL), 15: ("lora", LORA), 16: ("solar_mv", U)}
ANCHOR = {1: ("active", B), 2: ("battery", P), 3: ("rsrp_dbm", I), 4: ("heard", U), 5: ("rank", U), 6: ("queue", U)}
LIMITS = {1: "outer", 2: "holes", 3: "hole_vertices", 4: "total", 5: "slots", 6: "slot_bytes"}
MAX_TEXT = 32


def name(table, code):
    """A registry value's name; its number when this reader doesn't know it."""
    return table.get(code, code)


# ---------------------------------------------------------------- JSON view


def value_json(v):
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    if isinstance(v, list):
        return [value_json(x) for x in v]
    if isinstance(v, dict):
        return {(k if isinstance(k, str) else json.dumps(value_json(k))): value_json(x) for k, x in v.items()}
    if isinstance(v, Tag):
        return {"tag": v.tag, "value": value_json(v.value)}
    return v


def _uint(v, bits=64):
    if not _is_uint(v) or v >= 1 << bits:
        raise BadCbor("not an unsigned integer")
    return v


def _int(v, bits=64):
    if type(v) is not int or not -(1 << (bits - 1)) <= v < 1 << (bits - 1):
        raise BadCbor("not an integer")
    return v


def _text(v, most=MAX_TEXT):
    if not isinstance(v, str) or len(v.encode()) > most:
        raise BadCbor("not a short text")
    return v


def _bytes(v, n=None):
    if not isinstance(v, bytes) or (n is not None and len(v) != n):
        raise BadCbor("not the right bytes")
    return v


def _ranged(lo, hi):
    def check(v):
        if not _is_uint(v) or not lo <= v <= hi:
            raise BadCbor("out of range")
        return v
    return check


def _part(v):
    if not isinstance(v, list) or len(v) != 2:
        raise BadCbor("part")
    i, n = _uint(v[0], 8), _uint(v[1], 8)
    if n < 2 or i >= n:
        raise BadCbor("part index past its count")
    return [i, n]


def table_json(m, table):
    """A typed map through its table: known keys checked and named, unknown
    keys kept by number."""
    if not isinstance(m, dict):
        raise BadCbor("not a map")
    out = {}
    for k in sorted(m):
        entry, v = table.get(k), m[k]
        if entry is None:
            out[str(k)] = value_json(v)
            continue
        key, ty = entry
        if isinstance(ty, dict):
            out[key] = table_json(v, ty)
        else:
            {U: _uint, I: _int, T: _text, P: _ranged(0, 100)}.get(ty, lambda x: x)(v)
            if ty == B and not isinstance(v, bool):
                raise BadCbor("not a bool")
            out[key] = value_json(v)
    return out


def record_json(rec):
    """The JSON view of one record (a decoded CBOR array), or BadCbor."""
    if not isinstance(rec, list) or len(rec) < 3:
        raise BadCbor("not a record")
    rt, seq, t = _uint(rec[0]), _uint(rec[1], 32), _uint(rec[2])
    rest = rec[3:]

    def at(k):
        return rest[k] if k < len(rest) and rest[k] is not None else None

    def req(k, conv=_uint):
        if at(k) is None:
            raise BadCbor("missing field")
        return conv(at(k))

    def opt(k, conv):
        return None if at(k) is None else conv(at(k))

    u32 = lambda v: _uint(v, 32)
    i32 = lambda v: _int(v, 32)
    out = {"type": name(RECORD_TYPES, rt), "seq": seq, "t": t}

    def put(key, v):
        if v is not None:
            out[key] = v

    if rt == 1:
        out.update(lon=req(0, i32), lat=req(1, i32), acc_dm=req(2, u32))
        put("state", None if at(3) is None else name(FENCE_STATES, _uint(at(3))))
        out["bver"] = req(4, u32)
        put("battery", opt(5, _ranged(0, 100)))
        put("flags", opt(6, u32))
    elif rt == 2:
        fix = [t, req(0, i32), req(1, i32), req(2, u32)]
        fixes = [list(fix)]
        deltas = at(3)
        if not isinstance(deltas, list) or len(deltas) % 4:
            raise BadCbor("fix deltas")
        for i in range(0, len(deltas), 4):
            dt, dlon, dlat, acc = deltas[i : i + 4]
            fix = [fix[0] + _uint(dt), i32(fix[1] + _int(dlon)), i32(fix[2] + _int(dlat)), u32(acc)]
            fixes.append(list(fix))
        out["fixes"] = fixes
    elif rt == 3:
        out.update(kind=name(CUE_KINDS, req(0)), level=req(1, _ranged(1, 4)), margin_cm=req(2, i32),
                   ring=req(3, lambda v: _uint(v, 16)), bver=req(4, u32))
        put("dur_ms", opt(5, u32))
    elif rt == 4:
        out.update(dur_s=req(0, u32), bver=req(1, u32), ring=req(2, lambda v: _uint(v, 16)),
                   cues=req(3, u32), max_level=req(4, _ranged(0, 4)), min_margin_cm=req(5, i32),
                   outcome=name(OUTCOMES, req(6)))
    elif rt == 5:
        out.update(message_type=name(MESSAGE_TYPES, req(0)), version=req(1, u32), status=name(ACK_STATUSES, req(2)))
        put("code", None if at(3) is None else name(REJECT_CODES, _uint(at(3))))
        put("digest", opt(4, lambda v: _bytes(v, 8).hex()))
    elif rt == 6:
        out["health"] = table_json(at(0), HEALTH)
    elif rt == 9:
        out["anchor"] = table_json(at(0), ANCHOR)
    elif rt == 7:
        out["device"] = device_json(at(0))
    elif rt == 8:
        slots = at(0)
        if not isinstance(slots, list):
            raise BadCbor("slots")
        out["slots"] = []
        for s in slots:
            if not isinstance(s, list) or len(s) < 2:
                raise BadCbor("slot")
            e = {"version": u32(s[0]), "status": name(ACK_STATUSES, _uint(s[1]))}
            if len(s) > 2 and s[2] is not None:
                e["effective_at"] = _uint(s[2])
            out["slots"].append(e)
        put("part", opt(1, _part))
    elif rt == 10:
        out["state"] = name(FIRMWARE_STATES, req(0))
        out["version"] = req(1, _text)
        put("digest", opt(2, lambda v: _bytes(v, 8).hex()))
        put("code", None if at(3) is None else name(REJECT_CODES, _uint(at(3))))
    else:
        out["fields"] = [value_json(x) for x in rest]
    return out


def device_json(m):
    if not isinstance(m, dict):
        raise BadCbor("not a map")
    out = {}

    def put(key, k, conv):
        if k in m:
            out[key] = conv(m[k])

    def texts(v):
        if not isinstance(v, list):
            raise BadCbor("not a list")
        return [_text(c) for c in v]

    def kids(v):
        if not isinstance(v, list):
            raise BadCbor("not a list")
        return [_bytes(k, 8).hex() for k in v]

    def limits(v):
        if not isinstance(v, dict):
            raise BadCbor("limits")
        return {LIMITS[k]: _uint(v[k]) for k in LIMITS}

    def versions(v):
        if not isinstance(v, dict):
            raise BadCbor("versions")
        return {str(name(MESSAGE_TYPES, _uint(t))): _uint(n, 32) for t, n in v.items()}

    def short(v):
        if not _is_uint(v) or not 1 <= v <= 65534:
            raise BadCbor("short")
        return v

    def herd(v):
        if not isinstance(v, bytes) or not 1 <= len(v) <= 16:
            raise BadCbor("herd")
        return v.hex()

    def pair(v):
        if not isinstance(v, list) or len(v) != 2:
            raise BadCbor("pair")
        return [_uint(x, 32) for x in v]

    put("class", 1, lambda v: name(DEVICE_CLASSES, _uint(v)))
    put("fw", 2, _text)
    if 3 in m:
        caps = texts(m[3])
        if caps:
            out["caps"] = caps
    put("limits", 4, limits)
    put("hw_rev", 5, lambda v: _text(v, 16))
    put("server_kid", 6, lambda v: _bytes(v, 8).hex())
    put("pending_kid", 7, lambda v: _bytes(v, 8).hex())
    put("owner_kid", 8, lambda v: _bytes(v, 8).hex())
    if 9 in m and versions(m[9]):
        out["versions"] = versions(m[9])
    put("herd", 10, herd)
    put("short", 11, short)
    put("claim_nonce", 12, lambda v: _bytes(v, 8).hex())
    put("boot", 13, _text)
    put("security_counter", 14, lambda v: _uint(v, 32))
    if 15 in m and kids(m[15]):
        out["image_keys"] = kids(m[15])
    put("part", 16, _part)
    put("device_key", 17, lambda v: _bytes(v, 32).hex())
    if 18 in m:
        plans = m[18]
        if not isinstance(plans, list):
            raise BadCbor("plans")
        if plans:
            out["plans"] = [_uint(p, 32) for p in plans]
    put("zone_limits", 19, pair)
    return out


def read_record(raw):
    """One record's bytes to its JSON view, or BadCbor."""
    return record_json(decode(raw))


def read_frame_plaintext(data):
    """A frame's records, each its JSON view or None when malformed."""
    out = []
    for raw in split_array(data):
        try:
            out.append(None if raw is None else read_record(raw))
        except BadCbor:
            out.append(None)
    return out


# ---------------------------------------------------------------- LoRa (protocol/v2/lora.md)


def beacon_json(frame, keys):
    """A beacon's JSON view if its tag verifies under one of keys, else
    raises BadCbor ("bad_sig" for a tag that doesn't verify)."""
    if len(frame) < 18 or frame[0] != 0x20 or len(frame) > 255:
        raise BadCbor("not a beacon")
    body, tag = frame[:-8], frame[-8:]
    if not any(hmac.compare_digest(hmac.new(k, body, hashlib.sha256).digest()[:8], tag) for k in keys):
        raise BadCbor("bad_sig")
    m = decode(bytes(body[9:]))
    if not isinstance(m, dict):
        raise BadCbor("beacon map")
    out = {"net": int.from_bytes(frame[1:3], "big"), "anchor": int.from_bytes(frame[3:5], "big"),
           "minute": int.from_bytes(frame[5:9], "big"), "bver": None, "pending": [], "msgs": [], "heard": None,
           "state": None, "handon": None, "term": 0}
    if 1 in m:
        out["bver"] = _uint(m[1], 32)
    if 2 in m:
        out["pending"] = [_uint(s, 16) for s in m[2]]
    if 3 in m:
        out["msgs"] = [{"msg": _uint(a[0], 32), "count": _ranged(1, 65535)(a[1]), "dst": _uint(a[2], 16), "type": _uint(a[3])} for a in m[3]]
    if 4 in m:
        out["heard"] = {"first": _uint(m[4][0], 16), "bits": _bytes(m[4][1]).hex()}
    if 5 in m:
        out["state"] = [_ranged(0, 100)(m[5][0]), _ranged(0, 4)(m[5][1]), _uint(m[5][2], 32)]
    if 6 in m:
        out["handon"] = {"short": _ranged(1, 65534)(m[6][0]), "minute": _uint(m[6][1], 32)}
    if 7 in m:
        out["term"] = _ranged(1, (1 << 32) - 1)(m[7])
    return out


SLOTS = 300


def sends(short, minute, cycle, groups, fast):
    """Whether a collar sends in this minute (lora.md §3): slot k of minute m
    is in phase (m − k) mod cycle; phases below groups belong to that group;
    spare phase j (from groups) to group j mod groups, used when fast."""
    k, g = (short - 1) % SLOTS, (short - 1) // SLOTS
    if g >= groups:
        return False
    phase = (minute - k) % cycle
    if phase < groups:
        return phase == g
    return fast and (phase - groups) % groups == g


def run_link(path):
    f = json.load(open(path))
    key = bytes.fromhex(f["beacon_key"])
    failures = 0
    for b in f["beacons"]:
        try:
            got, outcome = beacon_json(bytes.fromhex(b["hex"]), [key]), "ok"
        except BadCbor as e:
            got, outcome = None, "bad_sig" if str(e) == "bad_sig" else "bad_cbor"
        if outcome != b["expect"] or (got is not None and got != b["json"]):
            failures += 1
            print(f"FAIL beacon {b['name']}: {outcome} {json.dumps(got)}")
    for s in f["slots"]:
        if (s["short"] - 1) % SLOTS != s["k"] or (s["short"] - 1) // SLOTS != s["g"]:
            failures += 1
            print(f"FAIL slot {s['short']}: k/g")
        got = [sends(s["short"], m, s["cycle_min"], s["groups"], s["fast"]) for m in s["minutes"]]
        if got != s["sends"]:
            failures += 1
            print(f"FAIL slot {s['short']} cycle {s['cycle_min']} groups {s['groups']} fast {s['fast']}: {got}")
    # No two collars of a full net share a slot, fast or not.
    for cycle, groups in [(5, 1), (5, 2), (5, 5), (15, 4)]:
        for minute in range(cycle):
            used = {}
            for short in range(1, SLOTS * groups + 1):
                if sends(short, minute, cycle, groups, short % 2 == 0):
                    k = (short - 1) % SLOTS
                    if k in used:
                        failures += 1
                        print(f"FAIL collision cycle {cycle} groups {groups} minute {minute}: {used[k]} and {short}")
                    used[k] = short
    n = len(f["beacons"]) + len(f["slots"])
    print(f"{n} beacons and slot cases, {failures} failures")
    return failures == 0


# ---------------------------------------------------------------- command line


def run_vectors(path):
    cases = json.load(open(path))["records"]
    failures = 0
    for c in cases:
        try:
            got, outcome = read_record(bytes.fromhex(c["hex"])), "ok"
        except BadCbor:
            got, outcome = None, "bad_cbor"
        if outcome != c["expect"] or (got is not None and got != c["json"]):
            failures += 1
            print(f"FAIL {c['name']}: {outcome} {json.dumps(got)}")
    # A frame with a malformed record in the middle keeps its neighbours.
    good = [c for c in cases if c["expect"] == "ok"][:2]
    bad = [c for c in cases if c["expect"] == "bad_cbor" and c["name"] != "not_deterministic"][0]
    frame = bytes([0x83]) + bytes.fromhex(good[0]["hex"]) + bytes.fromhex(bad["hex"]) + bytes.fromhex(good[1]["hex"])
    got = read_frame_plaintext(frame)
    if got != [good[0]["json"], None, good[1]["json"]]:
        failures += 1
        print(f"FAIL one malformed record among valid: {json.dumps(got)}")
    print(f"{len(cases)} records, {failures} failures")
    return failures == 0


def main(argv):
    if len(argv) == 3 and argv[1] == "--test":
        return 0 if run_vectors(argv[2]) else 1
    if len(argv) == 3 and argv[1] == "--test-link":
        return 0 if run_link(argv[2]) else 1
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    data = bytes.fromhex(argv[1])
    try:
        print(json.dumps(read_record(data), indent=2))
    except BadCbor:
        print(json.dumps(read_frame_plaintext(data), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
