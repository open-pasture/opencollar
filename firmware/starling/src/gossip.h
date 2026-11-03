/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Starling fence-gossip policy on top of op-fw-proto stubs.
 *
 * starling_serve off: receive only from Rooks (one-hop fallback).
 * starling_serve on:  also serve neighbors (multi-hop).
 */
#ifndef STARLING_GOSSIP_H
#define STARLING_GOSSIP_H

#include <stdbool.h>
#include <stdint.h>

#include "fence_gossip.h"
#include "fence_store.h"
#include "radio_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

struct starling_gossip {
	struct fence_store *store;
	struct lora_gossip_ops lora;
	void *lora_ctx;
	struct radio_hal radio;
	bool starling_serve; /* default off */
	bool accept_from_starling; /* when serve off, only adopt from Rook sources */
	int64_t next_beacon_ms;
	/* Host-test injection of peers (bypasses radio). */
	struct lora_gossip_peer inject_peer;
	bool has_inject;
	const uint8_t *inject_fence;
	size_t inject_fence_len;
	bool inject_is_rook;
	/* Observability for tests */
	unsigned adopt_count;
	unsigned serve_count;
	unsigned reject_count;
};

void starling_gossip_init(struct starling_gossip *g, struct fence_store *store,
			  bool starling_serve);

/* Inject a peer advertisement + optional fence bytes (host tests). */
void starling_gossip_inject_peer(struct starling_gossip *g, const struct lora_gossip_peer *peer,
				 const uint8_t *fence, size_t fence_len, bool from_rook);

/*
 * Run one gossip step: Trickle beacon if due; poll peers; adopt newer
 * (after verify via fence_store_offer); serve if we are newer and serve on.
 */
void starling_gossip_tick(struct starling_gossip *g, int64_t now_ms, int64_t now_utc);

#ifdef __cplusplus
}
#endif

#endif
