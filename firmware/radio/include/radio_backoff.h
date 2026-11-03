/*
 * Randomized backoff for CAD/LBT retries.
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_BACKOFF_H
#define OPENCOLLAR_RADIO_BACKOFF_H

#include <stdint.h>

void radio_backoff_seed(uint32_t seed);

/* Uniform random in [min_ms, max_ms], with exponential growth by attempt. */
uint32_t radio_backoff_ms(uint32_t attempt, uint32_t min_ms, uint32_t max_ms);

#endif
