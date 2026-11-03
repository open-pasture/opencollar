/*
 * TEMPORARY shim — DELETE when PR #6 (firmware/lora) merges.
 * Layout of oc_fh_freshness_t MUST match PR #6 fence_node.h.
 * No gossip engine here (no oc_fh_node_poll).
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_FENCE_NODE_H
#define OPENCOLLAR_FENCE_NODE_H

#include "opencollar/fence_ids.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct oc_fh_freshness {
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint32_t fence_seq; /* 0 = none */
	uint8_t poly_hash[OC_FH_POLY_HASH_LEN];
	uint32_t received_at_ms;
	uint16_t source_id;
} oc_fh_freshness_t;

/* Gossip API is not provided by this shim — link firmware/lora for that. */

#ifdef __cplusplus
}
#endif

#endif
