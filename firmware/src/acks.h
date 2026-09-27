/*
 * Acks waiting to be delivered (protocol v1 §3.3). They survive a reboot in
 * NVS id 2 until the server takes them. Plain C over store.h, host-testable.
 *
 * The queue holds the newest ACKS_MAX; when it is full the oldest goes (the
 * next report's `slots` list is the ground truth for what the collar holds).
 */
#ifndef OPENCOLLAR_ACKS_H
#define OPENCOLLAR_ACKS_H

#include <stdbool.h>
#include <stdint.h>

#include "slots.h"

#define ACKS_MAX 16

struct acks {
	struct slot_ack q[ACKS_MAX];
	uint8_t n;
};

/* Load from the store (an unreadable entry reads as empty) */
void acks_load(struct acks *a);
/* Queue one and persist. Returns 0 or a negative errno from the store. */
int acks_push(struct acks *a, const struct slot_ack *ack);
/* The oldest, if any */
const struct slot_ack *acks_peek(const struct acks *a);
/* The oldest was delivered */
int acks_pop(struct acks *a);
/* Provisioning: forget them all */
int acks_clear(struct acks *a);

#endif
