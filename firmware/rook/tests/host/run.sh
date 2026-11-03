#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Same as `make -C firmware/rook/tests/host`, for boxes without make.
set -euo pipefail
cd "$(dirname "$0")"
F=../../..
mkdir -p build
CF=(-std=c11 -Wall -Wextra -Werror -O1 -g -ffp-contract=off -D_POSIX_C_SOURCE=200809L
    -D_DEFAULT_SOURCE -I"$F/src" -I../../src -I"$F/third_party/monocypher" -I"$F/tests/host"
    '-DSAMPLES="../mock_server/samples"')
SRCS=()
for m in protocol shape geofence cue command config slots acks provision app; do SRCS+=("$F/src/$m.c"); done
for m in rook_queue rook_backoff rook_report rook_http rook_fence rook_battery_math; do SRCS+=("../../src/$m.c"); done
SRCS+=("$F/third_party/monocypher/monocypher.c" "$F/third_party/monocypher/monocypher-ed25519.c" "$F/tests/host/store_ram.c")
for t in queue backoff report http fence battery; do
  ${CC:-cc} "${CFLAGS_EXTRA[@]+"${CFLAGS_EXTRA[@]}"}" "${CF[@]}" -o "build/test_$t" "test_$t.c" "${SRCS[@]}" -lm
  "./build/test_$t"
done
python3 ../mock_server/test_server.py >/dev/null 2>&1 && echo "mock server: all tests passed"
