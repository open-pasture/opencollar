/* SPDX-License-Identifier: Apache-2.0 */
/*
 * What the report and the boundary query need from the core (struct app),
 * copied on the main thread so the reporter thread never reads struct app.
 * Plain C, host-testable.
 */
#ifndef ROOK_STATE_H
#define ROOK_STATE_H

#include <stdbool.h>
#include <stdint.h>

#include "app.h"

struct rook_slot_info {
	uint32_t version;
	bool applied;
	bool has_effective_at;
	int64_t effective_at; /* Unix s */
};

struct rook_dev_state {
	bool provisioned;
	struct collar_limits limits;
	uint8_t n_slots;
	struct rook_slot_info slot[SLOT_IDS];
	uint32_t have, free;
	bool has_free_bytes;
	uint32_t free_bytes;
	bool has_config;
	uint32_t config_version;
	bool has_config_reject;
	uint32_t config_reject_version;
	uint8_t config_reject_code; /* enum reject_code */
	char endpoint[PROTO_MAX_ENDPOINT_BYTES + 1]; /* config's, else provisioning's */
	uint32_t report_s;
	bool has_ack;          /* The oldest ack waiting in the core's queue (NVS id 2) */
	struct slot_ack ack;
	uint8_t acks_waiting;
};

void rook_state_take(const struct app *a, struct rook_dev_state *out);

/* What an ack POST's status does to it */
enum rook_ack_fate {
	ROOK_ACK_KEEP, /* network, 401, 408, 429, 5xx: resend later (it stays in NVS) */
	ROOK_ACK_DONE, /* 2xx: delivered */
	ROOK_ACK_DROP, /* any other 4xx: the server will never take it; drop */
};
enum rook_ack_fate rook_ack_fate(int status);

/*
 * After POSTing `sent`: pop it from the core's queue (persisted) when its
 * fate is DONE or DROP and it is still the oldest. Main thread only.
 * Returns true when it was popped.
 */
bool rook_acks_settle(struct app *a, const struct slot_ack *sent, int status);

#endif
