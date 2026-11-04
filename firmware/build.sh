#!/usr/bin/env bash
# Build the firmware inside the nRF Connect SDK toolchain:
#   nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh
#   ./build.sh
#                       build MCUboot + signed app (prj.conf only), print the
#                       partition map, check image size; flashable image:
#                       build/merged.hex
#   EXTRA_CONF_FILE=rook/rook.conf BUILD_DIR=build-rook ./build.sh
#   ./build.sh --extra-conf rook/rook.conf --build-dir build-rook
#                       same, but layer EXTRA_CONF_FILE on top of prj.conf
#                       (never CONF_FILE — that would replace prj.conf) and
#                       write into BUILD_DIR (default build)
#   ./build.sh flash [--erase]
#                       build and flash $BUILD_DIR/merged.hex over the onboard
#                       CMSIS-DAP (pyocd). Use --erase the first time over a
#                       0.2 (no-bootloader) image.
set -euo pipefail
cd "$(dirname "$0")"
NCS_VERSION="${NCS_VERSION:-v3.4.1}"
BUILD_DIR="${BUILD_DIR:-build}"
EXTRA_CONF_FILE="${EXTRA_CONF_FILE:-}"
do_flash=0
erase=sector

while [[ $# -gt 0 ]]; do
  case "$1" in
    --extra-conf)
      EXTRA_CONF_FILE="${2:?--extra-conf needs a value}"
      shift 2
      ;;
    --build-dir)
      BUILD_DIR="${2:?--build-dir needs a value}"
      shift 2
      ;;
    flash)
      do_flash=1
      shift
      ;;
    --erase)
      erase=chip
      shift
      ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $1 (try --help)" >&2
      exit 2
      ;;
  esac
done

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

cmake_args=(-DBOARD_ROOT="$PWD")
if [[ -n "$EXTRA_CONF_FILE" ]]; then
  cmake_args+=(-DEXTRA_CONF_FILE="$EXTRA_CONF_FILE")
fi
# Pristine when layering an EXTRA_CONF (or BUILD_PRISTINE=1): otherwise a
# previous prj.conf-only tree can leave stale Kconfig values in BUILD_DIR.
pristine_args=()
if [[ -n "$EXTRA_CONF_FILE" || "${BUILD_PRISTINE:-}" == "1" ]]; then
  pristine_args=(-p)
fi

west build "${pristine_args[@]}" --sysbuild -b nrf9151_connectkit/nrf9151/ns \
  -d "$BUILD_DIR" . -- "${cmake_args[@]}"
python3 scripts/check_image.py "$BUILD_DIR/firmware/zephyr"
ls -l "$BUILD_DIR/merged.hex" "$BUILD_DIR/mcuboot/zephyr/zephyr.hex" \
  "$BUILD_DIR/firmware/zephyr/zephyr.signed.bin" \
  "$BUILD_DIR/firmware/zephyr/zephyr.signed.hex"
if [[ "$do_flash" -eq 1 ]]; then
  # One pyocd load of the whole image, so a chip erase (--erase) happens
  # before MCUboot is written, never between MCUboot and the app.
  pyocd flash -t nrf91 -f 4000000 -e "$erase" "$BUILD_DIR/merged.hex"
fi
