/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Low-power scheduling placeholders: GNSS duty cycle, LoRa RX windows, sleep.
 */
#ifndef STARLING_POWER_H
#define STARLING_POWER_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* PLACEHOLDER timings — tune with radio/GNSS engineers. */
#define STARLING_PWR_GNSS_ON_MS 5000u
#define STARLING_PWR_GNSS_OFF_MS 25000u
#define STARLING_PWR_LORA_RX_MS 250u
#define STARLING_PWR_LORA_SLEEP_MS 5000u

enum power_phase {
	POWER_GNSS_ON = 0,
	POWER_GNSS_OFF,
	POWER_LORA_RX,
	POWER_SLEEP,
};

struct power_sched {
	enum power_phase phase;
	int64_t phase_until_ms;
	uint32_t gnss_on_ms;
	uint32_t gnss_off_ms;
	uint32_t lora_rx_ms;
	uint32_t lora_sleep_ms;
};

void power_sched_init(struct power_sched *p);
enum power_phase power_sched_tick(struct power_sched *p, int64_t now_ms);
bool power_want_gnss(const struct power_sched *p);
bool power_want_lora_rx(const struct power_sched *p);

#ifdef __cplusplus
}
#endif

#endif
