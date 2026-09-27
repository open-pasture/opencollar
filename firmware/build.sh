#!/usr/bin/env bash
# Build the firmware inside the nRF Connect SDK toolchain:
#   nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh
#   ./build.sh          build, print the partition map, check image size
#   ./build.sh flash    build and flash over the onboard CMSIS-DAP
set -euo pipefail
cd "$(dirname "$0")"
# Outside the SDK's west workspace, west finds it through ZEPHYR_BASE
if [[ -z "${ZEPHYR_BASE:-}" && -d /opt/nordic/ncs/v3.4.1/zephyr ]]; then
  export ZEPHYR_BASE=/opt/nordic/ncs/v3.4.1/zephyr
fi
west build -b nrf9151_connectkit/nrf9151/ns -d build . -- -DBOARD_ROOT="$PWD"
python3 scripts/check_image.py build/firmware/zephyr
if [[ "${1:-}" == "flash" ]]; then
  west flash -d build
fi
