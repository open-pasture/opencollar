<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 openpasture contributors
-->

# Shared portable core

Portable C used by both Rook (`firmware/` today, later `firmware/rook`) and
Starling (`firmware/starling`). **No Zephyr dependency** in these modules.

## Status (Starling port)

op-firmware owns the eventual layout (`firmware/ARCHITECTURE.md`). Until a
coordinated move of `firmware/src/` lands:

| Module | Lives today | Consumed by Starling via |
| --- | --- | --- |
| geofence, cue, shape, protocol | `firmware/src/` | `firmware/core/portable.mk` |
| boundary parse + Ed25519 verify | `firmware/src/command.c` (+ Monocypher) | same |
| slots | `firmware/src/slots.c` | same |
| welfare cap hooks | **this tree** (`welfare.h`) | Starling cue loop |
| fence freshness record types | **this tree** (`fence_freshness.h`) | Starling fence store / gossip stubs |

**Do not move** files out of `firmware/src/` here. Any relocation is
coordinated with op-firmware.

Welfare numeric defaults are **PLACEHOLDER** pending Cody's decision on
[PR #2](https://github.com/open-pasture/opencollar/pull/2). See `welfare.h`.
