/*
 * The collar's core, without Zephyr: provisioning, config, slots, pending
 * acks, the fence and the cue policy, wired together. main.c feeds it GNSS
 * fixes and console lines and plays what it returns; host tests drive it the
 * same way.
 *
 * Clocks: now_ms is uptime (monotonic, for cue timing). GNSS UTC from fixes
 * is the only clock for boundary activation and for ack times; between fixes
 * it is carried forward on the uptime counter. Nothing unsigned from a
 * server sets it.
 *
 * Boot: provisioning from NVS id 1 (none: GNSS only), config from id 3,
 * slots from 0x100 + i with the latest active boundary enforced at once,
 * pending acks from id 2. No stored boundary means no fence and no cues;
 * the collar never invents one (a bench boundary only with
 * CONFIG_OPENCOLLAR_BENCH_BOUNDARY, as version 0, RAM only).
 *
 * Console lines (§3.9):
 *   provision <payload>  -> ok <collar id> | error <code>
 *   status               -> collar id, herd id, fw, config version, slots
 *   boundary <command>   -> the same path as a download: applied/received/rejected
 *   config <command>     -> the same path as a report response: ok <version> | error <code>
 */
#ifndef OPENCOLLAR_APP_H
#define OPENCOLLAR_APP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "acks.h"
#include "command.h"
#include "config.h"
#include "cue.h"
#include "geofence.h"
#include "provision.h"
#include "slots.h"

#define APP_FW_VERSION "0.2.0"

struct app_fix_in {
	bool valid;
	double lat, lon;
	double accuracy_m;
	bool has_time;
	int64_t utc; /* GNSS UTC of this fix, Unix seconds */
};

struct app_fix_out {
	bool fenced; /* A boundary is in force */
	uint32_t version;
	struct geofence_result r;
	struct cue_command cmd;
	bool applied; /* A staged boundary took effect at this fix */
	struct slot_ack ack;
};

struct app {
	struct provision prov;
	struct config cfg;
	struct slots slots;
	struct acks acks;
	struct geofence_config defaults;
	struct geofence fences[2]; /* The active one and a scratch one to build into */
	struct geofence *fence;    /* NULL: no boundary, no cues */
	struct cue cue;
	bool has_clock;
	int64_t clock_utc;
	int64_t clock_ms;
	int64_t now_ms; /* Uptime of the call in progress */
	int32_t e7[SHAPE_BUF_VERTICES][2];
	struct boundary_cmd cmd;
};

void app_init(struct app *a, const struct cue_config *cue_cfg,
	      const struct geofence_config *defaults);

/* Load everything from the store and enforce the active boundary */
void app_boot(struct app *a, int64_t now_ms);

/* A bench boundary as version 0 (RAM only), when no boundary is in force */
bool app_bench(struct app *a, const struct geo_point *vertices, int n, int64_t now_ms);

struct app_fix_out app_fix(struct app *a, const struct app_fix_in *fix, int64_t now_ms);

/* A downloaded boundary command. The ack (if any) is queued and copied to *ack. */
enum reject_code app_boundary(struct app *a, const char *wire, size_t len, int64_t now_ms,
			      struct slot_ack *ack, bool *has_ack);

/* A config command from a report response */
enum reject_code app_config(struct app *a, const char *wire, size_t len, int64_t now_ms);

/* One console line (without the line ending). The reply is NUL-terminated;
 * empty when there is nothing to say. */
void app_line(struct app *a, const char *line, size_t len, bool overflow, int64_t now_ms,
	      char *reply, size_t cap);

/* GNSS time now, carried forward from the last fix; false before the first */
bool app_now(const struct app *a, int64_t now_ms, int64_t *utc);

/* The herd boundaries are checked against: the config's, else provisioning's */
const struct proto_id *app_herd(const struct app *a);

#endif
