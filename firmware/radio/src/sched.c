/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_sched.h"
#include "radio_backoff.h"

#include <stddef.h>
#include <stdint.h>

void radio_sched_init(struct radio_sched *s, const struct radio_sched_cfg *cfg,
		      uint32_t now_ms)
{
	if (s == NULL || cfg == NULL) {
		return;
	}
	s->cfg = *cfg;
	if (s->cfg.rx_period_ms == 0u) {
		s->cfg.rx_period_ms = 1000u;
	}
	if (s->cfg.rx_window_ms == 0u) {
		s->cfg.rx_window_ms = 50u;
	}
	if (s->cfg.rx_window_ms > s->cfg.rx_period_ms) {
		s->cfg.rx_window_ms = s->cfg.rx_period_ms;
	}
	if (s->cfg.beacon_period_ms == 0u) {
		s->cfg.beacon_period_ms = 30000u;
	}
	s->next_rx_ms = now_ms;
	s->rx_until_ms = 0u;
	s->in_rx = false;
	s->next_cad_ms = s->cfg.cad_wake_period_ms ? now_ms + s->cfg.cad_wake_period_ms : 0u;
	radio_sched_arm_beacon(s, now_ms);
}

void radio_sched_arm_beacon(struct radio_sched *s, uint32_t now_ms)
{
	uint32_t jitter;
	uint32_t half;
	uint32_t delay;

	if (s == NULL) {
		return;
	}
	half = s->cfg.beacon_jitter_ms;
	if (half == 0u) {
		delay = s->cfg.beacon_period_ms;
	} else {
		jitter = radio_backoff_ms(0u, 0u, half * 2u);
		delay = s->cfg.beacon_period_ms + jitter - half;
	}
	s->next_beacon_ms = now_ms + delay;
}

void radio_sched_beacon_done(struct radio_sched *s, uint32_t now_ms)
{
	radio_sched_arm_beacon(s, now_ms);
}

static uint32_t min_u32(uint32_t a, uint32_t b)
{
	return a < b ? a : b;
}

enum radio_sched_action radio_sched_poll(struct radio_sched *s, uint32_t now_ms,
					 uint32_t *wake_ms)
{
	uint32_t next = UINT32_MAX;
	enum radio_sched_action act = RADIO_SCHED_SLEEP;

	if (s == NULL) {
		if (wake_ms) {
			*wake_ms = now_ms;
		}
		return RADIO_SCHED_SLEEP;
	}

	/* Beacon has priority once its time arrives (still CAD'd by HAL on send). */
	if (now_ms >= s->next_beacon_ms) {
		if (wake_ms) {
			*wake_ms = now_ms;
		}
		return RADIO_SCHED_BEACON;
	}
	next = min_u32(next, s->next_beacon_ms);

	if (s->in_rx) {
		if (now_ms >= s->rx_until_ms) {
			s->in_rx = false;
			s->next_rx_ms = s->rx_until_ms +
					(s->cfg.rx_period_ms - s->cfg.rx_window_ms);
		} else {
			if (wake_ms) {
				*wake_ms = s->rx_until_ms;
			}
			return RADIO_SCHED_RX_WINDOW;
		}
	}

	if (now_ms >= s->next_rx_ms) {
		s->in_rx = true;
		s->rx_until_ms = now_ms + s->cfg.rx_window_ms;
		if (wake_ms) {
			*wake_ms = s->rx_until_ms;
		}
		return RADIO_SCHED_RX_WINDOW;
	}
	next = min_u32(next, s->next_rx_ms);

	if (s->cfg.cad_wake_period_ms && s->next_cad_ms && now_ms >= s->next_cad_ms) {
		s->next_cad_ms = now_ms + s->cfg.cad_wake_period_ms;
		if (wake_ms) {
			*wake_ms = now_ms;
		}
		return RADIO_SCHED_CAD_WAKE;
	}
	if (s->cfg.cad_wake_period_ms && s->next_cad_ms) {
		next = min_u32(next, s->next_cad_ms);
	}

	if (wake_ms) {
		*wake_ms = next == UINT32_MAX ? now_ms + s->cfg.rx_period_ms : next;
	}
	(void)act;
	return RADIO_SCHED_SLEEP;
}
