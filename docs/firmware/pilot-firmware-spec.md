# OpenCollar pilot firmware spec: Rook + Starling (draft, 2026-11-02)

Source: Cody (voice, Nov 2), checked against open-pasture/opencollar main @ ca73590 (origin has nothing newer).
"Verified" = read in the repo or Nordic's docs. "Assumed" = my inference.

## Mapping to the repo
The repo already designs this, under other names: **Rook = anchor** (role 2, LTE + LoRa), **Starling = node** (LoRa only) in `protocol/v2/README.md` and `protocol/v2/lora.md`. Verified.
**Design change (Cody, Nov 2, 6:13 PM CT): Starlings relay to each other, multi-hop gossip.** This departs from `lora.md §1` (*star, one hop, nodes never relay*). The cost is listening energy on Starlings, and `lora.md` has to change, which is a protocol owner/counsel decision. Firmware ships both modes behind a config flag `starling_serve` (placeholder name): off = today's one-hop star, on = multi-hop gossip (§4). Hardware plan: Rook = nRF9151 + SX1262; Starling = nRF52840 + SX1262 + external u-blox GNSS. See `firmware/ARCHITECTURE.md` on branch `docs/firmware-architecture`.

## 1. Rook firmware (nRF9151, today's code)
- Has now (verified, v0.2): GNSS fix, geofence, buzzer, serial console, Ed25519-signed boundary commands (`firmware/src/command.c`, monocypher).
- Pilot adds: LTE-M v1 HTTPS report and boundary download (option 3 in `/workspace/op-architect/decision-records-2026-11-02.md`), and MCUboot `merged.hex`.
- To relay fences to Starlings it needs **a LoRa radio. The nRF9151 has none.** Nordic lists only LTE-M/NB-IoT, DECT NR+ and GNSS on it: no BLE, no sub-GHz LoRa (verified on the product page, not the full datasheet). The current board (`hardware/bom.md`: Makerdiary nRF9151 Connect Kit) has **no LoRa part. This is the main BOM risk.** Fix: add an SX1262 over SPI. Off-the-shelf options are RAK4630 (nRF52840 + SX1262, which the protocol already targets) or a bare SX1262 module. Then the Rook runs the anchor role: beacon, downlink window, uplink slots, batch to server. That requires protocol v2 framing (`lora.md`). v1 can't do LoRa (decision records, option 3).

## 2. Starling firmware (LoRa only)
LoRa receive of signed herd broadcasts, reassembly, signature check, and atomic switch to the new boundary. Plus own GNSS, geofence, buzzer, welfare caps (PR #2 approved: 3 outside cues / 3 escape cycles / 24 h in `cue.h` `WELFARE_DEFAULT_*`), and records kept in flash. No cellular, no BLE.
- Chip: the repo implies **nRF52840 + SX1262 (RAK4630)**, via the boot profile `nrf52840-mcuboot-1` "node and anchor boards" in `protocol/v2/firmware.md`, the RAK4630 FCC grant in `lora.md §2`, and the SX1262 energy figures in `v2/README.md`. Inferred, because no Starling BOM exists. `hardware/rook/cad/lib/node_v1.py` covers only the shell.
- Options: (a) **RAK4630**, which matches the repo, is FCC-certified and runs Zephyr. Its BLE goes unused. Recommended. (b) STM32WL (MCU and LoRa in one chip): cheapest at volume, but a new SDK and the C fence code has to be ported. (c) nRF54L15 + SX1262: newer and lower power, but a new board. (d) nRF9151 + SX1262 without a SIM: same code as the Rook, but it pays for a modem it doesn't use, which defeats the cost reason for Starling.
- Reusable from Rook (assumed portable; it's plain C): `boundary`, `geofence`, `shape`, `cue`, `command` (Ed25519 verify), `slots`, `config`. Needs rewriting: modem/LTE and the nRF91 GNSS driver. The nRF52840 has no GNSS, so a Starling needs a separate GNSS chip. `docs/V1-REQUIREMENTS.md` already recommends a dedicated multi-constellation receiver.

## 3. BOM
- **Rook:** current Connect Kit + LTE-M SIM + **SX1262/RAK module + 915 MHz antenna** (new) + battery/buzzer as today.
- **Starling:** RAK4630 (or chosen MCU+SX1262) + GNSS module + antenna + battery + buzzer + charger. Not specified anywhere in `hardware/`. **Nothing to order until Cody approves.**
- Ratio 1:10: fine. v2 sizes a net at up to 300 collars. Keep **at least 2 Rooks per herd** for failover (`lora.md §5`), so a 20–50 head pilot needs about 3–5 Rooks. No reason found to change the 1:10 ratio.

## 4. Protocol: symmetric fence gossip (revised 2026-11-02; names are placeholders until counsel)
- **One exchange for every node.** A Rook and a Starling run the same LoRa fence exchange. A Rook is just a node that also gets fences from the server over LTE-M.
- **What the server issues:** a monotonic `fence_seq` per farm plus `issued_at`, and an Ed25519-signed **manifest**: farm id, fence_seq, issued_at, polygon hash, fragment count, and a hash per fragment. The polygon itself is carried in fragments (≤209 B data, `lora.md §7.1` limits: 64 fragments, 12 KB, 4 assemblies).
- **Freshness log per node** (in flash): fence_seq, hash, received_at, source id, for the fence in force and the last few received.
- **Anti-entropy beacon, Trickle-style (RFC 6206):** each node beacons (fence_seq, short hash). The interval doubles from Imin to Imax while neighbours agree; a node suppresses its beacon if it already heard k consistent ones in this interval; any inconsistency resets the interval to Imin.
  - Hear an **older** seq: that neighbour is stale. Wait a random backoff, then serve manifest + fragments, unless someone else served it first (suppression).
  - Hear a **newer** seq: request the manifest, then only the missing fragments (bitmap, as `need` in `lora.md §4`).
  - Same seq, different hash: inconsistency. Reset Trickle, fetch the manifest, let the signature decide; log it for the server.
- **Security and rollback:** beacons are unauthenticated hints, rate-limited per source. A manifest with fence_seq ≤ current is refused. Each fragment is checked against its hash in the signed manifest as it arrives, so a bad fragment is dropped at once. The fence activates only after full reassembly, the polygon hash matches, and the signature checks; until then the old fence stays in force. A node never serves a fence it hasn't verified.
- **Hops:** each hop is a fresh exchange between neighbours, so fences need no TTL and no hop count. A hop count is kept only for any future telemetry relay.
- **Duplicate suppression:** by (farm, fence_seq, fragment index); a node that holds a fragment ignores repeats and doesn't re-serve what it just heard served.
- **Airtime and listening:** listen windows on GNSS time (the `lora.md §3` minute stays for Rook uplink); serving and beacons capped per node per window with a per-hour airtime budget enforced in the radio HAL. US915 plan 1 has no duty-cycle rule, but battery and channel share do. EU 868 (1%) is out of pilot scope.
- **Telemetry up** stays one hop to the active Rook (`lora.md §8`) in the pilot; Starling relay of telemetry is future work.
- **Acks to the server:** link-level `got`/`need` plus the collar's signed record (unchanged). The freshness log lets the server see which source fed each node.


## 5. Friday (Nov 6) target
- **Doable:** Rook `merged.hex` with MCUboot (draft PR in progress), plus v1 LTE-M report/boundary download if the SIM is active.
- **Not doable by Friday:** Starling firmware and the Rook's LoRa side. There's no LoRa hardware and no Starling board, and the v2 firmware isn't written (vectors exist; the Rust reference is in op-protocol). Realistic order: Friday Rook v1 → order RAK4630 dev boards (Cody approves) → v2 LoRa bench link Rook↔Starling over about 2–3 weeks (estimate).

## 6. Open questions / risks
1. Multi-hop gossip changes `lora.md §1`'s no-relay rule. Starling listening energy goes up with `starling_serve` on: measure before turning it on by default. The protocol doc change needs the protocol owner; firmware keeps names as placeholders.
2. Rook has no LoRa radio. It must add an SX1262/RAK4630. Biggest BOM change.
3. Starling MCU and GNSS aren't specified. RAK4630 + external GNSS is assumed.
4. v1 can't carry LoRa. Starlings need v2 firmware and server `/collar/v2/batch`. Don't freeze v2 names before counsel.
5. FCC: the 500 kHz bandwidth and the RAK4630 grant aren't checked. Whether pilot loaner units are allowed is a question for a specialist.
6. Welfare cap numbers: PR #2 approved defaults in `firmware/src/cue.h` (`WELFARE_DEFAULT_*`).
7. Node energy figures come from the datasheet, not measurements (v2 README open question 6).

## 7. Added: DECT NR+ vs LoRa for the Starling radio, and the no-Bluetooth check
**No Bluetooth (verified, by omission).** The nRF9151 Product Specification key-features table (https://docs.nordicsemi.com/r/bundle/ps_nrf9151/page/nrf9151_html5_keyfeatures.html) lists the M33 MCU, the LTE modem, the GPS receiver and DECT NR+, and **no Bluetooth or other 2.4 GHz radio**. The DECT page's coexistence section names "a companion ... Bluetooth Low Energy device" as external. There is no explicit sentence saying "no BLE"; the conclusion comes from the feature list.

**DECT NR+ on the nRF9151 (verified, PS DECT page https://docs.nordicsemi.com/r/bundle/ps_nrf9151/page/dect.html):**
- **It replaces the modem firmware.** "While running DECT NR+ firmware, the nRF9151 SiP does not support the LTE modem or GPS receiver." So a **Rook can't do LTE-M and NR+ in one image**; it would have to reflash or swap modem firmware at runtime, which is not practical. An NR+ Starling on the nRF9151 needs an **external GNSS** (the repo wants one anyway, `V1-REQUIREMENTS.md`).
- **Bands:** 1, 2, 4, 9, 22. Band 4 is 902–928 MHz (19 dBm max) and band 9 is 1.9 GHz (21 dBm), so "915 MHz" is real. The band-4 frequency comes from a third-party integration guide (FLSEMI BFi91XTD, 2026-10) and the ETSI band plan, not the Nordic PS table. Bands 1, 2 and 22 are not usable in the US.
- **RF:** 1.728 MHz channel. Sensitivity is −105 dBm (beacon, MCS0) and −103 dBm (unicast). The peak rate is up to 3.4 Mbps.
- **FCC (verified):** Nordic's nRF9151 FCC grants cover **LTE-M/NB-IoT and NTN only**. Its NR+ certification is **CE/UKCA only** (https://www.nordicsemi.com/Products/Wireless/Low-power-cellular-IoT/nRF91-Series-certifications/nRF9151-Global-and-regulatory). A US NR+ product needs **its own FCC Part 15 certification**. FLSEMI says band 4 range and throughput are "not yet characterised."
- **NCS 3.4.1 (verified locally, `~/ncs/v3.4.1/nrf`):** the samples are `samples/dect/{dect_phy, dect_shell, hello_dect}` (nrf9151dk). There is a DECT L2 in `subsys/net/l2_dect/` and `include/net/dect/dect_net_l2.h`. The software-maturity table has a "DECT NR+ PHY" row with **no "Supported" entries** (`doc/nrf/releases_and_maturity/software_maturity.rst` ~l.205). Nordic ships the PHY; a MAC/mesh with routing would be ours to write or license (e.g. FLSEMI). The NR+ modem firmware is a separate download from Nordic.

| | LoRa (SX1262) | DECT NR+ (nRF9151) |
|---|---|---|
| Range per hop | Longest: −120 to −130 dBm sensitivity at SF8–SF12 (datasheet; 500 kHz SF8 ≈ −117) | Shorter: −103 to −105 dBm. NR+ is designed to mesh rather than reach far |
| Data rate | ~10–20 kbps (500 kHz SF8) | Up to Mbps. Boundaries and firmware move fast |
| Power | Low, well characterised (repo budget in `v2/README.md`) | Not characterised for collars. Wider-band RX likely costs more per listen (assumed) |
| US regulatory | Certified modules exist (RAK4630 grant, to check) | No US grant for the nRF9151's NR+. We'd certify ourselves |
| Stack | The repo's v2 LoRa binding is specified and tested in op-protocol | PHY only in NCS. Our v2 binding would need a new link layer |
| Ecosystem | Huge (Semtech, RAK, Meshtastic) | Young. Few US deployments |
| Same chip as Rook? | No: Rook adds an SX1262, Starling is a RAK4630 | Starling could be an nRF9151, giving one firmware tree for the app layer. But the **Rook still can't run LTE and NR+ at once**, so a Rook would need a second NR+ radio or a time-shared modem |

**Verdict:** keep **LoRa (SX1262)** for the pilot. NR+ fails the Rook role: LTE and NR+ are mutually exclusive on one nRF9151, it has no US certification, and its stack is immature. It also gives shorter range, which is what a pasture needs most. Revisit NR+ for V2 if a true multi-hop mesh becomes a requirement and Nordic gets an FCC grant for it.
