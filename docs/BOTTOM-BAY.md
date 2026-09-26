# Bottom bay: swappable modules instead of a dead counterweight

## Why the bottom needs mass at all

The GNSS antenna only works well pointing at the sky. Without weight at the bottom of the collar, the top unit rolls to the side of the neck as the animal grazes, lies down and scratches, and the antenna ends up facing the ground or the animal. Every commercial collar solves this with a 0.5–1.5 kg counterweight. GNSS is our top priority, so the mass has to stay.

**What we can change is what that mass is.** Instead of a lump of steel, the bottom of the collar is a **bay**: a standard cradle on the strap that accepts interchangeable modules. Each module must fall within the same mass window, so the collar balances the same whichever one is fitted.

## The bay standard

| | |
| --- | --- |
| Mount | Cradle riveted/bolted to the strap; modules lock in with two captive stainless thumbscrews (tool-free, can't vibrate loose) |
| Mass window | **450–650 g per module**, to be tuned on real animals |
| Envelope | Fixed maximum size and a low, rounded profile. Nothing protruding that can snag on fences or hit the ground when grazing |
| Electrical | **None through the strap.** Each module is self-contained. Modules that need to talk to the top unit use Bluetooth LE |
| Identification | Each module carries a BLE or NFC tag so the top unit and app know what's fitted |

No wires through the strap keeps the most failure-prone part out of the design. It also means a farmer can swap a module in the field in under a minute.

## Modules

| Module | V1? | What it is | Mass comes from |
| --- | --- | --- | --- |
| **Ballast** | Yes, default | Sealed shell with a steel or zinc slab. The cheapest option and what most collars wear | The slab |
| **Camera** | Yes, a few units | GoPro-standard mount, camera, and a power bank | The camera and the power bank |
| **Battery** | Later | Extra energy for the top unit, for dark winters or heavy camera or pulse use | The cells |
| Sensors | Later | Ideas: rumen or water-point proximity beacons, gas, temperature | TBD |

### Why the battery module waits

Feeding power to the top unit needs either a cable through the strap (the thing we deleted) or a contact/inductive link across the strap. The V1 energy budget already runs 60+ days without sun on the top unit's own cells, so this module isn't needed yet. We'll revisit it if the camera or pulse change the budget.

## Electric pulse: top unit, not the bay

The pulse has to reach the animal reliably on every collar, whichever module is in the bay. It goes on an **add-on board inside the top unit**, with electrodes on the underside of the top unit resting on the top of the neck. The top unit shell reserves the space, the electrode openings and the connector from V1, so adding the pulse means fitting a board, not redesigning the collar.

## Camera module: first iteration

### Goal

Real footage of what cattle do and see: grazing behaviour, forage, how they react at the virtual fence. It's valuable for research, for the pilot farmer, and for telling the OpenCollar story. It doesn't need to be on every collar: a handful of camera collars in a herd is plenty.

### V1-camera: a GoPro in the bay, no integration

The fastest useful version needs no custom electronics:

- **GoPro-standard two-prong mount** molded into the module. It also fits cheap action cameras, since nearly all copy the mount.
- **Camera:** a GoPro, for its waterproofing (10 m without a housing), stabilization and ruggedness, and because of its open control API (below). The base GoPro HERO is roughly $200; any action camera fits the mount for cheaper tests.
- **Power bank as the ballast.** A ~10,000 mAh (~37 Wh, ~200 g) USB-C bank sits in the module and powers the camera through a sealed cable. The mass we needed anyway now runs the camera for many hours of video instead of the camera's own ~1.5 hours.
- **Top-up ballast** (a small steel plate) brings the module into the 450–650 g window.
- **Capture schedule:** GoPro Labs (GoPro's free official firmware add-on, programmed by showing the camera a QR code) supports delayed starts, scheduled daily captures and long-interval time-lapse. To confirm which Labs modes power the camera down between shots on our model.

### What the camera sees from the bottom

Under the chin, facing forward:
- **Head down (grazing):** the muzzle and the forage being eaten, close up. Useful for bite rate and what's actually being grazed, which is data nobody gets today.
- **Head up:** the ground ahead and other animals' legs. Not a scenic view.

For a cow's-eye view of the pasture, the camera belongs on top of the neck, which is the top unit's space. The bay camera is the right first step because it's where the mass already has to be. A top-mounted camera can come later as a variant of the top unit if the footage proves valuable.

### V1.5: the collar controls the camera

GoPro publishes the **Open GoPro API**: start/stop recording, change settings, check battery, all over Bluetooth LE. Once the top unit has BLE, the collar can drive the camera:
- **Record when it matters:** start a clip when the animal enters the warning zone and stop a minute after it's back inside. Every fence interaction on video, with position and cue data alongside.
- **Scheduled pasture snapshots** for forage monitoring.
- **Camera health** (battery, storage) reported in the collar's normal telemetry.
- Footage stays on the camera's card and is collected at the handling yard. LTE-M is far too slow for video; at most, small stills or event metadata go over the network.

This needs BLE in the top unit. The nRF9151 doesn't have it, so V1-beta adds a small BLE chip (e.g. Nordic nRF54L15, a few dollars). That same chip also enables shelter beacons (switching GNSS off under roofs, as Nofence does), phone setup, and identifying which bay module is fitted.

### Risks to test

- **Weight and snagging:** the module stays inside the envelope; the camera sits recessed, not hanging below it.
- **Mud, water troughs and rubbing:** the GoPro is waterproof, but lens scratches and mud cover the view. Test a replaceable clear lens guard.
- **Heat:** a GoPro recording in summer sun can overheat and shut down. Short triggered clips help; continuous recording may not be realistic in July.
- **Animal behaviour:** first camera trials go on calm animals, with the physical fence in place.

## First steps

1. **Our fabrication partner prints the bay cradle and two module shells:** ballast, and GoPro + power bank.
2. **Test on a person first:** balance, rotation (does the top unit stay up?), and camera runtime with the power bank.
3. **One camera collar on a cow at the pilot farm** alongside a ballast collar, with the physical fence in place. Collect footage and compare how well each stays upright.
4. **Add BLE and camera triggering** in V1-beta once the footage proves it's worth it.
