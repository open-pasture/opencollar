<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 openpasture contributors
-->

# Shared portable core (minimal)

Until op-firmware coordinates a move of `firmware/src/` into `firmware/core/`:

| Piece | Location |
| --- | --- |
| geofence, cue, shape, protocol, slots, … | still `firmware/src/` (do not move here) |
| Welfare hook interface (no numeric caps) | `welfare.h` |
| Fence freshness / gossip | **PR #6** `opencollar/fence_node.h` (`oc_fh_freshness_t`) — not duplicated here |

Starling’s `portable.mk` lives under `firmware/starling/`.
