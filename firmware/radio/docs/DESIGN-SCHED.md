# Sleep / listen / beacon scheduling

Topology-neutral scheduler in `radio_sched` (unit-tested on the host mock):

```
 sleep ──► RX window (rx_window_ms every rx_period_ms)
        ├─► optional CAD wake sniff (cad_wake_period_ms)
        └─► freshness beacon (beacon_period_ms ± jitter)
```

- **Symmetric**: every node (Rook and Starling) both listens and transmits.
  The HAL has no star/mesh role flag.
- **Freshness beacons**: compact version/timestamp adverts for gossip
  anti-entropy (protocol owns the payload; HAL only times them and enforces
  airtime/CAD/power).
- **CAD before TX**: always, via `rhal_send` (random backoff helpers on busy).
- **Low average current**: radio sleeps between RX windows; when boards
  arrive, prefer Zephyr `lora_recv_duty_cycle` (wake-on-radio) if the native
  SX126x backend supports it on our modules — measure mA first (RUNBOOK).

Kconfig (ping/pong sample): `RADIO_RX_PERIOD_MS`, `RADIO_RX_WINDOW_MS`,
`RADIO_BEACON_PERIOD_MS`, `RADIO_BEACON_JITTER_MS`.

Fallback: one-hop star with multiple Rooks stays available when protocol
config `starling_serve` is off (ARCHITECTURE.md); the HAL does not change.
