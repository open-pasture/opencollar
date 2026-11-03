# CI firmware artifacts (Rook / nRF9151 Connect Kit)

GitHub Actions workflow: `.github/workflows/firmware-build.yml`.

On every pull request or push to `main` that touches `firmware/` (or the
workflow itself), CI runs:

1. `make -C firmware/tests/host`
2. An NCS **v3.4.1** sysbuild of the Rook app (`firmware/build.sh`), which
   produces the MCUboot + signed TF-M/app image.

## Download the flashable artifact

1. Open the Actions run for the commit (PR checks → **Firmware build** →
   **NCS sysbuild (merged.hex)**).
2. Under **Artifacts**, download
   `rook-firmware-nrf9151-connectkit-<sha>` (kept for **14 days**).
3. Unpack it. The flashable file is **`merged.hex`**.

Also included:

| file | use |
|---|---|
| `merged.hex` | Full image: MCUboot @0x0 + signed app @0x10000 — **flash this** |
| `zephyr.signed.hex` | Signed TF-M + app only (slot0) |
| `dfu_application.zip` | DFU package (for later FOTA use) |
| `sysbuild.log` | Full west/sysbuild log from CI |

## Flash it

Follow **[mcuboot-flash.md](mcuboot-flash.md)** (Connect Kit, USB-C,
onboard CMSIS-DAP / pyocd). Quick path once you have `merged.hex`:

```bash
# First flash onto a board without this bootloader layout (erases NVS):
pyocd flash -t nrf91 -f 4000000 -e chip merged.hex

# Later flashes (keeps NVS / provisioning):
pyocd flash -t nrf91 -f 4000000 -e sector merged.hex
```

Or place `merged.hex` at `firmware/build/merged.hex` after a local
`./build.sh` and use `./build.sh flash` / `./build.sh flash --erase` as
described in the MCUboot runbook.

## Signing key: DEV ONLY (bench artifacts)

CI signs with MCUboot’s **public default ECDSA P-256 key**. That private
half is public — anyone can forge images for boards flashed with it.

These workflow artifacts are **bench-only**. They are **not** field /
production builds. Replace the key (`SB_CONFIG_BOOT_SIGNATURE_KEY_FILE` in
`firmware/sysbuild.conf`) before any field image; see the signing section
in [mcuboot-flash.md](mcuboot-flash.md).
