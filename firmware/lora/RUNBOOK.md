# Fence gossip runbook

All names are PLACEHOLDERs. Draft PR only — do not merge.

## Layout

```
firmware/lora/          portable library (no Zephyr)
  include/opencollar/   radio_hal.h, fence_*.h, fence_store.h
  src/                  implementation (+ fence_store_ram.c)
  tests/                host tests
  vectors/              KAT hex
  NOTES.md              assumptions, pilot decision, freshness layout
  INTEGRATION.md        handoff for op-fw-starling / op-fw-rook-lte
  Makefile

firmware/sim/           virtual radio (implements radio_hal.h)
```

## Build and test

```bash
make -C firmware/lora test
make -C firmware/lora loss    # one-hop 1000@30% + latejoin multi-hop sweeps
```

| Binary | Coverage |
|---|---|
| `test_vectors` | Manifest/fragment/NEED KATs; tamper; bad sig |
| `test_onehop` | One-hop; 0/30/50% loss (`starling_serve` OFF) |
| `test_chain` | Multi-hop chain @ 30%; newer supersedes; partition heal |
| `test_security` | Forged beacon flood; LOCAL air gate; beacon-hint never blocks sealed; pending timeout; sealed preempts local; peer oldest eviction; rollback; dup/reorder |
| `test_persist` | Atomic HWM+active A/B CRC; higher-seq wins if both valid; failed/torn save; serve |
| `test_pilot` | Opaque inject (`accept_local_air`); valid activates; tamper/evil sig fail; older rejected |
| `test_maxfrag` | 64-fragment sealed fence re-served by relay (`starling_serve` ON) |
| `test_latejoin` | 3/5-node late join (empty/older), supersede mid-catchup, mid pushes newer (`starling_serve` ON). Fast in `test`; `--loss30` long sweeps via `make loss` |
| `test_integration_snippets` | Rook/Starling INTEGRATION.md setup (own buffers each); init + poll |

### Clean

```bash
make -C firmware/lora clean
```

## Config

- `starling_serve` — default **OFF**. Rooks always serve. Multi-hop / latejoin tests set **ON**.
- Pilot: `accept_local_air=1` + `oc_fh_inject_opaque` + `oc_fh_node_set_payload_verify`.
  Without both, air `MANIFEST_LOCAL` is dropped.
- Later: `oc_fh_inject_local` with farm-sealed manifests (`fence_seq` ≤ `OC_FH_SEQ_MAX`).
- Optional: `oc_fh_node_set_store` + `oc_fh_node_restore` after reboot.
- `pending_timeout_ms` — clear stuck pending (0 → `OC_FH_PENDING_TIMEOUT_MS`).

Integration details: **`INTEGRATION.md`**.

## Regenerate vectors

```bash
make -C firmware/lora build/test_vectors && (cd firmware/lora && ./build/test_vectors)
```

## Branch

**`proto-fence-gossip`** for op-fw-radio / reviewers.  
PR head: `cursor/proto-fence-gossip-c865` (same tip).
