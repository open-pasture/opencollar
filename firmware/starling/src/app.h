/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Starling collar app: fake/real GNSS → geofence → cue (+ welfare placeholders)
 * → fence store / gossip. Plain C, host-testable.
 */
#ifndef STARLING_APP_H
#define STARLING_APP_H

#include <stdbool.h>
#include <stdint.h>

#include "cue.h"
#include "fence_store.h"
#include "geofence.h"
#include "gnss.h"
#include "gossip.h"
#include "power.h"
#include "welfare.h"

#ifdef __cplusplus
extern "C" {
#endif

#define STARLING_FW_VERSION "0.1.0-starling"

struct starling_app {
	struct gnss gnss;
	struct fence_store store;
	struct geofence fence;
	struct geofence_config geo_cfg;
	struct cue cue;
	struct cue_config cue_cfg;
	struct welfare_caps welfare;
	struct starling_gossip gossip;
	struct power_sched power;
	bool fenced;
	/* Welfare PLACEHOLDER tracking (full policy lands with PR #2 merge). */
	uint16_t outside_cues_this_crossing;
	uint16_t escape_cycles;
	int64_t escape_window_start_ms;
	bool cues_suspended;
	bool enforcement_off;
	struct cue_command last_cmd;
	struct geofence_result last_geo;
};

struct starling_tick_out {
	bool fenced;
	struct geofence_result geo;
	struct cue_command cue;
	enum power_phase power;
	uint32_t fence_seq;
};

void starling_app_init(struct starling_app *a, bool starling_serve);
void starling_app_bind_gnss(struct starling_app *a, enum gnss_backend backend,
			    const struct gnss_ops *ops, void *ctx);

/* Boot: load NVS fences, apply active geofence, init GNSS. */
int starling_app_boot(struct starling_app *a, int64_t now_ms);

/* Install a verified demo/active fence (host / bench). */
int starling_app_set_fence(struct starling_app *a, const struct starling_fence_blob *blob,
			   int64_t now_utc);

struct starling_tick_out starling_app_tick(struct starling_app *a, int64_t now_ms);

#ifdef __cplusplus
}
#endif

#endif
