/*
 * SPDX-License-Identifier: Apache-2.0
 */
#include "opencollar/radio_hal.h"
#include "opencollar/radio_sx1262.h"

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

static void setup(oc_radio_t *r, uint32_t duty_limit_us)
{
	oc_radio_cfg_t cfg;
	oc_radio_hw_ops_t ops;

	oc_radio_mock_reset();
	oc_radio_mock_ops(&ops);
	oc_radio_cfg_us915_defaults(&cfg);
	cfg.duty_limit_us = duty_limit_us;
	cfg.min_tx_gap_ms = 50;
	check(oc_radio_sx1262_open(r, &cfg, &ops) == OC_RADIO_OK, "open");
}

int main(void)
{
	oc_radio_t r;
	oc_radio_rx_meta_t meta;
	uint8_t payload[16];
	uint8_t buf[32];
	size_t n = 0;
	uint32_t air;
	oc_radio_cad_result_t cad;
	oc_radio_tx_opts_t opts = oc_radio_tx_opts_default();

	memset(payload, 0xA5, sizeof(payload));

	setup(&r, 5u * 1000u * 1000u);
	air = oc_radio_airtime_us(&r, 16);
	check(air > 0, "airtime");
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_OK, "send1");
	check(oc_radio_mock_tx_count() == 1, "tx count");
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_DUTY,
	      "min gap");

	oc_radio_mock_advance_ms(60);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_OK, "send2");

	oc_radio_sx1262_close(&r);
	setup(&r, 5u * 1000u * 1000u);
	oc_radio_mock_set_cad_busy(1);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_BUSY,
	      "cad busy");
	oc_radio_mock_set_cad_busy(0);

	oc_radio_sx1262_close(&r);
	setup(&r, air);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_OK, "budget ok");
	oc_radio_mock_advance_ms(100);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_DUTY,
	      "budget refuse");
	check(oc_radio_duty_budget_us(&r) == 0, "left zero");

	oc_radio_mock_queue_rx(payload, 16, -95, 7);
	check(oc_radio_recv(&r, buf, sizeof(buf), &n, &meta, 100) == OC_RADIO_OK,
	      "recv");
	check(n == 16 && meta.rssi_dbm == -95 && meta.snr_db == 7, "meta");

	check(oc_radio_set_power(&r, 30) == OC_RADIO_ERR_PARAM, "power cap");
	check(oc_radio_cad(&r, &cad) == OC_RADIO_OK && cad == OC_RADIO_CAD_FREE,
	      "cad free");
	check(oc_radio_backoff_ms(&r, 10, 20) >= 10, "backoff");
	check(oc_radio_trickle_t_ms(&r, 1000) >= 500, "trickle");
	check(oc_radio_sx1262_sleep(&r) == OC_RADIO_OK, "sleep");

	/* MTU */
	check(oc_radio_send(&r, payload, 300, &opts) == OC_RADIO_ERR_TOO_LARGE,
	      "too large");

	if (fails) {
		return 1;
	}
	puts("ok");
	return 0;
}
