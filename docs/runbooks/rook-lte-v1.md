# Rook LTE-M v1 runbook (draft, 2026-11-02)

Owner: op-fw-rook-lte. Code: `firmware/rook/` (branch `rook-lte-v1`). Status: compiles and
host-tested against a mock server; **never run on a live network** (SIM not active yet).

## What it does
- `rook_lte.c` (Zephyr thread): attach LTE-M (APN `hologram`, PSM requested), then every
  `CONFIG_ROOK_LTE_REPORT_S` s: `POST <endpoint>/report`, then `GET <endpoint>/boundary?have=N`.
  A downloaded command goes to the **main thread**, which verifies it with the existing
  Ed25519 path (`app_boundary` → `command_parse`) and stores it as a slot in NVS. The ack is
  `POST <endpoint>/ack`.
- Verified fences with a rising `fence_seq` (v1: the signed `version`) are handed, still as the
  signed bytes, to a LoRa sink registered with `rook_fence_set_sink()` (hook for op-fw-proto's
  `firmware/lora`; nothing in `firmware/lora` is touched).
- Retries per `protocol/v2/http.md` §5/§8: 30 s doubling to 30 min ±25 %, `Retry-After`
  (≤1 h) on 429/503, hourly on 401, drop on 400/403.
- Offline queue: RAM ring of 64 samples (one per 10 s, plus every fence-state change), oldest
  overwritten; `health.dropped` counts losses. **RAM only: lost on reboot** (NVS later).
- Battery: carrier rev A3 MAX17260 (U6, I2C 0x36, 10 mΩ). Off unless
  `CONFIG_ROOK_BATTERY_MAX17260=y`; without it reports omit `battery`.

## Server contract used
The v1 contract in `protocol/README.md` "Endpoints" + "Position report" and the v1 status
rules in `protocol/v2/http.md` §8. Rook **additions** (unknown fields are ignored by v1, but
flag to op-proto/server): top-level `collar_id`; per-fix `fence` (`none|inside|warn|outside`)
and `margin_m`; `health.dropped`. Key `roster` is **reserved** for a Starling freshness
summary (`firmware/rook/src/rook_roster.h`, stub). No v2 names used; `fence_seq` is a local
placeholder name for v1 `version`.

## Build
```
cd firmware
export ZEPHYR_BASE=~/ncs/v3.4.1/zephyr
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  west build -p -b nrf9151_connectkit/nrf9151/ns -d build-rook . -- -DBOARD_ROOT=$PWD \
  -DEXTRA_CONF_FILE="rook/rook.conf"                       # real server
# bench against the mock: -DEXTRA_CONF_FILE="rook/rook.conf;rook/rook-mock.conf"
```
Without `EXTRA_CONF_FILE` the build is unchanged from main (CONFIG_ROOK_LTE off).

Host tests: `make -C firmware/rook/tests/host` (or `firmware/rook/tests/host/run.sh`).

## Mock server
```
cd firmware/rook/tests/mock_server
python3 server.py --port 8080                       # needs: pip install cryptography
python3 server.py --port 8443 --tls cert.pem key.pem
curl -X POST localhost:8080/mock/boundary -d '{}'   # stage the next signed version
curl -X POST localhost:8080/mock/fail -d '{"status":503,"count":2,"retry_after":5}'
curl localhost:8080/mock/state                      # reports and acks received
```
Signed with the **dev key** (seed 00..1f, public key `A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=`,
same as `protocol/vectors`). Provision the bench collar with that `s` and the token
`0123456789abcdef0123456789abcdef`. Samples: `samples/boundary_v{1,2}.json`, `boundary_tampered.json`.
A device on LTE needs a public address for the mock (e.g. a tunnel); set it in `rook-mock.conf`.

## Pointing a real Rook at Hologram (once Cody activates the SIM)
1. Activate the nano SIM in the Hologram dashboard (by ICCID), plan with LTE-M enabled.
2. Insert SIM, flash the `rook.conf` build, provision with the real farm endpoint
   (`https://<farm>/collar/v1`) and server key.
3. Put the server's **CA certificate** in modem sec tag 42 (once, e.g. with the `at_client`
   sample or `nrfutil`/Cellular Monitor: `AT%CMNG=0,42,0,"<PEM>"`). Without it TLS fails
   (peer verify is required).
4. Watch the log, or check by AT (at_client / Cellular Monitor):
   - `AT+CFUN?` → 1; `AT%XSYSTEMMODE?` → `1,0,1,0` (LTE-M + GPS)
   - `AT+CGDCONT?` → `0,"IP","hologram",...`
   - `AT+CEREG?` → `...,1` (home) or `...,5` (roaming; Hologram is usually 5)
   - `AT%XMONITOR` → band, cell, RSRP (want > −110 dBm)
   - `AT+CPSMS?` → whether the network granted PSM
   - `AT+CNEC=24` then retry, for attach reject causes
5. Expect `report: N fixes ... -> 200` and `boundary: ...` in the log.

## Unverified (honest list)
- Anything on air: attach, APN, PSM grant, TLS handshake with the modem, DNS. Not run.
- Coexistence: LTE attach while GNSS is tracking (time-shared on the nRF9151; GNSS fixes will
  pause during LTE activity; PSM/eDRX tuning not done).
- `lte_lc_connect()` blocks the reporter thread up to its timeout; fine but untested.
- MAX17260: register maths host-tested only; the I2C bus label (`i2c2` placeholder) must match
  the carrier overlay, which doesn't exist yet. No gauge config (ModelGauge EZ init) is written,
  so SoC is the gauge's default model until that is added.
- Pending acks from `app.acks` (NVS) are not resent by the reporter yet; only the ack for the
  command just downloaded is posted.
- Config command in the report response (`config`) is not applied yet (cap not advertised).
- 413 split: the next cycle relies on `CONFIG_ROOK_LTE_MAX_FIXES`/body cap, not a real halving.
