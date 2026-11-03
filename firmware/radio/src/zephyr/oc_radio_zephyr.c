/*
 * Zephyr SX126x ops for oc_radio (NCS v3.4.1 native backend).
 * ops.ctx is oc_radio_t*; radio->hw holds the device pointer.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "opencollar/radio_sx1262.h"

#include <zephyr/device.h>
#include <zephyr/drivers/lora.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/random/random.h>
#include <string.h>

LOG_MODULE_REGISTER(oc_radio_zephyr, LOG_LEVEL_INF);

static const struct device *g_dev;

static enum lora_signal_bandwidth bw_z(uint8_t code)
{
	switch (code) {
	case 1:
		return BW_250_KHZ;
	case 2:
		return BW_500_KHZ;
	default:
		return BW_125_KHZ;
	}
}

static int apply(oc_radio_t *r, bool tx)
{
	struct lora_modem_config mc;
	const struct device *dev = r->hw ? r->hw : g_dev;

	if (dev == NULL) {
		return -ENODEV;
	}
	memset(&mc, 0, sizeof(mc));
	mc.frequency = r->cfg.freq_hz;
	mc.bandwidth = bw_z(r->cfg.bw_khz_code);
	mc.datarate = (enum lora_datarate)r->cfg.sf;
	mc.coding_rate =
		(enum lora_coding_rate)(r->cfg.cr >= 5 ? r->cfg.cr - 4 : 1);
	mc.preamble_len = r->cfg.preamble ? r->cfg.preamble : 8;
	mc.tx_power = r->power_dbm;
	mc.tx = tx;
	mc.public_network = (r->cfg.sync_word == 0x34);
#if defined(LORA_CAD_MODE_NONE)
	mc.cad.mode = LORA_CAD_MODE_NONE;
	mc.cad.symbol_num = LORA_CAD_SYMB_2;
#endif
	return lora_config(dev, &mc);
}

static oc_radio_t *as_radio(void *ctx)
{
	return (oc_radio_t *)ctx;
}

static oc_radio_status_t z_cad(void *ctx, oc_radio_cad_result_t *out)
{
	oc_radio_t *r = as_radio(ctx);
	const struct device *dev = r->hw ? r->hw : g_dev;
	int rc;

	if (apply(r, false) != 0) {
		return OC_RADIO_ERR_IO;
	}
	rc = lora_cad(dev, K_MSEC(50));
	if (rc == 0) {
		*out = OC_RADIO_CAD_FREE;
		return OC_RADIO_OK;
	}
	if (rc == 1) {
		*out = OC_RADIO_CAD_BUSY;
		return OC_RADIO_OK;
	}
	if (rc == -ENOSYS) {
		LOG_WRN("lora_cad unsupported; assuming free");
		*out = OC_RADIO_CAD_FREE;
		return OC_RADIO_OK;
	}
	return OC_RADIO_ERR_IO;
}

static oc_radio_status_t z_send(void *ctx, const uint8_t *buf, size_t len,
				int8_t dbm)
{
	oc_radio_t *r = as_radio(ctx);
	const struct device *dev = r->hw ? r->hw : g_dev;
	uint8_t tmp[OC_RADIO_MTU];

	r->power_dbm = dbm;
	if (apply(r, true) != 0) {
		return OC_RADIO_ERR_IO;
	}
	if (len > sizeof(tmp)) {
		return OC_RADIO_ERR_TOO_LARGE;
	}
	memcpy(tmp, buf, len);
	if (lora_send(dev, tmp, (uint32_t)len) != 0) {
		return OC_RADIO_ERR_IO;
	}
	return OC_RADIO_OK;
}

static oc_radio_status_t z_recv(void *ctx, uint8_t *buf, size_t cap,
				size_t *out_len, oc_radio_rx_meta_t *meta,
				uint32_t timeout_ms)
{
	oc_radio_t *r = as_radio(ctx);
	const struct device *dev = r->hw ? r->hw : g_dev;
	int16_t rssi = 0;
	int8_t snr = 0;
	int n;
	k_timeout_t to;

	if (apply(r, false) != 0) {
		return OC_RADIO_ERR_IO;
	}
	if (timeout_ms == 0u) {
		to = K_NO_WAIT;
	} else if (timeout_ms == UINT32_MAX) {
		to = K_FOREVER;
	} else {
		to = K_MSEC(timeout_ms);
	}
	if (cap > 255u) {
		cap = 255u;
	}
	n = lora_recv(dev, buf, (uint8_t)cap, to, &rssi, &snr);
	if (n < 0) {
		return (n == -EAGAIN || n == -ETIMEDOUT) ? OC_RADIO_ERR_TIMEOUT :
							   OC_RADIO_ERR_IO;
	}
	*out_len = (size_t)n;
	if (meta) {
		memset(meta, 0, sizeof(*meta));
		meta->rssi_dbm = rssi;
		meta->snr_db = snr;
		meta->timestamp_ms = k_uptime_get_32();
	}
	return OC_RADIO_OK;
}

static oc_radio_status_t z_set_power(void *ctx, int8_t dbm)
{
	oc_radio_t *r = as_radio(ctx);

	r->power_dbm = dbm;
	return apply(r, false) == 0 ? OC_RADIO_OK : OC_RADIO_ERR_IO;
}

static oc_radio_status_t z_sleep(void *ctx)
{
	(void)ctx;
	return OC_RADIO_OK;
}

static uint32_t z_now(void *ctx)
{
	(void)ctx;
	return k_uptime_get_32();
}

static uint32_t z_rand(void *ctx)
{
	(void)ctx;
	return sys_rand32_get();
}

oc_radio_status_t oc_radio_zephyr_ops(oc_radio_hw_ops_t *ops,
				      const struct device *dev)
{
	if (ops == NULL || dev == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	if (!device_is_ready(dev)) {
		return OC_RADIO_ERR_IO;
	}
	g_dev = dev;
	memset(ops, 0, sizeof(*ops));
	ops->cad = z_cad;
	ops->send = z_send;
	ops->recv = z_recv;
	ops->set_power = z_set_power;
	ops->sleep = z_sleep;
	ops->now_ms = z_now;
	ops->rand32 = z_rand;
	ops->ctx = NULL; /* oc_radio_sx1262_open_zephyr sets to radio */
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_sx1262_open_zephyr(oc_radio_t *radio,
					      const oc_radio_cfg_t *cfg,
					      const struct device *dev)
{
	oc_radio_hw_ops_t ops;
	oc_radio_status_t st;

	st = oc_radio_zephyr_ops(&ops, dev);
	if (st != OC_RADIO_OK) {
		return st;
	}
	st = oc_radio_sx1262_open(radio, cfg, &ops);
	if (st != OC_RADIO_OK) {
		return st;
	}
	radio->hw = (void *)dev;
	radio->ops.ctx = radio;
	return OC_RADIO_OK;
}
