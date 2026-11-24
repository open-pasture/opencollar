#!/usr/bin/env bash
# The protocol vectors have three homes, and each check here names its fix.
#
#   scripts/check-vectors.sh          the firmware's copies match protocol/vectors/
#   scripts/check-vectors.sh <base>   also: a change to protocol/vectors/ since <base>
#                                     carries the openpasture pin note
#
# protocol/vectors/ is the source of truth (protocol/vectors/README.md). The firmware
# runs copies in firmware/tests/host/vectors/. openpasture keeps a third copy and its CI
# compares it with the opencollar commit pinned as OPENCOLLAR_REF, so a vector change
# here passes there, silently, until that pin moves. CI runs this same command.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1
status=0
shopt -s nullglob

for f in firmware/tests/host/vectors/*.json; do
  want="protocol/vectors/$(basename "$f")"
  if [ ! -f "$want" ]; then
    echo "::error file=$f::$f has no source $want. Vectors start in protocol/vectors/ (protocol/vectors/README.md); add it there, or delete the firmware copy."
    status=1
  elif ! cmp -s "$f" "$want"; then
    echo "::error file=$f::$f differs from $want, the source of truth. Run: cp $want $f   (to change the vector itself, regenerate it in openpasture: protocol/vectors/README.md)"
    status=1
  fi
done

base=${1:-}
if [ -n "$base" ]; then
  changed=$(git diff --name-only "$base...HEAD" -- 'protocol/vectors/*.json' | sort -u)
  if [ -n "$changed" ] &&
     ! git diff "$base...HEAD" -- protocol/CHANGELOG.md | grep -q '^+.*OPENCOLLAR_REF'; then
    for f in $changed; do
      echo "::error file=$f::$f changed, but protocol/CHANGELOG.md adds no OPENCOLLAR_REF line. openpasture's CI compares its vectors with the opencollar commit pinned as OPENCOLLAR_REF, so it keeps passing on the old ones. Add to this change's CHANGELOG entry: \"- openpasture: copy protocol/vectors/ to crates/op-protocol/vectors/ and set OPENCOLLAR_REF to this PR's merge commit.\" Then open that openpasture PR."
    done
    status=1
  fi
fi
exit "$status"
