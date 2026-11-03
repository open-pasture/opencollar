# CI hooks for op-firmware

## Host tests (this PR)

`.github/workflows/ci.yml` already has a **Radio host tests** job:

```bash
make -C firmware/radio/tests/host
```

No NCS required. Keep it unless it conflicts with a later unified workflow.

## Board builds (owned by op-firmware)

Do **not** add a radio-owned board-build workflow. Another agent drafts
`.github/workflows/firmware-build.yml` (NCS v3.4.1 via `nrfutil sdk-manager`,
Rook sysbuild, host tests, `ZEPHYR_BASE`). op-firmware will call this hook:

```bash
# After the parent job exports ZEPHYR_BASE / launches the NCS toolchain:
firmware/radio/ci/build_board.sh xiao_ble    # XIAO + wio_sx1262 shield
firmware/radio/ci/build_board.sh nrf9151     # Connect Kit + Core1262 overlay
firmware/radio/ci/build_board.sh all
```

Local equivalent (same scripts as `firmware/radio/scripts/build_*.sh`):

```bash
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/radio/ci/build_board.sh all
```
