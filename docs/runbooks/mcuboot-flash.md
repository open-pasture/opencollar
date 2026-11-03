# OpenCollar firmware: MCUboot + merged.hex runbook (branch firmware/mcuboot-merged-hex)

## Build
    cd opencollar/firmware
    nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- ./build.sh
build.sh uses an existing ZEPHYR_BASE, or else finds NCS in ~/ncs/v3.4.1 or /opt/nordic/ncs/v3.4.1
(set NCS_VERSION to use a different version). Clean build takes about 25 s. It prints the partition map and the size check.

## Outputs (build of 2026-11-02, 18:14 CST)
| file | size | what |
|---|---|---|
| build/merged.hex | 493,056 B | **flash this**: MCUboot @0x0 + signed TF-M/app @0x10000 |
| build/mcuboot/zephyr/zephyr.hex | 86,938 B | MCUboot alone (0x0-0x7898) |
| build/firmware/zephyr/zephyr.signed.hex | 408,144 B | signed TF-M + app (slot0, 0x10000-0x343A7) |
| build/firmware/zephyr/zephyr.signed.bin | 148,390 B | the same image as a bin (for later DFU/FOTA) |
| build/dfu_application.zip | 149,147 B | DFU package (for later use) |
| build/firmware/zephyr/zephyr.bin | 115,472 B | unsigned app (size checked: 112.8 KB of 416 KB) |

Flash map: MCUboot 64K @0x0 | slot0 448K @0x10000 (TF-M 32K, app 416K) | slot1 448K @0x80000 | storage (NVS) 64K @0xF0000 (unchanged from 0.2).

## Flash (Connect Kit, USB-C data cable, onboard CMSIS-DAP; no J-Link needed)
- **First time** on a board that has 0.2 (no bootloader) or an unknown image: `./build.sh flash --erase`
  (pyocd chip erase, then writes merged.hex). This also erases NVS, so provisioning, config and boundary slots are lost.
  Provision again over the console (115200 baud) afterwards.
- After that: `./build.sh flash` (sector erase; NVS is kept).
- Without build.sh: `pyocd flash -t nrf91 -f 4000000 -e chip build/merged.hex`.
  `west flash -d build` also works: it writes MCUboot and then the signed image as two steps. Don't add `--erase` to it.
- UF2/drag-and-drop: the board's UF2 runner targets the nRF52820 IFMCU (its own firmware). Whether its USB drive accepts an
  nRF9151 .hex is **not verified**, so use pyocd.
- Linux: if pyocd reports no probe or permission denied, add a udev rule for the CMSIS-DAP (e.g. pyocd's
  `50-cmsis-dap.rules` in /etc/udev/rules.d), then run `sudo udevadm control --reload && sudo udevadm trigger` and replug.
- Check: the console should show the MCUboot banner ("Starting bootloader" / "Jumping to the first image slot"), then the app.

## Signing key: DEV ONLY
Images are signed with MCUboot's public default key (`~/ncs/v3.4.1/bootloader/mcuboot/root-ec-p256.pem`). Its private
half is public, so anyone can sign images for these boards. This is fine for bench builds. Before any field build, generate a project
key, keep it outside the repo, and set `SB_CONFIG_BOOT_SIGNATURE_KEY_FILE` in sysbuild.conf (MCUboot is frozen at
manufacture, so this is a one-way decision). There are no private keys in the repo.
