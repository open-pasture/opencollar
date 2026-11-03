/*
 * Implements firmware/lora/include/opencollar/radio_hal.h for SX1262 / mock.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "opencollar/radio_sx1262.h"
#include "radio_airtime.h"

#include <stdio.h>
#include <string.h>

#ifdef __ZEPHYR__
#include <zephyr/logging/log.h>
LOG_MODULE_REGISTER(oc_radio_hal, LOG_LEVEL_INF);
#endif

static void log_skip_cad(oc_radio_t *radio)
{
	radio->skip_cad_count++;
#ifdef __ZEPHYR__
	LOG_INF("SKIP_CAD (count=%u); duty/gap limits still enforced",
		radio->skip_cad_count);
#else
	fprintf(stderr, "oc_radio: SKIP_CAD (count=%u)\n", radio->skip_cad_count);
#endif
}

void oc_radio_cfg_us915_defaults(oc_radio_cfg_t *cfg, oc_radio_limits_t *lim)
{
	if (cfg) {
		memset(cfg, 0, sizeof(*cfg));
		cfg->freq_hz = OC_RADIO_US915_FREQ_HZ;
		cfg->sf = OC_RADIO_US915_SF_DEFAULT;
		cfg->bw_khz_code = OC_RADIO_US915_BW_CODE_125K;
		cfg->cr = OC_RADIO_US915_CR_4_5;
		cfg->sync_word = 0x12;
		cfg->tx_dbm = OC_RADIO_US915_TX_CAP_DBM;
	}
	if (lim) {
		memset(lim, 0, sizeof(*lim));
		lim->max_frame_airtime_us = OC_RADIO_US915_MAX_FRAME_AIR_US;
		lim->airtime_budget_us_per_h = OC_RADIO_US915_BUDGET_US_PER_H;
		lim->min_tx_gap_ms = OC_RADIO_US915_MIN_TX_GAP_MS;
	}
}

static uint32_t bw_hz(uint8_t code)
{
	switch (code) {
	case 1:
		return 250000u;
	case 2:
		return 500000u;
	default:
		return 125000u;
	}
}

static uint64_t now_us(const oc_radio_t *r)
{
	if (r->ops.now_us) {
		return r->ops.now_us(r->ops.ctx);
	}
	return 0ull;
}

oc_radio_status_t oc_radio_sx1262_bind(oc_radio_t *radio,
				       const oc_radio_hw_ops_t *ops)
{
	if (radio == NULL || ops == NULL || ops->cad == NULL ||
	    ops->send == NULL || ops->recv == NULL || ops->now_us == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	memset(radio, 0, sizeof(*radio));
	radio->ops = *ops;
	if (radio->ops.ctx == NULL) {
		radio->ops.ctx = radio;
	}
	radio->mtu = OC_RADIO_MTU;
	radio->preamble = OC_RADIO_US915_PREAMBLE;
	radio->tx_power_cap_dbm = OC_RADIO_US915_TX_CAP_DBM;
	radio->cad_before_tx = true;
	radio->cad_timeout_default_ms = CONFIG_RADIO_CAD_TIMEOUT_MS;
	radio->skip_cad_count = 0u;
	radio->dwell_limit_us = OC_RADIO_US915_DWELL_LIMIT_US;
	radio->dwell_window_ms = OC_RADIO_US915_DWELL_WINDOW_MS;
	radio->bound = true;
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_init(oc_radio_t *radio, const oc_radio_cfg_t *cfg,
				const oc_radio_limits_t *lim)
{
	uint64_t t;

	if (radio == NULL || cfg == NULL || lim == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	if (!radio->bound) {
		/* Backend must bind ops/hw first (mock or Zephyr). */
		return OC_RADIO_ERR_PARAM;
	}
	if (cfg->sf < 7u || cfg->sf > 12u) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->cfg = *cfg;
	radio->lim = *lim;
	radio->power_dbm = cfg->tx_dbm;
	if (radio->power_dbm > radio->tx_power_cap_dbm) {
		radio->power_dbm = radio->tx_power_cap_dbm;
	}
	t = now_us(radio);
	radio->duty_used_us = 0u;
	radio->duty_window_start_us = t;
	radio->dwell_used_us = 0u;
	radio->dwell_window_start_ms = (uint32_t)(t / 1000ull);
	radio->dwell_freq_hz = cfg->freq_hz;
	radio->last_tx_end_us = 0ull;
	radio->rng = 0xC0FFEEULL ^ t;
	if (radio->rng == 0ull) {
		radio->rng = 1ull;
	}
	radio->inited = true;
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_sleep(oc_radio_t *radio)
{
	if (radio == NULL || !radio->inited) {
		return OC_RADIO_ERR_PARAM;
	}
	if (radio->ops.sleep == NULL) {
		return OC_RADIO_ERR_UNSUPPORTED;
	}
	return radio->ops.sleep(radio->ops.ctx);
}

uint64_t oc_radio_now_us(const oc_radio_t *radio)
{
	if (radio == NULL || !radio->inited) {
		return 0ull;
	}
	return now_us(radio);
}

static void roll_hourly(oc_radio_t *r, uint64_t t_us)
{
	const uint64_t hour = 3600ull * 1000000ull;

	if (t_us - r->duty_window_start_us >= hour) {
		r->duty_window_start_us = t_us;
		r->duty_used_us = 0u;
	}
}

static void roll_dwell(oc_radio_t *r, uint32_t t_ms)
{
	uint32_t w = r->dwell_window_ms ? r->dwell_window_ms : 1u;

	if (t_ms - r->dwell_window_start_ms >= w) {
		r->dwell_window_start_ms = t_ms;
		r->dwell_used_us = 0u;
	}
}

uint32_t oc_radio_airtime_us(const oc_radio_t *radio, size_t len)
{
	struct radio_airtime_params p;

	if (radio == NULL || !radio->inited) {
		return 0u;
	}
	memset(&p, 0, sizeof(p));
	p.bandwidth_hz = bw_hz(radio->cfg.bw_khz_code);
	p.spreading_factor = radio->cfg.sf;
	p.coding_rate = radio->cfg.cr ? radio->cfg.cr : 5u;
	p.preamble_symbols = radio->preamble ? radio->preamble : 8u;
	p.explicit_header = true;
	p.crc_on = true;
	return radio_airtime_packet_us(&p, len);
}

uint32_t oc_radio_duty_budget_us(const oc_radio_t *radio)
{
	oc_radio_t *r;
	uint64_t t;

	if (radio == NULL || !radio->inited) {
		return 0u;
	}
	r = (oc_radio_t *)radio;
	t = now_us(r);
	roll_hourly(r, t);
	if (r->lim.airtime_budget_us_per_h <= r->duty_used_us) {
		return 0u;
	}
	return r->lim.airtime_budget_us_per_h - r->duty_used_us;
}

oc_radio_status_t oc_radio_set_power(oc_radio_t *radio, int8_t dbm)
{
	if (radio == NULL || !radio->inited) {
		return OC_RADIO_ERR_PARAM;
	}
	if (dbm > radio->tx_power_cap_dbm) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->power_dbm = dbm;
	if (radio->ops.set_power) {
		return radio->ops.set_power(radio->ops.ctx, dbm);
	}
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_cad(oc_radio_t *radio, oc_radio_cad_result_t *out,
			       uint32_t timeout_ms)
{
	uint32_t t;

	if (radio == NULL || !radio->inited || out == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	t = timeout_ms ? timeout_ms : radio->cad_timeout_default_ms;
	return radio->ops.cad(radio->ops.ctx, out, t);
}

oc_radio_status_t oc_radio_recv(oc_radio_t *radio, uint8_t *buf, size_t cap,
				size_t *out_len, oc_radio_rx_meta_t *out_meta,
				uint32_t timeout_ms)
{
	oc_radio_status_t st;

	if (radio == NULL || !radio->inited || buf == NULL || out_len == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	st = radio->ops.recv(radio->ops.ctx, buf, cap, out_len, out_meta,
			     timeout_ms);
	if (st == OC_RADIO_OK && out_meta) {
		if (out_meta->t_rx_us == 0ull) {
			out_meta->t_rx_us = now_us(radio);
		}
		/*
		 * peer_id: SX1262 PHY has no addressing. Leave 0 unless a
		 * higher layer / sim backend fills it. Documented in RUNBOOK.
		 */
	}
	return st;
}

oc_radio_status_t oc_radio_send(oc_radio_t *radio, const uint8_t *buf,
				size_t len, const oc_radio_tx_opts_t *opts)
{
	uint32_t air;
	uint64_t t;
	uint64_t at_us;
	int8_t pwr;
	oc_radio_status_t st;
	oc_radio_cad_result_t cad;
	uint32_t dwell_used;
	uint32_t t_ms;

	if (radio == NULL || !radio->inited || buf == NULL || len == 0u) {
		return OC_RADIO_ERR_PARAM;
	}
	if (len > radio->mtu) {
		return OC_RADIO_ERR_TOO_LARGE;
	}

	air = oc_radio_airtime_us(radio, len);
	if (air == 0u) {
		return OC_RADIO_ERR_PARAM;
	}
	if (radio->lim.max_frame_airtime_us &&
	    air > radio->lim.max_frame_airtime_us) {
		return OC_RADIO_ERR_AIRTIME;
	}

	at_us = (opts && opts->at_us) ? opts->at_us : 0ull;
	t = now_us(radio);
	if (at_us != 0ull && at_us > t) {
		while ((t = now_us(radio)) < at_us) {
			/* busy-wait; Zephyr backend may sleep inside now_us */
		}
	}

	t = now_us(radio);
	roll_hourly(radio, t);
	t_ms = (uint32_t)(t / 1000ull);
	roll_dwell(radio, t_ms);

	if (radio->lim.min_tx_gap_ms && radio->last_tx_end_us != 0ull) {
		uint64_t gap_us = (uint64_t)radio->lim.min_tx_gap_ms * 1000ull;

		if (t < radio->last_tx_end_us + gap_us) {
			return OC_RADIO_ERR_GAP;
		}
	}
	if (radio->lim.airtime_budget_us_per_h &&
	    radio->duty_used_us + air > radio->lim.airtime_budget_us_per_h) {
		return OC_RADIO_ERR_DUTY;
	}
	if (radio->dwell_limit_us) {
		dwell_used = (radio->cfg.freq_hz == radio->dwell_freq_hz) ?
				     radio->dwell_used_us :
				     0u;
		if (dwell_used + air > radio->dwell_limit_us) {
			return OC_RADIO_ERR_DUTY; /* dwell shares duty family */
		}
	}

	pwr = radio->power_dbm;
	if (opts && opts->tx_power_dbm != OC_RADIO_TX_POWER_DEFAULT) {
		pwr = opts->tx_power_dbm;
	}
	if (pwr > radio->tx_power_cap_dbm) {
		return OC_RADIO_ERR_PARAM;
	}

	if (opts && (opts->flags & OC_RADIO_TX_FLAG_SKIP_CAD)) {
		log_skip_cad(radio);
	} else if (radio->cad_before_tx) {
		st = radio->ops.cad(radio->ops.ctx, &cad,
				    radio->cad_timeout_default_ms);
		if (st != OC_RADIO_OK) {
			return st;
		}
		if (cad == OC_RADIO_CAD_BUSY) {
			return OC_RADIO_ERR_BUSY;
		}
	}

	st = radio->ops.send(radio->ops.ctx, buf, len, pwr);
	if (st != OC_RADIO_OK) {
		return st;
	}

	t = now_us(radio);
	roll_hourly(radio, t);
	t_ms = (uint32_t)(t / 1000ull);
	roll_dwell(radio, t_ms);
	radio->duty_used_us += air;
	if (radio->cfg.freq_hz != radio->dwell_freq_hz) {
		radio->dwell_freq_hz = radio->cfg.freq_hz;
		radio->dwell_used_us = 0u;
		radio->dwell_window_start_ms = t_ms;
	}
	radio->dwell_used_us += air;
	radio->last_tx_end_us = t;
	return OC_RADIO_OK;
}

static uint32_t next_u32(oc_radio_t *radio)
{
	uint64_t x;

	if (radio->ops.rand32) {
		return radio->ops.rand32(radio->ops.ctx);
	}
	x = radio->rng;
	x ^= x >> 12;
	x ^= x << 25;
	x ^= x >> 27;
	radio->rng = x ? x : 1ull;
	return (uint32_t)((x * 0x2545F4914F6CDD1Dull) >> 32);
}

uint32_t oc_radio_backoff_ms(oc_radio_t *radio, uint32_t lo_ms, uint32_t hi_ms)
{
	uint32_t span;

	if (radio == NULL || !radio->inited) {
		return lo_ms;
	}
	if (hi_ms < lo_ms) {
		return lo_ms;
	}
	span = hi_ms - lo_ms + 1u;
	if (span == 0u) {
		return lo_ms;
	}
	return lo_ms + (next_u32(radio) % span);
}

uint32_t oc_radio_trickle_t_ms(oc_radio_t *radio, uint32_t interval_ms)
{
	if (interval_ms == 0u) {
		return 0u;
	}
	return oc_radio_backoff_ms(radio, interval_ms / 2u, interval_ms);
}
