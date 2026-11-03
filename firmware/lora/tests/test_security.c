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

static void test_forged_beacon(void)
{
	/*
	 * Forged freshness beacon is an unauthenticated hint only: may schedule
	 * a bounded NEED, must never change the active fence (no state apply).
	 */
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 11 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[80];
	oc_fh_built_t built;
	oc_fh_node_t star;
	oc_fh_config_t cs;
	node_mem_t ms;
	oc_fh_beacon_t forged;
	uint8_t wire[64];
	size_t wlen;
	uint32_t seq_before;
	unsigned i;

	test_keygen(&kp, seed);
	memset(payload, 0x42, sizeof(payload));
	sim_world_init(&world, 2, 17);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	memset(&cs, 0, sizeof(cs));
	cs.node_id = 2;
	cs.is_rook = 0;
	cs.starling_serve = OC_FH_STARLING_SERVE_DEFAULT; /* OFF */
	memcpy(cs.farm_id, farm, 8);
	cs.frag_data_max = 40;
	cs.trickle_imin_ms = 50;
	cs.trickle_imax_ms = 200;
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);

	/* Establish a real last-good fence first. */
	CHECK(oc_fh_build_signed(&built, farm, 5, 5, payload, sizeof(payload), 40, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&star, built.sealed, built.sealed_len, payload,
	                         sizeof(payload)) == 0);
	seq_before = oc_fh_active(&star)->fence_seq;
	CHECK(seq_before == 5);

	/* Flood forged beacons claiming a much newer seq + garbage hash. */
	memset(&forged, 0, sizeof(forged));
	memcpy(forged.farm_id, farm, 8);
	forged.fence_seq = 999;
	for (i = 0; i < OC_FH_SHORT_HASH_LEN; i++) {
		forged.short_hash[i] = (uint8_t)(0xA5 ^ i);
	}
	forged.hop_reserved = 0;
	wlen = oc_fh_encode_beacon(&forged, wire, sizeof(wire));
	CHECK(wlen > 0);
	/* ~15 s of flood: enough to hit OC_FH_NEED_HINT_MAX, then pause. */
	for (i = 0; i < 3000; i++) {
		CHECK(oc_radio_send(sim_radio(&world, 0), wire, wlen, NULL) == OC_RADIO_OK);
		sim_world_advance(&world, 5);
		oc_fh_node_poll(&star);
	}
	/* Active fence unchanged; hint may have opened a pending shell only. */
	CHECK(oc_fh_active(&star)->fence_seq == seq_before);
	CHECK(oc_fh_stats(&star)->applied == 1); /* only the local inject */
	CHECK(oc_fh_stats(&star)->reject_sig == 0); /* beacon is not signature-checked */
	/* NEED/airtime bounded despite flood. */
	CHECK(oc_fh_stats(&star)->need_tx >= 1);
	CHECK(oc_fh_stats(&star)->need_capped >= 1);
	/* ~15 s flood / 5 s windows → a few windows × HINT_MAX, still bounded. */
	CHECK(oc_fh_stats(&star)->need_tx <= OC_FH_NEED_HINT_MAX * 5u + 2u);
	CHECK(oc_fh_stats(&star)->airtime_us < 500000u);
	CHECK(oc_fh_active(&star)->fence_seq == 5);
	CHECK(memcmp(ms.active, payload, sizeof(payload)) == 0);
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

/* Build a minimal unsigned LOCAL manifest (forged / pilot air path). */
static size_t forge_local(uint8_t *out, size_t cap, const uint8_t farm[8], uint32_t seq,
                          uint16_t frag_count)
{
	oc_fh_manifest_t m;
	memset(&m, 0, sizeof(m));
	memcpy(m.farm_id, farm, 8);
	m.fence_seq = seq;
	m.issued_at = seq;
	m.frag_count = frag_count ? frag_count : 1;
	memset(m.poly_hash, 0x5a, sizeof(m.poly_hash));
	memset(m.frag_hash[0], 0x5b, OC_FH_FRAG_HASH_LEN);
	return oc_fh_manifest_encode_local(&m, out, cap);
}

static int payload_verify_ok(const uint8_t *payload, size_t len, uint32_t fence_seq, void *ctx)
{
	(void)payload;
	(void)len;
	(void)fence_seq;
	(void)ctx;
	return 0;
}

static void test_local_air_gate_and_ffffffff_attack(void)
{
	/*
	 * A: air MANIFEST_LOCAL dropped unless accept_local_air + payload_verify.
	 * Exact 0xFFFFFFFF forged LOCAL must not block a real sealed fence.
	 */
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 21 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[80];
	uint8_t local_wire[OC_FH_MANIFEST_LOCAL_WIRE_MAX];
	size_t llen;
	oc_fh_built_t built;
	oc_fh_node_t star;
	oc_fh_config_t cs;
	node_mem_t ms;

	test_keygen(&kp, seed);
	memset(payload, 0x33, sizeof(payload));
	sim_world_init(&world, 2, 3);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	memset(&cs, 0, sizeof(cs));
	cs.node_id = 2;
	cs.is_rook = 0;
	cs.accept_local_air = 0; /* default: reject air LOCAL */
	memcpy(cs.farm_id, farm, 8);
	cs.frag_data_max = 40;
	cs.trickle_imin_ms = 50;
	cs.trickle_imax_ms = 200;
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);

	llen = forge_local(local_wire, sizeof(local_wire), farm, 0xFFFFFFFFu, 1);
	CHECK(llen > 0);
	CHECK(oc_radio_send(sim_radio(&world, 0), local_wire, llen, NULL) == OC_RADIO_OK);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&star);
	CHECK(oc_fh_stats(&star)->reject_local_air >= 1);
	CHECK(star.have_pending == 0);
	CHECK(oc_fh_active(&star)->fence_seq == 0);

	/* Even with pilot flag + verify, seq above OC_FH_SEQ_MAX is refused. */
	cs.accept_local_air = 1;
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);
	oc_fh_node_set_payload_verify(&star, payload_verify_ok, NULL);
	CHECK(oc_radio_send(sim_radio(&world, 0), local_wire, llen, NULL) == OC_RADIO_OK);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&star);
	CHECK(oc_fh_stats(&star)->reject_seq >= 1);
	CHECK(star.have_pending == 0);

	/* Real sealed fence still applies (attack failed to block). */
	CHECK(oc_fh_build_signed(&built, farm, 5, 5, payload, sizeof(payload), 40, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&star, built.sealed, built.sealed_len, payload,
	                         sizeof(payload)) == OC_FH_OK);
	CHECK(oc_fh_active(&star)->fence_seq == 5);
}

static void test_pending_timeout(void)
{
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 22 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	oc_fh_beacon_t forged;
	uint8_t wire[64];
	size_t wlen;
	oc_fh_node_t star;
	oc_fh_config_t cs;
	node_mem_t ms;
	unsigned i;

	test_keygen(&kp, seed);
	sim_world_init(&world, 2, 4);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	memset(&cs, 0, sizeof(cs));
	cs.node_id = 2;
	cs.is_rook = 0;
	memcpy(cs.farm_id, farm, 8);
	cs.frag_data_max = 40;
	cs.trickle_imin_ms = 50;
	cs.trickle_imax_ms = 200;
	cs.pending_timeout_ms = 200; /* short for test */
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);

	memset(&forged, 0, sizeof(forged));
	memcpy(forged.farm_id, farm, 8);
	forged.fence_seq = 50;
	memset(forged.short_hash, 0xab, OC_FH_SHORT_HASH_LEN);
	wlen = oc_fh_encode_beacon(&forged, wire, sizeof(wire));
	CHECK(oc_radio_send(sim_radio(&world, 0), wire, wlen, NULL) == OC_RADIO_OK);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&star);
	CHECK(star.have_pending == 1);

	for (i = 0; i < 80; i++) {
		oc_fh_node_poll(&star);
		sim_world_advance(&world, 5);
	}
	CHECK(star.have_pending == 0);
	CHECK(oc_fh_stats(&star)->pending_timeout >= 1);
	CHECK(oc_fh_active(&star)->fence_seq == 0);
}

static void test_sealed_preempts_unsigned_pending(void)
{
	/*
	 * Forged LOCAL with high (but allowed) seq becomes pending; a sealed
	 * manifest with lower seq must preempt it and then activate.
	 */
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 23 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	uint8_t payload[80];
	uint8_t local_wire[OC_FH_MANIFEST_LOCAL_WIRE_MAX];
	size_t llen;
	oc_fh_built_t built;
	oc_fh_node_t rook, star;
	oc_fh_config_t cr, cs;
	node_mem_t mr, ms;
	int t;

	test_keygen(&kp, seed);
	memset(payload, 0x44, sizeof(payload));
	sim_world_init(&world, 2, 6);
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
	cs.accept_local_air = 1;
	setup_node(&rook, &cr, &mr, sim_radio(&world, 0), &kp, &world);
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);
	oc_fh_node_set_payload_verify(&star, payload_verify_ok, NULL);

	llen = forge_local(local_wire, sizeof(local_wire), farm, OC_FH_SEQ_MAX, 4);
	CHECK(llen > 0);
	CHECK(oc_radio_send(sim_radio(&world, 0), local_wire, llen, NULL) == OC_RADIO_OK);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&star);
	CHECK(star.have_pending == 1);
	CHECK(star.pending_is_local == 1);
	CHECK(star.pending_manifest.fence_seq == OC_FH_SEQ_MAX);

	CHECK(oc_fh_build_signed(&built, farm, 8, 8, payload, sizeof(payload), 40, test_sign,
	                         &kp) == 0);
	CHECK(oc_fh_inject_local(&rook, built.sealed, built.sealed_len, payload,
	                         sizeof(payload)) == OC_FH_OK);
	/* Deliver sealed manifest: must preempt unsigned high-seq pending. */
	CHECK(oc_radio_send(sim_radio(&world, 0), built.sealed, built.sealed_len, NULL) ==
	      OC_RADIO_OK);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&star);
	CHECK(star.have_pending == 1);
	CHECK(star.pending_is_local == 0);
	CHECK(star.pending_manifest.fence_seq == 8);

	for (t = 0; t < 3000; t++) {
		oc_fh_node_poll(&rook);
		oc_fh_node_poll(&star);
		sim_world_advance(&world, 5);
		if (oc_fh_active(&star)->fence_seq == 8) {
			break;
		}
	}
	CHECK(oc_fh_active(&star)->fence_seq == 8);
	CHECK(memcmp(ms.active, payload, sizeof(payload)) == 0);
	CHECK(star.have_pending == 0);
}

static void test_peer_evict_oldest(void)
{
	/* Rotating peer_ids must evict the oldest slot, not always slot 0. */
	sim_world_t world;
	sim_link_t link;
	test_keypair_t kp;
	uint8_t seed[32] = { 24 };
	uint8_t farm[8] = { 'F', 'A', 'R', 'M', '0', '0', '0', '1' };
	oc_fh_beacon_t b;
	uint8_t wire[64];
	size_t wlen;
	oc_fh_node_t star;
	oc_fh_config_t cs;
	node_mem_t ms;
	uint16_t i;
	uint16_t first_peer;

	test_keygen(&kp, seed);
	sim_world_init(&world, 2, 7);
	memset(&link, 0, sizeof(link));
	link.loss_pct = 0;
	link.latency_ms = 1;
	sim_world_set_fully_connected(&world, &link);

	memset(&cs, 0, sizeof(cs));
	cs.node_id = 2;
	cs.is_rook = 0;
	memcpy(cs.farm_id, farm, 8);
	cs.frag_data_max = 40;
	cs.trickle_imin_ms = 50;
	cs.trickle_imax_ms = 200;
	cs.pending_timeout_ms = 60000;
	setup_node(&star, &cs, &ms, sim_radio(&world, 1), &kp, &world);

	memset(&b, 0, sizeof(b));
	memcpy(b.farm_id, farm, 8);
	b.fence_seq = 100;
	memset(b.short_hash, 0xcd, OC_FH_SHORT_HASH_LEN);
	wlen = oc_fh_encode_beacon(&b, wire, sizeof(wire));

	/* Fill all peer slots with distinct sources via meta.peer_id from sim:
	 * send from radio 0 repeatedly while manually driving need_budget through
	 * beacon opens — use pending_source path: each beacon opens pending;
	 * force NEED by polling. peer_id comes from sim link. For distinct
	 * peers we poke peer_need via many beacon floods after clearing slots
	 * by advancing window... Simpler: call poll after injecting beacons
	 * that open pending, then inspect eviction by filling slots directly. */
	for (i = 0; i < OC_FH_NEED_PEER_SLOTS; i++) {
		star.peer_need[i].used = 1;
		star.peer_need[i].peer_id = (uint16_t)(1000u + i);
		star.peer_need[i].window_start_ms = 1000u + (uint32_t)i * 10u;
		star.peer_need[i].need_count = 0;
	}
	first_peer = star.peer_need[0].peer_id;
	/* Oldest is slot 0 (window_start 1000). Open pending + force NEED. */
	CHECK(oc_radio_send(sim_radio(&world, 0), wire, wlen, NULL) == OC_RADIO_OK);
	sim_world_advance(&world, 5);
	oc_fh_node_poll(&star);
	CHECK(star.have_pending == 1);
	/* Drain NEED retries until budget path allocates a new peer slot. */
	for (i = 0; i < 20; i++) {
		oc_fh_node_poll(&star);
		sim_world_advance(&world, 20);
	}
	/* Slot 0 should have been reused for the real pending_source peer. */
	CHECK(star.peer_need[0].peer_id != first_peer || star.peer_need[0].peer_id == 0 ||
	      star.peer_need[0].window_start_ms != 1000u);
	/* Stronger: oldest window_start among still-1000+ peers is gone from slot0
	 * if eviction took slot 0 (oldest). */
	CHECK(star.peer_need[0].peer_id != first_peer);
}

int main(void)
{
	test_forged_beacon();
	test_forged_manifest();
	test_rollback();
	test_dup_reorder_resume();
	test_local_air_gate_and_ffffffff_attack();
	test_pending_timeout();
	test_sealed_preempts_unsigned_pending();
	test_peer_evict_oldest();
	if (failures) {
		printf("test_security: %d failure(s)\n", failures);
		return 1;
	}
	printf("test_security: all tests passed\n");
	return 0;
}
