/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_backoff.h"

static uint32_t rng_state = 0xA5A5A5A5u;

void radio_backoff_seed(uint32_t seed)
{
	rng_state = seed ? seed : 0xA5A5A5A5u;
}

static uint32_t next_u32(void)
{
	/* xorshift32 — good enough for collision jitter, not crypto. */
	uint32_t x = rng_state;
	x ^= x << 13;
	x ^= x >> 17;
	x ^= x << 5;
	rng_state = x ? x : 0xA5A5A5A5u;
	return rng_state;
}

uint32_t radio_backoff_ms(uint32_t attempt, uint32_t min_ms, uint32_t max_ms)
{
	uint32_t span;
	uint32_t cap;
	uint32_t shift;

	if (max_ms < min_ms) {
		uint32_t t = min_ms;
		min_ms = max_ms;
		max_ms = t;
	}
	if (max_ms == min_ms) {
		return min_ms;
	}

	/* Exponential growth: min * 2^attempt, capped at max. */
	shift = attempt > 16u ? 16u : attempt;
	cap = min_ms << shift;
	if (cap < min_ms || cap > max_ms) {
		cap = max_ms;
	}
	span = cap - min_ms;
	if (span == 0u) {
		return min_ms;
	}
	return min_ms + (next_u32() % (span + 1u));
}
