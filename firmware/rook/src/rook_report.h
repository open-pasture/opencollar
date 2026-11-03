/* SPDX-License-Identifier: Apache-2.0 */
/*
 * The v1 position report body (protocol/README.md "Position report"),
 * kept small: only the fields below. Plain C, host-testable.
 *
 * {"boundary_version":57,"collar_id":"col_1",
 *  "device":{"fw":"0.2.0","caps":["holes","slots","collar_id","cue_mode"]},
 *  "fixes":[{"at":"2026-11-02T18:00:00Z","point":[-92.405,38.124],
 *            "accuracy_m":1.8,"sats":9,"fence":"inside","margin_m":12.34}],
 *  "battery":0.81,
 *  "health":{"battery_v":3.31,"charging":true,"uptime_s":86400,"dropped":0}}
 *
 * Rook additions (flagged in docs/runbooks/rook-lte-v1.md; unknown fields
 * are ignored by v1 servers): "collar_id" (the device id, also implied by
 * the bearer key), per-fix "fence"/"margin_m", health "dropped". The key
 * "roster" is reserved for the Starling freshness summary and not sent yet.
 */
#ifndef ROOK_REPORT_H
#define ROOK_REPORT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "rook_queue.h"

struct rook_report_info {
	const char *collar_id;
	const char *fw;
	uint32_t boundary_version; /* 0: none in force */
	bool has_battery;
	float soc;       /* 0..1 */
	float battery_v;
	bool has_charging;
	bool charging;
	uint32_t uptime_s;
	uint32_t dropped; /* Samples lost to a full queue */
};

/*
 * Encode the report with as many of the oldest queued samples as fit in cap
 * (at most max_fixes). Returns the body length (NUL-terminated) or -1 when
 * even zero fixes don't fit. *n_fixes: how many samples went in.
 */
int rook_report_encode(const struct rook_report_info *info, const struct rook_queue *q,
		       uint16_t max_fixes, char *out, size_t cap, uint16_t *n_fixes);

const char *rook_fence_state_str(enum rook_fence_state s);

#endif
