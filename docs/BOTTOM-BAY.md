# Bottom bay: swappable modules instead of a dead counterweight

## Why the bottom needs mass at all

The GNSS antenna only works well pointing at the sky. Without weight at the bottom of the collar, the top unit rolls to the side of the neck as the animal grazes, lies down and scratches, and the antenna ends up facing the ground or the animal. Every commercial collar solves this with a 0.5–1.5 kg counterweight. GNSS is our top priority, so the mass has to stay.

**What we can change is what that mass is.** Instead of a lump of steel, the bottom of the collar is a **bay**: a standard cradle on the strap that accepts interchangeable modules. Each module must fall within the same mass window, so the collar balances the same whichever one is fitted.

## Two ways to get a collar

| | **DIY (open design)** | **OpenCollar (sold)** |
| --- | --- | --- |
| Strap | Any standard ~50 mm cattle neck strap you buy | Our wired strap |
| Printed parts | Top unit, bay cradle, modules, printed from the published files | Supplied |
| Wiring | None by default. Optional: add the harness (an off-the-shelf M8 cordset clipped along the strap) | Built in |
| Bottom modules | Self-contained only: **ballast**, or **camera** (GoPro + its own power bank) | Ballast, **Battery Extension**, **Battery + Camera**, anything that uses the bus |
| Fence | Identical. The top unit is the same, and the fence never depends on the bottom module | Identical |

Same top unit, same firmware, same bay standard in both. The DIY collar gives up only the modules that share power with the collar (Battery Extension, collar-charged camera). Adding the M8 harness to a DIY collar unlocks them.

## Product lineup (sold)

The collar always works on its own. Everything in the bay is optional.

| Package | What's in it | Who it's for |
| --- | --- | --- |
| **OpenCollar** (base) | Top unit + wired strap + **ballast module** | Most animals. The cheapest complete virtual fence collar |
| **+ Battery Extension** (add-on) | Battery module | Northern winters, heavy shade, collars running the pulse or a camera hard |
| **+ Camera** (add-on) | Battery + Camera module (a Battery Extension with a GoPro mount) | A few animals per herd, for footage and research |

Every module doubles as the counterweight, so swapping one never changes how the collar balances.

## The bay standard

| | |
| --- | --- |
| Mount | Cradle on the strap; modules lock in with two captive stainless thumbscrews (tool-free, can't vibrate loose) |
| Mass window | **450–650 g per module**, to be tuned on real animals |
| Envelope | Fixed maximum size and a low, rounded profile. Nothing protruding that can snag on fences or hit the ground when grazing |
| Electrical | Optional. Sold collars have a wired strap; DIY collars can add the harness. Self-contained modules (ballast, standalone camera) work with or without it |
| Identification | Each module identifies itself over the wire, so the top unit and app know what's fitted |

### The wired strap: a harness that rides on a bought strap

The strap itself is a standard cattle neck strap (see `MATERIALS-AND-STRAP.md`). The wiring is a **separate harness** that rides along it, so the open design never needs a custom strap.

- **The harness is an off-the-shelf industrial cable.** An M8 4-pin male-to-female cordset in a high-flex PUR jacket: the same cable used on robot arms and drag chains, rated for millions of bend cycles, IP67/68 at both ends, and sold in fixed lengths by every automation supplier for about $10–20.
- **The top unit and the bay cradle each have a panel-mount M8 socket.** The cordset plugs into both.
- **It runs along one side of the strap only**, between the top unit and the bay, held flat with printed TPU clips (or threaded through a sewn webbing sleeve). The top unit and bay clamp to the strap at a fixed spacing on that side, so the cable length never changes. All sizing happens at the buckle on the other side.
- **Replacing it** takes a minute: unclip, unplug, plug in a new one. Anyone can buy the same cable.
- **The collar never depends on it.** The top unit runs on its internal battery and fence logic whether or not the harness is intact. Its port has short-circuit protection, so a crushed cable or flooded connector gets reported and isolated, never drains the collar.
- **Prove it early:** the V1-alpha collar gets a harness from day one, so person-wear and cow tests show how it survives.

### The power bus

Four pins: **power, ground, and two data lines.**

- **Power is a 5 V bus that either end can supply.** The top unit's charger (TI BQ25798) has two inputs and can also output power:
  - Input 1 is the solar panels.
  - Input 2 is the strap bus. When a battery module supplies 5 V, the top unit charges from it exactly as it would from a solar panel.
  - In reverse (the charger's output, or "OTG", mode), the top unit puts 5 V on the bus to charge a battery module or power a camera when it has solar surplus.
- **Data** (I2C to start): every module carries a small ID chip saying what it is. Battery modules report charge and health; camera modules take start/stop commands. The top unit is always in charge of the bus and decides which direction power flows.
- **5 V was chosen** because it can charge a GoPro or any USB device directly.

## Modules

| Module | V1? | What it is | Mass comes from |
| --- | --- | --- | --- |
| **Ballast** | Yes, ships with every collar | Sealed shell with a steel or zinc slab and a dummy M8 plug | The slab |
| **Battery Extension** | Designed in V1, built after the first pilot | LiFePO4 pack with its own charger, protection and fuel gauge. Feeds the collar through the bus and refills from solar surplus | The cells |
| **Battery + Camera** | Yes, one for the pilot | A Battery Extension with a GoPro mount on the front. The pack powers the camera over USB-C inside the module, and the collar refills the pack from solar | The cells and the camera |
| Sensors | Later | Ideas: water-point proximity, temperature | TBD |

### Why the camera module is a battery module

The bay holds one module at a time, so the camera can't sit next to a separate battery pack. A GoPro recording draws about 4 W, which would drain the top unit's internal battery (~22 Wh) in a few hours and threaten the fence. So the camera brings its own energy: its module is a battery pack with a mount. The pack's mass is the counterweight, the collar's solar tops it up, and the fence's own battery is never touched by the camera.

Budget: in summer, solar surplus of a few Wh/day covers roughly an hour of recording a day, which suits event-triggered clips (fence approaches, scheduled snapshots) rather than all-day recording.

### Battery Extension

**How it connects:** swap the ballast module for the battery module and plug in the harness.

**How it works:**
- **Pack:** 4 × 26650 LiFePO4 (~45 Wh, ~350 g plus shell), inside the mass window. With the internal ~22 Wh, total autonomy with no sun goes from ~60 days to **~190 days**.
- **Charging:** the top unit's solar charger fills the internal battery first, then sends surplus down to the pack. The pack has its own protection circuit and fuel gauge and reports its charge to the top unit.
- **Failure-safe:** if the strap or pack fails, the top unit sees it, reports it, and carries on with its internal battery. Containment never depends on the extension.

**What V1 must include so this is a pure add-on later:**
- **Power-path circuitry** on the main board that can charge and draw from an external LiFePO4 pack through the strap.
- **Firmware** that detects the pack and adds it to the energy and telemetry reports.

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
- **The power bank is the prototype battery module.** Pick one with pass-through charging and wire its USB-C input to the bay's M8 socket: the collar tops it up from solar over the harness while it powers the camera. That's the Battery + Camera module built from bought parts; the custom LiFePO4 pack replaces it later.
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

With the wired strap, a small bridge chip in the camera module can pass commands from the collar to the camera, so BLE isn't strictly required. BLE is still worth adding to the top unit. The nRF9151 doesn't have it, so V1-beta adds a small BLE chip (e.g. Nordic nRF54L15, a few dollars). That same chip also enables shelter beacons (switching GNSS off under roofs, as Nofence does), phone setup, and identifying which bay module is fitted.

### Risks to test

- **Weight and snagging:** the module stays inside the envelope; the camera sits recessed, not hanging below it.
- **Mud, water troughs and rubbing:** the GoPro is waterproof, but lens scratches and mud cover the view. Test a replaceable clear lens guard.
- **Heat:** a GoPro recording in summer sun can overheat and shut down. Short triggered clips help; continuous recording may not be realistic in July.
- **Animal behaviour:** first camera trials go on calm animals, with the physical fence in place.

## First steps

1. **Our fabrication partner prints the bay cradle and two module shells:** ballast, and Battery + Camera (GoPro + pass-through power bank).
2. **Test on a person first:** balance, rotation (does the top unit stay up?), and camera runtime with the power bank.
3. **One camera collar on a cow at the pilot farm** alongside a ballast collar, with the physical fence in place. Collect footage and compare how well each stays upright.
4. **Add BLE and camera triggering** in V1-beta once the footage proves it's worth it.
