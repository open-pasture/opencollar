/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_us915.h"

void rhal_us915_default_cfg(struct rhal_cfg *cfg)
{
	if (cfg == NULL) {
		return;
	}
	cfg->freq_hz = RADIO_US915_FREQ_DEFAULT_HZ;
	cfg->sf = RADIO_US915_SF_DEFAULT;
	cfg->bw_khz_code = 0; /* 125 kHz */
	cfg->cr = RADIO_US915_CR_DEFAULT;
	cfg->sync_word = 0x12;
	cfg->tx_dbm = RADIO_US915_TX_CAP_DBM_DEFAULT;
}

void rhal_us915_default_limits(struct rhal_limits *lim)
{
	if (lim == NULL) {
		return;
	}
	lim->max_frame_airtime_us = 400000u;
	lim->airtime_budget_us_per_h = 36000000u; /* 36 s/hour ≈ 1 % */
	lim->min_tx_gap_ms = 100u;
	lim->dwell_limit_us = RADIO_US915_DWELL_LIMIT_US;
	lim->dwell_window_ms = RADIO_US915_DWELL_WINDOW_MS;
	lim->tx_power_cap_dbm = RADIO_US915_TX_CAP_DBM_DEFAULT;
}
