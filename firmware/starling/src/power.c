/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "power.h"

void power_sched_init(struct power_sched *p)
{
	p->phase = POWER_GNSS_ON;
	p->phase_until_ms = 0;
	p->gnss_on_ms = STARLING_PWR_GNSS_ON_MS;
	p->gnss_off_ms = STARLING_PWR_GNSS_OFF_MS;
	p->lora_rx_ms = STARLING_PWR_LORA_RX_MS;
	p->lora_sleep_ms = STARLING_PWR_LORA_SLEEP_MS;
}

enum power_phase power_sched_tick(struct power_sched *p, int64_t now_ms)
{
	if (p->phase_until_ms == 0) {
		p->phase_until_ms = now_ms + (int64_t)p->gnss_on_ms;
		p->phase = POWER_GNSS_ON;
		return p->phase;
	}
	if (now_ms < p->phase_until_ms) {
		return p->phase;
	}

	switch (p->phase) {
	case POWER_GNSS_ON:
		p->phase = POWER_LORA_RX;
		p->phase_until_ms = now_ms + (int64_t)p->lora_rx_ms;
		break;
	case POWER_LORA_RX:
		p->phase = POWER_SLEEP;
		p->phase_until_ms = now_ms + (int64_t)p->lora_sleep_ms;
		break;
	case POWER_SLEEP:
		p->phase = POWER_GNSS_OFF;
		p->phase_until_ms = now_ms + (int64_t)p->gnss_off_ms;
		break;
	case POWER_GNSS_OFF:
	default:
		p->phase = POWER_GNSS_ON;
		p->phase_until_ms = now_ms + (int64_t)p->gnss_on_ms;
		break;
	}
	return p->phase;
}

bool power_want_gnss(const struct power_sched *p)
{
	return p->phase == POWER_GNSS_ON;
}

bool power_want_lora_rx(const struct power_sched *p)
{
	return p->phase == POWER_LORA_RX;
}
