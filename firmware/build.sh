#!/usr/bin/env bash
# Build the V0 firmware. Run from anywhere; needs the nRF Connect SDK toolchain.
#   ./build.sh          build
#   ./build.sh flash    build and flash over the onboard CMSIS-DAP
set -euo pipefail
cd "$(dirname "$0")"
west build -b nrf9151_connectkit/nrf9151/ns -d build . -- -DBOARD_ROOT="$PWD"
if [[ "${1:-}" == "flash" ]]; then
  west flash -d build
fi
