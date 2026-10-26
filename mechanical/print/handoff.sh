#!/bin/bash
# Zip the print-lab hand-off: README, the parts sheet and the print-oriented
# STLs. Re-orients and re-renders from exports/ first.
set -e
cd "$(dirname "$0")"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
"$BLENDER" -b --factory-startup --python orient.py > /dev/null
"$BLENDER" -b --factory-startup --python bed_views.py > /dev/null
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
  --force-device-scale-factor=1 --window-size=1000,1712 \
  --screenshot="$PWD/handoff/what-to-print.png" "file://$PWD/handoff/sheet.html" 2> /dev/null
name=opencollar-print-job
out="${1:-../../../output}/$name"
rm -rf "$out" "$out.zip"
mkdir -p "$out/stl"
cp handoff/README.md handoff/what-to-print.png "$out/"
cp stl/*.stl "$out/stl/"
(cd "$(dirname "$out")" && zip -qrX "$name.zip" "$name" -x '*/.DS_Store')
echo "$out.zip"
