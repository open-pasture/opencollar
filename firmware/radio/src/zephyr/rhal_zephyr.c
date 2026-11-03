/*
 * Zephyr SX126x backend for radio_hal (NCS v3.4.1 / Zephyr 4.4.2).
 * Uses the in-tree native driver: CONFIG_LORA_MODULE_BACKEND_NATIVE.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_hal.h"
#include "radio_us915.h"

#include <zephyr/device.h>
#include <zephyr/drivers/lora.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <string.h>

LOG_MODULE_REGISTER(rhal_zephyr, LOG_LEVEL_INF);

struct rhal_zephyr_ctx {
	const struct device *dev;
	struct rhal_cfg cfg;
	int8_t power_dbm;
};

static struct rhal_zephyr_ctx g_ctx;

static enum lora_signal_bandwidth bw_to_zephyr(uint8_t code)
{
	switch (code) {
	case 1:
		return BW_250_KHZ;
	case 2:
		return BW_500_KHZ;
	case 0:
	default:
		return BW_125_KHZ;
	}
}

static enum lora_coding_rate cr_to_zephyr(uint8_t cr)
{
	/* Our CR is 5..8 (4/5..4/8); Zephyr uses 1..4. */
	if (cr >= 5u && cr <= 8u) {
		return (enum lora_coding_rate)(cr - 4u);
	}
	return CR_4_5;
}

static int apply_config(struct rhal_zephyr_ctx *c, bool tx)
{
	struct lora_modem_config mc;

	memset(&mc, 0, sizeof(mc));
	mc.frequency = c->cfg.freq_hz;
	mc.bandwidth = bw_to_zephyr(c->cfg.bw_khz_code);
	mc.datarate = (enum lora_datarate)c->cfg.sf;
	mc.coding_rate = cr_to_zephyr(c->cfg.cr);
	mc.preamble_len = RADIO_US915_PREAMBLE;
	mc.tx_power = c->power_dbm;
	mc.tx = tx;
	mc.iq_inverted = false;
	/* sync_word 0x12 → private network (public_network = false). */
	mc.public_network = (c->cfg.sync_word == 0x34);
#if defined(LORA_CAD_MODE_NONE)
	mc.cad.mode = LORA_CAD_MODE_NONE;
	mc.cad.symbol_num = LORA_CAD_SYMB_2;
#endif
	return lora_config(c->dev, &mc);
}

static uint64_t z_now_us(void *ctx)
{
	(void)ctx;
	return k_ticks_to_us_floor64(k_uptime_ticks());
}

static int z_init(void *ctx, const struct rhal_cfg *cfg)
{
	struct rhal_zephyr_ctx *c = ctx;

	if (c == NULL || cfg == NULL) {
		return RHAL_E_INVAL;
	}
	if (!device_is_ready(c->dev)) {
		LOG_ERR("lora device not ready");
		return RHAL_E_IO;
	}
	c->cfg = *cfg;
	c->power_dbm = cfg->tx_dbm;
	if (apply_config(c, false) != 0) {
		return RHAL_E_IO;
	}
	return RHAL_OK;
}

static void z_deinit(void *ctx)
{
	(void)ctx;
}

static int z_set_power(void *ctx, int8_t dbm)
{
	struct rhal_zephyr_ctx *c = ctx;

	c->power_dbm = dbm;
	return apply_config(c, false) == 0 ? RHAL_OK : RHAL_E_IO;
}

static int z_cad(void *ctx, uint32_t timeout_ms)
{
	struct rhal_zephyr_ctx *c = ctx;
	int rc;

	if (apply_config(c, false) != 0) {
		return RHAL_E_IO;
	}
	rc = lora_cad(c->dev, K_MSEC(timeout_ms ? timeout_ms : 50));
	if (rc == 0 || rc == 1) {
		return rc;
	}
	if (rc == -ENOSYS) {
		/* Older backend without CAD: treat as clear (LBT best-effort). */
		LOG_WRN("lora_cad unsupported; assuming clear");
		return 0;
	}
	return RHAL_E_IO;
}

static int z_send(void *ctx, const uint8_t *buf, uint8_t len, int8_t dbm)
{
	struct rhal_zephyr_ctx *c = ctx;
	uint8_t tmp[255];

	c->power_dbm = dbm;
	if (apply_config(c, true) != 0) {
		return RHAL_E_IO;
	}
	/* lora_send wants non-const; copy to stack. */
	if (len > sizeof(tmp)) {
		return RHAL_E_INVAL;
	}
	memcpy(tmp, buf, len);
	if (lora_send(c->dev, tmp, len) != 0) {
		return RHAL_E_IO;
	}
	return RHAL_OK;
}

static int z_recv(void *ctx, struct rhal_rx *out, uint32_t window_ms)
{
	struct rhal_zephyr_ctx *c = ctx;
	int n;

	if (apply_config(c, false) != 0) {
		return RHAL_E_IO;
	}
	memset(out, 0, sizeof(*out));
	n = lora_recv(c->dev, out->buf, sizeof(out->buf),
		      K_MSEC(window_ms), &out->rssi_dbm, &out->snr_db);
	if (n < 0) {
		return (n == -EAGAIN || n == -ETIMEDOUT) ? RHAL_E_TIMEOUT : RHAL_E_IO;
	}
	out->len = (uint8_t)n;
	out->t_rx_us = z_now_us(ctx);
	return RHAL_OK;
}

static int z_sleep(void *ctx)
{
	(void)ctx;
	/*
	 * Zephyr LoRa API has no explicit sleep; duty-cycle RX covers low-power
	 * listening. Leaving the modem in the last RX/standby config is fine
	 * for bring-up; starling/rook apps will add PM later.
	 */
	return RHAL_OK;
}

int rhal_zephyr_platform(struct rhal_platform *plat, const struct device *dev)
{
	if (plat == NULL || dev == NULL) {
		return RHAL_E_INVAL;
	}
	memset(&g_ctx, 0, sizeof(g_ctx));
	g_ctx.dev = dev;
	memset(plat, 0, sizeof(*plat));
	plat->now_us = z_now_us;
	plat->init = z_init;
	plat->deinit = z_deinit;
	plat->set_power = z_set_power;
	plat->cad = z_cad;
	plat->send = z_send;
	plat->recv = z_recv;
	plat->sleep = z_sleep;
	plat->ctx = &g_ctx;
	return RHAL_OK;
}
