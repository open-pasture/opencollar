/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Conforms to firmware/lora/INTEGRATION.md (PR #6).
 */
#include "gossip.h"

#include <string.h>

#ifdef STARLING_HAS_LORA

static void mirror_active_to_geo(struct starling_gossip *g)
{
	const oc_fh_freshness_t *fr;
	struct starling_fence_blob blob;

	if (!g->geo_store) {
		return;
	}
	fr = oc_fh_active(&g->node);
	if (!fr || fr->fence_seq == 0) {
		return;
	}

	memset(&blob, 0, sizeof(blob));
	blob.freshness = *fr;
	blob.verified = true;
	if (g->node.active_len <= sizeof(blob.payload)) {
		blob.payload_len = (uint16_t)g->node.active_len;
		memcpy(blob.payload, g->buf.active_payload, blob.payload_len);
	}
	if (g->node.active_manifest_wire_len <= sizeof(blob.sealed)) {
		blob.sealed_len = (uint16_t)g->node.active_manifest_wire_len;
		memcpy(blob.sealed, g->node.active_manifest_wire, blob.sealed_len);
	}
	/*
	 * Raise geo-store HWM + active mirror. Vertices may be absent for
	 * opaque pilot payloads; fence_store_offer still records seq/hwm.
	 */
	(void)fence_store_offer(g->geo_store, &blob, fr->received_at_ms);
}

int starling_gossip_restore(struct starling_gossip *g)
{
	int rc;

	if (!g || !g->enabled || !g->fh_store) {
		return -1;
	}
	rc = oc_fh_node_restore(&g->node);
	if (rc == OC_FH_OK) {
		g->restored = true;
		mirror_active_to_geo(g);
		return 0;
	}
	/* Empty store is fine — nothing to load. */
	if (rc == OC_FH_ERR_STORE) {
		g->restored = false;
		return 0;
	}
	return rc;
}

void starling_gossip_init(struct starling_gossip *g, struct fence_store *geo_store,
			  oc_fh_store_t *fh_store, uint16_t node_id,
			  const uint8_t farm_id[OC_FH_FARM_ID_LEN], bool starling_serve,
			  oc_radio_t *radio, oc_fh_verify_fn verify, void *verify_ctx,
			  oc_fh_payload_verify_fn payload_verify, void *payload_verify_ctx,
			  uint32_t (*now_ms)(void *), void *clock_ctx)
{
	memset(g, 0, sizeof(*g));
	g->geo_store = geo_store;
	g->fh_store = fh_store;
	g->starling_serve = starling_serve;

	if (!radio || !verify || !now_ms || !farm_id) {
		g->enabled = false;
		return;
	}

	memset(&g->cfg, 0, sizeof(g->cfg));
	g->cfg.node_id = node_id;
	g->cfg.is_rook = 0;
	g->cfg.starling_serve = starling_serve ? 1u : OC_FH_STARLING_SERVE_DEFAULT;
	/* Pilot: accept Rook MANIFEST_LOCAL over the air. */
	g->cfg.accept_local_air = 1;
	memcpy(g->cfg.farm_id, farm_id, OC_FH_FARM_ID_LEN);
	g->cfg.frag_data_max = OC_FH_DEFAULT_FRAG_DATA;
	g->cfg.trickle_imin_ms = OC_FH_TRICKLE_IMIN_MS;
	g->cfg.trickle_imax_ms = OC_FH_TRICKLE_IMAX_MS;
	g->cfg.trickle_k = OC_FH_TRICKLE_K;

	g->buf.active_payload = g->active_payload;
	g->buf.active_cap = STARLING_GOSSIP_PAYLOAD_CAP;
	g->buf.pending_payload = g->pending_payload;
	g->buf.pending_cap = STARLING_GOSSIP_PAYLOAD_CAP;
	g->buf.rx_scratch = g->rx_scratch;
	g->buf.rx_scratch_cap = sizeof(g->rx_scratch);
	g->buf.tx_scratch = g->tx_scratch;
	g->buf.tx_scratch_cap = sizeof(g->tx_scratch);

	oc_fh_node_init(&g->node, &g->cfg, &g->buf, radio, verify, verify_ctx, now_ms, clock_ctx);

	if (fh_store) {
		oc_fh_node_set_store(&g->node, fh_store);
	}
	if (payload_verify) {
		oc_fh_node_set_payload_verify(&g->node, payload_verify, payload_verify_ctx);
	}

	g->enabled = true;

	/* INTEGRATION: restore HWM + active BEFORE any radio poll. */
	(void)starling_gossip_restore(g);
}

void starling_gossip_poll(struct starling_gossip *g)
{
	oc_fh_event_t ev;

	if (!g->enabled) {
		return;
	}
	oc_fh_node_poll(&g->node);
	ev = g->node.last_event;
	if (ev == OC_FH_EV_APPLIED) {
		g->apply_count++;
		mirror_active_to_geo(g);
	} else if (ev == OC_FH_EV_REJECT_SEQ) {
		g->reject_seq_count++;
	}
}

int starling_gossip_inject_opaque(struct starling_gossip *g, const uint8_t *payload, size_t plen,
				  uint32_t fence_seq, uint32_t issued_at)
{
	int rc;

	if (!g->enabled) {
		return -1;
	}
	rc = oc_fh_inject_opaque(&g->node, payload, plen, fence_seq, issued_at);
	if (rc == OC_FH_OK) {
		g->apply_count++;
		mirror_active_to_geo(g);
	} else if (g->node.last_event == OC_FH_EV_REJECT_SEQ) {
		g->reject_seq_count++;
	}
	return rc;
}

int starling_gossip_inject_local(struct starling_gossip *g, const uint8_t *sealed_manifest,
				 size_t mlen, const uint8_t *payload, size_t plen)
{
	int rc;

	if (!g->enabled) {
		return -1;
	}
	rc = oc_fh_inject_local(&g->node, sealed_manifest, mlen, payload, plen);
	if (rc == OC_FH_OK) {
		g->apply_count++;
		mirror_active_to_geo(g);
	} else if (g->node.last_event == OC_FH_EV_REJECT_SEQ) {
		g->reject_seq_count++;
	}
	return rc;
}

#else /* !STARLING_HAS_LORA */

void starling_gossip_init(struct starling_gossip *g, struct fence_store *geo_store, void *fh_store,
			  uint16_t node_id, const uint8_t farm_id[OC_FH_FARM_ID_LEN],
			  bool starling_serve, void *radio, void *verify, void *verify_ctx,
			  void *payload_verify, void *payload_verify_ctx,
			  uint32_t (*now_ms)(void *), void *clock_ctx)
{
	(void)fh_store;
	(void)node_id;
	(void)farm_id;
	(void)radio;
	(void)verify;
	(void)verify_ctx;
	(void)payload_verify;
	(void)payload_verify_ctx;
	(void)now_ms;
	(void)clock_ctx;
	memset(g, 0, sizeof(*g));
	g->geo_store = geo_store;
	g->starling_serve = starling_serve;
	g->enabled = false;
}

int starling_gossip_restore(struct starling_gossip *g)
{
	(void)g;
	return 0;
}

void starling_gossip_poll(struct starling_gossip *g)
{
	(void)g;
}

#endif /* STARLING_HAS_LORA */
