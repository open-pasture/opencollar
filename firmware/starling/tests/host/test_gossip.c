/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * adopt-newer from Rook, push-to-older when starling_serve on,
 * reject Starling peers when serve off, reject stale.
 */
#include "test.h"

#include "fence_demo.h"
#include "gossip.h"
#include "store_ram.h"

static int serve_calls;
static uint32_t last_served_seq_hint;

static int mock_serve(void *ctx, const struct lora_gossip_peer *peer, const uint8_t *fence,
		      size_t fence_len)
{
	(void)ctx;
	(void)peer;
	(void)fence_len;
	serve_calls++;
	if (fence_len >= 4) {
		last_served_seq_hint = fence[0];
	}
	(void)last_served_seq_hint;
	return 0;
}

static struct starling_fence_blob make_blob(uint32_t seq)
{
	struct starling_fence_blob b;

	memset(&b, 0, sizeof(b));
	b.freshness.fence_seq = seq;
	b.freshness.issued_at = 1000 + (int64_t)seq;
	b.freshness.verified = true;
	b.n_vertices = STARLING_DEMO_FENCE_N;
	memcpy(b.vertices, STARLING_DEMO_FENCE, sizeof(STARLING_DEMO_FENCE));
	b.warn_m = 5.0;
	b.hysteresis_m = 1.0;
	b.payload[0] = (uint8_t)seq;
	b.payload_len = 1;
	return b;
}

int main(void)
{
	struct fence_store fs;
	struct starling_gossip g;
	struct starling_fence_blob local, newer;
	struct lora_gossip_peer peer;

	store_ram_reset();
	fence_store_init(&fs, NULL);
	fence_store_boot(&fs);

	local = make_blob(1);
	CHECK(fence_store_offer(&fs, &local, 2000, true) == 1);

	/* serve off: adopt newer from Rook */
	starling_gossip_init(&g, &fs, false);
	newer = make_blob(3);
	memset(&peer, 0, sizeof(peer));
	peer.freshness = newer.freshness;
	peer.id[0] = 1;
	peer.id_len = 1;
	starling_gossip_inject_peer(&g, &peer, (const uint8_t *)&newer, sizeof(newer), true);
	starling_gossip_tick(&g, 100, 2001);
	CHECK(g.adopt_count == 1);
	CHECK(fs.active.freshness.fence_seq == 3);

	/* serve off: reject Starling-sourced peer */
	{
		struct starling_fence_blob even_newer = make_blob(4);

		peer.freshness = even_newer.freshness;
		starling_gossip_inject_peer(&g, &peer, (const uint8_t *)&even_newer,
					    sizeof(even_newer), false);
		starling_gossip_tick(&g, 200, 2002);
		CHECK(fs.active.freshness.fence_seq == 3);
		CHECK(g.reject_count >= 1);
	}

	/* stale / equal rejected */
	{
		struct starling_fence_blob stale = make_blob(2);

		peer.freshness = stale.freshness;
		starling_gossip_inject_peer(&g, &peer, (const uint8_t *)&stale, sizeof(stale),
					    true);
		starling_gossip_tick(&g, 300, 2003);
		CHECK(fs.active.freshness.fence_seq == 3);
	}

	/* starling_serve on: push to older neighbor */
	starling_gossip_init(&g, &fs, true);
	g.lora.serve_fence = mock_serve;
	serve_calls = 0;
	memset(&peer, 0, sizeof(peer));
	peer.freshness.fence_seq = 1; /* older than our 3 */
	peer.id[0] = 9;
	peer.id_len = 1;
	starling_gossip_inject_peer(&g, &peer, NULL, 0, false);
	starling_gossip_tick(&g, 400, 2004);
	CHECK(serve_calls == 1);
	CHECK(g.serve_count == 1);

	return test_done("gossip");
}
