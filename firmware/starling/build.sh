#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build Starling inside the nRF Connect SDK toolchain (same convention as Rook):
#   nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh
#   ./build.sh              # board: xiao_ble/nrf52840 (override with BOARD=)
#   ./build.sh flash
set -euo pipefail
cd "$(dirname "$0")"
BOARD="${BOARD:-xiao_ble/nrf52840}"
if [[ -z "${ZEPHYR_BASE:-}" && -d /opt/nordic/ncs/v3.4.1/zephyr ]]; then
  export ZEPHYR_BASE=/opt/nordic/ncs/v3.4.1/zephyr
fi
if [[ -z "${ZEPHYR_BASE:-}" ]]; then
  echo "ZEPHYR_BASE unset and NCS not found under /opt/nordic/ncs/v3.4.1 — cannot west build." >&2
  echo "Host tests: make -C tests/host" >&2
  exit 2
fi
west build -b "$BOARD" -d build . -- -DBOARD_ROOT="${BOARD_ROOT:-}"
if [[ "${1:-}" == "flash" ]]; then
  west flash -d build
fi
