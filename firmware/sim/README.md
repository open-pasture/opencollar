# firmware/sim — host virtual radio

Implements `opencollar/radio_hal.h` for fence-gossip tests: seeded loss, burst
loss, reorder, duplicates, latency, MTU, and a hard duty-cycle budget.

Owned here (op-firmware fence-gossip). op-fw-radio's own host mock is separate.

See `firmware/lora/RUNBOOK.md`.
