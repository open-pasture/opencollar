/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * STUB — owned by op-fw-proto (firmware/lora). Starling calls this through
 * radio_hal. Replace includes with the real library when that PR lands.
 *
 * Trickle-timed beacons advertise fence freshness; on hearing a newer peer
 * the collar requests/adopts the fence (after signature verify). When
 * starling_serve is on and we are newer, we serve the neighbor.
 */
#ifndef OPENCOLLAR_STUB_LORA_FENCE_GOSSIP_H
#define OPENCOLLAR_STUB_LORA_FENCE_GOSSIP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "fence_freshness.h"

#ifdef __cplusplus
extern "C" {
#endif

struct lora_gossip_peer {
	uint8_t id[FENCE_SOURCE_ID_LEN];
	uint8_t id_len;
	struct fence_freshness freshness;
};

struct lora_gossip_ops {
	/* Send a freshness beacon (opaque bytes owned by op-fw-proto). */
	int (*beacon_send)(void *ctx, const struct fence_freshness *local);
	/* Poll for a heard peer advertisement; return true if one is ready. */
	bool (*peer_poll)(void *ctx, struct lora_gossip_peer *out);
	/* Request full fence from peer; bytes written to buf, length in *len. */
	int (*fetch_fence)(void *ctx, const struct lora_gossip_peer *peer, uint8_t *buf,
			   size_t cap, size_t *len);
	/* Serve our fence bytes to a peer that needs an update. */
	int (*serve_fence)(void *ctx, const struct lora_gossip_peer *peer, const uint8_t *fence,
			   size_t fence_len);
	/* Trickle: next due time (ms uptime) for beacon or listen. */
	int64_t (*trickle_next_ms)(void *ctx, int64_t now_ms);
	void (*trickle_heard)(void *ctx, int64_t now_ms);
};

/* No-op defaults for host tests and builds before op-fw-proto lands. */
int lora_gossip_stub_beacon_send(void *ctx, const struct fence_freshness *local);
bool lora_gossip_stub_peer_poll(void *ctx, struct lora_gossip_peer *out);
int lora_gossip_stub_fetch_fence(void *ctx, const struct lora_gossip_peer *peer, uint8_t *buf,
				 size_t cap, size_t *len);
int lora_gossip_stub_serve_fence(void *ctx, const struct lora_gossip_peer *peer,
				 const uint8_t *fence, size_t fence_len);
int64_t lora_gossip_stub_trickle_next_ms(void *ctx, int64_t now_ms);
void lora_gossip_stub_trickle_heard(void *ctx, int64_t now_ms);

void lora_gossip_ops_stub(struct lora_gossip_ops *ops);

#ifdef __cplusplus
}
#endif

#endif
