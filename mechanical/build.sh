#!/bin/bash
# Build collar parts headless: export STLs, render review images, run checks.
#   ./build.sh            build every part in parts/
#   ./build.sh fit_test   build one part
set -o pipefail
cd "$(dirname "$0")"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
parts="$*"
[ -z "$parts" ] && parts=$(ls parts/*.py | xargs -n1 basename | sed 's/\.py$//')
status=0
for p in $parts; do
  "$BLENDER" --background --factory-startup --python-exit-code 1 --python "parts/$p.py" 2>&1 \
    | grep -vE '^(Blender [0-9]|Read prefs|Fra:|  Time:|$)|Saved: |STL Export|exported successfully' || status=1
done
exit $status
