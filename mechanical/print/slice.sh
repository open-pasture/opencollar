#!/bin/bash
# Slice the collar for the Ender-3 V3 SE in PLA (quick-look profile).
# Needs OrcaSlicer in /Applications. Run orient.py in Blender first.
set -e
cd "$(dirname "$0")"
O=/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer
python3 flatten_profiles.py > /dev/null
mkdir -p gcode
plate() {
  name=$1; shift
  tmp=$(mktemp -d)
  "$O" --load-settings "ender3v3se/machine.json;ender3v3se/process.json" \
       --load-filaments ender3v3se/filament.json \
       --arrange 1 --orient 0 --slice 0 --outputdir "$tmp" "$@" > /dev/null 2>&1
  mv "$tmp/plate_1.gcode" "gcode/$name.gcode"
  rm -rf "$tmp"
  t=$(grep -m1 'estimated printing time' "gcode/$name.gcode" | cut -d= -f2)
  g=$(grep -m1 'total filament used \[g\]' "gcode/$name.gcode" | cut -d= -f2)
  echo "$name:$t,$g g"
}
plate OC1_top_base stl/top_unit_base.stl stl/top_unit_clamp_bar.stl stl/top_unit_clamp_bar.stl
plate OC2_top_lid stl/top_unit_lid.stl
plate OC3_bay stl/bay_cradle.stl stl/bay_ballast_module.stl
