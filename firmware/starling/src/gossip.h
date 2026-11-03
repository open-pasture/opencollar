/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * Starling glue around PR #6's fence-gossip node (oc_fh_node_*).
 * When STARLING_HAS_LORA is unset, init/poll are no-ops (fake-GNSS builds).
 */
#ifndef STARLING_GOSSIP_H
#define STARLING_GOSSIP_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "fence_store.h"
#include "opencollar/fence_ids.h"
#include "opencollar/fence_node.h"

#ifdef STARLING_HAS_LORA
#include "opencollar/radio_hal.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define STARLING_GOSSIP_RX_MTU 256
#define STARLING_GOSSIP_TX_MTU 256

struct starling_gossip {
	struct fence_store *store;
	bool enabled;
	bool starling_serve;
	unsigned apply_count;
	unsigned reject_seq_count;
#ifdef STARLING_HAS_LORA
	oc_fh_node_t node;
	oc_fh_config_t cfg;
	oc_fh_buffers_t buf;
	uint8_t active_payload[STARLING_FENCE_PAYLOAD_MAX];
	uint8_t pending_payload[STARLING_FENCE_PAYLOAD_MAX];
	uint8_t rx_scratch[STARLING_GOSSIP_RX_MTU];
	uint8_t tx_scratch[STARLING_GOSSIP_TX_MTU];
#endif
};

#ifdef STARLING_HAS_LORA
void starling_gossip_init(struct starling_gossip *g, struct fence_store *store, uint16_t node_id,
			  const uint8_t farm_id[OC_FH_FARM_ID_LEN], bool starling_serve,
			  oc_radio_t *radio, oc_fh_verify_fn verify, void *verify_ctx,
			  uint32_t (*now_ms)(void *), void *clock_ctx);
int starling_gossip_inject_local(struct starling_gossip *g, const uint8_t *sealed_manifest,
				 size_t mlen, const uint8_t *payload, size_t plen);
#else
void starling_gossip_init(struct starling_gossip *g, struct fence_store *store, uint16_t node_id,
			  const uint8_t farm_id[OC_FH_FARM_ID_LEN], bool starling_serve,
			  void *radio, void *verify, void *verify_ctx, uint32_t (*now_ms)(void *),
			  void *clock_ctx);
#endif

void starling_gossip_poll(struct starling_gossip *g);

#ifdef __cplusplus
}
#endif

#endif
