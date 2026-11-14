# /// script
# dependencies = ["numpy", "matplotlib"]
# ///
"""Patch what OrcaSlicer's CLI leaves out of a .gcode.3mf so Bambu Connect
accepts it. Without an OpenGL context the CLI writes no plate thumbnails,
and Bambu Connect's import fails on the missing `thumbnail_file`. It also
leaves the printer model ID blank and the first-layer time as garbage.

    uv run fix_bbl_3mf.py job.gcode.3mf N7 part.stl [part.stl ...]   # N7 = Bambu Lab P2S
"""
import io, re, shutil, struct, sys, tempfile, zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection

path, model, stls = sys.argv[1], sys.argv[2], sys.argv[3:]


def read_stl(p):
    data = open(p, "rb").read()
    n = struct.unpack_from("<I", data, 80)[0]
    if len(data) == 84 + 50 * n:
        a = np.frombuffer(data, dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]), count=n, offset=84)
        return a["v"].reshape(-1, 3, 3).astype(float)
    v = [list(map(float, l.split()[1:4])) for l in data.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
    return np.array(v).reshape(-1, 3, 3)


def render(size, top=False):
    # Parts side by side, viewed from above (top) or at an angle, Lambert-shaded.
    tris, x0 = [], 0.0
    for p in stls:
        t = read_stl(p)
        t = t - t.reshape(-1, 3).min(0)
        t[:, :, 0] += x0
        x0 = t[:, :, 0].max() + 10
        tris.append(t)
    t = np.concatenate(tris)
    rz, rx = (0.0, 0.0) if top else (np.radians(-35), np.radians(-55))
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    v = t @ (Rx @ Rz).T
    nrm = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    keep = nrm[:, 2] > 0
    v, nrm = v[keep], nrm[keep]
    order = np.argsort(v[:, :, 2].mean(1))
    light = np.array([-0.3, 0.4, 0.87]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(nrm @ light, 0, 1)
    base = np.array([0.95, 0.46, 0.31])
    fig = plt.figure(figsize=(1, 1), dpi=size)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.add_collection(PolyCollection(v[order][:, :, :2], facecolors=base * shade[order][:, None], edgecolors="none"))
    lo, hi = v[:, :, :2].reshape(-1, 2).min(0), v[:, :, :2].reshape(-1, 2).max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2 * 1.1
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_aspect("equal")
    buf = io.BytesIO(); fig.savefig(buf, format="png", transparent=True); plt.close(fig)
    return buf.getvalue()


big, small, top = render(512), render(128), render(512, top=True)
pngs = {"Metadata/plate_1.png": big, "Metadata/plate_no_light_1.png": big,
        "Metadata/plate_1_small.png": small, "Metadata/top_1.png": top, "Metadata/pick_1.png": top}
thumbs = ('    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>\n'
          '    <metadata key="thumbnail_no_light_file" value="Metadata/plate_no_light_1.png"/>\n'
          '    <metadata key="top_file" value="Metadata/top_1.png"/>\n'
          '    <metadata key="pick_file" value="Metadata/pick_1.png"/>\n')

tmp = tempfile.mktemp(suffix=".3mf")
with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    names = zin.namelist()
    for item in zin.infolist():
        if item.filename in pngs:
            continue
        data = zin.read(item.filename)
        if item.filename == "Metadata/slice_info.config":
            s = data.decode()
            s = s.replace('key="printer_model_id" value=""', f'key="printer_model_id" value="{model}"')
            s = re.sub(r'key="first_layer_time" value="[^"]*"', 'key="first_layer_time" value="0"', s)
            data = s.encode()
        if item.filename == "Metadata/model_settings.config" and b"thumbnail_file" not in data:
            s = data.decode()
            s = s.replace('    <metadata key="gcode_file" value="Metadata/plate_1.gcode"/>\n',
                          '    <metadata key="gcode_file" value="Metadata/plate_1.gcode"/>\n' + thumbs)
            data = s.encode()
        if item.filename == "[Content_Types].xml" and b'Extension="png"' not in data:
            data = data.replace(b"</Types>", b' <Default Extension="png" ContentType="image/png"/>\n</Types>')
        zout.writestr(item, data)
    for name, png in pngs.items():
        zout.writestr(name, png)
shutil.move(tmp, path)
