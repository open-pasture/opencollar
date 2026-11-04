# Rook LTE-M v1 runbook (draft, 2026-11-02)

Owner: op-fw-rook-lte. Code: `firmware/rook/` (branch `rook-lte-v1`). Status: compiles and
host-tested against a mock server; **never run on a live network** (SIM not active yet).

## What it does
- `rook_lte.c` (Zephyr thread): attach LTE-M (APN `hologram`, PSM requested), then every
  `CONFIG_ROOK_LTE_REPORT_S` s: `POST <endpoint>/report`, then `GET <endpoint>/boundary?have=N`.
  A downloaded command goes to the **main thread**, which verifies it with the existing
  Ed25519 path (`app_boundary` → `command_parse`) and stores it as a slot in NVS. The ack is
  `POST <endpoint>/ack`.
- Verified fences with a rising `fence_seq` (v1: the signed `version`) are persisted and handed,
  still as the signed bytes, to a LoRa sink registered with `rook_fence_set_sink()` (see
  "Fence sink and persistence" below; nothing in `firmware/lora` is touched).
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

### Checked against the real ingest (openpasture `crates/op-ingest/src/device.rs`, 2026-11-03)
- Auth `Authorization: Bearer <64-hex key>`; 401 missing/unknown key, 403 when the body
  `collar_id` isn't the key's (report and ack). The Rook sends its provisioned `collar_id`.
- Report: `accuracy_m` in every fix; `battery` a 0..1 fraction (volts only in
  `health.battery_v`); times RFC 3339 UTC `...Z`. Any fix more than **10 min ahead** of the
  server clock is a 400 for the whole report (and a 400 drops the batch), so the Rook keeps the
  server's clock from each response's `Date` and leaves out fixes > 9 min ahead of it, plus any
  fix stamped before 2024 (GNSS time not set). They count in `health.dropped`.
- `device` is always sent: `fw`, `caps` `holes slots collar_id cue_mode config` (no caps means
  LEGACY limits), `limits` (from the core's slot store), `config_version`, `config_reject` once;
  plus the full `slots` list. The reply's `config` is applied by the core (`app_config`) on the
  main thread; its `endpoint` and `report_s` are used from the next cycle (the endpoint trial
  and 24 h fallback are the core's `config_report_result`).
- `GET /boundary?have=&free=&free_bytes=` from the slot store; 200 command, 204 nothing new,
  **409 = the server's safety gate refuses it**: treated as nothing new (no backoff).
- Ack: `at` is required by the server; the ack's GNSS time, else the server `Date`, else
  `1970-01-01T00:00:00Z`. 204 on success.
- Provisioning `e` = `https://<host>/collar/v1`: the Rook appends `/report`, `/boundary`,
  `/ack` (a trailing `/` is dropped). Port 443 unless given.
- TLS to the Cloudflare tunnel hostname: SNI and hostname check use the `e` host; the CA in
  sec tag 42 must be the root that signs **Cloudflare's edge certificate** for that hostname
  (not the origin, which is plain http on 7878 behind the tunnel). Chunked responses (a proxy
  may re-chunk) are decoded.

## Fence sink and persistence
- Sink signature (unchanged): `void sink(void *ctx, uint32_t fence_seq, const char *signed_wire,
  size_t len)`. `signed_wire`/`len` is the v1 signed JSON boundary command exactly as the server
  sent it, as **opaque bytes** (not re-encoded, not NUL-terminated by contract). `fence_seq` is
  the v1 `version` of that command.
- op-fw-proto's `inject_local` takes these bytes as an opaque payload; it should not parse them.
- Receivers (collars, Starlings) verify the Ed25519 signature themselves with the provisioned
  server key, as they do for any boundary command. The Rook is only a relay: **it holds no
  signing key** and cannot mint or alter fences (any change breaks the signature).
- Persistence (`firmware/src/store.h`): `STORE_ID_ROOK_FENCE` (4) holds a header (magic, fence_seq,
  len, crc32, active bank, bound herd + server key); the signed bytes go in 1 KB chunks at
  `STORE_ID_ROOK_FENCE_BASE + bank*16 + i` (two A/B banks; new bank written first, header last,
  so a power cut leaves the old fence intact). `rook_fence_init()` restores the high-water mark
  and active fence at boot; a download with `version <= hwm` is rejected as stale before
  verification. Re-provisioning to another herd/server key resets the record.
- Host test `test_fence` simulates reboot: older fence_seq rejected, active fence restored,
  power cut mid-write survives.

## Proposed additions to v1 report (for op-software to accept)
v1 servers ignore unknown fields, so these are backward compatible; none are v2 names.
- `collar_id` (top level, string): already accepted by the real ingest (optional, 403 on a
  mismatch with the key), so this one needs no change.
- `fence` (per fix, `none|inside|warn|outside`): fence state at that fix.
- `margin_m` (per fix, number): signed distance to the boundary in metres (negative = outside).
- `health.dropped` (integer): samples lost from the offline queue since boot.
- `roster` (top level, **reserved**): future Starling freshness summary; currently never sent.
  Servers should ignore it until it is specified.

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
python3 server.py --port 7878                       # needs: pip install cryptography
python3 server.py --port 8443 --tls cert.pem key.pem
curl -X POST localhost:7878/mock/boundary -d '{}'   # stage the next signed version
curl -X POST localhost:7878/mock/fail -d '{"status":503,"count":2,"retry_after":5}'
curl -X POST localhost:7878/mock/gate -d '{"refuse":true}'   # boundary -> 409
curl -X POST localhost:7878/mock/config -d '{"version":3,"report_s":30}'  # signed config in replies
curl localhost:7878/mock/state                      # reports, acks, queries, legacy, slots
```
Signed with the **dev key** (seed 00..1f, public key `A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=`,
same as `protocol/vectors`). Provision the bench collar with that `s`, collar id
`col_01J9SIMCOLLAR` and the key `0123456789abcdef` ×4 (64 hex). It mirrors the real ingest's
checks (bearer 401, collar 403, accuracy_m, battery 0..1, 10-min-ahead 400, ack `at`, LEGACY
without caps). `tests/host/run.sh` also runs `test_live`: the firmware encoders against it. Samples: `samples/boundary_v{1,2}.json`, `boundary_tampered.json`.
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

## Battery for the first report
- `CONFIG_ROOK_BATTERY_MAX17260` is off by default and the **bare Connect Kit has no fuel gauge
  and no battery divider**, so reports omit `battery` (the app shows no battery; position still
  shows). Nothing is faked.
- With the carrier rev A3: `CONFIG_ROOK_BATTERY_MAX17260=y` plus a carrier devicetree overlay
  naming its I2C bus (missing: the overlay and the bus label; `i2c2` is a placeholder).
- Proposed fallback without the carrier: a VBAT divider into one nRF9151 AIN pin read by the
  Zephyr ADC (`zephyr,user` `io-channels`) and a LiPo voltage-to-fraction curve. Missing: the
  divider (two resistors and the pin, hardware), the overlay, and a curve. Not implemented.
  The modem's `%XVBAT` is the regulated supply, not the battery: not used.

## Shortest path to a first report in the app
1. Activate the SIM (Cody). 2. Put the root CA for the tunnel hostname's Cloudflare edge
certificate in sec tag 42. 3. Provision over serial 115200 with the server's `provision {...}`
line. 4. Flash the `rook.conf` build (MAX17260 on only with the carrier). 5. First GNSS fix,
then the next cycle posts it; the server's `Date` arrives on that first response.

## Unverified (honest list)
- Anything on air: attach, APN, PSM grant, TLS handshake with the modem, DNS. Not run.
- Coexistence: LTE attach while GNSS is tracking (time-shared on the nRF9151; GNSS fixes will
  pause during LTE activity; PSM/eDRX tuning not done).
- `lte_lc_connect()` blocks the reporter thread up to its timeout; fine but untested.
- MAX17260: register maths host-tested only; the I2C bus label (`i2c2` placeholder) must match
  the carrier overlay, which doesn't exist yet. No gauge config (ModelGauge EZ init) is written,
  so SoC is the gauge's default model until that is added.
- Fence persistence: host-tested on `store_ram.c` only; not yet exercised on real NVS flash.
- Pending acks from `app.acks` (NVS) are not resent by the reporter yet; only the ack for the
  command just downloaded is posted.
- Config: applied through the core and host-tested with a mock-signed config; the endpoint
  switch and `report_s` cadence on the device are not exercised on hardware. `poll_s` is not
  used separately (the boundary is fetched every report cycle).
- `device_class` is not sent (optional; the Rook's class in the herd network isn't decided).
- 413 split: the next cycle relies on `CONFIG_ROOK_LTE_MAX_FIXES`/body cap, not a real halving.
