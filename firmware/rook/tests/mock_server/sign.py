# SPDX-License-Identifier: Apache-2.0
"""Sign v1 boundary commands the way the collar checks them (protocol/README.md
"Signing"): Ed25519 over canonical JSON (keys sorted bytewise, no whitespace,
numbers as serde_json writes them), `sig` left out.

DEV KEY ONLY: the seed is bytes 00..1f, the same as protocol/vectors, so a
collar provisioned with the vectors' public key accepts these. Never use it
on a field collar.
"""
import base64
import json
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

DEV_SEED = bytes(range(32))


def key(seed=DEV_SEED):
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_key_b64(seed=DEV_SEED):
    raw = key(seed).public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode()


def canonical(obj):
    # Python's repr(float) is the shortest round trip, like serde_json, and
    # keeps "5.0" for 5.0. Keys sorted by UTF-8 bytes.
    def enc(v):
        if isinstance(v, dict):
            items = sorted(v.items(), key=lambda kv: kv[0].encode())
            return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + enc(x)
                                  for k, x in items) + "}"
        if isinstance(v, list):
            return "[" + ",".join(enc(x) for x in v) + "]"
        if isinstance(v, float):
            return repr(v)
        return json.dumps(v, ensure_ascii=False)
    return enc(obj).encode()


def sign(cmd, seed=DEV_SEED):
    body = {k: v for k, v in cmd.items() if k != "sig"}
    sig = key(seed).sign(canonical(body))
    out = dict(body)
    out["sig"] = base64.b64encode(sig).decode()
    return out


def boundary(version, herd_id="herd_01J7GOLDEN", collar_id=None, ring=None,
             effective_at=None, seed=DEV_SEED):
    cmd = {
        "command_id": "bnd_rook_%d" % version,
        "herd_id": herd_id,
        "version": version,
        "boundary": ring or [[-92.41, 38.12], [-92.4, 38.12], [-92.4, 38.13], [-92.41, 38.13]],
        "warn_m": 5.0,
        "hysteresis_m": 1.0,
    }
    if collar_id:
        cmd["collar_id"] = collar_id
    if effective_at:
        cmd["effective_at"] = effective_at
    return sign(cmd, seed)


def config(version, collar_id="col_01J9SIMCOLLAR", report_s=60, poll_s=60, herd_id=None,
           endpoint=None, seed=DEV_SEED):
    """A signed config command (protocol/README.md "Config"), as a report reply carries it."""
    cmd = {"command_id": "cfg_rook_%d" % version, "collar_id": collar_id, "version": version,
           "report_s": report_s, "poll_s": poll_s}
    if herd_id:
        cmd["herd_id"] = herd_id
    if endpoint:
        cmd["endpoint"] = endpoint
    return sign(cmd, seed)


if __name__ == "__main__":
    v = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(json.dumps(boundary(v), separators=(",", ":")))
