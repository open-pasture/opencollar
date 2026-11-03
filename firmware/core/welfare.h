/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Welfare cap hooks shared by Rook and Starling cue loops.
 *
 * Numeric defaults are PLACEHOLDERs pending Cody's animal-welfare decision
 * on PR #2 (cursor/welfare-safeguards-cd56). Do not treat these as final.
 */
#ifndef OPENCOLLAR_CORE_WELFARE_H
#define OPENCOLLAR_CORE_WELFARE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * TODO(cody): welfare cap decision (PR #2)
 * Outside/pulse cues allowed per boundary crossing, then suspend until
 * clear inside (GEOFENCE_INSIDE).
 */
#define WELFARE_PLACEHOLDER_MAX_OUTSIDE_CUES 2u

/*
 * TODO(cody): welfare cap decision (PR #2)
 * Escape→return cycles before auto shut-off of cues.
 */
#define WELFARE_PLACEHOLDER_ESCAPE_CYCLE_LIMIT 3u

/*
 * TODO(cody): welfare cap decision (PR #2)
 * Rolling window for escape cycles (milliseconds). 1 hour.
 */
#define WELFARE_PLACEHOLDER_ESCAPE_CYCLE_WINDOW_MS (60u * 60u * 1000u)

/* Existing cue timing caps still apply (warn rest / outside tone window). */
#define WELFARE_PLACEHOLDER_OUTSIDE_MAX_MS 10000u
#define WELFARE_PLACEHOLDER_MAX_ACTIVE_MS 20000u
#define WELFARE_PLACEHOLDER_REST_MS 30000u

struct welfare_caps {
	uint16_t max_outside_cues;
	uint16_t escape_cycle_limit;
	uint32_t escape_cycle_window_ms;
	uint32_t outside_max_ms;
	uint32_t max_active_ms;
	uint32_t rest_ms;
};

/* Fill with PLACEHOLDER defaults. Zero fields are replaced by placeholders. */
static inline void welfare_caps_defaults(struct welfare_caps *c)
{
	c->max_outside_cues = WELFARE_PLACEHOLDER_MAX_OUTSIDE_CUES;
	c->escape_cycle_limit = WELFARE_PLACEHOLDER_ESCAPE_CYCLE_LIMIT;
	c->escape_cycle_window_ms = WELFARE_PLACEHOLDER_ESCAPE_CYCLE_WINDOW_MS;
	c->outside_max_ms = WELFARE_PLACEHOLDER_OUTSIDE_MAX_MS;
	c->max_active_ms = WELFARE_PLACEHOLDER_MAX_ACTIVE_MS;
	c->rest_ms = WELFARE_PLACEHOLDER_REST_MS;
}

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_CORE_WELFARE_H */
