#!/bin/bash
# Rebuild shared parts and zip a share package: STLs, renders, .blend, print list.
set -e
cd "$(dirname "$0")"
export OC_PRODUCT_ROOT="$(cd .. && pwd)"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
./build.sh
"$BLENDER" --background --factory-startup --python-exit-code 1 --python assembly/collar.py > /dev/null
name="opencollar-v1-alpha-$(date +%Y-%m-%d)"
out="${1:-../../../../output}/$name"
rm -rf "$out" "$out.zip"
mkdir -p "$out/stl" "$out/renders"
cp ../stl/*/*.stl "$out/stl/"
cp ../renders/collar/*.png "$out/renders/"
for p in fit_test seal_box top_unit bay; do cp "../renders/$p/section_"*.png "$out/renders/${p}_section.png"; done
cp assembly/collar_v1_alpha.blend ../../rook/print/PRINT-LIST.md "$out/"
(cd "$(dirname "$out")" && zip -qr "$name.zip" "$name")
echo "$out.zip"
