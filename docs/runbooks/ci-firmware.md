# CI firmware artifacts (Rook / nRF9151 Connect Kit)

GitHub Actions workflow: `.github/workflows/firmware-build.yml`.

On every pull request or push to `main` that touches `firmware/` (or the
workflow itself), CI runs:

1. `make -C firmware/tests/host`
2. An NCS **v3.4.1** sysbuild of the **main** app (`firmware/build.sh` /
   `prj.conf` only) → `firmware/build/merged.hex`
3. An NCS **v3.4.1** sysbuild of the **Rook LTE** image with
   `EXTRA_CONF_FILE=rook/rook.conf` → `firmware/build-rook/merged.hex`
4. A **mock** Rook LTE compile check
   (`EXTRA_CONF_FILE="rook/rook.conf;rook/rook-mock.conf"`) — build only

Until [PR #12](https://github.com/open-pasture/opencollar/pull/12)
(`rook-lte-v1`) merges, steps 3–4 check out that branch when
`firmware/rook/rook.conf` is missing from the PR head. After #12 lands on
`main`, CI builds LTE from the same checkout as the rest of the job.

## Download the flashable artifacts

1. Open the Actions run (PR checks → **Firmware build** →
   **NCS sysbuild (merged.hex)**).
2. Under **Artifacts** (kept for **14 days**):

| Artifact name | Flash this | Config |
|---|---|---|
| `rook-firmware-BENCH-devkey-nrf9151-connectkit-<sha>` | `merged.hex` | main / `prj.conf` |
| `rook-lte-BENCH-devkey-nrf9151-connectkit-<sha>` | `merged.hex` | Rook LTE (`rook/rook.conf`); expect ~572 KB |

Each archive also has `zephyr.signed.hex`, `dfu_application.zip` (when
produced), the sysbuild log, and for LTE a `BENCH-ONLY-DEV-KEY.txt`
reminder.

## Local Rook LTE build

Inside the NCS toolchain environment, from `firmware/`:

```bash
export ZEPHYR_BASE=$HOME/ncs/v3.4.1/zephyr
# Either (matches CI / op-fw-rook-lte):
west build -p --sysbuild -b nrf9151_connectkit/nrf9151/ns -d build-rook . -- \
  -DBOARD_ROOT=$PWD -DEXTRA_CONF_FILE="rook/rook.conf"
# Or via build.sh:
./build.sh --extra-conf rook/rook.conf --build-dir build-rook
```

Use **`EXTRA_CONF_FILE`**, not `CONF_FILE` (the latter replaces `prj.conf`).
Mock bench server overlay:

```bash
./build.sh --extra-conf 'rook/rook.conf;rook/rook-mock.conf' --build-dir build-rook-mock
```

## Flash it

Follow **[mcuboot-flash.md](mcuboot-flash.md)** (Connect Kit, USB-C,
onboard CMSIS-DAP / pyocd). Quick path once you have `merged.hex`:

```bash
# First flash onto a board without this bootloader layout (erases NVS):
pyocd flash -t nrf91 -f 4000000 -e chip merged.hex

# Later flashes (keeps NVS / provisioning):
pyocd flash -t nrf91 -f 4000000 -e sector merged.hex
```

Or place the hex at `firmware/build/merged.hex` (or `build-rook/`) and use
`./build.sh flash` / `./build.sh flash --erase` (set `BUILD_DIR` /
`--build-dir` for the LTE image).

## Signing key: DEV ONLY (bench artifacts)

CI signs with MCUboot’s **public default ECDSA P-256 key**. That private
half is public — anyone can forge images for boards flashed with it.

Artifact names include **`BENCH-devkey`** on purpose. These workflow
artifacts are **bench-only**. They are **not** field / production builds.
Replace the key (`SB_CONFIG_BOOT_SIGNATURE_KEY_FILE` in
`firmware/sysbuild.conf`) before any field image; see the signing section
in [mcuboot-flash.md](mcuboot-flash.md).
