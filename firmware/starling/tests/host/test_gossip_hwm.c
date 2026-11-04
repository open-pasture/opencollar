/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * Against PR #6 oc_fh_* (+ sim + oc_fh_store_ram):
 *   restore after reboot, inject_opaque adopt-newer, reject-stale.
 */
#include "test.h"

#include "gossip.h"
#include "opencollar/fence_node.h"
#include "opencollar/fence_store.h"
#include "sim_radio.h"
#include "store_ram.h"
#include "test_crypto.h"

#include "monocypher-ed25519.h"

#include <string.h>

/* Fake v1-style: payload = version_be32 || body || sig[64]. */
static void make_signed_payload(uint8_t *out, size_t *out_len, uint32_t version,
				const uint8_t *body, size_t body_len, test_keypair_t *kp)
{
	out[0] = (uint8_t)(version >> 24);
	out[1] = (uint8_t)(version >> 16);
	out[2] = (uint8_t)(version >> 8);
	out[3] = (uint8_t)version;
	memcpy(out + 4, body, body_len);
	crypto_ed25519_sign(out + 4 + body_len, kp->sk, out, 4 + body_len);
	*out_len = 4 + body_len + 64;
}

static int payload_verify(const uint8_t *payload, size_t len, uint32_t fence_seq, void *ctx)
{
	const test_keypair_t *kp = ctx;
	uint32_t ver;

	if (len < 4 + 64) {
		return -1;
	}
	ver = ((uint32_t)payload[0] << 24) | ((uint32_t)payload[1] << 16) |
	      ((uint32_t)payload[2] << 8) | (uint32_t)payload[3];
	if (ver != fence_seq) {
		return -1;
	}
	return crypto_ed25519_check(payload + len - 64, kp->pk, payload, len - 64);
}

int main(void)
{
	sim_world_t world;
	test_keypair_t kp;
	uint8_t seedk[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t body[80];
	uint8_t payload[200];
	size_t plen = 0;
	oc_fh_store_ram_t ram;
	struct fence_store geo;
	struct starling_gossip g;
	unsigned i;

	for (i = 0; i < 32; i++) {
		seedk[i] = (uint8_t)(i + 9);
	}
	test_keygen(&kp, seedk);
	memset(body, 0xA5, sizeof(body));

	store_ram_reset();
	fence_store_init(&geo);
	CHECK(fence_store_boot(&geo) == 0);
	oc_fh_store_ram_init(&ram);

	sim_world_init(&world, 1, 42);
	starling_gossip_init(&g, &geo, &ram.api, 2, farm, false, sim_radio(&world, 0),
			     test_verify, &kp, payload_verify, &kp, sim_clock_ms, &world);
	CHECK(g.enabled);

	make_signed_payload(payload, &plen, 5, body, sizeof(body), &kp);
	CHECK(starling_gossip_inject_opaque(&g, payload, plen, 5, 100) == OC_FH_OK);
	CHECK(oc_fh_store_ram_hwm(&ram) == 5);
	CHECK(oc_fh_active(&g.node)->fence_seq == 5);
	CHECK(g.apply_count >= 1);

	/* Older seq rejected — HWM unchanged */
	{
		uint8_t stale[200];
		size_t slen = 0;

		make_signed_payload(stale, &slen, 3, body, sizeof(body), &kp);
		CHECK(starling_gossip_inject_opaque(&g, stale, slen, 3, 90) == OC_FH_ERR_SEQ);
		CHECK(oc_fh_store_ram_hwm(&ram) == 5);
		CHECK(g.reject_seq_count >= 1);
	}

	/* Equal rejected */
	{
		uint8_t same[200];
		size_t slen = 0;

		make_signed_payload(same, &slen, 5, body, sizeof(body), &kp);
		CHECK(starling_gossip_inject_opaque(&g, same, slen, 5, 101) == OC_FH_ERR_SEQ);
		CHECK(oc_fh_store_ram_hwm(&ram) == 5);
	}

	/* Reboot node: restore from oc_fh_store_ram before any poll */
	{
		sim_world_t world2;
		struct starling_gossip g2;
		struct fence_store geo2;

		fence_store_init(&geo2);
		sim_world_init(&world2, 1, 99);
		starling_gossip_init(&g2, &geo2, &ram.api, 2, farm, false, sim_radio(&world2, 0),
				     test_verify, &kp, payload_verify, &kp, sim_clock_ms, &world2);
		CHECK(g2.restored);
		CHECK(oc_fh_active(&g2.node)->fence_seq == 5);
		CHECK(oc_fh_store_ram_hwm(&ram) == 5);

		/* Stale still rejected after restore */
		{
			uint8_t stale[200];
			size_t slen = 0;

			make_signed_payload(stale, &slen, 4, body, sizeof(body), &kp);
			CHECK(starling_gossip_inject_opaque(&g2, stale, slen, 4, 95) ==
			      OC_FH_ERR_SEQ);
			CHECK(oc_fh_store_ram_hwm(&ram) == 5);
		}

		/* Newer accepted */
		make_signed_payload(payload, &plen, 6, body, sizeof(body), &kp);
		CHECK(starling_gossip_inject_opaque(&g2, payload, plen, 6, 110) == OC_FH_OK);
		CHECK(oc_fh_store_ram_hwm(&ram) == 6);
		CHECK(oc_fh_active(&g2.node)->fence_seq == 6);
	}

	return test_done("gossip_hwm");
}
