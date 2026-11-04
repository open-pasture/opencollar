/*
 * Persisted welfare / rearm high-water state (NVS id STORE_ID_WELFARE).
 *
 * Survives reboot: auto shut-off stays off until an explicit re-arm.
 * rearm_seq is a lifetime counter: never reset or lowered (not on provision,
 * serial rearm, boot, or a server database restore that goes backwards).
 *
 * Record layout follows the pending-ack pattern: magic, fields, CRC-32.
 */
#ifndef OPENCOLLAR_WELFARE_STORE_H
#define OPENCOLLAR_WELFARE_STORE_H

#include <stdbool.h>
#include <stdint.h>

struct welfare_store {
	bool enforcement_off;
	bool has_shutoff_at;
	int64_t shutoff_at; /* Unix seconds when shut-off tripped */
	uint8_t escape_cycles;
	bool has_window_start;
	int64_t window_start; /* Unix seconds; start of escape-cycle window */
	uint32_t rearm_seq;   /* Highest accepted rearm_seq (0 = none yet) */
	uint32_t store_errors;
};

void welfare_store_init(struct welfare_store *w);
void welfare_store_load(struct welfare_store *w);
/* Persist. rearm_seq in *w must be >= the previously stored value; a lower
 * value is ignored and the held seq is kept (never lowered). */
int welfare_store_save(struct welfare_store *w);
/* Clear shut-off and cycle counters for a caretaker / server re-arm, keeping
 * rearm_seq. */
void welfare_store_clear_shutoff(struct welfare_store *w);
/* Advance rearm_seq (only upwards) and clear shut-off. */
void welfare_store_accept_rearm(struct welfare_store *w, uint32_t rearm_seq);
/* Provisioning: wipe shut-off / cycles but keep rearm_seq. */
void welfare_store_wipe_shutoff_keep_seq(struct welfare_store *w);

#endif
