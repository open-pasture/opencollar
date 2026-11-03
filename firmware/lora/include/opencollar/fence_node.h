/*
 * Symmetric fence-gossip node: Rook and Starling run the same exchange.
 * A Rook is a node that also receives fences from the server (inject_local /
 * inject_opaque).
 *
 * starling_serve defaults to OFF (OC_FH_STARLING_SERVE_DEFAULT): only Rooks
 * serve (one-hop star; matches lora.md §1 until the protocol owner decides).
 * starling_serve=1 → any node with a verified fence may re-serve the same
 * signed/local manifest bytes and fragments (multi-hop gossip). Pilot
 * telemetry stays one hop to the Rook regardless.
 *
 * All field/type names are PLACEHOLDERs.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_FENCE_NODE_H
#define OPENCOLLAR_FENCE_NODE_H

#include "opencollar/fence_ids.h"
#include "opencollar/fence_manifest.h"
#include "opencollar/fence_store.h"
#include "opencollar/fence_wire.h"
#include "opencollar/radio_hal.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Explicit status codes (inject / restore). */
#define OC_FH_OK 0
#define OC_FH_ERR_PARAM -1
#define OC_FH_ERR_SIG -2
#define OC_FH_ERR_SEQ -3
#define OC_FH_ERR_HASH -4
#define OC_FH_ERR_MANIFEST_WIRE -5
#define OC_FH_ERR_PAYLOAD -6
#define OC_FH_ERR_STORE -7

typedef enum oc_fh_event {
	OC_FH_EV_NONE = 0,
	OC_FH_EV_APPLIED,
	OC_FH_EV_REJECT_SIG,
	OC_FH_EV_REJECT_SEQ,
	OC_FH_EV_REJECT_HASH,
	OC_FH_EV_GOT_FRAG,
	OC_FH_EV_SERVED,
	OC_FH_EV_BEACON_TX,
	OC_FH_EV_NEED_TX,
	OC_FH_EV_MANIFEST_WIRE_OVF,
	OC_FH_EV_NEED_CAPPED,
	OC_FH_EV_REJECT_PAYLOAD
} oc_fh_event_t;

typedef struct oc_fh_stats {
	uint32_t tx_frames;
	uint32_t rx_frames;
	uint32_t retransmit_frags;
	uint32_t airtime_us;
	uint32_t applied;
	uint32_t reject_sig;
	uint32_t reject_seq;
	uint32_t reject_hash;
	uint32_t reject_payload;
	uint32_t manifest_wire_ovf; /* sealed/local wire would not fit buffer */
	uint32_t need_capped;       /* beacon-hint NEED suppressed by budget */
	uint32_t need_tx;           /* NEED frames actually sent */
} oc_fh_stats_t;

typedef struct oc_fh_config {
	uint16_t node_id;
	uint8_t is_rook;
	uint8_t starling_serve;
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint16_t frag_data_max;
	uint32_t trickle_imin_ms;
	uint32_t trickle_imax_ms;
	uint8_t trickle_k;
} oc_fh_config_t;

typedef struct oc_fh_buffers {
	uint8_t *active_payload;
	size_t active_cap;
	uint8_t *pending_payload;
	size_t pending_cap;
	uint8_t *rx_scratch;
	size_t rx_scratch_cap;
	uint8_t *tx_scratch;
	size_t tx_scratch_cap;
} oc_fh_buffers_t;

/*
 * After opaque (pilot) reassembly: verify the payload bytes themselves
 * (e.g. core v1 command Ed25519). Return 0 on success.
 */
typedef int (*oc_fh_payload_verify_fn)(const uint8_t *payload, size_t len,
                                       uint32_t fence_seq, void *ctx);

typedef struct oc_fh_peer_need {
	uint16_t peer_id;
	uint32_t window_start_ms;
	uint16_t need_count;
	uint8_t used;
} oc_fh_peer_need_t;

typedef struct oc_fh_node oc_fh_node_t;

struct oc_fh_node {
	oc_fh_config_t cfg;
	oc_fh_buffers_t buf;
	oc_radio_t *radio;
	oc_fh_verify_fn verify; /* sealed-manifest Ed25519 (farm key) */
	void *verify_ctx;
	oc_fh_payload_verify_fn payload_verify; /* opaque/pilot payload check */
	void *payload_verify_ctx;
	oc_fh_store_t *store; /* optional; NULL = RAM-only session */
	uint32_t (*now_ms)(void *clock_ctx);
	void *clock_ctx;

	oc_fh_freshness_t active;
	size_t active_len;
	oc_fh_manifest_t active_manifest;
	uint8_t active_manifest_wire[OC_FH_MANIFEST_WIRE_MAX];
	size_t active_manifest_wire_len;
	uint8_t active_is_local; /* 1 = MSG_MANIFEST_LOCAL (unsigned envelope) */
	uint32_t fence_seq_hwm;  /* max accepted; survives via store */

	uint8_t have_pending;
	oc_fh_manifest_t pending_manifest;
	uint8_t pending_manifest_wire[OC_FH_MANIFEST_WIRE_MAX];
	size_t pending_manifest_wire_len;
	uint8_t pending_is_local;
	uint8_t have_frag[OC_FH_MAX_FRAGMENTS];
	uint16_t pending_got;
	size_t pending_len;
	uint16_t pending_source;
	uint8_t pending_from_hint; /* opened by beacon; subject to NEED cap */

	uint32_t trickle_I;
	uint32_t trickle_t;
	uint32_t trickle_c;
	uint32_t trickle_interval_start;
	uint32_t last_beacon_ms;

	uint8_t serve_pending;
	uint32_t serve_at_ms;
	uint32_t serve_target_seq_seen;

	uint8_t need_pending;
	uint32_t need_at_ms;
	uint32_t need_retries;

	/* Global + per-peer budgets for beacon-hint NEEDs. */
	uint32_t need_global_window_start_ms;
	uint16_t need_global_count;
	oc_fh_peer_need_t peer_need[OC_FH_NEED_PEER_SLOTS];
	uint16_t last_rx_peer;

	oc_fh_stats_t stats;
	oc_fh_event_t last_event;
};

void oc_fh_node_init(oc_fh_node_t *n, const oc_fh_config_t *cfg, const oc_fh_buffers_t *buf,
                     oc_radio_t *radio, oc_fh_verify_fn verify, void *verify_ctx,
                     uint32_t (*now_ms)(void *), void *clock_ctx);

/* Optional hooks (call after init, before inject/poll). */
void oc_fh_node_set_store(oc_fh_node_t *n, oc_fh_store_t *store);
void oc_fh_node_set_payload_verify(oc_fh_node_t *n, oc_fh_payload_verify_fn fn, void *ctx);

/*
 * Restore active fence + HWM from store (simulate reboot). Returns OC_FH_OK
 * if a fence was loaded, OC_FH_ERR_STORE if empty/missing, or an error.
 */
int oc_fh_node_restore(oc_fh_node_t *n);

/*
 * Server-issued sealed manifest path (farm Ed25519 over domain||body).
 * Returns OC_FH_OK or OC_FH_ERR_*.
 */
int oc_fh_inject_local(oc_fh_node_t *n, const uint8_t *sealed_manifest, size_t mlen,
                       const uint8_t *payload, size_t plen);

/*
 * PILOT: Rook has no farm signing key. Builds an unsigned local manifest
 * around an already-signed opaque payload (e.g. v1 JSON command). fence_seq
 * is the payload's version. Authenticity = payload_verify after reassembly
 * at receivers. Envelope is NOT signed.
 */
int oc_fh_inject_opaque(oc_fh_node_t *n, const uint8_t *payload, size_t plen,
                        uint32_t fence_seq, uint32_t issued_at);

void oc_fh_node_poll(oc_fh_node_t *n);
int oc_fh_may_serve(const oc_fh_node_t *n);
const oc_fh_freshness_t *oc_fh_active(const oc_fh_node_t *n);
const oc_fh_stats_t *oc_fh_stats(const oc_fh_node_t *n);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_FENCE_NODE_H */
