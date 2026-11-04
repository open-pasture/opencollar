/*
 * Fence-gossip wire codecs (beacon, fragment, need, have).
 * All multi-byte integers are big-endian on the wire.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_FENCE_WIRE_H
#define OPENCOLLAR_FENCE_WIRE_H

#include "opencollar/fence_ids.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct oc_fh_beacon {
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint32_t fence_seq;
	uint8_t short_hash[OC_FH_SHORT_HASH_LEN];
	uint8_t hop_reserved; /* always 0 for fence path; reserved for telemetry */
} oc_fh_beacon_t;

typedef struct oc_fh_fragment {
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint32_t fence_seq;
	uint16_t idx;
	uint16_t count;
	const uint8_t *data;
	uint16_t data_len;
} oc_fh_fragment_t;

typedef struct oc_fh_need {
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint32_t fence_seq;
	uint16_t from; /* first bit = fragment `from` */
	uint8_t bitmap_len;
	uint8_t bitmap[OC_FH_MAX_FRAGMENTS / 8u]; /* bit i set => fragment from+i missing */
} oc_fh_need_t;

typedef struct oc_fh_have {
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint32_t fence_seq;
	uint8_t short_hash[OC_FH_SHORT_HASH_LEN];
} oc_fh_have_t;

size_t oc_fh_encode_beacon(const oc_fh_beacon_t *b, uint8_t *out, size_t cap);
int oc_fh_decode_beacon(oc_fh_beacon_t *b, const uint8_t *in, size_t len);

size_t oc_fh_encode_fragment(const oc_fh_fragment_t *f, uint8_t *out, size_t cap);
int oc_fh_decode_fragment(oc_fh_fragment_t *f, const uint8_t *in, size_t len);

size_t oc_fh_encode_need(const oc_fh_need_t *n, uint8_t *out, size_t cap);
int oc_fh_decode_need(oc_fh_need_t *n, const uint8_t *in, size_t len);

size_t oc_fh_encode_have(const oc_fh_have_t *h, uint8_t *out, size_t cap);
int oc_fh_decode_have(oc_fh_have_t *h, const uint8_t *in, size_t len);

/* Bitmap helpers: bit i set means fragment (from + i) is missing. */
void oc_fh_bitmap_set(uint8_t *bm, unsigned bit);
void oc_fh_bitmap_clear(uint8_t *bm, unsigned bit);
int oc_fh_bitmap_get(const uint8_t *bm, unsigned bit);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_FENCE_WIRE_H */
