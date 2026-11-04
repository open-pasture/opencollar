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
- TLS: SNI and the certificate hostname check both use the `e` host (`ZSOCK_TLS_HOSTNAME`), with
  peer verification required. If any TLS socket option fails, the Rook doesn't connect. The CA
  in sec tag 42 must be the root the server's chain ends at; see "Staging server and its CA".
  Chunked responses (a proxy may re-chunk them) are decoded.

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

## Build the Rook image
Run from `firmware/` (CI uses the same line). `build.sh` can't make this image: it takes no
conf argument or env var and always builds the plain collar image into `build/`. Use west:
```
cd firmware
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- bash -c \
  'export ZEPHYR_BASE=$HOME/ncs/v3.4.1/zephyr; west build -p --sysbuild \
   -b nrf9151_connectkit/nrf9151/ns -d build-rook . -- \
   -DBOARD_ROOT=$PWD -DEXTRA_CONF_FILE="rook/rook.conf"'
# mock bench variant: -DEXTRA_CONF_FILE="rook/rook.conf;rook/rook-mock.conf"
```
- Use `EXTRA_CONF_FILE`, not `CONF_FILE`. `CONF_FILE` replaces `prj.conf`, and that drops the base app.
  `ZEPHYR_BASE` must be exported *inside* the toolchain shell. Run outside the NCS workspace,
  west finds the SDK only through it.
- Outputs, from a verified build on 2026-11-03:
  - `build-rook/merged.hex` (flash this: MCUboot plus the signed app, about 572 KB of hex);
  - `build-rook/firmware/zephyr/zephyr.signed.hex` (app only, for DFU);
  - `build-rook/firmware/zephyr/zephyr.hex` (unsigned app);
  - `build-rook/mcuboot/zephyr/zephyr.hex`.
- Sizes: the app takes 147984 B of 417642 B flash (35.4%) and 105072 B of RAM (49.7%); MCUboot
  takes 31632 B. `python3 scripts/check_image.py build-rook/firmware/zephyr` passes.
- The `.config` should have `CONFIG_ROOK_LTE=y` and `# CONFIG_ROOK_BATTERY_MAX17260 is not set`.
- Flash it the same way as `firmware/build.sh flash`:
  `pyocd flash -t nrf91 -f 4000000 -e sector build-rook/merged.hex`. Use `-e chip` the first time
  over a no-bootloader image. Then provision over serial (see "Shortest path" below).

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

## Staging server and its CA (2026-11-03)
- The endpoint is `https://op-server-staging-staging.up.railway.app/collar/v1`: Railway, https
  on 443, with no port in the URL and no 7878. It replaces the Cloudflare-tunnel assumption.
  Provision with the server's line, with `"e"` set to that URL:
  `provision {"v":1,"c":"<collar_id>","h":"<herd_id>","k":"<64 hex>","e":"https://op-server-staging-staging.up.railway.app/collar/v1","s":"<sig>"}`
  over serial at 115200. Expect `ok <collar_id>`. The `s` signature is made over the whole
  line by the server, so take the line as the server issues it; don't hand-edit `e`.
- The CA is **ISRG Root X1** (Let's Encrypt). It expires 2035-06-04, and its SHA-256 is
  `96:BC:EC:06:26:49:76:F3:74:60:77:9A:CF:28:C5:A7:CF:E8:A3:C0:AA:E1:1A:8F:FC:EE:05:C0:BD:DF:08:C6`.
  It is committed as `firmware/rook/certs/isrg-root-x1.pem`, from
  https://letsencrypt.org/certs/isrgrootx1.pem, and is byte-identical to op-software's
  `/workspace/secrets/op-staging-root-ca.pem`. Check it before you trust it:
  `openssl x509 -in firmware/rook/certs/isrg-root-x1.pem -noout -subject -enddate -fingerprint -sha256`
- The chain the host served on 2026-11-03 (`openssl s_client -connect
  op-server-staging-staging.up.railway.app:443 -servername op-server-staging-staging.up.railway.app -showcerts`):
  - leaf `*.up.railway.app`, ECDSA P-256, expires 2026-12-26;
  - intermediate `YE2`, P-384;
  - `ISRG Root YE`, signed by ISRG Root X2;
  - `ISRG Root X2`, cross-signed by ISRG Root X1.

  That is 4 certs, about 3.4 KB DER. `openssl verify` passes with X1 alone as the trust anchor.
  It also passes with X2 alone, but only because the server sends the X2 cross-cert. X1 is enough
  while Railway keeps sending that cross-cert. If the chain is ever shortened to end at X2,
  X1 alone stops validating. In that case load X2 as well (`isrg-root-x2.pem`, SHA-256
  `69:72:9B:8E:15:A8:6E:FC:17:7A:57:AF:B7:17:1D:FC:64:AD:D2:8C:2F:CA:8C:F1:50:7E:34:45:3C:CB:14:70`)
  in a second sec tag, with both tags in the socket's `SEC_TAG_LIST`. That is not implemented.
- The clock: `curl -sI https://op-server-staging-staging.up.railway.app/healthz` returned 200
  with `date: Wed, 04 Nov 2026 05:12:20 GMT`, matching the box's UTC to the second. A host test
  (`test_ca.c`) parses that header and checks the 9-minute guard against it: a fix at +540 s is
  sent and one at +541 s is left out.

### Loading the CA into sec tag 42
- **Automatic (this build):** `rook.conf` sets
  `CONFIG_ROOK_LTE_CA_PEM="rook/certs/isrg-root-x1.pem"`. The PEM is embedded at build time.
  Before the first attach after boot, the reporter puts the modem in CFUN=4 and calls
  `modem_key_mgmt_cmp` on tag 42. If the CA is missing or different, it calls
  `modem_key_mgmt_write`. Look for `CA in sec tag 42: present` or `written (1939 B) -> 0` in the log.
  An empty `CONFIG_ROOK_LTE_CA_PEM` turns this off, and the tag is then left as it is.
- **Manual AT** (any modem firmware; there is no serial `cert` command in the app). Flash
  NCS's `nrf/samples/cellular/at_client` for `nrf9151_connectkit/nrf9151/ns`, or use Cellular
  Monitor's certificate manager. Then, on its serial port:
  ```
  AT+CFUN=4                       # LTE off; credentials can't be written while online
  AT%CMNG=3,42,0                  # optional: delete an old CA in tag 42
  AT%CMNG=0,42,0,"-----BEGIN CERTIFICATE-----
  MIIFazCCA1Og...                 # the whole PEM, newlines kept, inside one pair of quotes
  -----END CERTIFICATE-----"
  AT%CMNG=1,42                    # list: expect %CMNG: 42,0,"<sha256 of the stored CA>"
  AT%CMNG=2,42,0                  # read it back
  AT+CFUN=0
  ```
  Then reflash the Rook image. Credentials live in the modem and survive an app reflash.

## Pointing a real Rook at Hologram (once Cody activates the SIM)
1. Activate the nano SIM in the Hologram dashboard (by ICCID), plan with LTE-M enabled.
2. Insert SIM, flash the `rook.conf` build, provision with the real farm endpoint
   (staging: `https://op-server-staging-staging.up.railway.app/collar/v1`) and server key.
3. The CA in sec tag 42: the build writes ISRG Root X1 itself (see "Loading the CA into sec
   tag 42"). Without it TLS fails, because peer verify is required.
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
- Demo decision (op-firmware, 2026-11-03): battery is omitted for the demo. MAX17260 stays off
  and the VBAT-divider path is not built.
  The modem's `%XVBAT` is the regulated supply, not the battery: not used.

## Shortest path to a first report in the app
1. Activate the SIM (Cody). 2. Flash the `rook.conf` build; it writes ISRG Root X1 into sec
tag 42 on the first attach. 3. Provision over serial 115200 with the server's `provision {...}`
line (`e` = the staging URL). 4. MAX17260 stays off. 5. First GNSS fix,
then the next cycle posts it; the server's `Date` arrives on that first response.

## Unverified (honest list)
- CA load: `rook_ca_provision` (compare, then write, in CFUN=4) has never run on a modem.
  Whether `modem_key_mgmt_cmp` fits a 1939 B PEM in its buffer (otherwise `-ENOBUFS`, then
  exists means keep) is not checked on hardware. The manual `AT%CMNG` steps are not run either.
- TLS to staging from the modem: not run. Not known: whether the nRF9151 modem accepts the
  4-cert ECDSA chain (P-384 intermediates, cross-signed X2) anchored at X1, and whether
  the modem offers the suite the edge picks: with `-tls1_2`, box openssl got
  ECDHE-ECDSA-AES256-GCM-SHA384 and verified against X1. The chain was
  checked only with box openssl.
- Anything on air: attach, APN, PSM grant, TLS handshake with the modem, DNS. Not run.
- Coexistence: LTE attach while GNSS is tracking (time-shared on the nRF9151; GNSS fixes will
  pause during LTE activity; PSM/eDRX tuning not done).
- `lte_lc_connect()` blocks the reporter thread up to its timeout; fine but untested.
- MAX17260: register maths host-tested only; the I2C bus label (`i2c2` placeholder) must match
  the carrier overlay, which doesn't exist yet. No gauge config (ModelGauge EZ init) is written,
  so SoC is the gauge's default model until that is added.
- Fence persistence: host-tested on `store_ram.c` only; not yet exercised on real NVS flash.
- Pending acks: every cycle after a 2xx report (so after any reboot or reconnect), and again
  after the boundary fetch, the reporter POSTs the core's queued acks (NVS id 2), oldest first,
  with their own `at` (or the server's `Date` if they were made without a clock). It pops an
  ack on a 2xx or any 4xx except 401/408/429, and keeps it on those and on network/5xx errors.
  Host-tested with reboot simulation on `store_ram.c`, not on real flash.
- Config: applied through the core and host-tested with a mock-signed config; the endpoint
  switch and `report_s` cadence on the device are not exercised on hardware. `poll_s` is not
  used separately (the boundary is fetched every report cycle).
- `device_class` is not sent (optional; the Rook's class in the herd network isn't decided).
- 413: the batch is halved from what was sent (down to 1) and resent at once, up to 8 times.
  A single fix that still gets 413 is dropped and counted in `dropped`. A 2xx restores
  `CONFIG_ROOK_LTE_MAX_FIXES`. The halving maths is host-tested; the device loop is not.
