# Prototype V0

Goal: draw a boundary in OpenPasture, send it to a collar built from off-the-shelf parts, walk across it, hear the collar respond, and see the event recorded.

## Bring-up checklist

- [x] Parts laid out, photographed, BOM recorded
- [x] Voltages and logic levels checked (VIO 3.3V, charger 4.2V/100mA; battery polarity still pending)
- [ ] SIM activated
- [ ] MCU: blink + serial logging
- [ ] GPS: raw NMEA, first fix, time-to-fix and accuracy recorded
- [ ] Buzzer: warning tone from code
- [ ] Cellular: registered on network, JSON POST to test endpoint
- [ ] Battery: runs on battery, voltage read over ADC
- [ ] Geofence: hardcoded polygon, inside/near/outside, cue on near
- [ ] Telemetry: periodic POST to OpenPasture
- [ ] Boundary download: fetch by version, store in flash, ack
- [ ] Walk test: cue position vs. true boundary logged

## Wiring

TBD

## Known issues

None yet.
