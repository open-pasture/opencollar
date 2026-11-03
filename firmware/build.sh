#!/usr/bin/env bash
# Build the firmware inside the nRF Connect SDK toolchain:
#   nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh
#   ./build.sh          build MCUboot + signed app, print the partition map,
#                       check image size; flashable image: build/merged.hex
#   ./build.sh flash [--erase]
#                       build and flash build/merged.hex over the onboard
#                       CMSIS-DAP (pyocd). Use --erase the first time over a
#                       0.2 (no-bootloader) image.
set -euo pipefail
cd "$(dirname "$0")"
NCS_VERSION="${NCS_VERSION:-v3.4.1}"
# Outside the SDK's west workspace, west finds it through ZEPHYR_BASE.
# An existing ZEPHYR_BASE wins; else look in the usual install places.
if [[ -z "${ZEPHYR_BASE:-}" ]]; then
  for d in "$HOME/ncs/$NCS_VERSION" "/opt/nordic/ncs/$NCS_VERSION"; do
    if [[ -d "$d/zephyr" ]]; then export ZEPHYR_BASE="$d/zephyr"; break; fi
  done
fi
if [[ -z "${ZEPHYR_BASE:-}" ]]; then
  echo "NCS $NCS_VERSION not found in ~/ncs or /opt/nordic/ncs; set ZEPHYR_BASE" >&2
  exit 1
fi
west build --sysbuild -b nrf9151_connectkit/nrf9151/ns -d build . -- -DBOARD_ROOT="$PWD"
python3 scripts/check_image.py build/firmware/zephyr
ls -l build/merged.hex build/mcuboot/zephyr/zephyr.hex \
  build/firmware/zephyr/zephyr.signed.bin build/firmware/zephyr/zephyr.signed.hex
if [[ "${1:-}" == "flash" ]]; then
  # One pyocd load of the whole image, so a chip erase (--erase) happens
  # before MCUboot is written, never between MCUboot and the app.
  erase=sector
  [[ "${2:-}" == "--erase" ]] && erase=chip
  pyocd flash -t nrf91 -f 4000000 -e "$erase" build/merged.hex
fi
