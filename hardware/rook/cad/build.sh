#!/bin/bash
# Build Rook (Node V1) parts headless: export STLs, render, run checks.
#   ./build.sh                 build every part in parts/ (gable cap default)
#   ./build.sh node_v1         build one part script
#   OC_CAP_STYLE=saddle ./build.sh node_v1
#   ./build.sh node_v1 -- cap saddle
# Extra args after the part name are forwarded after Blender's `--`.
set -o pipefail
cd "$(dirname "$0")"
export OC_PRODUCT_ROOT="$(cd .. && pwd)"
# Shared helpers (oc, dims) live in hardware/common/cad/lib.
export PYTHONPATH="$(cd ../../common/cad/lib && pwd)${PYTHONPATH:+:$PYTHONPATH}"
if [ -z "${BLENDER:-}" ]; then
  if [ -x /Applications/Blender.app/Contents/MacOS/Blender ]; then
    BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
  else
    BLENDER=blender
  fi
fi
# Split script names from forwarded args at `--`.
parts=()
forward=()
seen_dd=0
for a in "$@"; do
  if [ "$a" = "--" ]; then
    seen_dd=1
    continue
  fi
  if [ "$seen_dd" -eq 1 ]; then
    forward+=("$a")
  else
    parts+=("$a")
  fi
done
if [ ${#parts[@]} -eq 0 ]; then
  parts=($(ls parts/*.py | xargs -n1 basename | sed 's/\.py$//'))
fi
status=0
for p in "${parts[@]}"; do
  if [ ${#forward[@]} -gt 0 ]; then
    "$BLENDER" --background --factory-startup --python-exit-code 1 --python "parts/$p.py" -- "${forward[@]}" 2>&1 \
      | grep -vE '^(Blender [0-9]|Read prefs|Fra:|  Time:|$)|Saved: |STL Export|exported successfully' || status=1
  else
    "$BLENDER" --background --factory-startup --python-exit-code 1 --python "parts/$p.py" 2>&1 \
      | grep -vE '^(Blender [0-9]|Read prefs|Fra:|  Time:|$)|Saved: |STL Export|exported successfully' || status=1
  fi
done
exit $status
