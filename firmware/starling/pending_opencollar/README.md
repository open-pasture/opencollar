<!--
SPDX-License-Identifier: Apache-2.0
-->

# TEMPORARY — delete when PR #6 merges

Provides only `oc_fh_freshness_t` (+ size constants in `fence_ids.h`) so
Starling’s fence NVS / geofence path compiles on `starling-app` before
`firmware/lora` lands on `main`.

**Do not** grow this into a second radio/gossip stack. Host tests already
fetch `origin/proto-fence-gossip` into `tests/host/.deps/` for the real
`oc_fh_*` APIs (`node_init` / `set_store` / `restore` / `inject_opaque` /
`poll`).

When PR #6 is on `main`, remove this directory and always include
`opencollar/fence_node.h` from `firmware/lora`.
