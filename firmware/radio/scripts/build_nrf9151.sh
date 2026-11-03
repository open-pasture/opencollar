#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -z "${ZEPHYR_BASE:-}" && -d /opt/nordic/ncs/v3.4.1/zephyr ]]; then
  export ZEPHYR_BASE=/opt/nordic/ncs/v3.4.1/zephyr
fi
exec "$ROOT/ci/build_board.sh" nrf9151
