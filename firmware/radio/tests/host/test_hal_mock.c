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

static void setup(oc_radio_t *r, uint32_t budget_us, uint16_t gap_ms,
		  uint32_t max_air)
{
	oc_radio_cfg_t cfg;
	oc_radio_limits_t lim;
	oc_radio_hw_ops_t ops;

	oc_radio_mock_reset();
	oc_radio_mock_ops(&ops);
	oc_radio_cfg_us915_defaults(&cfg, &lim);
	lim.airtime_budget_us_per_h = budget_us;
	lim.min_tx_gap_ms = gap_ms;
	lim.max_frame_airtime_us = max_air;
	check(oc_radio_sx1262_bind(r, &ops) == OC_RADIO_OK, "bind");
	check(oc_radio_init(r, &cfg, &lim) == OC_RADIO_OK, "init");
}

int main(void)
{
	oc_radio_t r;
	oc_radio_rx_meta_t meta;
	uint8_t payload[16];
	uint8_t buf[32];
	size_t n = 0;
	uint32_t air;
	uint32_t cads_before;
	oc_radio_cad_result_t cad;
	oc_radio_tx_opts_t opts = oc_radio_tx_opts_default();

	memset(payload, 0xA5, sizeof(payload));

	setup(&r, 5u * 1000u * 1000u, 50, 400000u);
	air = oc_radio_airtime_us(&r, 16);
	check(air > 0, "airtime");
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_OK, "send1");
	check(oc_radio_mock_tx_count() == 1, "tx count");
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_GAP, "gap");

	oc_radio_mock_advance_us(60000ull);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_OK, "send2");

	/* CAD busy */
	setup(&r, 5u * 1000u * 1000u, 50, 400000u);
	oc_radio_mock_set_cad_busy(1);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_BUSY,
	      "cad busy");
	oc_radio_mock_set_cad_busy(0);

	/* SKIP_CAD: no CAD call, but gap/duty still apply */
	setup(&r, 5u * 1000u * 1000u, 50, 400000u);
	cads_before = oc_radio_mock_cad_count();
	opts.flags = OC_RADIO_TX_FLAG_SKIP_CAD;
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_OK, "skip cad");
	check(oc_radio_mock_cad_count() == cads_before, "no cad on skip");
	check(r.skip_cad_count == 1, "skip logged");
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_GAP,
	      "gap after skip");
	opts = oc_radio_tx_opts_default();

	/* Hourly budget → ERR_DUTY */
	setup(&r, air, 50, 400000u);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_OK, "budget ok");
	oc_radio_mock_advance_us(100000ull);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_DUTY,
	      "budget refuse");
	check(oc_radio_duty_budget_us(&r) == 0, "left zero");

	/* Max frame airtime → ERR_AIRTIME */
	setup(&r, 5u * 1000u * 1000u, 0, air - 1u);
	check(oc_radio_send(&r, payload, 16, &opts) == OC_RADIO_ERR_AIRTIME,
	      "airtime refuse");

	setup(&r, 5u * 1000u * 1000u, 50, 400000u);
	oc_radio_mock_queue_rx(payload, 16, -95, 7);
	check(oc_radio_recv(&r, buf, sizeof(buf), &n, &meta, 100) == OC_RADIO_OK,
	      "recv");
	check(n == 16 && meta.rssi_dbm == -95 && meta.snr_db == 7 &&
		      meta.t_rx_us != 0 && meta.peer_id == 0,
	      "meta");

	check(oc_radio_cad(&r, &cad, 0) == OC_RADIO_OK &&
		      cad == OC_RADIO_CAD_FREE,
	      "cad default timeout");
	check(oc_radio_cad(&r, &cad, 20) == OC_RADIO_OK, "cad 20ms");
	check(oc_radio_set_power(&r, 30) == OC_RADIO_ERR_PARAM, "power cap");
	check(oc_radio_now_us(&r) > 0, "now_us");
	check(oc_radio_sleep(&r) == OC_RADIO_OK, "sleep");
	check(oc_radio_send(&r, payload, 300, &opts) == OC_RADIO_ERR_TOO_LARGE,
	      "too large");

	if (fails) {
		return 1;
	}
	puts("ok");
	return 0;
}
