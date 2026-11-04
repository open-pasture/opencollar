#!/bin/bash
# PLA fit-check job for the Bambu Lab P2S, as a .gcode.3mf for Bambu Connect.
#   ./slice_p2s_pla.sh NAME part.stl [part.stl ...]  -> sliced/p2s_pla/NAME.gcode.3mf
set -e
cd "$(dirname "$0")"
O=/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer
P=p2s_pla; G=sliced/p2s_pla
name=$1; shift
stls=(); for f in "$@"; do stls+=("$(cd "$(dirname "$f")" && pwd)/$(basename "$f")"); done
python3 flatten_profiles.py p2s_pla > /dev/null
mkdir -p $G
tmp=$(mktemp -d)
"$O" --load-settings "$P/machine.json;$P/process.json" --load-filaments $P/filament.json \
     --arrange 1 --orient 0 --slice 0 --outputdir "$tmp" --export-3mf "$name.gcode.3mf" "${stls[@]}" > /dev/null 2>&1
mv "$tmp/$name.gcode.3mf" "$G/"; rm -rf "$tmp"
uv run --quiet fix_bbl_3mf.py "$G/$name.gcode.3mf" N7 "${stls[@]}"
for pl in $(unzip -Z1 "$G/$name.gcode.3mf" | grep -E 'plate_[0-9]+\.gcode$' | sort); do
  t=$(unzip -p "$G/$name.gcode.3mf" "$pl" | grep -m1 'total estimated time' | sed 's/.*total estimated time: //')
  g=$(unzip -p "$G/$name.gcode.3mf" "$pl" | grep -m1 'filament used \[g\]' | cut -d= -f2)
  echo "$name $(basename $pl .gcode): $t,$g g"
done
echo "$(pwd)/$G/$name.gcode.3mf"
