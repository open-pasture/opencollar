/*
 * Radio HAL core: limits, CAD-before-TX, airtime accounting.
 * SPDX-License-Identifier: Apache-2.0
 */
#include "radio_hal_priv.h"
#include "radio_backoff.h"
#include "radio_us915.h"

#include <string.h>

_Static_assert(sizeof(struct rhal_state) <= sizeof(struct rhal),
	       "rhal storage too small");

struct rhal_state *rhal_state(struct rhal *h)
{
	return h ? (struct rhal_state *)(void *)h->storage : NULL;
}

const struct rhal_state *rhal_state_c(const struct rhal *h)
{
	return h ? (const struct rhal_state *)(const void *)h->storage : NULL;
}

uint32_t rhal_bw_hz(uint8_t bw_khz_code)
{
	switch (bw_khz_code) {
	case 0:
		return 125000u;
	case 1:
		return 250000u;
	case 2:
		return 500000u;
	default:
		return 125000u;
	}
}

static void hour_tick(struct rhal_state *s, uint64_t now_us)
{
	if (now_us - s->hour_start_us >= 3600ull * 1000000ull) {
		s->hour_start_us = now_us;
		s->hour_used_us = 0u;
	}
}

static struct radio_airtime_params air_params(const struct rhal_state *s)
{
	struct radio_airtime_params p;

	memset(&p, 0, sizeof(p));
	p.bandwidth_hz = rhal_bw_hz(s->cfg.bw_khz_code);
	p.spreading_factor = s->cfg.sf;
	p.coding_rate = s->cfg.cr;
	p.preamble_symbols = RADIO_US915_PREAMBLE;
	p.explicit_header = true;
	p.crc_on = true;
	p.low_data_rate = false;
	return p;
}

int rhal_init(struct rhal *h, const struct rhal_cfg *cfg,
	      const struct rhal_limits *lim, const struct rhal_platform *plat)
{
	struct rhal_state *s = rhal_state(h);
	struct rhal_limits def_lim;
	int rc;

	if (s == NULL || cfg == NULL || plat == NULL || plat->now_us == NULL ||
	    plat->send == NULL || plat->recv == NULL || plat->cad == NULL) {
		return RHAL_E_INVAL;
	}
	memset(s, 0, sizeof(*s));
	s->cfg = *cfg;
	if (s->cfg.sf < 7u || s->cfg.sf > 12u) {
		return RHAL_E_INVAL;
	}
	if (s->cfg.cr < 5u || s->cfg.cr > 8u) {
		s->cfg.cr = 5u;
	}
	if (lim) {
		s->lim = *lim;
	} else {
		memset(&def_lim, 0, sizeof(def_lim));
		def_lim.max_frame_airtime_us = 400000u;          /* 400 ms dwell cap */
		def_lim.airtime_budget_us_per_h = 36000000u;     /* 1 % of an hour */
		def_lim.min_tx_gap_ms = 100u;
		def_lim.dwell_limit_us = RADIO_US915_DWELL_LIMIT_US;
		def_lim.dwell_window_ms = RADIO_US915_DWELL_WINDOW_MS;
		def_lim.tx_power_cap_dbm = RADIO_US915_TX_CAP_DBM_DEFAULT;
		s->lim = def_lim;
	}
	if (s->lim.tx_power_cap_dbm == 0) {
		s->lim.tx_power_cap_dbm = RADIO_US915_TX_CAP_DBM_DEFAULT;
	}
	s->plat = *plat;
	s->cur_power_dbm = s->cfg.tx_dbm;
	if (s->cur_power_dbm > s->lim.tx_power_cap_dbm) {
		s->cur_power_dbm = s->lim.tx_power_cap_dbm;
	}
	radio_duty_init(&s->duty,
			s->lim.dwell_window_ms ? s->lim.dwell_window_ms :
						RADIO_US915_DWELL_WINDOW_MS,
			/* rolling window unused for hourly; use dwell only here */
			0u,
			s->lim.dwell_window_ms ? s->lim.dwell_window_ms :
						 RADIO_US915_DWELL_WINDOW_MS,
			s->lim.dwell_limit_us ? s->lim.dwell_limit_us :
						RADIO_US915_DWELL_LIMIT_US);

	s->hour_start_us = plat->now_us(plat->ctx);
	s->hour_used_us = 0u;
	s->last_tx_end_us = 0u;

	if (plat->init) {
		rc = plat->init(plat->ctx, &s->cfg);
		if (rc != RHAL_OK) {
			return rc;
		}
	}
	s->inited = true;
	return RHAL_OK;
}

void rhal_deinit(struct rhal *h)
{
	struct rhal_state *s = rhal_state(h);

	if (s == NULL || !s->inited) {
		return;
	}
	if (s->plat.deinit) {
		s->plat.deinit(s->plat.ctx);
	}
	s->inited = false;
}

int rhal_set_power(struct rhal *h, int8_t tx_dbm)
{
	struct rhal_state *s = rhal_state(h);

	if (s == NULL || !s->inited) {
		return RHAL_E_INVAL;
	}
	if (tx_dbm > s->lim.tx_power_cap_dbm) {
		return RHAL_E_POWER;
	}
	s->cur_power_dbm = tx_dbm;
	if (s->plat.set_power) {
		return s->plat.set_power(s->plat.ctx, tx_dbm);
	}
	return RHAL_OK;
}

uint32_t rhal_airtime_us(const struct rhal *h, uint8_t len)
{
	const struct rhal_state *s = rhal_state_c(h);
	struct radio_airtime_params p;

	if (s == NULL || !s->inited) {
		return 0u;
	}
	p = air_params(s);
	return radio_airtime_packet_us(&p, len);
}

uint32_t rhal_airtime_left_us(const struct rhal *h)
{
	const struct rhal_state *s = rhal_state_c(h);
	uint64_t now;
	uint32_t used;

	if (s == NULL || !s->inited) {
		return 0u;
	}
	now = s->plat.now_us(s->plat.ctx);
	used = s->hour_used_us;
	if (now - s->hour_start_us >= 3600ull * 1000000ull) {
		used = 0u;
	}
	if (s->lim.airtime_budget_us_per_h <= used) {
		return 0u;
	}
	return s->lim.airtime_budget_us_per_h - used;
}

uint64_t rhal_now_us(struct rhal *h)
{
	struct rhal_state *s = rhal_state(h);

	if (s == NULL || !s->inited || s->plat.now_us == NULL) {
		return 0ull;
	}
	return s->plat.now_us(s->plat.ctx);
}

int rhal_cad(struct rhal *h, uint32_t timeout_ms)
{
	struct rhal_state *s = rhal_state(h);
	int rc;

	if (s == NULL || !s->inited) {
		return RHAL_E_INVAL;
	}
	rc = s->plat.cad(s->plat.ctx, timeout_ms);
	/* Normalize: platform returns 0 clear, 1 busy, <0 error. */
	return rc;
}

int rhal_sleep(struct rhal *h)
{
	struct rhal_state *s = rhal_state(h);

	if (s == NULL || !s->inited) {
		return RHAL_E_INVAL;
	}
	if (s->plat.sleep) {
		return s->plat.sleep(s->plat.ctx);
	}
	return RHAL_OK;
}

int rhal_recv(struct rhal *h, struct rhal_rx *out, uint32_t window_ms)
{
	struct rhal_state *s = rhal_state(h);

	if (s == NULL || !s->inited || out == NULL) {
		return RHAL_E_INVAL;
	}
	return s->plat.recv(s->plat.ctx, out, window_ms);
}

int rhal_send(struct rhal *h, const uint8_t *buf, uint8_t len, uint64_t at_us)
{
	return rhal_send_ex(h, buf, len, at_us, NULL);
}

int rhal_send_ex(struct rhal *h, const uint8_t *buf, uint8_t len, uint64_t at_us,
		 const struct rhal_tx_opts *opts)
{
	struct rhal_state *s = rhal_state(h);
	uint64_t now;
	uint32_t air;
	int8_t pwr;
	int rc;
	uint32_t cad_ms;
	uint32_t now_ms;

	if (s == NULL || !s->inited || buf == NULL || len == 0u) {
		return RHAL_E_INVAL;
	}

	air = rhal_airtime_us(h, len);
	if (air == 0u) {
		return RHAL_E_INVAL;
	}
	if (s->lim.max_frame_airtime_us && air > s->lim.max_frame_airtime_us) {
		return RHAL_E_BUDGET;
	}

	now = s->plat.now_us(s->plat.ctx);
	if (at_us != 0ull && at_us > now) {
		/* Busy-wait style; Zephyr backend may sleep. Host mock advances. */
		while ((now = s->plat.now_us(s->plat.ctx)) < at_us) {
			/* platform may yield inside now_us; keep spinning lightly */
		}
	}
	now = s->plat.now_us(s->plat.ctx);
	hour_tick(s, now);

	if (s->lim.min_tx_gap_ms && s->last_tx_end_us != 0ull) {
		uint64_t gap_us = (uint64_t)s->lim.min_tx_gap_ms * 1000ull;
		if (now < s->last_tx_end_us + gap_us) {
			return RHAL_E_BUDGET;
		}
	}

	if (s->lim.airtime_budget_us_per_h &&
	    s->hour_used_us + air > s->lim.airtime_budget_us_per_h) {
		return RHAL_E_BUDGET;
	}

	now_ms = (uint32_t)(now / 1000ull);
	if (s->lim.dwell_limit_us &&
	    !radio_duty_allow(&s->duty, now_ms, s->cfg.freq_hz, air)) {
		return RHAL_E_BUDGET;
	}

	pwr = s->cur_power_dbm;
	if (opts && opts->tx_dbm != INT8_MIN) {
		pwr = opts->tx_dbm;
	}
	if (pwr > s->lim.tx_power_cap_dbm) {
		return RHAL_E_POWER;
	}

	if (!(opts && opts->skip_cad)) {
		cad_ms = (opts && opts->cad_timeout_ms) ? opts->cad_timeout_ms : 50u;
		rc = s->plat.cad(s->plat.ctx, cad_ms);
		if (rc < 0) {
			return rc;
		}
		if (rc == 1) {
			return RHAL_E_BUSY;
		}
	}

	rc = s->plat.send(s->plat.ctx, buf, len, pwr);
	if (rc != RHAL_OK) {
		return rc;
	}

	now = s->plat.now_us(s->plat.ctx);
	hour_tick(s, now);
	s->hour_used_us += air;
	s->last_tx_end_us = now;
	now_ms = (uint32_t)(now / 1000ull);
	radio_duty_account(&s->duty, now_ms, s->cfg.freq_hz, air);
	return RHAL_OK;
}

void rhal_seed_rng(uint32_t seed)
{
	radio_backoff_seed(seed);
}

uint32_t rhal_backoff_ms(uint32_t attempt, uint32_t min_ms, uint32_t max_ms)
{
	return radio_backoff_ms(attempt, min_ms, max_ms);
}
