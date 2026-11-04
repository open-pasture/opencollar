#include "sim_radio.h"

#include <string.h>

static uint32_t rng_u32(sim_world_t *w)
{
	/* xorshift64* */
	uint64_t x = w->rng;
	x ^= x >> 12;
	x ^= x << 25;
	x ^= x >> 27;
	w->rng = x;
	return (uint32_t)((x * 0x2545F4914F6CDD1Dull) >> 32);
}

static uint32_t rng_range(sim_world_t *w, uint32_t lo, uint32_t hi)
{
	uint32_t span;
	if (hi < lo) {
		return lo;
	}
	span = hi - lo + 1u;
	if (span == 0) {
		return lo;
	}
	return lo + (rng_u32(w) % span);
}

static int chance(sim_world_t *w, uint16_t pct)
{
	if (pct == 0) {
		return 0;
	}
	if (pct >= 100) {
		return 1;
	}
	return (rng_u32(w) % 100u) < pct;
}

void sim_world_init(sim_world_t *w, uint8_t n_nodes, uint64_t seed)
{
	uint8_t i, j;
	memset(w, 0, sizeof(*w));
	w->rng = seed ? seed : 1;
	w->n_nodes = n_nodes > SIM_MAX_NODES ? SIM_MAX_NODES : n_nodes;
	w->now_ms = 0;
	for (i = 0; i < w->n_nodes; i++) {
		oc_radio_cfg_t cfg;
		oc_radio_limits_t lim;
		oc_radio_t *r = &w->nodes[i];
		memset(&cfg, 0, sizeof(cfg));
		cfg.freq_hz = 903000000u;
		cfg.sf = 8;
		cfg.bw_khz_code = 1; /* PLACEHOLDER: 1 = 500 kHz plan */
		cfg.cr = 5;
		cfg.sync_word = 0x12;
		cfg.tx_dbm = 14;
		memset(&lim, 0, sizeof(lim));
		/* Plan-1-ish defaults; tests may tighten via oc_radio_init. */
		lim.max_frame_airtime_us = 200000u;
		lim.airtime_budget_us_per_h = 3600u * 1000000u / 10u; /* 10% */
		lim.min_tx_gap_ms = 0; /* gossip tests: no gap unless set */
		r->world = w;
		r->id = i;
		r->mtu = 255; /* default LoRa-sized; tests may raise via sim_radio_set_mtu */
		r->bytes_per_ms_air = 2;
		(void)oc_radio_init(r, &cfg, &lim);
		for (j = 0; j < w->n_nodes; j++) {
			w->link[i][j].connected = 0;
		}
	}
}

void sim_world_set_fully_connected(sim_world_t *w, const sim_link_t *proto)
{
	uint8_t i, j;
	for (i = 0; i < w->n_nodes; i++) {
		for (j = 0; j < w->n_nodes; j++) {
			if (i == j) {
				continue;
			}
			w->link[i][j] = *proto;
			w->link[i][j].connected = 1;
		}
	}
}

void sim_world_set_chain(sim_world_t *w, const sim_link_t *proto)
{
	uint8_t i;
	for (i = 0; i + 1 < w->n_nodes; i++) {
		w->link[i][i + 1] = *proto;
		w->link[i][i + 1].connected = 1;
		w->link[i + 1][i] = *proto;
		w->link[i + 1][i].connected = 1;
	}
}

void sim_world_set_link(sim_world_t *w, uint8_t a, uint8_t b, const sim_link_t *ab,
                        const sim_link_t *ba)
{
	if (a >= w->n_nodes || b >= w->n_nodes) {
		return;
	}
	w->link[a][b] = *ab;
	w->link[a][b].connected = 1;
	w->link[b][a] = *ba;
	w->link[b][a].connected = 1;
}

void sim_world_partition(sim_world_t *w, uint8_t a, uint8_t b, int connected)
{
	if (a >= w->n_nodes || b >= w->n_nodes) {
		return;
	}
	w->link[a][b].connected = connected ? 1 : 0;
	w->link[b][a].connected = connected ? 1 : 0;
}

oc_radio_t *sim_radio(sim_world_t *w, uint8_t id)
{
	return id < w->n_nodes ? &w->nodes[id] : NULL;
}

uint32_t sim_world_now(sim_world_t *w)
{
	return w->now_ms;
}

uint32_t sim_clock_ms(void *ctx)
{
	return ((sim_world_t *)ctx)->now_ms;
}

static void enqueue_rx(oc_radio_t *dst, const sim_pending_t *p)
{
	if (dst->rq_count >= 32) {
		return;
	}
	dst->rxq[dst->rq_tail] = *p;
	dst->rq_tail = (uint8_t)((dst->rq_tail + 1) % 32);
	dst->rq_count++;
}

static void deliver_due(sim_world_t *w)
{
	unsigned i;
	for (i = 0; i < SIM_MAX_PENDING; i++) {
		sim_pending_t *p = &w->inflight[i];
		if (!p->used) {
			continue;
		}
		if (p->deliver_at_ms <= w->now_ms) {
			oc_radio_t *dst = &w->nodes[p->dst];
			enqueue_rx(dst, p);
			p->used = 0;
		}
	}
}

void sim_world_advance(sim_world_t *w, uint32_t ms)
{
	w->now_ms += ms;
	deliver_due(w);
}

static int queue_inflight(sim_world_t *w, const sim_pending_t *p)
{
	unsigned i;
	for (i = 0; i < SIM_MAX_PENDING; i++) {
		if (!w->inflight[i].used) {
			w->inflight[i] = *p;
			w->inflight[i].used = 1;
			return 0;
		}
	}
	return -1;
}

static void schedule_to(oc_radio_t *src, uint8_t dst_id, const uint8_t *buf, size_t len)
{
	sim_world_t *w = src->world;
	sim_link_t *L = &w->link[src->id][dst_id];
	sim_pending_t p;
	uint32_t delay;

	if (!L->connected || dst_id == src->id) {
		return;
	}
	if (src->burst_left[dst_id] > 0) {
		src->burst_left[dst_id]--;
		return; /* burst drop */
	}
	if (chance(w, L->burst_pct)) {
		src->burst_left[dst_id] = L->burst_len ? L->burst_len : 3;
		return;
	}
	if (chance(w, L->loss_pct)) {
		return;
	}
	memset(&p, 0, sizeof(p));
	p.src = src->id;
	p.dst = dst_id;
	p.len = (uint16_t)len;
	memcpy(p.data, buf, len);
	p.rssi_dbm = (int16_t)(-40 - (int)(rng_u32(w) % 40u));
	p.snr_db = (int8_t)(5 + (int)(rng_u32(w) % 10u));
	delay = L->latency_ms;
	if (L->latency_jitter_ms) {
		delay += rng_range(w, 0, L->latency_jitter_ms);
	}
	if (chance(w, L->reorder_pct)) {
		delay += rng_range(w, 5, 40);
	}
	p.deliver_at_ms = w->now_ms + delay;
	queue_inflight(w, &p);
	if (chance(w, L->duplicate_pct)) {
		p.deliver_at_ms = w->now_ms + delay + rng_range(w, 1, 10);
		queue_inflight(w, &p);
	}
}

/* ---- HAL implementation ------------------------------------------------- */

static void duty_roll_window(oc_radio_t *radio)
{
	uint32_t now = radio->world->now_ms;
	if (now - radio->duty_window_start_ms >= 3600u * 1000u) {
		radio->duty_window_start_ms = now;
		radio->duty_used_us = 0;
	}
}

oc_radio_status_t oc_radio_init(oc_radio_t *radio, const oc_radio_cfg_t *cfg,
                                const oc_radio_limits_t *lim)
{
	if (!radio || !cfg || !lim) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->cfg = *cfg;
	radio->limits = *lim;
	radio->power_dbm = cfg->tx_dbm;
	radio->asleep = 0;
	radio->duty_used_us = 0;
	radio->duty_window_start_ms = radio->world ? radio->world->now_ms : 0;
	radio->last_tx_ms = 0;
	if (radio->mtu == 0) {
		radio->mtu = 255;
	}
	if (radio->bytes_per_ms_air == 0) {
		radio->bytes_per_ms_air = 2;
	}
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_sleep(oc_radio_t *radio)
{
	if (!radio) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->asleep = 1;
	return OC_RADIO_OK;
}

uint64_t oc_radio_now_us(const oc_radio_t *radio)
{
	if (!radio || !radio->world) {
		return 0;
	}
	return (uint64_t)radio->world->now_ms * 1000ull;
}

oc_radio_status_t oc_radio_send(oc_radio_t *radio, const uint8_t *buf, size_t len,
                                const oc_radio_tx_opts_t *opts)
{
	uint32_t air;
	uint8_t i;
	uint32_t now_ms;

	if (!radio || !buf) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->asleep = 0;
	if (len == 0 || len > radio->mtu || len > SIM_MAX_MTU) {
		return OC_RADIO_ERR_TOO_LARGE;
	}
	air = oc_radio_airtime_us(radio, len);
	if (radio->limits.max_frame_airtime_us && air > radio->limits.max_frame_airtime_us) {
		return OC_RADIO_ERR_AIRTIME;
	}
	duty_roll_window(radio);
	if (radio->limits.airtime_budget_us_per_h &&
	    radio->duty_used_us + air > radio->limits.airtime_budget_us_per_h) {
		return OC_RADIO_ERR_DUTY;
	}
	now_ms = radio->world->now_ms;
	if (radio->limits.min_tx_gap_ms && radio->last_tx_ms != 0 &&
	    now_ms - radio->last_tx_ms < radio->limits.min_tx_gap_ms) {
		return OC_RADIO_ERR_GAP;
	}
	if (opts && opts->tx_power_dbm != OC_RADIO_TX_POWER_DEFAULT) {
		if (opts->tx_power_dbm < 0 || opts->tx_power_dbm > 22) {
			return OC_RADIO_ERR_PARAM;
		}
		/* per-packet override does not permanently change default */
	}
	if (opts && !(opts->flags & OC_RADIO_TX_FLAG_SKIP_CAD)) {
		oc_radio_cad_result_t cad;
		if (oc_radio_cad(radio, &cad, 0) != OC_RADIO_OK) {
			return OC_RADIO_ERR_IO;
		}
		if (cad == OC_RADIO_CAD_BUSY) {
			return OC_RADIO_ERR_BUSY;
		}
	}
	/* at_us: sim is discrete-ms; treat as advisory (no wait loop here). */
	radio->duty_used_us += air;
	radio->last_tx_ms = now_ms;
	radio->world->airtime_us_total += air;
	for (i = 0; i < radio->world->n_nodes; i++) {
		schedule_to(radio, i, buf, len);
	}
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_recv(oc_radio_t *radio, uint8_t *buf, size_t cap, size_t *out_len,
                                oc_radio_rx_meta_t *out_meta, uint32_t timeout_ms)
{
	(void)timeout_ms;
	if (!radio || !buf || !out_len) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->asleep = 0;
	deliver_due(radio->world);
	if (radio->rq_count == 0) {
		return OC_RADIO_ERR_TIMEOUT;
	}
	{
		sim_pending_t *p = &radio->rxq[radio->rq_head];
		if (p->len > cap) {
			return OC_RADIO_ERR_TOO_LARGE;
		}
		memcpy(buf, p->data, p->len);
		*out_len = p->len;
		if (out_meta) {
			out_meta->rssi_dbm = p->rssi_dbm;
			out_meta->snr_db = p->snr_db;
			out_meta->flags = 0;
			out_meta->timestamp_ms = radio->world->now_ms;
			out_meta->t_rx_us = oc_radio_now_us(radio);
			out_meta->peer_id = p->src;
		}
		radio->rq_head = (uint8_t)((radio->rq_head + 1) % 32);
		radio->rq_count--;
	}
	return OC_RADIO_OK;
}

void sim_radio_set_mtu(oc_radio_t *r, uint32_t mtu)
{
	uint32_t air;
	if (!r) {
		return;
	}
	if (mtu == 0 || mtu > SIM_MAX_MTU) {
		mtu = SIM_MAX_MTU;
	}
	r->mtu = mtu;
	/* Host tests may raise MTU for max sealed manifests; keep airtime cap coherent. */
	air = oc_radio_airtime_us(r, mtu);
	if (air > r->limits.max_frame_airtime_us) {
		r->limits.max_frame_airtime_us = air;
	}
}

oc_radio_status_t oc_radio_cad(oc_radio_t *radio, oc_radio_cad_result_t *out,
                               uint32_t timeout_ms)
{
	(void)timeout_ms; /* sim: instantaneous; hardware uses bound (default 50 ms) */
	if (!radio || !out) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->asleep = 0;
	*out = OC_RADIO_CAD_FREE;
	return OC_RADIO_OK;
}

oc_radio_status_t oc_radio_set_power(oc_radio_t *radio, int8_t dbm)
{
	if (!radio) {
		return OC_RADIO_ERR_PARAM;
	}
	if (dbm < 0 || dbm > 22) {
		return OC_RADIO_ERR_PARAM;
	}
	radio->power_dbm = dbm;
	radio->cfg.tx_dbm = dbm;
	return OC_RADIO_OK;
}

uint32_t oc_radio_airtime_us(const oc_radio_t *radio, size_t len)
{
	uint32_t bpm;
	if (!radio || len == 0) {
		return 0;
	}
	bpm = radio->bytes_per_ms_air ? radio->bytes_per_ms_air : 1;
	return (uint32_t)((len * 1000u) / bpm);
}

uint32_t oc_radio_duty_budget_us(const oc_radio_t *radio)
{
	uint32_t lim;
	if (!radio) {
		return 0;
	}
	lim = radio->limits.airtime_budget_us_per_h;
	if (lim == 0) {
		return UINT32_MAX;
	}
	if (radio->duty_used_us >= lim) {
		return 0;
	}
	return lim - radio->duty_used_us;
}

uint32_t oc_radio_backoff_ms(oc_radio_t *radio, uint32_t lo_ms, uint32_t hi_ms)
{
	if (!radio) {
		return lo_ms;
	}
	return rng_range(radio->world, lo_ms, hi_ms);
}

uint32_t oc_radio_trickle_t_ms(oc_radio_t *radio, uint32_t interval_ms)
{
	if (!radio || interval_ms == 0) {
		return 0;
	}
	return rng_range(radio->world, interval_ms / 2u, interval_ms);
}
