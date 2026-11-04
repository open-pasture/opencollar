/*
 * Milestone (a): signed Rook→Starling handoff under packet loss.
 * Default: quick smoke. --loss30 runs 1000 seeds at 30% loss.
 */
#include "fence_build.h"
#include "opencollar/fence_node.h"
#include "sim_radio.h"
#include "test_crypto.h"

#include <stdio.h>
#include <stdlib.h>
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

static int run_handoff(uint64_t seed, uint16_t loss_pct, int max_ms, uint32_t *out_rexmit,
                       uint32_t *out_air)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seedk[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[400];
	oc_fh_built_t built;
	oc_fh_node_t rook, star;
	oc_fh_config_t cr, cs;
	node_mem_t mr, ms;
	unsigned i;
	int t;

	for (i = 0; i < 32; i++) {
		seedk[i] = (uint8_t)(i + (seed & 0xff));
	}
	test_keygen(&kp, seedk);
	for (i = 0; i < sizeof(payload); i++) {
		payload[i] = (uint8_t)(0x3C ^ (i * 17) ^ (unsigned)seed);
	}

	sim_world_init(&world, 2, seed);
	memset(&link, 0, sizeof(link));
	link.loss_pct = loss_pct;
	link.burst_pct = (uint16_t)(loss_pct / 10u);
	link.burst_len = 3;
	link.reorder_pct = 5;
	link.duplicate_pct = 3;
	link.latency_ms = 2;
	link.latency_jitter_ms = 3;
	sim_world_set_fully_connected(&world, &link);

	memset(&cr, 0, sizeof(cr));
	cr.node_id = 1;
	cr.is_rook = 1;
	cr.starling_serve = 0;
	memcpy(cr.farm_id, farm, 8);
	cr.frag_data_max = 100; /* keep sealed manifest under radio MTU */
	cr.trickle_imin_ms = 50;
	cr.trickle_imax_ms = 500;
	cr.trickle_k = 1;
	cs = cr;
	cs.node_id = 2;
	cs.is_rook = 0;

	setup_node(&rook, &cr, &mr, sim_radio(&world, 0), &kp, &world);
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);

	if (oc_fh_build_signed(&built, farm, 100, 1700000001u, payload, sizeof(payload), 100,
	                       test_sign, &kp) != 0) {
		return 0;
	}
	if (oc_fh_inject_local(&rook, built.sealed, built.sealed_len, payload, sizeof(payload)) !=
	    0) {
		return 0;
	}

	for (t = 0; t < max_ms; t += 5) {
		oc_fh_node_poll(&rook);
		oc_fh_node_poll(&star);
		sim_world_advance(&world, 5);
		if (oc_fh_active(&star)->fence_seq == 100) {
			if (out_rexmit) {
				*out_rexmit = oc_fh_stats(&rook)->retransmit_frags +
				              oc_fh_stats(&star)->retransmit_frags;
			}
			if (out_air) {
				*out_air = world.airtime_us_total;
			}
			return 1;
		}
	}
	return 0;
}

static void run_loss30(void)
{
	const int N = 1000;
	int ok = 0;
	uint64_t sum_rex = 0;
	uint64_t sum_air = 0;
	int i;

	for (i = 0; i < N; i++) {
		uint32_t rex = 0, air = 0;
		if (run_handoff(1000ull + (uint64_t)i, 30, 20000, &rex, &air)) {
			ok++;
			sum_rex += rex;
			sum_air += air;
		}
	}
	printf("LOSS30 seeds=%d success=%d rate=%.3f mean_rexmit=%.2f mean_airtime_us=%.0f\n", N,
	       ok, (double)ok / (double)N, ok ? (double)sum_rex / (double)ok : 0.0,
	       ok ? (double)sum_air / (double)ok : 0.0);
	CHECK(ok == N);
}

int main(int argc, char **argv)
{
	int loss30 = 0;
	int i;
	for (i = 1; i < argc; i++) {
		if (strcmp(argv[i], "--loss30") == 0) {
			loss30 = 1;
		}
	}

	/* Smoke: 0% loss */
	CHECK(run_handoff(42, 0, 5000, NULL, NULL));
	/* Smoke: 30% single seed */
	CHECK(run_handoff(7, 30, 15000, NULL, NULL));
	/* Smoke: 50% stress single seed (may need more time) */
	CHECK(run_handoff(99, 50, 30000, NULL, NULL));

	if (loss30) {
		run_loss30();
	} else {
		/* CI default: 100 seeds at 30% for speed */
		int ok = 0;
		uint64_t sum_rex = 0, sum_air = 0;
		for (i = 0; i < 100; i++) {
			uint32_t rex = 0, air = 0;
			if (run_handoff(2000ull + (uint64_t)i, 30, 20000, &rex, &air)) {
				ok++;
				sum_rex += rex;
				sum_air += air;
			}
		}
		printf("LOSS30_CI seeds=100 success=%d rate=%.3f mean_rexmit=%.2f "
		       "mean_airtime_us=%.0f\n",
		       ok, (double)ok / 100.0, ok ? (double)sum_rex / (double)ok : 0.0,
		       ok ? (double)sum_air / (double)ok : 0.0);
		CHECK(ok == 100);
	}

	if (failures) {
		printf("test_onehop: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_onehop: all tests passed\n");
	return 0;
}
