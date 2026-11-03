/*
 * PILOT opaque-payload path: unsigned local manifest; payload Ed25519 verify.
 */
#include "opencollar/fence_node.h"
#include "sim_radio.h"
#include "test_crypto.h"

#include "monocypher-ed25519.h"

#include <stdio.h>
#include <string.h>

static int failures;
#define CHECK(c)                                                                       \
	do {                                                                           \
		if (!(c)) {                                                            \
			printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c);             \
			failures++;                                                    \
		}                                                                      \
	} while (0)

typedef struct {
	uint8_t active[OC_FH_MAX_PAYLOAD];
	uint8_t pending[OC_FH_MAX_PAYLOAD];
	uint8_t rx[512];
	uint8_t tx[1500];
} node_mem_t;

/* Fake v1-style: payload = body || sig[64]; body starts with version u32 BE. */
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

static void setup(oc_fh_node_t *n, oc_fh_config_t *cfg, node_mem_t *mem, oc_radio_t *radio,
                  test_keypair_t *kp, sim_world_t *w)
{
	oc_fh_buffers_t buf;
	buf.active_payload = mem->active;
	buf.active_cap = sizeof(mem->active);
	buf.pending_payload = mem->pending;
	buf.pending_cap = sizeof(mem->pending);
	buf.rx_scratch = mem->rx;
	buf.rx_scratch_cap = sizeof(mem->rx);
	buf.tx_scratch = mem->tx;
	buf.tx_scratch_cap = sizeof(mem->tx);
	oc_fh_node_init(n, cfg, &buf, radio, test_verify, kp, sim_clock_ms, w);
	oc_fh_node_set_payload_verify(n, payload_verify, kp);
}

int main(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t good, evil;
	uint8_t sg[32] = { 3 }, se[32] = { 9 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t body[100];
	uint8_t payload[200], bad[200];
	size_t plen = 0, blen = 0;
	oc_fh_node_t rook, star;
	oc_fh_config_t cr, cs;
	node_mem_t mr, ms;
	int t;

	test_keygen(&good, sg);
	test_keygen(&evil, se);
	memset(body, 0x5a, sizeof(body));
	make_signed_payload(payload, &plen, 7, body, sizeof(body), &good);

	sim_world_init(&world, 2, 11);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);
	/* Local manifests for this payload size are modest; keep default MTU. */

	memset(&cr, 0, sizeof(cr));
	cr.node_id = 1;
	cr.is_rook = 1;
	cr.accept_local_air = 1; /* pilot: air MANIFEST_LOCAL allowed */
	memcpy(cr.farm_id, farm, 8);
	cr.frag_data_max = 40;
	cr.trickle_imin_ms = 30;
	cr.trickle_imax_ms = 200;
	cs = cr;
	cs.node_id = 2;
	cs.is_rook = 0;

	setup(&rook, &cr, &mr, sim_radio(&world, 0), &good, &world);
	setup(&star, &cs, &ms, sim_radio(&world, 1), &good, &world);

	CHECK(oc_fh_inject_opaque(&rook, payload, plen, 7, 100) == OC_FH_OK);
	CHECK(oc_fh_active(&rook)->fence_seq == 7);

	for (t = 0; t < 3000; t++) {
		oc_fh_node_poll(&rook);
		oc_fh_node_poll(&star);
		sim_world_advance(&world, 5);
		if (oc_fh_active(&star)->fence_seq == 7) {
			break;
		}
	}
	CHECK(oc_fh_active(&star)->fence_seq == 7);
	CHECK(memcmp(ms.active, payload, plen) == 0);

	/* Older version rejected. */
	make_signed_payload(bad, &blen, 6, body, sizeof(body), &good);
	CHECK(oc_fh_inject_opaque(&star, bad, blen, 6, 90) == OC_FH_ERR_SEQ);

	/* Tampered payload fails payload_verify on inject. */
	{
		uint8_t tamp[200];
		size_t tlen = plen;
		memcpy(tamp, payload, plen);
		tamp[10] ^= 0xff;
		CHECK(oc_fh_inject_opaque(&rook, tamp, tlen, 8, 110) == OC_FH_ERR_PAYLOAD);
		CHECK(oc_fh_active(&rook)->fence_seq == 7);
	}

	/* Evil-signed payload rejected. */
	make_signed_payload(bad, &blen, 8, body, sizeof(body), &evil);
	CHECK(oc_fh_inject_opaque(&rook, bad, blen, 8, 120) == OC_FH_ERR_PAYLOAD);

	if (failures) {
		printf("test_pilot: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_pilot: all tests passed\n");
	return 0;
}
