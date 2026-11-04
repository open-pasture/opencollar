/* SPDX-License-Identifier: Apache-2.0 */
/*
 * Rook offline queue: a RAM ring of fixed-size samples waiting to be
 * reported. When full, the oldest sample is overwritten (newest data wins,
 * the count of lost samples is kept for health). Plain C, host-testable.
 * Not thread-safe: the caller holds a lock (rook_lte.c uses a k_mutex).
 */
#ifndef ROOK_QUEUE_H
#define ROOK_QUEUE_H

#include <stdbool.h>
#include <stdint.h>

#ifndef ROOK_QUEUE_CAP
#define ROOK_QUEUE_CAP 64
#endif

enum rook_fence_state {
	ROOK_FENCE_NONE = 0, /* No boundary in force */
	ROOK_FENCE_INSIDE,
	ROOK_FENCE_WARN,
	ROOK_FENCE_OUTSIDE,
};

struct rook_sample {
	int64_t at;          /* GNSS UTC, Unix seconds */
	int32_t lat_e7, lon_e7;
	uint16_t accuracy_dm; /* Accuracy in decimetres, saturating */
	uint8_t sats;
	uint8_t fence;        /* enum rook_fence_state */
	int32_t margin_cm;    /* Signed margin to the nearest edge */
	uint32_t boundary_version;
};

struct rook_queue {
	struct rook_sample s[ROOK_QUEUE_CAP];
	uint16_t head; /* Oldest */
	uint16_t n;
	uint32_t overwritten;
};

void rook_queue_init(struct rook_queue *q);
void rook_queue_push(struct rook_queue *q, const struct rook_sample *s);
/* The i-th oldest sample, or NULL */
const struct rook_sample *rook_queue_peek(const struct rook_queue *q, uint16_t i);
/* Drop the n oldest (after a 2xx or a 400) */
void rook_queue_drop(struct rook_queue *q, uint16_t n);

#endif
