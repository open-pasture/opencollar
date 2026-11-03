/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#include "app.h"

#include <string.h>

void starling_app_init(struct starling_app *a, bool starling_serve)
{
	memset(a, 0, sizeof(*a));

	a->geo_cfg.warn_m = 5.0;
	a->geo_cfg.hysteresis_m = 1.0;
	a->geo_cfg.max_accuracy_m = 10.0;

	welfare_caps_defaults(&a->welfare);

	a->cue_cfg.warn_freq_hz = 2700;
	a->cue_cfg.outside_freq_hz = 3200;
	a->cue_cfg.beep_ms = 200;
	a->cue_cfg.max_active_ms = a->welfare.max_active_ms;
	a->cue_cfg.rest_ms = a->welfare.rest_ms;
	a->cue_cfg.outside_max_ms = a->welfare.outside_max_ms;
	cue_init(&a->cue, &a->cue_cfg);

	fence_store_init(&a->store, NULL);
	starling_gossip_init(&a->gossip, &a->store, starling_serve);
	power_sched_init(&a->power);
}

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
			   int64_t now_utc)
{
	int rc = fence_store_offer(&a->store, blob, now_utc, true);

	if (rc == 1) {
		a->fenced = fence_store_apply_geofence(&a->store, &a->fence, &a->geo_cfg);
		cue_rearm(&a->cue);
		a->outside_cues_this_crossing = 0;
		a->cues_suspended = false;
		a->enforcement_off = false;
	}
	return rc;
}

/*
 * TODO(cody): welfare cap decision (PR #2) — thin local gate until PR #2's
 * cue.c welfare logic is merged into the shared portable core.
 */
static struct cue_command apply_welfare(struct starling_app *a, struct cue_command cmd,
					const struct geofence_result *r, int64_t now_ms)
{
	if (a->enforcement_off) {
		return (struct cue_command){0};
	}

	if (r->state == GEOFENCE_INSIDE) {
		if (a->cues_suspended) {
			a->cues_suspended = false;
			a->outside_cues_this_crossing = 0;
		}
	}

	if (cmd.active && cmd.kind == CUE_OUTSIDE) {
		if (a->cues_suspended) {
			return (struct cue_command){0};
		}
		a->outside_cues_this_crossing++;
		if (a->outside_cues_this_crossing > a->welfare.max_outside_cues) {
			/* PLACEHOLDER: suspend until clear inside */
			a->cues_suspended = true;
			a->outside_cues_this_crossing = 0;
			if (a->escape_window_start_ms == 0 ||
			    now_ms - a->escape_window_start_ms >
				    (int64_t)a->welfare.escape_cycle_window_ms) {
				a->escape_window_start_ms = now_ms;
				a->escape_cycles = 0;
			}
			a->escape_cycles++;
			if (a->escape_cycles >= a->welfare.escape_cycle_limit) {
				/* PLACEHOLDER: auto shut-off */
				a->enforcement_off = true;
			}
			return (struct cue_command){0};
		}
	}
	return cmd;
}

struct starling_tick_out starling_app_tick(struct starling_app *a, int64_t now_ms)
{
	struct starling_tick_out out = {0};
	struct gnss_fix fix = {0};
	int64_t utc = 0;

	out.power = power_sched_tick(&a->power, now_ms);

	if (power_want_gnss(&a->power) || a->gnss.backend == GNSS_BACKEND_FAKE) {
		gnss_poll(&a->gnss, now_ms, &fix);
	}

	if (fix.has_time) {
		utc = fix.utc;
	}

	starling_gossip_tick(&a->gossip, now_ms, utc);

	if (a->store.has_active) {
		uint32_t seq = a->store.active.freshness.fence_seq;

		if (!a->fenced || a->fence.version != seq) {
			a->fenced = fence_store_apply_geofence(&a->store, &a->fence, &a->geo_cfg);
			if (a->fenced) {
				cue_rearm_at(&a->cue, now_ms);
				a->outside_cues_this_crossing = 0;
				a->cues_suspended = false;
				a->enforcement_off = false;
			}
		}
	}

	out.fenced = a->fenced;
	if (a->fenced && fix.valid) {
		out.geo = geofence_update(&a->fence, (struct geo_point){fix.lat, fix.lon},
					  fix.accuracy_m);
		out.cue = cue_update(&a->cue, &out.geo, a->fence.cfg.warn_m, now_ms);
		out.cue = apply_welfare(a, out.cue, &out.geo, now_ms);
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
