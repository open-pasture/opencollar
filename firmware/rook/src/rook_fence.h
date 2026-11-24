/* SPDX-License-Identifier: Apache-2.0 */
/*
 * A signed fence downloaded over LTE-M: verified and stored through the
 * existing app_boundary() path (Ed25519 in command.c, slots in NVS), then
 * handed, still as the signed bytes, to the LoRa side for gossip to
 * Starlings. fence_seq is the server-issued monotonic number: in v1 it is
 * the command's `version`.
 *
 * The high-water mark (the highest fence_seq accepted) and the signed bytes
 * of that fence persist in the store (store.h STORE_ID_ROOK_FENCE*), so after
 * a reboot a validly signed but older fence is refused (REJECT_STALE, before
 * it reaches the slots) and the active signed fence can be re-gossiped. The
 * record is bound to the provisioned herd and server key: a re-provisioned
 * Rook (new herd or server) starts again from 0.
 *
 * Write order (power-cut safe, store writes are atomic per id): the chunks go
 * into the bank the header doesn't point at, then the header is written.
 *
 * The LoRa hand-off is a thin hook: op-fw-proto's portable library
 * (firmware/lora, in progress) registers a sink with rook_fence_set_sink().
 * The sink gets the v1 signed JSON command as opaque bytes plus fence_seq.
 *
 * Call from the main thread only (Ed25519 needs its 8 KB stack).
 */
#ifndef ROOK_FENCE_H
#define ROOK_FENCE_H

#include <stddef.h>
#include <stdint.h>

#include "app.h"

#define ROOK_FENCE_MAX_BYTES PROTO_MAX_COMMAND_BYTES
#define ROOK_FENCE_CHUNK 1024
#define ROOK_FENCE_CHUNKS (ROOK_FENCE_MAX_BYTES / ROOK_FENCE_CHUNK)

typedef void (*rook_fence_sink_fn)(void *ctx, uint32_t fence_seq, const char *signed_wire,
				   size_t len);

void rook_fence_set_sink(rook_fence_sink_fn fn, void *ctx);

struct rook_fence_result {
	enum reject_code code;
	bool has_ack;
	struct slot_ack ack;
	bool handed_on; /* Given to the LoRa sink */
};

/* After app_boot(): load the persisted high-water mark for this herd/server.
 * Returns the fence_seq restored (0 none). */
uint32_t rook_fence_init(const struct app *a);

struct rook_fence_result rook_fence_download(struct app *a, const char *wire, size_t len,
					     int64_t now_ms);

/* The highest fence_seq accepted (persisted; 0 none) */
uint32_t rook_fence_seq(void);

/* The persisted signed bytes of that fence into buf. Returns the length, or
 * a negative errno (-ENOENT none, -EIO corrupt, -ENOMEM cap too small). */
int rook_fence_active(char *buf, size_t cap, uint32_t *fence_seq);

void rook_fence_reset(void); /* Tests: forget the RAM state, not the store */

#endif
