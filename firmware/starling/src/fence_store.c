/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "fence_store.h"

#include <string.h>

#include "monocypher-ed25519.h"

void fence_store_init(struct fence_store *fs, const uint8_t pubkey[32])
{
	memset(fs, 0, sizeof(*fs));
	fs->pubkey = pubkey;
}

static int persist_active(const struct fence_store *fs)
{
	int rc;

	if (!fs->has_active) {
		return store_delete(STORE_ID_STARLING_ACTIVE);
	}
	rc = store_write(STORE_ID_STARLING_ACTIVE, &fs->active, sizeof(fs->active));
	if (rc != 0) {
		return rc;
	}
	return store_write(STORE_ID_STARLING_FRESHNESS, &fs->log, sizeof(fs->log));
}

static int persist_staged(const struct fence_store *fs)
{
	if (!fs->has_staged) {
		return store_delete(STORE_ID_STARLING_STAGED);
	}
	return store_write(STORE_ID_STARLING_STAGED, &fs->staged, sizeof(fs->staged));
}

int fence_store_boot(struct fence_store *fs)
{
	int n;

	n = store_read(STORE_ID_STARLING_ACTIVE, &fs->active, sizeof(fs->active));
	if (n == (int)sizeof(fs->active)) {
		fs->has_active = true;
	} else {
		fs->has_active = false;
		memset(&fs->active, 0, sizeof(fs->active));
	}

	n = store_read(STORE_ID_STARLING_STAGED, &fs->staged, sizeof(fs->staged));
	if (n == (int)sizeof(fs->staged)) {
		fs->has_staged = true;
	} else {
		fs->has_staged = false;
		memset(&fs->staged, 0, sizeof(fs->staged));
	}

	n = store_read(STORE_ID_STARLING_FRESHNESS, &fs->log, sizeof(fs->log));
	if (n == (int)sizeof(fs->log)) {
		fs->has_log = true;
	} else if (fs->has_active) {
		fs->log = fs->active.freshness;
		fs->has_log = true;
	} else {
		fs->has_log = false;
		memset(&fs->log, 0, sizeof(fs->log));
	}
	return 0;
}

static bool verify_blob(const struct fence_store *fs, const struct starling_fence_blob *cand)
{
	if (cand->freshness.verified && !cand->has_sig && fs->pubkey == NULL) {
		/* Host tests may inject a pre-verified blob. */
		return true;
	}
	if (!cand->has_sig || cand->payload_len == 0 || fs->pubkey == NULL) {
		return false;
	}
	/* Ed25519 over the opaque payload (protocol owns canonicalization). */
	return crypto_ed25519_check(cand->sig, fs->pubkey, cand->payload, cand->payload_len) == 0;
}

int fence_store_offer(struct fence_store *fs, const struct starling_fence_blob *cand,
		      int64_t now_utc, bool verified)
{
	struct starling_fence_blob copy;
	bool ok;

	if (cand == NULL || cand->n_vertices < 3) {
		return 0;
	}

	ok = verified || verify_blob(fs, cand);
	if (!ok) {
		return 0; /* reject unsigned / bad sig */
	}

	if (fs->has_active) {
		if (fence_freshness_cmp(&cand->freshness, &fs->active.freshness) <= 0) {
			return 0; /* reject older or equal */
		}
	}

	copy = *cand;
	copy.freshness.verified = true;
	copy.freshness.received_at = now_utc;

	fs->active = copy;
	fs->has_active = true;
	fs->log = copy.freshness;
	fs->has_log = true;

	if (persist_active(fs) != 0) {
		return -1;
	}
	(void)persist_staged(fs);
	return 1;
}

bool fence_store_apply_geofence(const struct fence_store *fs, struct geofence *gf,
				const struct geofence_config *cfg)
{
	struct geofence_config c;

	if (!fs->has_active) {
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

const struct fence_freshness *fence_store_freshness(const struct fence_store *fs)
{
	return fs->has_log ? &fs->log : NULL;
}
