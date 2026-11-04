/*
 * Late-joiner / multi-hop gossip scenarios (starling_serve=ON):
 *  - Mid-chain Starling powers on empty or with older seq and catches up
 *  - Rook injects newer while late joiner is catching up (supersede)
 *  - Late joiner holds NEWER fence and pushes toward the Rook side
 *
 * Fast path: few seeds (make test). Long 30% sweeps: --loss30 (make loss).
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

typedef struct {
	int ok;
	uint32_t converge_ms;
	uint32_t airtime_us_sum;
} run_result_t;

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

static void cfg_chain_node(oc_fh_config_t *cfg, uint16_t id, int is_rook, const uint8_t farm[8])
{
	memset(cfg, 0, sizeof(*cfg));
	cfg->node_id = id;
	cfg->is_rook = is_rook ? 1 : 0;
	cfg->starling_serve = 1; /* explicit multi-hop */
	memcpy(cfg->farm_id, farm, 8);
	cfg->frag_data_max = 64;
	cfg->trickle_imin_ms = 40;
	cfg->trickle_imax_ms = 400;
	cfg->trickle_k = 1;
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

static int all_at_seq(oc_fh_node_t *nodes, int n, uint32_t seq)
{
	int i;
	for (i = 0; i < n; i++) {
		if (oc_fh_active(&nodes[i])->fence_seq != seq) {
			return 0;
		}
	}
	return 1;
}

static uint32_t sum_airtime(oc_fh_node_t *nodes, int n)
{
	uint32_t s = 0;
	int i;
	for (i = 0; i < n; i++) {
		s += oc_fh_stats(&nodes[i])->airtime_us;
	}
	return s;
}

/*
 * Propagate seq on an N-node chain, wipe mid node to empty (or older), then
 * measure catch-up. mid index in [1, n-2].
 */
static run_result_t late_join_empty(uint64_t seed, int n_nodes, int mid, uint16_t loss_pct,
                                    int older_seq)
{
	run_result_t rr = {0};
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seedk[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[280], older[280];
	oc_fh_built_t built, built_old;
	oc_fh_node_t nodes[5];
	oc_fh_config_t cfg[5];
	node_mem_t mem[5];
	unsigned i;
	int t;
	uint32_t air0;
	const uint32_t target = 10;
	const int step_ms = 5;
	const int max_steps = 12000; /* 60 s */

	if (n_nodes < 3 || n_nodes > 5 || mid <= 0 || mid >= n_nodes - 1) {
		return rr;
	}
	for (i = 0; i < 32; i++) {
		seedk[i] = (uint8_t)(i ^ (seed & 0xff) ^ (uint8_t)n_nodes);
	}
	test_keygen(&kp, seedk);
	for (i = 0; i < sizeof(payload); i++) {
		payload[i] = (uint8_t)(i + 7);
		older[i] = (uint8_t)(i + 1);
	}

	sim_world_init(&world, (uint8_t)n_nodes, seed);
	memset(&link, 0, sizeof(link));
	link.loss_pct = loss_pct;
	link.burst_pct = 2;
	link.burst_len = 2;
	link.reorder_pct = 5;
	link.duplicate_pct = 2;
	link.latency_ms = 2;
	link.latency_jitter_ms = 2;
	sim_world_set_chain(&world, &link);

	for (i = 0; i < (unsigned)n_nodes; i++) {
		cfg_chain_node(&cfg[i], (uint16_t)(i + 1), i == 0, farm);
		setup_node(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp,
		           &world);
	}

	if (oc_fh_build_signed(&built, farm, target, target, payload, sizeof(payload), 64,
	                       test_sign, &kp) != 0) {
		return rr;
	}
	if (oc_fh_inject_local(&nodes[0], built.sealed, built.sealed_len, payload,
	                       sizeof(payload)) != 0) {
		return rr;
	}
	poll_all(nodes, n_nodes, &world, 8000, step_ms);
	if (!all_at_seq(nodes, n_nodes, target)) {
		return rr;
	}

	/* Mid-chain "reboot": empty or older seq. */
	memset(&mem[mid], 0, sizeof(mem[mid]));
	setup_node(&nodes[mid], &cfg[mid], &mem[mid], sim_radio(&world, (uint8_t)mid), &kp,
	           &world);
	if (older_seq) {
		if (oc_fh_build_signed(&built_old, farm, 3, 3, older, sizeof(older), 64, test_sign,
		                       &kp) != 0) {
			return rr;
		}
		if (oc_fh_inject_local(&nodes[mid], built_old.sealed, built_old.sealed_len, older,
		                       sizeof(older)) != 0) {
			return rr;
		}
		if (oc_fh_active(&nodes[mid])->fence_seq != 3) {
			return rr;
		}
	} else if (oc_fh_active(&nodes[mid])->fence_seq != 0) {
		return rr;
	}

	air0 = sum_airtime(nodes, n_nodes);
	for (t = 0; t < max_steps; t++) {
		poll_all(nodes, n_nodes, &world, 1, step_ms);
		if (oc_fh_active(&nodes[mid])->fence_seq == target) {
			rr.ok = 1;
			rr.converge_ms = (uint32_t)((t + 1) * step_ms);
			rr.airtime_us_sum = sum_airtime(nodes, n_nodes) - air0;
			return rr;
		}
	}
	return rr;
}

/* Rook injects newer while mid is still empty / catching up. */
static run_result_t late_join_supersede(uint64_t seed, int n_nodes, int mid, uint16_t loss_pct)
{
	run_result_t rr = {0};
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seedk[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t p1[200], p2[220];
	oc_fh_built_t b1, b2;
	oc_fh_node_t nodes[5];
	oc_fh_config_t cfg[5];
	node_mem_t mem[5];
	unsigned i;
	int t;
	uint32_t air0;
	const int step_ms = 5;
	const int max_steps = 14000;

	if (n_nodes < 3 || n_nodes > 5 || mid <= 0 || mid >= n_nodes - 1) {
		return rr;
	}
	for (i = 0; i < 32; i++) {
		seedk[i] = (uint8_t)(i ^ (seed & 0xff));
	}
	test_keygen(&kp, seedk);
	memset(p1, 0x41, sizeof(p1));
	memset(p2, 0x42, sizeof(p2));

	sim_world_init(&world, (uint8_t)n_nodes, seed ^ 0xA5A5);
	memset(&link, 0, sizeof(link));
	link.loss_pct = loss_pct;
	link.latency_ms = 2;
	link.latency_jitter_ms = 2;
	link.reorder_pct = 5;
	sim_world_set_chain(&world, &link);

	for (i = 0; i < (unsigned)n_nodes; i++) {
		cfg_chain_node(&cfg[i], (uint16_t)(i + 1), i == 0, farm);
		setup_node(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp,
		           &world);
	}

	if (oc_fh_build_signed(&b1, farm, 1, 1, p1, sizeof(p1), 50, test_sign, &kp) != 0 ||
	    oc_fh_build_signed(&b2, farm, 2, 2, p2, sizeof(p2), 50, test_sign, &kp) != 0) {
		return rr;
	}
	for (i = 0; i < (unsigned)n_nodes; i++) {
		cfg[i].frag_data_max = 50;
		setup_node(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp,
		           &world);
	}

	if (oc_fh_inject_local(&nodes[0], b1.sealed, b1.sealed_len, p1, sizeof(p1)) != 0) {
		return rr;
	}
	poll_all(nodes, n_nodes, &world, 6000, step_ms);
	if (!all_at_seq(nodes, n_nodes, 1)) {
		return rr;
	}

	/* Wipe mid; start catch-up on seq 1, then Rook injects seq 2. */
	memset(&mem[mid], 0, sizeof(mem[mid]));
	setup_node(&nodes[mid], &cfg[mid], &mem[mid], sim_radio(&world, (uint8_t)mid), &kp,
	           &world);
	air0 = sum_airtime(nodes, n_nodes);
	poll_all(nodes, n_nodes, &world, 40, step_ms); /* brief catch-up attempt */
	if (oc_fh_inject_local(&nodes[0], b2.sealed, b2.sealed_len, p2, sizeof(p2)) != 0) {
		return rr;
	}

	for (t = 0; t < max_steps; t++) {
		poll_all(nodes, n_nodes, &world, 1, step_ms);
		if (all_at_seq(nodes, n_nodes, 2)) {
			rr.ok = 1;
			rr.converge_ms = (uint32_t)((t + 1) * step_ms);
			rr.airtime_us_sum = sum_airtime(nodes, n_nodes) - air0;
			return rr;
		}
	}
	return rr;
}

/* Mid holds newer fence; must push back toward Rook side. */
static run_result_t late_join_push_newer(uint64_t seed, int n_nodes, int mid, uint16_t loss_pct)
{
	run_result_t rr = {0};
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seedk[32];
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t p_old[180], p_new[200];
	oc_fh_built_t b_old, b_new;
	oc_fh_node_t nodes[5];
	oc_fh_config_t cfg[5];
	node_mem_t mem[5];
	unsigned i;
	int t;
	uint32_t air0;
	const int step_ms = 5;
	const int max_steps = 14000;

	if (n_nodes < 3 || n_nodes > 5 || mid <= 0 || mid >= n_nodes - 1) {
		return rr;
	}
	for (i = 0; i < 32; i++) {
		seedk[i] = (uint8_t)(i ^ (seed & 0xff) ^ 0x3c);
	}
	test_keygen(&kp, seedk);
	memset(p_old, 0x61, sizeof(p_old));
	memset(p_new, 0x62, sizeof(p_new));

	sim_world_init(&world, (uint8_t)n_nodes, seed ^ 0x1111);
	memset(&link, 0, sizeof(link));
	link.loss_pct = loss_pct;
	link.latency_ms = 2;
	link.latency_jitter_ms = 2;
	sim_world_set_chain(&world, &link);

	for (i = 0; i < (unsigned)n_nodes; i++) {
		cfg_chain_node(&cfg[i], (uint16_t)(i + 1), i == 0, farm);
		cfg[i].frag_data_max = 50;
		setup_node(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp,
		           &world);
	}

	if (oc_fh_build_signed(&b_old, farm, 5, 5, p_old, sizeof(p_old), 50, test_sign, &kp) !=
	        0 ||
	    oc_fh_build_signed(&b_new, farm, 6, 6, p_new, sizeof(p_new), 50, test_sign, &kp) !=
	        0) {
		return rr;
	}

	/* Everyone starts on seq 5. */
	if (oc_fh_inject_local(&nodes[0], b_old.sealed, b_old.sealed_len, p_old, sizeof(p_old)) !=
	    0) {
		return rr;
	}
	poll_all(nodes, n_nodes, &world, 6000, step_ms);
	if (!all_at_seq(nodes, n_nodes, 5)) {
		return rr;
	}

	/* Mid alone gets seq 6 (e.g. offline Rook update / local inject). */
	if (oc_fh_inject_local(&nodes[mid], b_new.sealed, b_new.sealed_len, p_new,
	                       sizeof(p_new)) != 0) {
		return rr;
	}
	if (oc_fh_active(&nodes[mid])->fence_seq != 6) {
		return rr;
	}
	air0 = sum_airtime(nodes, n_nodes);

	for (t = 0; t < max_steps; t++) {
		poll_all(nodes, n_nodes, &world, 1, step_ms);
		if (all_at_seq(nodes, n_nodes, 6)) {
			rr.ok = 1;
			rr.converge_ms = (uint32_t)((t + 1) * step_ms);
			rr.airtime_us_sum = sum_airtime(nodes, n_nodes) - air0;
			return rr;
		}
	}
	return rr;
}

static void report_sweep(const char *name, int ok, int seeds, uint64_t sum_ms, uint64_t sum_air)
{
	printf("%s seeds=%d success=%d rate=%.3f mean_converge_ms=%.0f mean_airtime_us=%.0f\n",
	       name, seeds, ok, seeds ? (double)ok / (double)seeds : 0.0,
	       ok ? (double)sum_ms / (double)ok : 0.0, ok ? (double)sum_air / (double)ok : 0.0);
}

static void run_sweep(const char *name, int n_nodes, int mid, uint16_t loss, int seeds,
                      int mode, int require_all)
{
	/* mode: 0 empty join, 1 older join, 2 supersede, 3 push newer */
	int ok = 0, i;
	uint64_t sum_ms = 0, sum_air = 0;

	for (i = 0; i < seeds; i++) {
		run_result_t rr;
		uint64_t seed = 500ull + (uint64_t)i * 17ull + (uint64_t)n_nodes * 100ull +
		                (uint64_t)mode * 1000ull;
		if (mode == 0) {
			rr = late_join_empty(seed, n_nodes, mid, loss, 0);
		} else if (mode == 1) {
			rr = late_join_empty(seed, n_nodes, mid, loss, 1);
		} else if (mode == 2) {
			rr = late_join_supersede(seed, n_nodes, mid, loss);
		} else {
			rr = late_join_push_newer(seed, n_nodes, mid, loss);
		}
		if (rr.ok) {
			ok++;
			sum_ms += rr.converge_ms;
			sum_air += rr.airtime_us_sum;
		}
	}
	report_sweep(name, ok, seeds, sum_ms, sum_air);
	if (require_all) {
		CHECK(ok == seeds);
	}
}

static void fast_smoke(void)
{
	run_result_t rr;

	rr = late_join_empty(1, 3, 1, 0, 0);
	CHECK(rr.ok);
	rr = late_join_empty(2, 3, 1, 30, 0);
	CHECK(rr.ok);
	rr = late_join_empty(3, 5, 2, 0, 0);
	CHECK(rr.ok);
	rr = late_join_empty(4, 5, 2, 30, 1);
	CHECK(rr.ok);
	rr = late_join_supersede(5, 3, 1, 0);
	CHECK(rr.ok);
	rr = late_join_supersede(6, 5, 2, 10);
	CHECK(rr.ok);
	rr = late_join_push_newer(7, 3, 1, 0);
	CHECK(rr.ok);
	rr = late_join_push_newer(8, 5, 2, 10);
	CHECK(rr.ok);

	/* Small 30% batches for CI (fast). */
	run_sweep("LATEJOIN3_EMPTY30", 3, 1, 30, 20, 0, 1);
	run_sweep("LATEJOIN5_EMPTY30", 5, 2, 30, 15, 0, 1);
	run_sweep("LATEJOIN3_SUPERSEDE30", 3, 1, 30, 15, 2, 1);
	run_sweep("LATEJOIN3_PUSH30", 3, 1, 30, 15, 3, 1);
}

static void loss30_sweeps(void)
{
	run_sweep("LATEJOIN3_EMPTY30", 3, 1, 30, 200, 0, 1);
	run_sweep("LATEJOIN5_EMPTY30", 5, 2, 30, 100, 0, 1);
	run_sweep("LATEJOIN3_OLDER30", 3, 1, 30, 100, 1, 1);
	run_sweep("LATEJOIN5_OLDER30", 5, 2, 30, 80, 1, 1);
	run_sweep("LATEJOIN3_SUPERSEDE30", 3, 1, 30, 100, 2, 1);
	run_sweep("LATEJOIN5_SUPERSEDE30", 5, 2, 30, 80, 2, 1);
	run_sweep("LATEJOIN3_PUSH30", 3, 1, 30, 100, 3, 1);
	run_sweep("LATEJOIN5_PUSH30", 5, 2, 30, 80, 3, 1);
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

	if (loss30) {
		loss30_sweeps();
	} else {
		fast_smoke();
	}

	if (failures) {
		printf("test_latejoin: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_latejoin: all tests passed\n");
	return 0;
}
