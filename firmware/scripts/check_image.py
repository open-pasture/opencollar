#!/usr/bin/env python3
"""After a build: print the flash partition map, check every edge sits on a
32 KB SPU region boundary, and check the application image and RAM against
protocol v1 §3.1 (image <= 440 KB so an internal-flash MCUboot fits later).

Usage: scripts/check_image.py [build/firmware/zephyr]
"""
import os
import re
import sys

REGION = 32 * 1024
IMAGE_MAX = 440 * 1024
RAM_BASE, RAM_END = 0x20000000, 0x20040000

zdir = sys.argv[1] if len(sys.argv) > 1 else "build/firmware/zephyr"
dts = open(os.path.join(zdir, "zephyr.dts")).read()

# Partitions, with nesting: a child's reg is relative to its parent's ranges base
parts, stack, ok = [], [], True
for line in dts.splitlines():
    s = line.strip()
    m = re.match(r"(\w+): partition@([0-9a-f]+) \{", s)
    if m:
        stack.append({"label": m.group(1), "base": 0, "reg": None, "ranges": None, "depth": len(stack)})
        continue
    if not stack:
        continue
    m = re.match(r"reg = < (0x[0-9a-f]+) (0x[0-9a-f]+) >;", s)
    if m:
        stack[-1]["reg"] = (int(m.group(1), 16), int(m.group(2), 16))
    m = re.match(r"ranges = < 0x0 (0x[0-9a-f]+) (0x[0-9a-f]+) >;", s)
    if m:
        stack[-1]["ranges"] = int(m.group(1), 16)
    if s == "};":
        node = stack.pop()
        parent_base = stack[-1]["ranges"] if stack and stack[-1]["ranges"] is not None else 0
        start = parent_base + node["reg"][0]
        parts.append((start, start + node["reg"][1], node["label"], node["depth"]))

print("Flash partitions:")
for start, end, label, depth in sorted(parts, key=lambda p: (p[0], p[3])):
    aligned = start % REGION == 0 and end % REGION == 0
    ok &= aligned
    print(f"  {'  ' * depth}0x{start:05X}-0x{end:05X}  {(end - start) // 1024:4d} KB  {label}"
          f"{'' if aligned else '  NOT 32 KB-aligned'}")

ns = next(p for p in parts if p[2] == "slot0_ns_partition")
image = os.path.getsize(os.path.join(zdir, "zephyr.bin"))
fits = image <= IMAGE_MAX and image <= ns[1] - ns[0]
ok &= fits
print(f"Application image: {image} B ({image / 1024:.1f} KB) of {IMAGE_MAX // 1024} KB allowed"
      f"{'' if fits else '  TOO LARGE'}")

try:
    from elftools.elf.elffile import ELFFile

    with open(os.path.join(zdir, "zephyr.elf"), "rb") as f:
        elf = ELFFile(f)
        ram = sum(sec["sh_size"] for sec in elf.iter_sections()
                  if sec["sh_flags"] & 0x2 and RAM_BASE <= sec["sh_addr"] < RAM_END)
    print(f"Application RAM (data, bss, noinit, stacks): {ram} B ({ram / 1024:.1f} KB)")
except ImportError:
    print("Application RAM: pyelftools not installed; see the linker's memory report")

sys.exit(0 if ok else 1)
