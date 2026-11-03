/*
 * fence_ids.h — placeholder v2 identifiers for fence gossip.
 *
 * Names and numeric ids are NOT frozen. Keep every wire constant here so a
 * later rename is a one-header change. Do not scatter magic numbers.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_FENCE_IDS_H
#define OPENCOLLAR_FENCE_IDS_H

#include <stdint.h>

/* Protocol / domain separation (Ed25519 preimage prefix). */
#define OC_FH_MANIFEST_DOMAIN "oc/fh/manifest/1"
#define OC_FH_MANIFEST_DOMAIN_LEN 17

/* Wire message types (placeholders; high nibble marks gossip plane). */
#define OC_FH_MSG_BEACON 0xA0u   /* freshness advert: seq + short hash */
#define OC_FH_MSG_MANIFEST 0xA1u /* signed manifest */
#define OC_FH_MSG_FRAGMENT 0xA2u /* fence payload fragment */
#define OC_FH_MSG_NEED 0xA3u     /* selective missing-piece bitmap */
#define OC_FH_MSG_HAVE 0xA4u     /* peer holds whole fence (optional) */

/* Manifest body version byte. */
#define OC_FH_MANIFEST_VER 1u

/* Sizes. */
#define OC_FH_FARM_ID_LEN 8u
#define OC_FH_POLY_HASH_LEN 32u /* Blake2b-256 of full fence payload */
#define OC_FH_FRAG_HASH_LEN 16u /* Blake2b-128 of each fragment */
#define OC_FH_SHORT_HASH_LEN 8u /* first 8 of poly hash, for beacons */
#define OC_FH_SIG_LEN 64u
#define OC_FH_PUBKEY_LEN 32u

/* Bounds aligned with protocol/v2/lora.md §7.1. */
#define OC_FH_MAX_FRAGMENTS 64u
#define OC_FH_MAX_PAYLOAD 12288u
#define OC_FH_DEFAULT_FRAG_DATA 209u /* lora.md typical fragment data */

/* Reserved hop counter (telemetry later; unused in fence transfer). */
#define OC_FH_HOP_RESERVED 0u

/* Trickle defaults (ms), RFC 6206-inspired; tunable via node config. */
#define OC_FH_TRICKLE_IMIN_MS 1000u
#define OC_FH_TRICKLE_IMAX_MS 60000u
#define OC_FH_TRICKLE_K 1u /* redundancy constant */

/* Serve / request backoffs. */
#define OC_FH_SERVE_BACKOFF_LO_MS 20u
#define OC_FH_SERVE_BACKOFF_HI_MS 200u
#define OC_FH_NEED_BACKOFF_LO_MS 10u
#define OC_FH_NEED_BACKOFF_HI_MS 80u
/* While a transfer is incomplete, re-NEED on this period (plus jitter). */
#define OC_FH_NEED_RETRY_MS 120u

/* Beacon rate limit: min gap between beacons from this node. */
#define OC_FH_BEACON_MIN_GAP_MS 200u

/*
 * Default for PLACEHOLDER config key starling_serve: OFF until Starling
 * listen energy is measured (ARCHITECTURE.md). Rooks always serve; pilot
 * telemetry stays one hop to the Rook. Multi-hop tests set it to 1 explicitly.
 */
#define OC_FH_STARLING_SERVE_DEFAULT 0u

#endif /* OPENCOLLAR_FENCE_IDS_H */
