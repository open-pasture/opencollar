#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build Starling inside the nRF Connect SDK toolchain (same convention as Rook).
#
# Prefer setting ZEPHYR_BASE explicitly. This script only falls back to
# /opt/nordic/ncs/v3.4.1/zephyr when ZEPHYR_BASE is unset.
#
# Verified (NCS v3.4.1, commit c53eb49): 0 warnings;
# FLASH 98336 B / 788 KB (12.19%), RAM 46716 B / 256 KB (17.82%):
#   export PATH=$HOME/.nrfutil/bin:$PATH
#   export ZEPHYR_BASE=$HOME/ncs/v3.4.1/zephyr
#   nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
#     west build -b xiao_ble/nrf52840 firmware/starling \
#     --build-dir /workspace/starling-build -p
#
# Wrapper from this directory:
#   export ZEPHYR_BASE=$HOME/ncs/v3.4.1/zephyr
#   nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh
#   ./build.sh flash
set -euo pipefail
cd "$(dirname "$0")"
BOARD="${BOARD:-xiao_ble/nrf52840}"
if [[ -z "${ZEPHYR_BASE:-}" && -d /opt/nordic/ncs/v3.4.1/zephyr ]]; then
  echo "ZEPHYR_BASE unset; falling back to /opt/nordic/ncs/v3.4.1/zephyr" >&2
  export ZEPHYR_BASE=/opt/nordic/ncs/v3.4.1/zephyr
fi
if [[ -z "${ZEPHYR_BASE:-}" ]]; then
  echo "ZEPHYR_BASE unset and NCS not found under /opt/nordic/ncs/v3.4.1 — cannot west build." >&2
  echo "Set ZEPHYR_BASE explicitly (e.g. \$HOME/ncs/v3.4.1/zephyr). Host tests: make -C tests/host" >&2
  exit 2
fi
west build -b "$BOARD" -d build . -- -DBOARD_ROOT="${BOARD_ROOT:-}"
if [[ "${1:-}" == "flash" ]]; then
  west flash -d build
fi
