#!/usr/bin/env python3
"""Reference decoder for OpenCollar protocol v2 uplink records (draft).

Python standard library only. Decodes one record, or a frame's array of
records, from hex to its JSON view (protocol/v2/messages.md §6), and refuses
CBOR that isn't deterministic, as a conforming reader must.

    python3 opencollar_decode.py 8901...            # one record, or an array of them
    python3 opencollar_decode.py --test ../vectors/v2/records.json

Apache-2.0. A second implementation next to op-protocol's Rust, so the vectors
aren't checked by their own author alone.
"""

import json
import sys

# ---------------------------------------------------------------- deterministic CBOR


class BadCbor(Exception):
    pass


class Tag:
    def __init__(self, tag, value):
        self.tag, self.value = tag, value


def decode(data):
    """One item in deterministic form (RFC 8949 §4.2.1), nothing after it."""
    value, end = _item(data, 0, 0)
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


def _item(data, i, depth):
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
            v, i = _item(data, i, depth + 1)
            items.append(v)
        return items, i
    if major == 5:
        out, last = {}, None
        for _ in range(arg):
            start = i
            k, i = _item(data, i, depth + 1)
            key_bytes = bytes(data[start:i])
            if last is not None and key_bytes <= last:
                raise BadCbor("map keys out of order or repeated")
            last = key_bytes
            v, i = _item(data, i, depth + 1)
            out[k] = v
        return out, i
    if major == 6:
        v, i = _item(data, i, depth + 1)
        return Tag(arg, v), i
    if info in (20, 21, 22):
        return {20: False, 21: True, 22: None}[info], i
    raise BadCbor("simple value")


# ---------------------------------------------------------------- registries (protocol/registry.md)

RECORD_TYPES = {1: "status", 2: "fixes", 3: "cue", 4: "episode", 5: "ack", 6: "health", 7: "device", 8: "slots", 9: "anchor", 10: "firmware"}
MESSAGE_TYPES = {1: "boundary", 2: "config", 3: "membership", 4: "roster", 5: "bind", 6: "handover", 7: "confirm", 8: "owner",
                 9: "firmware", 10: "resend", 11: "release", 64: "factory", 65: "manifest", 66: "batch", 67: "hello"}
FENCE_STATES = {0: "unknown", 1: "inside", 2: "warning", 3: "outside"}
CUE_KINDS = {1: "warn", 2: "outside"}
OUTCOMES = {1: "turned_back", 2: "crossed", 3: "rest", 4: "boundary_changed"}
ACK_STATUSES = {1: "received", 2: "applied", 3: "rejected"}
FIRMWARE_STATES = {0: "idle", 1: "downloading", 2: "staged", 3: "testing", 4: "confirmed", 5: "rolled_back", 6: "refused"}
DEVICE_CLASSES = {1: "node", 2: "anchor", 3: "station", 4: "direct"}
REJECT_CODES = dict(enumerate(
    "bad_sig wrong_herd wrong_collar bad_json too_large stale out_of_range too_few_vertices too_many_vertices too_many_holes "
    "self_intersecting rings_cross hole_outside holes_overlap zero_area hole_too_small hole_too_close bad_margins slots_full "
    "bad_config bad_cbor expired unknown_kid unsupported claimed bad_claim rate_limited not_now bad_image incompatible downgrade".split(), 1))

CELL = {1: "rsrp_dbm", 2: "rsrq_db", 3: "snr_db", 4: "mode", 5: "band", 6: "cell_id", 7: "tac"}
LORA = {1: "rssi_dbm", 2: "snr_db", 3: "beacons", 4: "missed", 5: "frames"}
HEALTH = {1: "fix_attempts", 2: "fix_ok", 3: "sats", 4: "cn0_dbhz", 5: "ttf_ds", 6: "hdop_x10", 7: "battery_mv", 8: "charging",
          9: "temp_dc", 10: "uptime_s", 11: "reset", 12: "still_s", 13: "tilt_deg", 14: ("cell", CELL), 15: ("lora", LORA), 16: "solar_mv"}
ANCHOR = {1: "active", 2: "battery", 3: "rsrp_dbm", 4: "heard", 5: "rank", 6: "queue"}
LIMITS = {1: "outer", 2: "holes", 3: "hole_vertices", 4: "total", 5: "slots", 6: "slot_bytes"}


def name(table, code):
    """A registry value's name; "other" for one this reader doesn't know."""
    return table.get(code, "other")


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


def table_json(m, table):
    out = {}
    for k in sorted(m, key=lambda k: (not isinstance(k, int), k)):
        if not isinstance(k, int) or k < 0:
            continue
        entry = table.get(k)
        if isinstance(entry, tuple) and isinstance(m[k], dict):
            out[entry[0]] = table_json(m[k], entry[1])
        elif entry is not None:
            out[entry if isinstance(entry, str) else entry[0]] = value_json(m[k])
        else:
            out[str(k)] = value_json(m[k])
    return out


def _uint(v, bits=64):
    if not isinstance(v, int) or isinstance(v, bool) or v < 0 or v >= 1 << bits:
        raise BadCbor("not an unsigned integer")
    return v


def _int32(v):
    if not isinstance(v, int) or isinstance(v, bool) or not -(1 << 31) <= v < 1 << 31:
        raise BadCbor("not a 32-bit integer")
    return v


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

    out = {"type": name(RECORD_TYPES, rt), "seq": seq, "t": t}
    if rt == 1:
        out.update(lon=req(0, _int32), lat=req(1, _int32), acc_dm=req(2, lambda v: _uint(v, 32)))
        if isinstance(at(3), int) and at(3) >= 0:
            out["state"] = name(FENCE_STATES, at(3))
        out["bver"] = req(4, lambda v: _uint(v, 32))
        if isinstance(at(5), int) and 0 <= at(5) <= 255:
            out["battery"] = at(5)
        if isinstance(at(6), int):
            out["flags"] = at(6)
    elif rt == 2:
        fix = [t, req(0, _int32), req(1, _int32), req(2, lambda v: _uint(v, 32))]
        fixes = [list(fix)]
        deltas = at(3)
        if not isinstance(deltas, list) or len(deltas) % 4 or not all(isinstance(x, int) for x in deltas):
            raise BadCbor("fix deltas")
        for i in range(0, len(deltas), 4):
            dt, dlon, dlat, acc = deltas[i : i + 4]
            fix = [fix[0] + _uint(dt), _int32(fix[1] + dlon), _int32(fix[2] + dlat), _uint(acc, 32)]
            fixes.append(list(fix))
        out["fixes"] = fixes
    elif rt == 3:
        out.update(kind=name(CUE_KINDS, req(0)), level=req(1, lambda v: _uint(v, 8)), margin_cm=req(2, _int32),
                   ring=req(3, lambda v: _uint(v, 16)), bver=req(4, lambda v: _uint(v, 32)))
        if isinstance(at(5), int):
            out["dur_ms"] = at(5)
    elif rt == 4:
        out.update(dur_s=req(0, lambda v: _uint(v, 32)), bver=req(1, lambda v: _uint(v, 32)), ring=req(2, lambda v: _uint(v, 16)),
                   cues=req(3, lambda v: _uint(v, 32)), max_level=req(4, lambda v: _uint(v, 8)), min_margin_cm=req(5, _int32),
                   outcome=name(OUTCOMES, req(6)))
    elif rt == 5:
        out.update(message_type=name(MESSAGE_TYPES, req(0)), version=req(1, lambda v: _uint(v, 32)), status=name(ACK_STATUSES, req(2)))
        if isinstance(at(3), int):
            out["code"] = name(REJECT_CODES, at(3))
        if isinstance(at(4), bytes) and len(at(4)) == 8:
            out["digest"] = at(4).hex()
    elif rt in (6, 9):
        if not isinstance(at(0), dict):
            raise BadCbor("not a map")
        key = "health" if rt == 6 else "anchor"
        out[key] = table_json(at(0), HEALTH if rt == 6 else ANCHOR)
    elif rt == 7:
        m = at(0)
        if not isinstance(m, dict):
            raise BadCbor("not a map")
        out["device"] = device_json(m)
    elif rt == 8:
        slots = at(0)
        if not isinstance(slots, list):
            raise BadCbor("slots")
        out["slots"] = []
        for s in slots:
            if not isinstance(s, list) or len(s) < 2:
                raise BadCbor("slot")
            e = {"version": _uint(s[0], 32), "status": name(ACK_STATUSES, _uint(s[1]))}
            if len(s) > 2 and isinstance(s[2], int):
                e["effective_at"] = s[2]
            out["slots"].append(e)
    elif rt == 10:
        out["state"] = name(FIRMWARE_STATES, req(0))
        if not isinstance(at(1), str):
            raise BadCbor("version")
        out["version"] = at(1)
        if isinstance(at(2), bytes) and len(at(2)) == 8:
            out["digest"] = at(2).hex()
        if isinstance(at(3), int):
            out["code"] = name(REJECT_CODES, at(3))
    else:
        out["record_type"] = rt
        out["fields"] = [value_json(x) for x in rest]
    return out


def device_json(m):
    out = {}
    kid = lambda k: m[k].hex() if isinstance(m.get(k), bytes) and len(m[k]) == 8 else None
    text = lambda k: m[k] if isinstance(m.get(k), str) else None
    put = lambda k, v: out.__setitem__(k, v) if v is not None else None
    put("class", name(DEVICE_CLASSES, m[1]) if isinstance(m.get(1), int) else None)
    put("fw", text(2))
    put("caps", [c for c in m[3] if isinstance(c, str)] if isinstance(m.get(3), list) and m[3] else None)
    lim = m.get(4)
    if isinstance(lim, dict) and all(isinstance(lim.get(k), int) for k in LIMITS):
        out["limits"] = {LIMITS[k]: lim[k] for k in LIMITS}
    put("hw_rev", text(5))
    put("server_kid", kid(6))
    put("pending_kid", kid(7))
    put("owner_kid", kid(8))
    if isinstance(m.get(9), dict) and m[9]:
        out["versions"] = {name(MESSAGE_TYPES, t): v for t, v in m[9].items() if isinstance(t, int) and isinstance(v, int)}
    put("herd", m[10].hex() if isinstance(m.get(10), bytes) else None)
    put("short", m[11] if isinstance(m.get(11), int) else None)
    put("claim_nonce", kid(12))
    put("boot", text(13))
    put("security_counter", m[14] if isinstance(m.get(14), int) else None)
    if isinstance(m.get(15), list) and m[15]:
        out["image_keys"] = [k.hex() for k in m[15] if isinstance(k, bytes) and len(k) == 8]
    return out


# ---------------------------------------------------------------- command line


def run_vectors(path):
    cases = json.load(open(path))["records"]
    failures = 0
    for c in cases:
        try:
            got, outcome = record_json(decode(bytes.fromhex(c["hex"]))), "ok"
        except BadCbor:
            got, outcome = None, "bad_cbor"
        if outcome != c["expect"] or (got is not None and got != c["json"]):
            failures += 1
            print(f"FAIL {c['name']}: {outcome} {json.dumps(got)}")
    print(f"{len(cases)} records, {failures} failures")
    return failures == 0


def main(argv):
    if len(argv) == 3 and argv[1] == "--test":
        return 0 if run_vectors(argv[2]) else 1
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    v = decode(bytes.fromhex(argv[1]))
    is_frame = isinstance(v, list) and all(isinstance(x, list) for x in v) and v
    print(json.dumps([record_json(r) for r in v] if is_frame else record_json(v), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
