#!/usr/bin/env bash
# Build ping/pong for Seeed XIAO nRF52840 + Wio-SX1262 (in-repo shield).
# Board target verified in NCS v3.4.1: xiao_ble/nrf52840
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FW="$(cd "$ROOT/.." && pwd)"
if [[ -z "${ZEPHYR_BASE:-}" && -d /opt/nordic/ncs/v3.4.1/zephyr ]]; then
  export ZEPHYR_BASE=/opt/nordic/ncs/v3.4.1/zephyr
fi
CONF_ARGS=()
if [[ "${1:-}" == "responder" ]]; then
  CONF_ARGS+=(-DCONFIG_RADIO_PINGPONG_INITIATOR=n)
fi
west build -b xiao_ble/nrf52840 -d "$ROOT/build/xiao" \
  "$ROOT/samples/pingpong" -- \
  -DSHIELD=wio_sx1262 \
  -DSHIELD_ROOT="$ROOT" \
  -DBOARD_ROOT="$FW" \
  "${CONF_ARGS[@]}"
echo "Built: $ROOT/build/xiao"
