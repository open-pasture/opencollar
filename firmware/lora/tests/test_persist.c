/*
 * Persistence: HWM + active blob survive reboot; older/equal rejected; can serve.
 */
#include "fence_build.h"
#include "opencollar/fence_node.h"
#include "opencollar/fence_store.h"
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
	uint8_t rx[512];
	uint8_t tx[1500];
} node_mem_t;

static void setup(oc_fh_node_t *n, oc_fh_config_t *cfg, node_mem_t *mem, oc_radio_t *radio,
                  test_keypair_t *kp, sim_world_t *w, oc_fh_store_t *store)
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
	oc_fh_node_set_store(n, store);
}

int main(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 1 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[200], older[200];
	oc_fh_built_t built, built_old;
	oc_fh_store_ram_t ram;
	oc_fh_node_t n1, n2, peer;
	oc_fh_config_t cfg, cfg_peer;
	node_mem_t m1, m2, mp;
	int t;

	test_keygen(&kp, seed);
	memset(payload, 0x11, sizeof(payload));
	memset(older, 0x22, sizeof(older));
	oc_fh_store_ram_init(&ram);

	sim_world_init(&world, 2, 42);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	memset(&cfg, 0, sizeof(cfg));
	cfg.node_id = 1;
	cfg.is_rook = 1;
	memcpy(cfg.farm_id, farm, 8);
	cfg.frag_data_max = 50;
	cfg.trickle_imin_ms = 40;
	cfg.trickle_imax_ms = 200;
	cfg_peer = cfg;
	cfg_peer.node_id = 2;
	cfg_peer.is_rook = 0;

	setup(&n1, &cfg, &m1, sim_radio(&world, 0), &kp, &world, &ram.api);
	CHECK(oc_fh_build_signed(&built, farm, 10, 10, payload, sizeof(payload), 50, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&n1, built.sealed, built.sealed_len, payload, sizeof(payload)) ==
	      OC_FH_OK);
	CHECK(oc_fh_active(&n1)->fence_seq == 10);
	CHECK(ram.hwm == 10);
	CHECK(oc_fh_store_ram_have_active(&ram));

	/* Simulate reboot: new node instance, same store. */
	memset(&n2, 0, sizeof(n2));
	memset(&m2, 0, sizeof(m2));
	setup(&n2, &cfg, &m2, sim_radio(&world, 0), &kp, &world, &ram.api);
	CHECK(oc_fh_node_restore(&n2) == OC_FH_OK);
	CHECK(oc_fh_active(&n2)->fence_seq == 10);
	CHECK(memcmp(m2.active, payload, sizeof(payload)) == 0);

	CHECK(oc_fh_build_signed(&built_old, farm, 9, 9, older, sizeof(older), 50, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&n2, built_old.sealed, built_old.sealed_len, older,
	                         sizeof(older)) == OC_FH_ERR_SEQ);
	CHECK(oc_fh_inject_local(&n2, built.sealed, built.sealed_len, payload, sizeof(payload)) ==
	      OC_FH_ERR_SEQ);
	CHECK(oc_fh_active(&n2)->fence_seq == 10);

	/* Restored fence can be served to a peer. */
	setup(&peer, &cfg_peer, &mp, sim_radio(&world, 1), &kp, &world, NULL);
	for (t = 0; t < 2000; t++) {
		oc_fh_node_poll(&n2);
		oc_fh_node_poll(&peer);
		sim_world_advance(&world, 5);
		if (oc_fh_active(&peer)->fence_seq == 10) {
			break;
		}
	}
	CHECK(oc_fh_active(&peer)->fence_seq == 10);

	/* Failed save: fence must not apply in RAM; old active kept. */
	{
		uint8_t newer[200];
		oc_fh_built_t built_new;
		memset(newer, 0x33, sizeof(newer));
		CHECK(oc_fh_build_signed(&built_new, farm, 11, 11, newer, sizeof(newer), 50,
		                         test_sign, &kp) == 0);
		ram.fail_next_save = 1;
		CHECK(oc_fh_inject_local(&n2, built_new.sealed, built_new.sealed_len, newer,
		                         sizeof(newer)) == OC_FH_ERR_STORE);
		CHECK(oc_fh_active(&n2)->fence_seq == 10);
		CHECK(memcmp(m2.active, payload, sizeof(payload)) == 0);
		CHECK(oc_fh_stats(&n2)->persist_fail >= 1);
	}

	/* Torn A/B write: primary CRC bad → load falls back to other copy. */
	{
		oc_fh_store_ram_t ram2;
		oc_fh_node_t na, nb;
		node_mem_t ma, mb;
		uint8_t p_a[100], p_b[100];
		oc_fh_built_t ba, bb;

		memset(p_a, 0xA1, sizeof(p_a));
		memset(p_b, 0xB2, sizeof(p_b));
		oc_fh_store_ram_init(&ram2);
		memset(&na, 0, sizeof(na));
		memset(&ma, 0, sizeof(ma));
		setup(&na, &cfg, &ma, sim_radio(&world, 0), &kp, &world, &ram2.api);
		CHECK(oc_fh_build_signed(&ba, farm, 20, 20, p_a, sizeof(p_a), 50, test_sign,
		                         &kp) == 0);
		CHECK(oc_fh_inject_local(&na, ba.sealed, ba.sealed_len, p_a, sizeof(p_a)) ==
		      OC_FH_OK);
		CHECK(oc_fh_active(&na)->fence_seq == 20);

		CHECK(oc_fh_build_signed(&bb, farm, 21, 21, p_b, sizeof(p_b), 50, test_sign,
		                         &kp) == 0);
		ram2.tear_next_save = 1;
		/* Persist reports OK (driver), RAM applies 21; flash primary torn. */
		CHECK(oc_fh_inject_local(&na, bb.sealed, bb.sealed_len, p_b, sizeof(p_b)) ==
		      OC_FH_OK);
		CHECK(oc_fh_active(&na)->fence_seq == 21);

		memset(&nb, 0, sizeof(nb));
		memset(&mb, 0, sizeof(mb));
		setup(&nb, &cfg, &mb, sim_radio(&world, 0), &kp, &world, &ram2.api);
		CHECK(oc_fh_node_restore(&nb) == OC_FH_OK);
		/* Fallback to intact A/B copy (seq 20). */
		CHECK(oc_fh_active(&nb)->fence_seq == 20);
		CHECK(memcmp(mb.active, p_a, sizeof(p_a)) == 0);
	}

	if (failures) {
		printf("test_persist: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_persist: all tests passed\n");
	return 0;
}
