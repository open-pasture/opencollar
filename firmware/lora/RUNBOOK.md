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
| `test_security` | Forged beacon flood (bounded NEED); forged manifest; rollback; dup/reorder/resume |
| `test_persist` | Store HWM + active blob; reboot restore; older rejected; can serve |
| `test_pilot` | Opaque inject; valid activates; tamper/evil sig fail; older rejected |
| `test_maxfrag` | 64-fragment sealed fence re-served by relay (`starling_serve` ON) |

### Clean

```bash
make -C firmware/lora clean
```

## Config

- `starling_serve` — default **OFF**. Rooks always serve.
- Pilot: use `oc_fh_inject_opaque` + `oc_fh_node_set_payload_verify`.
- Later: `oc_fh_inject_local` with farm-sealed manifests.
- Optional: `oc_fh_node_set_store` + `oc_fh_node_restore` after reboot.

## Regenerate vectors

```bash
make -C firmware/lora build/test_vectors && (cd firmware/lora && ./build/test_vectors)
```

## Branch

**`proto-fence-gossip`** for op-fw-radio / reviewers.  
PR head: `cursor/proto-fence-gossip-c865` (same tip).
