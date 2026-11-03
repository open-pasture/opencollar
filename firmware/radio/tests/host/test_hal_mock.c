/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_hal.h"
#include "radio_us915.h"
#include "rhal_mock.h"

#include <stdio.h>
#include <string.h>

static int fails;

static void check(int cond, const char *msg)
{
	if (!cond) {
		fprintf(stderr, "FAIL %s\n", msg);
		fails++;
	}
}

static void setup(struct rhal *h, struct rhal_platform *plat,
		  struct rhal_limits *lim_out, uint32_t budget_us)
{
	struct rhal_cfg cfg;
	struct rhal_limits lim;

	rhal_mock_reset();
	rhal_mock_platform(plat);
	rhal_us915_default_cfg(&cfg);
	rhal_us915_default_limits(&lim);
	lim.airtime_budget_us_per_h = budget_us;
	lim.min_tx_gap_ms = 50;
	lim.max_frame_airtime_us = 400000;
	if (lim_out) {
		*lim_out = lim;
	}
	check(rhal_init(h, &cfg, &lim, plat) == RHAL_OK, "init");
}

int main(void)
{
	struct rhal h;
	struct rhal_limits lim;
	struct rhal_platform plat;
	struct rhal_rx rx;
	uint8_t payload[16];
	int rc;
	uint32_t air;

	memset(payload, 0xA5, sizeof(payload));

	setup(&h, &plat, &lim, 5u * 1000u * 1000u);
	air = rhal_airtime_us(&h, 16);
	check(air > 0, "airtime");

	rc = rhal_send(&h, payload, 16, 0);
	check(rc == RHAL_OK, "first send");
	check(rhal_mock_tx_count() == 1, "tx count");

	rc = rhal_send(&h, payload, 16, 0);
	check(rc == RHAL_E_BUDGET, "min gap");

	rhal_mock_advance_us(60000);
	rc = rhal_send(&h, payload, 16, 0);
	check(rc == RHAL_OK, "second send after gap");

	rhal_deinit(&h);
	setup(&h, &plat, NULL, 5u * 1000u * 1000u);
	rhal_mock_set_cad_busy(1);
	rc = rhal_send(&h, payload, 16, 0);
	check(rc == RHAL_E_BUSY, "cad busy");
	rhal_mock_set_cad_busy(0);

	rhal_deinit(&h);
	setup(&h, &plat, NULL, air); /* exactly one packet */
	check(rhal_send(&h, payload, 16, 0) == RHAL_OK, "budget send");
	rhal_mock_advance_us(100000);
	check(rhal_send(&h, payload, 16, 0) == RHAL_E_BUDGET, "budget refuse");
	check(rhal_airtime_left_us(&h) == 0, "left zero");

	rhal_mock_queue_rx(payload, 16, -95, 7);
	check(rhal_recv(&h, &rx, 100) == RHAL_OK, "recv");
	check(rx.len == 16 && rx.rssi_dbm == -95 && rx.snr_db == 7, "meta");

	check(rhal_set_power(&h, 30) == RHAL_E_POWER, "power cap");
	check(rhal_cad(&h, 10) == 0, "cad clear");
	check(rhal_sleep(&h) == RHAL_OK, "sleep");

	if (fails) {
		return 1;
	}
	puts("ok");
	return 0;
}
