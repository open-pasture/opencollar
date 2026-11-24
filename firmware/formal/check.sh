#!/usr/bin/env bash
# Model-check Shutoff.tla and FenceGossip.tla, and run the bounded explorer over the
# real cue.c. Each config has an expected result; this fails when any result changes.
#
#   firmware/formal/check.sh
#
# Needs Java 11+ and TLC 1.7.4 (tla2tools.jar). Set TLA2TOOLS to the jar, or install it:
#   mkdir -p ~/.local/share/tla && curl -sSL -o ~/.local/share/tla/tla2tools-1.7.4.jar \
#     https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar
#   sha256: 936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88
# How to read a result: .claude/skills/verify-shutoff-and-gossip/SKILL.md
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
jar=${TLA2TOOLS:-$HOME/.local/share/tla/tla2tools-1.7.4.jar}
[ -f "$jar" ] || { echo "no tla2tools.jar at $jar: see the install lines at the top of $0"; exit 2; }
meta=$(mktemp -d)
trap 'rm -rf "$meta"' EXIT
status=0

# check <spec> <config> <expected: pass | the one invariant that must break>
check() {
  local out got
  out=$(cd "$here" && java -XX:+UseParallelGC -cp "$jar" tlc2.TLC -workers 1 \
    -metadir "$meta/$2" -config "$2.cfg" "$1.tla" 2>&1)
  if grep -q "No error has been found" <<<"$out"; then
    got=pass
  else
    got=$(sed -n 's/^Error: Invariant \([A-Za-z0-9_]*\) is violated.*/\1/p' <<<"$out" | head -1)
    got=${got:-error}
  fi
  if [ "$got" = "$3" ]; then
    echo "ok    $2: $got"
  else
    echo "FAIL  $2: expected $3, got $got"
    echo "$out" | sed -n '/^Error/,/states generated/p' | head -80
    status=1
  fi
}

check Shutoff Shutoff_main pass                  # main, minus finding F1
check Shutoff Shutoff ShutoffSurvivesReboot       # finding F1 on main; pass once #25 lands
check Shutoff Shutoff_pr25 pass                  # main + #25's persistence
check Shutoff Shutoff_pre22 BoundaryKeepsShutoff # can fail: cue_rearm_at before #22
check FenceGossip FenceGossip pass
check FenceGossip FenceGossip_broken HintNeverOutranksManifest # can fail

make -s -C "$here/../tests/host" build/test_cue_explore >/dev/null &&
  "$here/../tests/host/build/test_cue_explore" || status=1
exit "$status"
