/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Welfare cue hooks shared by Rook and Starling.
 *
 * No numeric caps here — PR #2 owns those values and needs Cody's approval.
 * Until PR #2 lands, the default gate is "no cap" (pass the cue through).
 *
 * Shut-off (PR #22): once auto shut-off trips, enforcement stays off until an
 * explicit caretaker cue_clear_shutoff (not a fence move / cue_rearm). The
 * welfare gate must honor cue.enforcement_off as a hard suppress — cue_update
 * already returns silent when shut off; this hook is the shared policy
 * surface so Starling/Rook cannot "forget" that rule.
 *
 * Persist + signed remote re-arm (draft PR #25): Starling does NOT yet load
 * welfare_store / rearm over LoRa — see RUNBOOK TODO(cody).
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
 * ctx is caller-owned. A NULL fn means no cap.
 *
 * TODO(cody): welfare cap decision (PR #2) — implement real caps in the
 * shared cue path; do not hard-code thresholds in Starling.
 */
typedef struct cue_command (*welfare_gate_fn)(void *ctx, struct cue_command cmd,
					     const struct geofence_result *r,
					     int64_t now_ms);

struct welfare_hooks {
	welfare_gate_fn gate; /* NULL = no cap */
	void *ctx;
};

/* Default: pass cue through unchanged (no welfare cap). */
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
 * Does not clear shut-off; only cue_clear_shutoff / PR #25 rearm does.
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
