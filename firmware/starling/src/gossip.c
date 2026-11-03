/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "gossip.h"

#include <string.h>

void starling_gossip_init(struct starling_gossip *g, struct fence_store *store,
			  bool starling_serve)
{
	memset(g, 0, sizeof(*g));
	g->store = store;
	g->starling_serve = starling_serve;
	g->accept_from_starling = starling_serve;
	lora_gossip_ops_stub(&g->lora);
	radio_hal_ops_stub(&g->radio);
	g->next_beacon_ms = 0;
}

void starling_gossip_inject_peer(struct starling_gossip *g, const struct lora_gossip_peer *peer,
				 const uint8_t *fence, size_t fence_len, bool from_rook)
{
	g->inject_peer = *peer;
	g->has_inject = true;
	g->inject_fence = fence;
	g->inject_fence_len = fence_len;
	g->inject_is_rook = from_rook;
}

static int adopt_from_blob(struct starling_gossip *g, const struct starling_fence_blob *blob,
			   int64_t now_utc)
{
	int rc = fence_store_offer(g->store, blob, now_utc, blob->freshness.verified);

	if (rc == 1) {
		g->adopt_count++;
	} else if (rc == 0) {
		g->reject_count++;
	}
	return rc;
}

void starling_gossip_tick(struct starling_gossip *g, int64_t now_ms, int64_t now_utc)
{
	const struct fence_freshness *local;
	struct lora_gossip_peer peer;
	bool have_peer = false;

	local = fence_store_freshness(g->store);

	if (g->lora.trickle_next_ms) {
		if (g->next_beacon_ms == 0) {
			g->next_beacon_ms = g->lora.trickle_next_ms(g->lora_ctx, now_ms);
		}
		if (now_ms >= g->next_beacon_ms && local && g->lora.beacon_send) {
			g->lora.beacon_send(g->lora_ctx, local);
			g->next_beacon_ms = g->lora.trickle_next_ms(g->lora_ctx, now_ms);
		}
	}

	if (g->has_inject) {
		peer = g->inject_peer;
		have_peer = true;
		g->has_inject = false;
	} else if (g->lora.peer_poll) {
		have_peer = g->lora.peer_poll(g->lora_ctx, &peer);
	}

	if (!have_peer) {
		return;
	}

	if (!g->accept_from_starling && !g->inject_is_rook) {
		/* One-hop fallback: ignore Starling-sourced ads when serve off. */
		g->reject_count++;
		return;
	}

	if (local && fence_freshness_cmp(&peer.freshness, local) <= 0) {
		if (g->starling_serve && fence_freshness_cmp(local, &peer.freshness) > 0 &&
		    g->store->has_active && g->lora.serve_fence) {
			const struct starling_fence_blob *a = &g->store->active;

			if (a->payload_len > 0 &&
			    g->lora.serve_fence(g->lora_ctx, &peer, a->payload, a->payload_len) ==
				    0) {
				g->serve_count++;
			}
		} else {
			g->reject_count++;
		}
		return;
	}

	/* Peer claims newer data: adopt if tests injected a full blob. */
	if (g->inject_fence && g->inject_fence_len >= sizeof(struct starling_fence_blob)) {
		struct starling_fence_blob blob;

		memcpy(&blob, g->inject_fence, sizeof(blob));
		blob.freshness = peer.freshness;
		adopt_from_blob(g, &blob, now_utc);
		g->inject_fence = NULL;
		g->inject_fence_len = 0;
		if (g->lora.trickle_heard) {
			g->lora.trickle_heard(g->lora_ctx, now_ms);
		}
	}
}
