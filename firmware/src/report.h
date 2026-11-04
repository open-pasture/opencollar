/*
 * Position-report fragments for welfare and device caps (v1 JSON).
 *
 * Hooks only: the Rook LTE transport (PR #12 / rook-lte-v1) owns the full
 * report body. Call these to append the welfare block and to list caps that
 * include `rearm`. Field names are in wire_fields.h.
 */
#ifndef OPENCOLLAR_REPORT_H
#define OPENCOLLAR_REPORT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "cue.h"
#include "wire_fields.h"

struct report_welfare {
	bool enforcement_off;
	bool has_shutoff_at;
	int64_t shutoff_at; /* Unix seconds */
	uint8_t escape_cycles;
	uint32_t rearm_seq;
};

/* Caps a V0 collar with rearm lists (NUL-terminated list of string literals). */
extern const char *const REPORT_CAPS[];
extern const size_t REPORT_CAPS_N;

/*
 * Write the welfare object (no surrounding key) into out.
 * {"enforcement":"off","shutoff_at":"…","escape_cycles":3,"rearm_seq":1}
 * Returns bytes written (no NUL) or -1 if it does not fit.
 */
int report_encode_welfare(const struct report_welfare *w, char *out, size_t cap);

/*
 * Encode one welfare_events[] element from a queued event.
 * Times: at_ms is uptime; when has_at_utc, at is rendered as RFC3339 from at_utc.
 * Returns bytes written or -1.
 */
int report_encode_welfare_event(const struct welfare_event *e, bool has_at_utc, int64_t at_utc,
				char *out, size_t cap);

#endif
