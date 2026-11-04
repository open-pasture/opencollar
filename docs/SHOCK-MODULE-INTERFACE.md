# Shock (pulse) module interface — reserved

**Status:** interface reservation only. Nothing in this document, and nothing
in the accompanying enum-only header, enables or drives any stimulus output.
Cue behaviour is unchanged (audio V0). Hardware current-limit values stay
**TBD for the welfare reviewer**.

**Live use is blocked until all of:** a **named** animal-welfare reviewer has
signed off (Record H’s welfare-reviewer question is necessary but not
sufficient — the reviewer must be named), **owner opt-in**, an **audit log**
of grants and stimulus events, and the module reporting ready. The server
**offers no pulse settings** unless the module is ready. This reservation
adds none of that behaviour.

**Standing rule (Cody, 2026-11-04):** no separate pilot and production
designs. The unit we test is the production design even if only some
components are fitted. The shock module (electrode + driver) may be unfitted
at first; the production enclosure and connectors must still leave a defined
place and the same interfaces for the completed version.

**Placement (OPEN — Cody to decide):** existing docs disagree. Do **not**
treat either as settled in this reservation:

| Source | Says |
| --- | --- |
| [`docs/BOTTOM-BAY.md`](BOTTOM-BAY.md) (Electric pulse) | Pulse add-on board in the **top / crest unit**, electrodes on its underside |
| [`hardware/rook/bom/HARDWARE-FIT.md`](../hardware/rook/bom/HARDWARE-FIT.md), [`hardware/rook/cad/assembly/node_v1.py`](../hardware/rook/cad/assembly/node_v1.py) | Electrode studs in the **side pods** (unwired today) |

This file reserves **logical** connectors, rails, and report fields that work
either way. Mechanical choice is out of scope here.

Related: [`WELFARE-POLICY.md`](WELFARE-POLICY.md),
[`protocol/registry.md`](../protocol/registry.md)
(including reserved `welfare.enforcement` from record L and `cue_state` /
`pulse_off` from record N),
[`hardware/carrier/SPEC.md`](../hardware/carrier/SPEC.md) (existing pin map).

---

## 1. Presence and identification

| Item | Reservation |
| --- | --- |
| **Sense pin** | A dedicated presence / sense line on the module connector shows whether a module is mechanically and electrically fitted. |
| **ID chip** | A small ID chip **on the module** holds serial and hardware revision (I2C footprint reserved; part TBD). |
| **Unfitted** | With no module, the collar **reports nothing** about shock/pulse hardware in the uplink. Firmware may still hold internal state `not_fitted`. |

Detection method details (pull-up/down resistor value, sense polarity, ID
address) are **TBD**. Constraints: sense must not share a net with the
buzzer Qwiic bus enable path in a way that a floating unfitted connector
can look like a live driver enable; ID traffic must not hang the main
GNSS/IMU I2C bus (same external-bus isolation pattern as cue ports if the
module rides off-board).

---

## 2. Dual enable: firmware HV enable + gate latch

High voltage may run only when **both** are asserted:

1. **Firmware enable** (`HV_EN` / logical driver enable) — software path,
   welfare-gated; default inactive at reset, on fault, and whenever the
   module is not in a ready state.
2. **Hardware gate latch**, armed by the MCU output **`GATE_LATCH`**.
   Firmware **does** fire this output: the latch is **one-shot**, cleared on
   any reset, and **not** firmware-independent. Firmware arms it only after
   checking a valid **`pulse_grant`** (below). Saying the latch is
   “hardware” means the latch *holds* until reset once set — **not** that
   firmware cannot assert it alone.

**What actually protects against firmware alone enabling HV:** the
server-signed **`pulse_grant`**, the **fixed hardware current limit**, and
the **independent kill line**. Do not claim the latch itself is outside
firmware’s reach.

Under that AND-gate sit, always:

| Layer | Role |
| --- | --- |
| **Fixed hardware current limit** | Value **TBD by the named welfare reviewer**. Firmware never programs above it; any software limit is strictly lower. |
| **Independent kill line** | Cuts the driver / HV rail **independent of firmware** (kill switch, fuse, or equivalent). Firmware **observes** kill asserted; it does not implement the cut. |
| **Hardware watchdog** | Loss of kick or latch integrity forces HV off. |

**Safe state is always high voltage off:** unfitted, unknown, reset, fault,
kill asserted, latch cleared, watchdog trip, missing / revoked `pulse_grant`,
welfare enforcement off, or `cue_state` of `pulse_off`.

Firmware may assert `HV_EN` **only** from the existing welfare-gated cue path
(same counters as [`WELFARE-POLICY.md`](WELFARE-POLICY.md) / `cue.c`), and
only while the latch is set and grant / welfare / cue-state allow it. This
reservation adds **no** new cue behaviour and **no** driver code.

### `pulse_grant` (signed server permission)

Cap `shock_module` means the **device** understands the interface. It is
**not** the grant.

| | |
| --- | --- |
| Name | `pulse_grant` — **RESERVED (no behaviour)** in [`registry.md`](../protocol/registry.md) |
| What | Signed, revocable server capability that includes a **country rule** |
| Scope | Tied to the collar’s **device id** |
| Revocation | Grant is revoked on **release**, **transfer**, or **factory reset** (and whenever the server revokes it) |
| Latch | Collar may arm `GATE_LATCH` only after verifying a current grant; any reset clears the latch |

Wire shape TBD; name reserved so it is not confused with `shock_module`.

### Welfare and cue-state links

- **`welfare.enforcement`** (record L): when enforcement is off (auto
  shut-off, etc.), no pulse path may run. Distinct from clearing a module
  fault — caretaker `rearm` / `cue_clear_shutoff` clears welfare shut-off
  only; it does **not** clear a module fault.
- **`cue_state` value `pulse_off`** (record N, reserved): cue / stimulus
  state that keeps pulse off; reserved so audio and pulse are not conflated.

---

## 3. Connector pinout (logical; MCU / shell pins TBD)

One module connector (or equivalent harness to the reserved module bay).
Logical names; **physical pin numbers are TBD** and must not collide with
existing carrier wiring in [`hardware/carrier/SPEC.md`](../hardware/carrier/SPEC.md).

| Logical | Direction (collar ↔ module) | Constraint |
| --- | --- | --- |
| `SENSE` | in (collar) | Presence. Must not float into an “enable” interpretation when unfitted. |
| `I2C_SDA` / `I2C_SCL` | bidirectional | ID chip (serial, `hw_rev`). Prefer the protected external bus pattern if off-board; **must not** share pins with GNSS UART or GNSS control lines. |
| `HV_EN` | out (collar) | Firmware enable into the AND with the gate latch. **Pulldown** so unfitted / unpowered / floating never enables. **Must not** share a pin with the buzzer path or GNSS. |
| `KILL` | in (collar observes) | Independent kill / rail-cut sense. |
| `FAULT` | in (collar) | Driver / module fault (open-drain preferred). |
| `GND` | — | Return. |
| `BAT` / pack rail | power | Module power as decided with placement; must not back-power the Kit VIO rail unsafely. |

**MCU pins to reserve (TBD numbers, two free GPIOs minimum):**

| Logical MCU net | Use | Constraints vs today’s map |
| --- | --- | --- |
| `GATE_LATCH` | **MCU output** that arms the one-shot hardware gate latch (only after a verified `pulse_grant`). Cleared on reset. Not firmware-independent — see §2. | Not P0.30/P0.31 (I2C/buzzer), not GNSS (P0.22–P0.27, P0.24 PPS/SAFEBOOT), not FLASH SPI (P0.01–P0.04), not `EXT_EN` (P0.07) reused as HV enable. Prefer a spare such as the NC analog bank **only after** a pin audit; mark **TBD** until assigned. Pulldown / safe-off at reset. |
| `KILL_SENSE` | Observe the independent kill line | Same exclusion set. Input with defined idle level so an open connector is not “ok”. |

**ID chip footprint:** reserved on the module PCB (package TBD; I2C). Collar
side needs only the bus and presence sense.

Optional per-pod duplication (if Cody chooses side-pod electrodes): the same
logical set may be indexed `_*_N` for pod index `N` (0 = left / `CUE_L`, 1 =
right / `CUE_R`). Indexing does not decide placement.

---

## 4. Module states

Firmware-internal and registry-defined state values
([`protocol/registry.md`](../protocol/registry.md)):

| State | Meaning |
| --- | --- |
| `not_fitted` | No module on the sense pin / ID. **Internal + registry only** — not sent as a report block. |
| `fitted_disabled` | Fitted; HV held off (default, latch cleared, missing grant, or welfare / cue-state). |
| `fitted_ready` | Fitted; `pulse_grant` + latch + firmware path allow enable when a welfare-gated cue would fire. Still off until that path asserts. |
| `fault` | A fault code is latched; module forced off until a **person re-enables** it (not caretaker `rearm` / welfare shut-off clear). |
| `killed` | Independent kill asserted; HV off. |

`not_fitted` and unknown **must** mean no firmware path may drive HV. Default
is off.

**v2 status bits:** do **not** reuse the existing `armed` fence status bit for
the module. Module readiness stays a **separate** state (this reservation /
future record fields). Fence `armed` keeps its current meaning only.

---

## 5. Fault codes (proposed names; RESERVED)

Any fault turns the module **off until a person re-enables** it. That is
**not** the welfare `rearm` path (record L / `cue_clear_shutoff`).

| Name | Intent |
| --- | --- |
| `open_electrode` | Open load / electrode path |
| `short` | Shorted electrode or driver output |
| `over_current` | Over the hardware (or lower software) current limit |
| `no_contact` | Fitted but no animal contact detected (method TBD) |
| `over_temp` | Driver or electrode over-temperature |
| `bad_id` | ID chip missing, unreadable, or revision refused |

Wire codes / CBOR numbers: assign when behaviour lands; names are reserved
so they are not reused for something else.

---

## 6. Reports and caps (omit-when-unknown / omit-when-unfitted)

### Caps / grants

| Name | Meaning when listed (future) |
| --- | --- |
| `shock_module` | **Device cap:** collar hardware/firmware understands the reserved shock-module interface. **RESERVED — no behaviour today.** Not a live-use grant. |
| `pulse_grant` | **Signed server permission** (country rule, device-id-scoped, revocable). **RESERVED — no behaviour today.** See §2. |

Listing `shock_module` must never be taken as “pulse is live.” Live use still
needs a named welfare reviewer, owner opt-in, audit log, and a ready module.

### Cue kind

| Kind | Notes |
| --- | --- |
| `pulse` | **RESERVED** in the cue-kind registry. Distinct from `warn` / `outside` audio and from any future vibration kind. **No behaviour** in this PR. |

### v1 report shape

When a module **is** fitted, the position report may include (names reserved).
Omit unknown fields (no placeholders):

```json
"health": {
  "module": {
    "hw_rev": "<from ID chip>",
    "state": "fitted_disabled"
  }
}
```

If a fault is latched, include `"fault": "<name>"`; otherwise **omit**
`fault` entirely.

- Emit `health.module` **only when a module is fitted**.
- v1 fields: `hw_rev`, `state`, and `fault` only when known / latched.
  **No `present` field in v1** — the block’s presence already means fitted.
- When **not** fitted: **omit** the entire `health.module` block (do not send
  `state: "not_fitted"` on the wire).
- Servers **must** treat an absent `health.module` as **not fitted or
  unknown**, and **never** as ok / ready / stimulus-capable.
- The server **offers no pulse settings** unless the module is ready
  (`fitted_ready` and live-use gates above).

Optional later: serial from the ID chip under the same block; omit when
unknown.

### v2

Keep module state out of the fence `armed` bit. A future health-map key or
record field may carry the same semantics; unknown keys stay ignored per
registry extensibility. If a v2 encoding needs an explicit present flag
inside a denser structure, that is a v2-only concern — **not** a v1 JSON
field. No CDDL / vector change in this PR (reservation only).

---

## 7. Hard rules (unchanged welfare gating)

1. Unfitted or unknown → no firmware path may drive the module.
2. Default is **off** (reset clears the latch; enable inactive).
3. This reservation **does not** enable any output and **does not** change
   audio cue behaviour.
4. Live use needs a **named** welfare reviewer (Record H alone is not
   enough), **owner opt-in**, an **audit log**, and a ready module; the
   server offers no pulse settings otherwise.
5. Hardware current limit value remains **TBD for the welfare reviewer**;
   software limits stay strictly below that hardware limit once set.
6. One production design: leave mechanical and connector room even when the
   module is not fitted for early builds.
7. Protection against firmware-alone HV is `pulse_grant` + HW current limit
   + kill line — not a claim that `GATE_LATCH` is outside firmware.

Enum / field-name constants only (no drivers): optional
[`firmware/src/shock_iface.h`](../firmware/src/shock_iface.h).
