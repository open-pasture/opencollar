/*
 * Test/host helper: split payload and seal a manifest with injectable sign.
 * Not required on collar flash path (server seals; Rook injects).
 */
#ifndef OPENCOLLAR_FENCE_BUILD_H
#define OPENCOLLAR_FENCE_BUILD_H

#include "opencollar/fence_manifest.h"

#include <stddef.h>
#include <stdint.h>

typedef struct oc_fh_built {
	oc_fh_manifest_t manifest;
	uint8_t sealed[1 + 64 + 1 + 8 + 4 + 4 + 32 + 2 + 64 * 16];
	size_t sealed_len;
	uint16_t frag_data_max;
} oc_fh_built_t;

int oc_fh_build_signed(oc_fh_built_t *out, const uint8_t farm_id[8], uint32_t fence_seq,
                       uint32_t issued_at, const uint8_t *payload, size_t plen,
                       uint16_t frag_data_max, oc_fh_sign_fn sign, void *sign_ctx);

#endif
