/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * No-op LoRa fence-gossip stubs until op-fw-proto publishes firmware/lora.
 */
#include "fence_gossip.h"

#include <string.h>

int lora_gossip_stub_beacon_send(void *ctx, const struct fence_freshness *local)
{
	(void)ctx;
	(void)local;
	return 0;
}

bool lora_gossip_stub_peer_poll(void *ctx, struct lora_gossip_peer *out)
{
	(void)ctx;
	(void)out;
	return false;
}

int lora_gossip_stub_fetch_fence(void *ctx, const struct lora_gossip_peer *peer, uint8_t *buf,
				 size_t cap, size_t *len)
{
	(void)ctx;
	(void)peer;
	(void)buf;
	(void)cap;
	(void)len;
	return -1;
}

int lora_gossip_stub_serve_fence(void *ctx, const struct lora_gossip_peer *peer,
				 const uint8_t *fence, size_t fence_len)
{
	(void)ctx;
	(void)peer;
	(void)fence;
	(void)fence_len;
	return -1;
}

int64_t lora_gossip_stub_trickle_next_ms(void *ctx, int64_t now_ms)
{
	(void)ctx;
	/* PLACEHOLDER: 60 s beacon interval until Trickle parameters land. */
	return now_ms + 60000;
}

void lora_gossip_stub_trickle_heard(void *ctx, int64_t now_ms)
{
	(void)ctx;
	(void)now_ms;
}

void lora_gossip_ops_stub(struct lora_gossip_ops *ops)
{
	memset(ops, 0, sizeof(*ops));
	ops->beacon_send = lora_gossip_stub_beacon_send;
	ops->peer_poll = lora_gossip_stub_peer_poll;
	ops->fetch_fence = lora_gossip_stub_fetch_fence;
	ops->serve_fence = lora_gossip_stub_serve_fence;
	ops->trickle_next_ms = lora_gossip_stub_trickle_next_ms;
	ops->trickle_heard = lora_gossip_stub_trickle_heard;
}
