# Radio bring-up runbook (SX1262)

Pilot stance: no BLE. Rook = LTE-M + GPS + LoRa; Starling = LoRa mesh-relay /
gossip. This tree is Zephyr SX126x glue implementing `radio_hal.h`.

## NCS facts (v3.4.1 / Zephyr 4.4.2)

| Item | Path / value |
| --- | --- |
| Native SX126x driver | `zephyr/drivers/lora/native/sx126x/sx126x.c` |
| Backend Kconfig | `CONFIG_LORA_MODULE_BACKEND_NATIVE=y` |
| Bindings | `semtech,sx1262` / `semtech,sx126x-base` |
| XIAO board | `zephyr/boards/seeed/xiao_ble` → target `xiao_ble/nrf52840` |
| Wio-SX1262 shield | **Not in Zephyr** — use in-repo `boards/shields/wio_sx1262` |
| Rook board | in-repo `firmware/boards/makerdiary/nrf9151_connectkit` → `nrf9151_connectkit/nrf9151/ns` |

## Build / flash

Needs the NCS v3.4.1 toolchain (`nrfutil sdk-manager toolchain launch --ncs-version v3.4.1`).

### Starling bench: XIAO nRF52840 + Wio-SX1262

```bash
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/radio/scripts/build_xiao.sh              # initiator
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/radio/scripts/build_xiao.sh responder    # other board
west flash -d firmware/radio/build/xiao
```

### Rook bench: nRF9151 Connect Kit + Core1262-HF (**PROPOSED pins**)

```bash
nrfutil sdk-manager toolchain launch --ncs-version v3.4.1 -- \
  firmware/radio/scripts/build_nrf9151.sh
west flash -d firmware/radio/build/nrf9151
```

### Host tests (no hardware, CI)

```bash
make -C firmware/radio/tests/host
```

## Pin tables

### XIAO + Wio-SX1262 (sourced)

| Signal | XIAO | nRF52840 | Notes |
| --- | --- | --- | --- |
| NSS/CS | D4 | P0.04 | |
| SCK | D8 | P1.13 | `xiao_spi` / spi2 |
| MOSI | D10 | P1.15 | |
| MISO | D9 | P1.14 | |
| DIO1 | D1 | P0.03 | IRQ |
| RESET | D2 | P0.28 | |
| BUSY | D3 | P0.29 | |
| RXEN | D5 | P0.05 | LNA gate, HIGH on RX |
| DIO2 | (module) | — | `dio2-tx-enable` RF switch |
| DIO3 | (module) | — | TCXO 1.8 V |

Sources: Seeed wiki *XIAO nRF52840 & Wio-SX1262 Kit*; Meshtastic
`seeed_xiao_nrf52840_kit` variant; Seeed Wio-SX1262 for XIAO schematic.

### nRF9151 + Core1262-HF — **PROPOSED, confirm on arrival**

Already taken: UART0 P0.11/12, button P0.25, I2C2 P0.30/31. Use **SPIM3**.

| Signal | nRF9151 | Status |
| --- | --- | --- |
| SCK | P0.03 | PROPOSED |
| MOSI | P0.02 | PROPOSED |
| MISO | P0.01 | PROPOSED |
| CS | P0.16 | PROPOSED (header pin 24?) |
| BUSY | P0.17 | PROPOSED (25?) |
| DIO1 | P0.18 | PROPOSED (26?) |
| RESET | P0.19 | PROPOSED (27?) |
| RXEN | P0.20 | PROPOSED optional (28?) |

Not checked: header reachability of P0.16–P0.20; whether Core1262 hard-wires
DIO2 to the RF SPDT; whether RXEN/TXEN pads must be driven or left open;
TCXO on DIO3 @ 1.8 V.

Core1262-HF switch (Waveshare): TXEN/RXEN control an on-board SPDT; DIO2 may
act as RF-switch ctrl (HIGH in TX). Overlay sets `dio2-tx-enable` and
`rx-enable-gpios`.

## First ping/pong day (boards ~ Nov 5–6)

1. Flash initiator on one board, responder on the other (or both initiators).
2. USB serial 115200: expect `rx PING` / `rx PONG` with RSSI/SNR and counts.
3. Same SF/freq on both (`CONFIG_RADIO_SF`, `CONFIG_RADIO_FREQ_HZ`).
4. If CAD busy storms: check antennas and distance; watch `RHAL_E_BUDGET`.

## Assumptions

- Bring-up preset is **125 kHz SF8 CR4/5**, not protocol Plan 1 (500 kHz).
- TX capped at **+14 dBm** until conducted power is measured.
- Hourly airtime budget ~1 %; min TX gap 100 ms; CAD before every TX.
- `radio_hal.h` here is the proposed shape until `firmware/lora/radio_hal.h`
  lands on a `proto-*` branch (none present when this PR opened).

## Measurement plans (hardware-dependent — do not guess)

| ID | What | How (when boards arrive) | Pass criteria (fill in) |
| --- | --- | --- | --- |
| M1 | Average current vs RX scheme | Nordic PPK2; compare continuous RX vs `rx_window/rx_period` vs `lora_recv_duty_cycle` if available | ___ µA avg at scheme X |
| M2 | Packet success vs distance | Fixed SF8/14 dBm; LOS pasture distances 10/50/100/200 m; 100 pings each | ___ % @ ___ m |
| M3 | Conducted TX power | Spectrum analyzer / power meter at U.FL | ≤ cap; match grant |
| M4 | 6 dB BW / PSD | For whichever FCC regime ships | 15.247 pass |
| M5 | CAD false-busy rate | Quiet bench vs 2-node traffic | ___ % |

## Open questions for op-firmware

1. Ship 125 kHz hop preset or Plan 1 500 kHz first?
2. Confirm Rook header pins P0.16–P0.20 and Core1262 RF-switch wiring.
3. Reconcile this `radio_hal.h` with op-fw-proto's `firmware/lora` copy when it lands.
4. CI: NCS board builds — see `ci/README.md` (needs NCS in the runner).
