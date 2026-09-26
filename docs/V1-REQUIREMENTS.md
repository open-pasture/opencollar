# V1 requirements

Running notes on what matters for the next hardware version. Ranked.

## 1. GPS uptime and accuracy (top priority)

A virtual fence is only as good as its position. A missed or wrong fix means either no cue when the animal is at the line, or a false cue when it isn't. Both teach the animal the wrong thing.

### What we want

- **Availability.** A usable fix (≤ 5 m estimated accuracy) whenever the firmware asks for one, including under tree cover, on hillsides, next to other cattle, and with the animal lying down or grazing head-down.
- **Accuracy.** Open sky: ≤ 2.5 m typical (V0 already does 2.0–2.2 m). Under canopy: ≤ 5 m typical.
- **Fast reacquisition.** A fix within seconds after sleep, so duty cycling doesn't create blind spots.
- **Resilience.** The collar recovers on its own from any GPS outage: no reboot needed, no stuck states.

### Known constraints of V0

- The nRF9151's built-in GNSS tracks **GPS + QZSS only**, single-band L1. No Galileo, BeiDou, or GLONASS. That's the biggest limit on satellite count under obstruction.
- Ceramic patch antenna, orientation not controlled.
- Cold start took ~3 minutes in open sky. No assistance data yet.

### Levers to test (hardware)

1. **Multi-constellation receiver:** roughly 3x more satellites in view.
2. **Dual-band L1 + L5:** better multipath rejection and accuracy.
3. **Antenna:** size, active vs. passive, ground plane, patch vs. helical.
4. **Mechanical:** keep the antenna on top of the neck with a counterweight at the bottom of the collar, and away from the battery, LTE antenna, and the animal's body.
5. **IMU:** motion-triggered fixes, dead reckoning through short dropouts, and flagging a rotated collar.

### Levers to test (firmware)

1. **A-GNSS / P-GNSS over LTE.** Seconds instead of minutes to first fix.
2. **Adaptive fix rate.** Faster fixes near the boundary, slower deep inside it or when the animal isn't moving.
3. **Accuracy gating.** Already in V0: ignore fixes worse than 10 m.
4. **Filtering.** Kalman or similar smoothing of position and velocity, so a single bad fix can't trigger a cue.
5. **Health metrics.** Log fix availability, satellites used, C/N0, and time-to-fix on every fix. We can't improve what we don't measure.

### How we'll measure

- Same route, same time, several collars side by side, one variable changed at a time: open sky, tree line, under canopy, hillside, and lying on the ground.
- Record fix availability %, accuracy distribution (CEP50 / CEP95 against a surveyed point), time-to-fix, and current per fix.

## 2. Battery life and power

TBD. Needs PPK2 measurements. Commercial collars run months, often with solar.

## 3. Ruggedness and animal safety

TBD. Enclosure, strap, weight, heat, water, impact, and no pinch or rub points.

## 4. Connectivity

TBD. Cellular LTE-M first. Compare with coverage at the pilot farm; keep LoRa and base-station options open.

## 5. Openness and repairability

- Off-the-shelf parts wherever possible. Every part in the BOM should be buyable by one person.
- The electronics tray comes out of the enclosure independently of the strap.
- Full build docs, open protocol, host-testable firmware logic.

## Open questions

- How much does the commercial state of the art actually achieve? (Research in progress: Halter, Nofence, Monil, Gallagher eShepherd, Vence, Corral.)
- Is a dedicated GNSS receiver worth its extra power over the nRF9151's built-in one?
- What fix rate does reliable containment actually need?
