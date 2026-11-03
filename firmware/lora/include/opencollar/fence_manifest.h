/*
 * Signed fence manifest: farm id, fence_seq, issued_at, polygon hash,
 * fragment count, per-fragment hashes. Signature is Ed25519 over
 * OC_FH_MANIFEST_DOMAIN || body (fleet/farm signer, never the relayer).
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef OPENCOLLAR_FENCE_MANIFEST_H
#define OPENCOLLAR_FENCE_MANIFEST_H

#include "opencollar/fence_ids.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct oc_fh_manifest {
	uint8_t farm_id[OC_FH_FARM_ID_LEN];
	uint32_t fence_seq;
	uint32_t issued_at;
	uint8_t poly_hash[OC_FH_POLY_HASH_LEN];
	uint16_t frag_count;
	uint8_t frag_hash[OC_FH_MAX_FRAGMENTS][OC_FH_FRAG_HASH_LEN];
} oc_fh_manifest_t;

/* Encode unsigned body into out (cap bytes). Returns length or 0 on error. */
size_t oc_fh_manifest_encode_body(const oc_fh_manifest_t *m, uint8_t *out, size_t cap);

/* Decode body. Returns 0 on success. */
int oc_fh_manifest_decode_body(oc_fh_manifest_t *m, const uint8_t *in, size_t len);

/* Body length for a given fragment count. */
size_t oc_fh_manifest_body_len(uint16_t frag_count);

/*
 * Build wire message: type | sig[64] | body.
 * sign(sig, body_preimage) is caller-provided (tests use Monocypher).
 * Returns total length or 0.
 */
typedef void (*oc_fh_sign_fn)(uint8_t sig[OC_FH_SIG_LEN], const uint8_t *msg, size_t len,
                              void *ctx);

size_t oc_fh_manifest_seal(const oc_fh_manifest_t *m, uint8_t *out, size_t cap,
                           oc_fh_sign_fn sign, void *sign_ctx);

/*
 * Verify signature and decode. verify returns 0 on success.
 * out_m may be NULL to only check the signature/layout.
 */
typedef int (*oc_fh_verify_fn)(const uint8_t sig[OC_FH_SIG_LEN], const uint8_t *msg,
                               size_t len, void *ctx);

int oc_fh_manifest_open(const uint8_t *msg, size_t len, oc_fh_manifest_t *out_m,
                        oc_fh_verify_fn verify, void *verify_ctx);

/* Hash helpers (Blake2b via Monocypher when linked; see fence_hash.c). */
void oc_fh_hash_payload(uint8_t out[OC_FH_POLY_HASH_LEN], const uint8_t *data, size_t len);
void oc_fh_hash_fragment(uint8_t out[OC_FH_FRAG_HASH_LEN], const uint8_t *data, size_t len);

#ifdef __cplusplus
}
#endif

#endif /* OPENCOLLAR_FENCE_MANIFEST_H */
