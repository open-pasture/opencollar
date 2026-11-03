/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * NVS layout for Starling fences:
 *   - active fence (verified payload + freshness)
 *   - staged fence (optional, future effective_at)
 *   - freshness log (signed server-issued metadata)
 *
 * Never adopt unsigned or older/equal fence_seq. Keep enforcing the last
 * valid active fence with no radio contact.
 */
#ifndef STARLING_FENCE_STORE_H
#define STARLING_FENCE_STORE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "fence_freshness.h"
#include "geofence.h"
#include "store.h"

#ifdef __cplusplus
extern "C" {
#endif

#define STORE_ID_STARLING_ACTIVE 0x40
#define STORE_ID_STARLING_STAGED 0x41
#define STORE_ID_STARLING_FRESHNESS 0x42

#define STARLING_FENCE_PAYLOAD_MAX 4096
#define STARLING_FENCE_SIG_LEN 64
#define STARLING_FENCE_MAX_VERTICES 64

struct starling_fence_blob {
	struct fence_freshness freshness;
	uint8_t sig[STARLING_FENCE_SIG_LEN];
	bool has_sig;
	uint16_t n_vertices;
	struct geo_point vertices[STARLING_FENCE_MAX_VERTICES];
	double warn_m;
	double hysteresis_m;
	/* Raw signed payload bytes (for re-serve / hash); optional. */
	uint16_t payload_len;
	uint8_t payload[STARLING_FENCE_PAYLOAD_MAX];
};

struct fence_store {
	struct starling_fence_blob active;
	struct starling_fence_blob staged;
	bool has_active;
	bool has_staged;
	struct fence_freshness log; /* Persisted freshness of active */
	bool has_log;
	const uint8_t *pubkey; /* 32-byte Ed25519; NULL = accept only pre-verified */
};

void fence_store_init(struct fence_store *fs, const uint8_t pubkey[32]);

/* Load active/staged/freshness from NVS. Returns 0 or negative errno. */
int fence_store_boot(struct fence_store *fs);

/*
 * Offer a candidate fence. Must be signature-verified (or verify here if
 * pubkey set and payload/sig present). Rejects unsigned, unverified, or
 * fence_seq <= active. On accept: becomes active (or staged if future),
 * updates freshness log, persists.
 *
 * Returns: 1 adopted, 0 rejected (stale/equal/unsigned), -1 error.
 */
int fence_store_offer(struct fence_store *fs, const struct starling_fence_blob *cand,
		      int64_t now_utc, bool verified);

/* Apply active vertices into a geofence. Returns false if none. */
bool fence_store_apply_geofence(const struct fence_store *fs, struct geofence *gf,
				const struct geofence_config *cfg);

const struct fence_freshness *fence_store_freshness(const struct fence_store *fs);

#ifdef __cplusplus
}
#endif

#endif
