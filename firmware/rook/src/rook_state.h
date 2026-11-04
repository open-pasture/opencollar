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
};

void rook_state_take(const struct app *a, struct rook_dev_state *out);

#endif
