"""Mirror a binary STL across X (for the right-hand pod): mirror_stl.py in.stl out.stl"""
import struct
import sys

src, dst = sys.argv[1], sys.argv[2]
d = open(src, "rb").read()
n = struct.unpack("<I", d[80:84])[0]
out = bytearray(d[:84])
for i in range(n):
    f = list(struct.unpack("<12f", d[84 + i * 50:84 + i * 50 + 48]))
    for k in (0, 3, 6, 9):
        f[k] = -f[k]
    f[6:9], f[9:12] = f[9:12], f[6:9]  # swap two vertices to keep normals outward
    out += struct.pack("<12f", *f) + d[84 + i * 50 + 48:84 + i * 50 + 50]
open(dst, "wb").write(out)
