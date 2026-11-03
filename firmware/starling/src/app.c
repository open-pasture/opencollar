/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "app.h"

#include <string.h>

void starling_app_init(struct starling_app *a, bool starling_serve)
{
	static const uint8_t k_farm[OC_FH_FARM_ID_LEN] = { 'F', 'A', 'R', 'M', '0', '0', '0',
							   '1' };

	memset(a, 0, sizeof(*a));

	a->geo_cfg.warn_m = 5.0;
	a->geo_cfg.hysteresis_m = 1.0;
	a->geo_cfg.max_accuracy_m = 10.0;

	welfare_hooks_init_none(&a->welfare);

	a->cue_cfg.warn_freq_hz = 2700;
	a->cue_cfg.outside_freq_hz = 3200;
	a->cue_cfg.beep_ms = 200;
	a->cue_cfg.max_active_ms = 20000;
	a->cue_cfg.rest_ms = 30000;
	a->cue_cfg.outside_max_ms = 10000;
	cue_init(&a->cue, &a->cue_cfg);

	fence_store_init(&a->store);
	a->starling_serve = starling_serve;
	starling_gossip_init(&a->gossip, &a->store, 2, k_farm, starling_serve, NULL, NULL, NULL,
			     NULL, NULL);
	power_sched_init(&a->power);
}

#ifdef STARLING_HAS_LORA
void starling_app_bind_gossip(struct starling_app *a, uint16_t node_id,
			      const uint8_t farm_id[OC_FH_FARM_ID_LEN], oc_radio_t *radio,
			      oc_fh_verify_fn verify, void *verify_ctx, uint32_t (*now_ms)(void *),
			      void *clock_ctx)
{
	starling_gossip_init(&a->gossip, &a->store, node_id, farm_id, a->starling_serve, radio,
			     verify, verify_ctx, now_ms, clock_ctx);
}
#endif

void starling_app_bind_gnss(struct starling_app *a, enum gnss_backend backend,
			    const struct gnss_ops *ops, void *ctx)
{
	gnss_bind(&a->gnss, backend, ops, ctx);
}

int starling_app_boot(struct starling_app *a, int64_t now_ms)
{
	(void)now_ms;
	if (fence_store_boot(&a->store) != 0) {
		return -1;
	}
	a->fenced = fence_store_apply_geofence(&a->store, &a->fence, &a->geo_cfg);
	if (a->fenced) {
		cue_rearm(&a->cue);
	}
	if (a->gnss.ops) {
		return gnss_init(&a->gnss);
	}
	return 0;
}

int starling_app_set_fence(struct starling_app *a, const struct starling_fence_blob *blob,
			   uint32_t received_at_ms)
{
	int rc = fence_store_offer(&a->store, blob, received_at_ms);

	if (rc == 1) {
		a->fenced = fence_store_apply_geofence(&a->store, &a->fence, &a->geo_cfg);
		cue_rearm(&a->cue);
	}
	return rc;
}

struct starling_tick_out starling_app_tick(struct starling_app *a, int64_t now_ms)
{
	struct starling_tick_out out = {0};
	struct gnss_fix fix = {0};

	out.power = power_sched_tick(&a->power, now_ms);

	if (power_want_gnss(&a->power) || a->gnss.backend == GNSS_BACKEND_FAKE) {
		gnss_poll(&a->gnss, now_ms, &fix);
	}

	starling_gossip_poll(&a->gossip);

	if (a->store.has_active) {
		uint32_t seq = a->store.active.freshness.fence_seq;

		if (!a->fenced || a->fence.version != seq) {
			a->fenced = fence_store_apply_geofence(&a->store, &a->fence, &a->geo_cfg);
			if (a->fenced) {
				cue_rearm_at(&a->cue, now_ms);
			}
		}
	}

	out.fenced = a->fenced;
	if (a->fenced && fix.valid) {
		out.geo = geofence_update(&a->fence, (struct geo_point){fix.lat, fix.lon},
					  fix.accuracy_m);
		out.cue = cue_update(&a->cue, &out.geo, a->fence.cfg.warn_m, now_ms);
		out.cue = welfare_apply(&a->welfare, out.cue, &out.geo, now_ms);
	} else if (a->fenced) {
		out.geo.state = GEOFENCE_UNKNOWN;
	}

	a->last_cmd = out.cue;
	a->last_geo = out.geo;
	if (a->store.has_active) {
		out.fence_seq = a->store.active.freshness.fence_seq;
	}
	return out;
}
