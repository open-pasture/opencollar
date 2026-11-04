/*
 * Compiles and exercises the Rook/Starling setup from INTEGRATION.md
 * (own buffers + own oc_fh_node_t each; init + one poll).
 */
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

/* --- INTEGRATION.md Rook snippet (statics + setup body, no infinite loop) --- */
static uint8_t rook_active[2048], rook_pending[2048], rook_rx[256], rook_tx[1500];
static oc_fh_node_t rook_node;
static oc_fh_store_ram_t rook_store;

static void rook_setup(oc_radio_t *radio, const uint8_t farm[8], test_keypair_t *kp,
                       sim_world_t *w)
{
	oc_fh_config_t cfg = {0};
	oc_fh_buffers_t buf = {
		rook_active, sizeof rook_active, rook_pending, sizeof rook_pending,
		rook_rx, sizeof rook_rx, rook_tx, sizeof rook_tx
	};
	cfg.node_id = 1;
	cfg.is_rook = 1;
	cfg.starling_serve = OC_FH_STARLING_SERVE_DEFAULT; /* OFF */
	cfg.accept_local_air = 1;
	memcpy(cfg.farm_id, farm, 8);
	cfg.frag_data_max = 209;

	oc_fh_store_ram_init(&rook_store);
	oc_fh_node_init(&rook_node, &cfg, &buf, radio, test_verify, kp, sim_clock_ms, w);
	oc_fh_node_set_store(&rook_node, &rook_store.api);
	oc_fh_node_set_payload_verify(&rook_node, NULL, NULL); /* sealed path in this smoke */
	(void)oc_fh_node_restore(&rook_node);
}

/* --- INTEGRATION.md Starling snippet (own node + buffers) --- */
static uint8_t star_active[2048], star_pending[2048], star_rx[256], star_tx[1500];
static oc_fh_node_t star_node;

static void starling_setup(oc_radio_t *radio, const uint8_t farm[8], test_keypair_t *kp,
                           sim_world_t *w)
{
	oc_fh_config_t cfg = {0};
	oc_fh_buffers_t buf = {
		star_active, sizeof star_active, star_pending, sizeof star_pending,
		star_rx, sizeof star_rx, star_tx, sizeof star_tx
	};
	cfg.node_id = 2;
	cfg.is_rook = 0;
	cfg.starling_serve = OC_FH_STARLING_SERVE_DEFAULT; /* OFF = one-hop */
	cfg.accept_local_air = 1;
	memcpy(cfg.farm_id, farm, 8);
	cfg.frag_data_max = 209;

	oc_fh_node_init(&star_node, &cfg, &buf, radio, test_verify, kp, sim_clock_ms, w);
	oc_fh_node_set_payload_verify(&star_node, NULL, NULL);
}

int main(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 42 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };

	test_keygen(&kp, seed);
	sim_world_init(&world, 2, 7);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	rook_setup(sim_radio(&world, 0), farm, &kp, &world);
	starling_setup(sim_radio(&world, 1), farm, &kp, &world);

	CHECK(&rook_node != &star_node);
	CHECK(rook_node.buf.active_payload == rook_active);
	CHECK(star_node.buf.active_payload == star_active);
	CHECK(rook_node.buf.active_payload != star_node.buf.active_payload);
	CHECK(rook_node.cfg.is_rook == 1);
	CHECK(star_node.cfg.is_rook == 0);
	CHECK(rook_node.cfg.frag_data_max == 209);
	CHECK(star_node.cfg.frag_data_max == 209);

	oc_fh_node_poll(&rook_node);
	oc_fh_node_poll(&star_node);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&rook_node);
	oc_fh_node_poll(&star_node);

	CHECK(oc_fh_active(&rook_node)->fence_seq == 0);
	CHECK(oc_fh_active(&star_node)->fence_seq == 0);

	if (failures) {
		printf("test_integration_snippets: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_integration_snippets: all tests passed\n");
	return 0;
}
