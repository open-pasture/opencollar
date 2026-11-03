/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * Against PR #6 oc_fh_* (+ sim): inject_local adopt-newer, reject older,
 * and fence_seq high-water survives store reboot (no rollback).
 */
#include "test.h"

#include "fence_build.h"
#include "fence_store.h"
#include "gossip.h"
#include "opencollar/fence_node.h"
#include "sim_radio.h"
#include "store_ram.h"
#include "test_crypto.h"

#include <string.h>

typedef struct {
	uint8_t active[STARLING_FENCE_PAYLOAD_MAX];
	uint8_t pending[STARLING_FENCE_PAYLOAD_MAX];
	uint8_t rx[SIM_MAX_MTU];
	uint8_t tx[SIM_MAX_MTU];
} unused_mem_t;

int main(void)
{
	sim_world_t world;
	test_keypair_t kp;
	uint8_t seedk[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[120];
	oc_fh_built_t built;
	struct fence_store store;
	struct starling_gossip g;
	unsigned i;

	for (i = 0; i < 32; i++) {
		seedk[i] = (uint8_t)(i + 9);
	}
	test_keygen(&kp, seedk);
	memset(payload, 0xA5, sizeof(payload));

	store_ram_reset();
	fence_store_init(&store);
	CHECK(fence_store_boot(&store) == 0);

	sim_world_init(&world, 1, 42);
	starling_gossip_init(&g, &store, 2, farm, false, sim_radio(&world, 0), test_verify, &kp,
			     sim_clock_ms, &world);
	CHECK(g.enabled);

	/* frag_data_max must match the node's cfg (OC_FH_DEFAULT_FRAG_DATA). */
	CHECK(oc_fh_build_signed(&built, farm, 5, 100, payload, sizeof(payload),
				 OC_FH_DEFAULT_FRAG_DATA, test_sign, &kp) == 0);
	CHECK(starling_gossip_inject_local(&g, built.sealed, built.sealed_len, payload,
					   sizeof(payload)) == 0);
	CHECK(fence_store_hwm(&store) == 5);
	CHECK(store.has_active);
	CHECK(store.active.freshness.fence_seq == 5);
	CHECK(g.apply_count >= 1);

	/* Older seq rejected by node + must not lower hwm */
	CHECK(oc_fh_build_signed(&built, farm, 3, 90, payload, sizeof(payload),
				 OC_FH_DEFAULT_FRAG_DATA, test_sign, &kp) == 0);
	CHECK(starling_gossip_inject_local(&g, built.sealed, built.sealed_len, payload,
					   sizeof(payload)) != 0);
	CHECK(fence_store_hwm(&store) == 5);

	/* Equal rejected */
	CHECK(oc_fh_build_signed(&built, farm, 5, 101, payload, sizeof(payload),
				 OC_FH_DEFAULT_FRAG_DATA, test_sign, &kp) == 0);
	CHECK(starling_gossip_inject_local(&g, built.sealed, built.sealed_len, payload,
					   sizeof(payload)) != 0);
	CHECK(fence_store_hwm(&store) == 5);

	/* Reboot store: hwm persists; older still rejected via fence_store_offer */
	store_ram_reboot();
	{
		struct fence_store fs2;
		struct starling_fence_blob stale;

		fence_store_init(&fs2);
		CHECK(fence_store_boot(&fs2) == 0);
		CHECK(fence_store_hwm(&fs2) == 5);
		CHECK(fs2.has_active);
		memset(&stale, 0, sizeof(stale));
		stale.freshness.fence_seq = 4;
		stale.verified = true;
		stale.payload_len = 1;
		stale.n_vertices = 0;
		CHECK(fence_store_offer(&fs2, &stale, 1) == 0);
		CHECK(fence_store_hwm(&fs2) == 5);
	}

	/* Newer still accepted after reboot (fresh sim + node). */
	{
		sim_world_t world2;
		struct fence_store fs3;
		struct starling_gossip g3;

		sim_world_init(&world2, 1, 99);
		fence_store_init(&fs3);
		CHECK(fence_store_boot(&fs3) == 0);
		CHECK(fence_store_hwm(&fs3) == 5);
		starling_gossip_init(&g3, &fs3, 2, farm, false, sim_radio(&world2, 0),
				     test_verify, &kp, sim_clock_ms, &world2);
		CHECK(oc_fh_active(&g3.node)->fence_seq == 5); /* restored from NVS */
		CHECK(oc_fh_build_signed(&built, farm, 6, 110, payload, sizeof(payload),
					 OC_FH_DEFAULT_FRAG_DATA, test_sign, &kp) == 0);
		CHECK(starling_gossip_inject_local(&g3, built.sealed, built.sealed_len, payload,
						   sizeof(payload)) == 0);
		CHECK(fence_store_hwm(&fs3) == 6);
	}

	return test_done("gossip_hwm");
}
