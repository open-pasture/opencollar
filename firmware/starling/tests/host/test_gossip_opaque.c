/*
 * SPDX-License-Identifier: Apache-2.0
 *
 * INTEGRATION.md pilot path: inject_opaque, restore, reject-stale,
 * tampered payload → REJECT_PAYLOAD.
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
	test_keypair_t good, evil;
	uint8_t sg[32] = { 3 }, se[32] = { 9 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t body[100];
	uint8_t payload[200], bad[200];
	size_t plen = 0, blen = 0;
	oc_fh_store_ram_t ram;
	struct fence_store geo;
	struct starling_gossip g;

	test_keygen(&good, sg);
	test_keygen(&evil, se);
	memset(body, 0x5a, sizeof(body));

	store_ram_reset();
	fence_store_init(&geo);
	oc_fh_store_ram_init(&ram);
	sim_world_init(&world, 1, 11);

	starling_gossip_init(&g, &geo, &ram.api, 2, farm, false /* starling_serve OFF */,
			     sim_radio(&world, 0), test_verify, &good, payload_verify, &good,
			     sim_clock_ms, &world);
	CHECK(g.enabled);
	CHECK(g.cfg.accept_local_air == 1);
	CHECK(g.cfg.starling_serve == OC_FH_STARLING_SERVE_DEFAULT);
	CHECK(g.cfg.frag_data_max == OC_FH_DEFAULT_FRAG_DATA);

	/* Empty restore is OK */
	CHECK(starling_gossip_restore(&g) == 0);
	CHECK(!g.restored);

	make_signed_payload(payload, &plen, 7, body, sizeof(body), &good);
	CHECK(starling_gossip_inject_opaque(&g, payload, plen, 7, 100) == OC_FH_OK);
	CHECK(oc_fh_active(&g.node)->fence_seq == 7);
	CHECK(oc_fh_store_ram_hwm(&ram) == 7);

	/* Freshness field widths (NOTES.md): farm 8, seq 4, poly 32, recv 4, source 2 */
	{
		const oc_fh_freshness_t *fr = oc_fh_active(&g.node);

		CHECK(sizeof(fr->farm_id) == 8);
		CHECK(sizeof(fr->fence_seq) == 4);
		CHECK(sizeof(fr->poly_hash) == 32);
		CHECK(sizeof(fr->received_at_ms) == 4);
		CHECK(sizeof(fr->source_id) == 2);
		CHECK(memcmp(fr->farm_id, farm, 8) == 0);
	}

	/* reject-stale */
	make_signed_payload(bad, &blen, 6, body, sizeof(body), &good);
	CHECK(starling_gossip_inject_opaque(&g, bad, blen, 6, 90) == OC_FH_ERR_SEQ);

	/* Tampered payload */
	{
		uint8_t tamp[200];

		memcpy(tamp, payload, plen);
		tamp[10] ^= 0xff;
		CHECK(starling_gossip_inject_opaque(&g, tamp, plen, 8, 110) == OC_FH_ERR_PAYLOAD);
		CHECK(oc_fh_active(&g.node)->fence_seq == 7);
	}

	/* Evil key */
	make_signed_payload(bad, &blen, 8, body, sizeof(body), &evil);
	CHECK(starling_gossip_inject_opaque(&g, bad, blen, 8, 120) == OC_FH_ERR_PAYLOAD);

	/* Restore after "reboot" loads HWM + active before poll */
	{
		sim_world_t w2;
		struct starling_gossip g2;
		struct fence_store geo2;

		fence_store_init(&geo2);
		sim_world_init(&w2, 1, 22);
		starling_gossip_init(&g2, &geo2, &ram.api, 2, farm, false, sim_radio(&w2, 0),
				     test_verify, &good, payload_verify, &good, sim_clock_ms, &w2);
		CHECK(g2.restored);
		CHECK(oc_fh_active(&g2.node)->fence_seq == 7);
		CHECK(g2.node.fence_seq_hwm == 7);

		/* Still reject stale after restore */
		make_signed_payload(bad, &blen, 5, body, sizeof(body), &good);
		CHECK(starling_gossip_inject_opaque(&g2, bad, blen, 5, 50) == OC_FH_ERR_SEQ);
	}

	return test_done("gossip_opaque");
}
