<!--
SPDX-License-Identifier: Apache-2.0
-->

# TEMPORARY — delete when PR #6 merges

Provides only `oc_fh_freshness_t` (same layout as
`firmware/lora/include/opencollar/fence_node.h`) so Starling’s fence NVS
store compiles on `starling-app` before `firmware/lora` lands.

**Do not** grow this into a second radio/gossip stack. When PR #6 is on
`main`, remove this directory and always include `opencollar/fence_node.h`.
