/*
 * US 915 MHz bring-up preset and FCC Part 15.247 assumptions.
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_US915_H
#define OPENCOLLAR_RADIO_US915_H

#include "radio_hal.h"

/*
 * Regime implemented by default:
 *
 *   FCC 15.247(a)(1) frequency hopping for LoRa at 125 kHz (SF7..SF10).
 *   Per-channel dwell ≤ 400 ms / 20 s enforced in the HAL. Hourly airtime
 *   budget and min TX gap are additional software limits (fairness /
 *   battery / beacon+gossip headroom), not FCC numbers.
 *
 * Protocol v2 Plan 1 (US915_500: SF8 / 500 kHz / 15.247(a)(2)) remains a
 * selectable preset for the one-hop star fallback; not the bring-up default.
 * See docs/FCC-US915.md. Decision for op-firmware: which preset ships first.
 */

#define RADIO_US915_BW_HZ           125000u
#define RADIO_US915_SF_DEFAULT      8u
#define RADIO_US915_CR_DEFAULT      5u
#define RADIO_US915_PREAMBLE        8u
#define RADIO_US915_FREQ_DEFAULT_HZ 903900000u

#define RADIO_US915_TX_CAP_DBM_DEFAULT   14
#define RADIO_US915_TX_CAP_DBM_ABSOLUTE  22

#define RADIO_US915_DWELL_LIMIT_US   400000u
#define RADIO_US915_DWELL_WINDOW_MS  20000u

void rhal_us915_default_cfg(struct rhal_cfg *cfg);
void rhal_us915_default_limits(struct rhal_limits *lim);

#endif
