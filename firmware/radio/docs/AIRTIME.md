# US 915 bring-up airtime table

Preset: **LoRa, 125 kHz, CR 4/5, 8-symbol preamble, explicit header, CRC on**,
private sync word `0x12`. Spreading factors **SF7–SF10**. Formula: Semtech
AN1200.13 (same as op-protocol `Plan::airtime_us`).

Computed by `radio_airtime_packet_us` (host test `test_airtime` locks these):

| Payload (B) | SF7 (µs) | SF8 (µs) | SF9 (µs) | SF10 (µs) |
| --- | ---: | ---: | ---: | ---: |
| 0 | 25856 | 51712 | 103424 | 206848 |
| 16 | 51456 | 92672 | 164864 | 329728 |
| 64 | 118016 | 215552 | 390144 | 698368 |
| 128 | 215296 | 379392 | 676864 | 1230848 |
| 222 | 348416 | 614912 | 1106944 | 2009088 |

## Pilot dwell accounting

The HAL's pilot default accounts **≤ 400 ms airtime on one channel per 20 s**
(hopping-style planning). Rows above 400 000 µs trip `max_frame_airtime_us`
(`ERR_AIRTIME`). Practical bring-up frames:

- SF7 / SF8: up to 128 B stays under 400 ms.
- SF9: 64 B under; 128 B over.
- SF10: even 64 B over — use short freshness beacons, or switch to the
  500 kHz preset when op-firmware enables it.

Default bring-up SF is **8**. This is a software limiter for the pilot, not a
lab certification result.
