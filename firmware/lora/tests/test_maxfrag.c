/*
 * 64-fragment fence stored and re-served by a Starling relay (starling_serve=1).
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
	uint8_t rx[2048];
	uint8_t tx[2048];
} node_mem_t;

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
}

int main(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 64 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[64 * 16]; /* 64 fragments × 16 bytes */
	oc_fh_built_t built;
	oc_fh_node_t nodes[3];
	oc_fh_config_t cfg[3];
	node_mem_t mem[3];
	unsigned i;
	int t;

	test_keygen(&kp, seed);
	for (i = 0; i < sizeof(payload); i++) {
		payload[i] = (uint8_t)i;
	}

	CHECK(oc_fh_build_signed(&built, farm, 42, 42, payload, sizeof(payload), 16, test_sign,
	                         &kp) == 0);
	CHECK(built.manifest.frag_count == 64);
	CHECK(built.sealed_len == OC_FH_MANIFEST_WIRE_MAX);
	CHECK(built.sealed_len == 1140u);

	sim_world_init(&world, 3, 64);
	/* Raise MTU so the 1140 B sealed manifest can move in one sim frame.
	 * Real LoRa still ≤255; multi-frame manifests are future work (NOTES). */
	for (i = 0; i < 3; i++) {
		sim_radio_set_mtu(sim_radio(&world, (uint8_t)i), 1500);
	}
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_chain(&world, &link); /* Rook-S1-S2; S2 out of Rook range */

	for (i = 0; i < 3; i++) {
		memset(&cfg[i], 0, sizeof(cfg[i]));
		cfg[i].node_id = (uint16_t)(i + 1);
		cfg[i].is_rook = (i == 0);
		cfg[i].starling_serve = 1;
		memcpy(cfg[i].farm_id, farm, 8);
		cfg[i].frag_data_max = 16;
		cfg[i].trickle_imin_ms = 30;
		cfg[i].trickle_imax_ms = 300;
		setup(&nodes[i], &cfg[i], &mem[i], sim_radio(&world, (uint8_t)i), &kp, &world);
	}

	CHECK(oc_fh_inject_local(&nodes[0], built.sealed, built.sealed_len, payload,
	                         sizeof(payload)) == OC_FH_OK);
	CHECK(nodes[0].active_manifest_wire_len == 1140u);
	CHECK(oc_fh_stats(&nodes[0])->manifest_wire_ovf == 0);

	for (t = 0; t < 20000; t++) {
		for (i = 0; i < 3; i++) {
			oc_fh_node_poll(&nodes[i]);
		}
		sim_world_advance(&world, 5);
		if (oc_fh_active(&nodes[1])->fence_seq == 42 &&
		    oc_fh_active(&nodes[2])->fence_seq == 42) {
			break;
		}
	}
	CHECK(oc_fh_active(&nodes[1])->fence_seq == 42);
	CHECK(oc_fh_active(&nodes[2])->fence_seq == 42);
	CHECK(nodes[1].active_manifest_wire_len == 1140u); /* relay stored full wire */
	CHECK(memcmp(mem[2].active, payload, sizeof(payload)) == 0);
	CHECK(oc_fh_stats(&nodes[0])->manifest_wire_ovf == 0);
	CHECK(oc_fh_stats(&nodes[1])->manifest_wire_ovf == 0);

	if (failures) {
		printf("test_maxfrag: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_maxfrag: all tests passed\n");
	return 0;
}
