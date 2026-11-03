/*
 * Symmetric fence-gossip node: Rook and Starling run the same exchange.
 * A Rook is a node that also receives fences from the server (inject_local).
 *
 * starling_serve defaults to OFF (OC_FH_STARLING_SERVE_DEFAULT): only Rooks
 * serve (one-hop star; matches lora.md §1 until the protocol owner decides).
 * starling_serve=1 → any node with a verified fence may re-serve the same
 * signed manifest/fragments (multi-hop gossip). Pilot telemetry stays one
 * hop to the Rook regardless.
 *
 * All field/type names are PLACEHOLDERs.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_FENCE_NODE_H
#define OPENCOLLAR_FENCE_NODE_H

#include "opencollar/fence_ids.h"
#include "opencollar/fence_manifest.h"
#include "opencollar/fence_wire.h"
#include "opencollar/radio_hal.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum oc_fh_event {
	OC_FH_EV_NONE = 0,
	OC_FH_EV_APPLIED,     /* new fence activated after full verify */
	OC_FH_EV_REJECT_SIG,  /* bad signature / tampered */
	OC_FH_EV_REJECT_SEQ,  /* rollback: seq <= current */
	OC_FH_EV_REJECT_HASH, /* fragment hash mismatch */
	OC_FH_EV_GOT_FRAG,    /* accepted a fragment into pending */
	OC_FH_EV_SERVED,      /* transmitted manifest/fragments */
	OC_FH_EV_BEACON_TX,
	OC_FH_EV_NEED_TX
} oc_fh_event_t;

typedef struct oc_fh_freshness {
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint32_t fence_seq; /* 0 = none */
	uint8_t poly_hash[OC_FH_POLY_HASH_LEN];
	uint32_t received_at_ms;
	uint16_t source_id;
} oc_fh_freshness_t;

typedef struct oc_fh_stats {
	uint32_t tx_frames;
	uint32_t rx_frames;
	uint32_t retransmit_frags;
	uint32_t airtime_us;
	uint32_t applied;
	uint32_t reject_sig;
	uint32_t reject_seq;
	uint32_t reject_hash;
} oc_fh_stats_t;

typedef struct oc_fh_config {
	uint16_t node_id;
	uint8_t is_rook;        /* 1 = Rook; always may serve */
	uint8_t starling_serve; /* PLACEHOLDER; 0=default OFF, 1=multi-hop */
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint16_t frag_data_max;  /* default OC_FH_DEFAULT_FRAG_DATA */
	uint32_t trickle_imin_ms;
	uint32_t trickle_imax_ms;
	uint8_t trickle_k;
} oc_fh_config_t;

/*
 * Caller-provided storage for the active fence payload and for a pending
 * assembly (no heap).
 */
typedef struct oc_fh_buffers {
	uint8_t *active_payload;
	size_t active_cap;
	uint8_t *pending_payload;
	size_t pending_cap;
	uint8_t *rx_scratch; /* >= radio MTU */
	size_t rx_scratch_cap;
	uint8_t *tx_scratch;
	size_t tx_scratch_cap;
} oc_fh_buffers_t;

typedef struct oc_fh_node oc_fh_node_t;

struct oc_fh_node {
	oc_fh_config_t cfg;
	oc_fh_buffers_t buf;
	oc_radio_t *radio;
	oc_fh_verify_fn verify;
	void *verify_ctx;
	uint32_t (*now_ms)(void *clock_ctx);
	void *clock_ctx;

	oc_fh_freshness_t active; /* last-good */
	size_t active_len;
	oc_fh_manifest_t active_manifest;
	uint8_t active_manifest_wire[8u + 64u + 4u + 32u + 2u +
	                             OC_FH_MAX_FRAGMENTS * OC_FH_FRAG_HASH_LEN];
	size_t active_manifest_wire_len;

	/* Pending transfer (newer seq being assembled). */
	uint8_t have_pending;
	oc_fh_manifest_t pending_manifest;
	uint8_t pending_manifest_wire[8u + 64u + 4u + 32u + 2u +
	                              OC_FH_MAX_FRAGMENTS * OC_FH_FRAG_HASH_LEN];
	size_t pending_manifest_wire_len;
	uint8_t have_frag[OC_FH_MAX_FRAGMENTS];
	uint16_t pending_got;
	size_t pending_len;
	uint16_t pending_source;

	/* Trickle */
	uint32_t trickle_I;
	uint32_t trickle_t;
	uint32_t trickle_c;
	uint32_t trickle_interval_start;
	uint32_t last_beacon_ms;

	/* Scheduled serve of our active fence to a stale peer. */
	uint8_t serve_pending;
	uint32_t serve_at_ms;
	uint32_t serve_target_seq_seen; /* neighbor's older seq that triggered */

	/* Scheduled NEED (initial + retries while incomplete). */
	uint8_t need_pending;
	uint32_t need_at_ms;
	uint32_t need_retries;

	oc_fh_stats_t stats;
	oc_fh_event_t last_event;
};

void oc_fh_node_init(oc_fh_node_t *n, const oc_fh_config_t *cfg, const oc_fh_buffers_t *buf,
                     oc_radio_t *radio, oc_fh_verify_fn verify, void *verify_ctx,
                     uint32_t (*now_ms)(void *), void *clock_ctx);

/*
 * Rook/server path: install a sealed manifest + payload locally (already
 * signed by the farm key). Verifies, rejects seq<=current, activates.
 * Returns 0 on apply, negative on reject.
 */
int oc_fh_inject_local(oc_fh_node_t *n, const uint8_t *sealed_manifest, size_t mlen,
                       const uint8_t *payload, size_t plen);

/* Drive the node: poll radio, run Trickle/serve/need timers. */
void oc_fh_node_poll(oc_fh_node_t *n);

/* True if this node is allowed to serve its active fence. */
int oc_fh_may_serve(const oc_fh_node_t *n);

const oc_fh_freshness_t *oc_fh_active(const oc_fh_node_t *n);
const oc_fh_stats_t *oc_fh_stats(const oc_fh_node_t *n);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_FENCE_NODE_H */
