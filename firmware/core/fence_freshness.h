/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Fence freshness types shared by Starling (and later Rook / sim).
 *
 * Wire encoding of beacons and fence payloads is owned by op-fw-proto
 * (firmware/lora, firmware/sim). This header is the collar-side record
 * Starling persists in NVS and compares when deciding adopt / serve.
 *
 * Protocol open questions (see Starling PR): whether beacons carry
 * fence_seq + fence hash (v2 LoRa beacon map already has bver for herd
 * boundary version — may need hash / issued_at / source for multi-hop).
 */
#ifndef OPENCOLLAR_CORE_FENCE_FRESHNESS_H
#define OPENCOLLAR_CORE_FENCE_FRESHNESS_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FENCE_HASH_LEN 32
#define FENCE_SOURCE_ID_LEN 16

/* One entry in the freshness log (signed server-issued metadata). */
struct fence_freshness {
	uint32_t fence_seq;                 /* Server-issued sequence; higher = newer */
	uint8_t fence_hash[FENCE_HASH_LEN]; /* SHA-256 (or protocol digest) of fence bytes */
	int64_t issued_at;                  /* GNSS Unix seconds when server issued */
	int64_t received_at;                /* GNSS Unix seconds when this collar got it */
	uint8_t source_id[FENCE_SOURCE_ID_LEN]; /* Who we received it from (device/short) */
	uint8_t source_id_len;
	bool verified; /* Signature over the fence payload checked OK */
};

/* Compare two freshness records: 1 if a newer than b, -1 if older, 0 if equal seq. */
static inline int fence_freshness_cmp(const struct fence_freshness *a,
				      const struct fence_freshness *b)
{
	if (a->fence_seq > b->fence_seq) {
		return 1;
	}
	if (a->fence_seq < b->fence_seq) {
		return -1;
	}
	return 0;
}

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_CORE_FENCE_FRESHNESS_H */
