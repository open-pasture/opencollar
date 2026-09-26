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

### Industry baseline (see `research/virtual-fence-gnss.md`)

Antenna on top with a heavy counterweight under the chin; single-band L1 multi-constellation receivers; adaptive fix rate (~1 Hz within ~20 m of the fence); fence logic on the collar. Best public claim is eShepherd's ±1 m near the fence. Nobody claims L5 or RTK. **Beating the industry on GNSS means L5, a better antenna, and better firmware, not RTK.**

### Direction for V1 hardware

1. **Add a dedicated multi-constellation GNSS receiver; keep the nRF9151 for LTE-M and assistance data.** The nRF91's built-in GNSS is GPS + QZSS only (~8–10 usable satellites) and shares time with the LTE radio, so fixes stall while the modem is busy.
   - **Default candidate:** u-blox **MAX-M10S**. L1, four constellations, < 25 mW continuous, low-power (LEAP) mode, ~$10–15.
   - **Accuracy candidate:** u-blox **MAX-F10S**. L1 + L5, 1.0 m CEP with SBAS (1.5 m without), ~€18. More power; needs a dual-band antenna. L5 mainly fights multipath near trees and the animal's body.
   - **Watch for V2:** u-blox F11 (dual-band at 7 mW in LEAP mode, modules due Q4 2026).
   - **Cheaper L1 alternative:** Quectel LC76G (< 9 mA, four constellations).
   - **Skip RTK.** Nobody uses it; the power and bandwidth cost isn't worth it for ~1 m.
2. **Antenna.** At least a 25×25 mm patch on a 50–70 mm ground plane. Our current small patch is likely the biggest single loss. For L1/L5, use a stacked dual-feed patch or a small quadrifilar helix: circular polarization, and it holds up better when the collar tilts or rotates.
3. **Mechanical.** Antenna in the top housing; battery in the bottom counterweight so its mass does double duty as ballast. Keep the LTE antenna and battery away from the GNSS antenna, and test whether LTE transmissions degrade GNSS.
4. **IMU.** Stationary → slow or stop fixes; walking → speed up; short GNSS gaps → dead reckoning for 10–30 s. Log orientation with every fix to measure time spent rotated.
5. **Shelter beacons** (BLE) so GNSS can switch off under roofs, as Nofence does.

### Levers to test (firmware)

1. **A-GNSS / P-GNSS over LTE** (nRF Cloud or u-blox AssistNow). Hot starts in ~1–5 s instead of minutes; cached predicted orbits cover periods without coverage.
2. **Adaptive fix rate.** One fix per 5–15 min when > 100 m from the fence, rising to 1 Hz within 20–30 m.
3. **Accuracy gating before any cue.** Estimated accuracy under ~3–5 m, at least 6 satellites, and 2–3 consecutive fixes agreeing. V0 only ignores fixes worse than 10 m.
4. **Filtering.** Constant-velocity Kalman filter using the receiver's accuracy estimate, with IMU input; reject jumps implying > 3 m/s.
5. **Health metrics.** Log fix availability, satellites used, C/N0, and time-to-fix on every fix. We can't improve what we don't measure.

### How we'll measure

- Same route, same time, several collars side by side, one variable changed at a time: open sky, tree line, under canopy, hillside, and lying on the ground.
- Record fix availability %, accuracy distribution (CEP50 / CEP95 against a surveyed point), time-to-fix, and current per fix.

## 2. Battery life and power

Needs PPK2 measurements. Industry: 20–70 Wh battery plus solar (Nofence 72 Wh). Rough estimate: duty-cycled M10 (~5 mW average) plus LTE-M in power-saving mode ≈ 0.2 Wh/day, so a 20–40 Wh battery with 1–2 W solar is in line with competitors.

## 3. Ruggedness and animal safety

TBD. Enclosure, strap, weight, heat, water, impact, and no pinch or rub points.

## 4. Connectivity

TBD. Cellular LTE-M first. Compare with coverage at the pilot farm; keep LoRa and base-station options open.

## 5. Openness and repairability

- Off-the-shelf parts wherever possible. Every part in the BOM should be buyable by one person.
- The electronics tray comes out of the enclosure independently of the strap.
- Full build docs, open protocol, host-testable firmware logic.

## Open questions

- Which GNSS chips are inside Nofence, Halter, and Vence? Their FCC internal photos should show them (links in `research/virtual-fence-gnss.md`).
- Is a dedicated GNSS receiver worth its extra power over the nRF9151's built-in one?
- What fix rate does reliable containment actually need?
