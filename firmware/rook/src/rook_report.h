/* SPDX-License-Identifier: Apache-2.0 */
/*
 * The v1 position report body (protocol/README.md "Position report"),
 * kept small: only the fields below. Plain C, host-testable.
 *
 * {"boundary_version":57,"collar_id":"col_1",
 *  "device":{"fw":"0.2.0","caps":["holes","slots","collar_id","cue_mode","config"],
 *            "limits":{...},"config_version":3,"config_reject":{"version":4,"code":"stale"}},
 *  "slots":[{"version":57,"status":"applied"},
 *           {"version":58,"status":"received","effective_at":"..."}],
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
#include "rook_state.h"

/* The server answers 400 to a report with a time more than 10 min ahead of
 * its clock (and drops the whole batch with it): fixes more than this ahead
 * of the server's Date are left out. */
#define ROOK_MAX_AHEAD_S 540
/* Fixes before this (2024-01-01) carry a GNSS time that isn't set yet */
#define ROOK_MIN_SANE_TIME 1704067200

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
	uint32_t dropped; /* Samples lost to a full queue or a bad clock */
	const struct rook_dev_state *dev; /* NULL: no device limits, slots or config */
	bool has_server_now;
	int64_t server_now; /* From the last response's Date, carried on uptime */
};

/*
 * Encode the report with as many of the oldest queued samples as fit in cap
 * (at most max_fixes). Returns the body length (NUL-terminated) or -1 when
 * even zero fixes don't fit. *n_fixes: how many of the oldest samples were
 * used (sent, or left out for a bad time: *n_skipped of them). Drop
 * *n_fixes from the queue after a 2xx.
 */
int rook_report_encode(const struct rook_report_info *info, const struct rook_queue *q,
		       uint16_t max_fixes, char *out, size_t cap, uint16_t *n_fixes,
		       uint16_t *n_skipped);

/*
 * The ack body {"command_id","version","status","code"?,"at"}. The server
 * requires "at": the ack's own GNSS time, else fallback_at (the server's
 * Date carried on uptime), else the Unix epoch (still accepted; the server
 * keeps it as sent). Returns the length or -1.
 */
struct slot_ack;
int rook_ack_encode(const struct slot_ack *ack, bool has_fallback, int64_t fallback_at,
		    char *out, size_t cap);

/* "/boundary?have=H[&free=F][&free_bytes=B]" (free/free_bytes from dev, if any) */
int rook_boundary_query(uint32_t have, const struct rook_dev_state *dev, char *out,
			size_t cap);

const char *rook_fence_state_str(enum rook_fence_state s);

#endif
