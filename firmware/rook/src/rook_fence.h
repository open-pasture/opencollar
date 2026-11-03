/* SPDX-License-Identifier: Apache-2.0 */
/*
 * A signed fence downloaded over LTE-M: verified and stored through the
 * existing app_boundary() path (Ed25519 in command.c, slots in NVS), then
 * handed, still as the signed bytes, to the LoRa side for gossip to
 * Starlings. fence_seq is the server-issued monotonic number: in v1 it is
 * the command's `version`. Only a fence that verified and was stored
 * (received or applied) is handed on, and only when fence_seq rises.
 *
 * The LoRa hand-off is a thin hook: op-fw-proto's portable library
 * (firmware/lora, in progress) registers a sink with rook_fence_set_sink().
 * Nothing is written into firmware/lora from here.
 *
 * Call from the main thread only (Ed25519 needs its 8 KB stack).
 */
#ifndef ROOK_FENCE_H
#define ROOK_FENCE_H

#include <stddef.h>
#include <stdint.h>

#include "app.h"

typedef void (*rook_fence_sink_fn)(void *ctx, uint32_t fence_seq, const char *signed_wire,
				   size_t len);

void rook_fence_set_sink(rook_fence_sink_fn fn, void *ctx);

struct rook_fence_result {
	enum reject_code code;
	bool has_ack;
	struct slot_ack ack;
	bool handed_on; /* Given to the LoRa sink */
};

struct rook_fence_result rook_fence_download(struct app *a, const char *wire, size_t len,
					     int64_t now_ms);

/* The highest fence_seq handed on since boot (0 none) */
uint32_t rook_fence_seq(void);
void rook_fence_reset(void); /* Tests */

#endif
