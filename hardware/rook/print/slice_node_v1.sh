#!/bin/bash
# Slice node V1 for one collar. Exports already sit on their print face
# (largest flat face at z = 0).
#   ./slice_node_v1.sh       Ender-3 V3 SE, PETG, one plate per part -> gcode/node_v1/
#   ./slice_node_v1.sh p2s   Bambu Lab P2S, ASA, two plates -> gcode/node_v1_p2s/ (.gcode.3mf to send)
set -e
cd "$(dirname "$0")"
O=/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer
E=../stl
if [ "$1" = p2s ]; then P=p2s_asa; G=gcode/node_v1_p2s; else P=ender3v3se_petg; G=gcode/node_v1; fi
python3 flatten_profiles.py ${P/ender3v3se_/} > /dev/null
mkdir -p $G stl/node_v1
python3 mirror_stl.py $E/node_v1_pod/node_pod_base.stl stl/node_v1/node_pod_base_right.stl
python3 mirror_stl.py $E/node_v1_pod/node_pod_lid.stl stl/node_v1/node_pod_lid_right.stl
plate() {
  name=$1; shift
  tmp=$(mktemp -d)
  "$O" --load-settings "$P/machine.json;$P/process.json" \
       --load-filaments $P/filament.json \
       --arrange 1 --orient 0 --slice 0 --outputdir "$tmp" \
       ${P3MF:+--export-3mf "$name.gcode.3mf"} "$@" > /dev/null 2>&1
  if [ -n "$P3MF" ]; then
    # Arrange spills onto extra plates; report each one from the project file.
    mv "$tmp/$name.gcode.3mf" "$G/"
    for pl in $(unzip -Z1 "$G/$name.gcode.3mf" | grep -E 'plate_[0-9]+\.gcode$' | sort); do
      t=$(unzip -p "$G/$name.gcode.3mf" "$pl" | grep -m1 'total estimated time' | sed 's/.*total estimated time: //')
      g=$(unzip -p "$G/$name.gcode.3mf" "$pl" | grep -m1 'filament used \[g\]' | cut -d= -f2)
      echo "$name $(basename $pl .gcode): $t,$g g"
    done
  else
    mv "$tmp/plate_1.gcode" "$G/$name.gcode"
    t=$(grep -m1 'estimated printing time' "$G/$name.gcode" | cut -d= -f2)
    g=$(grep -m1 'total filament used \[g\]' "$G/$name.gcode" | cut -d= -f2)
    echo "$name:$t,$g g"
  fi
  rm -rf "$tmp"
}
bar_cap=$E/node_v1_cap/node_cap_clamp_bar.stl
bar_pod=$E/node_v1_pod/node_pod_clamp_bar.stl
if [ "$1" = p2s ]; then
  P3MF=1
  plate P1_cap_and_counterweight $E/node_v1_cap/node_cap_base.stl $E/node_v1_cap/node_cap_lid.stl \
    $E/node_v1_cw/node_cw_tub.stl $E/node_v1_cw/node_cw_lid.stl $bar_cap $bar_cap
  plate P2_pods $E/node_v1_pod/node_pod_base.stl stl/node_v1/node_pod_base_right.stl \
    $E/node_v1_pod/node_pod_lid.stl stl/node_v1/node_pod_lid_right.stl \
    $bar_pod $bar_pod $bar_pod $bar_pod $E/node_v1_cw/node_cw_clamp_bar.stl $E/node_v1_cw/node_cw_clamp_bar.stl
  exit 0
fi
plate N1_cap_base   $E/node_v1_cap/node_cap_base.stl $bar_cap $bar_cap
plate N2_cap_lid    $E/node_v1_cap/node_cap_lid.stl
plate N3_pod_left   $E/node_v1_pod/node_pod_base.stl $bar_pod $bar_pod
plate N4_pod_right  stl/node_v1/node_pod_base_right.stl $bar_pod $bar_pod
plate N5_pod_lids   $E/node_v1_pod/node_pod_lid.stl stl/node_v1/node_pod_lid_right.stl
plate N6_cw_tub     $E/node_v1_cw/node_cw_tub.stl $E/node_v1_cw/node_cw_clamp_bar.stl $E/node_v1_cw/node_cw_clamp_bar.stl
plate N7_cw_lid     $E/node_v1_cw/node_cw_lid.stl
