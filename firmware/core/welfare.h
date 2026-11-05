/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Welfare cue hooks shared by Rook and Starling.
 *
 * Numeric caps (PR #2, approved on main): live in firmware/src/cue.h as
 * WELFARE_DEFAULT_MAX_OUTSIDE_CUES (3), WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT (3),
 * WELFARE_DEFAULT_ESCAPE_WINDOW_MS (24 h). cue_init applies them when fields
 * are zero; welfare_config_apply_approved_caps sets them explicitly. Enforcement
 * of the outside-cue budget and escape-cycle shut-off is inside cue_update
 * (firmware/src/cue.c) — audio/cue gate only; this header never enables pulse.
 *
 * Shut-off (PR #22): once auto shut-off trips, enforcement stays off until an
 * explicit caretaker cue_clear_shutoff (not a fence move / cue_rearm). The
 * welfare gate must honor cue.enforcement_off as a hard suppress — cue_update
 * already returns silent when shut off; this hook is the shared policy
 * surface so Starling/Rook cannot "forget" that rule.
 *
 * Starling pilot: caretaker re-arm is serial-only (starling_app_caretaker_rearm).
 * Do not wire LoRa / signed remote re-arm here (draft PR #25 stays optional).
 */
#ifndef OPENCOLLAR_CORE_WELFARE_H
#define OPENCOLLAR_CORE_WELFARE_H

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "cue.h"
#include "geofence.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Optional policy hook. Return the (possibly suppressed) cue command.
 * ctx is caller-owned. A NULL fn means pass-through (caps still apply inside
 * cue_update when the cue was inited with WELFARE_DEFAULT_*).
 */
typedef struct cue_command (*welfare_gate_fn)(void *ctx, struct cue_command cmd,
					     const struct geofence_result *r,
					     int64_t now_ms);

struct welfare_hooks {
	welfare_gate_fn gate; /* NULL = pass-through */
	void *ctx;
};

/* Apply PR #2 approved caps from cue.h (single source of truth). */
static inline void welfare_config_apply_approved_caps(struct cue_config *cfg)
{
	cfg->max_outside_cues = WELFARE_DEFAULT_MAX_OUTSIDE_CUES;
	cfg->escape_cycle_limit = WELFARE_DEFAULT_ESCAPE_CYCLE_LIMIT;
	cfg->escape_cycle_window_ms = WELFARE_DEFAULT_ESCAPE_WINDOW_MS;
}

/* Default: pass cue through unchanged (caps already enforced in cue_update). */
static inline struct cue_command welfare_gate_none(void *ctx, struct cue_command cmd,
						  const struct geofence_result *r,
						  int64_t now_ms)
{
	(void)ctx;
	(void)r;
	(void)now_ms;
	return cmd;
}

/*
 * Honor shut-off-until-caretaker-re-arm (PR #22).
 * ctx must be a struct cue *. Suppresses any active cue while enforcement_off.
 * Does not clear shut-off; only cue_clear_shutoff (serial caretaker on Starling).
 */
static inline struct cue_command welfare_gate_honor_shutoff(void *ctx, struct cue_command cmd,
							    const struct geofence_result *r,
							    int64_t now_ms)
{
	const struct cue *c = ctx;

	(void)r;
	(void)now_ms;
	if (c && c->enforcement_off && cmd.active) {
		memset(&cmd, 0, sizeof(cmd));
		cmd.kind = CUE_NONE;
	}
	return cmd;
}

static inline void welfare_hooks_init_none(struct welfare_hooks *h)
{
	h->gate = welfare_gate_none;
	h->ctx = NULL;
}

/* Wire the shut-off honor gate to the live cue (Starling / Rook boot). */
static inline void welfare_hooks_init_shutoff(struct welfare_hooks *h, struct cue *c)
{
	h->gate = welfare_gate_honor_shutoff;
	h->ctx = c;
}

static inline struct cue_command welfare_apply(const struct welfare_hooks *h,
					      struct cue_command cmd,
					      const struct geofence_result *r, int64_t now_ms)
{
	if (h && h->gate) {
		return h->gate(h->ctx, cmd, r, now_ms);
	}
	return cmd;
}

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_CORE_WELFARE_H */
