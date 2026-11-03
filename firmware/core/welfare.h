/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Welfare cue hooks shared by Rook and Starling.
 *
 * No numeric caps here — PR #2 owns those values and needs Cody's approval.
 * Until PR #2 lands, the default gate is "no cap" (pass the cue through).
 */
#ifndef OPENCOLLAR_CORE_WELFARE_H
#define OPENCOLLAR_CORE_WELFARE_H

#include <stdbool.h>
#include <stdint.h>

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

static inline void welfare_hooks_init_none(struct welfare_hooks *h)
{
	h->gate = welfare_gate_none;
	h->ctx = NULL;
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
