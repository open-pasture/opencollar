/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_duty.h"

#include <stddef.h>

void radio_duty_init(struct radio_duty *d, uint32_t window_ms, uint32_t limit_us,
		     uint32_t dwell_window_ms, uint32_t dwell_limit_us)
{
	if (d == NULL) {
		return;
	}
	d->window_ms = window_ms ? window_ms : 1u;
	d->limit_us = limit_us;
	d->used_us = 0u;
	d->window_start_ms = 0u;
	d->dwell_window_ms = dwell_window_ms ? dwell_window_ms : 1u;
	d->dwell_limit_us = dwell_limit_us;
	d->dwell_used_us = 0u;
	d->dwell_start_ms = 0u;
	d->dwell_freq_hz = 0u;
}

static void roll_window(uint32_t *start_ms, uint32_t *used, uint32_t now_ms,
			uint32_t window_ms)
{
	if (now_ms - *start_ms >= window_ms) {
		*start_ms = now_ms;
		*used = 0u;
	}
}

void radio_duty_tick(struct radio_duty *d, uint32_t now_ms)
{
	if (d == NULL) {
		return;
	}
	roll_window(&d->window_start_ms, &d->used_us, now_ms, d->window_ms);
	roll_window(&d->dwell_start_ms, &d->dwell_used_us, now_ms, d->dwell_window_ms);
}

bool radio_duty_allow(struct radio_duty *d, uint32_t now_ms, uint32_t freq_hz,
		      uint32_t airtime_us)
{
	uint32_t dwell_used;

	if (d == NULL) {
		return false;
	}
	radio_duty_tick(d, now_ms);

	if (d->limit_us > 0u && d->used_us + airtime_us > d->limit_us) {
		return false;
	}

	if (d->dwell_limit_us == 0u) {
		return true;
	}

	if (freq_hz != d->dwell_freq_hz) {
		/* New channel: dwell counter resets for this check. */
		dwell_used = 0u;
	} else {
		dwell_used = d->dwell_used_us;
	}
	return dwell_used + airtime_us <= d->dwell_limit_us;
}

void radio_duty_account(struct radio_duty *d, uint32_t now_ms, uint32_t freq_hz,
			uint32_t airtime_us)
{
	if (d == NULL) {
		return;
	}
	radio_duty_tick(d, now_ms);

	if (freq_hz != d->dwell_freq_hz) {
		d->dwell_freq_hz = freq_hz;
		d->dwell_used_us = 0u;
		d->dwell_start_ms = now_ms;
	}

	d->used_us += airtime_us;
	d->dwell_used_us += airtime_us;
}
