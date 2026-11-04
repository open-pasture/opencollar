/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "fence_store.h"

#include <string.h>

void fence_store_init(struct fence_store *fs)
{
	memset(fs, 0, sizeof(*fs));
}

static int persist_hwm(const struct fence_store *fs)
{
	return store_write(STORE_ID_STARLING_HWM, &fs->fence_seq_hwm, sizeof(fs->fence_seq_hwm));
}

static int persist_active(const struct fence_store *fs)
{
	if (!fs->has_active) {
		return store_delete(STORE_ID_STARLING_ACTIVE);
	}
	return store_write(STORE_ID_STARLING_ACTIVE, &fs->active, sizeof(fs->active));
}

int fence_store_boot(struct fence_store *fs)
{
	uint32_t hwm = 0;
	int n;

	n = store_read(STORE_ID_STARLING_HWM, &hwm, sizeof(hwm));
	if (n == (int)sizeof(hwm)) {
		fs->fence_seq_hwm = hwm;
	} else {
		fs->fence_seq_hwm = 0;
	}

	n = store_read(STORE_ID_STARLING_ACTIVE, &fs->active, sizeof(fs->active));
	if (n == (int)sizeof(fs->active) && fs->active.verified &&
	    fs->active.freshness.fence_seq > 0) {
		fs->has_active = true;
		if (fs->active.freshness.fence_seq > fs->fence_seq_hwm) {
			fs->fence_seq_hwm = fs->active.freshness.fence_seq;
			(void)persist_hwm(fs);
		}
		/* Drop active if somehow below hwm (corrupt / partial write). */
		if (fs->active.freshness.fence_seq < fs->fence_seq_hwm) {
			memset(&fs->active, 0, sizeof(fs->active));
			fs->has_active = false;
			(void)persist_active(fs);
		}
	} else {
		fs->has_active = false;
		memset(&fs->active, 0, sizeof(fs->active));
	}
	return 0;
}

int fence_store_offer(struct fence_store *fs, const struct starling_fence_blob *cand,
		      uint32_t received_at_ms)
{
	struct starling_fence_blob copy;

	if (cand == NULL || !cand->verified || cand->freshness.fence_seq == 0) {
		return 0;
	}
	if (cand->n_vertices < 3 && cand->payload_len == 0) {
		return 0;
	}
	/* High-water: reject older or equal across reboots. */
	if (cand->freshness.fence_seq <= fs->fence_seq_hwm) {
		return 0;
	}

	copy = *cand;
	copy.freshness.received_at_ms = received_at_ms;
	copy.verified = true;

	fs->active = copy;
	fs->has_active = true;
	fs->fence_seq_hwm = copy.freshness.fence_seq;

	if (persist_hwm(fs) != 0) {
		return -1;
	}
	if (persist_active(fs) != 0) {
		return -1;
	}
	return 1;
}

bool fence_store_apply_geofence(const struct fence_store *fs, struct geofence *gf,
				const struct geofence_config *cfg)
{
	struct geofence_config c;

	if (!fs->has_active || fs->active.n_vertices < 3) {
		return false;
	}
	c = *cfg;
	if (fs->active.warn_m > 0) {
		c.warn_m = fs->active.warn_m;
	}
	if (fs->active.hysteresis_m > 0) {
		c.hysteresis_m = fs->active.hysteresis_m;
	}
	return geofence_init(gf, &c, fs->active.vertices, fs->active.n_vertices,
			     fs->active.freshness.fence_seq) == 0;
}

const oc_fh_freshness_t *fence_store_freshness(const struct fence_store *fs)
{
	return fs->has_active ? &fs->active.freshness : NULL;
}

uint32_t fence_store_hwm(const struct fence_store *fs)
{
	return fs->fence_seq_hwm;
}
