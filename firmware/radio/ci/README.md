# CI notes for op-firmware

## What this PR changes in `.github/workflows/ci.yml`

Adds one job that runs `make -C firmware/radio/tests/host` on ubuntu-24.04
(no NCS). Flagged for op-firmware review; host tests are owned by op-fw-radio
and are required for the Thu Nov 5 hardware-free handoff.

## Proposed (not enabled): NCS board builds

NCS v3.4.1 is **not** installed in the current GitHub Actions image for this
repo. Enabling board builds needs one of:

1. A self-hosted runner with NCS v3.4.1 + west, or
2. A container image with the Nordic toolchain (large; license/cache), or
3. A later op-firmware workflow that caches `nrfutil sdk-manager` installs.

Draft job text is in `ncs-boards-proposed.yml`. Do not merge that into the
main workflow until the runner can actually build. Local builds:

```bash
firmware/radio/scripts/build_xiao.sh
firmware/radio/scripts/build_nrf9151.sh
```
