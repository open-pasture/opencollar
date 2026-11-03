/*
 * oc_radio_* — implements firmware/lora/include/opencollar/radio_hal.h
 * on top of an SX1262 (or mock) ops table.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "opencollar/radio_sx1262.h"
#include "radio_airtime.h"

#include <string.h>

void oc_radio_cfg_us915_defaults(oc_radio_cfg_t *cfg)
{
	if (cfg == NULL) {
		return;
	}
	memset(cfg, 0, sizeof(*cfg));
	cfg->freq_hz = OC_RADIO_US915_FREQ_HZ;
	cfg->sf = OC_RADIO_US915_SF_DEFAULT;
	cfg->bw_khz_code = OC_RADIO_US915_BW_CODE_125K;
	cfg->cr = OC_RADIO_US915_CR_4_5;
	cfg->preamble = 8;
	cfg->sync_word = 0x12;
	cfg->tx_power_dbm = OC_RADIO_US915_TX_CAP_DBM;
	cfg->tx_power_cap_dbm = OC_RADIO_US915_TX_CAP_DBM;
	cfg->mtu = OC_RADIO_MTU;
	cfg->duty_window_us = OC_RADIO_US915_DUTY_WINDOW_US;
	cfg->duty_limit_us = OC_RADIO_US915_DUTY_LIMIT_US;
	cfg->dwell_limit_us = OC_RADIO_US915_DWELL_LIMIT_US;
	cfg->dwell_window_ms = OC_RADIO_US915_DWELL_WINDOW_MS;
	cfg->min_tx_gap_ms = OC_RADIO_US915_MIN_TX_GAP_MS;
	cfg->max_frame_airtime_us = OC_RADIO_US915_MAX_FRAME_AIR_US;
	cfg->cad_before_tx = true;
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

static uint32_t now_ms(const oc_radio_t *r)
{
	if (r->ops.now_ms) {
		return r->ops.now_ms(r->ops.ctx);
	}
	return 0u;
}

static void roll_duty(oc_radio_t *r, uint32_t t_ms)
{
	uint32_t window_ms;

	if (r->cfg.duty_window_us == 0u) {
		return;
	}
	window_ms = r->cfg.duty_window_us / 1000u;
	if (window_ms == 0u) {
		window_ms = 1u;
	}
	if (t_ms - r->duty_window_start_ms >= window_ms) {
		r->duty_window_start_ms = t_ms;
		r->duty_used_us = 0u;
	}
}

static void roll_dwell(oc_radio_t *r, uint32_t t_ms)
{
	uint32_t w = r->cfg.dwell_window_ms ? r->cfg.dwell_window_ms : 1u;

	if (t_ms - r->dwell_window_start_ms >= w) {
		r->dwell_window_start_ms = t_ms;
		r->dwell_used_us = 0u;
	}
}

oc_radio_status_t oc_radio_sx1262_open(oc_radio_t *radio,
				       const oc_radio_cfg_t *cfg,
				       const oc_radio_hw_ops_t *ops)
{
	if (radio == NULL || cfg == NULL || ops == NULL ||
	    ops->cad == NULL || ops->send == NULL || ops->recv == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	memset(radio, 0, sizeof(*radio));
	radio->cfg = *cfg;
	radio->ops = *ops;
	/* Zephyr ops use ops.ctx = oc_radio_t*; stash device from prior bind. */
	if (radio->ops.ctx == NULL) {
		radio->ops.ctx = radio;
	}
	if (radio->cfg.mtu == 0u) {
		radio->cfg.mtu = OC_RADIO_MTU;
	}
	if (radio->cfg.sf < 7u || radio->cfg.sf > 12u) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->power_dbm = cfg->tx_power_dbm;
	if (radio->power_dbm > radio->cfg.tx_power_cap_dbm) {
		radio->power_dbm = radio->cfg.tx_power_cap_dbm;
	}
	radio->rng = 0xC0FFEEULL ^ (uint64_t)now_ms(radio);
	if (radio->rng == 0ull) {
		radio->rng = 1ull;
	}
	radio->duty_window_start_ms = now_ms(radio);
	radio->dwell_window_start_ms = radio->duty_window_start_ms;
	radio->dwell_freq_hz = radio->cfg.freq_hz;
	radio->inited = true;
	return OC_RADIO_OK;
}

void oc_radio_sx1262_close(oc_radio_t *radio)
{
	if (radio == NULL) {
		return;
	}
	radio->inited = false;
}

oc_radio_status_t oc_radio_sx1262_sleep(oc_radio_t *radio)
{
	if (radio == NULL || !radio->inited) {
		return OC_RADIO_ERR_PARAM;
	}
	if (radio->ops.sleep == NULL) {
		return OC_RADIO_ERR_UNSUPPORTED;
	}
	return radio->ops.sleep(radio->ops.ctx);
}

uint32_t oc_radio_sx1262_now_ms(const oc_radio_t *radio)
{
	if (radio == NULL || !radio->inited) {
		return 0u;
	}
	return now_ms(radio);
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
	p.coding_rate = radio->cfg.cr;
	p.preamble_symbols = radio->cfg.preamble ? radio->cfg.preamble : 8u;
	p.explicit_header = true;
	p.crc_on = true;
	return radio_airtime_packet_us(&p, len);
}

uint32_t oc_radio_duty_budget_us(const oc_radio_t *radio)
{
	oc_radio_t *r;
	uint32_t t;

	if (radio == NULL || !radio->inited) {
		return 0u;
	}
	/* roll on a mutable copy view — const API but window is time-based */
	r = (oc_radio_t *)radio;
	t = now_ms(r);
	roll_duty(r, t);
	if (r->cfg.duty_limit_us <= r->duty_used_us) {
		return 0u;
	}
	return r->cfg.duty_limit_us - r->duty_used_us;
}

oc_radio_status_t oc_radio_set_power(oc_radio_t *radio, int8_t dbm)
{
	if (radio == NULL || !radio->inited) {
		return OC_RADIO_ERR_PARAM;
	}
	if (dbm > radio->cfg.tx_power_cap_dbm) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->power_dbm = dbm;
	if (radio->ops.set_power) {
		return radio->ops.set_power(radio->ops.ctx, dbm);
	}
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_cad(oc_radio_t *radio, oc_radio_cad_result_t *out)
{
	if (radio == NULL || !radio->inited || out == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	return radio->ops.cad(radio->ops.ctx, out);
}

oc_radio_status_t oc_radio_recv(oc_radio_t *radio, uint8_t *buf, size_t cap,
				size_t *out_len, oc_radio_rx_meta_t *out_meta,
				uint32_t timeout_ms)
{
	if (radio == NULL || !radio->inited || buf == NULL || out_len == NULL) {
		return OC_RADIO_ERR_PARAM;
	}
	return radio->ops.recv(radio->ops.ctx, buf, cap, out_len, out_meta,
			       timeout_ms);
}

oc_radio_status_t oc_radio_send(oc_radio_t *radio, const uint8_t *buf,
				size_t len, const oc_radio_tx_opts_t *opts)
{
	uint32_t air;
	uint32_t t;
	int8_t pwr;
	oc_radio_status_t st;
	oc_radio_cad_result_t cad;
	uint32_t dwell_used;

	if (radio == NULL || !radio->inited || buf == NULL || len == 0u) {
		return OC_RADIO_ERR_PARAM;
	}
	if (len > radio->cfg.mtu) {
		return OC_RADIO_ERR_TOO_LARGE;
	}

	air = oc_radio_airtime_us(radio, len);
	if (air == 0u) {
		return OC_RADIO_ERR_PARAM;
	}
	if (radio->cfg.max_frame_airtime_us &&
	    air > radio->cfg.max_frame_airtime_us) {
		/* Airtime over the per-frame cap — DUTY (budget family).
		 * TOO_LARGE is reserved for MTU byte length per radio_hal.h. */
		return OC_RADIO_ERR_DUTY;
	}

	t = now_ms(radio);
	roll_duty(radio, t);
	roll_dwell(radio, t);

	if (radio->cfg.min_tx_gap_ms && radio->last_tx_end_ms != 0u &&
	    t < radio->last_tx_end_ms + radio->cfg.min_tx_gap_ms) {
		return OC_RADIO_ERR_DUTY;
	}
	if (radio->cfg.duty_limit_us &&
	    radio->duty_used_us + air > radio->cfg.duty_limit_us) {
		return OC_RADIO_ERR_DUTY;
	}

	if (radio->cfg.dwell_limit_us) {
		dwell_used = (radio->cfg.freq_hz == radio->dwell_freq_hz) ?
				     radio->dwell_used_us :
				     0u;
		if (dwell_used + air > radio->cfg.dwell_limit_us) {
			return OC_RADIO_ERR_DUTY;
		}
	}

	pwr = radio->power_dbm;
	if (opts && opts->tx_power_dbm != OC_RADIO_TX_POWER_DEFAULT) {
		pwr = opts->tx_power_dbm;
	}
	if (pwr > radio->cfg.tx_power_cap_dbm) {
		return OC_RADIO_ERR_PARAM;
	}

	if (radio->cfg.cad_before_tx) {
		st = radio->ops.cad(radio->ops.ctx, &cad);
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

	t = now_ms(radio);
	roll_duty(radio, t);
	roll_dwell(radio, t);
	radio->duty_used_us += air;
	if (radio->cfg.freq_hz != radio->dwell_freq_hz) {
		radio->dwell_freq_hz = radio->cfg.freq_hz;
		radio->dwell_used_us = 0u;
		radio->dwell_window_start_ms = t;
	}
	radio->dwell_used_us += air;
	radio->last_tx_end_ms = t;
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
