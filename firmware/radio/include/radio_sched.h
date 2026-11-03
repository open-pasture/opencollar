/*
 * Low-power RX windows + freshness-beacon scheduling (topology-neutral).
 *
 * Every collar (Rook and Starling) both listens and transmits. This module
 * only times RX windows and randomized beacon intervals; the protocol layer
 * decides what to put in a beacon or whether to gossip a fence update.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_SCHED_H
#define OPENCOLLAR_RADIO_SCHED_H

#include <stdbool.h>
#include <stdint.h>

enum radio_sched_action {
	RADIO_SCHED_SLEEP = 0,
	RADIO_SCHED_RX_WINDOW,
	RADIO_SCHED_BEACON,
	RADIO_SCHED_CAD_WAKE,
};

struct radio_sched_cfg {
	uint32_t rx_period_ms;       /* time between RX window starts */
	uint32_t rx_window_ms;       /* how long to stay in RX */
	uint32_t beacon_period_ms;   /* nominal freshness-beacon interval */
	uint32_t beacon_jitter_ms;   /* ± jitter applied to beacon_period */
	bool cad_before_beacon;      /* run CAD before each beacon TX */
	uint32_t cad_wake_period_ms; /* optional CAD sniff between RX windows (0=off) */
};

struct radio_sched {
	struct radio_sched_cfg cfg;
	uint32_t next_rx_ms;
	uint32_t rx_until_ms;
	uint32_t next_beacon_ms;
	uint32_t next_cad_ms;
	bool in_rx;
};

void radio_sched_init(struct radio_sched *s, const struct radio_sched_cfg *cfg,
		      uint32_t now_ms);

/* Recompute next beacon time with fresh jitter. */
void radio_sched_arm_beacon(struct radio_sched *s, uint32_t now_ms);

/* What the radio should do at now_ms, and when to wake next (wake_ms). */
enum radio_sched_action radio_sched_poll(struct radio_sched *s, uint32_t now_ms,
					 uint32_t *wake_ms);

/* Call after a beacon was sent (or skipped) so the next one is scheduled. */
void radio_sched_beacon_done(struct radio_sched *s, uint32_t now_ms);

#endif
