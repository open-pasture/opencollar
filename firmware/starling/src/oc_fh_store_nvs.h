/*
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 openpasture contributors
 *
 * NVS-backed oc_fh_store_t (PR #6 contract: A/B + CRC, atomic HWM+active).
 * Uses firmware/src/store.h ids. Host tests prefer oc_fh_store_ram from #6.
 */
#ifndef STARLING_OC_FH_STORE_NVS_H
#define STARLING_OC_FH_STORE_NVS_H

#include "opencollar/fence_store.h"

#ifdef __cplusplus
extern "C" {
#endif

/* NVS ids: two A/B slots + primary index. */
#define STORE_ID_STARLING_FH_SLOT0 0x50
#define STORE_ID_STARLING_FH_SLOT1 0x51
#define STORE_ID_STARLING_FH_PRIMARY 0x52

/* Pilot payload cap (INTEGRATION.md typical buffers). */
#define STARLING_FH_NVS_PAYLOAD_MAX 2048
#define STARLING_FH_NVS_WIRE_MAX OC_FH_MANIFEST_WIRE_MAX

typedef struct starling_fh_nvs_slot {
	uint32_t crc;
	uint32_t hwm;
	oc_fh_freshness_t fr;
	oc_fh_manifest_t manifest;
	uint16_t plen;
	uint16_t mlen;
	uint8_t occupied;
	uint8_t payload[STARLING_FH_NVS_PAYLOAD_MAX];
	uint8_t wire[STARLING_FH_NVS_WIRE_MAX];
} starling_fh_nvs_slot_t;

typedef struct starling_fh_nvs {
	oc_fh_store_t api;
	uint8_t primary;
	int ready;
} starling_fh_nvs_t;

void starling_fh_nvs_init(starling_fh_nvs_t *s);

#ifdef __cplusplus
}
#endif

#endif
