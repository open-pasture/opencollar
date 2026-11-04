/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 */
#ifndef STARLING_APP_H
#define STARLING_APP_H

#include <stdbool.h>
#include <stdint.h>

#include "cue.h"
#include "fence_store.h"
#include "geofence.h"
#include "gnss.h"
#include "gossip.h"
#include "power.h"
#include "welfare.h"

#ifdef STARLING_HAS_LORA
#include "oc_fh_store_nvs.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define STARLING_FW_VERSION "0.1.2-starling"

struct starling_app {
	struct gnss gnss;
	struct fence_store store;
	struct geofence fence;
	struct geofence_config geo_cfg;
	struct cue cue;
	struct cue_config cue_cfg;
	struct welfare_hooks welfare;
	struct starling_gossip gossip;
	struct power_sched power;
#ifdef STARLING_HAS_LORA
	starling_fh_nvs_t fh_nvs; /* oc_fh_store_t over NVS (INTEGRATION.md) */
#endif
	bool starling_serve;
	bool fenced;
	struct cue_command last_cmd;
	struct geofence_result last_geo;
};

struct starling_tick_out {
	bool fenced;
	struct geofence_result geo;
	struct cue_command cue;
	enum power_phase power;
	uint32_t fence_seq;
};

void starling_app_init(struct starling_app *a, bool starling_serve);

#ifdef STARLING_HAS_LORA
/*
 * Bind radio + farm verify + payload_verify, then restore from NVS before
 * any poll. Call after store_init() / starling_app_init().
 */
void starling_app_bind_gossip(struct starling_app *a, uint16_t node_id,
			      const uint8_t farm_id[OC_FH_FARM_ID_LEN], oc_radio_t *radio,
			      oc_fh_verify_fn verify, void *verify_ctx,
			      oc_fh_payload_verify_fn payload_verify, void *payload_verify_ctx,
			      uint32_t (*now_ms)(void *), void *clock_ctx);
#endif

void starling_app_bind_gnss(struct starling_app *a, enum gnss_backend backend,
			    const struct gnss_ops *ops, void *ctx);

/*
 * Boot: load geo fence_store, then (if LoRa bound) ensure gossip restore
 * already ran so HWM/active are in RAM before radio traffic.
 */
int starling_app_boot(struct starling_app *a, int64_t now_ms);

int starling_app_set_fence(struct starling_app *a, const struct starling_fence_blob *blob,
			   uint32_t received_at_ms);

struct starling_tick_out starling_app_tick(struct starling_app *a, int64_t now_ms);

#ifdef __cplusplus
}
#endif

#endif
