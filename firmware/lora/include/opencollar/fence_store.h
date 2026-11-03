/*
 * Persistence for fence high-water mark and active fence blob.
 * Apps implement over NVS; host tests / sim use oc_fh_store_ram.
 *
 * Contract (power-cut safe):
 *   1. Write HWM first (monotonic; never decreases).
 *   2. Then write the active fence as two copies (A/B) each with a CRC.
 *      Commit by selecting the new primary only after that copy's CRC is
 *      valid. A torn write leaves the other copy loadable → old fence kept.
 *   3. Callers must treat non-zero returns from set_hwm / save_active as
 *      failure: do not promote the fence in RAM (see persist path in
 *      fence_node.c).
 *
 * PLACEHOLDER names. SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_FENCE_STORE_H
#define OPENCOLLAR_FENCE_STORE_H

#include "opencollar/fence_ids.h"
#include "opencollar/fence_manifest.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct oc_fh_store oc_fh_store_t;

struct oc_fh_store {
	void *ctx;
	int (*get_hwm)(oc_fh_store_t *s, uint32_t *out_seq);
	int (*set_hwm)(oc_fh_store_t *s, uint32_t seq);
	int (*save_active)(oc_fh_store_t *s, const oc_fh_freshness_t *fr,
	                    const uint8_t *payload, size_t plen,
	                    const uint8_t *manifest_wire, size_t mlen,
	                    const oc_fh_manifest_t *manifest);
	int (*load_active)(oc_fh_store_t *s, oc_fh_freshness_t *fr, uint8_t *payload,
	                    size_t payload_cap, size_t *out_plen, uint8_t *manifest_wire,
	                    size_t wire_cap, size_t *out_mlen, oc_fh_manifest_t *manifest);
};

/* One A/B slot: payload + wire + CRC over the logical record. */
typedef struct oc_fh_store_ram_slot {
	uint8_t occupied;
	uint32_t crc;
	oc_fh_freshness_t fr;
	oc_fh_manifest_t manifest;
	uint8_t payload[OC_FH_MAX_PAYLOAD];
	size_t plen;
	uint8_t wire[OC_FH_MANIFEST_WIRE_MAX];
	size_t mlen;
} oc_fh_store_ram_slot_t;

typedef struct oc_fh_store_ram {
	oc_fh_store_t api;
	uint32_t hwm;
	oc_fh_store_ram_slot_t slot[2];
	uint8_t primary; /* 0 or 1; last successfully committed copy */

	/*
	 * Fault injection (tests):
	 *   fail_next_save  — next save_active returns -1; no slot changed
	 *   tear_next_save  — write new copy with bad CRC; leave primary on old
	 */
	int fail_next_save;
	int tear_next_save;
} oc_fh_store_ram_t;

void oc_fh_store_ram_init(oc_fh_store_ram_t *ram);

/* Helpers for tests / callers that need "is anything stored". */
int oc_fh_store_ram_have_active(const oc_fh_store_ram_t *ram);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_FENCE_STORE_H */
