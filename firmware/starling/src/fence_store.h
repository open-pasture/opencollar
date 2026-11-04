/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Starling geofence mirror: active vertices + fence_seq high-water.
 *
 * Gossip engine persistence is PR #6's oc_fh_store_t (see oc_fh_store_nvs).
 * This store mirrors applied fences for geofence_init / demo. Never adopt
 * unsigned or seq <= hwm. Reboot must not roll back to an older fence.
 */
#ifndef STARLING_FENCE_STORE_H
#define STARLING_FENCE_STORE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "geofence.h"
#include "opencollar/fence_node.h"
#include "store.h"

#ifdef __cplusplus
extern "C" {
#endif

#define STORE_ID_STARLING_ACTIVE 0x40
#define STORE_ID_STARLING_HWM 0x43

#define STARLING_FENCE_PAYLOAD_MAX 4096
#define STARLING_FENCE_MAX_VERTICES 64
#define STARLING_SEALED_MANIFEST_MAX 512

struct starling_fence_blob {
	oc_fh_freshness_t freshness;
	bool verified; /* signature checked (by #6 node or test inject) */
	uint16_t n_vertices;
	struct geo_point vertices[STARLING_FENCE_MAX_VERTICES];
	double warn_m;
	double hysteresis_m;
	uint16_t payload_len;
	uint8_t payload[STARLING_FENCE_PAYLOAD_MAX];
	uint16_t sealed_len;
	uint8_t sealed[STARLING_SEALED_MANIFEST_MAX];
};

struct fence_store {
	struct starling_fence_blob active;
	bool has_active;
	uint32_t fence_seq_hwm; /* persisted; never decreases */
};

void fence_store_init(struct fence_store *fs);

/* Load active + hwm from NVS. hwm = max(stored_hwm, active.seq). */
int fence_store_boot(struct fence_store *fs);

/*
 * Offer a verified candidate. Rejects !verified or fence_seq <= hwm.
 * On accept: updates active, raises hwm, persists both.
 * Returns 1 adopted, 0 rejected, -1 I/O error.
 */
int fence_store_offer(struct fence_store *fs, const struct starling_fence_blob *cand,
		      uint32_t received_at_ms);

bool fence_store_apply_geofence(const struct fence_store *fs, struct geofence *gf,
				const struct geofence_config *cfg);

const oc_fh_freshness_t *fence_store_freshness(const struct fence_store *fs);

uint32_t fence_store_hwm(const struct fence_store *fs);

#ifdef __cplusplus
}
#endif

#endif
