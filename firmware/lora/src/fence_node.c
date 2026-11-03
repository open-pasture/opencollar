#include "opencollar/fence_node.h"

#include "fence_util.h"

#include <string.h>

typedef char oc_fh_assert_active_wire[(sizeof(((oc_fh_node_t *)0)->active_manifest_wire) >=
                                       OC_FH_MANIFEST_WIRE_MAX)
                                          ? 1
                                          : -1];

static uint32_t now(const oc_fh_node_t *n)
{
	return n->now_ms ? n->now_ms(n->clock_ctx) : 0;
}

int oc_fh_may_serve(const oc_fh_node_t *n)
{
	if (!n || n->active.fence_seq == 0) {
		return 0;
	}
	if (n->cfg.starling_serve) {
		return 1;
	}
	return n->cfg.is_rook ? 1 : 0;
}

const oc_fh_freshness_t *oc_fh_active(const oc_fh_node_t *n)
{
	return n ? &n->active : NULL;
}

const oc_fh_stats_t *oc_fh_stats(const oc_fh_node_t *n)
{
	return n ? &n->stats : NULL;
}

void oc_fh_node_set_store(oc_fh_node_t *n, oc_fh_store_t *store)
{
	if (n) {
		n->store = store;
	}
}

void oc_fh_node_set_payload_verify(oc_fh_node_t *n, oc_fh_payload_verify_fn fn, void *ctx)
{
	if (n) {
		n->payload_verify = fn;
		n->payload_verify_ctx = ctx;
	}
}

void oc_fh_node_init(oc_fh_node_t *n, const oc_fh_config_t *cfg, const oc_fh_buffers_t *buf,
                     oc_radio_t *radio, oc_fh_verify_fn verify, void *verify_ctx,
                     uint32_t (*now_ms_fn)(void *), void *clock_ctx)
{
	memset(n, 0, sizeof(*n));
	n->cfg = *cfg;
	n->buf = *buf;
	n->radio = radio;
	n->verify = verify;
	n->verify_ctx = verify_ctx;
	n->now_ms = now_ms_fn;
	n->clock_ctx = clock_ctx;
	if (n->cfg.frag_data_max == 0) {
		n->cfg.frag_data_max = (uint16_t)OC_FH_DEFAULT_FRAG_DATA;
	}
	if (n->cfg.trickle_imin_ms == 0) {
		n->cfg.trickle_imin_ms = OC_FH_TRICKLE_IMIN_MS;
	}
	if (n->cfg.trickle_imax_ms == 0) {
		n->cfg.trickle_imax_ms = OC_FH_TRICKLE_IMAX_MS;
	}
	if (n->cfg.trickle_k == 0) {
		n->cfg.trickle_k = (uint8_t)OC_FH_TRICKLE_K;
	}
	n->trickle_I = n->cfg.trickle_imin_ms;
	n->trickle_interval_start = now(n);
	n->trickle_t = n->trickle_interval_start +
	               oc_radio_trickle_t_ms(n->radio, n->trickle_I);
}

static uint32_t effective_hwm(const oc_fh_node_t *n)
{
	uint32_t h = n->fence_seq_hwm;
	if (n->active.fence_seq > h) {
		h = n->active.fence_seq;
	}
	return h;
}

/*
 * Persist HWM then active (A/B+CRC contract in fence_store.h). On failure do
 * not advance fence_seq_hwm in RAM beyond what store already holds.
 */
static int persist_fence(oc_fh_node_t *n, const oc_fh_freshness_t *fr, const uint8_t *payload,
                         size_t plen, const uint8_t *wire, size_t mlen,
                         const oc_fh_manifest_t *manifest)
{
	if (!n->store) {
		if (fr->fence_seq > n->fence_seq_hwm) {
			n->fence_seq_hwm = fr->fence_seq;
		}
		return OC_FH_OK;
	}
	if (n->store->set_hwm(n->store, fr->fence_seq) != 0) {
		n->stats.persist_fail++;
		n->last_event = OC_FH_EV_PERSIST_FAIL;
		return OC_FH_ERR_STORE;
	}
	if (n->store->save_active(n->store, fr, payload, plen, wire, mlen, manifest) != 0) {
		n->stats.persist_fail++;
		n->last_event = OC_FH_EV_PERSIST_FAIL;
		return OC_FH_ERR_STORE;
	}
	if (fr->fence_seq > n->fence_seq_hwm) {
		n->fence_seq_hwm = fr->fence_seq;
	}
	return OC_FH_OK;
}

int oc_fh_node_restore(oc_fh_node_t *n)
{
	uint32_t hwm = 0;
	size_t plen = 0, mlen = 0;

	if (!n || !n->store) {
		return OC_FH_ERR_STORE;
	}
	if (n->store->get_hwm(n->store, &hwm) == 0) {
		n->fence_seq_hwm = hwm;
	}
	if (n->store->load_active(n->store, &n->active, n->buf.active_payload, n->buf.active_cap,
	                          &plen, n->active_manifest_wire, sizeof(n->active_manifest_wire),
	                          &mlen, &n->active_manifest) != 0) {
		return OC_FH_ERR_STORE;
	}
	n->active_len = plen;
	n->active_manifest_wire_len = mlen;
	n->active_is_local =
	    (mlen > 0 && n->active_manifest_wire[0] == OC_FH_MSG_MANIFEST_LOCAL) ? 1 : 0;
	if (n->active.fence_seq > n->fence_seq_hwm) {
		n->fence_seq_hwm = n->active.fence_seq;
	}
	return OC_FH_OK;
}

static void trickle_reset(oc_fh_node_t *n)
{
	n->trickle_I = n->cfg.trickle_imin_ms;
	n->trickle_c = 0;
	n->trickle_interval_start = now(n);
	n->trickle_t = n->trickle_interval_start +
	               oc_radio_trickle_t_ms(n->radio, n->trickle_I);
}

static void short_hash_from_poly(uint8_t out[OC_FH_SHORT_HASH_LEN],
                                 const uint8_t poly[OC_FH_POLY_HASH_LEN])
{
	memcpy(out, poly, OC_FH_SHORT_HASH_LEN);
}

static int tx(oc_fh_node_t *n, const uint8_t *buf, size_t len)
{
	oc_radio_status_t st;
	uint32_t air;
	oc_radio_tx_opts_t opts = oc_radio_tx_opts_default();

	opts.flags = OC_RADIO_TX_FLAG_SKIP_CAD; /* protocol schedules; CAD optional */
	st = oc_radio_send(n->radio, buf, len, &opts);
	if (st != OC_RADIO_OK) {
		return (int)st;
	}
	air = oc_radio_airtime_us(n->radio, len);
	n->stats.tx_frames++;
	n->stats.airtime_us += air;
	return 0;
}

static void send_beacon(oc_fh_node_t *n)
{
	oc_fh_beacon_t b;
	size_t len;
	uint32_t t = now(n);

	if (n->active.fence_seq == 0) {
		return;
	}
	if (t - n->last_beacon_ms < OC_FH_BEACON_MIN_GAP_MS && n->last_beacon_ms != 0) {
		return;
	}
	memcpy(b.farm_id, n->cfg.farm_id, OC_FH_FARM_ID_LEN);
	b.fence_seq = n->active.fence_seq;
	short_hash_from_poly(b.short_hash, n->active.poly_hash);
	b.hop_reserved = (uint8_t)OC_FH_HOP_RESERVED;
	len = oc_fh_encode_beacon(&b, n->buf.tx_scratch, n->buf.tx_scratch_cap);
	if (len && tx(n, n->buf.tx_scratch, len) == 0) {
		n->last_beacon_ms = t;
		n->last_event = OC_FH_EV_BEACON_TX;
	}
}

static size_t frag_offset(uint16_t idx, size_t total_len, uint16_t frag_data_max,
                          uint16_t *out_len)
{
	size_t off = (size_t)idx * frag_data_max;
	size_t rem;

	if (off >= total_len) {
		*out_len = 0;
		return 0;
	}
	rem = total_len - off;
	*out_len = (uint16_t)(rem > frag_data_max ? frag_data_max : rem);
	return off;
}

static void serve_active(oc_fh_node_t *n, const oc_fh_need_t *need_or_null)
{
	uint16_t i;
	oc_fh_fragment_t fr;
	size_t len;
	uint16_t dlen;
	size_t off;

	if (!oc_fh_may_serve(n)) {
		return;
	}
	if (n->active_manifest_wire_len == 0) {
		n->stats.manifest_wire_ovf++;
		n->last_event = OC_FH_EV_MANIFEST_WIRE_OVF;
		return;
	}
	if (tx(n, n->active_manifest_wire, n->active_manifest_wire_len) == 0) {
		n->last_event = OC_FH_EV_SERVED;
	}
	for (i = 0; i < n->active_manifest.frag_count; i++) {
		int send_it = 1;
		if (need_or_null) {
			unsigned bit;
			if (i < need_or_null->from) {
				send_it = 0;
			} else {
				bit = (unsigned)(i - need_or_null->from);
				if (bit / 8u >= need_or_null->bitmap_len ||
				    !oc_fh_bitmap_get(need_or_null->bitmap, bit)) {
					send_it = 0;
				}
			}
		}
		if (!send_it) {
			continue;
		}
		off = frag_offset(i, n->active_len, n->cfg.frag_data_max, &dlen);
		if (dlen == 0) {
			continue;
		}
		memcpy(fr.farm_id, n->cfg.farm_id, OC_FH_FARM_ID_LEN);
		fr.fence_seq = n->active.fence_seq;
		fr.idx = i;
		fr.count = n->active_manifest.frag_count;
		fr.data = n->buf.active_payload + off;
		fr.data_len = dlen;
		len = oc_fh_encode_fragment(&fr, n->buf.tx_scratch, n->buf.tx_scratch_cap);
		if (len && tx(n, n->buf.tx_scratch, len) == 0) {
			n->stats.retransmit_frags++;
			n->last_event = OC_FH_EV_SERVED;
		}
	}
}

static void clear_pending(oc_fh_node_t *n)
{
	n->have_pending = 0;
	n->pending_got = 0;
	n->pending_len = 0;
	memset(n->have_frag, 0, sizeof(n->have_frag));
	n->pending_manifest_wire_len = 0;
	n->pending_is_local = 0;
	n->pending_from_hint = 0;
	n->need_pending = 0;
	n->need_retries = 0;
}

static int store_manifest_wire(oc_fh_node_t *n, uint8_t *dst, size_t dst_cap, size_t *dst_len,
                               const uint8_t *wire, size_t wire_len)
{
	if (!wire || wire_len == 0) {
		*dst_len = 0;
		return OC_FH_OK;
	}
	if (wire_len > dst_cap) {
		n->stats.manifest_wire_ovf++;
		n->last_event = OC_FH_EV_MANIFEST_WIRE_OVF;
		return OC_FH_ERR_MANIFEST_WIRE;
	}
	memcpy(dst, wire, wire_len);
	*dst_len = wire_len;
	return OC_FH_OK;
}

static int activate_pending(oc_fh_node_t *n)
{
	uint8_t poly[OC_FH_POLY_HASH_LEN];

	if (!n->have_pending || n->pending_got != n->pending_manifest.frag_count) {
		return -1;
	}
	oc_fh_hash_payload(poly, n->buf.pending_payload, n->pending_len);
	if (memcmp(poly, n->pending_manifest.poly_hash, OC_FH_POLY_HASH_LEN) != 0) {
		n->stats.reject_hash++;
		n->last_event = OC_FH_EV_REJECT_HASH;
		clear_pending(n);
		return -1;
	}
	if (n->pending_is_local) {
		if (!n->payload_verify ||
		    n->payload_verify(n->buf.pending_payload, n->pending_len,
		                      n->pending_manifest.fence_seq, n->payload_verify_ctx) != 0) {
			n->stats.reject_payload++;
			n->last_event = OC_FH_EV_REJECT_PAYLOAD;
			clear_pending(n);
			return -1;
		}
	}
	if (n->pending_len > n->buf.active_cap) {
		clear_pending(n);
		return -1;
	}
	if (n->pending_manifest_wire_len == 0 ||
	    n->pending_manifest_wire_len > sizeof(n->active_manifest_wire)) {
		n->stats.manifest_wire_ovf++;
		n->last_event = OC_FH_EV_MANIFEST_WIRE_OVF;
		clear_pending(n);
		return OC_FH_ERR_MANIFEST_WIRE;
	}
	{
		oc_fh_freshness_t fr;
		memcpy(fr.farm_id, n->pending_manifest.farm_id, OC_FH_FARM_ID_LEN);
		fr.fence_seq = n->pending_manifest.fence_seq;
		memcpy(fr.poly_hash, n->pending_manifest.poly_hash, OC_FH_POLY_HASH_LEN);
		fr.received_at_ms = now(n);
		fr.source_id = n->pending_source;
		/* Persist before mutating active RAM. */
		if (persist_fence(n, &fr, n->buf.pending_payload, n->pending_len,
		                  n->pending_manifest_wire, n->pending_manifest_wire_len,
		                  &n->pending_manifest) != OC_FH_OK) {
			clear_pending(n);
			return OC_FH_ERR_STORE;
		}
		memcpy(n->buf.active_payload, n->buf.pending_payload, n->pending_len);
		n->active_len = n->pending_len;
		n->active_manifest = n->pending_manifest;
		memcpy(n->active_manifest_wire, n->pending_manifest_wire,
		       n->pending_manifest_wire_len);
		n->active_manifest_wire_len = n->pending_manifest_wire_len;
		n->active_is_local = n->pending_is_local;
		n->active = fr;
	}
	n->stats.applied++;
	n->last_event = OC_FH_EV_APPLIED;
	clear_pending(n);
	trickle_reset(n);
	return 0;
}

static int need_budget_allow(oc_fh_node_t *n, uint16_t peer_id)
{
	uint32_t t = now(n);
	unsigned i;
	oc_fh_peer_need_t *slot = NULL;

	if (n->need_global_window_start_ms == 0 ||
	    t - n->need_global_window_start_ms > OC_FH_NEED_WINDOW_MS) {
		n->need_global_window_start_ms = t;
		n->need_global_count = 0;
	}
	if (n->need_global_count >= OC_FH_NEED_WINDOW_GLOBAL_MAX) {
		return 0;
	}
	for (i = 0; i < OC_FH_NEED_PEER_SLOTS; i++) {
		if (n->peer_need[i].used && n->peer_need[i].peer_id == peer_id) {
			slot = &n->peer_need[i];
			break;
		}
	}
	if (!slot) {
		for (i = 0; i < OC_FH_NEED_PEER_SLOTS; i++) {
			if (!n->peer_need[i].used) {
				slot = &n->peer_need[i];
				slot->used = 1;
				slot->peer_id = peer_id;
				slot->window_start_ms = t;
				slot->need_count = 0;
				break;
			}
		}
	}
	if (!slot) {
		/* Evict the oldest window (smallest window_start_ms). */
		unsigned oldest = 0;
		for (i = 1; i < OC_FH_NEED_PEER_SLOTS; i++) {
			if ((int32_t)(n->peer_need[i].window_start_ms -
			              n->peer_need[oldest].window_start_ms) < 0) {
				oldest = i;
			}
		}
		slot = &n->peer_need[oldest];
		slot->peer_id = peer_id;
		slot->window_start_ms = t;
		slot->need_count = 0;
		slot->used = 1;
	}
	if (t - slot->window_start_ms > OC_FH_NEED_WINDOW_MS) {
		slot->window_start_ms = t;
		slot->need_count = 0;
	}
	if (slot->need_count >= OC_FH_NEED_HINT_MAX) {
		return 0;
	}
	slot->need_count++;
	n->need_global_count++;
	return 1;
}

static int begin_pending_from_manifest(oc_fh_node_t *n, const oc_fh_manifest_t *m,
                                       const uint8_t *wire, size_t wire_len, uint16_t source,
                                       int is_local, int from_hint)
{
	uint16_t i;
	size_t total = 0;
	int was_pending = n->have_pending;
	uint32_t old_seq = n->pending_manifest.fence_seq;

	if (m->fence_seq == 0 || m->fence_seq > OC_FH_SEQ_MAX) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return OC_FH_ERR_SEQ;
	}
	if (m->fence_seq <= effective_hwm(n)) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return OC_FH_ERR_SEQ;
	}
	/*
	 * Higher pending seq normally wins. Exception: a sealed (signed)
	 * manifest preempts an unsigned/local pending even with a lower seq,
	 * so a forged LOCAL 0xFFFFFFFF (or any high local) cannot block a real
	 * farm-signed fence.
	 */
	if (n->have_pending && n->pending_manifest.fence_seq > m->fence_seq) {
		if (!(n->pending_is_local && !is_local)) {
			return OC_FH_OK;
		}
		clear_pending(n);
		was_pending = 0;
	}
	if (n->have_pending && n->pending_manifest.fence_seq < m->fence_seq) {
		clear_pending(n);
		was_pending = 0;
	}
	for (i = 0; i < m->frag_count; i++) {
		total += n->cfg.frag_data_max;
	}
	if (total > n->buf.pending_cap || total > OC_FH_MAX_PAYLOAD) {
		return OC_FH_ERR_PARAM;
	}
	if (wire && wire_len > 0) {
		if (wire_len > sizeof(n->pending_manifest_wire)) {
			n->stats.manifest_wire_ovf++;
			n->last_event = OC_FH_EV_MANIFEST_WIRE_OVF;
			return OC_FH_ERR_MANIFEST_WIRE;
		}
	}
	if (!n->have_pending || n->pending_manifest_wire_len == 0 ||
	    n->pending_manifest.fence_seq != m->fence_seq ||
	    n->pending_manifest.frag_count != m->frag_count) {
		memset(n->have_frag, 0, sizeof(n->have_frag));
		n->pending_got = 0;
		n->pending_len = 0;
	}
	n->have_pending = 1;
	n->pending_manifest = *m;
	n->pending_is_local = is_local ? 1 : 0;
	/* Real manifest wire clears the beacon-hint flag so loss recovery
	 * NEEDs are not starved by the anti-DoS budget. */
	if (wire && wire_len > 0) {
		n->pending_from_hint = 0;
		if (store_manifest_wire(n, n->pending_manifest_wire,
		                        sizeof(n->pending_manifest_wire),
		                        &n->pending_manifest_wire_len, wire, wire_len) != OC_FH_OK) {
			clear_pending(n);
			return OC_FH_ERR_MANIFEST_WIRE;
		}
	} else {
		n->pending_from_hint = from_hint ? 1 : 0;
	}
	n->pending_source = source;
	if (!was_pending || old_seq != m->fence_seq) {
		n->pending_started_ms = now(n);
	}
	n->need_pending = 1;
	n->need_at_ms = now(n) + oc_radio_backoff_ms(n->radio, OC_FH_NEED_BACKOFF_LO_MS,
	                                             OC_FH_NEED_BACKOFF_HI_MS);
	return OC_FH_OK;
}

static void send_need(oc_fh_node_t *n)
{
	oc_fh_need_t need;
	uint16_t i;
	size_t len;

	if (!n->have_pending) {
		return;
	}
	/* Cap NEEDs while still waiting for any manifest (forged-beacon DoS).
	 * Budget is per peer / per window (OC_FH_NEED_HINT_MAX); do not use a
	 * lifetime need_retries ceiling or loss recovery never resumes. */
	if (n->pending_from_hint && n->pending_manifest_wire_len == 0) {
		uint16_t peer = n->pending_source ? n->pending_source : n->last_rx_peer;
		if (!need_budget_allow(n, peer)) {
			n->stats.need_capped++;
			n->last_event = OC_FH_EV_NEED_CAPPED;
			n->need_pending = 1;
			n->need_at_ms = now(n) + OC_FH_NEED_WINDOW_MS;
			return;
		}
	}
	memset(&need, 0, sizeof(need));
	memcpy(need.farm_id, n->cfg.farm_id, OC_FH_FARM_ID_LEN);
	need.fence_seq = n->pending_manifest.fence_seq;
	need.from = 0;
	need.bitmap_len = (uint8_t)((n->pending_manifest.frag_count + 7u) / 8u);
	for (i = 0; i < n->pending_manifest.frag_count; i++) {
		if (!n->have_frag[i]) {
			oc_fh_bitmap_set(need.bitmap, i);
		}
	}
	len = oc_fh_encode_need(&need, n->buf.tx_scratch, n->buf.tx_scratch_cap);
	if (len && tx(n, n->buf.tx_scratch, len) == 0) {
		n->last_event = OC_FH_EV_NEED_TX;
		n->need_retries++;
		n->stats.need_tx++;
	}
	n->need_pending = 1;
	n->need_at_ms = now(n) + OC_FH_NEED_RETRY_MS +
	                oc_radio_backoff_ms(n->radio, 0, OC_FH_NEED_BACKOFF_HI_MS);
}

static void on_beacon(oc_fh_node_t *n, const oc_fh_beacon_t *b, uint16_t peer)
{
	if (!oc_fh_farm_eq(b->farm_id, n->cfg.farm_id)) {
		return;
	}
	if (b->fence_seq == n->active.fence_seq && n->active.fence_seq != 0) {
		uint8_t sh[OC_FH_SHORT_HASH_LEN];
		short_hash_from_poly(sh, n->active.poly_hash);
		if (memcmp(sh, b->short_hash, OC_FH_SHORT_HASH_LEN) == 0) {
			n->trickle_c++;
			return;
		}
	}
	if (b->fence_seq < n->active.fence_seq && oc_fh_may_serve(n)) {
		n->serve_pending = 1;
		n->serve_target_seq_seen = b->fence_seq;
		n->serve_at_ms = now(n) + oc_radio_backoff_ms(n->radio, OC_FH_SERVE_BACKOFF_LO_MS,
		                                             OC_FH_SERVE_BACKOFF_HI_MS);
		trickle_reset(n);
		return;
	}
	if (b->fence_seq > effective_hwm(n)) {
		if (!n->have_pending || n->pending_manifest.fence_seq < b->fence_seq) {
			oc_fh_manifest_t shell;
			memset(&shell, 0, sizeof(shell));
			memcpy(shell.farm_id, b->farm_id, OC_FH_FARM_ID_LEN);
			shell.fence_seq = b->fence_seq;
			shell.frag_count = 1;
			memcpy(shell.poly_hash, b->short_hash, OC_FH_SHORT_HASH_LEN);
			/* Shell only; NEED airtime gated in send_need(). */
			(void)begin_pending_from_manifest(n, &shell, NULL, 0, peer, 0, 1);
		}
		trickle_reset(n);
	}
}

static void on_manifest_sealed(oc_fh_node_t *n, const uint8_t *msg, size_t len, uint16_t peer)
{
	oc_fh_manifest_t m;
	int rc;

	rc = oc_fh_manifest_open(msg, len, &m, n->verify, n->verify_ctx);
	if (rc == -2) {
		n->stats.reject_sig++;
		n->last_event = OC_FH_EV_REJECT_SIG;
		return;
	}
	if (rc != 0) {
		return;
	}
	if (!oc_fh_farm_eq(m.farm_id, n->cfg.farm_id)) {
		return;
	}
	if (m.fence_seq == 0 || m.fence_seq > OC_FH_SEQ_MAX) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return;
	}
	if (m.fence_seq <= effective_hwm(n)) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		if (m.fence_seq < n->active.fence_seq && oc_fh_may_serve(n)) {
			n->serve_pending = 1;
			n->serve_at_ms = now(n);
		}
		return;
	}
	(void)begin_pending_from_manifest(n, &m, msg, len, peer, 0, 0);
}

static void on_manifest_local(oc_fh_node_t *n, const uint8_t *msg, size_t len, uint16_t peer)
{
	oc_fh_manifest_t m;

	/*
	 * Air LOCAL is pilot-only: require accept_local_air AND payload_verify.
	 * Otherwise a forged unsigned LOCAL (e.g. seq=0xFFFFFFFF) can become
	 * pending and starve every real lower-seq fence.
	 */
	if (!n->cfg.accept_local_air || !n->payload_verify) {
		n->stats.reject_local_air++;
		n->last_event = OC_FH_EV_REJECT_LOCAL_AIR;
		return;
	}
	if (oc_fh_manifest_open_local(msg, len, &m) != 0) {
		return;
	}
	if (!oc_fh_farm_eq(m.farm_id, n->cfg.farm_id)) {
		return;
	}
	if (m.fence_seq == 0 || m.fence_seq > OC_FH_SEQ_MAX) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return;
	}
	if (m.fence_seq <= effective_hwm(n)) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return;
	}
	(void)begin_pending_from_manifest(n, &m, msg, len, peer, 1, 0);
}

static void on_fragment(oc_fh_node_t *n, const oc_fh_fragment_t *f)
{
	uint8_t h[OC_FH_FRAG_HASH_LEN];
	size_t off;
	size_t end;

	if (!oc_fh_farm_eq(f->farm_id, n->cfg.farm_id) || !n->have_pending) {
		return;
	}
	if (f->fence_seq != n->pending_manifest.fence_seq) {
		if (f->fence_seq <= effective_hwm(n)) {
			n->stats.reject_seq++;
			n->last_event = OC_FH_EV_REJECT_SEQ;
		}
		return;
	}
	if (n->pending_manifest_wire_len == 0) {
		return;
	}
	if (f->count != n->pending_manifest.frag_count || f->idx >= f->count) {
		return;
	}
	oc_fh_hash_fragment(h, f->data, f->data_len);
	if (memcmp(h, n->pending_manifest.frag_hash[f->idx], OC_FH_FRAG_HASH_LEN) != 0) {
		n->stats.reject_hash++;
		n->last_event = OC_FH_EV_REJECT_HASH;
		return;
	}
	off = (size_t)f->idx * n->cfg.frag_data_max;
	end = off + f->data_len;
	if (end > n->buf.pending_cap) {
		return;
	}
	memcpy(n->buf.pending_payload + off, f->data, f->data_len);
	if (!n->have_frag[f->idx]) {
		n->have_frag[f->idx] = 1;
		n->pending_got++;
		n->last_event = OC_FH_EV_GOT_FRAG;
	}
	if (end > n->pending_len) {
		n->pending_len = end;
	}
	if (n->pending_got == n->pending_manifest.frag_count) {
		activate_pending(n);
	}
}

static void on_need(oc_fh_node_t *n, const oc_fh_need_t *need)
{
	if (!oc_fh_farm_eq(need->farm_id, n->cfg.farm_id) || !oc_fh_may_serve(n)) {
		return;
	}
	if (need->fence_seq == n->active.fence_seq) {
		serve_active(n, need);
		n->serve_pending = 0;
		return;
	}
	if (need->fence_seq < n->active.fence_seq) {
		n->serve_pending = 1;
		n->serve_at_ms = now(n) + oc_radio_backoff_ms(n->radio, OC_FH_SERVE_BACKOFF_LO_MS,
		                                             OC_FH_SERVE_BACKOFF_HI_MS);
	}
}

static void on_have(oc_fh_node_t *n, const oc_fh_have_t *h)
{
	if (!oc_fh_farm_eq(h->farm_id, n->cfg.farm_id)) {
		return;
	}
	if (n->serve_pending && h->fence_seq == n->active.fence_seq) {
		n->serve_pending = 0;
	}
	if (h->fence_seq == n->active.fence_seq) {
		n->trickle_c++;
	}
}

static void handle_rx(oc_fh_node_t *n, const uint8_t *buf, size_t len, uint16_t peer)
{
	oc_fh_beacon_t b;
	oc_fh_fragment_t f;
	oc_fh_need_t need;
	oc_fh_have_t have;

	n->stats.rx_frames++;
	n->last_rx_peer = peer;
	if (len == 0) {
		return;
	}
	switch (buf[0]) {
	case OC_FH_MSG_BEACON:
		if (oc_fh_decode_beacon(&b, buf, len) == 0) {
			on_beacon(n, &b, peer);
		}
		break;
	case OC_FH_MSG_MANIFEST:
		on_manifest_sealed(n, buf, len, peer);
		break;
	case OC_FH_MSG_MANIFEST_LOCAL:
		on_manifest_local(n, buf, len, peer);
		break;
	case OC_FH_MSG_FRAGMENT:
		if (oc_fh_decode_fragment(&f, buf, len) == 0) {
			on_fragment(n, &f);
		}
		break;
	case OC_FH_MSG_NEED:
		if (oc_fh_decode_need(&need, buf, len) == 0) {
			on_need(n, &need);
		}
		break;
	case OC_FH_MSG_HAVE:
		if (oc_fh_decode_have(&have, buf, len) == 0) {
			on_have(n, &have);
		}
		break;
	default:
		break;
	}
}

static void trickle_tick(oc_fh_node_t *n)
{
	uint32_t t = now(n);

	if (n->active.fence_seq == 0) {
		return;
	}
	if (t >= n->trickle_t && t < n->trickle_interval_start + n->trickle_I) {
		if (n->trickle_c < n->cfg.trickle_k) {
			send_beacon(n);
		}
		n->trickle_t = n->trickle_interval_start + n->trickle_I;
	}
	if (t >= n->trickle_interval_start + n->trickle_I) {
		n->trickle_I *= 2;
		if (n->trickle_I > n->cfg.trickle_imax_ms) {
			n->trickle_I = n->cfg.trickle_imax_ms;
		}
		n->trickle_c = 0;
		n->trickle_interval_start = t;
		n->trickle_t = t + oc_radio_trickle_t_ms(n->radio, n->trickle_I);
	}
}

void oc_fh_node_poll(oc_fh_node_t *n)
{
	size_t got = 0;
	oc_radio_rx_meta_t meta;
	oc_radio_status_t st;
	uint32_t t;
	int i;

	if (!n || !n->radio) {
		return;
	}
	for (i = 0; i < 8; i++) {
		memset(&meta, 0, sizeof(meta));
		st = oc_radio_recv(n->radio, n->buf.rx_scratch, n->buf.rx_scratch_cap, &got, &meta,
		                   0);
		if (st != OC_RADIO_OK) {
			break;
		}
		handle_rx(n, n->buf.rx_scratch, got, meta.peer_id);
	}
	t = now(n);
	if (n->have_pending) {
		uint32_t pto = n->cfg.pending_timeout_ms ? n->cfg.pending_timeout_ms
		                                         : OC_FH_PENDING_TIMEOUT_MS;
		if (pto > 0 && (t - n->pending_started_ms) >= pto) {
			clear_pending(n);
			n->stats.pending_timeout++;
			n->last_event = OC_FH_EV_PENDING_TIMEOUT;
		}
	}
	if (n->need_pending && t >= n->need_at_ms) {
		n->need_pending = 0;
		if (n->have_pending &&
		    (n->pending_manifest_wire_len == 0 ||
		     n->pending_got < n->pending_manifest.frag_count)) {
			send_need(n);
		}
	}
	if (n->serve_pending && t >= n->serve_at_ms) {
		n->serve_pending = 0;
		serve_active(n, NULL);
	}
	trickle_tick(n);
}

static int activate_from_parts(oc_fh_node_t *n, const oc_fh_manifest_t *m, const uint8_t *wire,
                               size_t mlen, const uint8_t *payload, size_t plen, int is_local)
{
	uint8_t poly[OC_FH_POLY_HASH_LEN];
	uint16_t i;
	size_t off;
	uint16_t dlen;

	if (m->fence_seq == 0 || m->fence_seq > OC_FH_SEQ_MAX || m->fence_seq <= effective_hwm(n)) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return OC_FH_ERR_SEQ;
	}
	oc_fh_hash_payload(poly, payload, plen);
	if (memcmp(poly, m->poly_hash, OC_FH_POLY_HASH_LEN) != 0) {
		n->stats.reject_hash++;
		n->last_event = OC_FH_EV_REJECT_HASH;
		return OC_FH_ERR_HASH;
	}
	off = 0;
	for (i = 0; i < m->frag_count; i++) {
		uint8_t h[OC_FH_FRAG_HASH_LEN];
		size_t rem = plen - off;
		dlen = (uint16_t)(rem > n->cfg.frag_data_max ? n->cfg.frag_data_max : rem);
		if (dlen == 0) {
			return OC_FH_ERR_HASH;
		}
		oc_fh_hash_fragment(h, payload + off, dlen);
		if (memcmp(h, m->frag_hash[i], OC_FH_FRAG_HASH_LEN) != 0) {
			n->stats.reject_hash++;
			n->last_event = OC_FH_EV_REJECT_HASH;
			return OC_FH_ERR_HASH;
		}
		off += dlen;
	}
	if (off != plen || plen > n->buf.active_cap) {
		return OC_FH_ERR_PARAM;
	}
	if (is_local) {
		if (!n->payload_verify ||
		    n->payload_verify(payload, plen, m->fence_seq, n->payload_verify_ctx) != 0) {
			n->stats.reject_payload++;
			n->last_event = OC_FH_EV_REJECT_PAYLOAD;
			return OC_FH_ERR_PAYLOAD;
		}
	}
	{
		uint8_t wire_tmp[OC_FH_MANIFEST_WIRE_MAX];
		size_t wire_tmp_len = 0;
		oc_fh_freshness_t fr;

		if (store_manifest_wire(n, wire_tmp, sizeof(wire_tmp), &wire_tmp_len, wire,
		                        mlen) != OC_FH_OK) {
			return OC_FH_ERR_MANIFEST_WIRE;
		}
		memcpy(fr.farm_id, m->farm_id, OC_FH_FARM_ID_LEN);
		fr.fence_seq = m->fence_seq;
		memcpy(fr.poly_hash, m->poly_hash, OC_FH_POLY_HASH_LEN);
		fr.received_at_ms = now(n);
		fr.source_id = n->cfg.node_id;
		/* Persist before mutating active RAM. */
		if (persist_fence(n, &fr, payload, plen, wire_tmp, wire_tmp_len, m) != OC_FH_OK) {
			return OC_FH_ERR_STORE;
		}
		memcpy(n->buf.active_payload, payload, plen);
		n->active_len = plen;
		n->active_manifest = *m;
		memcpy(n->active_manifest_wire, wire_tmp, wire_tmp_len);
		n->active_manifest_wire_len = wire_tmp_len;
		n->active_is_local = is_local ? 1 : 0;
		n->active = fr;
	}
	n->stats.applied++;
	n->last_event = OC_FH_EV_APPLIED;
	clear_pending(n);
	trickle_reset(n);
	return OC_FH_OK;
}

int oc_fh_inject_local(oc_fh_node_t *n, const uint8_t *sealed_manifest, size_t mlen,
                       const uint8_t *payload, size_t plen)
{
	oc_fh_manifest_t m;
	int rc;

	if (!n || !sealed_manifest || !payload) {
		return OC_FH_ERR_PARAM;
	}
	if (mlen > sizeof(n->active_manifest_wire)) {
		n->stats.manifest_wire_ovf++;
		n->last_event = OC_FH_EV_MANIFEST_WIRE_OVF;
		return OC_FH_ERR_MANIFEST_WIRE;
	}
	rc = oc_fh_manifest_open(sealed_manifest, mlen, &m, n->verify, n->verify_ctx);
	if (rc == -2) {
		n->stats.reject_sig++;
		n->last_event = OC_FH_EV_REJECT_SIG;
		return OC_FH_ERR_SIG;
	}
	if (rc != 0) {
		return OC_FH_ERR_PARAM;
	}
	if (!oc_fh_farm_eq(m.farm_id, n->cfg.farm_id)) {
		return OC_FH_ERR_PARAM;
	}
	return activate_from_parts(n, &m, sealed_manifest, mlen, payload, plen, 0);
}

int oc_fh_inject_opaque(oc_fh_node_t *n, const uint8_t *payload, size_t plen, uint32_t fence_seq,
                        uint32_t issued_at)
{
	oc_fh_manifest_t m;
	uint8_t wire[OC_FH_MANIFEST_WIRE_MAX];
	size_t wlen;
	uint16_t count;
	uint16_t i;
	size_t off;
	uint16_t frag_max;

	if (!n || !payload || plen == 0 || plen > OC_FH_MAX_PAYLOAD || fence_seq == 0) {
		return OC_FH_ERR_PARAM;
	}
	frag_max = n->cfg.frag_data_max ? n->cfg.frag_data_max : (uint16_t)OC_FH_DEFAULT_FRAG_DATA;
	count = (uint16_t)((plen + frag_max - 1) / frag_max);
	if (count == 0 || count > OC_FH_MAX_FRAGMENTS) {
		return OC_FH_ERR_PARAM;
	}
	memset(&m, 0, sizeof(m));
	memcpy(m.farm_id, n->cfg.farm_id, OC_FH_FARM_ID_LEN);
	m.fence_seq = fence_seq;
	m.issued_at = issued_at;
	m.frag_count = count;
	oc_fh_hash_payload(m.poly_hash, payload, plen);
	off = 0;
	for (i = 0; i < count; i++) {
		size_t rem = plen - off;
		uint16_t dlen = (uint16_t)(rem > frag_max ? frag_max : rem);
		oc_fh_hash_fragment(m.frag_hash[i], payload + off, dlen);
		off += dlen;
	}
	wlen = oc_fh_manifest_encode_local(&m, wire, sizeof(wire));
	if (wlen == 0) {
		n->stats.manifest_wire_ovf++;
		n->last_event = OC_FH_EV_MANIFEST_WIRE_OVF;
		return OC_FH_ERR_MANIFEST_WIRE;
	}
	return activate_from_parts(n, &m, wire, wlen, payload, plen, 1);
}
