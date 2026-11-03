#!/usr/bin/env bash
# Build ping/pong for nRF9151 Connect Kit + Core1262-HF (PROPOSED pins).
# Board target: nrf9151_connectkit/nrf9151/ns
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
west build -b nrf9151_connectkit/nrf9151/ns -d "$ROOT/build/nrf9151" \
  "$ROOT/samples/pingpong" -- \
  -DBOARD_ROOT="$FW" \
  -DEXTRA_DTC_OVERLAY_FILE="$ROOT/boards/nrf9151_connectkit/sx1262_core1262.overlay" \
  -DEXTRA_CONF_FILE="$ROOT/boards/nrf9151_connectkit/sx1262_core1262.conf" \
  "${CONF_ARGS[@]}"
echo "Built: $ROOT/build/nrf9151"
