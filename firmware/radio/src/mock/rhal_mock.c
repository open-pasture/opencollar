/*
 * Host / native_sim mock backend for limiter and scheduler tests.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_hal.h"

#include <string.h>

struct rhal_mock {
	uint64_t now_us;
	int8_t power_dbm;
	int cad_busy;          /* force next CAD result: 0 clear, 1 busy */
	int fail_send;
	uint8_t last_tx[255];
	uint8_t last_tx_len;
	uint8_t rx_queue[255];
	uint8_t rx_len;
	int16_t rx_rssi;
	int8_t rx_snr;
	uint32_t tx_count;
	uint32_t rx_count;
	uint32_t cad_count;
	struct rhal_cfg cfg;
};

static struct rhal_mock g_mock;

void rhal_mock_reset(void)
{
	memset(&g_mock, 0, sizeof(g_mock));
	g_mock.power_dbm = 14;
	g_mock.rx_rssi = -90;
	g_mock.rx_snr = 5;
}

void rhal_mock_set_time_us(uint64_t t)
{
	g_mock.now_us = t;
}

void rhal_mock_advance_us(uint64_t dt)
{
	g_mock.now_us += dt;
}

void rhal_mock_set_cad_busy(int busy)
{
	g_mock.cad_busy = busy ? 1 : 0;
}

void rhal_mock_queue_rx(const uint8_t *buf, uint8_t len, int16_t rssi, int8_t snr)
{
	if (buf == NULL || len == 0u) {
		g_mock.rx_len = 0u;
		return;
	}
	if (len > sizeof(g_mock.rx_queue)) {
		len = (uint8_t)sizeof(g_mock.rx_queue);
	}
	memcpy(g_mock.rx_queue, buf, len);
	g_mock.rx_len = len;
	g_mock.rx_rssi = rssi;
	g_mock.rx_snr = snr;
}

uint32_t rhal_mock_tx_count(void)
{
	return g_mock.tx_count;
}

const uint8_t *rhal_mock_last_tx(uint8_t *len_out)
{
	if (len_out) {
		*len_out = g_mock.last_tx_len;
	}
	return g_mock.last_tx;
}

static uint64_t mock_now(void *ctx)
{
	(void)ctx;
	return g_mock.now_us;
}

static int mock_init(void *ctx, const struct rhal_cfg *cfg)
{
	(void)ctx;
	if (cfg) {
		g_mock.cfg = *cfg;
		g_mock.power_dbm = cfg->tx_dbm;
	}
	return RHAL_OK;
}

static void mock_deinit(void *ctx)
{
	(void)ctx;
}

static int mock_set_power(void *ctx, int8_t dbm)
{
	(void)ctx;
	g_mock.power_dbm = dbm;
	return RHAL_OK;
}

static int mock_cad(void *ctx, uint32_t timeout_ms)
{
	(void)ctx;
	(void)timeout_ms;
	g_mock.cad_count++;
	g_mock.now_us += 1000ull; /* 1 ms CAD */
	return g_mock.cad_busy;
}

static int mock_send(void *ctx, const uint8_t *buf, uint8_t len, int8_t dbm)
{
	(void)ctx;
	if (g_mock.fail_send) {
		return RHAL_E_IO;
	}
	if (len > sizeof(g_mock.last_tx)) {
		return RHAL_E_INVAL;
	}
	memcpy(g_mock.last_tx, buf, len);
	g_mock.last_tx_len = len;
	g_mock.power_dbm = dbm;
	g_mock.tx_count++;
	/* Approximate airtime advance for SF8/125kHz ~ few ms; tests control time. */
	g_mock.now_us += 5000ull;
	return RHAL_OK;
}

static int mock_recv(void *ctx, struct rhal_rx *out, uint32_t window_ms)
{
	(void)ctx;
	g_mock.now_us += (uint64_t)window_ms * 1000ull;
	if (g_mock.rx_len == 0u) {
		return RHAL_E_TIMEOUT;
	}
	memset(out, 0, sizeof(*out));
	memcpy(out->buf, g_mock.rx_queue, g_mock.rx_len);
	out->len = g_mock.rx_len;
	out->rssi_dbm = g_mock.rx_rssi;
	out->snr_db = g_mock.rx_snr;
	out->t_rx_us = g_mock.now_us;
	g_mock.rx_len = 0u;
	g_mock.rx_count++;
	return RHAL_OK;
}

static int mock_sleep(void *ctx)
{
	(void)ctx;
	return RHAL_OK;
}

void rhal_mock_platform(struct rhal_platform *plat)
{
	if (plat == NULL) {
		return;
	}
	memset(plat, 0, sizeof(*plat));
	plat->now_us = mock_now;
	plat->init = mock_init;
	plat->deinit = mock_deinit;
	plat->set_power = mock_set_power;
	plat->cad = mock_cad;
	plat->send = mock_send;
	plat->recv = mock_recv;
	plat->sleep = mock_sleep;
	plat->ctx = &g_mock;
}
