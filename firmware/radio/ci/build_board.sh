#!/usr/bin/env bash
# Board build hook for op-firmware's firmware-build.yml (NCS v3.4.1).
#
# Usage (from repo root, with ZEPHYR_BASE / west already set by the caller):
#   firmware/radio/ci/build_board.sh xiao_ble
#   firmware/radio/ci/build_board.sh nrf9151
#   firmware/radio/ci/build_board.sh all
#
# Does not install NCS and does not define a GitHub workflow — that belongs
# to op-firmware. Expects west + ZEPHYR_BASE from the parent job.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FW="$(cd "$ROOT/.." && pwd)"
TARGET="${1:-}"

if [[ -z "${ZEPHYR_BASE:-}" ]]; then
  echo "ZEPHYR_BASE is unset; export it from the NCS toolchain job first" >&2
  exit 1
fi

build_xiao() {
  echo "== radio: xiao_ble/nrf52840 + shield wio_sx1262 =="
  west build -b xiao_ble/nrf52840 -d "$ROOT/build/xiao" \
    "$ROOT/samples/pingpong" -- \
    -DSHIELD=wio_sx1262 \
    -DSHIELD_ROOT="$ROOT" \
    -DBOARD_ROOT="$FW"
}

build_nrf9151() {
  echo "== radio: nrf9151_connectkit/nrf9151/ns + Core1262 overlay (PROPOSED) =="
  west build -b nrf9151_connectkit/nrf9151/ns -d "$ROOT/build/nrf9151" \
    "$ROOT/samples/pingpong" -- \
    -DBOARD_ROOT="$FW" \
    -DEXTRA_DTC_OVERLAY_FILE="$ROOT/boards/nrf9151_connectkit/sx1262_core1262.overlay" \
    -DEXTRA_CONF_FILE="$ROOT/boards/nrf9151_connectkit/sx1262_core1262.conf"
}

case "$TARGET" in
  xiao_ble|xiao)
    build_xiao
    ;;
  nrf9151|rook)
    build_nrf9151
    ;;
  all)
    build_xiao
    build_nrf9151
    ;;
  *)
    echo "usage: $0 {xiao_ble|nrf9151|all}" >&2
    exit 2
    ;;
esac
