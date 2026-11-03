/*
 * Host mock hardware ops for oc_radio_* unit tests.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "opencollar/radio_sx1262.h"

#include <string.h>

struct mock_ctx {
	uint64_t now_us;
	int cad_busy;
	uint8_t last_tx[255];
	size_t last_tx_len;
	uint8_t rx[255];
	size_t rx_len;
	int16_t rx_rssi;
	int8_t rx_snr;
	uint32_t tx_count;
	uint64_t rng;
};

static struct mock_ctx g;

void oc_radio_mock_reset(void)
{
	memset(&g, 0, sizeof(g));
	g.rng = 1;
	g.rx_rssi = -90;
	g.rx_snr = 5;
}

void oc_radio_mock_set_time_us(uint64_t us)
{
	g.now_us = us;
}

void oc_radio_mock_advance_us(uint64_t us)
{
	g.now_us += us;
}

void oc_radio_mock_set_cad_busy(int busy)
{
	g.cad_busy = busy ? 1 : 0;
}

void oc_radio_mock_queue_rx(const uint8_t *buf, size_t len, int16_t rssi,
			    int8_t snr)
{
	if (buf == NULL || len == 0u) {
		g.rx_len = 0u;
		return;
	}
	if (len > sizeof(g.rx)) {
		len = sizeof(g.rx);
	}
	memcpy(g.rx, buf, len);
	g.rx_len = len;
	g.rx_rssi = rssi;
	g.rx_snr = snr;
}

uint32_t oc_radio_mock_tx_count(void)
{
	return g.tx_count;
}

static oc_radio_status_t m_cad(void *ctx, oc_radio_cad_result_t *out)
{
	(void)ctx;
	g.now_us += 1000ull;
	*out = g.cad_busy ? OC_RADIO_CAD_BUSY : OC_RADIO_CAD_FREE;
	return OC_RADIO_OK;
}

static oc_radio_status_t m_send(void *ctx, const uint8_t *buf, size_t len,
				int8_t dbm)
{
	(void)ctx;
	(void)dbm;
	if (len > sizeof(g.last_tx)) {
		return OC_RADIO_ERR_TOO_LARGE;
	}
	memcpy(g.last_tx, buf, len);
	g.last_tx_len = len;
	g.tx_count++;
	g.now_us += 5000ull;
	return OC_RADIO_OK;
}

static oc_radio_status_t m_recv(void *ctx, uint8_t *buf, size_t cap,
				size_t *out_len, oc_radio_rx_meta_t *meta,
				uint32_t timeout_ms)
{
	(void)ctx;
	if (timeout_ms != 0u && timeout_ms != UINT32_MAX) {
		g.now_us += (uint64_t)timeout_ms * 1000ull;
	}
	if (g.rx_len == 0u) {
		return OC_RADIO_ERR_TIMEOUT;
	}
	if (g.rx_len > cap) {
		return OC_RADIO_ERR_NO_MEM;
	}
	memcpy(buf, g.rx, g.rx_len);
	*out_len = g.rx_len;
	if (meta) {
		memset(meta, 0, sizeof(*meta));
		meta->rssi_dbm = g.rx_rssi;
		meta->snr_db = g.rx_snr;
		meta->timestamp_ms = (uint32_t)(g.now_us / 1000ull);
		meta->t_rx_us = g.now_us;
	}
	g.rx_len = 0u;
	return OC_RADIO_OK;
}

static oc_radio_status_t m_set_power(void *ctx, int8_t dbm)
{
	(void)ctx;
	(void)dbm;
	return OC_RADIO_OK;
}

static oc_radio_status_t m_sleep(void *ctx)
{
	(void)ctx;
	return OC_RADIO_OK;
}

static uint64_t m_now(void *ctx)
{
	(void)ctx;
	return g.now_us;
}

static uint32_t m_rand(void *ctx)
{
	uint64_t x;

	(void)ctx;
	x = g.rng;
	x ^= x >> 12;
	x ^= x << 25;
	x ^= x >> 27;
	g.rng = x ? x : 1ull;
	return (uint32_t)x;
}

void oc_radio_mock_ops(oc_radio_hw_ops_t *ops)
{
	memset(ops, 0, sizeof(*ops));
	ops->cad = m_cad;
	ops->send = m_send;
	ops->recv = m_recv;
	ops->set_power = m_set_power;
	ops->sleep = m_sleep;
	ops->now_us = m_now;
	ops->rand32 = m_rand;
	ops->ctx = &g;
}
