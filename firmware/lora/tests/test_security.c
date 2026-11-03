/*
 * Tamper reject, rollback reject, duplicate/reorder fragments, resume via NEED.
 */
#include "fence_build.h"
#include "opencollar/fence_node.h"
#include "sim_radio.h"
#include "test_crypto.h"

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
	uint8_t rx[SIM_MAX_MTU];
	uint8_t tx[SIM_MAX_MTU];
} node_mem_t;

static void setup_node(oc_fh_node_t *n, oc_fh_config_t *cfg, node_mem_t *mem, oc_radio_t *radio,
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
}

static void poll_pair(oc_fh_node_t *a, oc_fh_node_t *b, sim_world_t *w, int steps)
{
	int t;
	for (t = 0; t < steps; t++) {
		oc_fh_node_poll(a);
		oc_fh_node_poll(b);
		sim_world_advance(w, 5);
	}
}

static void test_forged_manifest(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t good, evil;
	uint8_t sg[32] = { 1 }, se[32] = { 2 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[120];
	oc_fh_built_t built;
	oc_fh_node_t rook, star;
	oc_fh_config_t cr, cs;
	node_mem_t mr, ms;

	test_keygen(&good, sg);
	test_keygen(&evil, se);
	memset(payload, 0x7e, sizeof(payload));
	sim_world_init(&world, 2, 5);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	memset(&cr, 0, sizeof(cr));
	cr.node_id = 1;
	cr.is_rook = 1;
	memcpy(cr.farm_id, farm, 8);
	cr.frag_data_max = 40;
	cr.trickle_imin_ms = 30;
	cr.trickle_imax_ms = 200;
	cs = cr;
	cs.node_id = 2;
	cs.is_rook = 0;

	/* Starling trusts `good`; Rook will inject an evil-signed fence into radio path
	 * by building with evil and pushing frames manually... simpler: inject_local on
	 * rook with evil key fails verify on star when served — build with evil, but
	 * rook's verify is also good key so inject_local fails. Instead seal with evil
	 * offline and feed via radio send. */
	setup_node(&rook, &cr, &mr, sim_radio(&world, 0), &good, &world);
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &good, &world);

	CHECK(oc_fh_build_signed(&built, farm, 9, 9, payload, sizeof(payload), 40, test_sign,
	                         &evil) == 0);
	/* Deliver forged sealed manifest directly into star's radio RX by send from rook
	 * radio after bypassing inject (raw send). */
	CHECK(oc_radio_send(sim_radio(&world, 0), built.sealed, built.sealed_len, NULL) ==
	      OC_RADIO_OK);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&star);
	CHECK(oc_fh_active(&star)->fence_seq == 0);
	CHECK(oc_fh_stats(&star)->reject_sig >= 1);
}

static void test_rollback(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 8 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t p_new[100], p_old[100];
	oc_fh_built_t b_new, b_old;
	oc_fh_node_t rook, star;
	oc_fh_config_t cr, cs;
	node_mem_t mr, ms;

	test_keygen(&kp, seed);
	memset(p_new, 1, sizeof(p_new));
	memset(p_old, 2, sizeof(p_old));
	sim_world_init(&world, 2, 8);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	memset(&cr, 0, sizeof(cr));
	cr.node_id = 1;
	cr.is_rook = 1;
	memcpy(cr.farm_id, farm, 8);
	cr.frag_data_max = 40;
	cr.trickle_imin_ms = 30;
	cr.trickle_imax_ms = 200;
	cs = cr;
	cs.node_id = 2;
	cs.is_rook = 0;
	setup_node(&rook, &cr, &mr, sim_radio(&world, 0), &kp, &world);
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);

	CHECK(oc_fh_build_signed(&b_new, farm, 20, 20, p_new, sizeof(p_new), 40, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_build_signed(&b_old, farm, 19, 19, p_old, sizeof(p_old), 40, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&star, b_new.sealed, b_new.sealed_len, p_new, sizeof(p_new)) ==
	      0);
	CHECK(oc_fh_active(&star)->fence_seq == 20);
	/* Attempt rollback inject */
	CHECK(oc_fh_inject_local(&star, b_old.sealed, b_old.sealed_len, p_old, sizeof(p_old)) ==
	      -3);
	CHECK(oc_fh_active(&star)->fence_seq == 20);
	/* Attempt equal seq */
	CHECK(oc_fh_inject_local(&star, b_new.sealed, b_new.sealed_len, p_new, sizeof(p_new)) ==
	      -3);

	/* Over the air: rook holds old, star holds new — star must not roll back. */
	CHECK(oc_fh_inject_local(&rook, b_old.sealed, b_old.sealed_len, p_old, sizeof(p_old)) ==
	      0);
	poll_pair(&rook, &star, &world, 500);
	CHECK(oc_fh_active(&star)->fence_seq == 20);
}

static void test_dup_reorder_resume(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 4 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[250];
	oc_fh_built_t built;
	oc_fh_node_t rook, star;
	oc_fh_config_t cr, cs;
	node_mem_t mr, ms;
	unsigned i;

	test_keygen(&kp, seed);
	for (i = 0; i < sizeof(payload); i++) {
		payload[i] = (uint8_t)i;
	}
	sim_world_init(&world, 2, 44);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 20;
	link.reorder_pct = 40;
	link.duplicate_pct = 40;
	link.latency_ms = 2;
	link.latency_jitter_ms = 8;
	sim_world_set_fully_connected(&world, &link);

	memset(&cr, 0, sizeof(cr));
	cr.node_id = 1;
	cr.is_rook = 1;
	memcpy(cr.farm_id, farm, 8);
	cr.frag_data_max = 50;
	cr.trickle_imin_ms = 25;
	cr.trickle_imax_ms = 200;
	cs = cr;
	cs.node_id = 2;
	cs.is_rook = 0;
	setup_node(&rook, &cr, &mr, sim_radio(&world, 0), &kp, &world);
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);

	CHECK(oc_fh_build_signed(&built, farm, 3, 3, payload, sizeof(payload), 50, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&rook, built.sealed, built.sealed_len, payload,
	                         sizeof(payload)) == 0);

	/* Interrupt: partition mid-transfer, then heal (resume via NEED). */
	poll_pair(&rook, &star, &world, 40);
	sim_world_partition(&world, 0, 1, 0);
	poll_pair(&rook, &star, &world, 40);
	sim_world_partition(&world, 0, 1, 1);
	poll_pair(&rook, &star, &world, 4000);
	CHECK(oc_fh_active(&star)->fence_seq == 3);
	CHECK(memcmp(ms.active, payload, sizeof(payload)) == 0);
}

int main(void)
{
	test_forged_manifest();
	test_rollback();
	test_dup_reorder_resume();
	if (failures) {
		printf("test_security: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_security: all tests passed\n");
	return 0;
}
