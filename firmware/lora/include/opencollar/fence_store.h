/*
 * Persistence for fence high-water mark and active fence blob.
 * Apps implement over NVS; host tests / sim use oc_fh_store_ram.
 *
 * Contract (power-cut safe, atomic HWM + active):
 *   1. HWM and the active fence live in the **same** A/B record, each copy
 *      covered by one CRC. They commit together — never write HWM in a
 *      separate durable step before the active blob.
 *   2. Write the new record into the inactive slot; commit by selecting that
 *      slot as primary only after its CRC is valid. A torn write leaves the
 *      other copy loadable → old fence **and** old HWM kept together.
 *   3. `save_active` is the durable commit. Callers must treat a non-zero
 *      return as failure and must not promote the fence in RAM
 *      (`persist_fence` in fence_node.c).
 *   4. `get_hwm` reads the HWM from the committed A/B record (fallback copy
 *      if primary is torn). `set_hwm` is optional / soft only — durable
 *      backends may no-op it; do not rely on it for power-cut safety.
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
	/* HWM from the committed A/B record (see contract above). */
	int (*get_hwm)(oc_fh_store_t *s, uint32_t *out_seq);
	/* Soft/optional; durable HWM advances only via save_active. */
	int (*set_hwm)(oc_fh_store_t *s, uint32_t seq);
	/* Atomic commit of active fence + HWM into one A/B+CRC record. */
	int (*save_active)(oc_fh_store_t *s, const oc_fh_freshness_t *fr,
	                    const uint8_t *payload, size_t plen,
	                    const uint8_t *manifest_wire, size_t mlen,
	                    const oc_fh_manifest_t *manifest);
	int (*load_active)(oc_fh_store_t *s, oc_fh_freshness_t *fr, uint8_t *payload,
	                    size_t payload_cap, size_t *out_plen, uint8_t *manifest_wire,
	                    size_t wire_cap, size_t *out_mlen, oc_fh_manifest_t *manifest);
};

/* One A/B slot: HWM + payload + wire + CRC over the logical record. */
typedef struct oc_fh_store_ram_slot {
	uint8_t occupied;
	uint32_t crc;
	uint32_t hwm; /* committed with this copy */
	oc_fh_freshness_t fr;
	oc_fh_manifest_t manifest;
	uint8_t payload[OC_FH_MAX_PAYLOAD];
	size_t plen;
	uint8_t wire[OC_FH_MANIFEST_WIRE_MAX];
	size_t mlen;
} oc_fh_store_ram_slot_t;

typedef struct oc_fh_store_ram {
	oc_fh_store_t api;
	oc_fh_store_ram_slot_t slot[2];
	uint8_t primary; /* 0 or 1; last successfully committed copy */

	/*
	 * Fault injection (tests):
	 *   fail_next_save  — next save_active returns -1; no slot changed
	 *   tear_next_save  — write new copy with bad CRC; primary points at it
	 *                     (load falls back → old fence + old HWM)
	 */
	int fail_next_save;
	int tear_next_save;
} oc_fh_store_ram_t;

void oc_fh_store_ram_init(oc_fh_store_ram_t *ram);

/* Helpers for tests / callers that need "is anything stored". */
int oc_fh_store_ram_have_active(const oc_fh_store_ram_t *ram);

/* Committed HWM from the best valid A/B slot (0 if empty). */
uint32_t oc_fh_store_ram_hwm(const oc_fh_store_ram_t *ram);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_FENCE_STORE_H */
