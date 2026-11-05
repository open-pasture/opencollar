# OpenCollar firmware architecture (proposal, draft 2026-11-02)

Status: proposal on branch `docs/firmware-architecture`. Nothing has moved yet. Names marked
`PLACEHOLDER` are not frozen. v2 wire identifiers stay as they are in `protocol/v2/` until
counsel and the protocol owner sign off.

## Roles and hardware
- **Rook**: nRF9151 (LTE-M + GNSS) plus an SX1262 LoRa radio on SPI. Gets fences from the
  server, enforces its own fence, and gossips fences to its neighbours.
- **Starling**: nRF52840 + SX1262 + external u-blox GNSS (MAX-M10S class). Enforces its own
  fence and gossips fences. No LTE, no BLE use.
- Both run the **same portable core and the same LoRa fence exchange**. A Rook is a node that
  also gets fences from the server.

## Directory layout and owners
| Directory | What lives there | Owner |
|---|---|---|
| `firmware/` top level, `CMakeLists.txt`, `sysbuild/`, `scripts/`, CI | build glue, MCUboot, image checks | op-firmware |
| `firmware/core/` | portable C, no Zephyr headers: geofence, shape, cue policy, welfare-cap hooks, boundary parse, Ed25519 verify, slots, config, acks, provision, app state machine | op-firmware (op-fw-starling ports it to nRF52840) |
| `firmware/lora/` | portable fence handoff protocol and `radio_hal.h` | op-fw-proto |
| `firmware/sim/` | host simulator: N nodes on a lossy virtual radio | op-fw-proto |
| `firmware/radio/` | Zephyr SX126x glue implementing `radio_hal.h`, board overlays for the SX1262 | op-fw-radio |
| `firmware/rook/` | nRF9151 app: main, LTE-M, HTTPS, battery, buzzer, NVS store, console, MCUboot config | op-fw-rook-lte |
| `firmware/starling/` | nRF52840 app: u-blox GNSS, scheduling/sleep, buzzer, store | op-fw-starling |
| `firmware/tests/host/` | host tests for core and lora; vectors | owner of the module under test |
| `firmware/third_party/` | monocypher, unchanged | op-firmware |

Rule: `core/` and `lora/` never include Zephyr or board headers. Apps depend on core, lora and
radio; nothing depends on an app. Change someone else's directory only by PR they review.

## Where today's files go
| Today (`firmware/src/`) | Moves to | Note |
|---|---|---|
| geofence.c/h, shape.c/h, cue.c/h, boundary.h | core/ | cue welfare caps: `WELFARE_DEFAULT_*` in cue.h (PR #2 approved) |
| command.c/h (parse + Ed25519 verify), protocol.c/h | core/ | |
| slots.c/h, acks.c/h, config.c/h, provision.c/h, app.c/h, store.h | core/ | store.h is the interface; app.c has a couple of Zephyr-free time helpers, check on move |
| main.c, console.c/h, buzzer.c/h, store_nvs.c | rook/ | starling/ gets its own main and copies buzzer/store glue at first |
| boards/makerdiary/nrf9151_connectkit, boards/*.overlay, partitions | rook/boards/ | SX1262 overlay fragment lives in radio/boards/ |
| (new) | lora/, radio/, sim/, starling/ | |

`command.c`, `shape.c`, `slots.c` and `app.c` matched a grep for Zephyr-like tokens; on reading,
the hits are plain C (`ack_of`, `crypto_*`, clock fields), and the host Makefile already builds
them without Zephyr. Confirm with a no-Zephyr compile in CI after the move.

## Host test mapping
| Test | Covers | New home |
|---|---|---|
| test_geofence, test_shape, test_cue | core | tests/host/core |
| test_command, test_config, test_slots, test_store, test_provision, test_app | core (store via store_ram) | tests/host/core |
| test_herd | core app flow, signed commands | tests/host/core (later also sim) |
| (new) test_manifest, test_fragments, test_trickle, test_freshness | lora | tests/host/lora |
| (new) sim scenarios: 2 nodes, 10-node line (multi-hop), loss 10-50%, rollback, forged beacon | lora + sim | tests/host/sim |

Vectors stay in `protocol/vectors/` (copied into `tests/host/vectors/` as today).

## LoRa fence exchange (`firmware/lora/`): symmetric gossip
All field and type names below are PLACEHOLDERs.

- **Same exchange on every node.** Rook and Starling run identical code; the Rook also injects
  fences received from the server over LTE-M.
- **Server-issued fence**: per farm, a monotonic `fence_seq` and `issued_at`, and an
  Ed25519-signed **manifest**: farm id, fence_seq, issued_at, polygon hash, fragment count,
  per-fragment hashes. Fragments carry the polygon (≤209 data bytes each; limits from
  `lora.md §7.1`: 64 fragments, 12 288 bytes, 4 assemblies at once).
- **Freshness log** per node (flash): fence_seq, hash, received_at, source id, for the fence in
  force and the last few received. Reported to the server in records.
- **Trickle beacon (RFC 6206)** as anti-entropy: beacon = (fence_seq, short hash). Interval
  doubles Imin→Imax while consistent; suppress if k consistent beacons were heard this interval;
  reset to Imin on any inconsistency.
  - neighbour **older** → it is stale: after a random backoff, serve manifest then fragments;
    cancel if another node served first (suppression).
  - neighbour **newer** → request manifest, then only missing fragments (bitmap request).
  - **same seq, different hash** → reset, fetch the manifest, the signature decides; log it.
- **Safety**: beacons are unauthenticated hints, rate-limited per source id. Reject a manifest
  with fence_seq ≤ current (rollback). Verify each fragment against its manifest hash on arrival.
  Activate only after full reassembly, polygon-hash match and signature check; until then the
  old fence stays in force. Serve only verified fences.
- **Duplicates**: keyed by (farm, fence_seq, fragment index).
- **Hops**: every hop is a fresh exchange, so fences need no TTL. A hop count exists only for a
  future telemetry relay. Pilot telemetry stays one hop to the active Rook (`lora.md §8`).
- **Airtime**: listen windows on GNSS time; per-node caps on serves and beacons per window and an
  airtime budget per hour, enforced below the protocol in the HAL.
- **Mode flag** `starling_serve` (PLACEHOLDER config key): off = one-hop star fallback (Starlings
  receive and request, never serve; matches today's `lora.md`), on = multi-hop gossip. Rooks
  always serve. Default off until Starling listen energy is measured.

This departs from `lora.md §1` ("nodes never relay"). The protocol doc change is the protocol
owner's call; firmware carries both modes.

## Radio HAL sketch (`firmware/lora/radio_hal.h`)
```c
/* PLACEHOLDER names. Portable: no Zephyr types. */
struct rhal_cfg { uint32_t freq_hz; uint8_t sf, bw_khz_code, cr; uint8_t sync_word; int8_t tx_dbm; };
struct rhal_rx  { uint8_t buf[255]; uint8_t len; int16_t rssi_dbm; int8_t snr_db; uint64_t t_rx_us; };
struct rhal_limits {
  uint32_t max_frame_airtime_us;  /* refuse longer frames (plan 1: 222 B max) */
  uint32_t airtime_budget_us_per_h; /* per-node budget; send returns RHAL_E_BUDGET when spent */
  uint16_t min_tx_gap_ms;           /* rate limit between our own sends */
};
int  rhal_init(const struct rhal_cfg *cfg, const struct rhal_limits *lim);
int  rhal_set_power(int8_t tx_dbm);                 /* clamped to board/FCC maximum */
uint32_t rhal_airtime_us(uint8_t len);              /* Semtech AN1200.13, same as op-protocol */
int  rhal_send(const uint8_t *buf, uint8_t len, uint64_t at_us); /* 0 = now; blocking until TX done */
int  rhal_recv(struct rhal_rx *out, uint32_t window_ms); /* listen window; RHAL_E_TIMEOUT */
int  rhal_cad(uint32_t timeout_ms);                 /* 1 = channel busy, 0 = clear */
int  rhal_sleep(void);
uint64_t rhal_now_us(void);                         /* monotonic, GNSS-disciplined on target */
uint32_t rhal_airtime_left_us(void);
```
`radio/` implements it on Zephyr's `lora_*` API; `sim/` implements it on a virtual channel with
configurable loss, delay, collisions and range graph.

## Rook bench wiring for the SX1262 (proposal)
Board facts read in `boards/makerdiary/nrf9151_connectkit` (the board is in this repo, not in
Zephyr's tree): UART0 on P0.11/P0.12, button on P0.25, I2C2 (buzzer) on P0.30/P0.31 per the
app overlay. On nRF91 a serial instance is shared by UARTE/SPIM/TWIM with the same number, so
0 (console) and 2 (I2C) are taken: use **SPIM3** (or SPIM1). The carrier plan
(`hardware/carrier/SPEC.md`) puts SPI flash on P0.01–P0.04 and leaves P0.16–P0.20 spare, so the
SX1262 shares that bus with its own CS and uses the spares:

```dts
&pinctrl {
  spi3_default: spi3_default { group1 { psels = <NRF_PSEL(SPIM_SCK, 0, 3)>,
      <NRF_PSEL(SPIM_MOSI, 0, 2)>, <NRF_PSEL(SPIM_MISO, 0, 1)>; }; };
  spi3_sleep: spi3_sleep { group1 { psels = <NRF_PSEL(SPIM_SCK, 0, 3)>,
      <NRF_PSEL(SPIM_MOSI, 0, 2)>, <NRF_PSEL(SPIM_MISO, 0, 1)>; low-power-enable; }; };
};
/ { aliases { lora0 = &lora0; }; };
&spi3 {
  compatible = "nordic,nrf-spim"; status = "okay";
  pinctrl-0 = <&spi3_default>; pinctrl-1 = <&spi3_sleep>; pinctrl-names = "default", "sleep";
  cs-gpios = <&gpio0 16 GPIO_ACTIVE_LOW>;          /* + flash CS P0.04 on the carrier */
  lora0: sx1262@0 {
    compatible = "semtech,sx1262"; reg = <0>; spi-max-frequency = <DT_FREQ_M(8)>;
    reset-gpios = <&gpio0 19 GPIO_ACTIVE_LOW>;
    busy-gpios  = <&gpio0 17 GPIO_ACTIVE_HIGH>;
    dio1-gpios  = <&gpio0 18 GPIO_ACTIVE_HIGH>;
    rx-enable-gpios = <&gpio0 20 GPIO_ACTIVE_HIGH>; /* only if the module needs it */
    dio2-tx-enable;                                  /* module-dependent */
    dio3-tcxo-voltage = <SX126X_DIO3_TCXO_1V8>;      /* module-dependent */
    tcxo-power-startup-delay-ms = <5>;
  };
};
```
Not verified: that P0.16–P0.20 reach header pins 24–28 on the real Kit (taken from the carrier
SPEC table, not Makerdiary's schematic); the chosen module's RF-switch and TCXO wiring; and an
actual build. Check all three before soldering.

## Zephyr support (NCS v3.4.1, Zephyr 4.4.2), verified paths
- Native SX126x driver: `zephyr/drivers/lora/native/sx126x/sx126x.c` (+ `sx126x_hal_common.c`),
  `CONFIG_LORA_MODULE_BACKEND_NATIVE`. Also `drivers/lora/loramac-node/sx126x.c` (module present
  in `modules/lib/loramac-node`) and `drivers/lora/lora-basics-modem/lbm_sx126x.c` (module not
  checked out, so unusable). There is no `drivers/lora/sx126x.c` at the top level.
- Bindings: `zephyr/dts/bindings/lora/semtech,sx1262.yaml`, `semtech,sx126x-base.yaml`.
- Board: `zephyr/boards/seeed/xiao_ble/` (`xiao_ble`, plus `xiao_ble_nrf52840_sense`).
- **No Wio-SX1262 shield** in `zephyr/boards/shields/` (only `semtech_sx1262mb2das`,
  `semtech_sx1261mb2bas`). op-fw-radio writes a `wio_sx1262` overlay in `radio/boards/`.

## Per-collar docs and pairing
Each collar folder (`firmware/rook`, `firmware/starling`) gets `README.md`, `FLASH.md`,
`CONTROL.md` and `PROVISION.md`. Cross-collar behaviour lives in `firmware/docs/INTERFACES.md`:
how Rook, Starling and the server talk (v1 HTTPS/JSON, LoRa gossip, signing).

The pilot has no BLE. "Pairing" means provisioning the farm public key, collar id and role over
serial; the server then registers the collar.

`firmware/src/` stays in place until a migration PR after Nov 4 so in-flight draft PRs do not
conflict. Until then, op-fw-rook-lte's work lives in `firmware/src/rook_lte`.
