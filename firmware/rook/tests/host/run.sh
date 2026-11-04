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
for m in rook_queue rook_backoff rook_report rook_http rook_fence rook_state rook_ca rook_battery_math; do SRCS+=("../../src/$m.c"); done
SRCS+=("$F/third_party/monocypher/monocypher.c" "$F/third_party/monocypher/monocypher-ed25519.c" "$F/tests/host/store_ram.c")
for t in queue backoff report http fence battery state acks ca; do
  ${CC:-cc} "${CFLAGS_EXTRA[@]+"${CFLAGS_EXTRA[@]}"}" "${CF[@]}" -o "build/test_$t" "test_$t.c" "${SRCS[@]}" -lm
  "./build/test_$t"
done
python3 ../mock_server/test_server.py >/dev/null 2>&1 && echo "mock server: all tests passed"
# The firmware's encoders against the running mock server
${CC:-cc} "${CF[@]}" -o build/test_live test_live.c "${SRCS[@]}" -lm
PORT=$((20000 + RANDOM % 20000))
(cd ../mock_server && exec python3 server.py --host 127.0.0.1 --port $PORT >/dev/null 2>&1) &
SRV=$!
trap 'kill $SRV 2>/dev/null' EXIT
for _ in $(seq 50); do (exec 3<>/dev/tcp/127.0.0.1/$PORT) 2>/dev/null && break; sleep 0.1; done
./build/test_live "http://127.0.0.1:$PORT/collar/v1"
