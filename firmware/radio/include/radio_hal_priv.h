/*
 * Internal HAL state. Not for protocol consumers.
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_RADIO_HAL_PRIV_H
#define OPENCOLLAR_RADIO_HAL_PRIV_H

#include "radio_hal.h"
#include "radio_duty.h"
#include "radio_airtime.h"

struct rhal_state {
	struct rhal_cfg cfg;
	struct rhal_limits lim;
	struct rhal_platform plat;
	struct radio_duty duty;
	int8_t cur_power_dbm;
	uint64_t last_tx_end_us;
	uint32_t hour_used_us;
	uint64_t hour_start_us;
	bool inited;
};

struct rhal_state *rhal_state(struct rhal *h);
const struct rhal_state *rhal_state_c(const struct rhal *h);
uint32_t rhal_bw_hz(uint8_t bw_khz_code);

#endif
