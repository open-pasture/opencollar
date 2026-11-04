/*
 * Milestone (b): 3-node chain Rook — S1 — S2 (S2 out of Rook range).
 * starling_serve=1. Also: newer mid-propagation, partition heal.
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

static void poll_all(oc_fh_node_t *nodes, int n, sim_world_t *w, int steps, int step_ms)
{
	int t, i;
	for (t = 0; t < steps; t++) {
		for (i = 0; i < n; i++) {
			oc_fh_node_poll(&nodes[i]);
		}
		sim_world_advance(w, (uint32_t)step_ms);
	}
}

static int chain_propagate(uint64_t seed, uint16_t loss_pct)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seedk[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[350];
	oc_fh_built_t built;
	oc_fh_node_t nodes[3];
	oc_fh_config_t cfg[3];
	node_mem_t mem[3];
	unsigned i;

	for (i = 0; i < 32; i++) {
		seedk[i] = (uint8_t)(i ^ (seed & 0xff));
	}
	test_keygen(&kp, seedk);
	for (i = 0; i < sizeof(payload); i++) {
		payload[i] = (uint8_t)(i + 3);
	}

	sim_world_init(&world, 3, seed);
	memset(&link, 0, sizeof(link));
	link.loss_pct = loss_pct;
	link.burst_pct = 2;
	link.burst_len = 2;
	link.reorder_pct = 5;
	link.duplicate_pct = 2;
	link.latency_ms = 2;
	link.latency_jitter_ms = 2;
	sim_world_set_chain(&world, &link); /* 0-1, 1-2; NOT 0-2 */

	for (i = 0; i < 3; i++) {
		memset(&cfg[i], 0, sizeof(cfg[i]));
		cfg[i].node_id = (uint16_t)(i + 1);
		cfg[i].is_rook = (i == 0) ? 1 : 0;
		cfg[i].starling_serve = 1; /* multi-hop */
		memcpy(cfg[i].farm_id, farm, 8);
		cfg[i].frag_data_max = 64;
		cfg[i].trickle_imin_ms = 40;
		cfg[i].trickle_imax_ms = 400;
		cfg[i].trickle_k = 1;
		setup_node(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp,
		           &world);
	}

	if (oc_fh_build_signed(&built, farm, 10, 1700000100u, payload, sizeof(payload), 64,
	                       test_sign, &kp) != 0) {
		return 0;
	}
	if (oc_fh_inject_local(&nodes[0], built.sealed, built.sealed_len, payload,
	                       sizeof(payload)) != 0) {
		return 0;
	}

	poll_all(nodes, 3, &world, 8000, 5); /* up to 40s sim time */
	return oc_fh_active(&nodes[0])->fence_seq == 10 &&
	       oc_fh_active(&nodes[1])->fence_seq == 10 &&
	       oc_fh_active(&nodes[2])->fence_seq == 10;
}

static void test_newer_supersedes(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seedk[32] = { 9 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t p1[200], p2[220];
	oc_fh_built_t b1, b2;
	oc_fh_node_t nodes[3];
	oc_fh_config_t cfg[3];
	node_mem_t mem[3];
	unsigned i;

	test_keygen(&kp, seedk);
	memset(p1, 0x11, sizeof(p1));
	memset(p2, 0x22, sizeof(p2));
	sim_world_init(&world, 3, 12345);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 10;
	link.latency_ms = 1;
	sim_world_set_chain(&world, &link);

	for (i = 0; i < 3; i++) {
		memset(&cfg[i], 0, sizeof(cfg[i]));
		cfg[i].node_id = (uint16_t)(i + 1);
		cfg[i].is_rook = (i == 0);
		cfg[i].starling_serve = 1;
		memcpy(cfg[i].farm_id, farm, 8);
		cfg[i].frag_data_max = 50;
		cfg[i].trickle_imin_ms = 30;
		cfg[i].trickle_imax_ms = 300;
		setup_node(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp,
		           &world);
	}
	CHECK(oc_fh_build_signed(&b1, farm, 1, 1, p1, sizeof(p1), 50, test_sign, &kp) == 0);
	CHECK(oc_fh_build_signed(&b2, farm, 2, 2, p2, sizeof(p2), 50, test_sign, &kp) == 0);
	CHECK(oc_fh_inject_local(&nodes[0], b1.sealed, b1.sealed_len, p1, sizeof(p1)) == 0);
	poll_all(nodes, 3, &world, 200, 5);
	/* Inject newer mid-propagation at Rook. */
	CHECK(oc_fh_inject_local(&nodes[0], b2.sealed, b2.sealed_len, p2, sizeof(p2)) == 0);
	poll_all(nodes, 3, &world, 6000, 5);
	CHECK(oc_fh_active(&nodes[0])->fence_seq == 2);
	CHECK(oc_fh_active(&nodes[1])->fence_seq == 2);
	CHECK(oc_fh_active(&nodes[2])->fence_seq == 2);
}

static void test_partition_heal(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seedk[32] = { 3 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[180];
	oc_fh_built_t built;
	oc_fh_node_t nodes[2];
	oc_fh_config_t cfg[2];
	node_mem_t mem[2];
	unsigned i;

	test_keygen(&kp, seedk);
	memset(payload, 0x55, sizeof(payload));
	sim_world_init(&world, 2, 99);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);
	sim_world_partition(&world, 0, 1, 0); /* partitioned */

	for (i = 0; i < 2; i++) {
		memset(&cfg[i], 0, sizeof(cfg[i]));
		cfg[i].node_id = (uint16_t)(i + 1);
		cfg[i].is_rook = (i == 0);
		cfg[i].starling_serve = 0;
		memcpy(cfg[i].farm_id, farm, 8);
		cfg[i].frag_data_max = 60;
		cfg[i].trickle_imin_ms = 40;
		cfg[i].trickle_imax_ms = 200;
		setup_node(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp,
		           &world);
	}
	CHECK(oc_fh_build_signed(&built, farm, 5, 5, payload, sizeof(payload), 60, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&nodes[0], built.sealed, built.sealed_len, payload,
	                         sizeof(payload)) == 0);
	poll_all(nodes, 2, &world, 200, 5);
	CHECK(oc_fh_active(&nodes[1])->fence_seq == 0);
	sim_world_partition(&world, 0, 1, 1); /* heal */
	poll_all(nodes, 2, &world, 2000, 5);
	CHECK(oc_fh_active(&nodes[1])->fence_seq == 5);
}

int main(void)
{
	CHECK(chain_propagate(1, 0));
	CHECK(chain_propagate(2, 30));
	CHECK(chain_propagate(3, 30));
	CHECK(chain_propagate(4, 30));
	{
		int ok = 0, i;
		for (i = 0; i < 50; i++) {
			if (chain_propagate(100ull + (uint64_t)i, 30)) {
				ok++;
			}
		}
		printf("CHAIN30 seeds=50 success=%d rate=%.3f\n", ok, (double)ok / 50.0);
		CHECK(ok == 50);
	}
	test_newer_supersedes();
	test_partition_heal();

	if (failures) {
		printf("test_chain: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_chain: all tests passed\n");
	return 0;
}
