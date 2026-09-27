"""Turn a SKiDL/KiCad netlist into a .kicad_pcb with footprints placed on a grid and nets assigned.

Run with KiCad's bundled Python (it has the pcbnew module):
  kicad-python netlist_to_pcb.py build/smoke.net build/smoke.kicad_pcb
Placement here is a starting grid; real placement follows the shell outline.
"""
import os, re, sys
import pcbnew

FP_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

def sexp(text):
    """Minimal S-expression reader for KiCad netlists."""
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop(); stack[-1].append(done)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]

def child(node, key):
    return next((c for c in node[1:] if isinstance(c, list) and c and c[0] == key), None)

def val(node, key):
    c = child(node, key)
    return c[1] if c and len(c) > 1 else ""

def parse(net_text):
    root = sexp(net_text)
    comps = [(val(c, "ref"), val(c, "value"), val(c, "footprint"))
             for c in child(root, "components")[1:] if isinstance(c, list) and c[0] == "comp"]
    nets = []
    for n in child(root, "nets")[1:]:
        if isinstance(n, list) and n[0] == "net":
            nodes = [(val(x, "ref"), val(x, "pin")) for x in n[1:] if isinstance(x, list) and x[0] == "node"]
            nets.append((val(n, "name"), nodes))
    return comps, nets

def main(src, dst):
    comps, nets = parse(open(src).read())
    board = pcbnew.BOARD()
    fps = {}
    for i, (ref, val, fp) in enumerate(comps):
        lib, name = fp.split(":")
        f = pcbnew.FootprintLoad(os.path.join(FP_DIR, lib + ".pretty"), name)
        f.SetReference(ref); f.SetValue(val)
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(10 + 8 * (i % 6)), pcbnew.FromMM(10 + 8 * (i // 6))))
        board.Add(f); fps[ref] = f
    for name, nodes in nets:
        ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni)
        for ref, pin in nodes:
            for pad in fps[ref].Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(ni)
    board.Save(dst)
    print(f"{len(fps)} footprints, {len(nets)} nets -> {dst}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
