/*
 * Host virtual radio implementing opencollar/radio_hal.h.
 * Seeded loss, burst loss, reorder, duplicates, latency, MTU, duty budget.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_SIM_RADIO_H
#define OPENCOLLAR_SIM_RADIO_H

#include "opencollar/radio_hal.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SIM_MAX_NODES 16
#define SIM_MAX_PENDING 256
#define SIM_MAX_MTU 255

typedef struct sim_link {
	uint8_t connected;     /* 0 = partitioned */
	uint16_t loss_pct;     /* 0..100 independent drop probability */
	uint16_t burst_pct;    /* chance to start a burst drop */
	uint16_t burst_len;    /* packets dropped in a burst */
	uint16_t reorder_pct;  /* chance to delay/reorder */
	uint16_t duplicate_pct;
	uint32_t latency_ms;
	uint32_t latency_jitter_ms;
} sim_link_t;

typedef struct sim_world sim_world_t;

typedef struct sim_pending {
	uint8_t used;
	uint8_t src;
	uint8_t dst;
	uint32_t deliver_at_ms;
	uint16_t len;
	uint8_t data[SIM_MAX_MTU];
	int16_t rssi_dbm;
	int8_t snr_db;
} sim_pending_t;

struct oc_radio {
	sim_world_t *world;
	uint8_t id;
	uint8_t asleep;
	int8_t power_dbm;
	uint32_t mtu;
	uint32_t bytes_per_ms_air; /* crude airtime model */
	oc_radio_cfg_t cfg;
	oc_radio_limits_t limits;
	uint32_t duty_used_us; /* within current hour window */
	uint32_t duty_window_start_ms;
	uint32_t last_tx_ms; /* for min_tx_gap_ms; 0 = never */
	/* RX queue */
	uint8_t rq_head;
	uint8_t rq_tail;
	uint8_t rq_count;
	sim_pending_t rxq[32];
	/* burst state per destination */
	uint16_t burst_left[SIM_MAX_NODES];
};

struct sim_world {
	uint64_t rng;
	uint32_t now_ms;
	uint8_t n_nodes;
	oc_radio_t nodes[SIM_MAX_NODES];
	sim_link_t link[SIM_MAX_NODES][SIM_MAX_NODES]; /* [src][dst] */
	sim_pending_t inflight[SIM_MAX_PENDING];
	uint32_t airtime_us_total;
};

void sim_world_init(sim_world_t *w, uint8_t n_nodes, uint64_t seed);
void sim_world_set_fully_connected(sim_world_t *w, const sim_link_t *proto);
void sim_world_set_chain(sim_world_t *w, const sim_link_t *proto);
void sim_world_set_link(sim_world_t *w, uint8_t a, uint8_t b, const sim_link_t *ab,
                        const sim_link_t *ba);
void sim_world_partition(sim_world_t *w, uint8_t a, uint8_t b, int connected);

oc_radio_t *sim_radio(sim_world_t *w, uint8_t id);
void sim_world_advance(sim_world_t *w, uint32_t ms);
uint32_t sim_world_now(sim_world_t *w);

uint32_t sim_clock_ms(void *ctx); /* ctx = sim_world_t* */

#ifdef __cplusplus
}
#endif

#endif
