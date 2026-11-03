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
  Makefile

firmware/sim/           virtual radio (implements radio_hal.h)
```

## Build and test

```bash
make -C firmware/lora test
make -C firmware/lora loss    # 1000 seeds @ 30% one-hop
```

| Binary | Coverage |
|---|---|
| `test_vectors` | Manifest/fragment/NEED KATs; tamper; bad sig |
| `test_onehop` | One-hop; 0/30/50% loss (`starling_serve` OFF) |
| `test_chain` | Multi-hop chain @ 30%; newer supersedes; partition heal |
| `test_security` | Forged beacon flood; LOCAL air gate + 0xFFFFFFFF attack; pending timeout; sealed preempts local pending; peer oldest eviction; forged manifest; rollback; dup/reorder |
| `test_persist` | Store HWM + A/B CRC; reboot; failed save leaves old active; torn copy falls back; serve |
| `test_pilot` | Opaque inject (`accept_local_air`); valid activates; tamper/evil sig fail; older rejected |
| `test_maxfrag` | 64-fragment sealed fence re-served by relay (`starling_serve` ON) |

### Clean

```bash
make -C firmware/lora clean
```

## Config

- `starling_serve` — default **OFF**. Rooks always serve.
- Pilot: `accept_local_air=1` + `oc_fh_inject_opaque` + `oc_fh_node_set_payload_verify`.
  Without both, air `MANIFEST_LOCAL` is dropped.
- Later: `oc_fh_inject_local` with farm-sealed manifests (`fence_seq` ≤ `OC_FH_SEQ_MAX`).
- Optional: `oc_fh_node_set_store` + `oc_fh_node_restore` after reboot.
- `pending_timeout_ms` — clear stuck pending (0 → `OC_FH_PENDING_TIMEOUT_MS`).

## Regenerate vectors

```bash
make -C firmware/lora build/test_vectors && (cd firmware/lora && ./build/test_vectors)
```

## Branch

**`proto-fence-gossip`** for op-fw-radio / reviewers.  
PR head: `cursor/proto-fence-gossip-c865` (same tip).
