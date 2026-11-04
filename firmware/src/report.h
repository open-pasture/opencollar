/*
 * Position-report fragments for welfare, device caps and read-only telemetry
 * (v1 JSON).
 *
 * Hooks only: the Rook LTE transport (PR #12 / rook-lte-v1) owns the full
 * report body. Call these to append welfare, list caps that include `rearm`,
 * and to encode / supply the farmer-app telemetry fields:
 *   health.last_cue_at, fixes[].hdop, health.rsrp_dbm, battery (omit unknown).
 * Field names are in wire_fields.h for easy rename when the protocol record
 * lands. Do not edit the Rook transport from this tree.
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

/* One fix for the report encoder. accuracy_m is required; hdop is optional. */
struct report_fix {
	int64_t at; /* Unix seconds (RFC3339 Z on the wire) */
	double lon;
	double lat;
	double accuracy_m;
	bool has_sats;
	uint8_t sats;
	bool has_cn0;
	double cn0;
	bool has_hdop;
	double hdop; /* As the GNSS source reports (nRF PVT hdop); omit when unset */
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

/*
 * Encode one fixes[] element. accuracy_m is always present. hdop is included
 * only when f->has_hdop. Returns bytes written or -1.
 */
int report_encode_fix(const struct report_fix *f, char *out, size_t cap);

/*
 * Top-level battery field (no surrounding braces): "battery":0.81
 * When known is false, writes nothing (returns 0) — never "battery":0 for
 * unknown. A real measured empty pack (known && soc == 0) may still encode 0.
 */
int report_encode_battery(bool known, double soc, char *out, size_t cap);

/*
 * health object with only the telemetry keys this module owns:
 *   last_cue_at (RFC3339 Z) when a cue was noted with trusted time
 *   rsrp_dbm when report_set_signal_dbm() has been called
 * Returns "{}" when neither is set, bytes written, or -1.
 * last_cue_at is RAM-only: not persisted across reboot.
 */
int report_encode_health_telemetry(char *out, size_t cap);

/*
 * Note the time of a cue the collar delivered (warn / outside / future pulse).
 * Call only with trusted GNSS UTC. Omitted from the report until then.
 * Not persisted across reboot.
 */
void report_note_cue_at(int64_t utc_s);
void report_clear_last_cue_at(void);
bool report_get_last_cue_at(int64_t *out);

/*
 * LTE RSRP for health.rsrp_dbm. Wired by op-fw-rook-lte from the modem
 * reading; this tree only stores and encodes. Omit the field until set.
 * health.rssi_dbm is not used.
 */
void report_set_signal_dbm(int rsrp_dbm);
void report_clear_signal_dbm(void);
bool report_get_signal_dbm(int *out);

#endif
