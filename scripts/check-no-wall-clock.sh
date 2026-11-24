#!/usr/bin/env bash
# Tests, vectors and the reference tools use fixed dates (2026-09-27T12:00:00Z, the
# vectors' `now`). Those never age out only while nothing compares them with the real
# date, so the collar logic, its host tests and the protocol tools take time as an
# input and never read the wall clock. A monotonic clock for timing a benchmark is fine.
#
#   scripts/check-no-wall-clock.sh
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

pattern='\btime\((NULL|0|nullptr)\)|CLOCK_REALTIME|\bgettimeofday\b|\b(datetime|date)\.(now|utcnow|today)\b|\btime\.(time|time_ns|gmtime|localtime)\(\)'
hits=$(git grep -nE "$pattern" -- \
  'firmware/src/*' \
  'firmware/tests/host/*' 'protocol/*.py')
if [ -n "$hits" ]; then
  while IFS= read -r h; do
    echo "::error file=${h%%:*}::${h} reads the wall clock. Take the time as a parameter (the vector's \`now\`, the fix's GNSS time) so fixed test dates never age out: scripts/check-no-wall-clock.sh"
  done <<< "$hits"
  exit 1
fi
