#include "opencollar/fence_node.h"

#include "fence_util.h"

#include <string.h>

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

	st = oc_radio_send(n->radio, buf, len, NULL);
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

static size_t frag_offset(const oc_fh_manifest_t *m, uint16_t idx, size_t total_len,
                          uint16_t frag_data_max, uint16_t *out_len)
{
	size_t off = (size_t)idx * frag_data_max;
	size_t rem;

	if (off >= total_len) {
		*out_len = 0;
		return 0;
	}
	rem = total_len - off;
	*out_len = (uint16_t)(rem > frag_data_max ? frag_data_max : rem);
	(void)m;
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
	/* Manifest first. */
	if (n->active_manifest_wire_len) {
		if (tx(n, n->active_manifest_wire, n->active_manifest_wire_len) == 0) {
			n->last_event = OC_FH_EV_SERVED;
		}
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
		off = frag_offset(&n->active_manifest, i, n->active_len, n->cfg.frag_data_max,
		                  &dlen);
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
	n->need_pending = 0;
	n->need_retries = 0;
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
	/* Keep last-good until this point; now swap. */
	if (n->pending_len > n->buf.active_cap) {
		clear_pending(n);
		return -1;
	}
	memcpy(n->buf.active_payload, n->buf.pending_payload, n->pending_len);
	n->active_len = n->pending_len;
	n->active_manifest = n->pending_manifest;
	memcpy(n->active_manifest_wire, n->pending_manifest_wire,
	       n->pending_manifest_wire_len);
	n->active_manifest_wire_len = n->pending_manifest_wire_len;
	memcpy(n->active.farm_id, n->pending_manifest.farm_id, OC_FH_FARM_ID_LEN);
	n->active.fence_seq = n->pending_manifest.fence_seq;
	memcpy(n->active.poly_hash, n->pending_manifest.poly_hash, OC_FH_POLY_HASH_LEN);
	n->active.received_at_ms = now(n);
	n->active.source_id = n->pending_source;
	n->stats.applied++;
	n->last_event = OC_FH_EV_APPLIED;
	clear_pending(n);
	trickle_reset(n);
	return 0;
}

static void begin_pending_from_manifest(oc_fh_node_t *n, const oc_fh_manifest_t *m,
                                        const uint8_t *wire, size_t wire_len,
                                        uint16_t source)
{
	uint16_t i;
	size_t total = 0;
	uint16_t dlen;

	if (m->fence_seq <= n->active.fence_seq) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return;
	}
	if (n->have_pending && n->pending_manifest.fence_seq > m->fence_seq) {
		return; /* already assembling something newer */
	}
	if (n->have_pending && n->pending_manifest.fence_seq < m->fence_seq) {
		clear_pending(n); /* supersede older in-flight */
	}
	/* Estimate payload size from fragment layout: last frag may be short;
	 * we learn exact length as fragments arrive. Cap check uses max. */
	for (i = 0; i < m->frag_count; i++) {
		total += n->cfg.frag_data_max;
	}
	if (total > n->buf.pending_cap || total > OC_FH_MAX_PAYLOAD) {
		return;
	}
	/* Upgrading a beacon shell (no sealed wire yet) or starting fresh:
	 * always reset fragment progress when the sealed manifest arrives. */
	if (!n->have_pending || n->pending_manifest_wire_len == 0 ||
	    n->pending_manifest.fence_seq != m->fence_seq ||
	    n->pending_manifest.frag_count != m->frag_count) {
		memset(n->have_frag, 0, sizeof(n->have_frag));
		n->pending_got = 0;
		n->pending_len = 0;
	}
	n->have_pending = 1;
	n->pending_manifest = *m;
	if (wire && wire_len > 0 && wire_len <= sizeof(n->pending_manifest_wire)) {
		memcpy(n->pending_manifest_wire, wire, wire_len);
		n->pending_manifest_wire_len = wire_len;
	}
	n->pending_source = source;
	n->need_pending = 1;
	n->need_at_ms = now(n) + oc_radio_backoff_ms(n->radio, OC_FH_NEED_BACKOFF_LO_MS,
	                                             OC_FH_NEED_BACKOFF_HI_MS);
	(void)dlen;
}

static void send_need(oc_fh_node_t *n)
{
	oc_fh_need_t need;
	uint16_t i;
	size_t len;

	if (!n->have_pending) {
		return;
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
	}
	/* Schedule another NEED while incomplete (loss recovery). */
	n->need_pending = 1;
	n->need_at_ms = now(n) + OC_FH_NEED_RETRY_MS +
	                oc_radio_backoff_ms(n->radio, 0, OC_FH_NEED_BACKOFF_HI_MS);
}

static void on_beacon(oc_fh_node_t *n, const oc_fh_beacon_t *b)
{
	if (!oc_fh_farm_eq(b->farm_id, n->cfg.farm_id)) {
		return;
	}
	/* Beacons never change state directly — only schedule bounded actions. */
	if (b->fence_seq == n->active.fence_seq && n->active.fence_seq != 0) {
		uint8_t sh[OC_FH_SHORT_HASH_LEN];
		short_hash_from_poly(sh, n->active.poly_hash);
		if (memcmp(sh, b->short_hash, OC_FH_SHORT_HASH_LEN) == 0) {
			n->trickle_c++;
			return;
		}
	}
	if (b->fence_seq < n->active.fence_seq && oc_fh_may_serve(n)) {
		/* Neighbor is stale: schedule serve with backoff/suppression. */
		n->serve_pending = 1;
		n->serve_target_seq_seen = b->fence_seq;
		n->serve_at_ms = now(n) + oc_radio_backoff_ms(n->radio, OC_FH_SERVE_BACKOFF_LO_MS,
		                                             OC_FH_SERVE_BACKOFF_HI_MS);
		trickle_reset(n);
		return;
	}
	if (b->fence_seq > n->active.fence_seq) {
		/* Newer out there: ask for it (bounded NEED). */
		if (!n->have_pending || n->pending_manifest.fence_seq < b->fence_seq) {
			/* Soft-start pending shell so NEED can go out; manifest fills later. */
			oc_fh_manifest_t shell;
			memset(&shell, 0, sizeof(shell));
			memcpy(shell.farm_id, b->farm_id, OC_FH_FARM_ID_LEN);
			shell.fence_seq = b->fence_seq;
			shell.frag_count = 1; /* placeholder until manifest arrives */
			memcpy(shell.poly_hash, b->short_hash, OC_FH_SHORT_HASH_LEN);
			begin_pending_from_manifest(n, &shell, NULL, 0, 0);
			n->have_pending = 1; /* mark awaiting manifest */
			n->pending_manifest = shell;
			n->need_pending = 1;
			n->need_at_ms =
			    now(n) + oc_radio_backoff_ms(n->radio, OC_FH_NEED_BACKOFF_LO_MS,
			                                OC_FH_NEED_BACKOFF_HI_MS);
		}
		trickle_reset(n);
	}
}

static void on_manifest(oc_fh_node_t *n, const uint8_t *msg, size_t len)
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
	if (m.fence_seq <= n->active.fence_seq) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		/* Peer heard us needing old stuff — if they are stale relative to us, serve. */
		if (m.fence_seq < n->active.fence_seq && oc_fh_may_serve(n)) {
			n->serve_pending = 1;
			n->serve_at_ms = now(n);
		}
		return;
	}
	begin_pending_from_manifest(n, &m, msg, len, 0);
}

static void on_fragment(oc_fh_node_t *n, const oc_fh_fragment_t *f)
{
	uint8_t h[OC_FH_FRAG_HASH_LEN];
	size_t off;
	uint16_t expect_len;
	size_t end;

	if (!oc_fh_farm_eq(f->farm_id, n->cfg.farm_id)) {
		return;
	}
	if (!n->have_pending) {
		return;
	}
	if (f->fence_seq != n->pending_manifest.fence_seq) {
		if (f->fence_seq <= n->active.fence_seq) {
			n->stats.reject_seq++;
			n->last_event = OC_FH_EV_REJECT_SEQ;
		}
		return;
	}
	/* Manifest must be real (not beacon shell) before accepting frags. */
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
	} else {
		/* replace allowed */
		memcpy(n->buf.pending_payload + off, f->data, f->data_len);
	}
	if (end > n->pending_len) {
		n->pending_len = end;
	}
	(void)expect_len;
	if (n->pending_got == n->pending_manifest.frag_count) {
		activate_pending(n);
	}
}

static void on_need(oc_fh_node_t *n, const oc_fh_need_t *need)
{
	if (!oc_fh_farm_eq(need->farm_id, n->cfg.farm_id)) {
		return;
	}
	if (!oc_fh_may_serve(n)) {
		return;
	}
	if (need->fence_seq == n->active.fence_seq) {
		/* Someone else may also serve — small backoff suppression. */
		n->serve_pending = 1;
		n->serve_at_ms = now(n) + oc_radio_backoff_ms(n->radio, OC_FH_SERVE_BACKOFF_LO_MS,
		                                             OC_FH_SERVE_BACKOFF_HI_MS);
		/* Store need in tx path by serving immediately with filter:
		 * for simplicity serve filtered now and clear pending. */
		serve_active(n, need);
		n->serve_pending = 0;
		return;
	}
	if (need->fence_seq < n->active.fence_seq) {
		/* They want an older fence; offer ours instead. */
		n->serve_pending = 1;
		n->serve_at_ms = now(n) + oc_radio_backoff_ms(n->radio, OC_FH_SERVE_BACKOFF_LO_MS,
		                                             OC_FH_SERVE_BACKOFF_HI_MS);
	}
}

static void on_have(oc_fh_node_t *n, const oc_fh_have_t *h)
{
	/* Suppression: if we planned to serve the same seq, cancel. */
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

static void handle_rx(oc_fh_node_t *n, const uint8_t *buf, size_t len)
{
	oc_fh_beacon_t b;
	oc_fh_fragment_t f;
	oc_fh_need_t need;
	oc_fh_have_t have;

	n->stats.rx_frames++;
	if (len == 0) {
		return;
	}
	switch (buf[0]) {
	case OC_FH_MSG_BEACON:
		if (oc_fh_decode_beacon(&b, buf, len) == 0) {
			on_beacon(n, &b);
		}
		break;
	case OC_FH_MSG_MANIFEST:
		on_manifest(n, buf, len);
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
		/* ensure we only fire once per interval */
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

	if (!n || !n->radio) {
		return;
	}
	/* Drain a few frames per poll. */
	for (int i = 0; i < 8; i++) {
		st = oc_radio_recv(n->radio, n->buf.rx_scratch, n->buf.rx_scratch_cap, &got,
		                   &meta, 0);
		if (st != OC_RADIO_OK) {
			break;
		}
		handle_rx(n, n->buf.rx_scratch, got);
	}
	t = now(n);
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

int oc_fh_inject_local(oc_fh_node_t *n, const uint8_t *sealed_manifest, size_t mlen,
                       const uint8_t *payload, size_t plen)
{
	oc_fh_manifest_t m;
	int rc;
	uint8_t poly[OC_FH_POLY_HASH_LEN];
	uint16_t i;
	size_t off;
	uint16_t dlen;

	if (!n || !sealed_manifest || !payload) {
		return -1;
	}
	rc = oc_fh_manifest_open(sealed_manifest, mlen, &m, n->verify, n->verify_ctx);
	if (rc == -2) {
		n->stats.reject_sig++;
		n->last_event = OC_FH_EV_REJECT_SIG;
		return -2;
	}
	if (rc != 0) {
		return -1;
	}
	if (!oc_fh_farm_eq(m.farm_id, n->cfg.farm_id)) {
		return -1;
	}
	if (m.fence_seq <= n->active.fence_seq) {
		n->stats.reject_seq++;
		n->last_event = OC_FH_EV_REJECT_SEQ;
		return -3;
	}
	oc_fh_hash_payload(poly, payload, plen);
	if (memcmp(poly, m.poly_hash, OC_FH_POLY_HASH_LEN) != 0) {
		n->stats.reject_hash++;
		n->last_event = OC_FH_EV_REJECT_HASH;
		return -4;
	}
	/* Verify each fragment hash against payload split. */
	off = 0;
	for (i = 0; i < m.frag_count; i++) {
		uint8_t h[OC_FH_FRAG_HASH_LEN];
		size_t rem = plen - off;
		dlen = (uint16_t)(rem > n->cfg.frag_data_max ? n->cfg.frag_data_max : rem);
		if (dlen == 0) {
			return -4;
		}
		oc_fh_hash_fragment(h, payload + off, dlen);
		if (memcmp(h, m.frag_hash[i], OC_FH_FRAG_HASH_LEN) != 0) {
			n->stats.reject_hash++;
			n->last_event = OC_FH_EV_REJECT_HASH;
			return -4;
		}
		off += dlen;
	}
	if (off != plen || plen > n->buf.active_cap) {
		return -1;
	}
	memcpy(n->buf.active_payload, payload, plen);
	n->active_len = plen;
	n->active_manifest = m;
	if (mlen <= sizeof(n->active_manifest_wire)) {
		memcpy(n->active_manifest_wire, sealed_manifest, mlen);
		n->active_manifest_wire_len = mlen;
	}
	memcpy(n->active.farm_id, m.farm_id, OC_FH_FARM_ID_LEN);
	n->active.fence_seq = m.fence_seq;
	memcpy(n->active.poly_hash, m.poly_hash, OC_FH_POLY_HASH_LEN);
	n->active.received_at_ms = now(n);
	n->active.source_id = n->cfg.node_id;
	n->stats.applied++;
	n->last_event = OC_FH_EV_APPLIED;
	clear_pending(n);
	trickle_reset(n);
	return 0;
}
