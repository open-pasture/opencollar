/*
 * Rolling airtime budget and per-channel dwell limiter (US 915 hopping).
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_DUTY_H
#define OPENCOLLAR_RADIO_DUTY_H

#include <stdbool.h>
#include <stdint.h>

struct radio_duty {
	uint32_t window_ms;
	uint32_t limit_us;
	uint32_t used_us;
	uint32_t window_start_ms;

	uint32_t dwell_window_ms;
	uint32_t dwell_limit_us;
	uint32_t dwell_used_us;
	uint32_t dwell_start_ms;
	uint32_t dwell_freq_hz;
};

void radio_duty_init(struct radio_duty *d, uint32_t window_ms, uint32_t limit_us,
		     uint32_t dwell_window_ms, uint32_t dwell_limit_us);

/* Advance clocks; now_ms is a monotonic millisecond clock. */
void radio_duty_tick(struct radio_duty *d, uint32_t now_ms);

/* True if airtime_us fits both the rolling duty budget and channel dwell. */
bool radio_duty_allow(struct radio_duty *d, uint32_t now_ms, uint32_t freq_hz,
		      uint32_t airtime_us);

/* Record a successful TX of airtime_us on freq_hz. */
void radio_duty_account(struct radio_duty *d, uint32_t now_ms, uint32_t freq_hz,
			uint32_t airtime_us);

#endif
